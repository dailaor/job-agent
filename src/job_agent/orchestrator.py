from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .config import AgentConfig
from .connectors.base import ActionResult, ActionStatus
from .connectors.boss import BossConnector
from .connectors.registry import ChannelAdapter, ChannelRegistry, build_channel_registry
from .database import Database
from .matching import evaluate_job, strategy_allocation
from .models import ApplicationStatus, JobStatus, Strategy, utc_now
from .receipts import ImapReceiptChecker


class JobAgent:
    def __init__(
        self,
        config: AgentConfig,
        database: Database,
        channel_registry: ChannelRegistry | None = None,
    ) -> None:
        self.config = config
        self.db = database
        self.channel_registry = channel_registry or build_channel_registry(config)

    def channel_catalog(self) -> list[dict[str, Any]]:
        latest_runs = self.db.latest_source_runs()
        channels = [
            self._channel_entry(
                channel_id=adapter.id,
                name=adapter.name,
                channel_type=adapter.channel_type,
                enabled=adapter.enabled,
                ready=adapter.ready,
                keywords=adapter.keywords,
                strategy=adapter.strategy,
                url=adapter.url,
                latest_run=latest_runs.get(adapter.id),
                missing=adapter.missing,
                capabilities=adapter.capabilities,
            )
            for adapter in self.channel_registry.all()
        ]
        for index, message in enumerate(self.channel_registry.load_errors, start=1):
            channels.append(self._channel_entry(
                channel_id=f"registry:error:{index}",
                name="渠道扩展加载失败",
                channel_type="registry_error",
                enabled=True,
                ready=False,
                keywords=[],
                strategy="未加载",
                url="",
                latest_run=None,
                missing=[message],
                capabilities={},
            ))
        return channels

    @staticmethod
    def _channel_entry(
        *, channel_id: str, name: str, channel_type: str, enabled: bool, ready: bool,
        keywords: list[str], strategy: str, url: str,
        latest_run: dict[str, Any] | None, missing: list[str], capabilities: dict[str, Any],
    ) -> dict[str, Any]:
        status_labels = {
            "api_fetched": "正常：API 已提取真实岗位",
            "browser_fetched": "正常：浏览器已提取真实岗位",
            "portal_unparsed": "需维护：未提取到稳定岗位",
            "auth_required": "需要登录或恢复会话",
            "encrypted_api": "接口加密尚未适配",
            "portal_error": "渠道访问异常",
        }
        if not enabled:
            health = "disabled"
            health_label = "未启用"
        elif not ready:
            health = "not_ready"
            health_label = "配置不完整"
        elif latest_run is None:
            health = "never_run"
            health_label = "尚未检查"
        else:
            health = str(latest_run["status"])
            health_label = status_labels.get(health, health)
        return {
            "id": channel_id,
            "name": name,
            "type": channel_type,
            "enabled": enabled,
            "ready": ready,
            "keywords": keywords,
            "strategy": strategy,
            "url": url,
            "missing": missing,
            "health": health,
            "health_label": health_label,
            "last_run": latest_run,
            "capabilities": capabilities,
        }

    async def discover(self, channel: str = "all") -> dict[str, Any]:
        if channel == "all":
            selected = [item["id"] for item in self.channel_catalog() if item["ready"]]
        elif channel == "official":
            selected = [item["id"] for item in self.channel_catalog() if item["ready"] and item["type"] == "official"]
        else:
            selected = [channel]
        return await self.discover_selected(selected)

    async def discover_selected(self, channel_ids: list[str]) -> dict[str, Any]:
        catalog = {item["id"]: item for item in self.channel_catalog()}
        selected = list(dict.fromkeys(str(item) for item in channel_ids if str(item).strip()))
        if not selected:
            return {
                "status": "no_channels",
                "message": "没有选择可抓取渠道。请先在配置页面启用 BOSS 或添加官网/ATS 渠道。",
                "sources": [],
            }

        results: list[dict[str, Any]] = []
        for channel_id in selected:
            entry = catalog.get(channel_id)
            if entry is None:
                results.append({"source": channel_id, "status": "not_configured", "message": "渠道不存在于当前配置"})
                continue
            if not entry["ready"]:
                results.append({
                    "source": channel_id,
                    "status": "not_ready",
                    "message": "、".join(entry["missing"]) or "渠道尚未就绪",
                })
                continue
            adapter = self.channel_registry.get(channel_id)
            if adapter is None:
                results.append({"source": channel_id, "status": "not_configured", "message": "未找到渠道适配器"})
                continue
            results.append(await self._discover_adapter(adapter))
        completed = sum(1 for item in results if item.get("status") in {"api_fetched", "browser_fetched"})
        return {
            "status": "ok" if completed else "needs_configuration",
            "selected": selected,
            "completed": completed,
            "sources": results,
            "message": f"已完成 {completed}/{len(selected)} 个渠道" if completed else "所选渠道均未完成抓取，请查看渠道状态和原因。",
        }

    async def _discover_adapter(self, adapter: ChannelAdapter) -> dict[str, Any]:
        started = utc_now()
        if adapter.connector_factory is None:
            return {"source": adapter.id, "status": "not_ready", "records": 0, "message": "渠道适配器尚未就绪"}
        connector = adapter.connector_factory()
        try:
            jobs = await connector.discover(adapter.keywords)
            mismatched = sorted({job.source for job in jobs if job.source != adapter.id})
            if mismatched:
                raise ValueError(f"渠道返回了不一致的 source：{mismatched}，期望 {adapter.id}")
            self._validate_discovered_jobs(adapter, jobs)
            created = self._persist_jobs(jobs)
            status = adapter.success_status if jobs else "portal_unparsed"
            message = f"新增 {created}" if jobs else "未提取到具有稳定详情的真实岗位"
            self.db.record_source_run(adapter.id, status, len(jobs), message, started)
            return {"source": adapter.id, "status": status, "records": len(jobs), "created": created, "message": message}
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            status = "auth_required" if any(marker in lowered for marker in ("登录", "login", "sign in", "unauthorized")) else "portal_unparsed"
            self.db.record_source_run(adapter.id, status, 0, message, started)
            return {"source": adapter.id, "status": status, "records": 0, "message": message}
        finally:
            try:
                await connector.close()
            except Exception:
                pass

    @staticmethod
    def _validate_discovered_jobs(adapter: ChannelAdapter, jobs: list[Any]) -> None:
        """Reject incomplete or off-host records before they reach the shared pool."""

        if jobs and not adapter.allowed_hosts:
            raise ValueError("渠道必须配置 allowed_hosts，才能接收岗位详情链接")
        for index, job in enumerate(jobs, start=1):
            missing = [
                label
                for value, label in (
                    (job.source_id, "source_id"),
                    (job.title, "岗位名称"),
                    (job.company, "公司"),
                    (job.url, "详情 URL"),
                )
                if not str(value or "").strip()
            ]
            if missing:
                raise ValueError(f"第 {index} 条岗位缺少稳定证据：{', '.join(missing)}")
            for label, value in (("详情 URL", job.url), ("申请 URL", job.apply_url)):
                if not value:
                    continue
                parsed = urlparse(str(value))
                host = (parsed.hostname or "").lower()
                if parsed.scheme != "https" or host not in adapter.allowed_hosts:
                    raise ValueError(f"第 {index} 条岗位的{label}不在渠道 HTTPS 白名单：{value}")

    def _persist_jobs(self, jobs: list[Any]) -> int:
        created = 0
        for job in jobs:
            job_id, is_new = self.db.upsert_job(job)
            job.id = job_id
            self.db.resolve_fingerprint_priority(job.fingerprint, self.config.preferences.channel_priority)
            if is_new:
                created += 1
                self.db.event("job", job_id, "discovered", {"source": job.source, "title": job.title})
        return created

    def seed_demo(self) -> dict[str, Any]:
        from .connectors.demo import demo_jobs

        jobs = demo_jobs()
        return {"records": len(jobs), "created": self._persist_jobs(jobs)}

    def evaluate(self) -> dict[str, int]:
        rows = self.db.list_jobs(status=JobStatus.DISCOVERED.value)
        evaluated = eligible = rejected = 0
        for row in rows:
            job = self.db.get_job(int(row["id"]))
            if job is None:
                continue
            evaluation = evaluate_job(job, self.config)
            self.db.save_evaluation(evaluation)
            evaluated += 1
            if evaluation.strategy is Strategy.SKIP:
                self.db.set_job_status(job.id or 0, JobStatus.REJECTED)
                rejected += 1
            else:
                self.db.set_job_status(job.id or 0, JobStatus.ELIGIBLE)
                eligible += 1
            self.db.event("job", job.id or 0, "evaluated", evaluation.to_dict())
        return {"evaluated": evaluated, "eligible": eligible, "rejected": rejected}

    def _planning_sources(self, channel: str) -> tuple[list[str], int]:
        if channel == "boss":
            return ["boss"], self.config.preferences.boss_daily_limit
        if channel == "official":
            sources = [adapter.id for adapter in self.channel_registry.all() if adapter.channel_type == "official"]
            # Keep the bundled offline demo plannable even before a real site is configured.
            sources.extend(
                str(row["source"])
                for row in self.db.list_jobs(limit=1000)
                if str(row["source"]).startswith("official:")
            )
            return list(dict.fromkeys(sources)), self.config.preferences.official_daily_limit
        adapter = self.channel_registry.get(channel)
        if adapter is None:
            raise ValueError(f"unknown channel: {channel}")
        return [adapter.id], adapter.daily_limit if adapter.daily_limit is not None else self.config.preferences.official_daily_limit

    def planning_channels(self) -> list[str]:
        channels = ["boss", "official"]
        channels.extend(
            adapter.id
            for adapter in self.channel_registry.all()
            if adapter.channel_type not in {"boss", "official"}
        )
        return list(dict.fromkeys(channels))

    def plan(self, channel: str) -> dict[str, Any]:
        sources, daily_limit = self._planning_sources(channel)
        remaining = max(0, daily_limit - self.db.today_action_count(channel))
        candidates = self.db.eligible_jobs_for_sources(sources)
        allocation = strategy_allocation(remaining, self.config.preferences.strategy_mix)
        buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in allocation}
        for row in candidates:
            buckets.setdefault(str(row["strategy"]), []).append(row)
        selected: list[dict[str, Any]] = []
        selected_ids: set[int] = set()
        for strategy, count in allocation.items():
            for row in buckets.get(strategy, [])[:count]:
                selected.append(row)
                selected_ids.add(int(row["id"]))
        if len(selected) < remaining:
            for row in candidates:
                if int(row["id"]) in selected_ids:
                    continue
                selected.append(row)
                selected_ids.add(int(row["id"]))
                if len(selected) >= remaining:
                    break
        application_ids: list[int] = []
        for row in selected:
            greeting = self.config.greeting_for(str(row["title"]), str(row["company"])) if channel == "boss" else None
            application_id = self.db.create_application(int(row["id"]), channel, greeting)
            self.db.set_job_status(int(row["id"]), JobStatus.QUEUED)
            self.db.event("application", application_id, "planned", {"strategy": row["strategy"], "score": row["overall_score"]})
            application_ids.append(application_id)
        return {"channel": channel, "daily_limit": daily_limit, "remaining_before_plan": remaining, "allocation": allocation, "planned": len(application_ids), "application_ids": application_ids}

    def plan_all(self) -> dict[str, Any]:
        plans = [self.plan(channel) for channel in self.planning_channels()]
        return {
            "plans": plans,
            "planned": sum(int(item["planned"]) for item in plans),
        }

    async def execute(self, channel: str, *, live: bool = False) -> dict[str, Any]:
        applications = self.db.list_applications(status=ApplicationStatus.PLANNED.value, channel=channel)
        results: list[dict[str, Any]] = []
        if channel == "boss":
            adapter = self.channel_registry.get("boss")
            if adapter is None or not adapter.ready:
                message = "、".join(adapter.missing) if adapter else "未找到 BOSS 渠道配置"
                for application in applications:
                    job = self.db.get_job(int(application["job_id"]))
                    result = ActionResult(ActionStatus.NEEDS_HUMAN, message, evidence=(job.apply_url or job.url) if job else "")
                    self._record_action(int(application["id"]), result, "boss_greeting", live=live)
                    results.append({"application_id": application["id"], **result.to_dict()})
                return {"channel": channel, "live": live, "processed": len(results), "results": results}
            connector = adapter.connector_factory() if adapter.connector_factory else BossConnector(self.config.boss)
            try:
                for application in applications:
                    job = self.db.get_job(int(application["job_id"]))
                    if job is None:
                        continue
                    try:
                        result = await connector.send_greeting(job, str(application.get("greeting") or ""), live=live)
                    except Exception as exc:
                        result = ActionResult(ActionStatus.NEEDS_HUMAN, "BOSS 执行器当前不可用", evidence=job.url, details={"error": str(exc)})
                    self._record_action(int(application["id"]), result, "boss_greeting", live=live)
                    results.append({"application_id": application["id"], **result.to_dict()})
                    if result.status in {ActionStatus.LIMIT_REACHED, ActionStatus.NEEDS_HUMAN}:
                        break
            finally:
                try:
                    await connector.close()
                except Exception:
                    pass
        elif channel == "official":
            for application in applications:
                job = self.db.get_job(int(application["job_id"]))
                if job is None:
                    continue
                adapter = self.channel_registry.get(job.source)
                if adapter is None or adapter.connector_factory is None:
                    result = ActionResult(ActionStatus.NEEDS_HUMAN, f"未找到官网适配器配置：{job.source}", evidence=job.apply_url or job.url)
                else:
                    connector = adapter.connector_factory()
                    try:
                        submit = getattr(connector, "submit", None)
                        if not callable(submit):
                            result = ActionResult(ActionStatus.NEEDS_HUMAN, "该渠道只支持岗位发现，请跳转原始页面投递", evidence=job.apply_url or job.url)
                        else:
                            try:
                                result = await submit(job, self.config.fixed_answers, self.config.candidate.resume_path, live=live)
                            except Exception as exc:
                                result = ActionResult(ActionStatus.NEEDS_HUMAN, "官网执行器当前不可用，请跳转原始页面投递", evidence=job.apply_url or job.url, details={"error": str(exc)})
                    finally:
                        try:
                            await connector.close()
                        except Exception:
                            pass
                self._record_action(int(application["id"]), result, "official_submit", live=live)
                results.append({"application_id": application["id"], **result.to_dict()})
        else:
            adapter = self.channel_registry.get(channel)
            if adapter is None:
                raise ValueError(f"unknown channel: {channel}")
            for application in applications:
                job = self.db.get_job(int(application["job_id"]))
                if job is None:
                    continue
                if adapter.connector_factory is None:
                    result = ActionResult(ActionStatus.NEEDS_HUMAN, "渠道执行器未配置，请跳转原始页面投递", evidence=job.apply_url or job.url)
                else:
                    connector = adapter.connector_factory()
                    try:
                        submit = getattr(connector, "submit", None)
                        if not callable(submit):
                            result = ActionResult(ActionStatus.NEEDS_HUMAN, "该扩展渠道只支持岗位发现，请跳转原始页面投递", evidence=job.apply_url or job.url)
                        else:
                            try:
                                result = await submit(job, self.config.fixed_answers, self.config.candidate.resume_path, live=live)
                            except Exception as exc:
                                result = ActionResult(ActionStatus.NEEDS_HUMAN, "扩展渠道执行器当前不可用，请跳转原始页面投递", evidence=job.apply_url or job.url, details={"error": str(exc)})
                    finally:
                        try:
                            await connector.close()
                        except Exception:
                            pass
                self._record_action(int(application["id"]), result, "channel_submit", live=live)
                results.append({"application_id": application["id"], **result.to_dict()})
        return {"channel": channel, "live": live, "processed": len(results), "results": results}

    async def execute_all(self, *, live: bool = False) -> dict[str, Any]:
        channels = [await self.execute(channel, live=live) for channel in self.planning_channels()]
        return {
            "live": live,
            "processed": sum(int(item["processed"]) for item in channels),
            "channels": channels,
        }

    def _record_action(self, application_id: int, result: ActionResult, action: str, *, live: bool) -> None:
        if not live:
            self.db.event("application", application_id, f"dry_run:{action}", result.to_dict())
            return
        if action == "boss_greeting" and result.status is ActionStatus.SUBMITTED:
            status = ApplicationStatus.AWAITING_REPLY
        elif result.status is ActionStatus.CONFIRMED:
            status = ApplicationStatus.CONFIRMED
        elif result.status is ActionStatus.ALREADY_DONE:
            status = ApplicationStatus.NEEDS_HUMAN
        elif action.endswith("submit") and result.status is ActionStatus.SUBMITTED:
            status = ApplicationStatus.OFFICIAL_SUBMITTED
        else:
            status = self._failure_status(result.status)
        self.db.update_application(application_id, status, evidence=result.evidence or result.message, error=result.details.get("error"), external_id=result.external_id)

    @staticmethod
    def _failure_status(status: ActionStatus) -> ApplicationStatus:
        return {
            ActionStatus.NEEDS_LOGIN: ApplicationStatus.NEEDS_LOGIN,
            ActionStatus.NEEDS_HUMAN: ApplicationStatus.NEEDS_HUMAN,
            ActionStatus.UNVERIFIED: ApplicationStatus.UNVERIFIED,
            ActionStatus.LIMIT_REACHED: ApplicationStatus.NEEDS_HUMAN,
            ActionStatus.NOT_FOUND: ApplicationStatus.NEEDS_HUMAN,
        }.get(status, ApplicationStatus.FAILED)

    async def check_boss_replies(self, *, live_resume_send: bool = False) -> dict[str, Any]:
        applications = self.db.list_applications(status=ApplicationStatus.AWAITING_REPLY.value, channel="boss")
        connector = BossConnector(self.config.boss)
        results: list[dict[str, Any]] = []
        try:
            for application in applications:
                job = self.db.get_job(int(application["job_id"]))
                if job is None:
                    continue
                result = await connector.check_reply(job, str(application.get("greeting") or ""))
                item: dict[str, Any] = {"application_id": application["id"], "reply": result.to_dict()}
                if result.status is ActionStatus.CONFIRMED:
                    self.db.update_application(int(application["id"]), ApplicationStatus.HR_REPLIED, evidence=result.evidence)
                    if self.config.preferences.auto_send_resume_after_reply:
                        resume = await connector.send_resume(
                            job, self.config.candidate.resume_path,
                            greeting=str(application.get("greeting") or ""), live=live_resume_send,
                        )
                        item["resume"] = resume.to_dict()
                        if live_resume_send:
                            target = ApplicationStatus.RESUME_SENT if resume.status is ActionStatus.SUBMITTED else self._failure_status(resume.status)
                            self.db.update_application(int(application["id"]), target, evidence=resume.evidence or resume.message)
                results.append(item)
        finally:
            await connector.close()
        return {"checked": len(results), "results": results}

    async def send_boss_resume(self, application_id: int, *, live: bool = False) -> dict[str, Any]:
        application = self.db.get_application(application_id)
        if not application or application["channel"] != "boss":
            raise ValueError("BOSS application not found")
        if application["status"] != ApplicationStatus.HR_REPLIED.value:
            raise ValueError("Resume can only be sent after an effective HR reply")
        job = self.db.get_job(int(application["job_id"]))
        if job is None:
            raise ValueError("Job not found")
        connector = BossConnector(self.config.boss)
        try:
            result = await connector.send_resume(
                job, self.config.candidate.resume_path,
                greeting=str(application.get("greeting") or ""), live=live,
            )
        finally:
            await connector.close()
        if live:
            target = ApplicationStatus.RESUME_SENT if result.status is ActionStatus.SUBMITTED else self._failure_status(result.status)
            self.db.update_application(application_id, target, evidence=result.evidence or result.message)
        else:
            self.db.event("application", application_id, "dry_run:boss_resume", result.to_dict())
        return result.to_dict()

    def check_receipts(self) -> dict[str, Any]:
        if not self.config.mail.get("enabled", False):
            return {"checked": 0, "message": "邮件回执检查未启用", "results": []}
        checker = ImapReceiptChecker(self.config.mail)
        applications = self.db.list_applications(status=ApplicationStatus.OFFICIAL_SUBMITTED.value, channel="official")
        results: list[dict[str, Any]] = []
        for application in applications:
            since = datetime.fromisoformat(str(application["created_at"]).replace("Z", "+00:00"))
            receipt = checker.find(str(application["company"]), str(application["title"]), since)
            if receipt.matched:
                status = ApplicationStatus.CONFIRMED if receipt.positive else ApplicationStatus.REJECTED
                self.db.update_application(int(application["id"]), status, evidence=f"{receipt.subject} | {receipt.sender}")
            results.append({"application_id": application["id"], "matched": receipt.matched, "positive": receipt.positive, "subject": receipt.subject})
        return {"checked": len(results), "results": results}

    async def run_cycle(self, *, live: bool = False) -> dict[str, Any]:
        discovery = await self.discover("all")
        evaluation = self.evaluate()
        plans = self.plan_all()["plans"]
        execution: list[dict[str, Any]] = []
        if live:
            execution = (await self.execute_all(live=True))["channels"]
        return {"discovery": discovery, "evaluation": evaluation, "plans": plans, "execution": execution, "live": live}
