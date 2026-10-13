from __future__ import annotations

import asyncio
import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from job_agent.config import AgentConfig, Preferences, save_config
from job_agent.connectors.base import ActionResult, ActionStatus
from job_agent.connectors.registry import ChannelAdapter, ChannelRegistry
from job_agent.database import Database, RECRUITMENT_STAGES
from job_agent.models import ApplicationStatus, Candidate, Job
from job_agent.orchestrator import JobAgent
from job_agent.service import AgentService
from job_agent.web import ApiHandler


class ProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        work = Path(__file__).resolve().parents[1] / "work"
        work.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.database_path = self.directory / "agent.sqlite3"
        self.config_path = self.directory / "config.json"
        save_config(AgentConfig(
            candidate=Candidate("测试用户"), preferences=Preferences(), greetings={"default": "您好"},
            boss={"enabled": True}, mail={"enabled": True},
        ), self.config_path)
        self.service = AgentService(self.config_path, self.database_path)

    def add_job(self, source: str = "official:example", source_id: str = "one") -> int:
        return self.service.db.upsert_job(Job(
            source=source, source_id=source_id, title="产品经理", company=f"示例公司{source_id}",
            location="北京", url=f"https://jobs.example.com/{source_id}",
        ))[0]

    def test_legacy_database_migration_preserves_original_records(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("""CREATE TABLE applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL,
                channel TEXT NOT NULL, status TEXT NOT NULL, greeting TEXT, external_id TEXT,
                evidence TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(job_id)
            )""")
            connection.execute(
                """INSERT INTO applications(job_id, channel, status, greeting, external_id, evidence,
                   error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (1, "official", ApplicationStatus.CONFIRMED.value, "旧开场白", "receipt-123", "原回执",
                 "原错误", "2026-01-01T00:00:00+00:00", "2026-01-02T00:00:00+00:00"),
            )
            before = connection.execute("SELECT * FROM applications").fetchone()
            connection.commit()
        self.add_job()
        database = Database(self.database_path)
        with database.connect() as connection:
            row = dict(connection.execute("SELECT * FROM applications WHERE id=1").fetchone())
        self.assertEqual(tuple(row.values())[:len(before)], before)
        self.assertIsNone(row["recruitment_stage"])
        record = database.get_application(1)
        self.assertEqual(record["recruitment_stage"], "已投递")
        self.assertEqual(record["progress_source"], "legacy_status")
        self.assertEqual(record["progress_updated_at"], "2026-01-02T00:00:00+00:00")
        self.assertEqual(Database(self.database_path).get_application(1), record)

    def test_manual_record_is_local_and_not_queued_for_execution(self) -> None:
        job_id = self.add_job()
        with patch.object(self.service, "agent", side_effect=AssertionError("must not call agent")):
            record = self.service.record_manual_application({"job_id": job_id, "stage": "已投递", "note": "官网手工提交"})
            updated = self.service.update_application_progress(record["id"], {"stage": "面试", "note": "等待第二轮"})
        self.assertEqual(record["status"], ApplicationStatus.NEEDS_HUMAN.value)
        self.assertEqual(record["channel"], "official")
        self.assertIsNone(record["external_id"])
        self.assertIsNone(record["evidence"])
        self.assertEqual(updated["recruitment_stage"], "面试")
        self.assertEqual(updated["progress_source"], "manual")
        self.assertEqual(self.service.applications()[0]["progress_note"], "等待第二轮")
        self.assertEqual(self.service.db.list_applications(include_manual=False), [])
        self.assertEqual(self.service.jobs()[0]["status"], "已发现")

    def test_manual_update_does_not_rewrite_execution_evidence_or_timestamps(self) -> None:
        job_id = self.add_job()
        database = self.service.db
        application_id = database.create_application(job_id, "official", "保留开场白")
        database.update_application(
            application_id, ApplicationStatus.OFFICIAL_SUBMITTED,
            evidence="等待原回执", error="原错误", external_id="ats-42",
        )
        before = database.get_application(application_id)
        updated = self.service.update_application_progress(application_id, {"stage": "Offer", "note": "电话收到 Offer"})
        for field in ("status", "greeting", "external_id", "evidence", "error", "created_at", "updated_at"):
            self.assertEqual(updated[field], before[field])
        self.assertEqual(updated["recruitment_stage"], "Offer")
        self.assertEqual(updated["progress_note"], "电话收到 Offer")
        self.assertTrue(updated["progress_updated_at"])
        self.assertEqual(database.get_application(application_id), updated)

    def test_repeated_create_updates_one_record_and_omitted_note_is_preserved(self) -> None:
        job_id = self.add_job()
        first = self.service.record_manual_application({"job_id": job_id, "stage": "已投递", "note": "已提交"})
        second = self.service.record_manual_application({"job_id": job_id, "stage": "面试"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["progress_note"], "已提交")
        self.assertEqual(len(self.service.applications()), 1)
        event_count = len(self.service.events())
        unchanged = self.service.record_manual_application({"job_id": job_id, "stage": "面试"})
        self.assertEqual(unchanged["progress_updated_at"], second["progress_updated_at"])
        self.assertEqual(len(self.service.events()), event_count)
        cleared = self.service.update_application_progress(first["id"], {"stage": "面试", "note": ""})
        self.assertEqual(cleared["progress_note"], "")

    def test_concurrent_duplicate_create_keeps_unique_application(self) -> None:
        job_id = self.add_job()
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(lambda _: self.service.record_manual_application(
                {"job_id": job_id, "stage": "已投递"}), range(3)))
        self.assertEqual(len({record["id"] for record in results}), 1)
        self.assertEqual(len(self.service.applications()), 1)
        self.assertEqual(len(self.service.events()), 1)

    def test_legacy_stages_use_execution_status_without_claiming_unverified_submission(self) -> None:
        expected = {
            ApplicationStatus.PLANNED: "准备投递", ApplicationStatus.GREETING_SENT: "沟通中",
            ApplicationStatus.AWAITING_REPLY: "沟通中", ApplicationStatus.HR_REPLIED: "沟通中",
            ApplicationStatus.RESUME_SENT: "沟通中", ApplicationStatus.OFFICIAL_SUBMITTED: "提交待确认",
            ApplicationStatus.CONFIRMED: "已投递", ApplicationStatus.REJECTED: "已结束",
            ApplicationStatus.CLOSED: "已结束", ApplicationStatus.NEEDS_HUMAN: "待确认",
            ApplicationStatus.NEEDS_LOGIN: "待确认", ApplicationStatus.UNVERIFIED: "待确认",
            ApplicationStatus.FAILED: "待确认",
        }
        database = self.service.db
        for index, (status, stage) in enumerate(expected.items()):
            job_id = self.add_job(source_id=str(index))
            application_id = database.create_application(job_id, "official")
            database.update_application(application_id, status)
            record = database.get_application(application_id)
            with self.subTest(status=status):
                self.assertEqual(record["recruitment_stage"], stage)
                self.assertEqual(record["status"], status.value)
                self.assertEqual(record["progress_source"], "legacy_status")

    def test_payload_validation_rejects_bad_ids_stages_and_notes_without_changes(self) -> None:
        job_id = self.add_job()
        bad_payloads = [
            {}, {"job_id": job_id}, {"stage": "已投递"},
            {"job_id": True, "stage": "已投递"}, {"job_id": str(job_id), "stage": "已投递"},
            {"job_id": 0, "stage": "已投递"}, {"job_id": -1, "stage": "已投递"},
            {"job_id": 2**64, "stage": "已投递"}, {"job_id": 999, "stage": "已投递"},
            {"job_id": job_id, "stage": "自动投递"}, {"job_id": job_id, "stage": "待确认"},
            {"job_id": job_id, "stage": 1}, {"job_id": job_id, "stage": None},
            {"job_id": job_id, "stage": "已投递", "note": None},
            {"job_id": job_id, "stage": "已投递", "note": []},
            {"job_id": job_id, "stage": "已投递", "note": "长" * 2001}, [], None,
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises((ValueError, KeyError)):
                    self.service.record_manual_application(payload)
        self.assertEqual(self.service.applications(), [])
        self.assertEqual(self.service.events(), [])
        for application_id in (True, "1", 0, -1, 999, 2**64):
            with self.subTest(application_id=application_id):
                with self.assertRaises(ValueError):
                    self.service.update_application_progress(application_id, {"stage": "已投递"})

    def test_all_supported_stages_and_private_note_log_boundary(self) -> None:
        job_id = self.add_job()
        private_note = "HR 私人回复只保存在备注中"
        record = self.service.record_manual_application({"job_id": job_id, "stage": "准备投递", "note": private_note})
        for stage in RECRUITMENT_STAGES:
            updated = self.service.update_application_progress(record["id"], {"stage": stage})
            self.assertEqual(updated["recruitment_stage"], stage)
        events = json.dumps(self.service.events(), ensure_ascii=False)
        self.assertNotIn(private_note, events)
        self.assertIn("application_progress_updated", events)
        self.assertEqual(self.service.applications()[0]["progress_note"], private_note)

    def test_manual_legacy_plans_and_hr_records_are_excluded_from_external_executors(self) -> None:
        database = self.service.db
        for index, channel in enumerate(("official", "boss")):
            job_id = self.add_job("official:example" if channel == "official" else "boss", str(index))
            application_id = database.create_application(job_id, channel)
            self.service.update_application_progress(application_id, {"stage": "已投递"})
        agent = self.service.agent(include_knowledge=False)
        with patch("job_agent.orchestrator.BossConnector", side_effect=AssertionError("no browser")):
            for channel in ("official", "boss"):
                self.assertEqual(asyncio.run(agent.execute(channel, live=True))["processed"], 0)
            boss_record = next(record for record in self.service.applications() if record["channel"] == "boss")
            database.update_application(boss_record["id"], ApplicationStatus.AWAITING_REPLY)
            self.assertEqual(asyncio.run(agent.check_boss_replies(live_resume_send=True))["checked"], 0)
            database.update_application(boss_record["id"], ApplicationStatus.HR_REPLIED)
            with self.assertRaisesRegex(ValueError, "手工进度"):
                asyncio.run(agent.send_boss_resume(boss_record["id"], live=True))
        official_record = next(record for record in self.service.applications() if record["channel"] == "official")
        database.update_application(official_record["id"], ApplicationStatus.OFFICIAL_SUBMITTED)
        with patch("job_agent.orchestrator.ImapReceiptChecker", side_effect=AssertionError("no mailbox")):
            self.assertEqual(agent.check_receipts()["checked"], 0)
        self.assertEqual(len(self.service.applications()), 2)

    def test_legacy_automatic_plan_remains_executable_in_a_mixed_queue(self) -> None:
        submitted_jobs: list[int] = []

        class OfflineConnector:
            async def submit(self, job, *_args, **_kwargs):
                submitted_jobs.append(job.id)
                return ActionResult(ActionStatus.CONFIRMED, "offline stub", evidence="stub receipt")

            async def close(self):
                return None

        database = self.service.db
        manual_job_id = self.add_job(source_id="manual")
        manual_application_id = database.create_application(manual_job_id, "official")
        self.service.update_application_progress(manual_application_id, {"stage": "已投递"})
        automatic_job_id = self.add_job(source_id="automatic")
        automatic_application_id = database.create_application(automatic_job_id, "official")
        registry = ChannelRegistry([ChannelAdapter(
            id="official:example", name="离线测试", channel_type="official", enabled=True,
            keywords=["产品经理"], strategy="api", url="https://jobs.example.com",
            connector_factory=OfflineConnector,
        )])
        agent = JobAgent(self.service.config, database, registry)
        result = asyncio.run(agent.execute("official", live=True))
        self.assertEqual(result["processed"], 1)
        self.assertEqual(submitted_jobs, [automatic_job_id])
        self.assertEqual(database.get_application(manual_application_id)["status"], ApplicationStatus.PLANNED.value)
        self.assertEqual(database.get_application(automatic_application_id)["status"], ApplicationStatus.CONFIRMED.value)
        self.assertEqual(database.get_application(automatic_application_id)["progress_source"], "legacy_status")

    def test_batch_rechecks_manual_takeover_and_changed_status_before_next_submission(self) -> None:
        for takeover in ("manual", "execution_status"):
            with self.subTest(takeover=takeover):
                database = self.service.db
                pending_job_id = self.add_job(source_id=f"pending-{takeover}")
                pending_id = database.create_application(pending_job_id, "official")
                first_job_id = self.add_job(source_id=f"first-{takeover}")
                database.create_application(first_job_id, "official")
                submitted: list[int] = []

                class OfflineConnector:
                    async def submit(self, job, *_args, **_kwargs):
                        submitted.append(job.id)
                        if takeover == "manual":
                            database.update_application_progress(pending_id, "已投递", "用户已经提交")
                        else:
                            database.update_application(pending_id, ApplicationStatus.CLOSED)
                        return ActionResult(ActionStatus.CONFIRMED, "offline receipt")

                    async def close(self):
                        return None

                registry = ChannelRegistry([ChannelAdapter(
                    id="official:example", name="离线测试", channel_type="official", enabled=True,
                    keywords=["产品经理"], strategy="api", url="https://jobs.example.com",
                    connector_factory=OfflineConnector,
                )])
                result = asyncio.run(JobAgent(self.service.config, database, registry).execute("official", live=True))
                self.assertEqual(submitted, [first_job_id])
                self.assertEqual(result["processed"], 1)
                pending = database.get_application(pending_id)
                self.assertEqual(pending["status"], ApplicationStatus.PLANNED.value if takeover == "manual" else ApplicationStatus.CLOSED.value)

    def test_hr_reply_preserves_observed_fact_but_manual_takeover_stops_auto_resume(self) -> None:
        database = self.service.db
        job_id = self.add_job("boss")
        application_id = database.create_application(job_id, "boss")
        database.update_application(application_id, ApplicationStatus.AWAITING_REPLY)
        sends: list[int] = []

        class OfflineBoss:
            def __init__(self, _config):
                pass

            async def check_reply(self, _job, _greeting):
                database.update_application_progress(application_id, "面试", "人工接管")
                return ActionResult(ActionStatus.CONFIRMED, "HR reply", evidence="observed reply")

            async def send_resume(self, job, *_args, **_kwargs):
                sends.append(job.id)
                return ActionResult(ActionStatus.SUBMITTED, "unexpected send")

            async def close(self):
                return None

        config = self.service.config
        config.preferences.auto_send_resume_after_reply = True
        with patch("job_agent.orchestrator.BossConnector", OfflineBoss):
            result = asyncio.run(JobAgent(config, database).check_boss_replies(live_resume_send=True))
        self.assertEqual(result["checked"], 1)
        self.assertEqual(sends, [])
        record = database.get_application(application_id)
        self.assertEqual(record["status"], ApplicationStatus.HR_REPLIED.value)
        self.assertEqual(record["evidence"], "observed reply")
        self.assertEqual(record["recruitment_stage"], "面试")
        self.assertEqual(record["progress_note"], "人工接管")

    def test_in_flight_submission_receipt_is_preserved_without_overwriting_manual_progress(self) -> None:
        database = self.service.db
        job_id = self.add_job()
        application_id = database.create_application(job_id, "official")

        class OfflineConnector:
            async def submit(self, _job, *_args, **_kwargs):
                database.update_application_progress(application_id, "面试", "独立人工记录")
                return ActionResult(ActionStatus.CONFIRMED, "submission finished", evidence="actual receipt", external_id="ats-123")

            async def close(self):
                return None

        registry = ChannelRegistry([ChannelAdapter(
            id="official:example", name="离线测试", channel_type="official", enabled=True,
            keywords=["产品经理"], strategy="api", url="https://jobs.example.com",
            connector_factory=OfflineConnector,
        )])
        asyncio.run(JobAgent(self.service.config, database, registry).execute("official", live=True))
        record = database.get_application(application_id)
        self.assertEqual(record["status"], ApplicationStatus.CONFIRMED.value)
        self.assertEqual(record["evidence"], "actual receipt")
        self.assertEqual(record["external_id"], "ats-123")
        self.assertEqual(record["recruitment_stage"], "面试")
        self.assertEqual(record["progress_note"], "独立人工记录")
        self.assertEqual(record["progress_source"], "manual")

    def test_direct_resume_send_rechecks_after_connector_initialization(self) -> None:
        database = self.service.db
        job_id = self.add_job("boss")
        application_id = database.create_application(job_id, "boss")
        database.update_application(application_id, ApplicationStatus.HR_REPLIED)
        sends: list[int] = []

        class OfflineBoss:
            def __init__(self, _config):
                database.update_application_progress(application_id, "已结束", "停止自动处理")

            async def send_resume(self, job, *_args, **_kwargs):
                sends.append(job.id)
                return ActionResult(ActionStatus.SUBMITTED, "unexpected send")

            async def close(self):
                return None

        with patch("job_agent.orchestrator.BossConnector", OfflineBoss):
            with self.assertRaisesRegex(ValueError, "已变更"):
                asyncio.run(JobAgent(self.service.config, database).send_boss_resume(application_id, live=True))
        self.assertEqual(sends, [])
        record = database.get_application(application_id)
        self.assertEqual(record["status"], ApplicationStatus.HR_REPLIED.value)
        self.assertEqual(record["recruitment_stage"], "已结束")

    def test_http_create_update_and_bad_payloads(self) -> None:
        job_id = self.add_job()
        handler = type("ProgressApiHandler", (ApiHandler,), {
            "service": self.service, "log_message": lambda *_: None,
        })
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def request(method: str, path: str, body=None):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                try:
                    connection.request(method, path, json.dumps(body), {"Content-Type": "application/json"})
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()

            with patch.object(self.service, "agent", side_effect=AssertionError("no action runner")):
                status, created = request("POST", "/api/applications/manual", {"job_id": job_id, "stage": "已投递"})
                self.assertEqual(status, 200)
                application_id = created["id"]
                status, updated = request("PUT", f"/api/applications/{application_id}/progress", {"stage": "面试", "note": "周三面试"})
                self.assertEqual(status, 200)
                self.assertEqual(updated["recruitment_stage"], "面试")
                self.assertEqual(updated["progress_note"], "周三面试")
                status, records = request("GET", "/api/applications")
                self.assertEqual(status, 200)
                self.assertEqual(records[0], updated)
                for body in ([], None, 1, {}, {"job_id": True, "stage": "已投递"}, {"job_id": job_id, "stage": "违规阶段"}):
                    self.assertEqual(request("POST", "/api/applications/manual", body)[0], 400)
                for path, body in (
                    (f"/api/applications/{application_id}/progress", []),
                    (f"/api/applications/{application_id}/progress", {"stage": "已投递", "note": None}),
                    ("/api/applications/0/progress", {"stage": "已投递"}),
                    ("/api/applications/999/progress", {"stage": "已投递"}),
                ):
                    self.assertEqual(request("PUT", path, body)[0], 400)
                self.assertEqual(request("PUT", "/api/applications/bad/progress", {"stage": "面试"})[0], 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
