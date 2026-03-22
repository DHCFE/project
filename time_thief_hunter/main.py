"""Time Thief Hunter main entrypoint."""

import sys
import time
import os
from dataclasses import dataclass

from time_thief_hunter.agents import (
    ClassificationAgent,
    EnforcementAgent,
    NegotiationAgent,
    PerceptionAgent,
    PlannerAgent,
    PolicyAgent,
    TaskContextAgent,
)
from time_thief_hunter.brain import AgentBrain
from time_thief_hunter.config import (
    CHECK_INTERVAL,
    DISTRACTION_APPS,
    DISTRACTION_KEYWORDS,
    DISTRACTION_THRESHOLD,
    LOOKBACK_MINUTES,
)
from time_thief_hunter.decision_engine import DecisionEngine
from time_thief_hunter.event_bus import EventBus
from time_thief_hunter.memory import MemoryStore
from time_thief_hunter.orchestrator import HunterOrchestrator
from time_thief_hunter.popup import PopupManager
from time_thief_hunter.runtime import AgentRegistry, TraceRecorder, WorkflowExecutor
from time_thief_hunter.screenpipe_client import ScreenpipeClient
from time_thief_hunter.settings import AppSettings, SettingsStore
from time_thief_hunter.singleton import SingleInstanceLock
from time_thief_hunter.startup import print_startup_report, run_startup_checks
from time_thief_hunter.tools import DesktopControlTool, GitTool, IDETool, MemoryTool, PopupTool, ScreenshotTool
from time_thief_hunter.workflows import InterventionWorkflowGraph


@dataclass
class AppRuntime:
    orchestrator: HunterOrchestrator
    popup: PopupManager
    screenpipe_client: ScreenpipeClient
    negotiation_agent: NegotiationAgent
    decision_engine: DecisionEngine


def build_app(settings: AppSettings) -> AppRuntime:
    event_bus = EventBus()
    memory_store = MemoryStore()
    memory_tool = MemoryTool(memory_store)
    screenpipe_client = ScreenpipeClient(base_url=settings.screenpipe_url)
    screenshot_tool = ScreenshotTool()
    ide_tool = IDETool(os.getcwd())
    desktop_control_tool = DesktopControlTool()
    git_tool = GitTool(os.getcwd())
    decision_engine = DecisionEngine(
        api_key=settings.ai_api_key,
        provider=settings.ai_provider,
        model=settings.ai_model,
        base_url=settings.ai_base_url,
    )
    negotiation_agent = NegotiationAgent(
        AgentBrain(
            api_key=settings.ai_api_key,
            provider=settings.ai_provider,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
        ),
        memory_tool,
        event_bus,
    )
    popup = PopupManager(negotiation_agent)
    popup_tool = PopupTool(popup)

    registry = AgentRegistry(event_bus=event_bus)

    perception_agent = PerceptionAgent(
        screenshot_tool=screenshot_tool,
        lookback_minutes=LOOKBACK_MINUTES,
        distraction_apps=DISTRACTION_APPS,
        distraction_keywords=DISTRACTION_KEYWORDS,
        memory_tool=memory_tool,
        event_bus=event_bus,
    )
    task_context_agent = TaskContextAgent(
        git_tool=git_tool,
        memory_tool=memory_tool,
        workspace_root=os.getcwd(),
        event_bus=event_bus,
    )
    classification_agent = ClassificationAgent(
        threshold=DISTRACTION_THRESHOLD,
        memory_tool=memory_tool,
        decision_engine=decision_engine,
        event_bus=event_bus,
    )
    policy_agent = PolicyAgent(
        memory_tool=memory_tool,
        decision_engine=decision_engine,
        event_bus=event_bus,
    )
    planner_agent = PlannerAgent(memory_tool=memory_tool, event_bus=event_bus)
    enforcement_agent = EnforcementAgent(
        popup_tool=popup_tool,
        memory_tool=memory_tool,
        ide_tool=ide_tool,
        desktop_control_tool=desktop_control_tool,
        event_bus=event_bus,
    )
    popup.set_confirm_action_fn(enforcement_agent.run_confirmed_action)

    registry.register("perception-agent", perception_agent)
    registry.register("task-context-agent", task_context_agent)
    registry.register("classification-agent", classification_agent)
    registry.register("policy-agent", policy_agent)
    registry.register("planner-agent", planner_agent)
    registry.register("enforcement-agent", enforcement_agent)

    orchestrator = HunterOrchestrator(
        workflow_executor=WorkflowExecutor(
            registry=registry,
            graph=InterventionWorkflowGraph(),
            trace_recorder=TraceRecorder(),
            event_bus=event_bus,
        ),
        check_interval=CHECK_INTERVAL,
        event_bus=event_bus,
        pause_predicate=lambda: popup.is_showing,
    )
    return AppRuntime(
        orchestrator=orchestrator,
        popup=popup,
        screenpipe_client=screenpipe_client,
        negotiation_agent=negotiation_agent,
        decision_engine=decision_engine,
    )


def reconfigure_runtime(runtime: AppRuntime, settings: AppSettings) -> None:
    runtime.screenpipe_client.base_url = settings.screenpipe_url
    runtime.decision_engine.configure(
        provider=settings.ai_provider,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
    )
    runtime.negotiation_agent.brain.configure(
        provider=settings.ai_provider,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
    )


def main():
    test_mode = "--test" in sys.argv
    instance_lock = SingleInstanceLock()
    if not instance_lock.acquire():
        print("[startup] another TimeThiefHunter instance is already running, exiting this one.")
        return
    settings_store = SettingsStore()
    settings = settings_store.load()
    startup_report = run_startup_checks(settings)
    print_startup_report(startup_report)
    runtime = build_app(settings)
    popup = runtime.popup

    def refresh_report(mark_onboarding_complete: bool = False, payload=None):
        update_payload = dict(payload or {})
        if mark_onboarding_complete:
            update_payload["onboarding_completed"] = True
        if update_payload:
            current_settings = settings_store.update(update_payload)
        else:
            current_settings = settings_store.load()
        reconfigure_runtime(runtime, current_settings)
        report = run_startup_checks(current_settings)
        print_startup_report(report)
        return {
            **report.__dict__,
            "needs_setup": report.needs_setup,
            "is_fully_ready": report.is_fully_ready,
        }

    popup.configure_setup(
        initial_report={
            **startup_report.__dict__,
            "needs_setup": startup_report.needs_setup,
            "is_fully_ready": startup_report.is_fully_ready,
        },
        save_settings_fn=lambda payload: refresh_report(False, payload),
        refresh_setup_fn=lambda: refresh_report(False, None),
        continue_setup_fn=lambda payload: refresh_report(True, payload),
        monitor_runner=runtime.orchestrator.run_forever,
    )

    demo_mode = "--demo" in sys.argv

    if test_mode:
        def test_fn():
            time.sleep(1)
            popup.trigger_warning("YouTube (test)", 10)

        print("[test mode] opening the intervention popup in 1 second...")
        popup.start(background_func=test_fn)
        return

    if demo_mode:
        def demo_fn():
            apps = [
                ("YouTube", 8),
                ("Bilibili", 15),
                ("Reddit", 25),
                ("Twitter", 35),
                ("Steam", 40),
            ]
            print("[demo] demo mode: warnings will trigger automatically in a loop")
            print("[demo] the next warning appears 3 seconds after the current popup closes")
            print("[demo] a boss raid may trigger after the third offence")
            print("[demo] a matrix easter egg triggers on the tenth offence\n")
            idx = 0
            while True:
                time.sleep(1 if idx == 0 else 3)
                # Wait for previous popup to close
                while popup.is_showing:
                    time.sleep(0.3)
                app, count = apps[idx % len(apps)]
                print(f"[Demo] #{idx+1} → {app} (count={count})")
                popup.trigger_warning(app, count)
                idx += 1

        popup.start(background_func=demo_fn)
        return

    popup.start(background_func=popup.bootstrap)


if __name__ == "__main__":
    main()
