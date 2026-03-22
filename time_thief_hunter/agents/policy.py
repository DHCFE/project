"""Policy agent: decides whether to ignore, cool down, or intervene."""

from __future__ import annotations

from datetime import datetime

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.config import (
    BASE_COOLDOWN_SECONDS,
    WORKDAY_END_HOUR,
    WORKDAY_START_HOUR,
)
from time_thief_hunter.models import Classification, Observation, PolicyDecision, TaskContext


class PolicyAgent(BaseAgent):
    def __init__(self, memory_tool=None, decision_engine=None, event_bus=None):
        super().__init__("policy-agent", event_bus)
        self.memory_tool = memory_tool
        self.decision_engine = decision_engine

    def _is_work_hours(self, observed_at: str) -> bool:
        dt = datetime.fromisoformat(observed_at)
        return WORKDAY_START_HOUR <= dt.hour < WORKDAY_END_HOUR

    def decide(
        self,
        observation: Observation,
        task_context: TaskContext,
        classification: Classification,
        memory_snapshot: dict,
    ) -> PolicyDecision:
        debug = {
            "confidence": classification.confidence,
            "severity": classification.severity,
            "focus_score": memory_snapshot.get("focus_score"),
            "cooldown_until": memory_snapshot.get("cooldown_until"),
            "work_related": classification.work_related,
            "task_type": task_context.likely_task_type,
            "focus_mode": task_context.focus_mode,
            "classifier": classification.classifier_name,
        }

        if classification.label == "focused":
            decision = PolicyDecision(
                action="ignore",
                reason="No stable distraction signal was observed.",
                debug_factors=debug,
            )
            self.emit("policy.completed", decision.to_dict())
            return decision

        if classification.label == "suspicious":
            decision = PolicyDecision(
                action="observe",
                reason="Suspicious, but not strong enough yet. Keep monitoring.",
                debug_factors=debug,
            )
            self.emit("policy.completed", decision.to_dict())
            return decision

        cooldown_until = memory_snapshot.get("cooldown_until")
        if cooldown_until:
            cooldown_dt = datetime.fromisoformat(cooldown_until)
            observed_dt = datetime.fromisoformat(observation.observed_at)
            if cooldown_dt > observed_dt:
                decision = PolicyDecision(
                    action="cooldown",
                    reason="Still inside the cooldown window, so repeated popups are suppressed.",
                    debug_factors=debug,
                )
                self.emit("policy.completed", decision.to_dict())
                return decision

        app_profile = memory_snapshot.get("app_profiles", {}).get(classification.primary_app, {})
        repeat_warnings = app_profile.get("warnings", 0)
        escalation = "soft-stop"
        cooldown_seconds = BASE_COOLDOWN_SECONDS

        if classification.work_related and classification.severity <= 2:
            escalation = "soft-stop"
        elif classification.severity >= 4 or repeat_warnings >= 3:
            escalation = "hard-stop"
        elif classification.severity >= 2:
            escalation = "intervention"

        action = "warn"
        if escalation == "intervention":
            action = "focus_ide"
        elif escalation == "hard-stop":
            action = "hard_stop"

        decision = PolicyDecision(
            action=action,
            reason=f"Risk level {classification.severity} triggered {escalation}.",
            cooldown_seconds=cooldown_seconds,
            escalation_level=escalation,
            should_popup=True,
            debug_factors=debug,
        )
        should_consult_ai = (
            self.decision_engine is not None
            and self.decision_engine.enabled
            and classification.label != "focused"
        )
        if should_consult_ai:
            ai_result = self.decision_engine.decide_policy({
                "observation": observation.to_dict(),
                "task_context": task_context.to_dict(),
                "classification": classification.to_dict(),
                "memory_snapshot": {
                    "focus_score": memory_snapshot.get("focus_score"),
                    "cooldown_until": memory_snapshot.get("cooldown_until"),
                    "app_profile": app_profile,
                },
                "rule_policy": decision.to_dict(),
            })
            if ai_result:
                valid_actions = {"ignore", "observe", "cooldown", "warn", "focus_ide", "hard_stop", "slack_report", "close_browser"}
                valid_escalations = {"none", "soft-stop", "intervention", "hard-stop"}
                action = str(ai_result.get("action", decision.action)).strip() or decision.action
                escalation_level = str(ai_result.get("escalation_level", decision.escalation_level)).strip() or decision.escalation_level
                if action not in valid_actions:
                    action = decision.action
                if escalation_level not in valid_escalations:
                    escalation_level = decision.escalation_level
                try:
                    cooldown_seconds = max(0, int(ai_result.get("cooldown_seconds", decision.cooldown_seconds)))
                except (TypeError, ValueError):
                    cooldown_seconds = decision.cooldown_seconds
                should_popup = bool(ai_result.get("should_popup", decision.should_popup))
                reason = str(ai_result.get("reason", decision.reason)).strip() or decision.reason
                debug["ai_override"] = True
                decision = PolicyDecision(
                    action=action,
                    reason=reason,
                    cooldown_seconds=cooldown_seconds,
                    escalation_level=escalation_level,
                    should_popup=should_popup,
                    debug_factors=debug,
                    decision_source="ai",
                )
        self.emit("policy.completed", decision.to_dict())
        return decision

    def handle(self, message):
        if message.message_type != "decide.policy":
            raise ValueError(f"Unsupported message for {self.name}: {message.message_type}")
        observation = Observation(**message.payload["observation"])
        task_context = TaskContext(**message.payload["task_context"])
        classification = Classification(**message.payload["classification"])
        memory_snapshot = self.memory_tool.snapshot() if self.memory_tool else {}
        decision = self.decide(observation, task_context, classification, memory_snapshot)
        if self.memory_tool:
            self.memory_tool.record_decision(classification, decision)
        return {"decision": decision.to_dict()}
