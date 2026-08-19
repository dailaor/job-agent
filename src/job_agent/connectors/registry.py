from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from importlib.util import find_spec
from typing import Any
from urllib.parse import urlparse

from ..config import AgentConfig
from .base import JobConnector
from .boss import BossConnector
from .campus import CampusPortalConnector, SUPPORTED_CAMPUS_ADAPTERS
from .official import OfficialSiteConnector


ConnectorFactory = Callable[[], JobConnector]
ChannelProvider = Callable[[AgentConfig], Iterable["ChannelAdapter"]]


def _browser_runtime_available() -> bool:
    return find_spec("playwright") is not None


@dataclass(slots=True)
class ChannelAdapter:
    """One discoverable job source exposed to the orchestration layer."""

    id: str
    name: str
    channel_type: str
    enabled: bool
    keywords: list[str]
    strategy: str
    url: str
    connector_factory: ConnectorFactory | None
    missing: list[str] = field(default_factory=list)
    success_status: str = "api_fetched"
    allowed_hosts: set[str] = field(default_factory=set)
    daily_limit: int | None = None
    capabilities: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.enabled and self.connector_factory is not None and not self.missing


class ChannelRegistry:
    """A small, injectable registry that keeps channel branching out of JobAgent."""

    def __init__(self, adapters: Iterable[ChannelAdapter] = ()) -> None:
        self._adapters: dict[str, ChannelAdapter] = {}
        self.load_errors: list[str] = []
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: ChannelAdapter) -> None:
        channel_id = adapter.id.strip()
        if not channel_id:
            raise ValueError("Channel adapter id is required")
        if channel_id in self._adapters:
            raise ValueError(f"Duplicate channel adapter id: {channel_id}")
        if adapter.success_status not in {"api_fetched", "browser_fetched"}:
            raise ValueError("success_status must be api_fetched or browser_fetched")
        if adapter.daily_limit is not None and not 0 <= adapter.daily_limit <= 100:
            raise ValueError("daily_limit must be between 0 and 100")
        adapter.allowed_hosts = {
            str(host).strip().lower()
            for host in adapter.allowed_hosts
            if str(host).strip()
        }
        configured_host = (urlparse(adapter.url).hostname or "").lower()
        if configured_host:
            adapter.allowed_hosts.add(configured_host)
        adapter.id = channel_id
        self._adapters[channel_id] = adapter

    def get(self, channel_id: str) -> ChannelAdapter | None:
        return self._adapters.get(channel_id)

    def all(self) -> list[ChannelAdapter]:
        return list(self._adapters.values())


def _boss_provider(config: AgentConfig) -> Iterable[ChannelAdapter]:
    enabled = config.boss.get("enabled", False) is True
    missing: list[str] = []
    if not enabled:
        missing.append("需要启用 BOSS 渠道")
    elif not config.preferences.boss_keywords:
        missing.append("需要配置 BOSS 关键词")
    if enabled and not _browser_runtime_available():
        missing.append("当前版本未包含 Playwright 浏览器运行时，请从源码安装 browser 可选依赖")
    yield ChannelAdapter(
        id="boss",
        name="BOSS直聘",
        channel_type="boss",
        enabled=enabled,
        keywords=list(config.preferences.boss_keywords),
        strategy="browser",
        url="https://www.zhipin.com/web/geek/jobs",
        connector_factory=(lambda: BossConnector(config.boss)) if enabled and not missing else None,
        missing=missing,
        success_status="browser_fetched",
        allowed_hosts={"zhipin.com", "www.zhipin.com"},
        daily_limit=config.preferences.boss_daily_limit,
        capabilities={"discovery": "browser_optional", "autofill_status": "not_planned"},
    )


def _official_provider(config: AgentConfig) -> Iterable[ChannelAdapter]:
    for definition in config.official_sites:
        site_id = str(definition.get("id", "")).strip()
        enabled = definition.get("enabled", True) is True
        strategy = str(definition.get("strategy") or "")
        campus_adapter = str(definition.get("adapter") or "").strip()
        required = [
            label
            for value, label in (
                (site_id, "渠道 ID"),
                (definition.get("list_url"), "岗位列表地址"),
                (definition.get("strategy"), "抓取方式"),
            )
            if not value
        ]
        if not enabled:
            required = ["渠道未启用"]
        elif strategy == "browser" and not _browser_runtime_available():
            required.append("当前版本未包含 Playwright 浏览器运行时，请从源码安装 browser 可选依赖")
        elif strategy == "campus_api" and not campus_adapter:
            required.append("需要配置 campus_api 的 adapter")
        elif strategy == "campus_api" and campus_adapter not in SUPPORTED_CAMPUS_ADAPTERS:
            required.append(f"未知校园官网适配器：{campus_adapter}")
        source = f"official:{site_id}" if site_id else "official:invalid"
        factory: ConnectorFactory | None = None
        if enabled and not required:
            connector_type = CampusPortalConnector if strategy == "campus_api" else OfficialSiteConnector
            factory = lambda definition=definition, connector_type=connector_type: connector_type(definition)
        autofill = dict(definition.get("autofill") or {})
        yield ChannelAdapter(
            id=source,
            name=str(definition.get("name") or site_id or "未命名官网渠道"),
            channel_type="official",
            enabled=enabled,
            keywords=list(config.preferences.official_keywords),
            strategy=strategy or "未配置",
            url=str(definition.get("list_url", "")),
            connector_factory=factory,
            missing=required,
            success_status="browser_fetched" if strategy == "browser" else "api_fetched",
            allowed_hosts={
                str(host).strip().lower()
                for host in (definition.get("allowed_hosts") or [])
                if str(host).strip()
            },
            daily_limit=config.preferences.official_daily_limit,
            capabilities={
                "discovery": "available" if strategy in {"campus_api", "json_api"} else "browser_optional",
                "autofill_status": str(autofill.get("status") or ("experimental" if definition.get("form") else "planned")),
                "autofill_profile": str(autofill.get("profile") or ""),
                "autofill_allowed_hosts": list(autofill.get("allowed_hosts") or []),
            },
        )


DEFAULT_PROVIDERS: tuple[ChannelProvider, ...] = (_boss_provider, _official_provider)


def build_channel_registry(
    config: AgentConfig,
    *,
    providers: Iterable[ChannelProvider] = DEFAULT_PROVIDERS,
    load_entry_points: bool = True,
) -> ChannelRegistry:
    """Build the configured channel set and optionally load external providers.

    Third-party packages can expose a provider through the
    ``job_agent.channels`` entry-point group. A provider receives AgentConfig and
    returns one or more ChannelAdapter objects.
    """

    registry = ChannelRegistry()
    provider_list = list(providers)
    if load_entry_points:
        for item in entry_points(group="job_agent.channels"):
            try:
                provider_list.append(item.load())
            except Exception as exc:  # A broken optional adapter must not stop the local app.
                registry.load_errors.append(f"{item.name}: {type(exc).__name__}: {exc}")
    for provider in provider_list:
        try:
            for adapter in provider(config):
                registry.register(adapter)
        except Exception as exc:
            name = getattr(provider, "__name__", repr(provider))
            registry.load_errors.append(f"{name}: {type(exc).__name__}: {exc}")
    return registry
