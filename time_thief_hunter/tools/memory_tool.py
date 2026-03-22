"""Tool wrapper around the persistent memory store."""

from __future__ import annotations


class MemoryTool:
    def __init__(self, store):
        self.store = store

    def snapshot(self):
        return self.store.snapshot()

    def record_observation(self, observation):
        self.store.record_observation(observation)

    def record_task_context(self, task_context):
        self.store.record_task_context(task_context)

    def record_classification(self, observation, classification):
        self.store.record_classification(observation, classification)

    def record_decision(self, classification, decision):
        self.store.record_decision(classification, decision)

    def activate_plan(self, payload):
        self.store.activate_plan(payload)

    def start_negotiation(self, context):
        return self.store.start_negotiation(context)

    def append_negotiation_turn(self, role, message):
        self.store.append_negotiation_turn(role, message)

    def end_negotiation(self):
        self.store.end_negotiation()
