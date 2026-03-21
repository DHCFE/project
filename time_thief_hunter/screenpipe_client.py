"""Screenpipe REST API 客户端"""

import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta, timezone


class ScreenpipeClient:
    def __init__(self, base_url="http://localhost:3030"):
        self.base_url = base_url

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
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get("data", [])
        except Exception as e:
            print(f"[screenpipe] 连接失败: {e}")
            return []
