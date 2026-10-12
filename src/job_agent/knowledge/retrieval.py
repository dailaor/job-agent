from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from ..config import AgentConfig, KnowledgeSettings
from ..models import Job
from .embeddings import EmbeddingProvider, cosine_similarity, tokenize
from .models import (
    EmploymentType, EvidenceBundle, PostDocument, RetrievedEvidence, normalize_employment_type,
)
from .policy import DocumentPolicy
from .store import KnowledgeStore


ABILITY_TOPICS = ["duties", "skills", "interview"]
NEED_TOPICS = ["workload", "compensation", "culture", "growth", "stability", "work_style"]


def _bm25_scores(query: str, rows: list[dict[str, Any]]) -> list[float]:
    query_terms = list(dict.fromkeys(tokenize(query)))
    documents = [tokenize(str(row["contextual_text"])) for row in rows]
    if not query_terms or not documents:
        return [0.0] * len(rows)
    average_length = sum(len(document) for document in documents) / max(1, len(documents))
    frequencies = Counter(term for term in query_terms for document in documents if term in set(document))
    k1, b = 1.5, 0.75
    scores: list[float] = []
    for document in documents:
        counts = Counter(document)
        score = 0.0
        for term in query_terms:
            document_frequency = frequencies[term]
            if not document_frequency or not counts[term]:
                continue
            inverse = math.log(1 + (len(documents) - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = counts[term] + k1 * (1 - b + b * len(document) / max(1, average_length))
            score += inverse * counts[term] * (k1 + 1) / denominator
        scores.append(score)
    maximum = max(scores, default=0.0)
    return [score / maximum for score in scores] if maximum else scores


def _recency_score(value: str | None) -> float:
    if not value:
        return 0.35
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.25
    parsed = parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
    age_days = max(0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).days)
    return max(0.05, math.exp(-age_days / 540))


class KnowledgeRetriever:
    def __init__(
        self,
        store: KnowledgeStore,
        policy: DocumentPolicy,
        embedding_provider: EmbeddingProvider,
        settings: KnowledgeSettings,
    ) -> None:
        self.store = store
        self.policy = policy
        self.embedding_provider = embedding_provider
        self.settings = settings

    def _job_scope(self, job: Job) -> tuple[str, str, EmploymentType, str]:
        company = self.policy.canonical_company(job.company)
        declared = normalize_employment_type(job.metadata.get("employment_type"))
        probe = PostDocument(
            source="manual",
            url=job.url,
            title=job.title,
            content=job.description or job.title,
            company=company,
            employment_type=declared,
        )
        detected = self.policy.detect_employment_type(probe)
        if declared is not EmploymentType.UNKNOWN:
            origin = "job_metadata"
        elif detected is not EmploymentType.UNKNOWN:
            origin = "job_text"
        else:
            # A persisted job without internship markers is treated as a regular full-time
            # posting. This default is explicit in coverage and never changes a knowledge document.
            detected = EmploymentType.FULL_TIME
            origin = "regular_job_default"
        return company, self.policy.detect_role_family(probe), detected, origin

    def _query(self, job: Job, config: AgentConfig, dimension: str) -> str:
        if dimension == "ability":
            skills = " ".join(config.candidate.skills)
            return f"{job.company} {job.title} {job.description[:1600]} {skills} 实际职责 技能要求 面试考察"
        preferences = config.preferences
        return " ".join([
            job.company, job.title, job.location,
            " ".join(preferences.locations), " ".join(preferences.work_modes),
            f"最低薪资 {preferences.minimum_salary or '未设置'}",
            "工作强度 薪资福利 团队氛围 成长稳定性 办公方式",
        ])

    def _rank(
        self,
        *,
        query: str,
        company: str,
        role_family: str,
        employment_type: EmploymentType,
        topics: list[str],
        company_required: bool,
        limit: int,
    ) -> list[RetrievedEvidence]:
        rows = self.store.candidate_chunks(
            company=company if company_required else None,
            role_family=role_family,
            employment_type=employment_type.value,
            topics=topics,
            embedding_provider=self.embedding_provider.name,
        )
        if not rows:
            return []
        query_vector = self.embedding_provider.embed([query])[0]
        lexical_scores = _bm25_scores(query, rows)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row, lexical in zip(rows, lexical_scores, strict=True):
            dense = max(0.0, cosine_similarity(query_vector, row["embedding"]))
            exact_company = 1.0 if row["company"] == company else 0.0
            score = (
                dense * 0.48 + lexical * 0.27 + float(row["quality_score"]) * 0.10
                + _recency_score(row["published_at"]) * 0.10 + exact_company * 0.05
            )
            ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)

        selected: list[RetrievedEvidence] = []
        per_document: defaultdict[int, int] = defaultdict(int)
        for score, row in ranked:
            document_id = int(row["document_id"])
            if per_document[document_id] >= self.settings.max_chunks_per_document:
                continue
            selected.append(RetrievedEvidence(
                chunk_id=int(row["id"]),
                document_id=document_id,
                source=str(row["source"]),
                url=str(row["source_url"]),
                title=str(row["title"]),
                company=str(row["company"]),
                role_family=str(row["role_family"]),
                employment_type=str(row["employment_type"]),
                business_unit=str(row["business_unit"]),
                published_at=row["published_at"],
                topic=str(row["topic"]),
                text=str(row["text"]),
                score=round(score, 4),
                quality_score=float(row["quality_score"]),
                collection_method=str(row["collection_method"]),
            ))
            per_document[document_id] += 1
            if len(selected) >= limit:
                break
        return selected

    def retrieve_for_job(self, job: Job, config: AgentConfig) -> EvidenceBundle:
        if job.id is None:
            raise ValueError("Job must be persisted before evidence retrieval")
        company, role_family, employment_type, employment_type_origin = self._job_scope(job)
        bundle = EvidenceBundle(
            job_id=job.id,
            company=company,
            role_family=role_family,
            employment_type=employment_type.value,
        )
        queries = {
            "ability": self._query(job, config, "ability"),
            "need": self._query(job, config, "need"),
        }
        if company and role_family:
            per_dimension = max(1, self.settings.retrieval_top_k // 2)
            bundle.ability = self._rank(
                query=queries["ability"], company=company, role_family=role_family,
                employment_type=employment_type, topics=ABILITY_TOPICS,
                company_required=False, limit=per_dimension,
            )
            bundle.need = self._rank(
                query=queries["need"], company=company, role_family=role_family,
                employment_type=employment_type, topics=NEED_TOPICS,
                company_required=True, limit=per_dimension,
            )
        evidence = bundle.ability + bundle.need
        documents = {item.document_id for item in evidence}
        sources = {item.source for item in evidence}
        topics = sorted({item.topic for item in evidence})
        if len(documents) >= 4 and len(sources) >= 2:
            confidence = "high"
        elif len(documents) >= 2:
            confidence = "medium"
        elif documents:
            confidence = "low"
        else:
            confidence = "insufficient"
        bundle.coverage = {
            "documents": len(documents),
            "sources": len(sources),
            "topics": topics,
            "confidence": confidence,
            "employment_type": employment_type.value,
            "employment_type_origin": employment_type_origin,
            "cross_employment_fallback": False,
            "community_evidence_must_not_override_hard_rules": True,
        }
        self.store.save_retrieval(bundle, queries)
        return bundle
