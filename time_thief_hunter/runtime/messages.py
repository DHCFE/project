"""Typed message envelope for inter-agent communication."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import uuid

from time_thief_hunter.models import utc_now_iso


@dataclass
class AgentMessage:
    message_type: str
    recipient: str
    payload: dict[str, Any]
    sender: str = "runtime"
    correlation_id: str = ""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
