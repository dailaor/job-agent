from __future__ import annotations

import unittest

from job_agent.config import AgentConfig, Preferences
from job_agent.matching import evaluate_job, strategy_allocation
from job_agent.models import Candidate, Job, Strategy


def config() -> AgentConfig:
    return AgentConfig(
        candidate=Candidate("测试用户", years_experience=3, education="本科", skills=["SQL", "Python", "数据分析", "需求分析"]),
        preferences=Preferences(
            target_titles=["产品经理", "数据产品"], locations=["北京", "上海"],
            excluded_keywords=["销售", "外包"], company_tiers={"优先": ["大厂"], "可接受": [], "不投": []},
        ),
        greetings={"default": "您好，我关注{company}的{title}"},
    )


class MatchingTests(unittest.TestCase):
    def test_extended_hard_rules_reject_known_mismatches(self) -> None:
        candidate_config = config()
        candidate_config.preferences.employment_types = ["全职"]
        candidate_config.preferences.work_modes = ["远程"]
        candidate_config.preferences.minimum_salary = 20_000
        job = Job(
            id=9,
            source="official:test",
            source_id="9",
            title="数据产品经理（实习）",
            company="普通公司",
            location="北京现场",
            url="https://careers.example.com/9",
            salary_max=15_000,
            metadata={"employment_type": "实习", "work_mode": "现场"},
        )
        result = evaluate_job(job, candidate_config)
        self.assertIn("职位类型不符合要求", result.hard_reasons)
        self.assertIn("办公方式不符合要求", result.hard_reasons)
        self.assertIn("薪资上限低于最低期望", result.hard_reasons)

    def test_unknown_policy_can_reject_missing_job_fields(self) -> None:
        candidate_config = config()
        candidate_config.preferences.employment_types = ["全职"]
        candidate_config.preferences.minimum_salary = 10_000
        candidate_config.preferences.unknown_field_policy = "reject"
        job = Job(
            id=10,
            source="official:test",
            source_id="10",
            title="数据产品经理",
            company="普通公司",
            location="北京",
            url="https://careers.example.com/10",
        )
        result = evaluate_job(job, candidate_config)
        self.assertIn("职位类型未披露", result.hard_reasons)
        self.assertIn("薪资未披露", result.hard_reasons)

    def test_configured_experience_gap_is_the_single_hard_threshold(self) -> None:
        candidate_config = config()
        candidate_config.preferences.max_experience_gap = 4
        job = Job(
            id=11,
            source="official:test",
            source_id="11",
            title="数据产品经理",
            company="普通公司",
            location="北京",
            url="https://careers.example.com/11",
            experience_min=6,
            metadata={"required_skills": ["SQL", "Python", "数据分析", "需求分析"]},
        )
        result = evaluate_job(job, candidate_config)
        self.assertTrue(result.hard_pass)
        self.assertEqual(result.strategy, Strategy.STRETCH)

    def test_strategy_is_ability_relation_not_company_tier(self) -> None:
        job = Job(
            id=1, source="boss", source_id="1", title="数据产品经理", company="普通公司", location="北京",
            url="https://www.zhipin.com/job_detail/1.html", experience_min=3, experience_max=4,
            metadata={"required_skills": ["SQL", "Python", "数据分析", "需求分析"], "detail_loaded": True},
        )
        first = evaluate_job(job, config())
        self.assertEqual(first.strategy, Strategy.MATCH)
        changed = config()
        changed.preferences.company_tiers["优先"] = ["普通公司"]
        second = evaluate_job(job, changed)
        self.assertEqual(second.strategy, Strategy.MATCH)
        self.assertGreater(second.company_score, first.company_score)

    def test_strategy_mode_changes_two_direction_score_weights(self) -> None:
        job = Job(
            id=12, source="official:test", source_id="12", title="数据产品经理",
            company="普通公司", location="北京", url="https://careers.example.com/12",
            experience_min=3, experience_max=4,
            metadata={"required_skills": ["SQL", "Python", "数据分析", "需求分析"]},
        )
        stretch_config = config()
        stretch_config.preferences.strategy_mode = "stretch"
        safe_config = config()
        safe_config.preferences.strategy_mode = "safe"
        stretch = evaluate_job(job, stretch_config)
        safe = evaluate_job(job, safe_config)
        self.assertEqual(stretch.match_score, safe.match_score)
        self.assertEqual(stretch.need_score, safe.need_score)
        self.assertGreater(stretch.match_score, stretch.need_score)
        self.assertGreater(safe.overall_score, stretch.overall_score)

    def test_hard_rule_becomes_skip(self) -> None:
        job = Job(
            id=2, source="boss", source_id="2", title="销售产品经理", company="公司", location="北京",
            url="https://www.zhipin.com/job_detail/2.html", metadata={"required_skills": ["SQL"]},
        )
        result = evaluate_job(job, config())
        self.assertEqual(result.strategy, Strategy.SKIP)
        self.assertIn("命中排除关键词", result.hard_reasons)

    def test_allocation_preserves_limit(self) -> None:
        result = strategy_allocation(7, {"冲高": 0.25, "持平": 0.5, "保底": 0.25})
        self.assertEqual(sum(result.values()), 7)
        self.assertGreaterEqual(result["持平"], result["冲高"])


if __name__ == "__main__":
    unittest.main()
