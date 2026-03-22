"""本地状态和长期记忆。"""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from time_thief_hunter.config import STATE_FILE
from time_thief_hunter.models import Classification, Observation, PolicyDecision, utc_now_iso


class MemoryStore:
    def __init__(self, path: Path | None = None):
        self.path = path or STATE_FILE
        self._lock = threading.RLock()
        self.state = self._load()

    def _default_state(self) -> dict[str, Any]:
        return {
            "version": 2,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "focus_score": 100,
            "total_cycles": 0,
            "total_detections": 0,
            "total_warnings": 0,
            "total_negotiations": 0,
            "last_warning_at": None,
            "cooldown_until": None,
            "app_profiles": {},
            "recent_events": [],
            "pending_followups": [],
            "last_task_context": None,
            "active_plan": None,
            "active_negotiation": None,
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default_state()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            default = self._default_state()
            default.update(data)
            # Cooldown is runtime state; don't carry it across restarts during local testing.
            default["cooldown_until"] = None
            default["last_warning_at"] = None
            return default
        except Exception:
            return self._default_state()

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state["updated_at"] = utc_now_iso()
        self.path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.state)

    def _append_event_locked(self, event_type: str, payload: dict[str, Any]) -> None:
        self.state["recent_events"].append({
            "type": event_type,
            "timestamp": utc_now_iso(),
            "payload": payload,
        })
        self.state["recent_events"] = self.state["recent_events"][-100:]

    def _ensure_app_profile_locked(self, app: str) -> dict[str, Any]:
        if not app:
            app = "unknown"
        profiles = self.state["app_profiles"]
        if app not in profiles:
            profiles[app] = {
                "detections": 0,
                "warnings": 0,
                "negotiations": 0,
                "last_seen_at": None,
                "last_warning_at": None,
            }
        return profiles[app]

    def record_observation(self, observation: Observation) -> None:
        with self._lock:
            self.state["total_cycles"] += 1
            self._append_event_locked("observation", observation.to_dict())
            self._save_locked()

    def record_classification(
        self,
        observation: Observation,
        classification: Classification,
    ) -> None:
        with self._lock:
            if classification.is_distracted:
                self.state["total_detections"] += 1
                self.state["focus_score"] = max(
                    0,
                    self.state["focus_score"] - max(1, classification.severity),
                )
                profile = self._ensure_app_profile_locked(classification.primary_app)
                profile["detections"] += 1
                profile["last_seen_at"] = observation.observed_at

            self._append_event_locked(
                "classification",
                {
                    "observation": observation.to_dict(),
                    "classification": classification.to_dict(),
                },
            )
            self._save_locked()

    def record_task_context(self, task_context) -> None:
        with self._lock:
            self.state["last_task_context"] = task_context.to_dict()
            self._append_event_locked("task_context", task_context.to_dict())
            self._save_locked()

    def record_decision(
        self,
        classification: Classification,
        decision: PolicyDecision,
    ) -> None:
        with self._lock:
            if decision.should_popup:
                self.state["total_warnings"] += 1
                warned_at = datetime.now(timezone.utc)
                cooldown_until = warned_at + timedelta(seconds=decision.cooldown_seconds)
                self.state["last_warning_at"] = warned_at.isoformat()
                self.state["cooldown_until"] = cooldown_until.isoformat()

                profile = self._ensure_app_profile_locked(classification.primary_app)
                profile["warnings"] += 1
                profile["last_warning_at"] = warned_at.isoformat()

            self._append_event_locked(
                "decision",
                {
                    "classification": classification.to_dict(),
                    "decision": decision.to_dict(),
                },
            )
            self._save_locked()

    def is_in_cooldown(self) -> bool:
        with self._lock:
            value = self.state.get("cooldown_until")
            if not value:
                return False
            try:
                return datetime.now(timezone.utc) < datetime.fromisoformat(value)
            except ValueError:
                return False

    def app_history(self, app: str) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.state["app_profiles"].get(app, {}))

    def start_negotiation(self, context: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            app = context.get("app", "unknown")
            profile = self._ensure_app_profile_locked(app)
            profile["negotiations"] += 1
            self.state["total_negotiations"] += 1
            self.state["active_negotiation"] = {
                "started_at": utc_now_iso(),
                "context": deepcopy(context),
                "plan": deepcopy(self.state.get("active_plan")),
                "transcript": [],
            }
            self._append_event_locked("negotiation_started", deepcopy(context))
            self._save_locked()
            return deepcopy(profile)

    def append_negotiation_turn(self, role: str, message: str) -> None:
        with self._lock:
            if not self.state.get("active_negotiation"):
                return
            self.state["active_negotiation"]["transcript"].append({
                "role": role,
                "message": message,
                "timestamp": utc_now_iso(),
            })
            self._save_locked()

    def end_negotiation(self) -> None:
        with self._lock:
            if self.state.get("active_negotiation"):
                self._append_event_locked(
                    "negotiation_closed",
                    deepcopy(self.state["active_negotiation"]),
                )
                self.state["active_negotiation"] = None
                self._save_locked()

    def activate_plan(self, payload: dict[str, Any]) -> None:
        with self._lock:
            plan = deepcopy(payload.get("plan"))
            if not plan:
                return
            self.state["active_plan"] = {
                "activated_at": utc_now_iso(),
                "payload": deepcopy(payload),
            }
            follow_up_minutes = plan.get("follow_up_minutes", 0)
            if follow_up_minutes:
                self.state["pending_followups"].append({
                    "plan_id": plan.get("plan_id"),
                    "due_in_minutes": follow_up_minutes,
                    "mode": plan.get("mode"),
                    "title": plan.get("title"),
                    "created_at": utc_now_iso(),
                })
                self.state["pending_followups"] = self.state["pending_followups"][-20:]
            self._append_event_locked("plan_activated", deepcopy(self.state["active_plan"]))
            self._save_locked()
