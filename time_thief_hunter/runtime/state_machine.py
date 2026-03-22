"""Workflow run state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from time_thief_hunter.models import utc_now_iso


@dataclass
class WorkflowRunState:
    workflow_name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    phase: str = "idle"
    artifacts: dict[str, Any] = field(default_factory=dict)

    def set_phase(self, phase: str) -> None:
        self.phase = phase

    def store(self, key: str, value: Any) -> None:
        self.artifacts[key] = value
