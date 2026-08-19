from __future__ import annotations

import asyncio
import hashlib
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from ..models import Job
from . import boss_selectors as selectors
from .base import ActionResult, ActionStatus


ALLOWED_HOSTS = {"www.zhipin.com", "zhipin.com"}


def build_search_url(query: str, city_code: str) -> str:
    if not query.strip() or not city_code.isdigit():
        raise ValueError("A non-empty query and numeric city code are required")
    # Correct route: /web/geek/jobs. /web/geek/job commonly returns a shell.
    return "https://www.zhipin.com/web/geek/jobs?" + urlencode({"query": query.strip(), "city": city_code})


def normalize_boss_url(value: str) -> str:
    absolute = urljoin("https://www.zhipin.com", value)
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError("Only HTTPS BOSS直聘 URLs are allowed")
    return urlunparse(("https", "www.zhipin.com", parsed.path, "", parsed.query, ""))


def boss_job_id(value: str) -> str:
    parsed = urlparse(normalize_boss_url(value))
    security_id = parse_qs(parsed.query).get("securityId", [None])[0]
    if security_id:
        return str(security_id)
    slug = parsed.path.rsplit("/", 1)[-1].removesuffix(".html")
    return slug or hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def parse_salary(value: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s*[Kk]", value)
    if not match:
        return None, None
    return int(float(match.group(1)) * 1000), int(float(match.group(2)) * 1000)


class BossConnector:
    source = "boss"

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.city_code = str(config.get("city_code", "101010100"))
        self.city_name = str(config.get("city_name", ""))
        self.storage_state = Path(str(config.get("storage_state_path", ".job-agent/boss-storage-state.json"))).expanduser()
        self.headless = bool(config.get("headless", False))
        self.navigation_timeout_ms = int(config.get("navigation_timeout_ms", 30_000))
        self.selector_timeout_ms = int(config.get("selector_timeout_ms", 8_000))
        self.minimum_interval = float(config.get("minimum_action_interval_seconds", 8))
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._last_action: float | None = None

    async def __aenter__(self) -> "BossConnector":
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def start(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Install the browser extra: pip install -e .[browser]") from exc
        self.storage_state.parent.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        options: dict[str, Any] = {"locale": "zh-CN"}
        if self.storage_state.exists():
            options["storage_state"] = str(self.storage_state)
        self._context = await self._browser.new_context(**options)
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.selector_timeout_ms)

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._page = self._context = self._browser = self._playwright = None

    async def interactive_login(self, timeout_minutes: int = 5) -> ActionResult:
        await self.start()
        page = self._page
        await page.goto("https://www.zhipin.com/web/user/?ka=header-login", wait_until="domcontentloaded")
        deadline = time.monotonic() + timeout_minutes * 60
        while time.monotonic() < deadline and not page.is_closed():
            if "/web/geek/" in str(page.url) and not any(marker in str(page.url) for marker in selectors.LOGIN_PATH_MARKERS):
                await self._context.storage_state(path=str(self.storage_state))
                return ActionResult(ActionStatus.OK, "登录状态已保存", evidence=str(self.storage_state))
            await page.wait_for_timeout(1000)
        return ActionResult(ActionStatus.NEEDS_HUMAN, "未在时限内检测到登录，请重新运行登录命令")

    async def discover(self, keywords: list[str]) -> list[Job]:
        await self.start()
        jobs: list[Job] = []
        seen: set[str] = set()
        for query in keywords:
            page = self._page
            await page.goto(build_search_url(query, self.city_code), wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
            blocked = await self._blocked(page)
            if blocked:
                raise RuntimeError(blocked.message)
            cards = page.locator(", ".join(selectors.JOB_CARD))
            try:
                await cards.first.wait_for(state="attached", timeout=self.selector_timeout_ms)
            except Exception as exc:
                raise RuntimeError("未提取到真实岗位卡片；页面可能仅为加载壳或选择器已变化") from exc
            limit = int(self.config.get("search_limit_per_keyword", 30))
            for _ in range(8):
                if await cards.count() >= limit:
                    break
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(600)
            for index in range(min(await cards.count(), limit)):
                card = cards.nth(index)
                href = await self._first_attr(card, selectors.JOB_LINK, "href")
                if not href:
                    continue
                url = normalize_boss_url(href)
                source_id = boss_job_id(url)
                if source_id in seen:
                    continue
                title = await self._first_text(card, selectors.JOB_TITLE)
                company = await self._first_text(card, selectors.COMPANY_NAME)
                if not title or not company:
                    continue
                salary_text = await self._first_text(card, selectors.SALARY) or ""
                salary_min, salary_max = parse_salary(salary_text)
                tags = await self._all_text(card, selectors.JOB_TAGS)
                jobs.append(Job(
                    source="boss", source_id=source_id, title=title, company=company,
                    location=await self._first_text(card, selectors.JOB_LOCATION) or self.city_name,
                    url=url, description=await self._first_text(card, selectors.CARD_DESCRIPTION) or "",
                    salary_min=salary_min, salary_max=salary_max,
                    metadata={"query": query, "salary_text": salary_text, "tags": tags},
                ))
                seen.add(source_id)
        if self.config.get("enrich_details", True):
            detail_limit = int(self.config.get("detail_limit", len(jobs)))
            for job in jobs[:detail_limit]:
                try:
                    await self.enrich(job)
                    job.metadata["detail_loaded"] = bool(job.description.strip())
                except Exception as exc:
                    job.metadata["detail_loaded"] = False
                    job.metadata["detail_error"] = str(exc)
            for job in jobs[detail_limit:]:
                job.metadata["detail_loaded"] = False
                job.metadata["detail_error"] = "detail_limit_reached"
        return jobs

    async def enrich(self, job: Job) -> Job:
        await self.start()
        await self._page.goto(normalize_boss_url(job.url), wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
        blocked = await self._blocked(self._page)
        if blocked:
            raise RuntimeError(blocked.message)
        job.description = await self._first_text(self._page, selectors.DETAIL_DESCRIPTION) or job.description
        job.recruiter_name = await self._first_text(self._page, selectors.RECRUITER_NAME)
        job.recruiter_activity = await self._first_text(self._page, selectors.RECRUITER_ACTIVITY)
        return job

    async def send_greeting(self, job: Job, greeting: str, *, live: bool) -> ActionResult:
        if not live:
            return ActionResult(ActionStatus.OK, "演练完成：未向 BOSS 发送消息", evidence=greeting)
        await self.start()
        await self._respect_interval()
        page = self._page
        try:
            await page.goto(normalize_boss_url(job.url), wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
        except Exception as exc:
            return ActionResult(ActionStatus.FAILED, "岗位页面加载失败", details={"error": str(exc)})
        blocked = await self._blocked(page)
        if blocked:
            return blocked
        if await self._first_visible(page, selectors.CONTINUE_CHAT):
            return ActionResult(ActionStatus.ALREADY_DONE, "平台显示已经沟通过", evidence="继续沟通按钮可见")
        button = await self._first_visible(page, selectors.START_CHAT)
        if button is None:
            return ActionResult(ActionStatus.NOT_FOUND, "未找到“立即沟通”按钮")
        side_effect_started = False
        try:
            pages_before = {id(item) for item in self._context.pages}
            await button.click()
            side_effect_started = True
            await page.wait_for_timeout(900)
            page = await self._adopt_new_page(page, pages_before)
            blocked = await self._blocked(page)
            if blocked:
                return ActionResult(ActionStatus.UNVERIFIED, "点击沟通后出现验证或限制，禁止自动重试", details=blocked.to_dict())
            chat_input = await self._first_visible(page, selectors.CHAT_INPUT)
            if chat_input is None:
                return ActionResult(ActionStatus.UNVERIFIED, "已点击沟通但未找到输入框，需人工核验")
            await chat_input.fill(greeting)
            send = await self._first_visible(page, selectors.SEND_BUTTON)
            if send is None:
                return ActionResult(ActionStatus.UNVERIFIED, "消息已填入但未找到发送按钮，需人工核验")
            await send.click()
            self._last_action = time.monotonic()
            await page.wait_for_timeout(1000)
            if not await self._message_visible(page, greeting):
                return ActionResult(ActionStatus.UNVERIFIED, "已点击发送但缺少正向成功证据，禁止自动重试")
            await self._context.storage_state(path=str(self.storage_state))
            return ActionResult(ActionStatus.SUBMITTED, "开场白已发送", evidence=greeting[:120])
        except Exception as exc:
            status = ActionStatus.UNVERIFIED if side_effect_started else ActionStatus.FAILED
            return ActionResult(status, "沟通流程发生异常", details={"error": str(exc)})

    async def check_reply(self, job: Job, greeting: str) -> ActionResult:
        await self.start()
        page = self._page
        await page.goto(normalize_boss_url(job.url), wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
        blocked = await self._blocked(page)
        if blocked:
            return blocked
        button = await self._first_visible(page, selectors.CONTINUE_CHAT)
        if button is None:
            return ActionResult(ActionStatus.NOT_FOUND, "未找到现有会话")
        try:
            pages_before = {id(item) for item in self._context.pages}
            await button.click()
            await page.wait_for_timeout(800)
            page = await self._adopt_new_page(page, pages_before)
            anchor = greeting[:40].strip()
            if not anchor:
                return ActionResult(ActionStatus.NEEDS_HUMAN, "缺少已发送开场白，无法建立回复时间锚点")
            messages = await page.locator(".message-item, .chat-message").evaluate_all(
                """(elements, anchorText) => elements.map((element) => {
                    const classes = String(element.className || '');
                    return {
                      text: String(element.innerText || element.textContent || '').trim(),
                      self: /item-myself|is-self|(?:^|\\s)me(?:\\s|$)/.test(classes),
                      system: /system|notice/.test(classes)
                    };
                })""",
                anchor,
            )
            anchor_index = max(
                (index for index, item in enumerate(messages) if item.get("self") and anchor in str(item.get("text", ""))),
                default=-1,
            )
            if anchor_index < 0:
                return ActionResult(ActionStatus.NEEDS_HUMAN, "无法在会话中确认已发送开场白，不读取旧消息作为回复")
            meaningful = [
                str(item.get("text", "")).strip() for item in messages[anchor_index + 1:]
                if not item.get("self") and not item.get("system") and len(str(item.get("text", "")).strip()) >= 2
            ]
            if not meaningful:
                return ActionResult(ActionStatus.OK, "尚未检测到 HR 有效回复")
            evidence = meaningful[-1][:200]
            return ActionResult(ActionStatus.CONFIRMED, "检测到 HR 有效回复", evidence=evidence)
        except Exception as exc:
            return ActionResult(ActionStatus.FAILED, "读取会话失败", details={"error": str(exc)})

    async def send_resume(self, job: Job, resume_path: str, *, greeting: str, live: bool) -> ActionResult:
        target = Path(resume_path).expanduser()
        if not target.is_file():
            return ActionResult(ActionStatus.NEEDS_HUMAN, "固定简历文件不存在", evidence=str(target))
        if not live:
            return ActionResult(ActionStatus.OK, "演练完成：未发送简历", evidence=target.name)
        reply = await self.check_reply(job, greeting)
        if reply.status is not ActionStatus.CONFIRMED:
            return ActionResult(ActionStatus.NEEDS_HUMAN, "未确认 HR 有效回复，因此不发送简历", details=reply.to_dict())
        page = self._page
        file_input = await self._first_present(page, selectors.FILE_INPUT)
        side_effect_started = False
        try:
            if file_input is not None:
                await file_input.set_input_files(str(target))
                side_effect_started = True
            else:
                button = await self._first_visible(page, selectors.RESUME_BUTTON)
                if button is None:
                    return ActionResult(ActionStatus.NEEDS_HUMAN, "未找到发送简历控件")
                expected_label = str(self.config.get("resume_display_name", "")).strip()
                if not expected_label:
                    return ActionResult(ActionStatus.NEEDS_HUMAN, "平台未暴露文件输入框，需配置 resume_display_name 后才能确认固定简历")
                await button.click()
                side_effect_started = True
                await page.wait_for_timeout(500)
                if not await page.get_by_text(expected_label, exact=False).first.is_visible(timeout=2000):
                    return ActionResult(ActionStatus.UNVERIFIED, "发送简历动作已开始，但无法确认平台选中的是固定简历")
                file_input = await self._first_present(page, selectors.FILE_INPUT)
                if file_input is not None:
                    await file_input.set_input_files(str(target))
            confirm = await self._first_visible(page, selectors.CONFIRM_SEND)
            if confirm is not None:
                await confirm.click()
            await page.wait_for_timeout(1200)
            if not await self._any_visible(page, selectors.ATTACHMENT_EVIDENCE):
                return ActionResult(ActionStatus.UNVERIFIED, "简历发送动作已开始但无法确认成功，禁止自动重试")
            self._last_action = time.monotonic()
            return ActionResult(ActionStatus.SUBMITTED, "固定简历已发送", evidence=target.name)
        except Exception as exc:
            status = ActionStatus.UNVERIFIED if side_effect_started else ActionStatus.FAILED
            return ActionResult(status, "发送简历失败", details={"error": str(exc)})

    async def _blocked(self, page: Any) -> ActionResult | None:
        current = str(page.url)
        if any(marker in current for marker in selectors.LOGIN_PATH_MARKERS):
            return ActionResult(ActionStatus.NEEDS_LOGIN, "BOSS 登录状态失效", evidence=current)
        if await self._any_visible(page, selectors.CAPTCHA):
            return ActionResult(ActionStatus.NEEDS_HUMAN, "BOSS 要求人工完成验证", evidence=current)
        try:
            body = await page.locator("body").inner_text(timeout=2000)
        except Exception:
            body = ""
        if any(text in body for text in selectors.CAPTCHA_TEXT):
            return ActionResult(ActionStatus.NEEDS_HUMAN, "BOSS 要求人工完成验证", evidence=current)
        for text in selectors.DAILY_LIMIT_TEXT:
            if text in body:
                return ActionResult(ActionStatus.LIMIT_REACHED, text)
        return None

    async def _respect_interval(self) -> None:
        if self._last_action is None:
            return
        remaining = self.minimum_interval - (time.monotonic() - self._last_action)
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def _adopt_new_page(self, current: Any, pages_before: set[int]) -> Any:
        new_pages = [item for item in self._context.pages if id(item) not in pages_before]
        if not new_pages:
            return current
        page = new_pages[-1]
        await page.wait_for_load_state("domcontentloaded")
        page.set_default_timeout(self.selector_timeout_ms)
        self._page = page
        return page

    @staticmethod
    async def _first_visible(root: Any, candidates: tuple[str, ...]) -> Any | None:
        for selector in candidates:
            try:
                locator = root.locator(selector).first
                if await locator.is_visible(timeout=1000):
                    return locator
            except Exception:
                continue
        return None

    @staticmethod
    async def _first_present(root: Any, candidates: tuple[str, ...]) -> Any | None:
        for selector in candidates:
            try:
                locator = root.locator(selector).first
                if await locator.count():
                    return locator
            except Exception:
                continue
        return None

    @staticmethod
    async def _any_visible(root: Any, candidates: tuple[str, ...]) -> bool:
        return await BossConnector._first_visible(root, candidates) is not None

    @staticmethod
    async def _first_text(root: Any, candidates: tuple[str, ...]) -> str | None:
        for selector in candidates:
            try:
                locator = root.locator(selector).first
                text = (await locator.inner_text(timeout=1500)).strip()
                if text:
                    return text
            except Exception:
                continue
        return None

    @staticmethod
    async def _first_attr(root: Any, candidates: tuple[str, ...], name: str) -> str | None:
        for selector in candidates:
            try:
                value = await root.locator(selector).first.get_attribute(name, timeout=1500)
                if value:
                    return value
            except Exception:
                continue
        return None

    @staticmethod
    async def _all_text(root: Any, candidates: tuple[str, ...]) -> list[str]:
        for selector in candidates:
            try:
                values = [value.strip() for value in await root.locator(selector).all_inner_texts()]
                values = [value for value in values if value]
                if values:
                    return values
            except Exception:
                continue
        return []

    @staticmethod
    async def _message_visible(page: Any, message: str) -> bool:
        needle = message[:40]
        for selector in selectors.OUTGOING_MESSAGE:
            try:
                if await page.locator(selector).filter(has_text=needle).last.is_visible(timeout=2000):
                    return True
            except Exception:
                continue
        return await BossConnector._any_visible(page, selectors.CONTINUE_CHAT)
