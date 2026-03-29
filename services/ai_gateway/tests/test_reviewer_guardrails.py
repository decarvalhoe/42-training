"""Non-regression tests for Reviewer guardrails — issue #133.

Verify that the Reviewer role enforces the pedagogical contract:
- In foundation/practice/core phases, never output complete code solutions
- Provide constructive peer-style feedback without spoilers
- Allow slightly more detailed feedback in advanced phase
- Giveaway phrases are always detected
- Code blocks in strict phases are scrubbed
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.reviewer import (
    SOLUTION_GIVEAWAY_PATTERNS,
    STRICT_PHASES,
    GuardrailResult,
    build_review,
    check_solution_leakage,
    scrub_review_field,
)

client = TestClient(app)

ENDPOINT = "/api/v1/reviewer/review"

# ---------------------------------------------------------------------------
# Sample code snippets
# ---------------------------------------------------------------------------

C_CODE_MALLOC = """\
#include <stdlib.h>

char *ft_strdup(char *s)
{
    char *dup;
    int i;

    dup = malloc(strlen(s) + 1);
    i = 0;
    while (s[i])
    {
        dup[i] = s[i];
        i++;
    }
    dup[i] = '\\0';
    return (dup);
}
"""

SHELL_CODE_PIPE = """\
cat /etc/passwd | grep root | cut -d: -f1 > result.txt
"""

PYTHON_CODE_BROAD_EXCEPT = """\
def read_config(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None
"""


# ===================================================================
# 1. Unit tests for check_solution_leakage
# ===================================================================


class TestCheckSolutionLeakage:
    """Direct tests on the guardrail detection function."""

    @pytest.mark.parametrize("phrase", SOLUTION_GIVEAWAY_PATTERNS)
    def test_giveaway_phrase_detected_in_any_phase(self, phrase: str) -> None:
        """Every known giveaway phrase must be caught regardless of phase."""
        text = f"Some preamble. {phrase}. Some epilogue."
        for phase in ("foundation", "practice", "core", "advanced"):
            result = check_solution_leakage(text, phase)
            assert not result.clean, f"Giveaway '{phrase}' not caught in phase={phase}"
            assert any(f"giveaway_phrase:{phrase}" in v for v in result.violations)

    @pytest.mark.parametrize("phase", list(STRICT_PHASES))
    def test_code_block_detected_in_strict_phase(self, phase: str) -> None:
        """A fenced code block of 40+ chars must be flagged in strict phases."""
        text = "Look at this:\n```\n" + "x" * 50 + "\n```"
        result = check_solution_leakage(text, phase)
        assert not result.clean
        assert "code_block_detected" in result.violations

    def test_code_block_allowed_in_advanced_phase(self) -> None:
        """In advanced phase, code blocks alone are not flagged."""
        text = "Look at this:\n```\n" + "x" * 50 + "\n```"
        result = check_solution_leakage(text, "advanced")
        assert result.clean

    @pytest.mark.parametrize("phase", list(STRICT_PHASES))
    def test_c_function_pattern_detected_in_strict_phase(self, phase: str) -> None:
        """A C function definition in output must be flagged in strict phases."""
        text = "int main(int argc, char **argv) {\n    return 0;\n}"
        result = check_solution_leakage(text, phase)
        assert not result.clean
        assert any("full_solution_pattern" in v for v in result.violations)

    def test_clean_text_passes(self) -> None:
        """Normal pedagogical text should pass all checks."""
        text = "Memory allocation detected without a visible free."
        result = check_solution_leakage(text, "foundation")
        assert result.clean
        assert result.violations == []


# ===================================================================
# 2. Unit tests for scrub_review_field
# ===================================================================


class TestScrubReviewField:
    """Verify that scrubbing replaces leaking content with redirects."""

    def test_clean_field_unchanged(self) -> None:
        original = "Memory allocation detected."
        scrubbed, was_scrubbed = scrub_review_field(original, "foundation", "observation")
        assert scrubbed == original
        assert not was_scrubbed

    def test_leaking_observation_scrubbed(self) -> None:
        original = "Here is the solution: int main() { return 0; }"
        scrubbed, was_scrubbed = scrub_review_field(original, "foundation", "observation")
        assert was_scrubbed
        assert "here is the solution" not in scrubbed.lower()
        # Should contain pedagogical redirect
        assert "logic flow" in scrubbed.lower() or "closer look" in scrubbed.lower()

    def test_leaking_hint_scrubbed(self) -> None:
        original = "The fix is to add free() after malloc."
        scrubbed, was_scrubbed = scrub_review_field(original, "foundation", "hint")
        assert was_scrubbed
        assert "the fix is" not in scrubbed.lower()

    def test_leaking_next_action_scrubbed(self) -> None:
        original = "Copy this code into your file."
        scrubbed, was_scrubbed = scrub_review_field(original, "practice", "next_action")
        assert was_scrubbed
        assert "copy this code" not in scrubbed.lower()


# ===================================================================
# 3. Integration: build_review never outputs solutions in foundation
# ===================================================================


class TestBuildReviewFoundationGuardrails:
    """build_review must never leak solutions in strict phases."""

    @pytest.mark.parametrize("language", ["c", "shell", "python"])
    @pytest.mark.parametrize("phase", list(STRICT_PHASES))
    def test_no_giveaway_in_review_output(self, language: str, phase: str) -> None:
        """No giveaway phrase should appear in any review field."""
        track = {"id": "shell", "title": "Shell", "modules": []}
        review = build_review(
            code="echo hello" if language == "shell" else "int main(){}",
            language=language,
            track=track,
            module=None,
            phase=phase,
        )
        combined = " ".join(
            [
                review["observation"],
                " ".join(review["questions"]),
                review["hint"],
                review["next_action"],
            ]
        ).lower()

        for pattern in SOLUTION_GIVEAWAY_PATTERNS:
            assert pattern not in combined, f"Giveaway '{pattern}' found in {phase} review for {language}"

    @pytest.mark.parametrize("phase", list(STRICT_PHASES))
    def test_review_contains_no_corrected_code_field(self, phase: str) -> None:
        """The review dict must not contain corrected code."""
        track = {"id": "c", "title": "C / Core 42", "modules": []}
        review = build_review(code=C_CODE_MALLOC, language="c", track=track, module=None, phase=phase)
        # No field called corrected_code
        assert "corrected_code" not in review

    def test_review_has_four_part_structure(self) -> None:
        """Every review must have observation, questions, hint, next_action."""
        track = {"id": "shell", "title": "Shell", "modules": []}
        review = build_review(code="ls -la", language="shell", track=track, module=None, phase="foundation")
        assert "observation" in review
        assert "questions" in review
        assert "hint" in review
        assert "next_action" in review
        assert isinstance(review["questions"], list)
        assert len(review["questions"]) >= 1

    def test_guardrail_result_is_clean_for_normal_input(self) -> None:
        """Normal rule-based output should not trigger guardrails."""
        track = {"id": "shell", "title": "Shell", "modules": []}
        review = build_review(code="ls -la", language="shell", track=track, module=None, phase="foundation")
        guardrail: GuardrailResult = review["guardrail"]
        assert guardrail.clean
        assert guardrail.scrubbed_fields == []


# ===================================================================
# 4. Integration: endpoint never outputs solutions in strict phases
# ===================================================================


class TestReviewerEndpointGuardrails:
    """HTTP-level tests on the /api/v1/reviewer/review endpoint."""

    @pytest.mark.parametrize("phase", list(STRICT_PHASES))
    @pytest.mark.parametrize(
        "payload",
        [
            {"code": "echo hello", "track_id": "shell", "language": "shell"},
            {"code": C_CODE_MALLOC, "track_id": "c", "language": "c"},
            {
                "code": PYTHON_CODE_BROAD_EXCEPT,
                "track_id": "python_ai",
                "language": "python",
            },
        ],
    )
    def test_endpoint_no_giveaway_in_strict_phase(self, phase: str, payload: dict[str, str]) -> None:
        """No giveaway phrase in the JSON response for strict phases."""
        payload["phase"] = phase
        resp = client.post(ENDPOINT, json=payload)
        assert resp.status_code == 200
        data = resp.json()

        combined = " ".join(
            [
                data["observation"],
                " ".join(data["questions"]),
                data["hint"],
                data["next_action"],
            ]
        ).lower()

        for pattern in SOLUTION_GIVEAWAY_PATTERNS:
            assert pattern not in combined

    def test_endpoint_corrected_code_always_null(self) -> None:
        """corrected_code must always be null in every phase."""
        for phase in ("foundation", "practice", "core", "advanced"):
            resp = client.post(
                ENDPOINT,
                json={
                    "code": "echo hello",
                    "track_id": "shell",
                    "language": "shell",
                    "phase": phase,
                },
            )
            assert resp.status_code == 200
            assert resp.json()["corrected_code"] is None

    def test_endpoint_guardrail_fields_present(self) -> None:
        """Response must include guardrail_clean and guardrail_scrubbed_fields."""
        resp = client.post(
            ENDPOINT,
            json={
                "code": "echo hello",
                "track_id": "shell",
                "language": "shell",
                "phase": "foundation",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "guardrail_clean" in data
        assert "guardrail_scrubbed_fields" in data
        assert isinstance(data["guardrail_clean"], bool)
        assert isinstance(data["guardrail_scrubbed_fields"], list)

    def test_endpoint_questions_are_interrogative(self) -> None:
        """Every question must contain a question mark."""
        resp = client.post(
            ENDPOINT,
            json={
                "code": C_CODE_MALLOC,
                "track_id": "c",
                "language": "c",
                "phase": "foundation",
            },
        )
        assert resp.status_code == 200
        for q in resp.json()["questions"]:
            assert "?" in q, f"Question must be interrogative: {q}"


# ===================================================================
# 5. Advanced phase allows more detailed feedback
# ===================================================================


class TestReviewerAdvancedPhase:
    """In advanced phase, guardrails are relaxed for code blocks."""

    def test_advanced_phase_still_blocks_giveaway_phrases(self) -> None:
        """Even in advanced phase, explicit giveaway phrases are caught."""
        text = "Here is the solution for your problem."
        result = check_solution_leakage(text, "advanced")
        assert not result.clean

    def test_advanced_phase_allows_code_blocks(self) -> None:
        """In advanced phase, code blocks alone do not trigger guardrails."""
        text = "Consider this pattern:\n```\n" + "x = 1\n" * 10 + "```"
        result = check_solution_leakage(text, "advanced")
        assert result.clean

    def test_advanced_review_still_has_four_parts(self) -> None:
        """Even in advanced phase, the 4-part structure is preserved."""
        track = {"id": "c", "title": "C / Core 42", "modules": []}
        review = build_review(code=C_CODE_MALLOC, language="c", track=track, module=None, phase="advanced")
        for key in ("observation", "questions", "hint", "next_action"):
            assert key in review


# ===================================================================
# 6. Edge cases
# ===================================================================


class TestReviewerGuardrailEdgeCases:
    """Edge cases for guardrail enforcement."""

    def test_empty_text_is_clean(self) -> None:
        result = check_solution_leakage("", "foundation")
        assert result.clean

    def test_case_insensitive_giveaway_detection(self) -> None:
        """Giveaway detection must be case-insensitive."""
        result = check_solution_leakage("HERE IS THE SOLUTION", "foundation")
        assert not result.clean

    def test_giveaway_embedded_in_sentence(self) -> None:
        """Giveaway must be detected even when embedded in a larger sentence."""
        result = check_solution_leakage(
            "Well, I think here is the solution to your issue.",
            "foundation",
        )
        assert not result.clean

    def test_unknown_field_name_uses_default_redirect(self) -> None:
        """An unrecognized field name should still get a redirect."""
        scrubbed, was_scrubbed = scrub_review_field("here is the solution", "foundation", "unknown_field")
        assert was_scrubbed
        assert len(scrubbed) > 0
        assert "here is the solution" not in scrubbed.lower()

    def test_multiple_violations_all_recorded(self) -> None:
        """Multiple giveaway phrases in one text should all be recorded."""
        text = "Here is the solution. Also copy this code."
        result = check_solution_leakage(text, "foundation")
        assert not result.clean
        assert len(result.violations) >= 2
