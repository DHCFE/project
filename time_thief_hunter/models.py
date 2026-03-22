"""核心领域模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


@dataclass
class ActivityRecord:
    app_name: str
    window_name: str
    ocr_text: str
    captured_at: str
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Observation:
    observed_at: str
    lookback_minutes: int
    records_scanned: int
    distraction_hits: int
    screenshot_path: str = ""
    active_app: str = ""
    active_window: str = ""
    dominant_app: str = ""
    dominant_count: int = 0
    app_hits: dict[str, int] = field(default_factory=dict)
    keyword_hits: dict[str, int] = field(default_factory=dict)
    sample_windows: list[str] = field(default_factory=list)
    matched_records: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Classification:
    label: str
    confidence: float
    primary_app: str = ""
    evidence_count: int = 0
    severity: int = 0
    reasons: list[str] = field(default_factory=list)
    classifier_name: str = "rule-ensemble-v2"
    work_related: bool = False
    decision_source: str = "rules"

    @property
    def is_distracted(self) -> bool:
        return self.label == "distracted"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyDecision:
    action: str
    reason: str
    cooldown_seconds: int = 0
    escalation_level: str = "none"
    should_popup: bool = False
    debug_factors: dict[str, Any] = field(default_factory=dict)
    decision_source: str = "rules"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskContext:
    captured_at: str
    workspace_root: str
    repo_name: str
    git_branch: str = ""
    dirty_files: int = 0
    likely_task_type: str = "unknown"
    focus_mode: str = "normal"
    summary: str = ""
    signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InterventionPlan:
    plan_id: str
    mode: str
    priority: int
    title: str
    opening_message: str
    negotiation_brief: str
    required_commitment: str
    follow_up_minutes: int = 0
    contract_terms: list[str] = field(default_factory=list)
    context_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CycleResult:
    observation: Observation
    task_context: TaskContext
    classification: Classification
    decision: PolicyDecision
    plan: InterventionPlan

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
