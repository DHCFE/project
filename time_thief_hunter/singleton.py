"""Single-instance process lock."""

from __future__ import annotations

import atexit
import fcntl
import os
from pathlib import Path

from time_thief_hunter.config import STATE_DIR


class SingleInstanceLock:
    def __init__(self, path: Path | None = None):
        self.path = path or (STATE_DIR / "app.lock")
        self._fd = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        os.ftruncate(self._fd, 0)
        os.write(self._fd, str(os.getpid()).encode("utf-8"))
        atexit.register(self.release)
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(self._fd)
        except OSError:
            pass
        self._fd = None
