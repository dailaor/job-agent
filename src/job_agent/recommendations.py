from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AgentConfig
from .knowledge.models import EmploymentType, normalize_employment_type
from .matching import EDUCATION_LEVEL, _extract_required_skills, _parse_experience, hard_filter
from .models import Job, JobStatus, utc_now
from .resume import contains_skill


EXPERIENCE = {
    "time": ("时间负担", ["常规上下班时间", "周末加班频率", "值班、出差与通勤"],
             r"上下班|上班时间|下班|工作时间|工时|每周.{0,8}小时|加班|双休|大小周|996|995|on[- ]?call|值班|出差|远程|混合办公|通勤"),
    "pace": ("工作节奏", ["需求变化与紧急任务比例", "交付周期", "会议负担与人手配置"],
             r"需求.{0,8}(?:变更|变化|频繁)|紧急任务|临时任务|迭代周期|发布周期|交付周期|会议|汇报频率|人手不足|长期缺人"),
    "responsibility": ("职责质量", ["核心业务与实际职责", "决策权与自主空间", "重复执行工作占比"],
                       r"负责|岗位职责|工作内容|决策权|核心业务|支持部门|自主空间|重复执行"),
    "culture": ("管理文化", ["直属领导与沟通方式", "绩效透明度", "团队协作与心理安全"],
                r"团队氛围|管理方式|直属领导|绩效|末位淘汰|\bpip\b|心理安全|沟通方式|甩锅|内耗|管理透明"),
    "growth": ("成长性", ["导师与培训", "晋升与内部转岗路径", "能力可迁移性"],
               r"导师|\bmentor\b|培训|晋升|内部转岗|职业路径|培养计划|学习机会"),
    "stability": ("稳定性", ["团队流动与业务变化", "HC 与用工合同", "裁员、续签或转正情况"],
                  r"裁员|业务收缩|组织调整|人员流动|续签|劳务派遣|外包|劳动合同|转正|真实\s*hc|hc\s*(?:充足|冻结)"),
}
COMPENSATION_FIELDS = {
    "fixed_salary": "固定薪资", "salary_months": "发薪月数", "bonus": "奖金与年终奖",
    "equity": "股票、期权与归属", "benefits": "补贴与福利", "insurance": "五险一金基数",
    "probation": "试用期薪资", "overtime": "加班费或调休", "signing_bonus": "签字费",
    "annual_cash": "保底年现金收入", "total_package": "预期总包", "effective_hourly": "有效时薪",
}
COMPENSATION_PATTERNS = {
    "salary_months": r"\d+\s*薪|发薪.{0,8}\d+\s*个月",
    "bonus": r"年终奖|绩效奖金|目标奖金|年度奖金",
    "equity": r"(?:薪酬|薪资|待遇|授予|发放|归属|激励).{0,15}(?:股票|期权)|(?:股票|期权).{0,15}(?:归属|激励|授予|薪酬)",
    "benefits": r"餐补|房补|交通补贴|住房补贴|补贴|员工福利",
    "insurance": r"五险一金|公积金.{0,12}(?:基数|比例)|社保.{0,12}基数",
    "probation": r"试用期.{0,20}(?:薪|工资|折|待遇)",
    "overtime": r"加班费|加班.{0,10}调休|调休制度",
    "signing_bonus": r"签字费|签约奖金|sign[- ]?on",
}


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _json(value: Any, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (ValueError, TypeError):
        return default


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n\r。；;]+", text) if part.strip()]


def _education(value: str, *, structured: bool = False) -> tuple[str, str]:
    """Return the lowest explicitly accepted level, without upgrading preferences."""
    if not value.strip():
        return "", "unknown"
    if "不限" in value or "无学历要求" in value:
        return "不限", "none"
    levels = [level for level in EDUCATION_LEVEL if level and level != "不限" and level in value]
    if not levels:
        return "", "unknown"
    lowest = min(levels, key=EDUCATION_LEVEL.get)
    if any(marker in value for marker in ("优先", "优选", "加分", "可放宽")):
        clauses = re.split(r"[,，。；;]+|且|但", value)
        if len(clauses) > 1:
            required = [_education(clause, structured=structured) for clause in clauses
                        if not any(marker in clause for marker in ("优先", "优选", "加分", "可放宽"))]
            required = [level for level, kind in required if kind == "required"]
            if required:
                return min(required, key=EDUCATION_LEVEL.get), "required"
        return lowest, "preferred"
    if structured or re.search(r"学历|及以上|以上学历|至少|须|需具备|要求|毕业", value):
        return lowest, "required"
    return lowest, "unknown"


def _education_requirement(job: Job) -> tuple[str, str, str]:
    candidates: list[tuple[str, str, str]] = []
    if job.education:
        degree, kind = _education(job.education, structured=True)
        candidates.append((degree, kind, job.education))
    for sentence in _sentences(job.description):
        degree, kind = _education(sentence)
        if kind in {"required", "none", "preferred"}:
            candidates.append((degree, kind, sentence))
    required = [item for item in candidates if item[1] == "required"]
    if required:
        return max(required, key=lambda item: EDUCATION_LEVEL.get(item[0], 0))
    if candidates:
        return candidates[0]
    return "", "unknown", ""


def _canonical_company(company: str, config: AgentConfig) -> str:
    normalized = company.strip().lower()
    for canonical, aliases in config.knowledge.company_aliases.items():
        if normalized in {canonical.lower(), *(alias.lower() for alias in aliases)}:
            return canonical
    # Deliberately do not use substring matching: 腾讯音乐 is not every 腾讯 team.
    return normalized


def _job_scope(job: Job, config: AgentConfig) -> dict[str, str]:
    family = str(job.metadata.get("role_family") or "")
    if family not in config.knowledge.role_families:
        family = next((key for key, aliases in config.knowledge.role_families.items()
                       if any(alias.lower() in job.title.lower() for alias in aliases)), "")
    employment = normalize_employment_type(job.metadata.get("employment_type"))
    if employment is EmploymentType.UNKNOWN:
        if "实习" in job.title or "intern" in job.title.lower():
            employment = EmploymentType.INTERNSHIP
        elif any(marker in job.title for marker in ("校招", "社招", "全职", "应届")):
            employment = EmploymentType.FULL_TIME
    return {
        "company": job.company, "role_family": family, "employment_type": employment.value,
        "business_unit": str(job.metadata.get("business_unit") or job.metadata.get("team") or ""),
        "city": job.location,
    }


def _salary_unit(job: Job) -> str:
    declared = str(job.metadata.get("salary_unit") or job.metadata.get("salary_period") or "").lower()
    if declared in {"month", "monthly", "月", "月薪", "元/月", "cny/month"}:
        return "month"
    if declared in {"day", "daily", "日", "日薪", "元/天", "元/日"}:
        return "day"
    if declared in {"year", "annual", "年", "年薪", "元/年"}:
        return "year"
    raw = str(job.metadata.get("salary_text") or "")
    for unit, pattern in (("day", r"(?:元|k|万)?\s*[/／]\s*(?:天|日)|日薪"),
                          ("month", r"(?:元|k|万)?\s*[/／]\s*月|月薪"),
                          ("year", r"(?:元|k|万)?\s*[/／]\s*年|年薪")):
        if re.search(pattern, raw, re.I):
            return unit
    return "unknown"


def _read_current(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.is_file():
        return [], []
    # No Database/KnowledgeStore initializer, schema migration, retrieval or cache writes.
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=20)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "jobs" not in tables:
            return [], []
        jobs = [dict(row) for row in connection.execute("SELECT * FROM jobs ORDER BY id DESC")]
        evidence: list[dict[str, Any]] = []
        if {"knowledge_documents", "knowledge_chunks"}.issubset(tables):
            evidence = [dict(row) for row in connection.execute(
                """SELECT c.id AS chunk_id,c.document_id,c.topic,c.text,d.source,d.source_url,
                   d.title,d.company,d.role_family,d.employment_type,d.business_unit,d.city,
                   d.published_at,d.collected_at,d.quality_score
                   FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id
                   WHERE d.policy_status='accepted' ORDER BY d.quality_score DESC,d.published_at DESC,c.id DESC"""
            )]
        return jobs, evidence
    finally:
        connection.close()


def _dimensions(text: str) -> list[str]:
    # A stage anecdote mentioning 出差 is not evidence of this job's travel burden.
    if re.search(r"面试|笔试|一面|二面|三面|复试|初试|意向面|主管面|业务面|hr\s*面|面经|算法题", text, re.I):
        return []
    result = [key for key, (_, _, pattern) in EXPERIENCE.items() if re.search(pattern, text, re.I)]
    if any(re.search(pattern, text, re.I) for pattern in COMPENSATION_PATTERNS.values()):
        result.append("compensation")
    return result


def _marker_negated(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 8):match.start()]
    if re.search(r"(?:不|无|没|没有|不提供|不实行|不是|并非|取消).{0,3}$", prefix):
        return True
    suffix = re.split(r"[\n\r。；;，,]", text[match.end():match.end() + 16], maxsplit=1)[0]
    if re.search(r"(?:未|没有|并未|不会).{0,2}(?:取消|暂停)", suffix):
        return False
    return bool(re.search(r"^.{0,8}(?:已取消|未提供|不存在|暂停|取消)", suffix))


def _unnegated_marker(text: str, pattern: str) -> bool:
    return any(not _marker_negated(text, match) for match in re.finditer(pattern, text, re.I))


def _growth_gap(text: str) -> bool:
    return any(_marker_negated(text, match) for match in re.finditer(r"导师|培训|培养计划", text, re.I))


def _time_polarity(text: str) -> tuple[bool, bool]:
    low = _unnegated_marker(text, r"不加班|无需加班|双休|每周\s*(?:40|35|36|37|38|39)\s*小时")
    high = _unnegated_marker(text, r"996|995|大小周|经常加班|长期加班|周末加班|加班频繁|单休")
    high = high or bool(re.search(r"不双休|无双休|没有双休|不保证双休|不能双休", text))
    return low, high


def _community_evidence(job: Job, scope: dict[str, str], chunks: list[dict[str, Any]],
                        config: AgentConfig) -> list[dict[str, Any]]:
    if not config.knowledge.enabled or not scope["role_family"] or scope["employment_type"] == "unknown":
        return []
    company = _canonical_company(job.company, config)
    now = datetime.now(timezone.utc)
    candidates = []
    for chunk in chunks:
        if (chunk["source"] not in config.knowledge.allowed_sources
                or _canonical_company(str(chunk["company"]), config) != company
                or chunk["role_family"] != scope["role_family"]
                or chunk["employment_type"] != scope["employment_type"]
                or chunk["topic"] == "interview"):
            continue
        published = _date(chunk["published_at"])
        if published is None or published > now or (now - published).days > config.knowledge.max_age_days:
            continue
        dimensions = _dimensions(str(chunk["text"]))
        if not dimensions:
            continue
        document_id = int(chunk["document_id"])
        unit = str(chunk["business_unit"] or "")
        city = str(chunk["city"] or "")
        if unit and scope["business_unit"] and unit != scope["business_unit"]:
            continue
        if city and scope["city"] and city != scope["city"]:
            continue
        direct = bool(unit and scope["business_unit"] and unit == scope["business_unit"]
                      and city and scope["city"] and city == scope["city"])
        limitations = ["社区个人样本，未经该岗位 HR 确认，不代表团队所有人"]
        if not direct:
            limitations.append("团队或城市未完整对齐，仅作背景，不能当作本岗位事实")
        candidates.append({
            "id": f"community:{chunk['chunk_id']}", "type": "community", "source": chunk["source"],
            "source_label": {"nowcoder": "牛客社区", "xiaohongshu": "小红书社区", "manual": "手动导入"}.get(chunk["source"], chunk["source"]),
            "url": chunk["source_url"], "title": chunk["title"], "date": chunk["published_at"],
            "scope": {"company": chunk["company"], "role_family": chunk["role_family"],
                      "employment_type": chunk["employment_type"], "business_unit": unit, "city": city},
            "excerpt": chunk["text"], "relevance": "direct" if direct else "context",
            "limitations": limitations, "dimensions": dimensions, "document_id": document_id,
        })
    # Scope fit comes before quality: broad high-quality background cannot crowd
    # out the only directly aligned sample before the output limit is applied.
    candidates.sort(key=lambda item: 0 if item["relevance"] == "direct" else 1)
    selected: list[dict[str, Any]] = []
    per_document: dict[int, int] = {}
    for item in candidates:
        document_id = item["document_id"]
        if per_document.get(document_id, 0) >= config.knowledge.max_chunks_per_document:
            continue
        selected.append(item)
        per_document[document_id] = per_document.get(document_id, 0) + 1
        if len(selected) >= 12:
            break
    return selected


def _make_card(row: dict[str, Any], config: AgentConfig, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    job_fields = {key: row[key] for key in Job.__dataclass_fields__ if key in row}
    job_fields["metadata"] = _json(row.get("metadata_json"), {})
    job = Job(**job_fields)
    scope = _job_scope(job, config)
    evidence: list[dict[str, Any]] = []

    def jd(text: str, dimension: str) -> list[str]:
        for item in evidence:
            if item["type"] == "jd" and item["excerpt"] == text:
                if dimension not in item["dimensions"]:
                    item["dimensions"].append(dimension)
                return [item["id"]]
        identifier = f"jd:{job.id}:{len(evidence) + 1}"
        inference = text.startswith("岗位规则核对：")
        evidence.append({"id": identifier, "type": "jd", "source": job.source,
                         "source_label": "岗位字段与本地规则核对" if inference else "招聘页 / JD",
                         "inference": inference, "url": job.url, "title": job.title,
                         "date": job.published_at, "scope": dict(scope), "excerpt": text,
                         "relevance": "direct", "limitations": ["招聘页披露，实际执行情况仍需确认"],
                         "dimensions": [dimension]})
        return [identifier]

    reasons: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    questions: list[str] = []
    unknowns: list[str] = []
    degree, degree_kind, degree_excerpt = _education_requirement(job)
    candidate_degree, _ = _education(config.candidate.education, structured=True)
    checked = replace(job, education=degree if degree_kind == "required" else "")
    hard_reasons = hard_filter(checked, config)
    unit = _salary_unit(job)
    hard_reasons = [reason for reason in hard_reasons if reason not in {"薪资上限低于最低期望", "薪资未披露"}]
    bounds_valid = ((job.salary_min is None or job.salary_min > 0)
                    and (job.salary_max is None or job.salary_max > 0)
                    and (job.salary_min is None or job.salary_max is None or job.salary_min <= job.salary_max))
    if config.preferences.minimum_salary:
        if unit == "month" and bounds_valid and job.salary_max is not None and job.salary_max < config.preferences.minimum_salary:
            hard_reasons.append("薪资上限低于最低期望")
        elif config.preferences.unknown_field_policy == "reject":
            if unit != "month":
                hard_reasons.append("薪资月度口径未披露")
            elif not bounds_valid or (job.salary_min is None and job.salary_max is None):
                hard_reasons.append("薪资未披露或区间异常")
    # Re-evaluate education with normalized candidate degree, never the old evaluation row.
    hard_reasons = [reason for reason in hard_reasons if reason != "学历硬条件不满足"]
    education_ids = jd(degree_excerpt, "eligibility") if degree_excerpt else []
    if degree_kind == "required":
        if not candidate_degree:
            unknowns.append("当前档案学历缺失，无法核对学历门槛")
        elif EDUCATION_LEVEL.get(candidate_degree, 0) < EDUCATION_LEVEL.get(degree, 0):
            hard_reasons.append(f"学历硬条件不满足：要求{degree}，当前档案为{candidate_degree}")
        else:
            reasons.append({"text": f"学历符合 JD 已披露的{degree}门槛", "evidence_ids": education_ids})
    elif degree_kind == "preferred":
        unknowns.append(f"{degree_excerpt}是偏好条件，需确认实际筛选方式")
    elif degree_kind == "unknown":
        unknowns.append("岗位未明确披露学历门槛")
    if scope["employment_type"] == "unknown":
        unknowns.append("用工类型未明确，无法对齐社区体验样本")
    for text in ("专业及毕业时间要求需要核对", "ATS 表单与提交资格尚未验证"):
        unknowns.append(text)
    # A prior rule evaluation can be stale after a profile/preference update.
    if row.get("status") in {JobStatus.DUPLICATE.value, JobStatus.EXPIRED.value}:
        hard_reasons.append(f"岗位池状态：{row['status']}")
    hard_reasons = list(dict.fromkeys(hard_reasons))
    eligibility_status = "blocked" if hard_reasons else "verify" if degree_kind == "unknown" or not candidate_degree or scope["employment_type"] == "unknown" else "eligible"

    required = _extract_required_skills(job, config.candidate.skills)
    candidate_skills = {skill.lower() for skill in config.candidate.skills}
    matched = [skill for skill in required if skill.lower() in candidate_skills]
    missing = [skill for skill in required if skill.lower() not in candidate_skills]
    ability_score = round(100 * len(matched) / len(required)) if required and candidate_skills else None
    ability_label = "技能待核实" if ability_score is None else "已知技能较匹配" if ability_score >= 80 else "有能力缺口"
    skill_ids = list(dict.fromkeys(identifier for sentence in _sentences(job.description)
                                  if any(contains_skill(sentence, skill) for skill in required)
                                  for identifier in jd(sentence, "ability")))
    if required and not skill_ids:
        skill_ids = jd("岗位规则核对：结构化技能字段 " + "、".join(required), "ability")
    if matched:
        reasons.append({"text": f"当前档案覆盖 {len(matched)}/{len(required)} 项 JD 技能线索：{'、'.join(matched[:5])}", "evidence_ids": skill_ids})
    if missing:
        risks.append({"text": "档案尚未体现：" + "、".join(missing[:6]) + "；需核实是否必需及可用项目弥补", "evidence_ids": skill_ids})
    minimum, _ = _parse_experience(job)
    if minimum is not None and minimum > config.candidate.years_experience:
        risks.append({"text": f"JD 经验线索至少 {minimum:g} 年，当前档案 {config.candidate.years_experience:g} 年；需确认是否可放宽", "evidence_ids": jd(f"经验要求：{job.experience_min if job.experience_min is not None else job.description}", "ability")})

    community = _community_evidence(job, scope, chunks, config)
    evidence.extend(community)
    fields = [{"key": key, "label": label, "value": "未披露", "status": "unknown", "evidence_ids": []}
              for key, label in COMPENSATION_FIELDS.items()]
    by_key = {field["key"]: field for field in fields}
    lower, upper = job.salary_min, job.salary_max
    salary_label = "薪资未披露"
    salary_status = "unknown"
    if lower is not None or upper is not None:
        amount = f"{lower:,}–{upper:,}" if lower is not None and upper is not None else f"≥ {lower:,}" if lower is not None else f"≤ {upper:,}"
        suffix = {"month": "元/月", "day": "元/日", "year": "元/年", "unknown": "（口径待核实）"}[unit]
        salary_label = amount + suffix
        salary_status = "known" if lower is not None and upper is not None and unit != "unknown" and bounds_valid else "partial"
        if not bounds_valid:
            salary_label += "（区间异常，待核实）"
        salary_excerpt = str(job.metadata.get("salary_text") or f"招聘页薪资字段：下限 {lower if lower is not None else '未披露'}，上限 {upper if upper is not None else '未披露'}；单位 {unit}")
        by_key["fixed_salary"].update(value=salary_label, status=salary_status, evidence_ids=jd(salary_excerpt, "compensation"))
    else:
        questions.append("这个岗位固定薪资区间及计薪口径是什么？")
    preference_reasons = 0
    expectation = config.preferences.minimum_salary
    if expectation:
        if unit != "month":
            risks.append({"text": "月薪口径未确认，不能判断是否达到你的最低薪资期望", "evidence_ids": by_key["fixed_salary"]["evidence_ids"]})
            questions.append(f"固定月薪保底能否达到 {expectation:,} 元？实习如按日计薪，请确认每月计薪天数。")
        elif bounds_valid and lower is not None and lower >= expectation:
            reasons.append({"text": f"披露的固定月薪下限达到你的 {expectation:,} 元最低期望", "evidence_ids": by_key["fixed_salary"]["evidence_ids"]})
            preference_reasons += 1
        elif bounds_valid and upper is not None and upper < expectation:
            risks.append({"text": f"披露月薪上限低于你的 {expectation:,} 元最低期望", "evidence_ids": by_key["fixed_salary"]["evidence_ids"]})
        else:
            risks.append({"text": "仅上限或部分区间可能达到期望，保底月薪尚未满足或无法确认", "evidence_ids": by_key["fixed_salary"]["evidence_ids"]})
            questions.append(f"能否确认固定月薪保底至少 {expectation:,} 元，而不是仅区间上限？")
    if unit == "unknown" and (lower is not None or upper is not None):
        questions.append("这个薪资数字按月、按日还是按年计算？")

    groups: list[dict[str, Any]] = []
    all_facts: dict[str, list[dict[str, Any]]] = {}
    for key, (label, absent, _) in EXPERIENCE.items():
        facts = []
        for sentence in _sentences(job.description):
            if key in _dimensions(sentence):
                facts.append({"text": "JD 披露：" + sentence, "evidence_ids": jd(sentence, key)})
        for item in community:
            if item["relevance"] == "direct" and key in item["dimensions"]:
                facts.append({"text": "同作用域社区样本：" + item["excerpt"], "evidence_ids": [item["id"]]})
        all_facts[key] = facts
        groups.append({"key": key, "label": label, "status": "partial" if facts else "unknown",
                       "summary": f"有 {len(facts)} 条披露/样本，实际情况待确认" if facts else "暂无本岗位可信事实",
                       "facts": facts[:3], "unknowns": [f"{item}待确认" for item in absent]})
    for field_key, pattern in COMPENSATION_PATTERNS.items():
        statements = [(sentence, jd(sentence, "compensation")) for sentence in _sentences(job.description)
                      if re.search(pattern, sentence, re.I) and "compensation" in _dimensions(sentence)]
        statements.extend((item["excerpt"], [item["id"]]) for item in community if item["relevance"] == "direct"
                          and re.search(pattern, item["excerpt"], re.I) and "compensation" in item["dimensions"])
        if statements:
            by_key[field_key].update(value="；".join(text for text, _ in statements[:2]), status="partial",
                                     evidence_ids=list(dict.fromkeys(identifier for _, ids in statements for identifier in ids)))

    if config.preferences.locations and any(location.lower() in job.location.lower() for location in config.preferences.locations):
        reasons.append({"text": f"工作地点 {job.location} 符合你的城市选择", "evidence_ids": jd("工作地点：" + job.location, "eligibility")})
        preference_reasons += 1
    # Only explicit aligned facts can support a preference; no anonymous company stereotype.
    preference_conflict = False
    time_positive = [fact for fact in all_facts["time"] if _time_polarity(fact["text"])[0]]
    time_negative = [fact for fact in all_facts["time"] if _time_polarity(fact["text"])[1]]
    time_conflict = bool(time_positive and time_negative)
    if time_conflict:
        preference_conflict = True
        risks.append({"text": "工时线索同时出现双休/低工时和高强度或加班，证据有冲突，实际安排需向团队确认",
                      "evidence_ids": list(dict.fromkeys(identifier for fact in time_positive + time_negative for identifier in fact["evidence_ids"]))})
    for group in groups:
        growth_negative = any(_growth_gap(fact["text"])
                              for fact in all_facts["growth"])
        for fact in all_facts[group["key"]]:
            text = fact["text"]
            if group["key"] == "time" and config.preferences.workload_preference == "low_intensity":
                low, high = _time_polarity(text)
                if low and not high and not time_conflict:
                    reasons.append({"text": "现有披露/样本有双休或低工时线索，符合你偏好的较低强度；需确认实际执行", "evidence_ids": fact["evidence_ids"]})
                    preference_reasons += 1
                if high:
                    risks.append({"text": "现有披露/样本出现较高工时线索，与较低强度偏好冲突", "evidence_ids": fact["evidence_ids"]})
                    preference_conflict = True
            if group["key"] == "growth" and config.preferences.growth_priority == "high" and not growth_negative and _unnegated_marker(text, r"导师|培训|培养计划"):
                reasons.append({"text": "有导师或培训线索，支持你的成长优先偏好；培养质量仍需确认", "evidence_ids": fact["evidence_ids"]})
                preference_reasons += 1
            if group["key"] == "growth" and config.preferences.growth_priority == "high" and _growth_gap(text):
                risks.append({"text": "现有披露/样本明确缺少导师或培训，与成长优先偏好冲突", "evidence_ids": fact["evidence_ids"]})
                preference_conflict = True
            if group["key"] == "stability" and _unnegated_marker(text, r"裁员|业务收缩|hc\s*冻结"):
                risks.append({"text": "同作用域披露/样本出现稳定性风险，需要核实当前团队与 HC", "evidence_ids": fact["evidence_ids"]})
                if config.preferences.stability_priority == "high":
                    preference_conflict = True
    for reason in hard_reasons:
        ids = education_ids if "学历" in reason else []
        risks.insert(0, {"text": reason, "evidence_ids": ids})
    unknown_dimensions = [group["label"] for group in groups if not group["facts"]]
    if unknown_dimensions:
        risks.append({"text": "以下体验尚无本岗位可信事实：" + "、".join(unknown_dimensions), "evidence_ids": []})
    if salary_status == "unknown":
        risks.append({"text": "薪资未披露，不能估算年现金收入、总包或有效时薪", "evidence_ids": []})
    questions.extend(["这个岗位所属团队、用工类型、专业和毕业时间的硬要求是什么？",
                      "实际平均下班时间、周末加班频率以及值班安排如何？",
                      "发薪月数、奖金兑现、五险一金基数和试用期待遇分别是什么？"])
    direct_experience = sum(1 for item in community if item["relevance"] == "direct")
    important_unknown = (salary_status != "known" or eligibility_status != "eligible"
                         or (expectation is not None and unit != "month")
                         or (expectation is not None and (lower is None or lower < expectation))
                         or not groups[0]["facts"]
                         or (config.preferences.growth_priority == "high" and not groups[4]["facts"])
                         or (config.preferences.stability_priority == "high" and not groups[-1]["facts"]))
    decision_status = "not_recommended" if hard_reasons else "recommend" if preference_reasons >= 2 and not important_unknown and not preference_conflict and (ability_score or 0) >= 80 else "verify"
    labels = {"recommend": "优先了解", "verify": "核实后再投", "not_recommended": "暂不推荐"}
    summary = "存在明确门槛或岗位池过滤状态，保留原因供核对" if hard_reasons else "已知条件与偏好有证据支撑，确认实际待遇和提交资格后可推进" if decision_status == "recommend" else "已有部分匹配线索，关键待遇、门槛或体验仍待确认"
    evidence_summary = {"direct": sum(item["relevance"] == "direct" for item in evidence),
                        "context": sum(item["relevance"] == "context" for item in evidence),
                        "uncertain": sum(item["relevance"] == "uncertain" for item in evidence),
                        "documents": len({item["document_id"] for item in community}),
                        "experience_direct": direct_experience,
                        "label": "有同作用域社区样本" if direct_experience else "仅 JD 与背景，体验待核实",
                        "unknown_dimensions": unknown_dimensions}
    return {"job_id": job.id, "title": job.title, "company": job.company, "location": job.location,
            "source": job.source, "url": job.url, "apply_url": job.apply_url or job.url,
            "is_demo": job.source == "demo" or job.metadata.get("is_demo") is True or job.metadata.get("demo") is True,
            "job_status": row.get("status", ""), "decision": {"status": decision_status, "label": labels[decision_status], "summary": summary},
            "eligibility": {"status": eligibility_status, "label": {"blocked": "已知条件不通过", "verify": "门槛待核实", "eligible": "已知门槛通过"}[eligibility_status],
                            "reasons": hard_reasons, "unknowns": unknowns},
            "ability": {"label": ability_label, "matched": matched, "missing": missing, "score": ability_score,
                        "summary": "仅按当前档案与 JD 技能线索核对，不代表面试或录用概率"},
            "compensation": {"label": salary_label, "status": salary_status, "unit": unit, "fields": fields},
            "experience": groups, "reasons": reasons, "risks": risks, "questions": list(dict.fromkeys(questions)),
            "evidence": evidence, "evidence_summary": evidence_summary,
            "ranking_basis": {"preference_supports": preference_reasons, "experience_direct": direct_experience,
                              "unknown_fields": len(unknown_dimensions) + int(salary_status != "known")},
            "default_visible": not hard_reasons}


def build_recommendations(database_path: str | Path, config: AgentConfig) -> dict[str, Any]:
    rows, chunks = _read_current(Path(database_path))
    cards = [_make_card(row, config, chunks) for row in rows]
    eligibility_order = {"eligible": 0, "verify": 1, "blocked": 2}
    cards.sort(key=lambda card: (
        eligibility_order[card["eligibility"]["status"]],
        0 if card["decision"]["status"] == "recommend" else 1,
        -card["ranking_basis"]["preference_supports"], -card["ranking_basis"]["experience_direct"],
        -(card["ability"]["score"] or 0), card["ranking_basis"]["unknown_fields"], -int(card["job_id"]),
    ))
    return {"items": cards, "summary": {"total": len(cards),
            "recommended": sum(card["decision"]["status"] == "recommend" for card in cards),
            "verify": sum(card["decision"]["status"] == "verify" for card in cards),
            "excluded": sum(not card["default_visible"] for card in cards),
            "evidence_supported": sum(card["evidence_summary"]["experience_direct"] > 0 for card in cards)},
            "generated_at": utc_now(), "method": "local_rules",
            "policy": {"read_only": True, "paid_model_called": False, "unknown_is_not_positive": True,
                       "context_is_not_job_fact": True, "ranking_uses_company_prestige": False}}
