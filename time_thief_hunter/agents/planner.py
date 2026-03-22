"""Planner agent: builds intervention plans from risk and task context."""

from __future__ import annotations

import uuid

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.runtime.prompt_loader import load_prompt
from time_thief_hunter.models import (
    Classification,
    InterventionPlan,
    Observation,
    PolicyDecision,
    TaskContext,
)


class PlannerAgent(BaseAgent):
    def __init__(self, memory_tool=None, event_bus=None):
        super().__init__("planner-agent", event_bus)
        self.memory_tool = memory_tool
        self.planner_prompt = load_prompt("planner.md")

    def plan(
        self,
        observation: Observation,
        task_context: TaskContext,
        classification: Classification,
        decision: PolicyDecision,
        memory_snapshot: dict,
    ) -> InterventionPlan:
        app = classification.primary_app or observation.dominant_app or "Unknown app"
        app_profile = memory_snapshot.get("app_profiles", {}).get(app, {})
        warnings = app_profile.get("warnings", 0)

        if decision.escalation_level == "hard-stop":
            mode = "containment"
            title = "Hard Stop Protocol"
            priority = 95
            follow_up_minutes = 10
        elif decision.escalation_level == "intervention":
            mode = "contract"
            title = "Intervention Contract"
            priority = 80
            follow_up_minutes = 15
        else:
            mode = "nudge"
            title = "Focus Recovery"
            priority = 60
            follow_up_minutes = 20

        commitment = (
            f"Return to {task_context.likely_task_type} work within {follow_up_minutes} minutes "
            f"and commit to one concrete output."
        )
        opening_message = (
            f"You should not be drifting inside {app} right now. "
            f"Your current work context is {task_context.summary}. "
            f"Requirement: {commitment}"
        )
        negotiation_brief = (
            f"Prior warnings: {warnings}. Current risk: {classification.severity}/5. "
            f"Policy mode: {mode}. Planning rule: {self.planner_prompt.splitlines()[0]}"
        )
        contract_terms = [
            f"State exactly one concrete next task tied to {task_context.repo_name or 'the current project'}.",
            f"You may request up to {min(15, follow_up_minutes)} extra minutes, but only in exchange for a verifiable commitment.",
            "If you keep bargaining without substance, the next intervention escalates.",
        ]

        if task_context.signals.get("on_main_branch"):
            contract_terms.append(
                "You are working near the main branch, so the risk is higher and vague excuses are not accepted."
            )

        plan = InterventionPlan(
            plan_id=str(uuid.uuid4()),
            mode=mode,
            priority=priority,
            title=title,
            opening_message=opening_message,
            negotiation_brief=negotiation_brief,
            required_commitment=commitment,
            follow_up_minutes=follow_up_minutes,
            contract_terms=contract_terms,
            context_summary=task_context.summary,
            metadata={
                "app": app,
                "warnings": warnings,
                "focus_mode": task_context.focus_mode,
                "task_type": task_context.likely_task_type,
            },
        )
        self.emit("planner.completed", plan.to_dict())
        return plan

    def handle(self, message):
        if message.message_type != "plan.intervention":
            raise ValueError(f"Unsupported message for {self.name}: {message.message_type}")
        observation = Observation(**message.payload["observation"])
        task_context = TaskContext(**message.payload["task_context"])
        classification = Classification(**message.payload["classification"])
        decision = PolicyDecision(**message.payload["decision"])
        memory_snapshot = self.memory_tool.snapshot() if self.memory_tool else {}
        plan = self.plan(observation, task_context, classification, decision, memory_snapshot)
        return {"plan": plan.to_dict()}
