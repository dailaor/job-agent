from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


SKILL_UNIVERSE = (
    "Python", "Java", "Go", "C++", "JavaScript", "TypeScript", "SQL", "Excel",
    "Tableau", "Power BI", "Figma", "Axure", "数据分析", "需求分析", "用户研究",
    "A/B测试", "机器学习", "深度学习", "NLP", "LLM", "大模型", "项目管理",
    "产品设计", "增长", "运营", "英语", "市场分析", "商业分析", "原型设计",
)
EDUCATION_ORDER = ("高中", "大专", "本科", "硕士", "博士")
MAX_DOCX_XML_BYTES = 8 * 1024 * 1024


@dataclass(slots=True)
class ResumeProfile:
    skills: list[str]
    years_experience: float | None
    education: str | None


def _clean_text(value: str) -> str:
    value = value.replace("\x00", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)[:100_000]


def contains_skill(text: str, skill: str) -> bool:
    """Match Latin skill tokens without treating JavaScript as Java or Google as Go."""

    if re.fullmatch(r"[A-Za-z0-9+#. /-]+", skill):
        return re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(skill)}(?![A-Za-z0-9_])",
            text,
            flags=re.IGNORECASE,
        ) is not None
    return skill.lower() in text.lower()


def extract_resume_text(suffix: str, content: bytes) -> str:
    """Validate a resume container and return locally extracted text when possible."""

    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("文件扩展名是 PDF，但内容不是有效或可读取的 PDF")
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted and reader.decrypt("") == 0:
                raise ValueError("PDF 已加密，无法读取内容")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("文件扩展名是 PDF，但内容不是有效或可读取的 PDF") from exc
        return _clean_text(text)

    if suffix != ".docx":
        raise ValueError("仅支持 PDF 或 DOCX 简历")
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise ValueError("DOCX 缺少必要的 Word 文档结构")
            if archive.getinfo("word/document.xml").file_size > MAX_DOCX_XML_BYTES:
                raise ValueError("DOCX 正文结构过大，无法安全读取")
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
    except ValueError:
        raise
    except (BadZipFile, ElementTree.ParseError) as exc:
        raise ValueError("文件扩展名是 DOCX，但内容不是有效的 Word 文档") from exc
    text = "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    return _clean_text(text)


def infer_resume_profile(text: str) -> ResumeProfile:
    skills = sorted({skill for skill in SKILL_UNIVERSE if contains_skill(text, skill)}, key=str.lower)

    year_values: list[float] = []
    for pattern in (
        r"(\d+(?:\.\d+)?)\s*年(?:以上)?(?:的)?(?:工作|从业)?经验",
        r"工作年限\s*[:：]?\s*(\d+(?:\.\d+)?)\s*年",
    ):
        year_values.extend(float(value) for value in re.findall(pattern, text, flags=re.IGNORECASE))
    years = max(year_values) if year_values else None

    education = None
    for value in EDUCATION_ORDER:
        if value in text:
            education = value
    return ResumeProfile(skills=skills, years_experience=years, education=education)
