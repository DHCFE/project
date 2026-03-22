"""Workflow graph for distraction intervention."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class WorkflowStep:
    name: str
    recipient: str
    message_type: str
    result_key: str
    build_payload: Callable[[dict], dict]


class InterventionWorkflowGraph:
    def steps(self, workflow_name: str):
        if workflow_name != "intervention":
            raise ValueError(f"Unknown workflow: {workflow_name}")

        return [
            WorkflowStep(
                name="observe",
                recipient="perception-agent",
                message_type="observe.activity",
                result_key="observation_result",
                build_payload=lambda artifacts: {},
            ),
            WorkflowStep(
                name="inspect-task-context",
                recipient="task-context-agent",
                message_type="inspect.task_context",
                result_key="task_context_result",
                build_payload=lambda artifacts: {},
            ),
            WorkflowStep(
                name="classify",
                recipient="classification-agent",
                message_type="classify.distraction",
                result_key="classification_result",
                build_payload=lambda artifacts: {
                    "observation": artifacts["observation_result"]["observation"],
                    "task_context": artifacts["task_context_result"]["task_context"],
                },
            ),
            WorkflowStep(
                name="policy",
                recipient="policy-agent",
                message_type="decide.policy",
                result_key="policy_result",
                build_payload=lambda artifacts: {
                    "observation": artifacts["observation_result"]["observation"],
                    "task_context": artifacts["task_context_result"]["task_context"],
                    "classification": artifacts["classification_result"]["classification"],
                },
            ),
            WorkflowStep(
                name="plan",
                recipient="planner-agent",
                message_type="plan.intervention",
                result_key="plan_result",
                build_payload=lambda artifacts: {
                    "observation": artifacts["observation_result"]["observation"],
                    "task_context": artifacts["task_context_result"]["task_context"],
                    "classification": artifacts["classification_result"]["classification"],
                    "decision": artifacts["policy_result"]["decision"],
                },
            ),
            WorkflowStep(
                name="enforce",
                recipient="enforcement-agent",
                message_type="execute.intervention",
                result_key="enforcement_result",
                build_payload=lambda artifacts: {
                    "observation": artifacts["observation_result"]["observation"],
                    "task_context": artifacts["task_context_result"]["task_context"],
                    "classification": artifacts["classification_result"]["classification"],
                    "decision": artifacts["policy_result"]["decision"],
                    "plan": artifacts["plan_result"]["plan"],
                },
            ),
        ]
