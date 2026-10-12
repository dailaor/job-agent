from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..models import PostDocument, SourceFetchResult, SourceStatus


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return "\n".join(self.parts)


def _find_content_data(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        candidate = value.get("contentData")
        if isinstance(candidate, dict) and (candidate.get("content") or candidate.get("title")):
            return candidate
        for child in value.values():
            found = _find_content_data(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_content_data(child)
            if found:
                return found
    return None


def _iso_timestamp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat()
    text = str(value).strip()
    if text.isdigit():
        return _iso_timestamp(int(text))
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).isoformat()


class NowcoderPublicSource:
    """Single-page, read-only public fetcher. It never searches, logs in, or bypasses a challenge."""

    id = "nowcoder"
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024
    _lock = threading.Lock()
    _last_fetch_monotonic = 0.0

    def __init__(self, min_interval_seconds: float = 5.0, timeout_seconds: float = 15.0) -> None:
        self.min_interval_seconds = min_interval_seconds
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _valid_url(url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and (
            host == "nowcoder.com" or host.endswith(".nowcoder.com")
        ) and parsed.path.startswith("/discuss/")

    @staticmethod
    def parse_html(url: str, html: str) -> PostDocument:
        marker = re.search(r"window\.__INITIAL_STATE__\s*=\s*", html)
        if marker is None:
            raise ValueError("牛客页面未包含可验证的公开帖子数据")
        segment = html[marker.end():]
        try:
            state, _ = json.JSONDecoder().raw_decode(segment)
        except json.JSONDecodeError as exc:
            raise ValueError("牛客公开帖子数据无法解析") from exc
        content_data = _find_content_data(state)
        if not content_data:
            raise ValueError("牛客页面只有入口或加载壳，未取得帖子正文")

        raw_content = str(content_data.get("content") or content_data.get("contentText") or "")
        extractor = _TextExtractor()
        extractor.feed(raw_content)
        content = extractor.text() if "<" in raw_content and ">" in raw_content else raw_content.strip()
        user = content_data.get("userBrief") if isinstance(content_data.get("userBrief"), dict) else {}
        published = (
            content_data.get("createTime") or content_data.get("publishTime")
            or content_data.get("createTimestamp") or content_data.get("postTime")
        )
        return PostDocument(
            source="nowcoder",
            url=url,
            title=str(content_data.get("title") or "牛客帖子").strip(),
            content=content,
            published_at=_iso_timestamp(published),
            author=str(user.get("nickname") or ""),
            collection_method="public_html",
            source_status=SourceStatus.PUBLIC_FETCHED,
            metadata={"source_content_id": str(content_data.get("id") or "")},
        )

    def _respect_interval(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self.__class__._last_fetch_monotonic
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)
            self.__class__._last_fetch_monotonic = time.monotonic()

    def fetch(self, url: str) -> SourceFetchResult:
        if not self._valid_url(url):
            return SourceFetchResult(SourceStatus.PORTAL_UNPARSED, "仅支持牛客 HTTPS 讨论详情页 /discuss/<id>")
        self._respect_interval()
        request = Request(
            url,
            headers={
                "User-Agent": "LocalJobAgent/0.1 read-only personal knowledge import",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                final_url = response.geturl()
                if not self._valid_url(final_url):
                    return SourceFetchResult(SourceStatus.PORTAL_UNPARSED, "牛客页面跳转到了来源白名单之外")
                payload = response.read(self.MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            status = SourceStatus.ACCESS_LIMITED if exc.code in {403, 429} else SourceStatus.PORTAL_UNPARSED
            return SourceFetchResult(status, f"牛客公开页返回 HTTP {exc.code}；未重试")
        except (URLError, TimeoutError, OSError) as exc:
            return SourceFetchResult(SourceStatus.PORTAL_UNPARSED, f"牛客公开页读取失败：{exc}")
        if len(payload) > self.MAX_RESPONSE_BYTES:
            return SourceFetchResult(SourceStatus.PORTAL_UNPARSED, "牛客页面超过 2 MB 响应上限")
        html = payload.decode("utf-8", errors="replace")
        lowered = html.lower()
        if any(marker in lowered for marker in ("访问过于频繁", "安全验证", "请输入验证码")):
            return SourceFetchResult(SourceStatus.ACCESS_LIMITED, "牛客触发访问限制或验证码；未尝试绕过")
        try:
            document = self.parse_html(final_url, html)
        except ValueError as exc:
            return SourceFetchResult(SourceStatus.PORTAL_UNPARSED, str(exc))
        return SourceFetchResult(SourceStatus.PUBLIC_FETCHED, "已读取单个牛客公开帖子", document)
