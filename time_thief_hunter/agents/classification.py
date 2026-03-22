"""Classification agent: scores distraction risk from observation and memory."""

from __future__ import annotations

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.models import Classification, Observation, TaskContext


class ClassificationAgent(BaseAgent):
    BROWSER_APPS = {
        "Safari",
        "Google Chrome",
        "Arc",
        "Brave Browser",
        "Microsoft Edge",
        "Firefox",
        "Zen Browser",
        "Opera",
    }

    def __init__(self, threshold: int, memory_tool=None, decision_engine=None, event_bus=None):
        super().__init__("classification-agent", event_bus)
        self.threshold = threshold
        self.memory_tool = memory_tool
        self.decision_engine = decision_engine

    def _build_rule_classification(
        self,
        observation: Observation,
        memory_snapshot: dict,
    ) -> Classification:
        primary_app = observation.dominant_app or observation.active_app
        app_profile = memory_snapshot.get("app_profiles", {}).get(primary_app, {})
        repeat_warnings = app_profile.get("warnings", 0)
        repeat_detections = app_profile.get("detections", 0)

        reasons: list[str] = []
        severity = 0
        confidence = 0.05
        label = "focused"

        if observation.distraction_hits > 0:
            reasons.append(f"Detected {observation.distraction_hits} suspicious records.")
            confidence += min(0.35, observation.distraction_hits * 0.05)

        if observation.dominant_count >= self.threshold:
            label = "distracted"
            severity += 2
            confidence += 0.35
            reasons.append(
                f"Dominant distraction app {primary_app or 'unknown'} appeared {observation.dominant_count} times."
            )
        elif observation.distraction_hits > 0:
            label = "suspicious"
            severity += 1
            confidence += 0.15
            reasons.append("Reached the suspicious threshold, but not the hard-stop threshold.")

        if observation.keyword_hits:
            severity += 1
            confidence += min(0.15, len(observation.keyword_hits) * 0.03)
            reasons.append(f"Matched {len(observation.keyword_hits)} distraction keywords.")

        if repeat_detections:
            severity += min(2, repeat_detections // 3)
            confidence += min(0.08, repeat_detections * 0.01)
            reasons.append(f"Seen repeatedly in history: {repeat_detections} times.")

        if repeat_warnings:
            severity += min(2, repeat_warnings // 2)
            confidence += min(0.1, repeat_warnings * 0.02)
            reasons.append(f"Previously warned {repeat_warnings} times.")

        severity = min(5, severity)
        confidence = round(min(0.99, confidence), 2)

        return Classification(
            label=label,
            confidence=confidence,
            primary_app=primary_app,
            evidence_count=observation.distraction_hits,
            severity=severity,
            reasons=reasons,
        )

    def classify(
        self,
        observation: Observation,
        task_context: TaskContext,
        memory_snapshot: dict,
    ) -> Classification:
        classification = self._build_rule_classification(observation, memory_snapshot)
        should_consult_ai = (
            self.decision_engine is not None
            and self.decision_engine.enabled
            and (
                bool(observation.screenshot_path)
                or observation.distraction_hits > 0
                or observation.keyword_hits
                or classification.label != "focused"
            )
        )
        if should_consult_ai:
            ai_result = self.decision_engine.classify({
                "observation": observation.to_dict(),
                "task_context": task_context.to_dict(),
                "memory_snapshot": {
                    "focus_score": memory_snapshot.get("focus_score"),
                    "cooldown_until": memory_snapshot.get("cooldown_until"),
                    "app_profile": memory_snapshot.get("app_profiles", {}).get(classification.primary_app, {}),
                },
                "rule_classification": classification.to_dict(),
            }, image_path=observation.screenshot_path)
            if ai_result:
                valid_labels = {"focused", "suspicious", "distracted"}
                ai_label = str(ai_result.get("label", classification.label)).strip() or classification.label
                if ai_label not in valid_labels:
                    ai_label = classification.label
                ai_confidence = ai_result.get("confidence", classification.confidence)
                ai_severity = ai_result.get("severity", classification.severity)
                try:
                    ai_confidence = round(min(0.99, max(0.0, float(ai_confidence))), 2)
                except (TypeError, ValueError):
                    ai_confidence = classification.confidence
                try:
                    ai_severity = min(5, max(0, int(ai_severity)))
                except (TypeError, ValueError):
                    ai_severity = classification.severity
                ai_reason = str(ai_result.get("reason", "")).strip()
                ai_work_related = bool(ai_result.get("work_related"))
                primary_app = classification.primary_app or observation.active_app
                if (
                    ai_label == "suspicious"
                    and ai_severity >= 3
                    and not ai_work_related
                    and primary_app in self.BROWSER_APPS
                ):
                    ai_label = "distracted"
                    ai_confidence = max(ai_confidence, 0.78)
                    ai_reason = ai_reason or "The browser content appears unrelated to the current work, so the state was escalated to distracted."
                merged_reasons = list(classification.reasons)
                if ai_reason:
                    merged_reasons.insert(0, f"AI judgement: {ai_reason}")
                classification = Classification(
                    label=ai_label,
                    confidence=ai_confidence,
                    primary_app=primary_app,
                    evidence_count=classification.evidence_count,
                    severity=ai_severity,
                    reasons=merged_reasons,
                    classifier_name="ai-hybrid-v1",
                    work_related=ai_work_related,
                    decision_source="ai",
                )
        self.emit("classification.completed", classification.to_dict())
        return classification

    def handle(self, message):
        if message.message_type != "classify.distraction":
            raise ValueError(f"Unsupported message for {self.name}: {message.message_type}")
        observation_data = message.payload["observation"]
        observation = Observation(**observation_data)
        task_context = TaskContext(**message.payload["task_context"])
        memory_snapshot = self.memory_tool.snapshot() if self.memory_tool else {}
        classification = self.classify(observation, task_context, memory_snapshot)
        if self.memory_tool:
            self.memory_tool.record_classification(observation, classification)
        return {"classification": classification.to_dict()}
