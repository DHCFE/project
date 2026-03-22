"""Action agent: executes interruption behavior."""

from __future__ import annotations

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.models import Classification, Observation, PolicyDecision


class ActionAgent(BaseAgent):
    def __init__(self, popup_manager, event_bus=None):
        super().__init__("action-agent", event_bus)
        self.popup_manager = popup_manager

    def execute(
        self,
        observation: Observation,
        classification: Classification,
        decision: PolicyDecision,
    ) -> bool:
        if not decision.should_popup:
            self.emit(
                "action.skipped",
                {
                    "app": classification.primary_app,
                    "action": decision.action,
                    "reason": decision.reason,
                },
            )
            return False

        self.popup_manager.trigger_warning(
            classification.primary_app or observation.dominant_app or "Unknown app",
            observation.dominant_count,
        )
        self.emit(
            "action.executed",
            {
                "app": classification.primary_app,
                "count": observation.dominant_count,
                "escalation_level": decision.escalation_level,
            },
        )
        return True
