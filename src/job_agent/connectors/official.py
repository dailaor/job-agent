from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..models import Job
from .base import ActionResult, ActionStatus


def _dig(value: Any, path: str) -> Any:
    current = value
    for part in [item for item in path.split(".") if item]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def _number(value: Any, *, integer: bool = False) -> int | float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return int(parsed) if integer else parsed


def _metadata_value(value: Any) -> str | list[str] | None:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or None
    cleaned = str(value or "").strip()
    return cleaned or None


class _AllowedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, validator: Any) -> None:
        super().__init__()
        self.validator = validator

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        self.validator(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class OfficialSiteConnector:
    """A fixed-site connector supporting JSON feeds and selector-driven browser forms."""

    def __init__(self, definition: dict[str, Any]) -> None:
        self.definition = definition
        self.site_id = str(definition["id"])
        self.source = f"official:{self.site_id}"
        self.name = str(definition.get("name", self.site_id))
        self.list_url = str(definition["list_url"])
        self.allowed_hosts = {
            str(host).strip().lower()
            for host in (definition.get("allowed_hosts") or [urlparse(self.list_url).hostname])
            if str(host or "").strip()
        }
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    def _safe_url(self, value: str) -> str:
        target = urljoin(self.list_url, value)
        return self._assert_allowed_url(target)

    def _assert_allowed_url(self, target: str) -> str:
        parsed = urlparse(target)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in self.allowed_hosts:
            raise ValueError(f"URL outside configured hosts: {target}")
        return target

    async def discover(self, keywords: list[str]) -> list[Job]:
        strategy = self.definition.get("strategy", "json_api")
        if strategy == "json_api":
            return self._discover_json(keywords)
        if strategy == "browser":
            return await self._discover_browser(keywords)
        raise ValueError(f"Unsupported official site strategy: {strategy}")

    def _discover_json(self, keywords: list[str]) -> list[Job]:
        headers = {"Accept": "application/json", "User-Agent": "LocalJobAgent/0.1"}
        headers.update({str(k): str(v) for k, v in self.definition.get("headers", {}).items()})
        request = Request(self._safe_url(self.list_url), headers=headers)
        opener = build_opener(_AllowedRedirectHandler(self._assert_allowed_url))
        with opener.open(request, timeout=int(self.definition.get("timeout_seconds", 20))) as response:
            self._assert_allowed_url(str(response.geturl()))
            payload = json.load(response)
        records = _dig(payload, str(self.definition.get("records_path", "")))
        mapping = self.definition.get("mapping", {})
        jobs: list[Job] = []
        for record in records:
            def value(name: str, default: Any = "") -> Any:
                path = mapping.get(name)
                if not path:
                    return default
                try:
                    return _dig(record, str(path))
                except (KeyError, IndexError, TypeError, ValueError):
                    return default
            title = str(value("title")).strip()
            company = str(value("company", self.name)).strip() or self.name
            description = str(value("description")).strip()
            if keywords and not any(keyword.lower() in f"{title} {description}".lower() for keyword in keywords):
                continue
            raw_url = str(value("url")).strip()
            if not title or not raw_url:
                continue
            detail_url = self._safe_url(raw_url)
            source_id = str(value("id", "") or "").strip() or detail_url
            apply_url = self._safe_url(str(value("apply_url", detail_url) or detail_url))
            employment_type = _metadata_value(value("employment_type", None))
            work_mode = _metadata_value(value("work_mode", None))
            metadata: dict[str, Any] = {"site_id": self.site_id, "raw_id": source_id}
            if employment_type is not None:
                metadata["employment_type"] = employment_type
            if work_mode is not None:
                metadata["work_mode"] = work_mode
            jobs.append(Job(
                source=self.source, source_id=source_id, title=title,
                company=company, location=str(value("location")),
                url=detail_url, apply_url=apply_url,
                description=description, published_at=value("published_at", None),
                deadline=value("deadline", None), education=str(value("education")),
                salary_min=_number(value("salary_min", None), integer=True),
                salary_max=_number(value("salary_max", None), integer=True),
                experience_min=_number(value("experience_min", None)),
                experience_max=_number(value("experience_max", None)),
                metadata=metadata,
            ))
        return jobs

    async def _start_browser(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Install the browser extra: pip install -e .[browser]") from exc
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=bool(self.definition.get("headless", False)))
        self._context = await self._browser.new_context(locale="zh-CN")
        self._page = await self._context.new_page()

    async def _discover_browser(self, keywords: list[str]) -> list[Job]:
        await self._start_browser()
        page = self._page
        await page.goto(self._safe_url(self.list_url), wait_until="domcontentloaded", timeout=30_000)
        self._assert_allowed_url(str(page.url))
        selectors = self.definition.get("selectors", {})
        card_selector = selectors.get("job_card")
        if not card_selector:
            raise ValueError("selectors.job_card is required for browser discovery")
        cards = page.locator(card_selector)
        await cards.first.wait_for(state="attached", timeout=10_000)
        jobs: list[Job] = []
        for index in range(await cards.count()):
            card = cards.nth(index)
            title = (await card.locator(selectors["title"]).first.inner_text()).strip()
            description = ""
            if selectors.get("description"):
                description = (await card.locator(selectors["description"]).first.inner_text()).strip()
            if keywords and not any(keyword.lower() in f"{title} {description}".lower() for keyword in keywords):
                continue
            href = await card.locator(selectors["url"]).first.get_attribute("href")
            if not href:
                continue
            url = self._safe_url(href)
            async def optional_text(name: str) -> str:
                if not selectors.get(name):
                    return ""
                try:
                    return (await card.locator(selectors[name]).first.inner_text()).strip()
                except Exception:
                    return ""
            employment_type = _metadata_value(await optional_text("employment_type"))
            work_mode = _metadata_value(await optional_text("work_mode"))
            metadata: dict[str, Any] = {"site_id": self.site_id}
            if employment_type is not None:
                metadata["employment_type"] = employment_type
            if work_mode is not None:
                metadata["work_mode"] = work_mode
            jobs.append(Job(
                source=self.source, source_id=url, title=title,
                company=await optional_text("company") or self.name,
                location=await optional_text("location"), url=url, apply_url=url,
                description=description,
                salary_min=_number(await optional_text("salary_min"), integer=True),
                salary_max=_number(await optional_text("salary_max"), integer=True),
                experience_min=_number(await optional_text("experience_min")),
                experience_max=_number(await optional_text("experience_max")),
                education=await optional_text("education"),
                published_at=await optional_text("published_at") or None,
                deadline=await optional_text("deadline") or None,
                metadata=metadata,
            ))
        return jobs

    async def submit(self, job: Job, fixed_answers: dict[str, str], resume_path: str, *, live: bool) -> ActionResult:
        form = self.definition.get("form")
        if not form:
            return ActionResult(ActionStatus.NEEDS_HUMAN, "该官网只配置了岗位采集，尚未配置投递表单")
        required_keys = [str(item) for item in form.get("required_answer_keys", [])]
        missing = [key for key in required_keys if not fixed_answers.get(key)]
        if missing:
            return ActionResult(ActionStatus.NEEDS_HUMAN, "固定答案缺失", details={"missing_keys": missing})
        open_questions = form.get("open_questions", [])
        if open_questions:
            return ActionResult(ActionStatus.NEEDS_HUMAN, "表单包含开放题，按产品边界转人工", details={"questions": open_questions})
        resume = Path(resume_path).expanduser()
        if form.get("resume_selector") and not resume.is_file():
            return ActionResult(ActionStatus.NEEDS_HUMAN, "固定简历文件不存在", evidence=str(resume))
        await self._start_browser()
        page = self._page
        side_effect_started = False
        try:
            await page.goto(self._safe_url(job.apply_url or job.url), wait_until="domcontentloaded", timeout=30_000)
            # Redirects are rechecked before any personal data or resume is written.
            self._assert_allowed_url(str(page.url))
            for answer_key, selector in form.get("fields", {}).items():
                self._assert_allowed_url(str(page.url))
                value = fixed_answers.get(answer_key)
                if value is None:
                    return ActionResult(ActionStatus.NEEDS_HUMAN, f"未映射必填字段：{answer_key}")
                await page.locator(selector).first.fill(str(value))
            if form.get("resume_selector"):
                self._assert_allowed_url(str(page.url))
                await page.locator(form["resume_selector"]).first.set_input_files(str(resume))
            unfilled_required: list[str] = []
            required = page.locator("input[required], select[required], textarea[required], [aria-required='true']")
            for index in range(await required.count()):
                field = required.nth(index)
                descriptor = (
                    await field.get_attribute("name")
                    or await field.get_attribute("id")
                    or await field.get_attribute("aria-label")
                    or f"required-field-{index + 1}"
                )
                value = await field.evaluate(
                    "element => element.type === 'checkbox' || element.type === 'radio' ? element.checked : Boolean(element.value)"
                )
                if not value:
                    unfilled_required.append(str(descriptor))
            if unfilled_required:
                return ActionResult(
                    ActionStatus.NEEDS_HUMAN,
                    "页面存在未映射或未填写的必填字段",
                    details={"fields": unfilled_required},
                )
            if not live:
                return ActionResult(ActionStatus.OK, "官网表单预检和演练填写完成，未点击提交")
            submit_selector = form.get("submit_selector")
            if not submit_selector:
                return ActionResult(ActionStatus.NEEDS_HUMAN, "未配置提交按钮")
            self._assert_allowed_url(str(page.url))
            await page.locator(submit_selector).first.click()
            side_effect_started = True
            await page.wait_for_timeout(1200)
            success_selector = form.get("success_selector")
            success_text = str(form.get("success_text", ""))
            verified = False
            if success_selector:
                verified = await page.locator(success_selector).first.is_visible(timeout=5000)
            if success_text:
                body = await page.locator("body").inner_text(timeout=5000)
                verified = verified or success_text in body
            if not verified:
                return ActionResult(ActionStatus.UNVERIFIED, "官网已提交但缺少确定成功证据，禁止自动重投")
            return ActionResult(ActionStatus.SUBMITTED, "官网表单已提交，等待邮件回执", evidence=str(page.url))
        except Exception as exc:
            status = ActionStatus.UNVERIFIED if side_effect_started else ActionStatus.FAILED
            return ActionResult(status, "官网投递流程异常", details={"error": str(exc)})

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._page = self._context = self._browser = self._playwright = None
