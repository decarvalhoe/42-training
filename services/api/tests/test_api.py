"""Comprehensive API tests for all endpoints (Issue #27).

Tests are isolated from the filesystem via mocked repository functions.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne", "updated_on": "2026-03-27", "status": "mvp"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell 0 to Hero",
            "summary": "Linux-first recovery track.",
            "why_it_matters": "Command fluency.",
            "modules": [
                {"id": "shell-basics", "title": "Navigation", "phase": "foundation", "skills": ["pwd", "ls"], "deliverable": "Navigate."},
                {"id": "shell-streams", "title": "Pipes", "phase": "foundation", "skills": ["pipe"], "deliverable": "Pipe."},
            ],
        },
        {
            "id": "c",
            "title": "C / Core 42",
            "summary": "Low-level rigor.",
            "why_it_matters": "Memory discipline.",
            "modules": [
                {"id": "c-basics", "title": "Syntax", "phase": "foundation", "skills": ["variables"], "deliverable": "Compile."},
            ],
        },
    ],
}

_PROGRESSION_BASE: dict[str, object] = {
    "learning_plan": {
        "pace_mode": "self_paced",
        "active_course": "shell",
        "active_module": "shell-basics",
    },
    "progress": {
        "current_exercise": "Ex1",
        "current_step": "1.1",
        "completed": ["pwd"],
        "in_progress": ["ls"],
        "todo": ["cd"],
    },
    "next_command": "ls -la",
}


def _fresh_progression() -> dict[str, object]:
    return json.loads(json.dumps(_PROGRESSION_BASE))


def _patch_repo(progression: dict[str, object] | None = None):
    """Return context-manager patches for curriculum, progression and write."""
    prog = progression if progression is not None else _fresh_progression()
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


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "api"

    def test_health_has_required_keys(self) -> None:
        data = client.get("/health").json()
        assert set(data.keys()) == {"status", "service"}


# ---------------------------------------------------------------------------
# GET /api/v1/meta
# ---------------------------------------------------------------------------


class TestMeta:
    def test_meta_happy_path(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/meta")
        assert r.status_code == 200
        data = r.json()
        assert data["app"] == "42-training"
        assert data["campus"] == "42 Lausanne"
        assert data["active_course"] == "shell"
        assert data["pace_mode"] == "self_paced"

    def test_meta_defaults_when_progression_empty(self) -> None:
        """When progression has no learning_plan, defaults apply."""
        p_cur, p_load, p_write, _p, _w = _patch_repo(progression={})
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/meta").json()
        assert data["active_course"] == "shell"
        assert data["pace_mode"] == "self_paced"

    def test_meta_response_keys(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/meta").json()
        assert set(data.keys()) == {"app", "campus", "active_course", "pace_mode"}


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_happy_path(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "curriculum" in data
        assert "progression" in data

    def test_dashboard_curriculum_has_tracks(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/dashboard").json()
        assert len(data["curriculum"]["tracks"]) == 2

    def test_dashboard_progression_reflects_state(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/dashboard").json()
        assert data["progression"]["learning_plan"]["active_course"] == "shell"


# ---------------------------------------------------------------------------
# GET /api/v1/tracks
# ---------------------------------------------------------------------------


class TestTracks:
    def test_tracks_list(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/tracks")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2

    def test_tracks_contain_expected_ids(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/tracks").json()
        ids = {t["id"] for t in data}
        assert ids == {"shell", "c"}

    def test_tracks_module_count(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/tracks").json()
        shell = next(t for t in data if t["id"] == "shell")
        assert shell["module_count"] == 2
        c_track = next(t for t in data if t["id"] == "c")
        assert c_track["module_count"] == 1

    def test_tracks_summary_fields(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/tracks").json()
        for track in data:
            assert "id" in track
            assert "title" in track
            assert "summary" in track
            assert "why_it_matters" in track
            assert "module_count" in track


# ---------------------------------------------------------------------------
# GET /api/v1/tracks/{track_id}
# ---------------------------------------------------------------------------


class TestTrackDetail:
    def test_track_detail_shell(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/tracks/shell")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "shell"
        assert len(data["modules"]) == 2

    def test_track_detail_c(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/tracks/c")
        assert r.status_code == 200
        assert r.json()["id"] == "c"

    def test_track_detail_404(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/tracks/nonexistent")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_track_detail_includes_modules(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/tracks/shell").json()
        module_ids = [m["id"] for m in data["modules"]]
        assert module_ids == ["shell-basics", "shell-streams"]

    def test_track_detail_module_has_phase(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/tracks/shell").json()
        for m in data["modules"]:
            assert "phase" in m


# ---------------------------------------------------------------------------
# GET /api/v1/progression
# ---------------------------------------------------------------------------


class TestGetProgression:
    def test_progression_happy_path(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/progression")
        assert r.status_code == 200
        data = r.json()
        assert data["learning_plan"]["active_course"] == "shell"

    def test_progression_includes_progress_block(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/progression").json()
        assert "progress" in data
        assert data["progress"]["current_exercise"] == "Ex1"

    def test_progression_empty_state(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo(progression={})
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/progression")
        assert r.status_code == 200
        data = r.json()
        assert data["learning_plan"] == {}
        assert data["progress"] == {}


# ---------------------------------------------------------------------------
# POST /api/v1/progression
# ---------------------------------------------------------------------------


class TestUpdateProgression:
    def test_update_active_course(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_course": "c"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_course"] == "c"
        assert len(written) == 1

    def test_update_active_module(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_module": "shell-streams"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_module"] == "shell-streams"

    def test_update_pace_mode(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"pace_mode": "intensive"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["pace_mode"] == "intensive"

    def test_update_current_exercise(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"current_exercise": "Ex3"})
        assert r.status_code == 200
        assert r.json()["progress"]["current_exercise"] == "Ex3"

    def test_update_current_step(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"current_step": "3.2"})
        assert r.status_code == 200
        assert r.json()["progress"]["current_step"] == "3.2"

    def test_update_next_command(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"next_command": "cd /tmp"})
        assert r.status_code == 200
        assert r.json()["next_command"] == "cd /tmp"

    def test_update_multiple_fields(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post(
                "/api/v1/progression",
                json={"active_course": "c", "current_exercise": "Ex5", "next_command": "gcc main.c"},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["learning_plan"]["active_course"] == "c"
        assert data["progress"]["current_exercise"] == "Ex5"
        assert data["next_command"] == "gcc main.c"

    def test_update_empty_payload(self) -> None:
        """Empty payload should still succeed — no fields modified."""
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_course"] == "shell"

    def test_update_preserves_existing_fields(self) -> None:
        """Updating one field should not erase others."""
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_course": "c"})
        data = r.json()
        # active_module should still be present from original
        assert data["learning_plan"]["active_module"] == "shell-basics"
        # progress block should still be intact
        assert data["progress"]["current_exercise"] == "Ex1"

    def test_update_unknown_key_ignored(self) -> None:
        """Keys not handled by the endpoint should not crash."""
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"unknown_field": "value"})
        assert r.status_code == 200

    def test_update_writes_to_persistence(self) -> None:
        """Verify write_progression is called exactly once."""
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            client.post("/api/v1/progression", json={"active_course": "c"})
        assert len(written) == 1
        assert written[0]["learning_plan"]["active_course"] == "c"


# ---------------------------------------------------------------------------
# Progression mutation consistency
# ---------------------------------------------------------------------------


class TestProgressionConsistency:
    def test_sequential_mutations_accumulate(self) -> None:
        """Multiple sequential updates should accumulate state."""
        prog = _fresh_progression()
        written: list[dict[str, object]] = []

        def fake_write(data: dict[str, object]) -> None:
            prog.clear()
            prog.update(data)
            written.append(json.loads(json.dumps(data)))

        with (
            patch("app.main.load_curriculum", return_value=_CURRICULUM),
            patch("app.main.load_progression", side_effect=lambda: json.loads(json.dumps(prog))),
            patch("app.main.write_progression", side_effect=fake_write),
        ):
            # First update: change course
            r1 = client.post("/api/v1/progression", json={"active_course": "c"})
            assert r1.json()["learning_plan"]["active_course"] == "c"

            # Second update: change exercise
            r2 = client.post("/api/v1/progression", json={"current_exercise": "Ex10"})
            data2 = r2.json()
            # Both mutations should be reflected
            assert data2["learning_plan"]["active_course"] == "c"
            assert data2["progress"]["current_exercise"] == "Ex10"

            # Third update: change step
            r3 = client.post("/api/v1/progression", json={"current_step": "10.3"})
            data3 = r3.json()
            assert data3["learning_plan"]["active_course"] == "c"
            assert data3["progress"]["current_exercise"] == "Ex10"
            assert data3["progress"]["current_step"] == "10.3"

        assert len(written) == 3

    def test_get_reflects_latest_write(self) -> None:
        """GET /progression should return the state after POST."""
        prog = _fresh_progression()

        def fake_write(data: dict[str, object]) -> None:
            prog.clear()
            prog.update(data)

        with (
            patch("app.main.load_curriculum", return_value=_CURRICULUM),
            patch("app.main.load_progression", side_effect=lambda: json.loads(json.dumps(prog))),
            patch("app.main.write_progression", side_effect=fake_write),
        ):
            client.post("/api/v1/progression", json={"active_course": "python_ai"})
            r = client.get("/api/v1/progression")

        assert r.json()["learning_plan"]["active_course"] == "python_ai"


# ---------------------------------------------------------------------------
# 422 validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_post_progression_invalid_json(self) -> None:
        """Sending non-JSON body should return 422."""
        r = client.post("/api/v1/progression", content=b"not json", headers={"content-type": "application/json"})
        assert r.status_code == 422

    def test_post_progression_non_object_body(self) -> None:
        """Sending a JSON array instead of object."""
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json=[1, 2, 3])
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_tracks_empty_modules(self) -> None:
        """Track with no modules should have module_count=0."""
        curriculum_no_modules = {
            "metadata": {"campus": "42 Lausanne"},
            "tracks": [
                {"id": "empty", "title": "Empty", "summary": "No modules", "why_it_matters": "Test"},
            ],
        }
        with patch("app.main.load_curriculum", return_value=curriculum_no_modules):
            data = client.get("/api/v1/tracks").json()
        assert data[0]["module_count"] == 0

    def test_track_detail_special_characters_in_id(self) -> None:
        """Track IDs with URL-safe special chars should still 404 properly."""
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/tracks/some-weird-id_123")
        assert r.status_code == 404

    def test_progression_missing_learning_plan(self) -> None:
        """POST should create learning_plan if absent in progression."""
        p_cur, p_load, p_write, prog, written = _patch_repo(progression={"progress": {}})
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"active_course": "c"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_course"] == "c"

    def test_progression_missing_progress_block(self) -> None:
        """POST should create progress block if absent."""
        p_cur, p_load, p_write, prog, written = _patch_repo(progression={"learning_plan": {}})
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/progression", json={"current_exercise": "Ex1"})
        assert r.status_code == 200
        assert r.json()["progress"]["current_exercise"] == "Ex1"
