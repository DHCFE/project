"""Agent 基类。"""

from __future__ import annotations

from typing import Any

from time_thief_hunter.event_bus import EventBus


class BaseAgent:
    def __init__(self, name: str, event_bus: EventBus | None = None):
        self.name = name
        self.event_bus = event_bus

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            self.event_bus.publish(event_name, payload)

    def handle(self, message):
        raise NotImplementedError(f"{self.name} does not implement runtime message handling")
