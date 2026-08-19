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


@dataclass(slots=True)
class Preferences:
    boss_keywords: list[str] = field(default_factory=list)
    official_keywords: list[str] = field(default_factory=list)
    target_titles: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)
    work_modes: list[str] = field(default_factory=list)
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

    def validate(self) -> None:
        if not self.candidate.name.strip():
            raise ValueError("candidate.name is required")
        self.preferences.validate()
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
