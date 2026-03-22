"""Desktop screenshot and foreground app capture."""

from __future__ import annotations

import subprocess
from pathlib import Path

from time_thief_hunter.config import SCREENSHOT_DIR
from time_thief_hunter.models import utc_now

try:
    import Quartz
except Exception:  # pragma: no cover - optional macOS dependency
    Quartz = None


class ScreenshotTool:
    _request_attempted = False

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or SCREENSHOT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._access_requested = False

    def has_capture_access(self) -> bool:
        if Quartz is None:
            return True
        try:
            return bool(Quartz.CGPreflightScreenCaptureAccess())
        except Exception:
            return True

    def request_capture_access(self) -> bool:
        if Quartz is None:
            return True
        try:
            granted = bool(Quartz.CGRequestScreenCaptureAccess())
        except Exception:
            granted = False
        self._access_requested = True
        return granted

    @classmethod
    def request_capture_access_once(cls) -> bool:
        tool = cls()
        if cls._request_attempted:
            return tool.has_capture_access()
        cls._request_attempted = True
        if tool.has_capture_access():
            return True
        return tool.request_capture_access()

    def capture(self) -> Path | None:
        if not self.has_capture_access():
            if not self._access_requested:
                self.request_capture_access()
            return None
        timestamp = utc_now().strftime("%Y%m%d-%H%M%S")
        path = self.output_dir / f"screen-{timestamp}.png"
        try:
            subprocess.run(
                ["screencapture", "-x", str(path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return None
        return path if path.exists() else None

    def frontmost_context(self) -> dict[str, str]:
        command = [
            "osascript",
            "-e", 'tell application "System Events"',
            "-e", 'set frontApp to first application process whose frontmost is true',
            "-e", 'set appName to name of frontApp',
            "-e", 'set windowName to ""',
            "-e", 'try',
            "-e", 'set windowName to name of first window of frontApp',
            "-e", 'end try',
            "-e", 'return appName & "|||" & windowName',
            "-e", 'end tell',
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            raw = result.stdout.strip()
            app_name, _, window_name = raw.partition("|||")
            return {
                "app_name": app_name.strip(),
                "window_name": window_name.strip(),
            }
        except Exception:
            return {"app_name": "", "window_name": ""}
