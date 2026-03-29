"""
Guardrail regression tests — issue #34.

Verify that the mentor endpoint enforces the pedagogical contract:
- No direct/complete solution in foundation, practice, or core phases
- Blocked source tier never leaks into responses
- Response always follows the 4-part structure (observation, question, hint, next_action)
- Source trust tiers are respected
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repository import load_curriculum

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NON_ADVANCED_PHASES = ("foundation", "practice", "core")
ALL_TRACKS = ("shell", "c", "python_ai")

SOLUTION_GIVEAWAY_PATTERNS = [
    "voici la solution",
    "voici le code",
    "copie ce code",
    "here is the solution",
    "here is the code",
    "copy this code",
]

ALLOWED_SOURCE_TIERS = {
    tier["id"]
    for tier in load_curriculum()["source_policy"]["tiers"]
    if tier["id"] != "blocked_solution_content"
}

BLOCKED_SOURCE_TIERS = {
    "blocked_solution_content",
    "solution_content",
    "direct_solution",
}


def _mentor_request(
    track_id: str = "shell",
    module_id: str | None = "shell-basics",
    question: str = "Je bloque sur cp",
    phase: str = "foundation",
    pace_mode: str = "normal",
) -> dict:
    return {
        "track_id": track_id,
        "module_id": module_id,
        "question": question,
        "pace_mode": pace_mode,
        "phase": phase,
    }


# ---------------------------------------------------------------------------
# 1. Foundation / practice / core phases must NEVER allow direct solutions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase", NON_ADVANCED_PHASES)
@pytest.mark.parametrize("track_id", ALL_TRACKS)
def test_direct_solution_blocked_in_non_advanced_phases(phase: str, track_id: str) -> None:
    """direct_solution_allowed must be False for all non-advanced phases."""
    module_id = None
    if track_id == "shell":
        module_id = "shell-basics"
    elif track_id == "c":
        module_id = "c-compilation"
    # python_ai has no module_id required

    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(track_id=track_id, module_id=module_id, phase=phase),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["direct_solution_allowed"] is False, (
        f"direct_solution_allowed must be False in phase={phase}, track={track_id}"
    )


def test_direct_solution_allowed_in_advanced_phase() -> None:
    """Only the advanced phase may allow a complete solution."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(phase="advanced"),
    )
    assert resp.status_code == 200
    assert resp.json()["direct_solution_allowed"] is True


# ---------------------------------------------------------------------------
# 2. Response text must not contain solution giveaways in foundation phase
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("track_id", ALL_TRACKS)
def test_foundation_response_text_contains_no_solution(track_id: str) -> None:
    """Observation, hint, and next_action must not contain solution giveaway phrases."""
    module_id = None
    if track_id == "shell":
        module_id = "shell-basics"
    elif track_id == "c":
        module_id = "c-compilation"

    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(track_id=track_id, module_id=module_id, phase="foundation"),
    )
    assert resp.status_code == 200
    data = resp.json()

    text_fields = [data["observation"], data["hint"], data["next_action"]]
    combined = " ".join(text_fields).lower()

    for pattern in SOLUTION_GIVEAWAY_PATTERNS:
        assert pattern not in combined, (
            f"Solution giveaway '{pattern}' found in foundation response for track={track_id}"
        )


# ---------------------------------------------------------------------------
# 3. Response always contains the 4-part pedagogical structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase", NON_ADVANCED_PHASES)
def test_response_contains_four_part_structure(phase: str) -> None:
    """Every response must have observation, question, hint, next_action — all non-empty."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(phase=phase),
    )
    assert resp.status_code == 200
    data = resp.json()

    for field in ("observation", "question", "hint", "next_action"):
        assert field in data, f"Missing field: {field}"
        assert isinstance(data[field], str) and len(data[field]) > 0, (
            f"Field '{field}' must be a non-empty string in phase={phase}"
        )


# ---------------------------------------------------------------------------
# 4. Blocked source tiers never appear in the response source_policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase", (*NON_ADVANCED_PHASES, "advanced"))
def test_blocked_sources_not_in_response(phase: str) -> None:
    """No response should ever expose blocked_solution_content as an allowed tier."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(phase=phase),
    )
    assert resp.status_code == 200
    policy = set(resp.json()["source_policy"])

    leaked = policy & BLOCKED_SOURCE_TIERS
    assert not leaked, f"Blocked source tier(s) {leaked} leaked into response for phase={phase}"


def test_source_policy_contains_only_allowed_tiers() -> None:
    """The source_policy returned must be a subset of allowed tiers."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(),
    )
    assert resp.status_code == 200
    policy = set(resp.json()["source_policy"])
    assert policy <= ALLOWED_SOURCE_TIERS, f"Unexpected tiers in source_policy: {policy - ALLOWED_SOURCE_TIERS}"


def test_mentor_source_policy_matches_curriculum_non_blocked_tiers() -> None:
    """The mentor endpoint must expose the exact non-blocked curriculum source-policy ids."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(),
    )
    assert resp.status_code == 200
    assert set(resp.json()["source_policy"]) == ALLOWED_SOURCE_TIERS


# ---------------------------------------------------------------------------
# 5. Source-policy endpoint respects tier definitions from curriculum
# ---------------------------------------------------------------------------


def test_source_policy_endpoint_has_blocked_tier() -> None:
    """The /source-policy endpoint must list blocked_solution_content as blocked_by_default."""
    resp = client.get("/api/v1/source-policy")
    assert resp.status_code == 200
    tiers = resp.json()["tiers"]
    blocked = [t for t in tiers if t["id"] == "blocked_solution_content"]
    assert len(blocked) == 1
    assert blocked[0]["allowed_usage"] == "blocked_by_default"


# ---------------------------------------------------------------------------
# 6. Reviewer-style: the question field must interrogate, not correct
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase", NON_ADVANCED_PHASES)
def test_question_field_is_interrogative(phase: str) -> None:
    """The question field should ask, not tell — must contain '?' character."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(phase=phase),
    )
    assert resp.status_code == 200
    question = resp.json()["question"]
    assert "?" in question, f"Question field should be interrogative (contain '?'), got: {question}"


# ---------------------------------------------------------------------------
# 7. Edge case: very long question should not bypass guardrails
# ---------------------------------------------------------------------------


def test_long_question_still_guarded() -> None:
    """A question at max length must still enforce foundation guardrails."""
    long_q = "Explique moi comment faire cp " + "a" * 960  # near 1000 char limit
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(question=long_q[:1000], phase="foundation"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["direct_solution_allowed"] is False


# ---------------------------------------------------------------------------
# 8. Invalid track returns 404, not a solution leak
# ---------------------------------------------------------------------------


def test_invalid_track_returns_404() -> None:
    """An unknown track must return 404, never a fallback with leaked content."""
    resp = client.post(
        "/api/v1/mentor/respond",
        json=_mentor_request(track_id="nonexistent"),
    )
    assert resp.status_code == 404
