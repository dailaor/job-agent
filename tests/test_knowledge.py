from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_agent.config import AgentConfig, KnowledgeSettings, Preferences, config_from_dict, save_config
from job_agent.database import Database
from job_agent.knowledge.chunking import PostChunker
from job_agent.knowledge.models import PolicyStatus, PostDocument, SourceStatus
from job_agent.knowledge.policy import DocumentPolicy
from job_agent.knowledge.service import KnowledgeService
from job_agent.knowledge.sources.nowcoder import NowcoderPublicSource
from job_agent.knowledge.sources.xiaohongshu import XiaohongshuBrowserSource
from job_agent.knowledge.store import KnowledgeStore
from job_agent.models import Candidate, Job
from job_agent.service import AgentService


NOW = datetime.now(timezone.utc).isoformat()


def _settings() -> KnowledgeSettings:
    return KnowledgeSettings(min_document_chars=40, max_age_days=1000, public_fetch_min_interval_seconds=1)


def _content() -> str:
    return (
        "我在腾讯做AI产品实习，日常负责大模型功能需求、数据分析和项目推进，也需要使用SQL验证效果。"
        "面试会重点考察需求分析、实验设计和对模型能力边界的理解。"
        "团队通常晚上八点左右下班，工作强度会随版本发布上升，但导师沟通比较充分。"
    )


class KnowledgePolicyTests(unittest.TestCase):
    def test_legacy_config_gets_safe_knowledge_defaults(self) -> None:
        config = config_from_dict({
            "candidate": {"name": "测试"},
            "preferences": {},
            "greetings": {"default": "您好"},
        })
        self.assertTrue(config.knowledge.enabled)
        self.assertIn("美团", config.knowledge.company_aliases)
        self.assertIn("product", config.knowledge.role_families)

    def test_useful_scoped_post_is_accepted(self) -> None:
        document = PostDocument(
            source="nowcoder", url="https://www.nowcoder.com/discuss/100", title="腾讯AI产品实习复盘",
            content=_content(), published_at=NOW, collection_method="public_html",
        )
        decision = DocumentPolicy(_settings()).evaluate(document)
        self.assertEqual(decision.status, PolicyStatus.ACCEPTED)
        self.assertEqual(decision.company, "腾讯")
        self.assertEqual(decision.role_family, "product")
        self.assertIn("duties", decision.topics)
        self.assertIn("interview", decision.topics)

    def test_common_chinese_role_abbreviation_is_scoped(self) -> None:
        document = PostDocument(
            source="nowcoder", url="https://www.nowcoder.com/discuss/data-role",
            title="美团校招数分岗面经", content=(
                "面试主要考察数据清洗、SQL和业务分析，项目部分会追问数据来源和指标异常排查。"
                "实际职责包括搭建看板、分析订单波动并向运营团队解释结论。"
            ),
            published_at=NOW, collection_method="public_html",
        )
        decision = DocumentPolicy(_settings()).evaluate(document)
        self.assertEqual(decision.role_family, "data")
        self.assertEqual(decision.status, PolicyStatus.ACCEPTED)

    def test_missing_date_requires_review_and_shell_is_rejected(self) -> None:
        policy = DocumentPolicy(_settings())
        review = policy.evaluate(PostDocument(
            source="xiaohongshu", url="https://www.xiaohongshu.com/explore/a", title="腾讯产品体验",
            content=_content(), collection_method="browser_visible",
        ))
        self.assertEqual(review.status, PolicyStatus.NEEDS_REVIEW)
        rejected = policy.evaluate(PostDocument(
            source="xiaohongshu", url="https://www.xiaohongshu.com/explore/b", title="腾讯产品体验",
            content="登录探索更多内容 加载中，请稍候" * 8, published_at=NOW,
            collection_method="browser_visible",
        ))
        self.assertEqual(rejected.status, PolicyStatus.REJECTED)

    def test_employment_type_must_be_unique_or_explicit(self) -> None:
        mixed = PostDocument(
            source="nowcoder", url="https://www.nowcoder.com/discuss/mixed-employment",
            title="腾讯产品经理实习转正记录", published_at=NOW, collection_method="public_html",
            content=(
                "我先做产品实习，日常负责需求分析和数据复盘，后来转为全职正式员工。"
                "正职阶段负责跨团队项目和版本规划，两个阶段的工作强度与考核方式不同。"
            ),
        )
        rejected = DocumentPolicy(_settings()).evaluate(mixed)
        self.assertEqual(rejected.status, PolicyStatus.REJECTED)
        self.assertIn("无法唯一确认是正职还是实习，禁止混入向量索引", rejected.reasons)
        mixed.employment_type = "internship"
        accepted = DocumentPolicy(_settings()).evaluate(mixed)
        self.assertEqual(accepted.status, PolicyStatus.ACCEPTED)
        self.assertEqual(accepted.employment_type.value, "internship")

    def test_chunking_keeps_one_post_parent_and_contextual_children(self) -> None:
        document = PostDocument(
            source="nowcoder", url="https://www.nowcoder.com/discuss/101", title="腾讯AI产品",
            content=_content(), published_at=NOW, business_unit="腾讯云", employment_type="internship",
            collection_method="public_html",
        )
        chunks = PostChunker(min_chars=20).split(
            document, content=document.content, company="腾讯", role_family="product",
        )
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all("公司=腾讯" in chunk.contextual_text for chunk in chunks))
        self.assertTrue(all("用工类型=internship" in chunk.contextual_text for chunk in chunks))
        self.assertTrue(all(chunk.end_offset > chunk.start_offset for chunk in chunks))

    def test_interview_stage_aliases_keep_scheduling_context_in_interview_topic(self) -> None:
        document = PostDocument(
            source="nowcoder", url="https://www.nowcoder.com/discuss/interview-stages",
            title="腾讯产品经理招聘流程", published_at=NOW, collection_method="browser_visible",
            content=(
                "电话业务与意向面约十分钟；初试重点深挖业务、项目和实习经历；"
                "主管复试以业务交流为主；HR 面交流经历与项目；主管出差导致复试间隔较长。"
            ),
        )
        chunks = PostChunker(min_chars=20).split(
            document, content=document.content, company="腾讯", role_family="product",
        )
        self.assertGreater(len(chunks), 0)
        self.assertTrue(all(chunk.topic == "interview" for chunk in chunks))


class KnowledgeStoreAndRetrievalTests(unittest.TestCase):
    def test_existing_knowledge_database_adds_employment_type_before_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "agent.sqlite3")
            with database.connect() as connection:
                connection.executescript("""
                    CREATE TABLE knowledge_documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL, source_url TEXT NOT NULL, url_hash TEXT NOT NULL,
                        title TEXT NOT NULL, company TEXT NOT NULL DEFAULT '',
                        role_family TEXT NOT NULL DEFAULT '', business_unit TEXT NOT NULL DEFAULT '',
                        city TEXT NOT NULL DEFAULT '', seniority TEXT NOT NULL DEFAULT '', published_at TEXT,
                        collected_at TEXT NOT NULL, collection_method TEXT NOT NULL, source_status TEXT NOT NULL,
                        policy_status TEXT NOT NULL, policy_reasons_json TEXT NOT NULL, topics_json TEXT NOT NULL,
                        quality_score REAL NOT NULL, content_hash TEXT NOT NULL, content_text TEXT NOT NULL DEFAULT '',
                        author_hash TEXT NOT NULL DEFAULT '', duplicate_of_document_id INTEGER,
                        metadata_json TEXT NOT NULL DEFAULT '{}', UNIQUE(source, url_hash)
                    );
                    CREATE TABLE knowledge_retrieval_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL,
                        company TEXT NOT NULL, role_family TEXT NOT NULL, query_json TEXT NOT NULL,
                        evidence_json TEXT NOT NULL, retrieved_at TEXT NOT NULL
                    );
                """)
                connection.execute(
                    """INSERT INTO knowledge_documents(
                       source, source_url, url_hash, title, company, role_family, seniority,
                       collected_at, collection_method, source_status, policy_status, policy_reasons_json,
                       topics_json, quality_score, content_hash
                       ) VALUES ('nowcoder','https://www.nowcoder.com/discuss/old','old','腾讯产品实习复盘',
                       '腾讯','product','实习','2026-01-01','manual_import','imported','accepted','[]','[]',0.8,'old')"""
                )
            KnowledgeStore(database)
            with database.connect() as connection:
                document_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(knowledge_documents)")
                }
                retrieval_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(knowledge_retrieval_runs)")
                }
                migrated = connection.execute(
                    "SELECT employment_type FROM knowledge_documents WHERE url_hash='old'"
                ).fetchone()
            self.assertIn("employment_type", document_columns)
            self.assertIn("employment_type", retrieval_columns)
            self.assertEqual(migrated["employment_type"], "internship")

    def test_embedding_provider_can_be_injected_without_changing_store_or_service(self) -> None:
        class TestEmbeddingProvider:
            name = "test-embedding-v1"
            dimensions = 64

            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[1.0, *([0.0] * 63)] for _ in texts]

        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "agent.sqlite3")
            service = KnowledgeService(_settings(), database, embedding_provider=TestEmbeddingProvider())
            result = service.import_payload({
                "source": "nowcoder", "url": "https://www.nowcoder.com/discuss/provider",
                "title": "腾讯AI产品实习复盘", "content": _content(), "published_at": NOW,
                "collection_method": "public_html",
            })
            self.assertEqual(result["status"], "accepted")
            with database.connect() as connection:
                row = connection.execute(
                    "SELECT embedding_provider, embedding_dimensions FROM knowledge_chunks LIMIT 1"
                ).fetchone()
            self.assertEqual(row["embedding_provider"], "test-embedding-v1")
            self.assertEqual(row["embedding_dimensions"], 64)

    def test_rejected_copy_does_not_block_later_valid_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = KnowledgeService(_settings(), Database(Path(directory) / "agent.sqlite3"))
            invalid = service.import_payload({
                "source": "nowcoder", "url": "https://www.xiaohongshu.com/explore/wrong-host",
                "title": "腾讯AI产品实习复盘", "content": _content(), "published_at": NOW,
                "collection_method": "public_html",
            })
            self.assertEqual(invalid["status"], "rejected")
            valid = service.import_payload({
                "source": "xiaohongshu", "url": "https://www.xiaohongshu.com/explore/valid-copy",
                "title": "腾讯AI产品实习复盘", "content": _content(), "published_at": NOW,
                "collection_method": "browser_visible",
            })
            self.assertEqual(valid["status"], "accepted")

    def test_import_deduplicates_and_does_not_retain_full_text_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "agent.sqlite3")
            service = KnowledgeService(_settings(), database)
            payload = {
                "source": "nowcoder", "url": "https://www.nowcoder.com/discuss/102",
                "title": "腾讯AI产品实习复盘", "content": _content(), "published_at": NOW,
                "collection_method": "public_html",
            }
            first = service.import_payload(payload)
            self.assertEqual(first["status"], "accepted")
            self.assertGreater(first["chunks"], 0)
            with database.connect() as connection:
                row = connection.execute(
                    "SELECT content_text FROM knowledge_documents WHERE id=?", (first["document_id"],)
                ).fetchone()
            self.assertEqual(row["content_text"], "")
            duplicate = service.import_payload({
                **payload,
                "source": "xiaohongshu",
                "url": "https://www.xiaohongshu.com/explore/cross-post",
                "collection_method": "browser_visible",
            })
            self.assertEqual(duplicate["status"], "duplicate")
            self.assertEqual(duplicate["chunks"], 0)

    def test_retrieval_separates_ability_and_need_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "agent.sqlite3")
            settings = _settings()
            service = KnowledgeService(settings, database)
            posts = [
                {
                    "source": "nowcoder", "url": "https://www.nowcoder.com/discuss/201",
                    "title": "腾讯AI产品面经", "published_at": NOW, "collection_method": "public_html",
                    "employment_type": "full_time",
                    "content": (
                        "我面试腾讯AI产品经理时被连续追问SQL、实验设计和大模型评测方法。"
                        "入职后实际职责包括需求分析、模型效果复盘和跨团队项目推进。"
                    ),
                },
                {
                    "source": "xiaohongshu", "url": "https://www.xiaohongshu.com/explore/202",
                    "title": "腾讯AI产品工作体验", "published_at": NOW, "collection_method": "browser_visible",
                    "employment_type": "full_time",
                    "content": (
                        "我在腾讯AI产品团队工作期间通常晚上八点下班，版本发布前工作强度会明显上升。"
                        "团队氛围总体直接，导师会固定沟通，办公地点在深圳。"
                    ),
                },
                {
                    "source": "xiaohongshu", "url": "https://www.xiaohongshu.com/explore/203",
                    "title": "腾讯产品成长记录", "published_at": NOW, "collection_method": "browser_visible",
                    "role_family": "product",
                    "employment_type": "full_time",
                    "content": (
                        "腾讯产品岗位的导师制度提供了较多学习机会，转岗需要结合业务团队的HC。"
                        "福利和补贴较稳定，但不同业务线的绩效节奏差异很大。"
                    ),
                },
            ]
            for post in posts:
                result = service.import_payload(post)
                self.assertEqual(result["status"], "accepted")
            job = Job(
                source="official:tencent", source_id="rag-1", title="AI产品经理",
                company="腾讯科技", location="深圳", url="https://join.qq.com/post/rag-1",
                description="负责大模型产品需求、效果评测、数据分析和跨团队项目推进",
                metadata={"employment_type": "full_time"},
            )
            job.id = database.upsert_job(job)[0]
            config = AgentConfig(
                candidate=Candidate("测试", skills=["SQL", "需求分析", "数据分析"]),
                preferences=Preferences(target_titles=["产品经理"], locations=["深圳"]),
                greetings={"default": "您好"}, knowledge=settings,
            )
            bundle = service.retrieve_for_job(job, config)
            self.assertGreater(len(bundle.ability), 0)
            self.assertGreater(len(bundle.need), 0)
            self.assertTrue({item.topic for item in bundle.ability}.issubset({"duties", "skills", "interview"}))
            self.assertTrue({item.topic for item in bundle.need}.issubset({
                "workload", "compensation", "culture", "growth", "stability", "work_style",
            }))
            self.assertTrue(bundle.coverage["community_evidence_must_not_override_hard_rules"])
            document_id = bundle.ability[0].document_id
            self.assertTrue(service.delete_document(document_id)["deleted"])
            self.assertIsNone(service.evidence_for_job(job.id))

    def test_retrieval_never_crosses_full_time_and_internship(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "agent.sqlite3")
            settings = _settings()
            service = KnowledgeService(settings, database)
            base = {
                "source": "nowcoder", "published_at": NOW, "collection_method": "public_html",
                "company": "腾讯", "role_family": "product",
            }
            full_time = service.import_payload({
                **base,
                "url": "https://www.nowcoder.com/discuss/full-time-only",
                "title": "腾讯产品经理正职体验",
                "employment_type": "full_time",
                "content": (
                    "我在正职产品岗位负责需求分析、版本规划和SQL数据复盘。"
                    "团队在发布周期常到晚上八点下班，绩效和晋升按正式员工机制执行。"
                ),
            })
            internship = service.import_payload({
                **base,
                "url": "https://www.nowcoder.com/discuss/internship-only",
                "title": "腾讯产品实习体验",
                "employment_type": "internship",
                "content": (
                    "我在产品实习期间负责竞品分析、需求文档和基础数据复盘。"
                    "导师每周沟通一次，实习转正取决于业务线HC，通常晚上七点下班。"
                ),
            })
            self.assertEqual(full_time["status"], "accepted")
            self.assertEqual(internship["status"], "accepted")
            config = AgentConfig(
                candidate=Candidate("测试", skills=["SQL", "需求分析"]),
                preferences=Preferences(target_titles=["产品经理"]),
                greetings={"default": "您好"}, knowledge=settings,
            )
            jobs = [
                Job(
                    source="official:tencent", source_id="full", title="产品经理", company="腾讯",
                    location="深圳", url="https://join.qq.com/post/full", description="负责需求分析和版本规划",
                    metadata={"employment_type": "full_time"},
                ),
                Job(
                    source="official:tencent", source_id="intern", title="产品经理实习生", company="腾讯",
                    location="深圳", url="https://join.qq.com/post/intern", description="负责需求分析和数据复盘",
                    metadata={"employment_type": "internship"},
                ),
            ]
            for job in jobs:
                job.id = database.upsert_job(job)[0]
                bundle = service.retrieve_for_job(job, config)
                self.assertTrue(bundle.ability or bundle.need)
                self.assertTrue(all(
                    item.employment_type == job.metadata["employment_type"]
                    for item in [*bundle.ability, *bundle.need]
                ))
                self.assertFalse(bundle.coverage["cross_employment_fallback"])


class SourceAdapterTests(unittest.TestCase):
    def test_nowcoder_ssr_parser_extracts_one_public_post(self) -> None:
        state = {
            "prefetchData": {"2": {"ssrCommonData": {"contentData": {
                "id": "301", "title": "腾讯AI产品面经", "content": "<p>面试重点考察SQL和需求分析。</p>",
                "createTime": 1_750_000_000_000, "userBrief": {"nickname": "作者"},
            }}}}
        }
        html = f"<html><script>window.__INITIAL_STATE__ = {json.dumps(state, ensure_ascii=False)};(function(){{}})()</script></html>"
        document = NowcoderPublicSource.parse_html("https://www.nowcoder.com/discuss/301", html)
        self.assertEqual(document.title, "腾讯AI产品面经")
        self.assertIn("SQL", document.content)
        self.assertEqual(document.source_status, SourceStatus.PUBLIC_FETCHED)

    def test_xiaohongshu_direct_fetch_is_never_attempted(self) -> None:
        result = XiaohongshuBrowserSource().fetch("https://www.xiaohongshu.com/explore/abc")
        self.assertEqual(result.status, SourceStatus.AUTH_REQUIRED)
        self.assertIn("不执行直接爬取", result.message)


class KnowledgeApplicationBoundaryTests(unittest.TestCase):
    def test_direct_retrieval_endpoint_also_respects_hard_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            database_path = root / "agent.sqlite3"
            config = AgentConfig(
                candidate=Candidate("测试"),
                preferences=Preferences(target_titles=["产品经理"], excluded_keywords=["销售"]),
                greetings={"default": "您好"},
                knowledge=_settings(),
            )
            save_config(config, config_path)
            database = Database(database_path)
            job = Job(
                source="official:meituan", source_id="hard-reject", title="销售产品经理",
                company="美团", location="北京", url="https://zhaopin.meituan.com/job/hard-reject",
                description="负责销售业务",
            )
            job_id = database.upsert_job(job)[0]
            with self.assertRaisesRegex(ValueError, "未通过硬规则"):
                AgentService(config_path, database_path).retrieve_job_evidence(job_id)


if __name__ == "__main__":
    unittest.main()
