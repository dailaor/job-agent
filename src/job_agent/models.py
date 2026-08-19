from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    # Several campus portals use hash routing for the actual job detail page.
    # Dropping the fragment would turn every job into the same list URL.
    path = parts.path if parts.fragment else parts.path.rstrip("/")
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        path,
        parts.query,
        parts.fragment.rstrip("/"),
    ))


def job_fingerprint(company: str, title: str, location: str) -> str:
    key = "|".join(normalize_text(item).lower() for item in (company, title, location))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


class Strategy(StrEnum):
    STRETCH = "冲高"
    MATCH = "持平"
    SAFE = "保底"
    SKIP = "不投"


class JobStatus(StrEnum):
    DISCOVERED = "已发现"
    ELIGIBLE = "可投"
    REJECTED = "已过滤"
    QUEUED = "待执行"
    DUPLICATE = "重复"
    EXPIRED = "已过期"
    MANUAL = "需人工"


class ApplicationStatus(StrEnum):
    PLANNED = "待执行"
    GREETING_SENT = "已发开场白"
    AWAITING_REPLY = "等待HR回复"
    HR_REPLIED = "HR已有效回复"
    RESUME_SENT = "已发简历"
    OFFICIAL_SUBMITTED = "官网已提交待回执"
    CONFIRMED = "投递已确认"
    REJECTED = "已拒绝"
    NEEDS_LOGIN = "需要登录"
    NEEDS_HUMAN = "需要人工处理"
    UNVERIFIED = "结果待核验"
    FAILED = "执行失败"
    CLOSED = "已关闭"


@dataclass(slots=True)
class Candidate:
    name: str
    headline: str = ""
    years_experience: float = 0
    education: str = ""
    skills: list[str] = field(default_factory=list)
    resume_path: str = ""
    resume_filename: str = ""
    resume_text_path: str = ""
    profile_source: str = "manual"


@dataclass(slots=True)
class Job:
    source: str
    source_id: str
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    experience_min: float | None = None
    experience_max: float | None = None
    education: str = ""
    published_at: str | None = None
    deadline: str | None = None
    apply_url: str | None = None
    recruiter_name: str | None = None
    recruiter_activity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        self.title = normalize_text(self.title)
        self.company = normalize_text(self.company)
        self.location = normalize_text(self.location)
        self.url = normalize_url(self.url)
        if self.apply_url:
            self.apply_url = normalize_url(self.apply_url)
        if not self.fingerprint:
            self.fingerprint = job_fingerprint(self.company, self.title, self.location)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Job":
        data = dict(row)
        metadata = data.pop("metadata_json", "{}")
        data["metadata"] = json.loads(metadata or "{}")
        for key in ("status", "first_seen_at", "last_seen_at"):
            data.pop(key, None)
        return cls(**data)


@dataclass(slots=True)
class Evaluation:
    job_id: int
    hard_pass: bool
    strategy: Strategy
    ability_relation: str
    matched_capabilities: list[str]
    missing_capabilities: list[str]
    hard_reasons: list[str]
    match_score: float
    need_score: float
    company_score: float
    overall_score: float
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["strategy"] = self.strategy.value
        return data
