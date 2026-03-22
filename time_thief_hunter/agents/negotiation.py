"""Negotiation agent: wraps AI dialogue and memory writes."""

from __future__ import annotations

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.brain import AgentBrain


class NegotiationAgent(BaseAgent):
    def __init__(self, brain: AgentBrain, memory_tool, event_bus=None):
        super().__init__("negotiation-agent", event_bus)
        self.brain = brain
        self.memory_tool = memory_tool

    def start_negotiation(self, context: dict) -> None:
        app_profile = self.memory_tool.start_negotiation(context)
        enriched_context = dict(context)
        enriched_context["app_profile"] = app_profile
        enriched_context["memory_snapshot"] = self.memory_tool.snapshot()
        active_plan = enriched_context["memory_snapshot"].get("active_plan")
        if active_plan:
            enriched_context["active_plan"] = active_plan.get("payload", {}).get("plan")
        self.brain.start_negotiation(enriched_context)
        self.emit("negotiation.started", enriched_context)

    def negotiate(self, user_message: str) -> str:
        self.memory_tool.append_negotiation_turn("user", user_message)
        reply = self.brain.negotiate(user_message)
        self.memory_tool.append_negotiation_turn("assistant", reply)
        self.emit(
            "negotiation.turn_completed",
            {"user_message": user_message, "reply": reply},
        )
        return reply

    def reset(self) -> None:
        self.memory_tool.end_negotiation()
        self.brain.reset()
        self.emit("negotiation.closed", {})
