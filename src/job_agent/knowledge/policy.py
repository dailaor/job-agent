from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from ..config import KnowledgeSettings
from ..models import normalize_text
from .models import EmploymentType, PolicyDecision, PolicyStatus, PostDocument, normalize_employment_type


TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "duties": ("负责", "日常", "工作内容", "主要做", "需求", "项目", "职责", "业务"),
    "skills": ("技能", "要求", "sql", "python", "java", "golang", "模型", "数据分析", "实验", "技术栈"),
    "interview": (
        "面试", "笔试", "一面", "二面", "三面", "初试", "复试", "意向面", "业务面",
        "主管面", "hr面", "hr 面", "面经", "招聘流程", "考察", "追问",
    ),
    "workload": ("加班", "下班", "工作强度", "大小周", "996", "995", "作息", "工时"),
    "compensation": ("薪资", "工资", "年终奖", "奖金", "补贴", "福利", "总包", "base", "股票"),
    "culture": ("氛围", "领导", "老板", "同事", "管理", "汇报", "团队", "沟通"),
    "growth": ("成长", "晋升", "发展", "学习", "导师", "转岗", "职业路径"),
    "stability": ("裁员", "稳定", "组织调整", "业务收缩", "业务增长", "转正", "hc", "headcount"),
    "work_style": ("出差", "远程", "混合办公", "坐班", "办公地点", "通勤", "城市"),
}

# When one clause contains both interview subject matter (for example “业务、项目”)
# and an explicit stage name, the stage is the stronger signal for chunk routing.
TOPIC_STRONG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "interview": (
        "面试", "笔试", "一面", "二面", "三面", "初试", "复试", "意向面", "业务面",
        "主管面", "hr面", "hr 面", "面经", "招聘流程",
    ),
    "workload": ("工作强度", "加班", "大小周", "996", "995", "工时"),
    "compensation": ("薪资", "工资", "总包", "年终奖", "奖金", "股票"),
}

SHELL_MARKERS = (
    "加载中，请稍候", "登录探索更多内容", "请先登录", "安全验证", "访问过于频繁",
    "captcha", "enable javascript", "页面不存在", "404 not found",
)
PROMOTIONAL_MARKERS = ("加微信", "付费咨询", "课程报名", "内推码", "扫码咨询", "私聊发链接")

SOURCE_HOSTS = {
    "nowcoder": ("nowcoder.com",),
    "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
}

INTERNSHIP_MARKERS = (
    "实习", "暑期实习", "日常实习", "暑期项目", "intern", "internship",
)
FULL_TIME_MARKERS = (
    "正职", "全职", "校招", "秋招", "春招", "社招", "应届生", "正式员工", "在职", "full-time",
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def redact_personal_data(text: str) -> str:
    text = re.sub(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)", "[手机号已隐藏]", text)
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[邮箱已隐藏]", text)
    text = re.sub(
        r"(?im)^(?:微信|vx|wechat|联系方式)\s*[:：]?\s*[A-Za-z][A-Za-z0-9_-]{5,19}\s*$",
        "[联系方式已隐藏]",
        text,
    )
    return text.strip()


class DocumentPolicy:
    """Deterministic admission gate; rejected text is never embedded."""

    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings

    def canonical_company(self, value: str) -> str:
        lowered = normalize_text(value).lower()
        for company, aliases in self.settings.company_aliases.items():
            if any(alias.lower() in lowered for alias in aliases):
                return company
        return ""

    def detect_company(self, document: PostDocument) -> str:
        explicit = self.canonical_company(document.company)
        if explicit:
            return explicit
        return self.canonical_company(f"{document.title} {document.content}")

    def detect_role_family(self, document: PostDocument) -> str:
        if document.role_family in self.settings.role_families:
            return document.role_family
        lowered = f"{document.title} {document.content}".lower()
        scores = {
            family: sum(lowered.count(alias.lower()) for alias in aliases if alias.strip())
            for family, aliases in self.settings.role_families.items()
        }
        best = max(scores, key=scores.get, default="")
        return best if best and scores[best] > 0 else ""

    @staticmethod
    def detect_employment_type(document: PostDocument) -> EmploymentType:
        explicit = normalize_employment_type(document.employment_type)
        if explicit is not EmploymentType.UNKNOWN:
            return explicit
        lowered = f"{document.title} {document.seniority} {document.content}".lower()
        internship = any(marker in lowered for marker in INTERNSHIP_MARKERS)
        full_time = any(marker in lowered for marker in FULL_TIME_MARKERS)
        if internship == full_time:
            return EmploymentType.UNKNOWN
        return EmploymentType.INTERNSHIP if internship else EmploymentType.FULL_TIME

    @staticmethod
    def detect_topics(text: str) -> list[str]:
        lowered = text.lower()
        return [topic for topic, keywords in TOPIC_KEYWORDS.items() if any(keyword in lowered for keyword in keywords)]

    def evaluate(self, document: PostDocument) -> PolicyDecision:
        reasons: list[str] = []
        review_reasons: list[str] = []
        sanitized = redact_personal_data(document.content)
        lowered = f"{document.title} {sanitized}".lower()
        company = self.detect_company(document)
        role_family = self.detect_role_family(document)
        employment_type = self.detect_employment_type(document)
        topics = self.detect_topics(sanitized)

        if document.source not in self.settings.allowed_sources:
            reasons.append("来源不在知识库白名单")
        parsed_url = urlparse(document.url)
        if parsed_url.scheme != "https" or not parsed_url.hostname:
            reasons.append("来源必须是可追溯的 HTTPS 链接")
        allowed_hosts = SOURCE_HOSTS.get(document.source)
        if allowed_hosts and not any(
            parsed_url.hostname == host or parsed_url.hostname.endswith(f".{host}") for host in allowed_hosts
        ):
            reasons.append("来源链接与声明的平台不一致")
        if document.source == "xiaohongshu" and document.collection_method not in {"manual_import", "browser_visible"}:
            reasons.append("小红书只接受人工导入或用户登录后可见页面导入")
        if document.source == "nowcoder" and document.collection_method not in {
            "manual_import", "browser_visible", "public_html"
        }:
            reasons.append("牛客采集方式不受支持")
        if any(marker.lower() in lowered for marker in SHELL_MARKERS):
            reasons.append("内容是登录、验证码、加载壳或错误页")
        if len(sanitized) < self.settings.min_document_chars:
            reasons.append("正文过短，缺少可验证岗位信息")
        if len(sanitized) > self.settings.max_document_chars:
            reasons.append("正文超过单篇文档上限")
        if not company:
            reasons.append("无法对齐到首批目标公司")
        if not role_family:
            reasons.append("无法对齐到首批目标岗位族")
        if employment_type is EmploymentType.UNKNOWN:
            reasons.append("无法唯一确认是正职还是实习，禁止混入向量索引")
        if not topics:
            reasons.append("未发现能影响岗位决策的事实主题")
        promotional_hits = sum(lowered.count(marker) for marker in PROMOTIONAL_MARKERS)
        if promotional_hits >= 2 and len(topics) <= 1:
            reasons.append("内容主要是引流、付费咨询或内推广告")

        published = _parse_datetime(document.published_at)
        if document.published_at and published is None:
            review_reasons.append("发布时间格式无法确认")
        elif published is None:
            review_reasons.append("缺少发布时间")
        else:
            age_days = max(0, (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).days)
            if age_days > self.settings.max_age_days:
                reasons.append(f"帖子超过 {self.settings.max_age_days} 天有效期")

        if reasons:
            status = PolicyStatus.REJECTED
        elif review_reasons:
            status = PolicyStatus.NEEDS_REVIEW
        else:
            status = PolicyStatus.ACCEPTED

        quality = 0.35
        quality += min(0.15, len(sanitized) / max(1, self.settings.max_document_chars) * 1.5)
        quality += min(0.20, len(topics) * 0.04)
        quality += 0.10 if document.business_unit else 0
        quality += 0.05 if employment_type is not EmploymentType.UNKNOWN else 0
        quality += 0.10 if published else 0
        quality += 0.10 if re.search(r"我在|本人|入职|实习期间|面试过|亲历", sanitized) else 0
        if status is PolicyStatus.NEEDS_REVIEW:
            quality = min(quality, 0.59)
        if status is PolicyStatus.REJECTED:
            quality = 0

        return PolicyDecision(
            status=status,
            reasons=reasons + review_reasons,
            company=company,
            role_family=role_family,
            employment_type=employment_type,
            topics=topics,
            quality_score=round(min(1.0, quality), 3),
            sanitized_content=sanitized,
        )
