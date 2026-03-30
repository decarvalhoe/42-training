"""Tests for the tmux pane reader bridge."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from app.tmux_reader import capture_pane, format_terminal_context

# ---------------------------------------------------------------------------
# capture_pane
# ---------------------------------------------------------------------------


class TestCapturePaneSuccess:
    def test_returns_pane_content(self) -> None:
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="$ ls\nfile.c  main.c\n", stderr="")
        with patch("app.tmux_reader.subprocess.run", return_value=fake):
            result = capture_pane()

        assert result == "$ ls\nfile.c  main.c"

    def test_strips_trailing_whitespace(self) -> None:
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="$ echo hello\n\n\n", stderr="")
        with patch("app.tmux_reader.subprocess.run", return_value=fake):
            result = capture_pane()

        assert result == "$ echo hello"

    def test_respects_max_lines(self) -> None:
        lines = "\n".join(f"line-{i}" for i in range(100))
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=lines, stderr="")
        with patch("app.tmux_reader.subprocess.run", return_value=fake):
            result = capture_pane(max_lines=5)

        assert result is not None
        assert result.count("\n") == 4  # 5 lines → 4 newlines
        assert "line-99" in result
        assert "line-0" not in result

    def test_custom_session_name(self) -> None:
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="output\n", stderr="")
        with patch("app.tmux_reader.subprocess.run", return_value=fake) as mock_run:
            capture_pane("my-session")

        args = mock_run.call_args[0][0]
        assert "-t" in args
        assert args[args.index("-t") + 1] == "my-session"


class TestCapturePaneGracefulFailure:
    def test_returns_none_when_tmux_not_installed(self) -> None:
        with patch("app.tmux_reader.subprocess.run", side_effect=FileNotFoundError):
            assert capture_pane() is None

    def test_returns_none_when_session_not_found(self) -> None:
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="can't find session: mentor42")
        with patch("app.tmux_reader.subprocess.run", return_value=fake):
            assert capture_pane() is None

    def test_returns_none_on_timeout(self) -> None:
        with patch("app.tmux_reader.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="tmux", timeout=3)):
            assert capture_pane() is None

    def test_returns_none_on_os_error(self) -> None:
        with patch("app.tmux_reader.subprocess.run", side_effect=OSError("permission denied")):
            assert capture_pane() is None

    def test_returns_none_on_empty_output(self) -> None:
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n\n\n", stderr="")
        with patch("app.tmux_reader.subprocess.run", return_value=fake):
            assert capture_pane() is None


# ---------------------------------------------------------------------------
# format_terminal_context
# ---------------------------------------------------------------------------


class TestFormatTerminalContext:
    def test_wraps_content_with_markers(self) -> None:
        result = format_terminal_context("$ ls\nfile.c")
        assert result.startswith("--- Contexte terminal")
        assert "$ ls\nfile.c" in result
        assert result.endswith("--- Fin du contexte terminal ---")

    def test_includes_session_label(self) -> None:
        result = format_terminal_context("output")
        assert "mentor42" in result
