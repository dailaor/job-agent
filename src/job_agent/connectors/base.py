from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from ..models import Job


class ActionStatus(StrEnum):
    OK = "ok"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    ALREADY_DONE = "already_done"
    NEEDS_LOGIN = "needs_login"
    NEEDS_HUMAN = "needs_human"
    LIMIT_REACHED = "limit_reached"
    NOT_FOUND = "not_found"
    UNVERIFIED = "unverified"
    FAILED = "failed"


@dataclass(slots=True)
class ActionResult:
    status: ActionStatus
    message: str
    evidence: str = ""
    external_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class JobConnector(Protocol):
    source: str

    async def discover(self, keywords: list[str]) -> list[Job]: ...

    async def close(self) -> None: ...
