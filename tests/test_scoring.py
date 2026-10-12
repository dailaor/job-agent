from __future__ import annotations

import unittest

from job_agent.config import AgentConfig, Preferences, ScoringSettings, config_to_dict
from job_agent.knowledge.models import EvidenceBundle, RetrievedEvidence
from job_agent.models import Candidate, Job, Strategy
from job_agent.scoring import DeepSeekJudgeError, DeepSeekScoringPort


def _config() -> AgentConfig:
    return AgentConfig(
        candidate=Candidate(
            "测试", headline="AI产品经理", years_experience=2, education="本科",
            skills=["需求分析", "SQL", "数据分析"],
        ),
        preferences=Preferences(target_titles=["产品经理"], locations=["深圳"]),
        greetings={"default": "您好"},
        scoring=ScoringSettings(provider="deepseek"),
    )


def _job() -> Job:
    return Job(
        source="official:tencent", source_id="judge-1", title="AI产品经理", company="腾讯",
        location="深圳", url="https://join.qq.com/post/judge-1",
        description="负责大模型产品需求分析、SQL数据复盘和跨团队项目推进",
        metadata={"employment_type": "full_time", "required_skills": ["需求分析", "SQL", "项目推进"]},
        id=1,
    )


def _item(chunk_id: int, topic: str) -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=chunk_id, document_id=chunk_id, source="nowcoder",
        url=f"https://www.nowcoder.com/discuss/{chunk_id}", title="腾讯产品正职体验",
        company="腾讯", role_family="product", employment_type="full_time", business_unit="",
        published_at="2026-07-01T00:00:00+00:00", topic=topic,
        text="实际职责包括需求分析和数据复盘，版本期工作强度会上升。",
        score=0.8, quality_score=0.8, collection_method="browser_visible",
    )


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        job_id=1, company="腾讯", role_family="product", employment_type="full_time",
        ability=[_item(11, "duties")], need=[_item(21, "workload")],
        coverage={"confidence": "medium", "cross_employment_fallback": False},
    )


def _judge_result() -> dict[str, object]:
    return {
        "ability": {
            "relation": "基本持平",
            "matched_capabilities": ["需求分析", "SQL"],
            "missing_capabilities": ["项目推进"],
            "score": 76,
            "confidence": 0.82,
            "evidence_chunk_ids": [11],
        },
        "need": {
            "score": 62,
            "confidence": 0.65,
            "satisfied_needs": ["深圳"],
            "risks": ["版本期强度上升"],
            "evidence_chunk_ids": [21],
            "insufficient_evidence": False,
        },
        "recommended_strategy": "持平",
        "reason": "候选人覆盖核心分析能力，但项目推进仍需验证；地点匹配，版本期强度存在风险。",
        "abstain": False,
        "abstention_reason": "",
    }


class StubDeepSeekScoringPort(DeepSeekScoringPort):
    def __init__(self, result: dict[str, object]) -> None:
        super().__init__(ScoringSettings(provider="deepseek"), api_key="test-only")
        self.result = result
        self.requests = 0

    def _request(self, messages: list[dict[str, str]]) -> dict[str, object]:
        self.requests += 1
        self.last_messages = messages
        return self.result


class DeepSeekScoringTests(unittest.TestCase):
    def test_valid_grounded_json_becomes_two_axis_evaluation(self) -> None:
        scorer = StubDeepSeekScoringPort(_judge_result())
        evaluation = scorer.score(_job(), _config(), _bundle())
        self.assertEqual(evaluation.strategy, Strategy.MATCH)
        self.assertEqual(evaluation.match_score, 76)
        self.assertEqual(evaluation.need_score, 62)
        self.assertIn("ability=[11]", evaluation.reason)
        self.assertIn("need=[21]", evaluation.reason)
        self.assertEqual(scorer.last_diagnostics["ability_citations"], [11])
        self.assertEqual(scorer.last_diagnostics["need_citations"], [21])
        self.assertFalse(scorer.last_diagnostics["need_insufficient_evidence"])
        self.assertNotIn("test-only", "".join(item["content"] for item in scorer.last_messages))

    def test_reported_strategy_must_match_scores_and_relation(self) -> None:
        result = _judge_result()
        result["recommended_strategy"] = "冲高"
        with self.assertRaisesRegex(DeepSeekJudgeError, "strategy conflicts"):
            StubDeepSeekScoringPort(result).score(_job(), _config(), _bundle())

    def test_wrong_dimension_or_missing_citation_is_rejected(self) -> None:
        result = _judge_result()
        result["ability"]["evidence_chunk_ids"] = [21]  # type: ignore[index]
        with self.assertRaisesRegex(DeepSeekJudgeError, "wrong-dimension"):
            StubDeepSeekScoringPort(result).score(_job(), _config(), _bundle())

    def test_mixed_employment_bundle_is_rejected_before_api_call(self) -> None:
        bundle = _bundle()
        bundle.need[0].employment_type = "internship"
        scorer = StubDeepSeekScoringPort(_judge_result())
        with self.assertRaisesRegex(DeepSeekJudgeError, "mixes full-time and internship"):
            scorer.score(_job(), _config(), bundle)
        self.assertEqual(scorer.requests, 0)

    def test_hard_rejected_job_never_calls_model(self) -> None:
        config = _config()
        config.preferences.excluded_keywords = ["销售"]
        job = _job()
        job.title = "销售产品经理"
        scorer = StubDeepSeekScoringPort(_judge_result())
        evaluation = scorer.score(job, config, _bundle())
        self.assertEqual(evaluation.strategy, Strategy.SKIP)
        self.assertEqual(scorer.requests, 0)

    def test_config_serializes_only_environment_variable_name(self) -> None:
        config = _config()
        config.preferences.workload_preference = "low_intensity"
        config.preferences.role_boundary_preference = "clear"
        config.preferences.culture_preferences = ["导师反馈"]
        config.preferences.community_risk_avoidances = ["长期高强度"]
        serialized = config_to_dict(config)
        self.assertEqual(serialized["scoring"]["api_key_env"], "DEEPSEEK_API_KEY")
        self.assertNotIn("api_key", serialized["scoring"])
        self.assertEqual(serialized["preferences"]["workload_preference"], "low_intensity")
        self.assertEqual(serialized["preferences"]["culture_preferences"], ["导师反馈"])

    def test_community_preferences_are_locally_validated(self) -> None:
        config = _config()
        config.preferences.workload_preference = "always_overtime"
        with self.assertRaisesRegex(ValueError, "workload_preference"):
            config.validate()


if __name__ == "__main__":
    unittest.main()
