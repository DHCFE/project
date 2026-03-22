"""Tool wrapper around Screenpipe client."""

from __future__ import annotations


class ScreenpipeTool:
    def __init__(self, client):
        self.client = client

    def get_recent_activity(self, minutes: int):
        return self.client.get_recent_activity(minutes)
