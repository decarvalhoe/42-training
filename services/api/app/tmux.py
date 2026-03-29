"""Read-only tmux pane capture endpoint (Issue #179)."""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from .schemas import TmuxPaneResponse

logger = logging.getLogger(__name__)

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
