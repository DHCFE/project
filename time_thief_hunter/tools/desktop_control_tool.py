"""Desktop control helpers for browser suppression and app focus."""

from __future__ import annotations

import subprocess


class DesktopControlTool:
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

    def frontmost_app(self) -> str:
        command = [
            "osascript",
            "-e",
            'tell application "System Events" to return name of first application process whose frontmost is true',
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return ""

    def hide_app(self, app_name: str) -> bool:
        if not app_name:
            return False
        command = ["osascript", "-e", f'tell application "{app_name}" to hide']
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def hide_frontmost_browser(self) -> bool:
        app_name = self.frontmost_app()
        if app_name not in self.BROWSER_APPS:
            return False
        return self.hide_app(app_name)
