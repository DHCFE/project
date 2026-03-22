"""Startup checks and readiness detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import shutil
import subprocess
import time
import urllib.parse
import urllib.request

from time_thief_hunter.config import (
    ALLOW_LOCAL_NEGOTIATION_FALLBACK,
    SCREENPIPE_HEALTH_TIMEOUT_SECONDS,
    SCREENPIPE_REQUEST_TIMEOUT_SECONDS,
)
from time_thief_hunter.settings import AppSettings
from time_thief_hunter.tools.screenshot_tool import ScreenshotTool
from time_thief_hunter.vendor_screenpipe import (
    cargo_available,
    launch_vendored_screenpipe,
    rustup_available,
    vendored_binary_path,
    vendored_source_exists,
)


@dataclass
class StartupReport:
    screenpipe_reachable: bool
    screen_capture_access: bool
    ai_api_key_present: bool
    ai_provider: str
    ai_model: str
    negotiation_mode: str
    monitoring_mode: str
    screenpipe_command_available: bool
    vendored_screenpipe_available: bool
    vendored_screenpipe_built: bool
    vendored_screenpipe_selected: bool
    auto_start_attempted: bool = False
    issues: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)

    @property
    def is_fully_ready(self) -> bool:
        provider_ready = self.ai_api_key_present or self.ai_provider == "local-fallback"
        return self.screen_capture_access and provider_ready

    @property
    def needs_setup(self) -> bool:
        return (not self.settings.get("onboarding_completed")) or (not self.is_fully_ready)


def check_screenpipe(base_url: str) -> bool:
    health_url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=SCREENPIPE_HEALTH_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
            if isinstance(payload, dict) and payload.get("status") == "healthy":
                return True
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    params = urllib.parse.urlencode({
        "content_type": "ocr",
        "start_time": start,
        "end_time": end,
        "limit": 1,
    })

    try:
        with urllib.request.urlopen(
            f"{base_url.rstrip('/')}/search?{params}",
            timeout=SCREENPIPE_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            payload = json.loads(response.read())
            return isinstance(payload, dict) and "data" in payload
    except Exception:
        return False


def wait_for_screenpipe(base_url: str, timeout_seconds: float = 12.0, interval_seconds: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if check_screenpipe(base_url):
            return True
        time.sleep(interval_seconds)
    return False


def try_auto_start_screenpipe(settings: AppSettings) -> bool:
    if settings.use_vendored_screenpipe:
        return launch_vendored_screenpipe(settings.screenpipe_url, auto_build=False)

    command = settings.screenpipe_command.strip()
    if not settings.auto_start_screenpipe or not command:
        return False
    binary = shutil.which(command)
    if not binary:
        return False

    try:
        subprocess.Popen(
            [binary],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        return False

    time.sleep(1.2)
    return True


def run_startup_checks(settings: AppSettings, auto_start_screenpipe: bool = True) -> StartupReport:
    screenshot_tool = ScreenshotTool()
    screen_capture_access = screenshot_tool.has_capture_access()
    if not screen_capture_access and auto_start_screenpipe:
        ScreenshotTool.request_capture_access_once()
        screen_capture_access = screenshot_tool.has_capture_access()
    screenpipe_ok = check_screenpipe(settings.screenpipe_url)
    command_available = bool(shutil.which(settings.screenpipe_command.strip() or ""))
    vendored_available = vendored_source_exists()
    vendored_built = vendored_binary_path() is not None
    auto_start_attempted = False

    if not screenpipe_ok and auto_start_screenpipe and settings.auto_start_screenpipe:
        auto_start_attempted = try_auto_start_screenpipe(settings)
        if auto_start_attempted:
            screenpipe_ok = wait_for_screenpipe(settings.screenpipe_url)

    key_present = bool(settings.ai_api_key)
    issues: list[str] = []

    if not screen_capture_access:
        issues.append(
            "Screen capture permission is not granted yet. Enable it for TimeThiefHunter in System Settings and relaunch the app."
        )
    if settings.ai_provider != "local-fallback" and not key_present:
        issues.append("AI API key is not configured, so negotiation will fall back to the local mode.")
    if settings.use_vendored_screenpipe:
        if not vendored_available and not vendored_built:
            issues.append("The bundled monitoring engine is missing, so this build is incomplete.")
        elif not vendored_built:
            issues.append("No bundled monitoring engine is available in this build. Use a release that includes it.")
    elif not command_available:
        issues.append("The external monitoring engine is unavailable.")

    return StartupReport(
        screenpipe_reachable=screenpipe_ok,
        screen_capture_access=screen_capture_access,
        ai_api_key_present=key_present,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model,
        negotiation_mode=settings.ai_provider if key_present or settings.ai_provider == "local-fallback" else "local-fallback",
        monitoring_mode="live" if screen_capture_access else "permission-blocked",
        screenpipe_command_available=command_available,
        vendored_screenpipe_available=vendored_available,
        vendored_screenpipe_built=vendored_built,
        vendored_screenpipe_selected=settings.use_vendored_screenpipe,
        auto_start_attempted=auto_start_attempted,
        issues=issues,
        settings=settings.to_public_dict(),
    )


def print_startup_report(report: StartupReport) -> None:
    print(
        f"[startup] monitoring={report.monitoring_mode} "
        f"negotiation={report.negotiation_mode} "
        f"model={report.ai_model}"
    )
    print(
        f"[startup] screen_capture_access={'yes' if report.screen_capture_access else 'no'} "
        f"screenpipe={'yes' if report.screenpipe_reachable else 'no'}"
    )
    if report.vendored_screenpipe_selected:
        print(
            f"[startup] screenpipe_mode=vendored-source "
            f"built={'yes' if report.vendored_screenpipe_built else 'no'} "
            f"cargo={'yes' if cargo_available() else 'no'} "
            f"rustup={'yes' if rustup_available() else 'no'}"
        )
    if report.auto_start_attempted:
        print("[startup] attempted to auto-start Screenpipe")
    if ALLOW_LOCAL_NEGOTIATION_FALLBACK and report.ai_provider != "local-fallback" and not report.ai_api_key_present:
        print("[startup] local negotiation fallback enabled")
    for issue in report.issues:
        print(f"[startup] {issue}")
