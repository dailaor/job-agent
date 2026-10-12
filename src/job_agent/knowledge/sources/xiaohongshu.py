from __future__ import annotations

from urllib.parse import urlparse

from ..models import SourceFetchResult, SourceStatus


class XiaohongshuBrowserSource:
    """Explicitly refuses direct crawling; import only text visible in the user's logged-in browser."""

    id = "xiaohongshu"

    def fetch(self, url: str) -> SourceFetchResult:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not any(
            host == allowed or host.endswith(f".{allowed}") for allowed in ("xiaohongshu.com", "xhslink.com")
        ):
            return SourceFetchResult(SourceStatus.PORTAL_UNPARSED, "链接不是小红书 HTTPS 页面")
        return SourceFetchResult(
            SourceStatus.AUTH_REQUIRED,
            "小红书不执行直接爬取。请用户自行登录并导入当前可见正文；系统不接收 Cookie、Token 或密码。",
        )
