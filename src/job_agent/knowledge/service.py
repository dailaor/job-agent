from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..config import AgentConfig, KnowledgeSettings
from ..database import Database
from ..models import Job
from .chunking import PostChunker
from .embeddings import EmbeddingProvider, HashingEmbeddingProvider
from .models import PolicyDecision, PolicyStatus, PostDocument, SourceStatus
from .policy import DocumentPolicy
from .retrieval import KnowledgeRetriever
from .sources import NowcoderPublicSource, SourceRegistry, XiaohongshuBrowserSource
from .store import KnowledgeStore


class KnowledgeService:
    def __init__(
        self,
        settings: KnowledgeSettings,
        database: Database,
        *,
        source_registry: SourceRegistry | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        chunker: PostChunker | None = None,
    ) -> None:
        self.settings = settings
        self.store = KnowledgeStore(database)
        self.policy = DocumentPolicy(settings)
        self.chunker = chunker or PostChunker()
        self.embedding_provider = embedding_provider or HashingEmbeddingProvider(settings.embedding_dimensions)
        self.retriever = KnowledgeRetriever(
            self.store, self.policy, self.embedding_provider, settings,
        )
        self.sources = source_registry or SourceRegistry([
            NowcoderPublicSource(settings.public_fetch_min_interval_seconds),
            XiaohongshuBrowserSource(),
        ])

    @staticmethod
    def _source_status(collection_method: str) -> SourceStatus:
        if collection_method == "browser_visible":
            return SourceStatus.BROWSER_FETCHED
        if collection_method == "public_html":
            return SourceStatus.PUBLIC_FETCHED
        return SourceStatus.IMPORTED

    def import_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        collection_method = str(payload.get("collection_method") or "manual_import")
        document = PostDocument(
            source=str(payload["source"]),
            url=str(payload["url"]),
            title=str(payload["title"]),
            content=str(payload["content"]),
            published_at=str(payload["published_at"]) if payload.get("published_at") else None,
            company=str(payload.get("company") or ""),
            role_family=str(payload.get("role_family") or ""),
            business_unit=str(payload.get("business_unit") or ""),
            city=str(payload.get("city") or ""),
            seniority=str(payload.get("seniority") or ""),
            employment_type=str(payload.get("employment_type") or "unknown"),
            author=str(payload.get("author") or ""),
            collection_method=collection_method,
            source_status=self._source_status(collection_method),
            metadata=dict(payload.get("metadata") or {}),
        )
        return self.import_document(document, approve_review=payload.get("approve_review") is True)

    def import_document(self, document: PostDocument, *, approve_review: bool = False) -> dict[str, Any]:
        decision = self.policy.evaluate(document)
        if approve_review and decision.status is PolicyStatus.NEEDS_REVIEW:
            decision = replace(
                decision,
                status=PolicyStatus.ACCEPTED,
                reasons=[*decision.reasons, "由用户明确批准缺失项后入库"],
                quality_score=max(0.6, decision.quality_score),
            )
        chunks = []
        if decision.indexable:
            chunks = self.chunker.split(
                document,
                content=decision.sanitized_content,
                company=decision.company,
                role_family=decision.role_family,
                employment_type=decision.employment_type,
            )
            if not chunks:
                decision = PolicyDecision(
                    status=PolicyStatus.NEEDS_REVIEW,
                    reasons=[*decision.reasons, "无法切出具有独立决策主题的证据块"],
                    company=decision.company,
                    role_family=decision.role_family,
                    employment_type=decision.employment_type,
                    topics=decision.topics,
                    quality_score=min(decision.quality_score, 0.59),
                    sanitized_content=decision.sanitized_content,
                )
        result = self.store.save_document(
            document, decision, retain_full_text=self.settings.retain_full_text,
        )
        if result["status"] == PolicyStatus.ACCEPTED.value:
            vectors = self.embedding_provider.embed([chunk.contextual_text for chunk in chunks])
            for chunk, embedding in zip(chunks, vectors, strict=True):
                chunk.embedding = embedding
            self.store.replace_chunks(
                int(result["document_id"]), chunks,
                embedding_provider=self.embedding_provider.name,
                embedding_dimensions=self.embedding_provider.dimensions,
            )
        return {
            **result,
            "company": decision.company,
            "role_family": decision.role_family,
            "employment_type": decision.employment_type.value,
            "topics": decision.topics,
            "quality_score": decision.quality_score,
            "chunks": len(chunks) if result["status"] == PolicyStatus.ACCEPTED.value else 0,
            "raw_text_retained": self.settings.retain_full_text,
        }

    def fetch_url(self, source: str, url: str) -> dict[str, Any]:
        if source not in self.settings.allowed_sources:
            raise ValueError(f"知识来源未启用：{source}")
        adapter = self.sources.get(source)
        if adapter is None:
            raise ValueError(f"未配置知识来源：{source}")
        result = adapter.fetch(url)
        payload = result.to_dict()
        if result.document:
            payload["import"] = self.import_document(result.document)
        return payload

    def list_documents(self) -> list[dict[str, Any]]:
        return self.store.list_documents()

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "sources": self.sources.catalog(),
            "embedding_provider": self.embedding_provider.name,
            "raw_text_retained": self.settings.retain_full_text,
            **self.store.stats(),
        }

    def delete_document(self, document_id: int) -> dict[str, Any]:
        deleted = self.store.delete_document(document_id)
        return {"deleted": deleted, "document_id": document_id}

    def retrieve_for_job(self, job: Job, config: AgentConfig):
        return self.retriever.retrieve_for_job(job, config)

    def evidence_for_job(self, job_id: int) -> dict[str, Any] | None:
        return self.store.latest_evidence(job_id)
