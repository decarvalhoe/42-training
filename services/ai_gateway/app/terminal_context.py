"""Capture live terminal state from tmux panes.

Ports the context-capture logic from scripts/ask_mentor.sh (lines 45-68)
to Python. Used by the defense module to generate context-aware questions
that reference actual student work.

Gracefully returns None when tmux is unavailable (e.g. in CI, or when
the ai_gateway runs on a different host than the learner session).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

LEARN_SESSION = "learn42"
PANE_WINDOWS = ("work", "build", "tests")
MAX_PANE_LINES = 30


@dataclass
class TerminalContext:
    """Snapshot of the learner's tmux environment at a point in time."""

    cwd: str = ""
    git_status: str = ""
    panes: dict[str, str] = field(default_factory=dict)
    git_diff_summary: str = ""

    def is_empty(self) -> bool:
        return not self.cwd and not any(self.panes.values())

    def as_prompt_block(self) -> str:
        """Format terminal state as a text block suitable for question generation."""
        if self.is_empty():
            return ""

        parts: list[str] = []
        if self.cwd:
            parts.append(f"Working directory: {self.cwd}")
        if self.git_status:
            parts.append(f"Git status:\n{self.git_status}")
        for window, content in self.panes.items():
            if content.strip():
                parts.append(f"Terminal [{window}]:\n{content}")
        if self.git_diff_summary:
            parts.append(f"Git diff summary:\n{self.git_diff_summary}")
        return "\n\n".join(parts)


def _run_cmd(args: list[str], timeout: float = 3.0) -> str | None:
    """Run a command and return stdout, or None on any failure."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _has_tmux_session(session: str) -> bool:
    return _run_cmd(["tmux", "has-session", "-t", session]) is not None


def _pane_cwd(session: str, window: str) -> str:
    return _run_cmd(["tmux", "display-message", "-p", "-t", f"{session}:{window}", "#{pane_current_path}"]) or ""


def _capture_pane(session: str, window: str, lines: int = MAX_PANE_LINES) -> str:
    return _run_cmd(["tmux", "capture-pane", "-t", f"{session}:{window}", "-p", "-S", f"-{lines}"]) or ""


def _git_status(cwd: str) -> str:
    return _run_cmd(["git", "-C", cwd, "status", "--short"]) or ""


def _git_diff_stat(cwd: str) -> str:
    return _run_cmd(["git", "-C", cwd, "diff", "--stat"]) or ""


def capture_terminal_context(session_name: str = LEARN_SESSION) -> TerminalContext | None:
    """Capture the current state of the learner's tmux session.

    Returns None if the tmux session does not exist or tmux is unavailable.
    This is expected in CI, tests, and remote deployments.
    """
    if not _has_tmux_session(session_name):
        logger.debug("tmux session '%s' not found, skipping terminal context capture", session_name)
        return None

    cwd = _pane_cwd(session_name, "work")

    panes: dict[str, str] = {}
    for window in PANE_WINDOWS:
        content = _capture_pane(session_name, window)
        if content:
            panes[window] = content

    git_status = _git_status(cwd) if cwd else ""
    git_diff_summary = _git_diff_stat(cwd) if cwd else ""

    ctx = TerminalContext(
        cwd=cwd,
        git_status=git_status,
        panes=panes,
        git_diff_summary=git_diff_summary,
    )

    if ctx.is_empty():
        return None

    return ctx
