"""Read tmux pane content for contextual injection into the mentor prompt.

The bridge captures the visible content of a tmux pane (default: ``mentor42``)
and returns it as a string that can be prepended to the LLM user message.
Capture is best-effort: when tmux is unavailable or the target session does not
exist the function returns ``None`` without raising.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)

DEFAULT_SESSION = "mentor42"
DEFAULT_MAX_LINES = 80
CAPTURE_TIMEOUT_SECONDS = 3


def capture_pane(
    session: str = DEFAULT_SESSION,
    *,
    max_lines: int = DEFAULT_MAX_LINES,
) -> str | None:
    """Capture visible content of the *session* tmux pane.

    Returns the captured text (trailing whitespace stripped), or ``None``
    when the session does not exist, tmux is not installed, or any other
    error occurs.
    """
    try:
        result = subprocess.run(
            [
                "tmux",
                "capture-pane",
                "-t",
                session,
                "-p",  # print to stdout
            ],
            capture_output=True,
            text=True,
            timeout=CAPTURE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        logger.debug("tmux binary not found — skipping pane capture")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("tmux capture-pane timed out after %ss", CAPTURE_TIMEOUT_SECONDS)
        return None
    except OSError as exc:
        logger.warning("tmux capture-pane OS error: %s", exc)
        return None

    if result.returncode != 0:
        logger.debug("tmux capture-pane failed (rc=%d): %s", result.returncode, result.stderr.strip())
        return None

    lines = result.stdout.rstrip().splitlines()
    trimmed = lines[-max_lines:] if len(lines) > max_lines else lines
    content = "\n".join(trimmed).strip()
    return content if content else None


def format_terminal_context(content: str) -> str:
    """Wrap captured pane content into a labelled context block."""
    return f"--- Contexte terminal (session tmux mentor42) ---\n{content}\n--- Fin du contexte terminal ---"
