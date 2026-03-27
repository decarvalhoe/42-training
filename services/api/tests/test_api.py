"""Comprehensive API tests for all endpoints (Issue #27).

Tests are isolated from the filesystem via an in-memory repository.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repository import CurriculumRepository, set_repository

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


class InMemoryRepository(CurriculumRepository):
    """In-memory repository for isolated testing."""

    def __init__(self, curriculum: dict, progression: dict | None = None) -> None:
        self._curriculum = curriculum
        self._progression = progression if progression is not None else {}
        self.written: list[dict] = []

    def get_curriculum(self):
        return self._curriculum

    def get_tracks(self):
        return self._curriculum.get("tracks", [])

    def get_track(self, track_id):
        for t in self.get_tracks():
            if t["id"] == track_id:
                return t
        return None

    def get_modules(self, track_id):
        t = self.get_track(track_id)
        return t.get("modules", []) if t else []

    def get_module(self, module_id):
        for t in self.get_tracks():
            for m in t.get("modules", []):
                if m["id"] == module_id:
                    return m
        return None

    def get_progression(self, learner_id="default"):
        return json.loads(json.dumps(self._progression))

    def update_progression(self, data, learner_id="default"):
        self._progression = json.loads(json.dumps(data))
        self.written.append(json.loads(json.dumps(data)))


def _make_repo(progression: dict[str, object] | None = None, curriculum: dict | None = None) -> InMemoryRepository:
    prog = progression if progression is not None else _fresh_progression()
    cur = curriculum if curriculum is not None else _CURRICULUM
    return InMemoryRepository(cur, prog)


@pytest.fixture(autouse=True)
def _install_test_repo():
    """Install and clean up the test repository for each test."""
    repo = _make_repo()
    set_repository(repo)
    yield
    set_repository(repo)  # reset after test


def _use_repo(progression: dict[str, object] | None = None, curriculum: dict | None = None) -> InMemoryRepository:
    """Install a custom repo for a single test and return it."""
    repo = _make_repo(progression, curriculum)
    set_repository(repo)
    return repo


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
        r = client.get("/api/v1/meta")
        assert r.status_code == 200
        data = r.json()
        assert data["app"] == "42-training"
        assert data["campus"] == "42 Lausanne"
        assert data["active_course"] == "shell"
        assert data["pace_mode"] == "self_paced"

    def test_meta_defaults_when_progression_empty(self) -> None:
        """When progression has no learning_plan, defaults apply."""
        _use_repo(progression={})
        data = client.get("/api/v1/meta").json()
        assert data["active_course"] == "shell"
        assert data["pace_mode"] == "self_paced"

    def test_meta_response_keys(self) -> None:
        data = client.get("/api/v1/meta").json()
        assert set(data.keys()) == {"app", "campus", "active_course", "pace_mode"}


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_happy_path(self) -> None:
        r = client.get("/api/v1/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "curriculum" in data
        assert "progression" in data

    def test_dashboard_curriculum_has_tracks(self) -> None:
        data = client.get("/api/v1/dashboard").json()
        assert len(data["curriculum"]["tracks"]) == 2

    def test_dashboard_progression_reflects_state(self) -> None:
        data = client.get("/api/v1/dashboard").json()
        assert data["progression"]["learning_plan"]["active_course"] == "shell"


# ---------------------------------------------------------------------------
# GET /api/v1/tracks
# ---------------------------------------------------------------------------


class TestTracks:
    def test_tracks_list(self) -> None:
        r = client.get("/api/v1/tracks")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2

    def test_tracks_contain_expected_ids(self) -> None:
        data = client.get("/api/v1/tracks").json()
        ids = {t["id"] for t in data}
        assert ids == {"shell", "c"}

    def test_tracks_module_count(self) -> None:
        data = client.get("/api/v1/tracks").json()
        shell = next(t for t in data if t["id"] == "shell")
        assert shell["module_count"] == 2
        c_track = next(t for t in data if t["id"] == "c")
        assert c_track["module_count"] == 1

    def test_tracks_summary_fields(self) -> None:
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
        r = client.get("/api/v1/tracks/shell")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "shell"
        assert len(data["modules"]) == 2

    def test_track_detail_c(self) -> None:
        r = client.get("/api/v1/tracks/c")
        assert r.status_code == 200
        assert r.json()["id"] == "c"

    def test_track_detail_404(self) -> None:
        r = client.get("/api/v1/tracks/nonexistent")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_track_detail_includes_modules(self) -> None:
        data = client.get("/api/v1/tracks/shell").json()
        module_ids = [m["id"] for m in data["modules"]]
        assert module_ids == ["shell-basics", "shell-streams"]

    def test_track_detail_module_has_phase(self) -> None:
        data = client.get("/api/v1/tracks/shell").json()
        for m in data["modules"]:
            assert "phase" in m


# ---------------------------------------------------------------------------
# GET /api/v1/progression
# ---------------------------------------------------------------------------


class TestGetProgression:
    def test_progression_happy_path(self) -> None:
        r = client.get("/api/v1/progression")
        assert r.status_code == 200
        data = r.json()
        assert data["learning_plan"]["active_course"] == "shell"

    def test_progression_includes_progress_block(self) -> None:
        data = client.get("/api/v1/progression").json()
        assert "progress" in data
        assert data["progress"]["current_exercise"] == "Ex1"

    def test_progression_empty_state(self) -> None:
        _use_repo(progression={})
        r = client.get("/api/v1/progression")
        assert r.status_code == 200
        assert r.json() == {}


# ---------------------------------------------------------------------------
# POST /api/v1/progression
# ---------------------------------------------------------------------------


class TestUpdateProgression:
    def test_update_active_course(self) -> None:
        repo = _use_repo()
        r = client.post("/api/v1/progression", json={"active_course": "c"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_course"] == "c"
        assert len(repo.written) == 1

    def test_update_active_module(self) -> None:
        r = client.post("/api/v1/progression", json={"active_module": "shell-streams"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_module"] == "shell-streams"

    def test_update_pace_mode(self) -> None:
        r = client.post("/api/v1/progression", json={"pace_mode": "intensive"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["pace_mode"] == "intensive"

    def test_update_current_exercise(self) -> None:
        r = client.post("/api/v1/progression", json={"current_exercise": "Ex3"})
        assert r.status_code == 200
        assert r.json()["progress"]["current_exercise"] == "Ex3"

    def test_update_current_step(self) -> None:
        r = client.post("/api/v1/progression", json={"current_step": "3.2"})
        assert r.status_code == 200
        assert r.json()["progress"]["current_step"] == "3.2"

    def test_update_next_command(self) -> None:
        r = client.post("/api/v1/progression", json={"next_command": "cd /tmp"})
        assert r.status_code == 200
        assert r.json()["next_command"] == "cd /tmp"

    def test_update_multiple_fields(self) -> None:
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
        r = client.post("/api/v1/progression", json={})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_course"] == "shell"

    def test_update_preserves_existing_fields(self) -> None:
        """Updating one field should not erase others."""
        r = client.post("/api/v1/progression", json={"active_course": "c"})
        data = r.json()
        assert data["learning_plan"]["active_module"] == "shell-basics"
        assert data["progress"]["current_exercise"] == "Ex1"

    def test_update_unknown_key_ignored(self) -> None:
        """Keys not handled by the endpoint should not crash."""
        r = client.post("/api/v1/progression", json={"unknown_field": "value"})
        assert r.status_code == 200

    def test_update_writes_to_persistence(self) -> None:
        """Verify update_progression is called exactly once."""
        repo = _use_repo()
        client.post("/api/v1/progression", json={"active_course": "c"})
        assert len(repo.written) == 1
        assert repo.written[0]["learning_plan"]["active_course"] == "c"


# ---------------------------------------------------------------------------
# Progression mutation consistency
# ---------------------------------------------------------------------------


class TestProgressionConsistency:
    def test_sequential_mutations_accumulate(self) -> None:
        """Multiple sequential updates should accumulate state."""
        repo = _use_repo()

        r1 = client.post("/api/v1/progression", json={"active_course": "c"})
        assert r1.json()["learning_plan"]["active_course"] == "c"

        r2 = client.post("/api/v1/progression", json={"current_exercise": "Ex10"})
        data2 = r2.json()
        assert data2["learning_plan"]["active_course"] == "c"
        assert data2["progress"]["current_exercise"] == "Ex10"

        r3 = client.post("/api/v1/progression", json={"current_step": "10.3"})
        data3 = r3.json()
        assert data3["learning_plan"]["active_course"] == "c"
        assert data3["progress"]["current_exercise"] == "Ex10"
        assert data3["progress"]["current_step"] == "10.3"

        assert len(repo.written) == 3

    def test_get_reflects_latest_write(self) -> None:
        """GET /progression should return the state after POST."""
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
        r = client.post("/api/v1/progression", json=[1, 2, 3])
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_tracks_empty_modules(self) -> None:
        """Track with no modules should have module_count=0."""
        _use_repo(curriculum={
            "metadata": {"campus": "42 Lausanne"},
            "tracks": [
                {"id": "empty", "title": "Empty", "summary": "No modules", "why_it_matters": "Test"},
            ],
        })
        data = client.get("/api/v1/tracks").json()
        assert data[0]["module_count"] == 0

    def test_track_detail_special_characters_in_id(self) -> None:
        """Track IDs with URL-safe special chars should still 404 properly."""
        r = client.get("/api/v1/tracks/some-weird-id_123")
        assert r.status_code == 404

    def test_progression_missing_learning_plan(self) -> None:
        """POST should create learning_plan if absent in progression."""
        _use_repo(progression={"progress": {}})
        r = client.post("/api/v1/progression", json={"active_course": "c"})
        assert r.status_code == 200
        assert r.json()["learning_plan"]["active_course"] == "c"

    def test_progression_missing_progress_block(self) -> None:
        """POST should create progress block if absent."""
        _use_repo(progression={"learning_plan": {}})
        r = client.post("/api/v1/progression", json={"current_exercise": "Ex1"})
        assert r.status_code == 200
        assert r.json()["progress"]["current_exercise"] == "Ex1"
