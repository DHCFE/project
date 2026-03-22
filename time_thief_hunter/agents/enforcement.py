"""Enforcement agent: records plans, schedules follow-ups, and drives the UI."""

from __future__ import annotations

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.models import (
    Classification,
    InterventionPlan,
    Observation,
    PolicyDecision,
    TaskContext,
)


class EnforcementAgent(BaseAgent):
    def __init__(self, popup_tool, memory_tool, ide_tool=None, desktop_control_tool=None, event_bus=None):
        super().__init__("enforcement-agent", event_bus)
        self.popup_tool = popup_tool
        self.memory_tool = memory_tool
        self.ide_tool = ide_tool
        self.desktop_control_tool = desktop_control_tool

    def run_confirmed_action(self, payload: dict) -> dict:
        decision_payload = payload.get("decision", {})
        action = decision_payload.get("action", "")
        action_log = {
            "action": action,
            "app": payload.get("app", "Unknown app"),
            "browser_hidden": False,
            "ide_activated": False,
        }
        if action in {"focus_ide", "hard_stop", "close_browser"} and self.desktop_control_tool:
            action_log["browser_hidden"] = self.desktop_control_tool.hide_frontmost_browser()
        if action in {"focus_ide", "hard_stop"} and self.ide_tool:
            action_log["ide_activated"] = self.ide_tool.activate()
        self.emit("enforcement.desktop_control", action_log)
        return action_log

    def execute(
        self,
        observation: Observation,
        task_context: TaskContext,
        classification: Classification,
        decision: PolicyDecision,
        plan: InterventionPlan,
    ) -> bool:
        action_log = {
            "action": decision.action,
            "escalation_level": decision.escalation_level,
            "app": classification.primary_app or observation.active_app or observation.dominant_app or "Unknown app",
        }

        if not decision.should_popup:
            if decision.action in {"focus_ide", "hard_stop", "close_browser"}:
                confirmed = self.run_confirmed_action({
                    "app": action_log["app"],
                    "decision": decision.to_dict(),
                })
                action_log.update(confirmed)
            self.emit(
                "enforcement.skipped",
                {
                    "action": decision.action,
                    "reason": decision.reason,
                    "plan_mode": plan.mode,
                },
            )
            return False

        payload = {
            "app": classification.primary_app or observation.active_app or observation.dominant_app or "Unknown app",
            "count": observation.dominant_count,
            "plan": plan.to_dict(),
            "task_context": task_context.to_dict(),
            "classification": classification.to_dict(),
            "decision": decision.to_dict(),
        }
        self.memory_tool.activate_plan(payload)
        self.popup_tool.trigger_warning(payload)
        self.emit("enforcement.executed", payload)
        return True

    def handle(self, message):
        if message.message_type != "execute.intervention":
            raise ValueError(f"Unsupported message for {self.name}: {message.message_type}")
        observation = Observation(**message.payload["observation"])
        task_context = TaskContext(**message.payload["task_context"])
        classification = Classification(**message.payload["classification"])
        decision = PolicyDecision(**message.payload["decision"])
        plan = InterventionPlan(**message.payload["plan"])
        executed = self.execute(observation, task_context, classification, decision, plan)
        return {"executed": executed, "plan": plan.to_dict()}
