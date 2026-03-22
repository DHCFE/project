"""Screenpipe REST API client."""

import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta, timezone

from time_thief_hunter.config import SCREENPIPE_REQUEST_TIMEOUT_SECONDS, SCREENPIPE_URL


class ScreenpipeClient:
    def __init__(self, base_url=SCREENPIPE_URL):
        self.base_url = base_url
        self._last_error = None

    def get_recent_activity(self, minutes=5):
        now = datetime.now(timezone.utc)
        start = (now - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        params = urllib.parse.urlencode({
            "content_type": "ocr",
            "start_time": start,
            "end_time": end,
            "limit": 50,
        })

        try:
            url = f"{self.base_url}/search?{params}"
            with urllib.request.urlopen(url, timeout=SCREENPIPE_REQUEST_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read())
                self._last_error = None
                return data.get("data", [])
        except Exception as e:
            message = str(e)
            if message != self._last_error:
                print(f"[screenpipe] connection failed: {e}")
                self._last_error = message
            return []
