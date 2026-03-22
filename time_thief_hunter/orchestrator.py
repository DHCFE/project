"""Multi-agent orchestrator."""

from __future__ import annotations

import time
from typing import Callable

from time_thief_hunter.models import (
    Classification,
    CycleResult,
    InterventionPlan,
    Observation,
    PolicyDecision,
    TaskContext,
)


class HunterOrchestrator:
    def __init__(
        self,
        workflow_executor,
        check_interval: int,
        event_bus=None,
        pause_predicate: Callable[[], bool] | None = None,
    ):
        self.workflow_executor = workflow_executor
        self.event_bus = event_bus
        self.check_interval = check_interval
        self.pause_predicate = pause_predicate or (lambda: False)
        self.state = "idle"

    def run_cycle(self) -> CycleResult:
        self.state = "workflow-running"
        self.event_bus.publish("cycle.started", {})
        workflow_state, artifacts = self.workflow_executor.run("intervention")
        self.state = workflow_state.phase

        observation = Observation(**artifacts["observation_result"]["observation"])
        task_context = TaskContext(**artifacts["task_context_result"]["task_context"])
        classification = Classification(**artifacts["classification_result"]["classification"])
        decision = PolicyDecision(**artifacts["policy_result"]["decision"])
        plan = InterventionPlan(**artifacts["plan_result"]["plan"])
        executed = artifacts["enforcement_result"]["executed"]
        result = CycleResult(
            observation=observation,
            task_context=task_context,
            classification=classification,
            decision=decision,
            plan=plan,
        )
        self.state = "idle"
        self.event_bus.publish(
            "cycle.completed",
            {
                "executed": executed,
                "run_id": workflow_state.run_id,
                "state": workflow_state.phase,
                "result": result.to_dict(),
            },
        )
        return result

    def run_forever(self) -> None:
        print("Time Thief Hunter is running.")
        print("Architecture mode: multi-agent orchestration")
        print(f"Dispatch interval: every {self.check_interval} seconds")
        print("Close the terminal or press Ctrl+C to exit.\n")

        while True:
            if self.pause_predicate():
                self.event_bus.publish("cycle.paused", {"reason": "popup-active"})
            else:
                result = self.run_cycle()
                if result.decision.should_popup:
                    print(
                        f"[warn] {result.classification.primary_app} "
                        f"severity={result.classification.severity} "
                        f"action={result.decision.escalation_level} "
                        f"plan={result.plan.mode}"
                    )
                else:
                    print(
                        f"[{result.classification.label}] "
                        f"confidence={result.classification.confidence} "
                        f"reason={result.decision.reason} "
                        f"context={result.task_context.likely_task_type}"
                    )

            time.sleep(self.check_interval)
