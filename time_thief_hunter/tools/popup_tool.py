"""Tool wrapper around popup UI."""

from __future__ import annotations


class PopupTool:
    def __init__(self, popup_manager):
        self.popup_manager = popup_manager

    def trigger_warning(self, payload):
        self.popup_manager.trigger_warning(payload)
