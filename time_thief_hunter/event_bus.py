"""轻量事件总线。"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Callable

from time_thief_hunter.models import utc_now_iso


EventHandler = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self, max_history: int = 200):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: deque[dict[str, Any]] = deque(maxlen=max_history)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "name": event_name,
            "timestamp": utc_now_iso(),
            "payload": payload,
        }
        self._history.append(event)

        for handler in self._subscribers.get(event_name, []):
            handler(event)

        for handler in self._subscribers.get("*", []):
            handler(event)

        return event

    def recent_events(self) -> list[dict[str, Any]]:
        return list(self._history)
