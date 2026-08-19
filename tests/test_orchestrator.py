from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from job_agent.config import AgentConfig, Preferences
from job_agent.connectors.registry import ChannelAdapter, ChannelRegistry
from job_agent.database import Database
from job_agent.models import Candidate, Job
from job_agent.orchestrator import JobAgent


class OrchestratorTests(unittest.TestCase):
    def test_demo_end_to_end_until_planned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = AgentConfig(
                candidate=Candidate("测试", years_experience=3, education="本科", skills=["SQL", "Python", "数据分析", "需求分析", "A/B测试"]),
                preferences=Preferences(
                    target_titles=["产品经理", "AI 产品", "数据产品"],
                    excluded_keywords=["销售", "保险", "培训", "外包"],
                    locations=["北京", "上海"],
                    company_tiers={"优先": ["示例大厂"], "可接受": ["示例成长公司"], "不投": []},
                    boss_daily_limit=1, official_daily_limit=10,
                ),
                greetings={"default": "您好，我关注{company}的{title}"},
            )
            agent = JobAgent(config, Database(Path(directory) / "agent.sqlite3"))
            seeded = agent.seed_demo()
            evaluated = agent.evaluate()
            boss_plan = agent.plan("boss")
            official_plan = agent.plan("official")
            self.assertEqual(seeded["records"], 4)
            self.assertEqual(evaluated["evaluated"], 4)
            self.assertGreaterEqual(evaluated["rejected"], 1)
            self.assertGreaterEqual(boss_plan["planned"], 1)
            self.assertGreaterEqual(official_plan["planned"], 1)
            self.assertEqual(agent.plan("boss")["planned"], 0)


class ChannelSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_all_degrades_to_manual_when_browser_runtime_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = AgentConfig(
                candidate=Candidate(
                    "测试", years_experience=3, education="本科",
                    skills=["SQL", "Python", "数据分析", "需求分析", "A/B测试"],
                ),
                preferences=Preferences(
                    target_titles=["产品经理", "AI 产品", "数据产品"],
                    excluded_keywords=["销售", "保险", "培训", "外包"],
                    locations=["北京", "上海"],
                ),
                greetings={"default": "您好"},
                boss={"enabled": False},
            )
            agent = JobAgent(config, Database(Path(directory) / "agent.sqlite3"))
            agent.seed_demo()
            agent.evaluate()
            self.assertEqual(agent.plan_all()["planned"], 3)
            result = await agent.execute_all(live=False)
            self.assertEqual(result["processed"], 3)
            self.assertTrue(all(
                item["status"] == "needs_human"
                for channel in result["channels"]
                for item in channel["results"]
            ))

    async def test_registered_channel_needs_no_orchestrator_branch(self) -> None:
        class FakeConnector:
            source = "custom:example"

            async def discover(self, keywords: list[str]) -> list[Job]:
                self.keywords = keywords
                return [Job(
                    source=self.source,
                    source_id="one",
                    title="产品经理",
                    company="示例公司",
                    location="杭州",
                    url="https://jobs.example.com/one",
                )]

            async def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as directory:
            config = AgentConfig(
                candidate=Candidate("测试"),
                preferences=Preferences(target_titles=["产品经理"]),
                greetings={"default": "您好"},
            )
            registry = ChannelRegistry([ChannelAdapter(
                id="custom:example",
                name="示例扩展渠道",
                channel_type="custom",
                enabled=True,
                keywords=["产品经理"],
                strategy="api",
                url="https://jobs.example.com",
                connector_factory=FakeConnector,
            )])
            agent = JobAgent(config, Database(Path(directory) / "agent.sqlite3"), registry)
            result = await agent.discover_selected(["custom:example"])
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["sources"][0]["status"], "api_fetched")
            self.assertEqual(len(agent.db.list_jobs()), 1)
            self.assertEqual(agent.evaluate()["eligible"], 1)
            plan = agent.plan("custom:example")
            self.assertEqual(plan["planned"], 1)
            execution = await agent.execute("custom:example", live=False)
            self.assertEqual(execution["results"][0]["status"], "needs_human")

    async def test_registered_channel_rejects_off_host_job_urls(self) -> None:
        class UnsafeConnector:
            async def discover(self, keywords: list[str]) -> list[Job]:
                return [Job(
                    source="custom:safe",
                    source_id="one",
                    title="产品经理",
                    company="示例公司",
                    location="杭州",
                    url="https://redirect.example.net/one",
                )]

            async def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as directory:
            config = AgentConfig(
                candidate=Candidate("测试"),
                preferences=Preferences(target_titles=["产品经理"]),
                greetings={"default": "您好"},
            )
            registry = ChannelRegistry([ChannelAdapter(
                id="custom:safe",
                name="安全示例",
                channel_type="custom",
                enabled=True,
                keywords=["产品经理"],
                strategy="api",
                url="https://jobs.example.com",
                connector_factory=UnsafeConnector,
            )])
            agent = JobAgent(config, Database(Path(directory) / "agent.sqlite3"), registry)
            result = await agent.discover_selected(["custom:safe"])
            self.assertEqual(result["completed"], 0)
            self.assertIn("HTTPS 白名单", result["sources"][0]["message"])
            self.assertEqual(agent.db.list_jobs(), [])

    async def test_no_enabled_channels_returns_actionable_explanation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = AgentConfig(
                candidate=Candidate("测试"),
                preferences=Preferences(target_titles=["产品经理"]),
                greetings={"default": "您好"},
                boss={"enabled": False},
                official_sites=[],
            )
            agent = JobAgent(config, Database(Path(directory) / "agent.sqlite3"))
            catalog = agent.channel_catalog()
            self.assertEqual(catalog[0]["id"], "boss")
            self.assertEqual(catalog[0]["health"], "disabled")
            result = await agent.discover_selected([])
            self.assertEqual(result["status"], "no_channels")
            self.assertIn("配置页面", result["message"])

    async def test_disabled_selected_channel_is_not_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = AgentConfig(
                candidate=Candidate("测试"),
                preferences=Preferences(target_titles=["产品经理"], boss_keywords=["产品经理"]),
                greetings={"default": "您好"},
                boss={"enabled": False},
            )
            agent = JobAgent(config, Database(Path(directory) / "agent.sqlite3"))
            result = await agent.discover_selected(["boss"])
            self.assertEqual(result["status"], "needs_configuration")
            self.assertEqual(result["sources"][0]["status"], "not_ready")


if __name__ == "__main__":
    unittest.main()
