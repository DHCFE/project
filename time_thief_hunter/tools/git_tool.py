"""Tool wrapper around git context inspection."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitTool:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()

    def run(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception:
            return ""
        return result.stdout.strip()
