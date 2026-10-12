from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .models import EmploymentType, KnowledgeChunk, PostDocument, normalize_employment_type
from .policy import TOPIC_KEYWORDS, TOPIC_STRONG_KEYWORDS


@dataclass(slots=True)
class _Sentence:
    text: str
    start: int
    end: int
    topic: str


class PostChunker:
    """One post is one parent document; child chunks contain one decision topic."""

    def __init__(self, *, min_chars: int = 50, max_chars: int = 320) -> None:
        self.min_chars = min_chars
        self.max_chars = max_chars

    @staticmethod
    def _topic(text: str) -> str:
        lowered = text.lower()
        for topic, keywords in TOPIC_STRONG_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return topic
        scored = {
            topic: sum(lowered.count(keyword) for keyword in keywords)
            for topic, keywords in TOPIC_KEYWORDS.items()
        }
        best = max(scored, key=scored.get, default="")
        return best if best and scored[best] > 0 else "general"

    def _sentences(self, content: str) -> list[_Sentence]:
        results: list[_Sentence] = []
        for match in re.finditer(r"[^。！？!?；;\n]+[。！？!?；;]?|[^\n]+$", content):
            text = match.group(0).strip()
            if not text:
                continue
            if len(text) > self.max_chars:
                cursor = match.start()
                for part in re.split(r"(?<=[，、,：:])", text):
                    part = part.strip()
                    if not part:
                        continue
                    start = content.find(part, cursor, match.end())
                    start = cursor if start < 0 else start
                    results.append(_Sentence(part, start, start + len(part), self._topic(part)))
                    cursor = start + len(part)
            else:
                results.append(_Sentence(text, match.start(), match.end(), self._topic(text)))
        return results

    @staticmethod
    def _context_prefix(
        document: PostDocument,
        company: str,
        role_family: str,
        employment_type: EmploymentType,
        topic: str,
    ) -> str:
        fields = [
            f"公司={company}", f"岗位族={role_family}", f"用工类型={employment_type.value}",
            f"来源={document.source}", f"主题={topic}",
        ]
        for label, value in (
            ("业务线", document.business_unit), ("级别", document.seniority),
            ("城市", document.city), ("发布时间", document.published_at or ""),
        ):
            if value:
                fields.append(f"{label}={value}")
        return "[" + "｜".join(fields) + "]"

    def split(
        self,
        document: PostDocument,
        *,
        content: str,
        company: str,
        role_family: str,
        employment_type: EmploymentType | str | None = None,
    ) -> list[KnowledgeChunk]:
        scoped_employment_type = normalize_employment_type(employment_type or document.employment_type)
        sentences = self._sentences(content)
        chunks: list[KnowledgeChunk] = []
        current: list[_Sentence] = []
        current_topic = ""

        def flush() -> None:
            nonlocal current, current_topic
            if not current or current_topic == "general":
                current = []
                current_topic = ""
                return
            text = "".join(item.text for item in current).strip()
            if len(text) < self.min_chars and chunks and chunks[-1].topic == current_topic:
                prior = chunks[-1]
                merged = prior.text + text
                if len(merged) <= self.max_chars:
                    prior.text = merged
                    prior.contextual_text = self._context_prefix(
                        document, company, role_family, scoped_employment_type, current_topic,
                    ) + "\n" + merged
                    prior.end_offset = current[-1].end
                    prior.chunk_hash = hashlib.sha256(prior.contextual_text.encode("utf-8")).hexdigest()
                    current = []
                    current_topic = ""
                    return
            prefix = self._context_prefix(document, company, role_family, scoped_employment_type, current_topic)
            contextual = f"{prefix}\n{text}"
            chunks.append(KnowledgeChunk(
                ordinal=len(chunks),
                topic=current_topic,
                text=text,
                contextual_text=contextual,
                start_offset=current[0].start,
                end_offset=current[-1].end,
                chunk_hash=hashlib.sha256(contextual.encode("utf-8")).hexdigest(),
            ))
            current = []
            current_topic = ""

        for sentence in sentences:
            topic = sentence.topic
            if topic == "general" and current:
                topic = current_topic
            projected = sum(len(item.text) for item in current) + len(sentence.text)
            if current and (topic != current_topic or projected > self.max_chars):
                flush()
            if topic != "general":
                current_topic = topic
                current.append(sentence)
        flush()
        return chunks
