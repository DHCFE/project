"""Popup system built with pywebview and HTML/CSS.

UI loaded from ui/index.html — edit that file for frontend changes.
"""

from __future__ import annotations

import json
import os
import threading
import time

try:
    import webview
except ImportError:  # pragma: no cover - optional runtime UI dependency
    webview = None

try:
    import AppKit
    import webview.platforms.cocoa as cocoa
except Exception:  # pragma: no cover - optional macOS UI integration
    AppKit = None
    cocoa = None


def _load_ui():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()


class _Api:
    """JS - Python bridge"""

    def __init__(
        self,
        dismiss_fn,
        open_negotiation_fn,
        send_message_fn,
        close_chat_fn,
        save_setup_fn,
        retry_setup_fn,
        continue_setup_fn,
    ):
        self._dismiss_fn = dismiss_fn
        self._open_negotiation_fn = open_negotiation_fn
        self._send_message_fn = send_message_fn
        self._close_chat_fn = close_chat_fn
        self._save_setup_fn = save_setup_fn
        self._retry_setup_fn = retry_setup_fn
        self._continue_setup_fn = continue_setup_fn

    def dismiss(self):
        self._dismiss_fn()

    def open_negotiation(self):
        return self._open_negotiation_fn()

    def send_message(self, message):
        return self._send_message_fn(message)

    def close_chat(self):
        self._close_chat_fn()

    def save_setup(self, payload):
        return self._save_setup_fn(payload)

    def retry_setup(self):
        return self._retry_setup_fn()

    def continue_from_setup(self, payload):
        return self._continue_setup_fn(payload)

    def __dir__(self):
        return [
            "dismiss",
            "open_negotiation",
            "send_message",
            "close_chat",
            "save_setup",
            "retry_setup",
            "continue_from_setup",
        ]


class PopupManager:
    def __init__(self, negotiation_agent):
        self.negotiation_agent = negotiation_agent
        self.window = None
        self.is_showing = False
        self._cur_app = ""
        self._cur_payload = {}
        self._setup_report = None
        self._save_settings_fn = None
        self._refresh_setup_fn = None
        self._continue_setup_fn = None
        self._monitor_runner = None
        self._monitor_thread = None
        self._bootstrapped = False
        self._confirm_action_fn = None
        self._overlay_configured = False
        self._warning_lock = threading.RLock()

    def configure_setup(
        self,
        initial_report: dict,
        save_settings_fn,
        refresh_setup_fn,
        continue_setup_fn,
        monitor_runner,
    ) -> None:
        self._setup_report = initial_report
        self._save_settings_fn = save_settings_fn
        self._refresh_setup_fn = refresh_setup_fn
        self._continue_setup_fn = continue_setup_fn
        self._monitor_runner = monitor_runner

    def set_confirm_action_fn(self, confirm_action_fn) -> None:
        self._confirm_action_fn = confirm_action_fn

    def _ensure_monitoring_started(self) -> None:
        if not self._monitor_runner:
            return
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_thread = threading.Thread(
            target=self._monitor_runner,
            daemon=True,
        )
        self._monitor_thread.start()

    def _configure_overlay_window(self) -> None:
        if self._overlay_configured or self.window is None or cocoa is None or AppKit is None:
            return

        def configure():
            browser = cocoa.BrowserView.instances.get(self.window.uid)
            if not browser:
                return
            ns_window = browser.window
            behavior = int(ns_window.collectionBehavior())
            behavior |= (1 << 0)  # NSWindowCollectionBehaviorCanJoinAllSpaces
            behavior |= (1 << 1)  # NSWindowCollectionBehaviorMoveToActiveSpace
            behavior |= (1 << 3)  # NSWindowCollectionBehaviorTransient
            behavior |= (1 << 8)  # NSWindowCollectionBehaviorFullScreenAuxiliary
            ns_window.setCollectionBehavior_(behavior)
            ns_window.setLevel_(AppKit.NSModalPanelWindowLevel)
            ns_window.setHidesOnDeactivate_(False)
            ns_window.orderFrontRegardless()
            self._overlay_configured = True

        app_helper = getattr(cocoa, "AppHelper", None)
        if app_helper is not None:
            app_helper.callAfter(configure)
        else:
            configure()

    def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        self._bootstrapped = True
        time.sleep(0.3)
        if self._setup_report:
            self.show_setup(self._setup_report)
            return
        self._ensure_monitoring_started()

    def trigger_warning(self, payload_or_app, count=None):
        with self._warning_lock:
            if self.is_showing:
                print("[popup] warning skipped: popup already showing")
                return
            if isinstance(payload_or_app, dict):
                payload = dict(payload_or_app)
                app = payload.get("app", "")
                count_value = payload.get("count", 0)
            else:
                app = payload_or_app
                count_value = count or 0
                payload = {"app": app, "count": count_value, "plan": {}}

            self._cur_payload = payload
            self._cur_app = app
            self.is_showing = True
            if self.window is None:
                print(f"[popup] warning app={app} count={count_value} plan={payload.get('plan', {}).get('title', '-')}")
                return
            self._configure_overlay_window()
            self.window.resize(560, 460)
            self.window.evaluate_js(f"showWarning({json.dumps(payload)})")
            self.window.show()

    def show_setup(self, report: dict):
        self._setup_report = report
        self.is_showing = True
        if self.window is None:
            print("[setup] first-run setup")
            for issue in report.get("issues", []):
                print(f"[setup] {issue}")
            return
        self._configure_overlay_window()
        self.window.resize(720, 620)
        self.window.evaluate_js(f"showSetup({json.dumps(report)})")
        self.window.show()

    def _complete_setup(self, report):
        if not report:
            return False
        self._setup_report = report
        self.is_showing = False
        if self.window is not None:
            self.window.hide()
            self.window.resize(560, 460)
        self._ensure_monitoring_started()
        return True

    def dismiss(self):
        payload = dict(self._cur_payload) if self._cur_payload else {}
        decision = payload.get("decision", {})
        action = decision.get("action")
        if action in {"focus_ide", "hard_stop", "close_browser"} and self._confirm_action_fn:
            self._confirm_action_fn(payload)
        self.is_showing = False
        self._cur_payload = {}
        self._cur_app = ""
        if self.window is not None:
            self.window.hide()

    def open_negotiation(self):
        self.negotiation_agent.start_negotiation(self._cur_payload)
        if self.window is not None:
            self.window.resize(580, 560)
        plan = self._cur_payload.get("plan", {})
        return plan.get("opening_message") or f"I can see you are in {self._cur_app}. Go on, give me one good reason."

    def send_message(self, message):
        return self.negotiation_agent.negotiate(message)

    def close_chat(self):
        self.negotiation_agent.reset()
        self.is_showing = False
        if self.window is not None:
            self.window.hide()
            self.window.resize(560, 460)

    def save_setup(self, payload):
        report = self._save_settings_fn(payload) if self._save_settings_fn else self._setup_report
        if report:
            self.show_setup(report)
        return report

    def retry_setup(self):
        report = self._refresh_setup_fn() if self._refresh_setup_fn else self._setup_report
        if report:
            self.show_setup(report)
        return report

    def continue_from_setup(self, payload):
        report = self._continue_setup_fn(payload) if self._continue_setup_fn else self._setup_report
        self._complete_setup(report or {})
        return report

    def start(self, background_func=None):
        if webview is None:
            print("[startup] pywebview is not installed, switching to terminal mode")
            if background_func is self.bootstrap:
                self._bootstrapped = True
                if self._setup_report:
                    self.show_setup(self._setup_report)
            elif background_func:
                background_func()
            return
        api = _Api(
            dismiss_fn=self.dismiss,
            open_negotiation_fn=self.open_negotiation,
            send_message_fn=self.send_message,
            close_chat_fn=self.close_chat,
            save_setup_fn=self.save_setup,
            retry_setup_fn=self.retry_setup,
            continue_setup_fn=self.continue_from_setup,
        )
        self.window = webview.create_window(
            "",
            html=_load_ui(),
            js_api=api,
            width=460,
            height=340,
            hidden=True,
            on_top=True,
            background_color="#08080c",
            resizable=False,
            frameless=True,
            easy_drag=True,
        )
        webview.start(func=background_func, debug=False)
