from __future__ import annotations

import unittest

from job_agent.config import AgentConfig, Preferences
from job_agent.connectors.boss import build_search_url, normalize_boss_url
from job_agent.matching import evaluate_job
from job_agent.models import Candidate, Job, Strategy


class BossTests(unittest.TestCase):
    def test_correct_search_route(self) -> None:
        url = build_search_url("AI 产品经理", "101010100")
        self.assertIn("/web/geek/jobs?", url)
        self.assertNotIn("/web/geek/job?", url)

    def test_restricts_hosts(self) -> None:
        self.assertEqual(normalize_boss_url("/job_detail/a.html"), "https://www.zhipin.com/job_detail/a.html")
        with self.assertRaises(ValueError):
            normalize_boss_url("https://example.com/job_detail/a.html")

    def test_boss_shell_without_detail_is_not_actionable(self) -> None:
        config = AgentConfig(
            candidate=Candidate("测试", years_experience=2, skills=["SQL"]),
            preferences=Preferences(target_titles=["产品经理"], locations=["北京"]),
            greetings={"default": "您好"},
        )
        job = Job(
            id=1, source="boss", source_id="x", title="产品经理", company="公司", location="北京",
            url="https://www.zhipin.com/job_detail/x.html", metadata={"required_skills": ["SQL"]},
        )
        self.assertEqual(evaluate_job(job, config).strategy, Strategy.SKIP)


if __name__ == "__main__":
    unittest.main()
