"""Tests for business validation: prerequisites, phase ordering, track enrollment (Issue #26)."""

from __future__ import annotations

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.validation import (
    check_phase_ordering,
    check_prerequisites,
    check_track_enrollment,
    find_module,
    validate_module_activation,
)

client = TestClient(app)

# ---------------------------------------------------------------------------
# Test curriculum fixture — mirrors real structure with prerequisites/phases
# ---------------------------------------------------------------------------

_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell",
            "summary": "Shell track",
            "why_it_matters": "Fundamentals",
            "modules": [
                {"id": "shell-basics", "title": "Basics", "phase": "foundation", "prerequisites": [], "skills": []},
                {
                    "id": "shell-streams",
                    "title": "Streams",
                    "phase": "foundation",
                    "prerequisites": ["shell-basics"],
                    "skills": [],
                },
                {
                    "id": "shell-permissions",
                    "title": "Permissions",
                    "phase": "foundation",
                    "prerequisites": ["shell-basics"],
                    "skills": [],
                },
                {
                    "id": "shell-tooling",
                    "title": "Tooling",
                    "phase": "practice",
                    "prerequisites": ["shell-streams", "shell-permissions"],
                    "skills": [],
                },
            ],
        },
        {
            "id": "c",
            "title": "C",
            "summary": "C track",
            "why_it_matters": "Low-level",
            "modules": [
                {
                    "id": "c-basics",
                    "title": "Syntax",
                    "phase": "foundation",
                    "prerequisites": ["shell-basics"],
                    "skills": [],
                },
                {
                    "id": "c-memory",
                    "title": "Memory",
                    "phase": "foundation",
                    "prerequisites": ["c-basics"],
                    "skills": [],
                },
                {
                    "id": "c-build-debug",
                    "title": "Build",
                    "phase": "practice",
                    "prerequisites": ["c-basics", "shell-streams"],
                    "skills": [],
                },
                {
                    "id": "c-libft-bridge",
                    "title": "Libft bridge",
                    "phase": "core",
                    "prerequisites": ["c-memory", "c-build-debug"],
                    "skills": [],
                },
            ],
        },
        {
            "id": "python_ai",
            "title": "Python + AI",
            "summary": "Python track",
            "why_it_matters": "AI literacy",
            "modules": [
                {
                    "id": "python-basics",
                    "title": "Basics",
                    "phase": "foundation",
                    "prerequisites": ["shell-basics"],
                    "skills": [],
                },
                {
                    "id": "python-oop",
                    "title": "OOP",
                    "phase": "practice",
                    "prerequisites": ["python-basics"],
                    "skills": [],
                },
                {"id": "ai-rag", "title": "RAG", "phase": "advanced", "prerequisites": ["python-oop"], "skills": []},
            ],
        },
    ],
}


def _prog(active_course: str = "shell", completed_modules: list[str] | None = None) -> dict[str, object]:
    statuses = {module_id: {"status": "completed"} for module_id in (completed_modules or [])}
    return {
        "learning_plan": {"active_course": active_course},
        "progress": {},
        "module_status": statuses,
    }


def _patch_repo(progression: dict[str, object] | None = None):
    prog = progression if progression is not None else _prog()
    written: list[dict[str, object]] = []

    def fake_write(data: dict[str, object]) -> None:
        prog.clear()
        prog.update(data)
        written.append(json.loads(json.dumps(data)))

    return (
        patch("app.main.load_curriculum", return_value=_CURRICULUM),
        patch("app.main.load_progression", side_effect=lambda: json.loads(json.dumps(prog))),
        patch("app.main.write_progression", side_effect=fake_write),
        prog,
        written,
    )


# ===========================================================================
# Unit tests for validation functions
# ===========================================================================


class TestFindModule:
    def test_finds_existing_module(self) -> None:
        result = find_module(_CURRICULUM, "shell-basics")
        assert result is not None
        track, module = result
        assert track["id"] == "shell"
        assert module["id"] == "shell-basics"

    def test_finds_cross_track_module(self) -> None:
        result = find_module(_CURRICULUM, "c-basics")
        assert result is not None
        assert result[0]["id"] == "c"

    def test_returns_none_for_unknown(self) -> None:
        assert find_module(_CURRICULUM, "nonexistent") is None


class TestCheckPrerequisites:
    def test_no_prereqs(self) -> None:
        """shell-basics has no prerequisites."""
        missing = check_prerequisites(_CURRICULUM, "shell-basics", set())
        assert missing == []

    def test_prereq_not_met(self) -> None:
        """shell-streams requires shell-basics."""
        missing = check_prerequisites(_CURRICULUM, "shell-streams", set())
        assert missing == ["shell-basics"]

    def test_prereq_met(self) -> None:
        missing = check_prerequisites(_CURRICULUM, "shell-streams", {"shell-basics"})
        assert missing == []

    def test_multiple_prereqs_partial(self) -> None:
        """shell-tooling requires shell-streams AND shell-permissions."""
        missing = check_prerequisites(_CURRICULUM, "shell-tooling", {"shell-streams"})
        assert missing == ["shell-permissions"]

    def test_multiple_prereqs_all_met(self) -> None:
        missing = check_prerequisites(_CURRICULUM, "shell-tooling", {"shell-streams", "shell-permissions"})
        assert missing == []

    def test_cross_track_prereq(self) -> None:
        """c-basics requires shell-basics (cross-track)."""
        missing = check_prerequisites(_CURRICULUM, "c-basics", set())
        assert missing == ["shell-basics"]

    def test_cross_track_prereq_met(self) -> None:
        missing = check_prerequisites(_CURRICULUM, "c-basics", {"shell-basics"})
        assert missing == []

    def test_multi_cross_track_prereqs(self) -> None:
        """c-build-debug requires c-basics AND shell-streams."""
        missing = check_prerequisites(_CURRICULUM, "c-build-debug", {"c-basics"})
        assert missing == ["shell-streams"]

    def test_unknown_module_returns_empty(self) -> None:
        missing = check_prerequisites(_CURRICULUM, "nonexistent", set())
        assert missing == []


class TestCheckPhaseOrdering:
    def test_foundation_module_no_phase_issue(self) -> None:
        """First foundation module has no earlier phases to check."""
        missing = check_phase_ordering(_CURRICULUM, "shell-basics", set())
        assert missing == []

    def test_practice_requires_all_foundation(self) -> None:
        """shell-tooling (practice) requires all foundation modules in shell track."""
        missing = check_phase_ordering(_CURRICULUM, "shell-tooling", set())
        assert set(missing) == {"shell-basics", "shell-streams", "shell-permissions"}

    def test_practice_with_foundation_done(self) -> None:
        completed = {"shell-basics", "shell-streams", "shell-permissions"}
        missing = check_phase_ordering(_CURRICULUM, "shell-tooling", completed)
        assert missing == []

    def test_core_requires_foundation_and_practice(self) -> None:
        """c-libft-bridge (core) needs all foundation + practice in c track."""
        missing = check_phase_ordering(_CURRICULUM, "c-libft-bridge", set())
        assert set(missing) == {"c-basics", "c-memory", "c-build-debug"}

    def test_core_partial_completion(self) -> None:
        missing = check_phase_ordering(_CURRICULUM, "c-libft-bridge", {"c-basics", "c-memory"})
        assert missing == ["c-build-debug"]

    def test_advanced_requires_all_prior(self) -> None:
        """ai-rag (advanced) needs foundation + practice in python_ai."""
        missing = check_phase_ordering(_CURRICULUM, "ai-rag", set())
        assert set(missing) == {"python-basics", "python-oop"}

    def test_unknown_module_returns_empty(self) -> None:
        missing = check_phase_ordering(_CURRICULUM, "nonexistent", set())
        assert missing == []


class TestCheckTrackEnrollment:
    def test_enrolled_in_correct_track(self) -> None:
        err = check_track_enrollment(_prog("shell"), "shell-basics", _CURRICULUM)
        assert err is None

    def test_wrong_track(self) -> None:
        err = check_track_enrollment(_prog("shell"), "c-basics", _CURRICULUM)
        assert err is not None
        assert "track 'c'" in err
        assert "active course is 'shell'" in err

    def test_unknown_module(self) -> None:
        err = check_track_enrollment(_prog("shell"), "nonexistent", _CURRICULUM)
        assert err is None  # unknown module — no enrollment error


class TestValidateModuleActivation:
    def test_entry_module_valid(self) -> None:
        """shell-basics has no prereqs, is foundation, track matches."""
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "shell-basics")
        assert errors == []

    def test_unknown_module(self) -> None:
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "nonexistent")
        assert len(errors) == 1
        assert errors[0]["type"] == "not_found"

    def test_missing_prerequisites(self) -> None:
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "shell-streams")
        types = {e["type"] for e in errors}
        assert "prerequisites" in types

    def test_wrong_track(self) -> None:
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "c-basics", completed_modules={"shell-basics"})
        types = {e["type"] for e in errors}
        assert "track_enrollment" in types

    def test_phase_ordering_violated(self) -> None:
        """shell-tooling (practice) without completing foundation modules."""
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "shell-tooling", completed_modules=set())
        types = {e["type"] for e in errors}
        assert "phase_ordering" in types
        assert "prerequisites" in types

    def test_all_valid_after_completion(self) -> None:
        """shell-tooling valid when all foundation shell modules are done."""
        completed = {"shell-basics", "shell-streams", "shell-permissions"}
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "shell-tooling", completed_modules=completed)
        assert errors == []

    def test_multiple_errors_reported(self) -> None:
        """c-libft-bridge with no completions: wrong track + prereqs + phase."""
        errors = validate_module_activation(_CURRICULUM, _prog("shell"), "c-libft-bridge", completed_modules=set())
        types = {e["type"] for e in errors}
        assert "track_enrollment" in types
        assert "prerequisites" in types
        assert "phase_ordering" in types


# ===========================================================================
# Integration tests — API endpoints
# ===========================================================================


class TestValidateEndpoint:
    def test_validate_entry_module(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/validate")
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_missing_prereqs(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-streams/validate")
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert any(e["type"] == "prerequisites" for e in data["errors"])

    def test_validate_wrong_track(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo(_prog("shell", ["shell-basics"]))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/c-basics/validate")
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert any(e["type"] == "track_enrollment" for e in data["errors"])

    def test_validate_phase_ordering(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-tooling/validate")
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert any(e["type"] == "phase_ordering" for e in data["errors"])

    def test_validate_unknown_module_404(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/nonexistent/validate")
        assert r.status_code == 404

    def test_validate_all_prereqs_met(self) -> None:
        completed = ["shell-basics", "shell-streams", "shell-permissions"]
        p_cur, p_load, p_write, _p, _w = _patch_repo(_prog("shell", completed))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-tooling/validate")
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_validate_legacy_completed_modules_still_works(self) -> None:
        legacy_progression = {
            "learning_plan": {"active_course": "shell"},
            "progress": {"completed_modules": ["shell-basics", "shell-streams", "shell-permissions"]},
        }
        p_cur, p_load, p_write, _p, _w = _patch_repo(legacy_progression)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-tooling/validate")
        assert r.status_code == 200
        assert r.json()["valid"] is True


class TestProgressionValidation:
    """POST /api/v1/progression with active_module triggers validation."""

    def test_set_active_module_valid(self) -> None:
        p_cur, p_load, p_write, _p, written = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "shell-basics"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_module"] == "shell-basics"
        assert len(written) == 1

    def test_set_active_module_prereqs_fail(self) -> None:
        p_cur, p_load, p_write, _p, written = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "shell-streams"})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert "validation_errors" in detail
        assert any(e["type"] == "prerequisites" for e in detail["validation_errors"])
        assert len(written) == 0  # no write on validation failure

    def test_set_active_module_wrong_track(self) -> None:
        p_cur, p_load, p_write, _p, _written = _patch_repo(_prog("shell", ["shell-basics"]))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "c-basics"})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert any(e["type"] == "track_enrollment" for e in detail["validation_errors"])

    def test_set_active_module_phase_fail(self) -> None:
        p_cur, p_load, p_write, _p, _written = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "shell-tooling"})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert any(e["type"] == "phase_ordering" for e in detail["validation_errors"])

    def test_set_active_module_after_completing_prereqs(self) -> None:
        completed = ["shell-basics", "shell-streams", "shell-permissions"]
        p_cur, p_load, p_write, _p, _written = _patch_repo(_prog("shell", completed))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "shell-tooling"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_module"] == "shell-tooling"

    def test_update_without_active_module_skips_validation(self) -> None:
        """Updating other fields should not trigger module validation."""
        p_cur, p_load, p_write, _p, written = _patch_repo(_prog("shell"))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"current_exercise": "Ex5"})
        assert r.status_code == 200
        assert len(written) == 1

    def test_cross_track_validation_c_after_shell(self) -> None:
        """c-basics needs shell-basics — should pass with correct track + prereqs."""
        completed = ["shell-basics"]
        p_cur, p_load, p_write, _p, _written = _patch_repo(_prog("c", completed))
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "c-basics"})
        assert r.status_code == 200

    def test_legacy_completed_modules_are_canonicalized_on_write(self) -> None:
        legacy_progression = {
            "learning_plan": {"active_course": "shell"},
            "progress": {"completed_modules": ["shell-basics", "shell-streams", "shell-permissions"]},
        }
        p_cur, p_load, p_write, _p, written = _patch_repo(legacy_progression)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "shell-tooling"})
        assert r.status_code == 200
        assert len(written) == 1
        assert "completed_modules" not in written[0]["progress"]
        assert written[0]["module_status"]["shell-basics"]["status"] == "completed"
        assert written[0]["module_status"]["shell-streams"]["status"] == "completed"
        assert written[0]["module_status"]["shell-permissions"]["status"] == "completed"
