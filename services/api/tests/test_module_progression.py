"""Tests for module progression CRUD endpoints (Issue #24)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Minimal curriculum fixture for tests
_TEST_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell",
            "summary": "Shell track",
            "why_it_matters": "Fundamentals",
            "modules": [
                {"id": "shell-basics", "title": "Basics", "phase": "foundation", "skills": [], "deliverable": ""},
                {"id": "shell-streams", "title": "Streams", "phase": "foundation", "skills": [], "deliverable": ""},
            ],
        }
    ],
}


def _make_progression(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"learning_plan": {}, "progress": {}, "module_status": {}}
    base.update(overrides)
    return base


def _patch_repo(progression: dict[str, object] | None = None):
    """Patch load_curriculum and load/write_progression for isolated tests."""
    prog = progression if progression is not None else _make_progression()
    written: list[dict[str, object]] = []

    def fake_write(data: dict[str, object]) -> None:
        prog.clear()
        prog.update(data)
        written.append(data)

    return (
        patch("app.main.load_curriculum", return_value=_TEST_CURRICULUM),
        patch("app.main.load_progression", side_effect=lambda: json.loads(json.dumps(prog))),
        patch("app.main.write_progression", side_effect=fake_write),
        prog,
        written,
    )


class TestModuleStatus:
    def test_status_not_started(self) -> None:
        p_cur, p_load, p_write, _prog, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/modules/shell-basics/status")
        assert r.status_code == 200
        data = r.json()
        assert data["module_id"] == "shell-basics"
        assert data["track_id"] == "shell"
        assert data["status"] == "not_started"

    def test_status_after_start(self) -> None:
        prog = _make_progression(module_status={"shell-basics": {"status": "in_progress", "started_at": "2026-01-01T00:00:00+00:00"}})
        p_cur, p_load, p_write, _prog, _w = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/modules/shell-basics/status")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_status_unknown_module(self) -> None:
        p_cur, p_load, p_write, _prog, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/modules/nonexistent/status")
        assert r.status_code == 404


class TestModuleStart:
    def test_start_first_module(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/start")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "in_progress"
        assert data["message"] == "Module started"
        assert len(written) == 1

    def test_start_already_in_progress(self) -> None:
        prog = _make_progression(module_status={"shell-basics": {"status": "in_progress", "started_at": "2026-01-01T00:00:00+00:00"}})
        p_cur, p_load, p_write, _prog, written = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/start")
        assert r.status_code == 200
        assert r.json()["message"] == "Module already in progress"
        assert len(written) == 0  # no write when already in progress

    def test_start_blocked_by_prerequisite(self) -> None:
        """shell-streams requires shell-basics to be completed/skipped first."""
        p_cur, p_load, p_write, _prog, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-streams/start")
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert "shell-basics" in detail["missing_prerequisites"]

    def test_start_after_prerequisite_completed(self) -> None:
        prog = _make_progression(module_status={"shell-basics": {"status": "completed", "completed_at": "2026-01-01T00:00:00+00:00"}})
        p_cur, p_load, p_write, _prog, written = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-streams/start")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_start_after_prerequisite_skipped(self) -> None:
        prog = _make_progression(module_status={"shell-basics": {"status": "skipped", "skipped_at": "2026-01-01T00:00:00+00:00"}})
        p_cur, p_load, p_write, _prog, written = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-streams/start")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_start_unknown_module(self) -> None:
        p_cur, p_load, p_write, _prog, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/nonexistent/start")
        assert r.status_code == 404


class TestModuleComplete:
    def test_complete_in_progress_module(self) -> None:
        prog = _make_progression(module_status={"shell-basics": {"status": "in_progress", "started_at": "2026-01-01T00:00:00+00:00"}})
        p_cur, p_load, p_write, _prog, written = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/complete")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        assert data["message"] == "Module completed"
        assert len(written) == 1

    def test_complete_not_started_fails(self) -> None:
        p_cur, p_load, p_write, _prog, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/complete")
        assert r.status_code == 409

    def test_complete_already_completed_fails(self) -> None:
        prog = _make_progression(module_status={"shell-basics": {"status": "completed", "completed_at": "2026-01-01T00:00:00+00:00"}})
        p_cur, p_load, p_write, _prog, _w = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/complete")
        assert r.status_code == 409


class TestModuleSkip:
    def test_skip_module(self) -> None:
        p_cur, p_load, p_write, _prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/skip")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "skipped"
        assert len(written) == 1

    def test_skip_with_reason(self) -> None:
        p_cur, p_load, p_write, _prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/shell-basics/skip", json={"reason": "Already know this"})
        assert r.status_code == 200
        assert r.json()["status"] == "skipped"
        assert len(written) == 1

    def test_skip_unknown_module(self) -> None:
        p_cur, p_load, p_write, _prog, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/modules/nonexistent/skip")
        assert r.status_code == 404
