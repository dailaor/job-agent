from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from .config import AgentConfig
from .models import Evaluation, Job, Strategy
from .resume import SKILL_UNIVERSE, contains_skill


EDUCATION_LEVEL = {"": 0, "不限": 0, "高中": 1, "大专": 2, "本科": 3, "硕士": 4, "博士": 5}
RANKING_WEIGHTS = {
    "stretch": (0.35, 0.65),
    "balanced": (0.50, 0.50),
    "safe": (0.65, 0.35),
}


def _contains_any(text: str, values: list[str]) -> bool:
    lowered = text.lower()
    return any(value.strip().lower() in lowered for value in values if value.strip())


def _extract_required_skills(job: Job, configured_skills: list[str]) -> list[str]:
    explicit = job.metadata.get("required_skills")
    if isinstance(explicit, list) and explicit:
        return sorted({str(item).strip() for item in explicit if str(item).strip()})
    text = f"{job.title} {job.description}"
    universe = configured_skills + list(SKILL_UNIVERSE)
    return sorted({skill for skill in universe if skill and contains_skill(text, skill)})


def _parse_experience(job: Job) -> tuple[float | None, float | None]:
    if job.experience_min is not None or job.experience_max is not None:
        return job.experience_min, job.experience_max
    text = f"{job.title} {job.description}"
    match = re.search(r"(\d+(?:\.\d+)?)\s*[-—至]\s*(\d+(?:\.\d+)?)\s*年", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    match = re.search(r"(\d+(?:\.\d+)?)\s*年以上", text)
    if match:
        return float(match.group(1)), None
    if "应届" in text or "在校" in text or "实习" in job.title:
        return 0, 1
    return None, None


def _metadata_values(job: Job, *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = job.metadata.get(key)
        if isinstance(raw, list):
            values.extend(str(item).strip() for item in raw if str(item).strip())
        elif raw is not None and str(raw).strip():
            values.append(str(raw).strip())
    return values


def _employment_types(job: Job) -> list[str]:
    values = _metadata_values(job, "employment_type", "employment_types", "job_type")
    text = f"{job.title} {job.description} {' '.join(values)}".lower()
    detected: set[str] = set()
    if "实习" in text or "intern" in text:
        detected.add("实习")
    if any(marker in text for marker in ("校招", "校园招聘", "应届", "毕业生", "campus")):
        detected.add("校招")
    if "兼职" in text or "part-time" in text or "part time" in text:
        detected.add("兼职")
    if "全职" in text or "社招" in text or "full-time" in text or "full time" in text:
        detected.add("全职")
    return sorted(detected)


def _work_modes(job: Job) -> list[str]:
    values = _metadata_values(job, "work_mode", "work_modes")
    text = f"{job.location} {job.description} {' '.join(values)}".lower()
    detected: set[str] = set()
    if "远程" in text or "remote" in text:
        detected.add("远程")
    if "混合" in text or "hybrid" in text:
        detected.add("混合")
    if any(marker in text for marker in ("现场", "坐班", "到岗", "onsite", "on-site")):
        detected.add("现场")
    return sorted(detected)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def hard_filter(job: Job, config: AgentConfig) -> list[str]:
    p = config.preferences
    text = f"{job.title} {job.company} {job.description}"
    reasons: list[str] = []
    reject_unknown = p.unknown_field_policy == "reject"
    if job.source == "boss" and not job.metadata.get("detail_loaded"):
        reasons.append("未获取稳定岗位详情")
    if p.target_titles and not _contains_any(job.title, p.target_titles):
        reasons.append("岗位名称不在目标范围")
    if _contains_any(text, p.excluded_keywords):
        reasons.append("命中排除关键词")
    if any(name.lower() in job.company.lower() for name in p.blacklisted_companies):
        reasons.append("公司位于黑名单")
    if any(name.lower() in job.company.lower() for name in p.company_tiers.get("不投", [])):
        reasons.append("公司层级配置为不投")
    if p.locations and not _contains_any(job.location, p.locations):
        reasons.append("地点不符合要求")
    if p.employment_types:
        employment_types = _employment_types(job)
        if employment_types and not set(employment_types).intersection(p.employment_types):
            reasons.append("职位类型不符合要求")
        elif not employment_types and reject_unknown:
            reasons.append("职位类型未披露")
    if p.work_modes:
        work_modes = _work_modes(job)
        if work_modes and not set(work_modes).intersection(p.work_modes):
            reasons.append("办公方式不符合要求")
        elif not work_modes and reject_unknown:
            reasons.append("办公方式未披露")
    if p.minimum_salary:
        if job.salary_max is not None and job.salary_max < p.minimum_salary:
            reasons.append("薪资上限低于最低期望")
        elif job.salary_max is None and reject_unknown:
            reasons.append("薪资未披露")
    if job.deadline:
        deadline = _parse_datetime(job.deadline)
        if deadline is not None and deadline < datetime.now(timezone.utc):
            reasons.append("岗位已过截止时间")
        elif deadline is None and reject_unknown:
            reasons.append("截止时间格式无法确认")
    if p.published_within_days is not None:
        published = _parse_datetime(job.published_at)
        if published is not None:
            age_days = max(0, (datetime.now(timezone.utc) - published).days)
            if age_days > p.published_within_days:
                reasons.append(f"发布时间超过 {p.published_within_days} 天")
        elif reject_unknown:
            reasons.append("发布时间未披露")
    required_education = EDUCATION_LEVEL.get(job.education, 0)
    candidate_education = EDUCATION_LEVEL.get(config.candidate.education, 0)
    if required_education and candidate_education and candidate_education < required_education:
        reasons.append("学历硬条件不满足")
    minimum, _ = _parse_experience(job)
    if minimum is not None and minimum - config.candidate.years_experience > p.max_experience_gap:
        reasons.append(f"最低经验要求差距超过 {p.max_experience_gap:g} 年")
    return reasons


def _company_score(company: str, config: AgentConfig) -> tuple[float, str]:
    tiers = config.preferences.company_tiers
    for tier, score in (("优先", 100.0), ("可接受", 70.0), ("不投", 0.0)):
        if any(name.lower() in company.lower() for name in tiers.get(tier, [])):
            return score, tier
    return 50.0, "未知"


def _job_need_score(job: Job, config: AgentConfig, company_score: float, freshness: float) -> float:
    """Score how well the job satisfies the user's stated needs, separately from candidate fit."""

    p = config.preferences
    location = 100.0 if p.locations and _contains_any(job.location, p.locations) else 70.0
    if p.minimum_salary is None:
        salary = 75.0 if job.salary_max is not None else 65.0
    elif job.salary_max is None:
        salary = 55.0
    else:
        salary = 100.0 if job.salary_max >= p.minimum_salary else 0.0
    employment = 70.0
    if p.employment_types:
        known = _employment_types(job)
        employment = 100.0 if set(known).intersection(p.employment_types) else 55.0 if not known else 0.0
    work_mode = 70.0
    if p.work_modes:
        known = _work_modes(job)
        work_mode = 100.0 if set(known).intersection(p.work_modes) else 55.0 if not known else 0.0
    return max(0.0, min(100.0,
        company_score * 0.30
        + freshness * 0.20
        + location * 0.20
        + salary * 0.15
        + employment * 0.075
        + work_mode * 0.075
    ))


def evaluate_job(job: Job, config: AgentConfig) -> Evaluation:
    if job.id is None:
        raise ValueError("Job must be persisted before evaluation")
    hard_reasons = hard_filter(job, config)
    candidate_skills = {item.lower(): item for item in config.candidate.skills}
    required = _extract_required_skills(job, config.candidate.skills)
    matched = [item for item in required if item.lower() in candidate_skills]
    missing = [item for item in required if item.lower() not in candidate_skills]
    coverage = len(matched) / len(required) if required else 0.65
    minimum, maximum = _parse_experience(job)
    years = config.candidate.years_experience
    min_gap = (minimum - years) if minimum is not None else 0
    max_advantage = (years - maximum) if maximum is not None else 0

    if hard_reasons:
        strategy = Strategy.SKIP
        relation = "硬条件不满足"
    elif coverage < 0.45:
        strategy = Strategy.SKIP
        relation = "差距过大"
    elif max_advantage > config.preferences.max_overqualification_years:
        strategy = Strategy.SKIP
        relation = "岗位明显低于用户能力"
    elif min_gap > 0.25 or (missing and coverage < 0.8):
        strategy = Strategy.STRETCH
        relation = "岗位略高"
    elif max_advantage > 0.75 or (coverage >= 0.9 and maximum is not None and years > maximum):
        strategy = Strategy.SAFE
        relation = "用户略高"
    else:
        strategy = Strategy.MATCH
        relation = "基本持平"

    skill_score = coverage * 100
    experience_penalty = min(abs(min_gap) * 12, 30) if min_gap else min(max(max_advantage, 0) * 6, 20)
    match_score = max(0.0, min(100.0, skill_score - experience_penalty + 10))
    company_score, company_tier = _company_score(job.company, config)
    freshness = 60.0
    if job.published_at:
        try:
            published = datetime.fromisoformat(job.published_at.replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            age_days = max(0, (datetime.now(timezone.utc) - published).days)
            freshness = max(0, 100 - age_days * 4)
        except ValueError:
            freshness = 40
    need_score = _job_need_score(job, config, company_score, freshness)
    match_weight, need_weight = RANKING_WEIGHTS[config.preferences.strategy_mode]
    overall = match_score * match_weight + need_score * need_weight
    if strategy is Strategy.SKIP:
        overall = min(overall, 35)
    confidence = min(0.98, 0.55 + 0.08 * len(required) + (0.1 if minimum is not None else 0))
    reason = (
        f"能力关系：{relation}；技能覆盖 {len(matched)}/{len(required) or '未结构化'}；"
        f"岗位满足度 {need_score:.0f}；公司档位：{company_tier}。"
    )
    if hard_reasons:
        reason += " 硬规则：" + "、".join(hard_reasons)
    return Evaluation(
        job_id=job.id,
        hard_pass=not hard_reasons,
        strategy=strategy,
        ability_relation=relation,
        matched_capabilities=matched,
        missing_capabilities=missing,
        hard_reasons=hard_reasons,
        match_score=round(match_score, 2),
        need_score=round(need_score, 2),
        company_score=company_score,
        overall_score=round(overall, 2),
        confidence=round(confidence, 2),
        reason=reason,
    )


def strategy_allocation(limit: int, mix: dict[str, float]) -> dict[str, int]:
    active = {name: weight for name, weight in mix.items() if weight > 0}
    total = sum(active.values())
    if limit <= 0 or total <= 0:
        return {name: 0 for name in mix}
    raw = {name: limit * weight / total for name, weight in active.items()}
    result = {name: math.floor(value) for name, value in raw.items()}
    remaining = limit - sum(result.values())
    for name in sorted(raw, key=lambda item: raw[item] - result[item], reverse=True)[:remaining]:
        result[name] += 1
    return {name: result.get(name, 0) for name in mix}
