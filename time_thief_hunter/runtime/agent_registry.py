"""In-process agent registry and dispatcher."""

from __future__ import annotations

from typing import Any

from time_thief_hunter.runtime.messages import AgentMessage


class AgentRegistry:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self._agents: dict[str, Any] = {}

    def register(self, name: str, agent: Any) -> None:
        self._agents[name] = agent
        if self.event_bus:
            self.event_bus.publish("runtime.agent_registered", {"agent": name})

    def dispatch(self, message: AgentMessage) -> dict[str, Any]:
        agent = self._agents[message.recipient]
        if self.event_bus:
            self.event_bus.publish("runtime.message_dispatched", message.to_dict())
        response = agent.handle(message)
        if self.event_bus:
            self.event_bus.publish(
                "runtime.message_completed",
                {
                    "message": message.to_dict(),
                    "response_keys": sorted(response.keys()),
                },
            )
        return response
