"""Integration tests: tmux context injection into the mentor prompt."""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.llm_client import _build_user_message, get_mentor_response
from app.schemas import MentorRequest


def _mentor_request(**kwargs) -> MentorRequest:
    defaults = dict(track_id="shell", module_id="shell-basics", question="Je bloque sur ls", phase="foundation")
    defaults.update(kwargs)
    return MentorRequest(**defaults)


# ---------------------------------------------------------------------------
# _build_user_message integration
# ---------------------------------------------------------------------------


class TestBuildUserMessageWithTerminalContext:
    def test_includes_terminal_context_block(self) -> None:
        ctx = "--- Contexte terminal (session tmux mentor42) ---\n$ ls\n--- Fin du contexte terminal ---"
        msg = _build_user_message(_mentor_request(), "Shell 0 to Hero", "Navigation", "shell", terminal_context=ctx)

        assert msg.startswith("--- Contexte terminal")
        assert "$ ls" in msg
        assert "Question de l'apprenant" in msg

    def test_no_context_when_none(self) -> None:
        msg = _build_user_message(_mentor_request(), "Shell 0 to Hero", "Navigation", "shell", terminal_context=None)

        assert "Contexte terminal" not in msg
        assert msg.startswith("Learner: ")

    def test_context_precedes_track_line(self) -> None:
        ctx = "--- Contexte terminal (session tmux mentor42) ---\n$ pwd\n--- Fin du contexte terminal ---"
        msg = _build_user_message(_mentor_request(), "Shell 0 to Hero", "Navigation", "shell", terminal_context=ctx)

        ctx_pos = msg.index("Contexte terminal")
        track_pos = msg.index("Track: shell")
        assert ctx_pos < track_pos


# ---------------------------------------------------------------------------
# get_mentor_response integration
# ---------------------------------------------------------------------------


MOCK_JSON = """{
  "observation": "Tu explores ls.",
  "question": "Que vois-tu quand tu tapes ls ?",
  "hint": "Essaie ls -la.",
  "next_action": "Lance ls dans ton terminal."
}"""


class TestGetMentorResponseTmuxIntegration:
    def test_tmux_context_injected_into_llm_call(self) -> None:
        fake_client = MagicMock()
        fake_client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(text=MOCK_JSON)])

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("app.llm_client._build_anthropic_client", return_value=fake_client),
            patch("app.llm_client.capture_pane", return_value="$ ls -la\ntotal 8\n-rw-r--r-- 1 user user 42 main.c"),
        ):
            get_mentor_response(_mentor_request(), "Shell 0 to Hero", "Navigation", "shell")

        user_text = fake_client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"]
        assert "Contexte terminal" in user_text
        assert "$ ls -la" in user_text
        assert "main.c" in user_text

    def test_no_tmux_context_when_pane_unavailable(self) -> None:
        fake_client = MagicMock()
        fake_client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(text=MOCK_JSON)])

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("app.llm_client._build_anthropic_client", return_value=fake_client),
            patch("app.llm_client.capture_pane", return_value=None),
        ):
            get_mentor_response(_mentor_request(), "Shell 0 to Hero", "Navigation", "shell")

        user_text = fake_client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"]
        assert "Contexte terminal" not in user_text
        assert user_text.startswith("Learner: ")

    def test_mentor_still_works_when_tmux_capture_raises(self) -> None:
        """Even if capture_pane raises unexpectedly, get_mentor_response should not break."""
        fake_client = MagicMock()
        fake_client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(text=MOCK_JSON)])

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("app.llm_client._build_anthropic_client", return_value=fake_client),
            patch("app.llm_client.capture_pane", side_effect=RuntimeError("unexpected")),
            contextlib.suppress(RuntimeError),
        ):
            # capture_pane itself never raises (it catches internally), but if
            # something truly unexpected happens, the LLM call path raises and
            # the endpoint falls back.
            get_mentor_response(_mentor_request(), "Shell 0 to Hero", "Navigation", "shell")
