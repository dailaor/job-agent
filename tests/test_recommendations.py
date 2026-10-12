from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from job_agent.config import AgentConfig, Preferences, save_config
from job_agent.database import Database
from job_agent.knowledge.models import EmploymentType, KnowledgeChunk, PolicyDecision, PolicyStatus, PostDocument
from job_agent.knowledge.store import KnowledgeStore
from job_agent.models import Candidate, Job, JobStatus
from job_agent.recommendations import build_recommendations
from job_agent.service import AgentService
from job_agent.web import ApiHandler


class RecommendationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "work")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.database_path = self.directory / "agent.sqlite3"
        self.database = Database(self.database_path)
        self.config = AgentConfig(
            candidate=Candidate("测试用户", education="本科", skills=["Python", "SQL"], years_experience=3),
            preferences=Preferences(published_within_days=None, locations=["北京"], minimum_salary=18_000),
            greetings={"default": "您好"},
        )

    def _job(self, **values: object) -> int:
        base = {"source": "official:test", "source_id": str(len(self.database.list_jobs()) + 1),
                "title": "数据分析师", "company": "腾讯", "location": "北京",
                "url": "https://example.com/job/1", "description": "负责数据分析，熟悉 Python、SQL。",
                "education": "本科及以上", "salary_min": 20_000, "salary_max": 25_000,
                "metadata": {"salary_unit": "month", "employment_type": "full_time", "business_unit": "数据平台"}}
        base.update(values)
        identifier, _ = self.database.upsert_job(Job(**base))
        return identifier

    def _cards(self) -> list[dict]:
        return build_recommendations(self.database_path, self.config)["items"]

    def _evidence(self, text: str, *, company: str = "腾讯", employment: str = "full_time",
                  business_unit: str = "数据平台", city: str = "北京", days_ago: int = 1,
                  status: PolicyStatus = PolicyStatus.ACCEPTED, topic: str = "workload") -> tuple[int, int]:
        store = KnowledgeStore(self.database)
        unique = len(store.list_documents()) + 1
        published = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        document = PostDocument(source="manual", url=f"https://example.com/post/{unique}",
                                title=f"数据分析工作体验 {unique}", content=text, company=company,
                                role_family="data", employment_type=employment, business_unit=business_unit,
                                city=city, published_at=published)
        decision = PolicyDecision(status=status, reasons=[], company=company, role_family="data",
                                  employment_type=EmploymentType(employment), topics=[topic], quality_score=0.9,
                                  sanitized_content=text)
        result = store.save_document(document, decision, retain_full_text=False)
        document_id = int(result["document_id"])
        chunk = KnowledgeChunk(ordinal=1, topic=topic, text=text, contextual_text=text,
                               start_offset=0, end_offset=len(text), chunk_hash=f"chunk-{unique}", embedding=[1.0])
        store.replace_chunks(document_id, [chunk], embedding_provider="fixture", embedding_dimensions=1)
        with self.database.connect() as connection:
            chunk_id = int(connection.execute("SELECT id FROM knowledge_chunks WHERE document_id=?", (document_id,)).fetchone()[0])
        return document_id, chunk_id

    def test_get_reads_current_profile_and_does_not_rely_on_old_evaluation(self) -> None:
        identifier = self._job()
        self.config.candidate.skills = ["Java"]
        card = self._cards()[0]
        self.assertEqual(card["job_id"], identifier)
        self.assertEqual(card["ability"]["matched"], [])
        self.assertIn("Python", card["ability"]["missing"])
        self.assertEqual(card["ability"]["score"], 0)
        self.assertNotIn("overall_score", card)

    def test_composite_education_is_hard_but_preference_is_not(self) -> None:
        self._job(education="硕士及以上")
        self.assertEqual(self._cards()[0]["eligibility"]["status"], "blocked")
        self.assertIn("学历硬条件不满足", " ".join(self._cards()[0]["eligibility"]["reasons"]))
        self._job(source_id="soft", title="数据分析实习生", education="硕士优先")
        soft = next(card for card in self._cards() if card["title"] == "数据分析实习生")
        self.assertNotEqual(soft["eligibility"]["status"], "blocked")
        self.assertTrue(any("偏好" in text for text in soft["eligibility"]["unknowns"]))
        self._job(source_id="either", title="高级数据分析师", education="本科或硕士")
        either = next(card for card in self._cards() if card["title"] == "高级数据分析师")
        self.assertEqual(either["eligibility"]["status"], "eligible")

    def test_unknown_education_and_ats_are_not_claimed_satisfied(self) -> None:
        self._job(education="")
        card = self._cards()[0]
        self.assertEqual(card["eligibility"]["status"], "verify")
        self.assertEqual(card["decision"]["status"], "verify")
        self.assertIn("ATS 表单与提交资格尚未验证", card["eligibility"]["unknowns"])
        self.config.candidate.education = ""
        self.assertTrue(any("学历" in value for value in self._cards()[0]["eligibility"]["unknowns"]))

    def test_description_education_requirement_is_checked(self) -> None:
        self._job(education="", description="学历要求：硕士及以上。负责数据分析，熟悉 Python。")
        self.assertEqual(self._cards()[0]["eligibility"]["status"], "blocked")

    def test_education_preference_cannot_hide_a_separate_hard_requirement(self) -> None:
        self.config.candidate.education = "大专"
        for index, (education, description) in enumerate([
            ("本科及以上，硕士优先", "负责数据分析"),
            ("", "硕士优先。学历要求本科及以上。负责数据分析"),
            ("本科及以上且硕士优先", "负责数据分析"),
        ]):
            self._job(source_id=f"compound-{index}", title=f"数据分析师{index}",
                      education=education, description=description)
        self.assertTrue(all(card["eligibility"]["status"] == "blocked" for card in self._cards()))

    def test_daily_salary_does_not_become_monthly_salary_or_monthly_filter(self) -> None:
        self._job(title="数据分析实习生", salary_min=200, salary_max=300,
                  metadata={"employment_type": "internship", "salary_text": "200-300元/天"})
        card = self._cards()[0]
        self.assertEqual(card["compensation"]["unit"], "day")
        self.assertEqual(card["compensation"]["label"], "200–300元/日")
        self.assertNotEqual(card["eligibility"]["status"], "blocked")
        self.assertTrue(any("月薪口径" in value["text"] for value in card["risks"]))

    def test_daily_salary_with_other_positive_facts_still_needs_monthly_expectation_check(self) -> None:
        self.config.preferences.growth_priority = "high"
        self._job(title="数据分析实习生", salary_min=200, salary_max=300,
                  description="负责数据分析，熟悉Python、SQL。双休，不加班。提供导师和培训。",
                  metadata={"employment_type": "internship", "salary_text": "200-300元/天"})
        self.assertEqual(self._cards()[0]["decision"]["status"], "verify")

    def test_known_monthly_lower_bound_alone_is_not_rejected_as_undisclosed(self) -> None:
        self.config.preferences.unknown_field_policy = "reject"
        self._job(salary_min=20_000, salary_max=None)
        card = self._cards()[0]
        self.assertTrue(card["default_visible"])
        self.assertEqual(card["compensation"]["status"], "partial")
        self.assertTrue(any("月薪下限达到" in reason["text"] for reason in card["reasons"]))

    def test_inverted_salary_range_does_not_support_recommendation(self) -> None:
        self._job(salary_min=30_000, salary_max=20_000)
        card = self._cards()[0]
        self.assertIn("区间异常", card["compensation"]["label"])
        self.assertEqual(card["decision"]["status"], "verify")
        self.assertFalse(any("月薪下限达到" in reason["text"] for reason in card["reasons"]))

    def test_unknown_salary_unit_stays_partial_and_never_supports_recommendation(self) -> None:
        self._job(metadata={"employment_type": "full_time"})
        card = self._cards()[0]
        self.assertEqual(card["compensation"]["unit"], "unknown")
        self.assertIn("口径待核实", card["compensation"]["label"])
        self.assertEqual(card["decision"]["status"], "verify")
        self.assertFalse(any("月薪下限达到" in item["text"] for item in card["reasons"]))

    def test_salary_missing_or_partial_has_no_invented_total_package(self) -> None:
        self._job(salary_min=None, salary_max=None)
        card = self._cards()[0]
        self.assertEqual(card["compensation"]["status"], "unknown")
        fields = {item["key"]: item for item in card["compensation"]["fields"]}
        for key in ("annual_cash", "total_package", "effective_hourly"):
            self.assertEqual(fields[key]["status"], "unknown")
            self.assertEqual(fields[key]["value"], "未披露")
        self._job(source_id="partial", title="商业数据分析师", salary_min=None, salary_max=25_000)
        partial = next(item for item in self._cards() if item["title"] == "商业数据分析师")
        self.assertEqual(partial["compensation"]["status"], "partial")
        self.assertEqual(partial["decision"]["status"], "verify")
        self.assertTrue(any("保底" in risk["text"] for risk in partial["risks"]))

    def test_all_six_experience_groups_exist_with_unknowns(self) -> None:
        self._job()
        groups = self._cards()[0]["experience"]
        self.assertEqual([group["key"] for group in groups], ["time", "pace", "responsibility", "culture", "growth", "stability"])
        self.assertTrue(all(group["unknowns"] for group in groups))
        self.assertEqual(groups[0]["status"], "unknown")

    def test_same_team_evidence_is_linked_but_unaligned_team_is_context(self) -> None:
        self._job()
        _, direct_chunk = self._evidence("团队实际双休，不加班，平均18点下班。")
        _, context_chunk = self._evidence("经常加班，晚上22点下班。", business_unit="")
        card = self._cards()[0]
        evidence = {item["id"]: item for item in card["evidence"]}
        self.assertEqual(evidence[f"community:{direct_chunk}"]["relevance"], "direct")
        self.assertEqual(evidence[f"community:{context_chunk}"]["relevance"], "context")
        time = card["experience"][0]
        self.assertTrue(any(f"community:{direct_chunk}" in fact["evidence_ids"] for fact in time["facts"]))
        self.assertFalse(any(f"community:{context_chunk}" in fact["evidence_ids"] for group in card["experience"] for fact in group["facts"]))
        self.assertFalse(any(f"community:{context_chunk}" in reason["evidence_ids"] for reason in card["reasons"]))

    def test_other_company_city_employment_old_or_nonaccepted_evidence_is_excluded(self) -> None:
        self._job()
        values = [self._evidence("经常加班，晚上22点下班。", company="阿里"),
                  self._evidence("长期加班，晚上23点下班。", employment="internship"),
                  self._evidence("周末加班，晚上21点下班。", city="上海"),
                  self._evidence("996制度，22点下班。", days_ago=900),
                  self._evidence("大小周制度，21点下班。", status=PolicyStatus.REJECTED),
                  self._evidence("平均20点下班。", business_unit="游戏团队"),
                  self._evidence("平均19点下班。", company="腾讯音乐")]
        ids = {item["id"] for item in self._cards()[0]["evidence"]}
        self.assertFalse(any(f"community:{chunk_id}" in ids for _, chunk_id in values))

    def test_deleted_chunk_does_not_survive_a_cached_retrieval_snapshot(self) -> None:
        job_id = self._job()
        document_id, chunk_id = self._evidence("实际双休，18点下班。")
        with self.database.connect() as connection:
            connection.execute("INSERT INTO knowledge_retrieval_runs(job_id,company,role_family,employment_type,query_json,evidence_json,retrieved_at) VALUES(?,?,?,?,?,?,?)",
                               (job_id, "腾讯", "data", "full_time", "{}", json.dumps({"need": [{"chunk_id": chunk_id, "text": "实际双休"}]}), datetime.now(timezone.utc).isoformat()))
            connection.execute("DELETE FROM knowledge_documents WHERE id=?", (document_id,))
        self.assertFalse(any(item["type"] == "community" for item in self._cards()[0]["evidence"]))

    def test_stock_algorithm_and_interview_travel_are_not_compensation_or_time_facts(self) -> None:
        self._job(description="面试股票算法题，主管出差导致复试间隔。负责数据分析。")
        self._evidence("面试股票算法题，主管出差导致复试间隔。", topic="compensation")
        card = self._cards()[0]
        equity = next(field for field in card["compensation"]["fields"] if field["key"] == "equity")
        self.assertEqual(equity["status"], "unknown")
        self.assertEqual(card["experience"][0]["facts"], [])
        self.assertEqual(card["evidence_summary"]["documents"], 0)

    def test_negation_and_conflicting_workload_never_count_as_low_intensity_support(self) -> None:
        self.config.preferences.workload_preference = "low_intensity"
        for index, text in enumerate(["不双休，实行996", "双休，但经常加班", "不保证双休，实行大小周"]):
            self._job(source_id=f"negated-{index}", title=f"数据分析师{index}", description="负责数据分析，熟悉Python、SQL。" + text)
        for card in self._cards():
            self.assertEqual(card["decision"]["status"], "verify")
            self.assertFalse(any("符合你偏好的较低强度" in reason["text"] for reason in card["reasons"]))
            self.assertTrue(any("强度" in risk["text"] or "冲突" in risk["text"] for risk in card["risks"]))

    def test_negated_growth_is_a_gap_not_a_recommendation_reason(self) -> None:
        self.config.preferences.growth_priority = "high"
        self._job(description="负责数据分析，熟悉Python、SQL。双休，不加班。不提供导师，也没有培训。")
        card = self._cards()[0]
        self.assertEqual(card["decision"]["status"], "verify")
        self.assertFalse(any("支持你的成长" in reason["text"] for reason in card["reasons"]))
        self.assertTrue(any("缺少导师" in risk["text"] for risk in card["risks"]))

    def test_postposed_growth_negation_requires_verification_without_positive_support(self) -> None:
        self.config.preferences.growth_priority = "high"
        for index, text in enumerate(["导师制度已取消。培训项目已取消。", "导师制度未提供。培训项目不存在。", "导师制度暂停。培训项目取消。"]):
            self._job(source_id=f"postposed-{index}", title=f"数据分析师{index}",
                      description="使用Python、SQL。双休，不加班。" + text)
        for card in self._cards():
            self.assertEqual(card["decision"]["status"], "verify")
            self.assertFalse(any("支持你的成长" in reason["text"] for reason in card["reasons"]))
            self.assertTrue(any("缺少导师" in risk["text"] for risk in card["risks"]))

    def test_interview_topic_and_intention_stage_do_not_supply_work_time_evidence(self) -> None:
        self._job()
        self._evidence("意向面约在周末，主管出差，延期一周", topic="interview")
        self._evidence("主管面原定周末，因出差取消", topic="workload")
        card = self._cards()[0]
        self.assertEqual(card["experience"][0]["facts"], [])
        self.assertEqual(card["evidence_summary"]["experience_direct"], 0)

    def test_cross_source_workload_conflict_requires_verification(self) -> None:
        self._job(description="负责数据分析，熟悉Python、SQL。实行双休，不加班。")
        self._evidence("实际上经常加班，周末加班频繁。")
        card = self._cards()[0]
        self.assertEqual(card["decision"]["status"], "verify")
        self.assertTrue(any("证据有冲突" in risk["text"] for risk in card["risks"]))

    def test_scoped_sample_is_not_crowded_out_by_twelve_background_chunks(self) -> None:
        self._job()
        for index in range(12):
            self._evidence(f"背景样本{index}：双休，18点下班。", business_unit="")
        _, direct_id = self._evidence("唯一同团队样本：经常加班，21点下班。")
        with self.database.connect() as connection:
            connection.execute("UPDATE knowledge_documents SET quality_score=0.5 WHERE business_unit='数据平台'")
        card = self._cards()[0]
        self.assertTrue(any(f"community:{direct_id}" in fact["evidence_ids"] for fact in card["experience"][0]["facts"]))
        self.assertEqual(card["evidence_summary"]["experience_direct"], 1)

    def test_conflict_after_three_display_facts_is_still_checked(self) -> None:
        self.config.preferences.workload_preference = "low_intensity"
        self._job(description="负责数据分析，熟悉Python、SQL。双休。不加班。每周40小时。经常加班，实行996。")
        card = self._cards()[0]
        self.assertLessEqual(len(card["experience"][0]["facts"]), 3)
        self.assertEqual(card["decision"]["status"], "verify")
        self.assertTrue(any("证据有冲突" in risk["text"] for risk in card["risks"]))

    def test_duplicate_and_expired_jobs_are_hidden_by_default(self) -> None:
        identifiers = [self._job(source_id=str(index), title=f"数据分析师{index}") for index in range(2)]
        for identifier, status in zip(identifiers, [JobStatus.DUPLICATE, JobStatus.EXPIRED]):
            self.database.set_job_status(identifier, status)
        self.assertTrue(all(not card["default_visible"] for card in self._cards()))
        self.assertTrue(all(card["decision"]["status"] == "not_recommended" for card in self._cards()))

    def test_past_rejected_status_is_rechecked_against_current_profile(self) -> None:
        identifier = self._job(education="硕士及以上")
        self.database.set_job_status(identifier, JobStatus.REJECTED)
        self.assertFalse(self._cards()[0]["default_visible"])
        self.config.candidate.education = "硕士"
        card = self._cards()[0]
        self.assertTrue(card["default_visible"])
        self.assertEqual(card["eligibility"]["status"], "eligible")

    def test_order_respects_eligibility_before_evidence_and_ignores_company_prestige(self) -> None:
        eligible = self._job(company="普通公司")
        blocked = self._job(source_id="blocked", company="腾讯", education="博士")
        self._evidence("双休，不加班，导师培训。")
        self.config.preferences.company_tiers = {"优先": ["腾讯"]}
        cards = self._cards()
        self.assertEqual(cards[0]["job_id"], eligible)
        self.assertEqual(cards[-1]["job_id"], blocked)

    def test_read_only_api_does_not_initialize_missing_database_or_write_evidence(self) -> None:
        self._job()
        self._evidence("双休，不加班，18点下班。")
        with self.database.connect() as connection:
            before = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for table in ("events", "evaluations", "knowledge_retrieval_runs", "evaluation_evidence")}
        config_path = self.directory / "config.json"
        save_config(self.config, config_path)
        service = AgentService(config_path, self.database_path)
        handler = type("RecommendationHandler", (ApiHandler,), {"service": service})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            client.request("GET", "/api/recommendations")
            response = client.getresponse()
            payload = json.loads(response.read())
            client.close()
            self.assertEqual(len(payload["items"]), 1)
            self.assertTrue(payload["policy"]["read_only"])
            self.assertFalse(payload["policy"]["paid_model_called"])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
        with self.database.connect() as connection:
            after = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in before}
        self.assertEqual(before, after)
        missing = self.directory / "missing.sqlite3"
        self.assertEqual(build_recommendations(missing, self.config)["items"], [])
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
