from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from ..models import normalize_text, normalize_url, utc_now


class PolicyStatus(StrEnum):
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class SourceStatus(StrEnum):
    IMPORTED = "imported"
    PUBLIC_FETCHED = "public_fetched"
    BROWSER_FETCHED = "browser_fetched"
    AUTH_REQUIRED = "auth_required"
    PORTAL_UNPARSED = "portal_unparsed"
    ACCESS_LIMITED = "access_limited"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    UNKNOWN = "unknown"


EMPLOYMENT_TYPE_ALIASES = {
    "full_time": EmploymentType.FULL_TIME,
    "full-time": EmploymentType.FULL_TIME,
    "fulltime": EmploymentType.FULL_TIME,
    "全职": EmploymentType.FULL_TIME,
    "正职": EmploymentType.FULL_TIME,
    "校招": EmploymentType.FULL_TIME,
    "社招": EmploymentType.FULL_TIME,
    "正式": EmploymentType.FULL_TIME,
    "internship": EmploymentType.INTERNSHIP,
    "intern": EmploymentType.INTERNSHIP,
    "实习": EmploymentType.INTERNSHIP,
    "日常实习": EmploymentType.INTERNSHIP,
    "暑期实习": EmploymentType.INTERNSHIP,
}


def normalize_employment_type(value: str | EmploymentType | None) -> EmploymentType:
    if isinstance(value, EmploymentType):
        return value
    normalized = normalize_text(str(value or "")).lower()
    return EMPLOYMENT_TYPE_ALIASES.get(normalized, EmploymentType.UNKNOWN)


@dataclass(slots=True)
class PostDocument:
    source: str
    url: str
    title: str
    content: str
    published_at: str | None = None
    company: str = ""
    role_family: str = ""
    business_unit: str = ""
    city: str = ""
    seniority: str = ""
    employment_type: EmploymentType | str = EmploymentType.UNKNOWN
    author: str = ""
    collection_method: str = "manual_import"
    source_status: SourceStatus = SourceStatus.IMPORTED
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source = self.source.strip().lower()
        self.url = normalize_url(self.url)
        self.title = normalize_text(self.title)
        self.content = self.content.replace("\x00", "").strip()
        self.company = normalize_text(self.company)
        self.role_family = self.role_family.strip().lower()
        self.business_unit = normalize_text(self.business_unit)
        self.city = normalize_text(self.city)
        self.seniority = normalize_text(self.seniority)
        self.employment_type = normalize_employment_type(self.employment_type)

    @property
    def content_hash(self) -> str:
        normalized = normalize_text(self.content).lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @property
    def author_hash(self) -> str:
        if not self.author.strip():
            return ""
        return hashlib.sha256(f"{self.source}|{self.author.strip()}".encode("utf-8")).hexdigest()[:24]


@dataclass(slots=True)
class PolicyDecision:
    status: PolicyStatus
    reasons: list[str]
    company: str
    role_family: str
    employment_type: EmploymentType
    topics: list[str]
    quality_score: float
    sanitized_content: str

    @property
    def indexable(self) -> bool:
        return self.status is PolicyStatus.ACCEPTED


@dataclass(slots=True)
class KnowledgeChunk:
    ordinal: int
    topic: str
    text: str
    contextual_text: str
    start_offset: int
    end_offset: int
    chunk_hash: str
    embedding: list[float] = field(default_factory=list)


@dataclass(slots=True)
class RetrievedEvidence:
    chunk_id: int
    document_id: int
    source: str
    url: str
    title: str
    company: str
    role_family: str
    employment_type: str
    business_unit: str
    published_at: str | None
    topic: str
    text: str
    score: float
    quality_score: float
    collection_method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceBundle:
    job_id: int
    company: str
    role_family: str
    employment_type: str
    ability: list[RetrievedEvidence] = field(default_factory=list)
    need: list[RetrievedEvidence] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    retrieved_at: str = field(default_factory=utc_now)

    @property
    def evidence_count(self) -> int:
        return len(self.ability) + len(self.need)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "company": self.company,
            "role_family": self.role_family,
            "employment_type": self.employment_type,
            "ability": [item.to_dict() for item in self.ability],
            "need": [item.to_dict() for item in self.need],
            "coverage": self.coverage,
            "evidence_count": self.evidence_count,
            "retrieved_at": self.retrieved_at,
        }


@dataclass(slots=True)
class SourceFetchResult:
    status: SourceStatus
    message: str
    document: PostDocument | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "document": asdict(self.document) if self.document else None,
        }
