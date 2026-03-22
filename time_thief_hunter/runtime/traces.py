"""Workflow trace recorder."""

from __future__ import annotations

import json
from pathlib import Path

from time_thief_hunter.config import TRACE_FILE
from time_thief_hunter.models import utc_now_iso


class TraceRecorder:
    def __init__(self, path: Path | None = None):
        self.path = path or TRACE_FILE

    def write(self, run_id: str, phase: str, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps({
                "timestamp": utc_now_iso(),
                "run_id": run_id,
                "phase": phase,
                "payload": payload,
            }, ensure_ascii=False))
            fp.write("\n")
