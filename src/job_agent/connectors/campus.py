from __future__ import annotations

import asyncio
import base64
import html
import http.cookiejar
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from ..models import Job
from .base import ActionResult, ActionStatus


SUPPORTED_CAMPUS_ADAPTERS = frozenset({"meituan", "didi_moka", "kuaishou", "tencent", "jd"})

_BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _join_text(*values: Any) -> str:
    return "\n\n".join(str(value).strip() for value in values if str(value or "").strip())


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in (_clean(item) for item in values) if value))


def _names(values: Any, key: str = "name") -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        value = item.get(key) if isinstance(item, dict) else item
        if _clean(value):
            result.append(_clean(value))
    return _unique(result)


def _iso_datetime(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000
        try:
            return datetime.fromtimestamp(numeric, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


class _InitDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.value = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        if values.get("id") == "init-data":
            self.value = values.get("value", "")


class _AllowedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, validator: Callable[[str], str]) -> None:
        super().__init__()
        self.validator = validator

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        self.validator(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class CampusPortalConnector:
    """Read-only adapters for a small catalog of verified campus recruiting portals.

    Site-specific request and mapping code stays in this module, while registration,
    filtering, scoring and planning remain shared. No candidate data is sent during
    discovery. ``autofill.profile`` is only a stable future extension contract.
    """

    def __init__(self, definition: dict[str, Any]) -> None:
        self.definition = definition
        self.site_id = str(definition["id"]).strip()
        self.source = f"official:{self.site_id}"
        self.name = str(definition.get("name") or self.site_id)
        self.adapter = str(definition.get("adapter") or "").strip()
        if self.adapter not in SUPPORTED_CAMPUS_ADAPTERS:
            raise ValueError(f"Unsupported campus adapter: {self.adapter}")
        self.list_url = str(definition["list_url"])
        self.allowed_hosts = {
            str(host).strip().lower()
            for host in (definition.get("allowed_hosts") or [urlparse(self.list_url).hostname])
            if str(host or "").strip()
        }
        self.timeout = max(5, min(int(definition.get("timeout_seconds", 25)), 60))
        self.max_results = max(1, min(int(definition.get("max_results", 200)), 500))
        self.max_keywords = max(1, min(int(definition.get("max_keywords", 8)), 20))
        self.max_detail_requests = max(0, min(int(definition.get("max_detail_requests", 60)), 100))
        self.autofill = dict(definition.get("autofill") or {})
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener = build_opener(
            HTTPCookieProcessor(self._cookie_jar),
            _AllowedRedirectHandler(self._assert_allowed_url),
        )

    def _assert_allowed_url(self, target: str) -> str:
        parsed = urlparse(target)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in self.allowed_hosts:
            raise ValueError(f"URL outside configured campus hosts: {target}")
        return target

    def _safe_url(self, value: str) -> str:
        return self._assert_allowed_url(urljoin(self.list_url, value))

    def _headers(self, *, referer: str | None = None) -> dict[str, str]:
        result = dict(_BROWSER_HEADERS)
        if referer:
            result["Referer"] = referer
            parsed = urlparse(referer)
            result["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
        return result

    def _read(self, request: Request, *, max_bytes: int = 10 * 1024 * 1024) -> bytes:
        with self._opener.open(request, timeout=self.timeout) as response:
            self._assert_allowed_url(str(response.geturl()))
            payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("Recruiting portal response exceeded the safe size limit")
        return payload

    def _get_text(self, url: str) -> str:
        target = self._safe_url(url)
        request = Request(target, headers=self._headers())
        return self._read(request).decode("utf-8")

    def _get_json(self, url: str, *, referer: str | None = None) -> dict[str, Any]:
        target = self._safe_url(url)
        request = Request(target, headers=self._headers(referer=referer))
        return json.loads(self._read(request))

    def _post_json(self, url: str, payload: dict[str, Any], *, referer: str | None = None) -> dict[str, Any]:
        target = self._safe_url(url)
        headers = self._headers(referer=referer or self.list_url)
        headers["Content-Type"] = "application/json"
        request = Request(
            target,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        return json.loads(self._read(request))

    def _query_terms(self, keywords: list[str]) -> list[str]:
        terms = _unique([item[:100] for item in keywords])[: self.max_keywords]
        return terms or [""]

    @staticmethod
    def _matches(job: Job, term: str) -> bool:
        if not term:
            return True
        haystack = f"{job.title} {job.description} {job.location}".casefold()
        return term.casefold() in haystack

    def _job_metadata(self, **extra: Any) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "portal_adapter": self.adapter,
            "autofill_profile": str(self.autofill.get("profile") or ""),
            "autofill_status": str(self.autofill.get("status") or "planned"),
            **extra,
        }

    async def discover(self, keywords: list[str]) -> list[Job]:
        return await asyncio.to_thread(self._discover_sync, keywords)

    def _discover_sync(self, keywords: list[str]) -> list[Job]:
        handlers: dict[str, Callable[[list[str]], list[Job]]] = {
            "meituan": self._discover_meituan,
            "didi_moka": self._discover_didi,
            "kuaishou": self._discover_kuaishou,
            "tencent": self._discover_tencent,
            "jd": self._discover_jd,
        }
        jobs = handlers[self.adapter](self._query_terms(keywords))
        unique: dict[str, Job] = {}
        for job in jobs:
            unique.setdefault(job.source_id, job)
            if len(unique) >= self.max_results:
                break
        return list(unique.values())

    def _discover_meituan(self, terms: list[str]) -> list[Job]:
        api = "https://zhaopin.meituan.com/api/official/job/getJobList"
        jobs: list[Job] = []
        for term in terms:
            page_no = 1
            while len(jobs) < self.max_results:
                payload = {
                    "page": {"pageNo": page_no, "pageSize": 100},
                    "jobShareType": "1",
                    "keywords": term,
                    "cityList": [],
                    "department": [],
                    "jfJgList": [],
                    "jobType": [{"code": "1", "subCode": []}, {"code": "2", "subCode": []}],
                    "typeCode": [],
                    "specialCode": [],
                }
                data = self._post_json(api, payload)
                if data.get("status") != 1:
                    raise RuntimeError(str(data.get("message") or "Meituan campus API returned an error"))
                body = data.get("data") or {}
                records = body.get("list") or []
                for record in records:
                    job = self._meituan_job(record)
                    if self._matches(job, term):
                        jobs.append(job)
                page = body.get("page") or {}
                if not records or page_no >= int(page.get("totalPage") or page_no):
                    break
                page_no += 1
        return jobs

    def _meituan_job(self, record: dict[str, Any]) -> Job:
        source_id = str(record.get("jobUnionId") or "")
        detail = (
            "https://zhaopin.meituan.com/web/position/detail?"
            + urlencode({"jobUnionId": source_id, "highlightType": "campus"})
        )
        departments = _names(record.get("department"))
        job_type = ["实习", "校招"] if str(record.get("jobType")) == "2" else ["全职", "校招"]
        return Job(
            source=self.source,
            source_id=source_id,
            title=str(record.get("name") or ""),
            company="美团",
            location="、".join(_names(record.get("cityList"))),
            url=detail,
            apply_url=detail,
            description=_join_text(record.get("jobDuty"), record.get("jobRequirement"), record.get("highLight")),
            published_at=_iso_datetime(record.get("refreshTime") or record.get("firstPostTime")),
            deadline=_iso_datetime(record.get("expiredTime")),
            metadata=self._job_metadata(
                employment_type=job_type,
                work_mode="现场",
                department=departments,
                job_family=_clean(record.get("jobFamily")),
            ),
        )

    @staticmethod
    def _decrypt_moka_response(payload: dict[str, Any], iv: str) -> dict[str, Any]:
        key = str(payload.get("necromancer") or "").encode("utf-8")
        if len(key) not in {16, 24, 32} or len(iv.encode("utf-8")) != 16:
            raise ValueError("Moka returned an invalid encrypted response envelope")
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv.encode("utf-8"))).decryptor()
        padded = decryptor.update(base64.b64decode(str(payload.get("data") or ""))) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        clear = unpadder.update(padded) + unpadder.finalize()
        return json.loads(clear)

    def _moka_init(self) -> dict[str, Any]:
        parser = _InitDataParser()
        parser.feed(self._get_text(self.list_url))
        if not parser.value:
            raise ValueError("Moka page did not expose init-data")
        return json.loads(html.unescape(parser.value))

    def _moka_post(self, payload: dict[str, Any], iv: str) -> dict[str, Any]:
        encrypted = self._post_json(
            "https://app.mokahr.com/api/outer/ats-apply/website/jobs/v2",
            payload,
            referer=self.list_url,
        )
        decoded = self._decrypt_moka_response(encrypted, iv)
        if decoded.get("success") is not True:
            raise RuntimeError(str(decoded.get("msg") or f"Moka API error {decoded.get('code')}"))
        return decoded

    def _discover_didi(self, terms: list[str]) -> list[Job]:
        init = self._moka_init()
        iv = str(init.get("aesIv") or "")
        org_id = str((init.get("org") or {}).get("id") or self.definition.get("org_id") or "didiglobal")
        site_id = int(init.get("siteId") or self.definition.get("site_id") or 96064)
        mode = str(init.get("mode") or "campus")
        recommend_code = str(self.definition.get("recommend_code") or "").strip()
        jobs: list[Job] = []
        for term in terms:
            offset = 0
            while len(jobs) < self.max_results:
                payload = {
                    "orgId": org_id,
                    "siteId": site_id,
                    "limit": 50,
                    "offset": offset,
                    "needStat": True,
                    "keyword": term,
                    "site": mode,
                    "recommendCode": recommend_code,
                    "locale": "zh-CN",
                }
                decoded = self._moka_post(payload, iv)
                data = decoded.get("data") or {}
                records = data.get("jobs") or []
                for record in records:
                    job = self._didi_job(record, recommend_code)
                    if self._matches(job, term):
                        jobs.append(job)
                total = int((data.get("jobStats") or {}).get("total") or 0)
                offset += len(records)
                if not records or offset >= total:
                    break
        return jobs

    def _didi_job(self, record: dict[str, Any], recommend_code: str) -> Job:
        source_id = str(record.get("id") or "")
        query = f"?{urlencode({'recommendCode': recommend_code})}" if recommend_code else ""
        detail = f"https://app.mokahr.com/campus_apply/didiglobal/96064{query}#/job/{quote(source_id)}"
        locations = [
            _clean(item.get("cityName") or item.get("name") or item.get("address"))
            for item in (record.get("locations") or [])
            if isinstance(item, dict)
        ]
        commitment = _clean(record.get("commitment"))
        employment = ["实习", "校招"] if "实习" in commitment or str(record.get("hireMode")) == "1" else ["全职", "校招"]
        return Job(
            source=self.source,
            source_id=source_id,
            title=str(record.get("title") or ""),
            company="滴滴",
            location="、".join(_unique(locations)),
            url=detail,
            apply_url=detail,
            description=_join_text(record.get("jobDescription"), record.get("description")),
            education=_clean(record.get("education")),
            published_at=_iso_datetime(record.get("publishedAt") or record.get("openedAt")),
            metadata=self._job_metadata(
                employment_type=employment,
                work_mode="现场",
                department=_clean((record.get("department") or {}).get("name")),
                job_family=_clean((record.get("zhineng") or {}).get("name")),
            ),
        )

    def _discover_kuaishou(self, terms: list[str]) -> list[Job]:
        api = "https://campus.kuaishou.cn/recruit/campus/e/api/v1/open/positions/simple"
        project_codes = list(self.definition.get("recruit_sub_project_codes") or ["20271779425607"])
        jobs: list[Job] = []
        for term in terms:
            page_no = 1
            while len(jobs) < self.max_results:
                payload = {
                    "recruitSubProjectCodes": project_codes,
                    "pageSize": 100,
                    "pageNum": page_no,
                    "name": term,
                }
                data = self._post_json(api, payload)
                if data.get("code") != 0:
                    raise RuntimeError(str(data.get("message") or "Kuaishou campus API returned an error"))
                body = data.get("result") or {}
                records = body.get("list") or []
                for record in records:
                    job = self._kuaishou_job(record, project_codes)
                    if self._matches(job, term):
                        jobs.append(job)
                if not records or page_no >= int(body.get("pages") or page_no):
                    break
                page_no += 1
        return jobs

    def _kuaishou_job(self, record: dict[str, Any], project_codes: list[str]) -> Job:
        source_id = str(record.get("id") or record.get("code") or "")
        code = str(self.definition.get("share_code") or "campusNTjtWbAZm")
        query = urlencode({"code": code, "recruitSubProjectCodes": ",".join(project_codes)})
        detail = f"https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/{quote(source_id)}?{query}"
        nature = str(record.get("positionNatureCode") or "").lower()
        employment = ["实习", "校招"] if "intern" in nature else ["全职", "校招"] if "full" in nature else "校招"
        return Job(
            source=self.source,
            source_id=source_id,
            title=str(record.get("name") or ""),
            company="快手",
            location="、".join(_names(record.get("workLocationDicts"))),
            url=detail,
            apply_url=detail,
            description=_join_text(record.get("description"), record.get("positionDemand")),
            published_at=_iso_datetime(record.get("releaseTime") or record.get("updateTime")),
            deadline=_iso_datetime(record.get("closeTime")),
            metadata=self._job_metadata(
                employment_type=employment,
                work_mode="现场",
                position_category=_clean(record.get("positionCategoryCode")),
            ),
        )

    def _discover_tencent(self, terms: list[str]) -> list[Job]:
        search_api = "https://join.qq.com/api/v1/position/searchPosition"
        jobs: list[Job] = []
        detail_requests = 0
        for term in terms:
            page_index = 1
            while len(jobs) < self.max_results:
                payload = {
                    "keyword": term,
                    "bgList": [],
                    "workCountryType": 1,
                    "workCityList": [],
                    "recruitCityList": [],
                    "positionFidList": [],
                    "pageIndex": page_index,
                    "pageSize": 100,
                }
                data = self._post_json(search_api, payload)
                if data.get("status") != 0:
                    raise RuntimeError(str(data.get("message") or "Tencent campus API returned an error"))
                body = data.get("data") or {}
                records = body.get("positionList") or []
                for record in records:
                    job = self._tencent_job(record)
                    if not self._matches(job, term):
                        continue
                    if detail_requests < self.max_detail_requests:
                        detail_requests += 1
                        try:
                            detail_data = self._get_json(
                                "https://join.qq.com/api/v1/jobDetails/getJobDetailsByPostId?"
                                + urlencode({"postId": job.source_id}),
                                referer=self.list_url,
                            )
                            if detail_data.get("status") == 0:
                                job = self._tencent_job(record, detail_data.get("data") or {})
                        except (OSError, ValueError, json.JSONDecodeError):
                            # A list result is still a stable real job when one detail call fails.
                            pass
                    jobs.append(job)
                total = int(body.get("count") or 0)
                if not records or page_index * 100 >= total:
                    break
                page_index += 1
        return jobs

    def _tencent_job(self, record: dict[str, Any], detail_data: dict[str, Any] | None = None) -> Job:
        detail_data = detail_data or {}
        source_id = str(record.get("postId") or record.get("id") or "")
        external = _clean(record.get("positionUrl"))
        external_host = (urlparse(external).hostname or "").lower() if external else ""
        detail = external if external_host in self.allowed_hosts else f"https://join.qq.com/post_detail.html?postid={quote(source_id)}"
        label = _clean(record.get("recruitLabelName") or record.get("projectName"))
        employment = ["实习", "校招"] if "实习" in label else ["全职", "校招"]
        work_cities = detail_data.get("workCityList")
        location = "、".join(_unique([str(item) for item in work_cities])) if isinstance(work_cities, list) else _clean(record.get("workCities"))
        return Job(
            source=self.source,
            source_id=source_id,
            title=str(record.get("positionTitle") or ""),
            company="腾讯",
            location=location,
            url=detail,
            apply_url=detail,
            description=_join_text(
                detail_data.get("desc"),
                detail_data.get("request"),
                detail_data.get("graduateBonus"),
                detail_data.get("internBonus"),
                label,
            ),
            metadata=self._job_metadata(
                employment_type=employment,
                work_mode="现场",
                business_groups=_clean(record.get("bgs")),
                project_name=_clean(record.get("projectName")),
            ),
        )

    def _discover_jd(self, terms: list[str]) -> list[Job]:
        api = "https://campus.jd.com/api/wx/position/page?type=present"
        jobs: list[Job] = []
        for term in terms:
            page_index = 0
            while len(jobs) < self.max_results:
                payload = {
                    "pageSize": 100,
                    "pageIndex": page_index,
                    "parameter": {
                        "positionName": term,
                        "planIdList": [],
                        "jobDirectionCodeList": [],
                        "workCityCodeList": [],
                        "positionDeptList": [],
                        "publishIdList": [],
                    },
                }
                data = self._post_json(api, payload)
                if data.get("success") is not True:
                    raise RuntimeError(str(data.get("message") or "JD campus API returned an error"))
                body = data.get("body") or {}
                records = body.get("items") or []
                for record in records:
                    job = self._jd_job(record)
                    if self._matches(job, term):
                        jobs.append(job)
                total = int(body.get("totalNumber") or 0)
                if not records or (page_index + 1) * 100 >= total:
                    break
                page_index += 1
        return jobs

    def _jd_job(self, record: dict[str, Any]) -> Job:
        source_id = str(record.get("publishId") or record.get("reqId") or "")
        referral = str(self.definition.get("referral_erp") or "").strip()
        query = {"id": source_id}
        if referral:
            query["codeValueErp"] = referral
        detail = "https://campus.jd.com/api/wx/position/index#/details?" + urlencode(query)
        requirements = [item for item in (record.get("requirementVoList") or []) if isinstance(item, dict)]
        locations = _unique([_clean(item.get("workCity")) for item in requirements])
        business_units = _unique([_clean(item.get("positionBg")) for item in requirements])
        educations = _unique([_clean(item.get("education")) for item in requirements])
        return Job(
            source=self.source,
            source_id=source_id,
            title=str(record.get("positionName") or ""),
            company="京东",
            location="、".join(locations),
            url=detail,
            apply_url=detail,
            description=_join_text(record.get("workContent"), record.get("qualification")),
            education=educations[0] if len(educations) == 1 else "",
            published_at=_iso_datetime(record.get("publishTime")),
            metadata=self._job_metadata(
                employment_type=["全职", "校招"],
                work_mode="现场",
                business_units=business_units,
                job_direction=_clean(record.get("jobDirection")),
                requirement_ids=_unique([str(item.get("reqId") or "") for item in requirements]),
            ),
        )

    async def submit(
        self,
        job: Job,
        fixed_answers: dict[str, str],
        resume_path: str,
        *,
        live: bool,
    ) -> ActionResult:
        return ActionResult(
            ActionStatus.NEEDS_HUMAN,
            "该渠道已支持岗位采集；自动填表插件尚未实现，请跳转官网人工确认并提交",
            evidence=job.apply_url or job.url,
            details={
                "autofill_status": str(self.autofill.get("status") or "planned"),
                "autofill_profile": str(self.autofill.get("profile") or ""),
            },
        )

    async def close(self) -> None:
        return None
