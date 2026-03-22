"""感知 agent：截图并采集当前前台应用上下文。"""

from __future__ import annotations

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.models import Observation, utc_now_iso


class PerceptionAgent(BaseAgent):
    def __init__(
        self,
        screenshot_tool,
        lookback_minutes: int,
        distraction_apps: list[str],
        distraction_keywords: list[str],
        memory_tool=None,
        event_bus=None,
    ):
        super().__init__("perception-agent", event_bus)
        self.screenshot_tool = screenshot_tool
        self.lookback_minutes = lookback_minutes
        self.distraction_apps = distraction_apps
        self.distraction_keywords = distraction_keywords
        self.memory_tool = memory_tool

    def observe(self) -> Observation:
        screenshot = self.screenshot_tool.capture()
        frontmost = self.screenshot_tool.frontmost_context()
        active_app = frontmost.get("app_name", "")
        active_window = frontmost.get("window_name", "")

        searchable_text = f"{active_app}\n{active_window}".lower()
        app_match = any(app.lower() in active_app.lower() for app in self.distraction_apps if active_app)
        matched_keywords = [
            keyword for keyword in self.distraction_keywords
            if keyword.lower() in searchable_text
        ]

        distraction_hits = int(app_match) + len(matched_keywords)
        dominant_app = active_app if distraction_hits else ""

        observation = Observation(
            observed_at=utc_now_iso(),
            lookback_minutes=self.lookback_minutes,
            records_scanned=1 if screenshot else 0,
            distraction_hits=distraction_hits,
            screenshot_path=str(screenshot or ""),
            active_app=active_app,
            active_window=active_window,
            dominant_app=dominant_app,
            dominant_count=1 if dominant_app else 0,
            app_hits={active_app: 1} if app_match and active_app else {},
            keyword_hits={keyword: 1 for keyword in matched_keywords},
            sample_windows=[active_window] if active_window else [],
            matched_records=[{
                "app_name": active_app or "Unknown App",
                "window_name": active_window,
                "captured_at": utc_now_iso(),
            }] if distraction_hits else [],
        )
        self.emit("perception.completed", observation.to_dict())
        return observation

    def handle(self, message):
        if message.message_type != "observe.activity":
            raise ValueError(f"Unsupported message for {self.name}: {message.message_type}")
        observation = self.observe()
        if self.memory_tool:
            self.memory_tool.record_observation(observation)
        return {"observation": observation.to_dict()}
