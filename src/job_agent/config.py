from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Candidate


DEFAULT_STRATEGY_MIX = {"冲高": 0.25, "持平": 0.5, "保底": 0.25}
EMPLOYMENT_TYPES = {"全职", "实习", "校招", "兼职"}
WORK_MODES = {"现场", "混合", "远程"}
UNKNOWN_FIELD_POLICIES = {"keep", "reject"}
STRATEGY_MODES = {"stretch", "balanced", "safe"}
SCORING_PROVIDERS = {"rule", "deepseek"}
WORKLOAD_PREFERENCES = {"low_intensity", "balanced", "growth_first"}
ROLE_BOUNDARY_PREFERENCES = {"no_preference", "clear", "broad"}
PRIORITY_LEVELS = {"low", "medium", "high"}


def _default_knowledge_companies() -> dict[str, list[str]]:
    return {
        "美团": ["美团", "大众点评", "meituan"],
        "阿里": ["阿里", "阿里巴巴", "阿里云", "淘天", "淘宝", "天猫", "alibaba"],
        "快手": ["快手", "kuaishou"],
        "腾讯": ["腾讯", "腾讯云", "tencent"],
        "百度": ["百度", "百度集团", "baidu"],
    }


def _default_knowledge_roles() -> dict[str, list[str]]:
    return {
        "product": [
            "产品经理", "ai产品", "大模型产品", "智能体产品", "数据产品",
            "策略产品", "增长产品", "平台产品", "b端产品", "用户产品", "产品策划", "产品岗",
        ],
        "data": [
            "数据分析", "数分", "商业分析", "商分", "经营分析", "策略分析", "数据科学",
            "数据运营", "数据研发", "数据工程", "大数据开发", "数仓",
        ],
        "algorithm": [
            "算法工程师", "算法岗", "大模型算法", "ai算法", "机器学习", "llm", "nlp",
            "推荐算法", "搜索算法", "推理算法", "算法实习",
        ],
        "backend": [
            "后端开发", "后端研发", "后端岗", "服务端开发", "java开发", "go开发", "golang",
        ],
    }


@dataclass(slots=True)
class KnowledgeSettings:
    """Local job-intelligence settings with safe defaults for old configurations."""

    enabled: bool = True
    allowed_sources: list[str] = field(default_factory=lambda: ["nowcoder", "xiaohongshu", "manual"])
    company_aliases: dict[str, list[str]] = field(default_factory=_default_knowledge_companies)
    role_families: dict[str, list[str]] = field(default_factory=_default_knowledge_roles)
    min_document_chars: int = 120
    max_document_chars: int = 20_000
    max_age_days: int = 730
    retain_full_text: bool = False
    embedding_provider: str = "hashing"
    embedding_dimensions: int = 384
    retrieval_top_k: int = 12
    max_chunks_per_document: int = 2
    public_fetch_min_interval_seconds: float = 5.0

    def validate(self) -> None:
        if not self.allowed_sources:
            raise ValueError("knowledge.allowed_sources cannot be empty")
        unknown_sources = set(self.allowed_sources) - {"nowcoder", "xiaohongshu", "manual"}
        if unknown_sources:
            raise ValueError(f"Unknown knowledge sources: {sorted(unknown_sources)}")
        if not self.company_aliases or any(not aliases for aliases in self.company_aliases.values()):
            raise ValueError("knowledge.company_aliases must contain non-empty aliases")
        if not self.role_families or any(not aliases for aliases in self.role_families.values()):
            raise ValueError("knowledge.role_families must contain non-empty aliases")
        if not 40 <= self.min_document_chars <= 5_000:
            raise ValueError("knowledge.min_document_chars must be between 40 and 5000")
        if not self.min_document_chars <= self.max_document_chars <= 200_000:
            raise ValueError("knowledge.max_document_chars is invalid")
        if not 30 <= self.max_age_days <= 3650:
            raise ValueError("knowledge.max_age_days must be between 30 and 3650")
        if self.embedding_provider != "hashing":
            raise ValueError("Only the built-in hashing embedding provider is currently bundled")
        if not 64 <= self.embedding_dimensions <= 4096:
            raise ValueError("knowledge.embedding_dimensions must be between 64 and 4096")
        if not 1 <= self.retrieval_top_k <= 50:
            raise ValueError("knowledge.retrieval_top_k must be between 1 and 50")
        if not 1 <= self.max_chunks_per_document <= 5:
            raise ValueError("knowledge.max_chunks_per_document must be between 1 and 5")
        if not 1 <= self.public_fetch_min_interval_seconds <= 3600:
            raise ValueError("knowledge.public_fetch_min_interval_seconds must be between 1 and 3600")


@dataclass(slots=True)
class ScoringSettings:
    """Model-judge settings. Secrets are read only from the named process environment variable."""

    provider: str = "rule"
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "DEEPSEEK_API_KEY"
    timeout_seconds: float = 90.0
    max_tokens: int = 2400
    temperature: float = 0.0
    thinking: bool = False

    def validate(self) -> None:
        if self.provider not in SCORING_PROVIDERS:
            raise ValueError(f"Unknown scoring provider: {self.provider}")
        if self.provider == "deepseek" and self.model != "deepseek-v4-flash":
            raise ValueError("This evaluator is calibrated for deepseek-v4-flash")
        if not self.base_url.startswith("https://"):
            raise ValueError("scoring.base_url must use HTTPS")
        if not self.api_key_env or not self.api_key_env.replace("_", "").isalnum():
            raise ValueError("scoring.api_key_env must be an environment variable name")
        if not 5 <= self.timeout_seconds <= 600:
            raise ValueError("scoring.timeout_seconds must be between 5 and 600")
        if not 256 <= self.max_tokens <= 16_000:
            raise ValueError("scoring.max_tokens must be between 256 and 16000")
        if not 0 <= self.temperature <= 2:
            raise ValueError("scoring.temperature must be between 0 and 2")


@dataclass(slots=True)
class Preferences:
    boss_keywords: list[str] = field(default_factory=list)
    official_keywords: list[str] = field(default_factory=list)
    target_titles: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)
    work_modes: list[str] = field(default_factory=list)
    workload_preference: str = "balanced"
    role_boundary_preference: str = "no_preference"
    growth_priority: str = "medium"
    stability_priority: str = "medium"
    culture_preferences: list[str] = field(default_factory=list)
    community_risk_avoidances: list[str] = field(default_factory=list)
    minimum_salary: int | None = None
    max_experience_gap: float = 2
    published_within_days: int | None = 30
    unknown_field_policy: str = "keep"
    blacklisted_companies: list[str] = field(default_factory=list)
    company_tiers: dict[str, list[str]] = field(default_factory=dict)
    boss_daily_limit: int = 20
    official_daily_limit: int = 10
    strategy_mix: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_STRATEGY_MIX))
    strategy_mode: str = "balanced"
    channel_priority: list[str] = field(default_factory=lambda: ["official", "boss"])
    max_overqualification_years: float = 3
    auto_send_resume_after_reply: bool = False

    def validate(self) -> None:
        for name, value in (
            ("boss_daily_limit", self.boss_daily_limit),
            ("official_daily_limit", self.official_daily_limit),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        if any(value < 0 for value in self.strategy_mix.values()):
            raise ValueError("strategy_mix values must be non-negative")
        if sum(self.strategy_mix.values()) <= 0:
            raise ValueError("strategy_mix must contain a positive value")
        if self.strategy_mode not in STRATEGY_MODES:
            raise ValueError("strategy_mode must be stretch, balanced or safe")
        unknown_employment_types = set(self.employment_types) - EMPLOYMENT_TYPES
        if unknown_employment_types:
            raise ValueError(f"Unknown employment_types: {sorted(unknown_employment_types)}")
        unknown_work_modes = set(self.work_modes) - WORK_MODES
        if unknown_work_modes:
            raise ValueError(f"Unknown work_modes: {sorted(unknown_work_modes)}")
        if self.workload_preference not in WORKLOAD_PREFERENCES:
            raise ValueError("workload_preference must be low_intensity, balanced or growth_first")
        if self.role_boundary_preference not in ROLE_BOUNDARY_PREFERENCES:
            raise ValueError("role_boundary_preference must be no_preference, clear or broad")
        for name, value in (
            ("growth_priority", self.growth_priority),
            ("stability_priority", self.stability_priority),
        ):
            if value not in PRIORITY_LEVELS:
                raise ValueError(f"{name} must be low, medium or high")
        if len(self.culture_preferences) > 20 or len(self.community_risk_avoidances) > 20:
            raise ValueError("community preference lists cannot contain more than 20 items")
        if any(
            not isinstance(item, str) or not item.strip() or len(item.strip()) > 80
            for item in [*self.culture_preferences, *self.community_risk_avoidances]
        ):
            raise ValueError("community preference items must contain 1 to 80 characters")
        if self.minimum_salary is not None and self.minimum_salary < 0:
            raise ValueError("minimum_salary must be non-negative")
        if not 0 <= self.max_experience_gap <= 20:
            raise ValueError("max_experience_gap must be between 0 and 20")
        if self.published_within_days is not None and not 1 <= self.published_within_days <= 3650:
            raise ValueError("published_within_days must be between 1 and 3650")
        if self.unknown_field_policy not in UNKNOWN_FIELD_POLICIES:
            raise ValueError("unknown_field_policy must be keep or reject")


@dataclass(slots=True)
class AgentConfig:
    candidate: Candidate
    preferences: Preferences
    greetings: dict[str, str] = field(default_factory=dict)
    fixed_answers: dict[str, str] = field(default_factory=dict)
    boss: dict[str, Any] = field(default_factory=dict)
    official_sites: list[dict[str, Any]] = field(default_factory=list)
    mail: dict[str, Any] = field(default_factory=dict)
    knowledge: KnowledgeSettings = field(default_factory=KnowledgeSettings)
    scoring: ScoringSettings = field(default_factory=ScoringSettings)

    def validate(self) -> None:
        if not self.candidate.name.strip():
            raise ValueError("candidate.name is required")
        self.preferences.validate()
        self.knowledge.validate()
        self.scoring.validate()
        default_greeting = self.greetings.get("default", "")
        if not default_greeting.strip():
            raise ValueError("greetings.default is required")

    def greeting_for(self, title: str, company: str) -> str:
        template = self.greetings.get("default", "")
        for keyword, candidate in self.greetings.items():
            if keyword != "default" and keyword.lower() in title.lower():
                template = candidate
                break
        allowed = {"title": title, "company": company, "name": self.candidate.name}
        try:
            result = template.format(**allowed).strip()
        except KeyError as exc:
            raise ValueError(f"Unknown greeting placeholder: {exc.args[0]}") from exc
        if not result or len(result) > 500:
            raise ValueError("Greeting must contain 1 to 500 characters")
        return result


def load_config(path: str | Path) -> AgentConfig:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    return config_from_dict(data)


def config_from_dict(data: dict[str, Any]) -> AgentConfig:
    config = AgentConfig(
        candidate=Candidate(**data.get("candidate", {})),
        preferences=Preferences(**data.get("preferences", {})),
        greetings=dict(data.get("greetings", {})),
        fixed_answers={str(k): str(v) for k, v in data.get("fixed_answers", {}).items()},
        boss=dict(data.get("boss", {})),
        official_sites=list(data.get("official_sites", [])),
        mail=dict(data.get("mail", {})),
        knowledge=KnowledgeSettings(**data.get("knowledge", {})),
        scoring=ScoringSettings(**data.get("scoring", {})),
    )
    config.validate()
    return config


def config_to_dict(config: AgentConfig) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(config)


def save_config(config: AgentConfig, path: str | Path) -> None:
    config.validate()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(config_to_dict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
