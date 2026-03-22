"""Workflow executor that routes typed messages through the registry."""

from __future__ import annotations

from time_thief_hunter.runtime.messages import AgentMessage
from time_thief_hunter.runtime.state_machine import WorkflowRunState


class WorkflowExecutor:
    def __init__(self, registry, graph, trace_recorder, event_bus=None):
        self.registry = registry
        self.graph = graph
        self.trace_recorder = trace_recorder
        self.event_bus = event_bus

    def run(self, workflow_name: str, seed_payload: dict | None = None):
        state = WorkflowRunState(workflow_name=workflow_name)
        artifacts = dict(seed_payload or {})

        for step in self.graph.steps(workflow_name):
            state.set_phase(step.name)
            state.store("phase", step.name)
            message = AgentMessage(
                message_type=step.message_type,
                sender="workflow-executor",
                recipient=step.recipient,
                correlation_id=state.run_id,
                payload=step.build_payload(artifacts),
            )
            response = self.registry.dispatch(message)
            artifacts.update(response)
            artifacts[step.result_key] = response
            state.store(step.result_key, response)
            self.trace_recorder.write(
                state.run_id,
                step.name,
                {
                    "message": message.to_dict(),
                    "response": response,
                },
            )
            if self.event_bus:
                self.event_bus.publish(
                    "runtime.step_completed",
                    {
                        "run_id": state.run_id,
                        "step": step.name,
                        "recipient": step.recipient,
                    },
                )

        return state, artifacts
