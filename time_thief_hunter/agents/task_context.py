"""任务上下文 agent：读取本地工作区和 git 信号。"""

from __future__ import annotations

import os
from pathlib import Path

from time_thief_hunter.agents.base import BaseAgent
from time_thief_hunter.models import TaskContext, utc_now_iso


class TaskContextAgent(BaseAgent):
    def __init__(self, git_tool, memory_tool=None, workspace_root: str | None = None, event_bus=None):
        super().__init__("task-context-agent", event_bus)
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.git_tool = git_tool
        self.memory_tool = memory_tool

    def _run_git(self, *args: str) -> str:
        return self.git_tool.run(*args)

    def _infer_task_type(self, branch: str, root: Path) -> str:
        name = root.name.lower()
        branch_name = branch.lower()
        if any(token in branch_name for token in ("fix", "bug", "hotfix")):
            return "bugfix"
        if any(token in branch_name for token in ("feat", "feature", "epic")):
            return "feature"
        if any(token in branch_name for token in ("docs", "readme")):
            return "documentation"
        if any(token in name for token in ("api", "server", "backend")):
            return "backend"
        if any(token in name for token in ("web", "app", "ui", "frontend")):
            return "frontend"
        return "coding"

    def capture(self) -> TaskContext:
        git_root = self._run_git("rev-parse", "--show-toplevel")
        git_branch = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        dirty = self._run_git("status", "--porcelain")
        dirty_files = len([line for line in dirty.splitlines() if line.strip()])
        root = Path(git_root).resolve() if git_root else self.workspace_root
        task_type = self._infer_task_type(git_branch, root)

        focus_mode = "deep-work" if dirty_files >= 4 else "normal"
        if git_branch in ("main", "master"):
            focus_mode = "risk-sensitive"

        summary = (
            f"repo={root.name or 'unknown'} "
            f"branch={git_branch or 'detached'} "
            f"dirty_files={dirty_files} "
            f"task={task_type}"
        )

        context = TaskContext(
            captured_at=utc_now_iso(),
            workspace_root=str(root),
            repo_name=root.name,
            git_branch=git_branch,
            dirty_files=dirty_files,
            likely_task_type=task_type,
            focus_mode=focus_mode,
            summary=summary,
            signals={
                "cwd": str(self.workspace_root),
                "git_root_detected": bool(git_root),
                "on_main_branch": git_branch in ("main", "master"),
            },
        )
        self.emit("task_context.completed", context.to_dict())
        return context

    def handle(self, message):
        if message.message_type != "inspect.task_context":
            raise ValueError(f"Unsupported message for {self.name}: {message.message_type}")
        task_context = self.capture()
        if self.memory_tool:
            self.memory_tool.record_task_context(task_context)
        return {"task_context": task_context.to_dict()}
