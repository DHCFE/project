"""IDE activation and launch helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


class IDETool:
    CANDIDATE_APPS = [
        "Cursor",
        "Visual Studio Code",
        "Windsurf",
        "Code",
        "IntelliJ IDEA",
        "PyCharm",
        "WebStorm",
        "GoLand",
        "CLion",
        "Codex",
    ]

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = str(Path(workspace_root).resolve()) if workspace_root else ""

    def running_apps(self) -> list[str]:
        command = [
            "osascript",
            "-e",
            'tell application "System Events" to get name of every application process whose background only is false',
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except Exception:
            return []
        return [name.strip() for name in result.stdout.split(",") if name.strip()]

    def installed_apps(self) -> list[str]:
        apps: list[str] = []
        for app in self.CANDIDATE_APPS:
            if Path("/Applications", f"{app}.app").exists():
                apps.append(app)
        return apps

    def preferred_running_app(self) -> str | None:
        running = set(self.running_apps())
        for app in self.CANDIDATE_APPS:
            if app in running:
                return app
        return None

    def preferred_app(self) -> str | None:
        return self.preferred_running_app() or (self.installed_apps()[0] if self.installed_apps() else None)

    def _activate_existing(self, app_name: str) -> bool:
        command = ["osascript", "-e", f'tell application "{app_name}" to activate']
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def activate(self, app_name: str | None = None) -> bool:
        target = app_name or self.preferred_running_app() or self.preferred_app()
        if not target:
            return False
        running = set(self.running_apps())
        if target in running:
            return self._activate_existing(target)
        return False
