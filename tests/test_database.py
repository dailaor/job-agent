from __future__ import annotations

import tempfile
import unittest
import sqlite3
from pathlib import Path

from job_agent.database import Database
from job_agent.models import Job, JobStatus


class DatabaseTests(unittest.TestCase):
    def test_existing_database_gets_need_score_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agent.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute("""CREATE TABLE evaluations (
                    job_id INTEGER PRIMARY KEY, hard_pass INTEGER NOT NULL, strategy TEXT NOT NULL,
                    ability_relation TEXT NOT NULL, matched_json TEXT NOT NULL, missing_json TEXT NOT NULL,
                    hard_reasons_json TEXT NOT NULL, match_score REAL NOT NULL, company_score REAL NOT NULL,
                    overall_score REAL NOT NULL, confidence REAL NOT NULL, reason TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL
                )""")
                connection.commit()
            finally:
                connection.close()
            db = Database(path)
            with db.connect() as connection:
                columns = {row["name"] for row in connection.execute("PRAGMA table_info(evaluations)")}
            self.assertIn("need_score", columns)

    def test_cross_channel_priority_and_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "agent.sqlite3")
            boss = Job(source="boss", source_id="b1", title="产品经理", company="同一公司", location="北京", url="https://www.zhipin.com/job_detail/b1.html")
            official = Job(source="official:x", source_id="o1", title="产品经理", company="同一公司", location="北京", url="https://jobs.example.com/o1")
            boss_id, _ = db.upsert_job(boss)
            official_id, _ = db.upsert_job(official)
            db.resolve_fingerprint_priority(boss.fingerprint, ["official", "boss"])
            rows = {row["id"]: row for row in db.list_jobs()}
            self.assertEqual(rows[official_id]["status"], JobStatus.DISCOVERED.value)
            self.assertEqual(rows[boss_id]["status"], JobStatus.DUPLICATE.value)


if __name__ == "__main__":
    unittest.main()
