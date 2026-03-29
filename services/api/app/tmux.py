"""Tmux session discovery and pane capture (Issues #178, #179)."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from .schemas import TmuxPaneResponse, TmuxSession, TmuxSessionsResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pane capture router (Issue #179)
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/tmux", tags=["tmux"])

_DEFAULT_ROWS = 24
_DEFAULT_COLS = 80


async def _capture_pane(session: str) -> tuple[str, int, int]:
    """Run tmux capture-pane and return (content, rows, cols)."""
    if shutil.which("tmux") is None:
        raise HTTPException(status_code=503, detail="tmux is not available on this host")

    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux",
            "capture-pane",
            "-t",
            session,
            "-p",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    except TimeoutError as err:
        raise HTTPException(status_code=504, detail="tmux capture timed out") from err

    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        if "session not found" in stderr_text or "can't find" in stderr_text:
            raise HTTPException(status_code=404, detail=f"tmux session '{session}' not found")
        raise HTTPException(status_code=502, detail=f"tmux error: {stderr_text}")

    content = stdout.decode("utf-8", errors="replace")

    # Get pane dimensions
    rows, cols = _DEFAULT_ROWS, _DEFAULT_COLS
    try:
        dim_proc = await asyncio.create_subprocess_exec(
            "tmux",
            "display-message",
            "-t",
            session,
            "-p",
            "#{pane_height} #{pane_width}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        dim_out, _ = await asyncio.wait_for(dim_proc.communicate(), timeout=3.0)
        if dim_proc.returncode == 0:
            parts = dim_out.decode().strip().split()
            if len(parts) == 2:
                rows, cols = int(parts[0]), int(parts[1])
    except (TimeoutError, ValueError):
        pass  # keep defaults

    return content, rows, cols


@router.get("/pane/{session}", response_model=TmuxPaneResponse)
async def get_tmux_pane(session: str) -> TmuxPaneResponse:
    """Capture the current content of a tmux pane (read-only)."""
    content, rows, cols = await _capture_pane(session)
    return TmuxPaneResponse(
        session=session,
        content=content,
        rows=rows,
        cols=cols,
        timestamp=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Session listing (Issue #178)
# ---------------------------------------------------------------------------

_IDLE_THRESHOLD_SECONDS = 300  # 5 minutes without activity → idle


def _epoch_to_iso(epoch_str: str) -> str:
    try:
        return datetime.fromtimestamp(int(epoch_str), tz=UTC).isoformat()
    except (ValueError, OSError):
        return epoch_str


def _parse_status(last_activity_epoch: str, attached: bool) -> str:
    if attached:
        return "active"
    try:
        elapsed = datetime.now(UTC).timestamp() - int(last_activity_epoch)
        return "active" if elapsed < _IDLE_THRESHOLD_SECONDS else "idle"
    except (ValueError, OSError):
        return "idle"


def list_tmux_sessions() -> TmuxSessionsResponse:
    """Run ``tmux list-sessions`` and return structured data."""
    try:
        result = subprocess.run(
            [
                "tmux",
                "list-sessions",
                "-F",
                "#{session_name}\t#{session_created}\t#{session_activity}\t#{session_windows}\t#{session_attached}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        logger.info("tmux binary not found")
        return TmuxSessionsResponse(sessions=[], total=0)
    except subprocess.TimeoutExpired:
        logger.warning("tmux list-sessions timed out")
        return TmuxSessionsResponse(sessions=[], total=0)

    if result.returncode != 0:
        logger.info("tmux list-sessions returned %d: %s", result.returncode, result.stderr.strip())
        return TmuxSessionsResponse(sessions=[], total=0)

    sessions: list[TmuxSession] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        name, created, activity, windows, attached_flag = parts[:5]
        attached = attached_flag == "1"
        sessions.append(
            TmuxSession(
                name=name,
                status=_parse_status(activity, attached),  # type: ignore[arg-type]
                created_at=_epoch_to_iso(created),
                last_activity=_epoch_to_iso(activity),
                windows=int(windows) if windows.isdigit() else 0,
                attached=attached,
            )
        )

    return TmuxSessionsResponse(sessions=sessions, total=len(sessions))
