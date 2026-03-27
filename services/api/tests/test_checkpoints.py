"""Tests for checkpoint submission and listing endpoints (Issue #37)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CheckpointSubmission

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
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
                {
                    "id": "shell-basics",
                    "title": "Navigation",
                    "phase": "foundation",
                    "skills": ["pwd", "ls"],
                    "deliverable": "Navigate.",
                    "exit_criteria": [
                        "Complete a blind navigation exercise without errors",
                        "Recreate a given directory tree from a textual spec",
                        "Explain the difference between cp and mv in own words",
                    ],
                },
                {
                    "id": "shell-streams",
                    "title": "Pipes",
                    "phase": "foundation",
                    "skills": ["pipe"],
                    "deliverable": "Pipe.",
                    "exit_criteria": [
                        "Build a 3-stage pipeline",
                    ],
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
                    "skills": [],
                    "deliverable": "Compile.",
                    # No exit_criteria — tests empty case
                },
            ],
        },
    ],
}


def _prog(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"learning_plan": {}, "progress": {}}
    base.update(overrides)
    return base


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


# ---------------------------------------------------------------------------
# POST /api/v1/checkpoints/submit
# ---------------------------------------------------------------------------


class TestSubmitCheckpoint:
    def test_submit_happy_path(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 0,
                "type": "exit_criteria",
                "evidence": "cd /tmp && pwd => /tmp",
                "self_evaluation": "pass",
            })
        assert r.status_code == 200
        data = r.json()
        assert data["module_id"] == "shell-basics"
        assert data["checkpoint_index"] == 0
        assert data["prompt"] == "Complete a blind navigation exercise without errors"
        assert data["evidence"] == "cd /tmp && pwd => /tmp"
        assert data["self_evaluation"] == "pass"
        assert "submitted_at" in data
        assert len(written) == 1
        assert len(written[0]["checkpoints"]) == 1

    def test_submit_second_checkpoint(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 1,
                "type": "exit_criteria",
                "evidence": "mkdir -p a/b/c && tree a",
                "self_evaluation": "partial",
            })
        assert r.status_code == 200
        assert r.json()["checkpoint_index"] == 1
        assert r.json()["self_evaluation"] == "partial"

    def test_submit_fail_evaluation(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 2,
                "type": "exit_criteria",
                "evidence": "I'm not sure about the difference",
                "self_evaluation": "fail",
            })
        assert r.status_code == 200
        assert r.json()["self_evaluation"] == "fail"

    def test_submit_unknown_module_404(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "nonexistent",
                "checkpoint_index": 0,
                "type": "exit_criteria",
                "evidence": "test",
                "self_evaluation": "pass",
            })
        assert r.status_code == 404

    def test_submit_index_out_of_range(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 99,
                "type": "exit_criteria",
                "evidence": "test",
                "self_evaluation": "pass",
            })
        assert r.status_code == 422
        assert "out of range" in r.json()["detail"]

    def test_submit_module_no_exit_criteria(self) -> None:
        """c-basics has no exit_criteria — index 0 should be out of range."""
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "c-basics",
                "checkpoint_index": 0,
                "type": "exit_criteria",
                "evidence": "test",
                "self_evaluation": "pass",
            })
        assert r.status_code == 422

    def test_submit_empty_evidence_rejected(self) -> None:
        """Evidence must be non-empty."""
        r = client.post("/api/v1/checkpoints/submit", json={
            "module_id": "shell-basics",
            "checkpoint_index": 0,
            "type": "exit_criteria",
            "evidence": "",
            "self_evaluation": "pass",
        })
        assert r.status_code == 422

    def test_submit_invalid_self_evaluation_rejected(self) -> None:
        r = client.post("/api/v1/checkpoints/submit", json={
            "module_id": "shell-basics",
            "checkpoint_index": 0,
            "type": "exit_criteria",
            "evidence": "some evidence",
            "self_evaluation": "maybe",
        })
        assert r.status_code == 422

    def test_submit_invalid_type_rejected(self) -> None:
        r = client.post("/api/v1/checkpoints/submit", json={
            "module_id": "shell-basics",
            "checkpoint_index": 0,
            "type": "exam",
            "evidence": "some evidence",
            "self_evaluation": "pass",
        })
        assert r.status_code == 422

    def test_submit_persists_to_progression(self) -> None:
        """Verify the checkpoint record is written to progression data."""
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 0,
                "type": "exit_criteria",
                "evidence": "pwd => /tmp",
                "self_evaluation": "pass",
            })
        assert len(written) == 1
        record = written[0]["checkpoints"][0]
        assert record["module_id"] == "shell-basics"
        assert record["evidence"] == "pwd => /tmp"
        assert record["self_evaluation"] == "pass"

    def test_submit_appends_to_existing_checkpoints(self) -> None:
        """Multiple submissions should accumulate."""
        existing = _prog(checkpoints=[{
            "module_id": "shell-basics",
            "checkpoint_index": 0,
            "type": "exit_criteria",
            "prompt": "old",
            "evidence": "old evidence",
            "self_evaluation": "fail",
            "submitted_at": "2026-01-01T00:00:00+00:00",
        }])
        p_cur, p_load, p_write, prog, written = _patch_repo(existing)
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 0,
                "type": "exit_criteria",
                "evidence": "new evidence",
                "self_evaluation": "pass",
            })
        assert r.status_code == 200
        assert len(written) == 1
        assert len(written[0]["checkpoints"]) == 2

    def test_submit_deliverable_type(self) -> None:
        p_cur, p_load, p_write, prog, written = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.post("/api/v1/checkpoints/submit", json={
                "module_id": "shell-basics",
                "checkpoint_index": 0,
                "type": "deliverable",
                "evidence": "I can navigate freely",
                "self_evaluation": "pass",
            })
        assert r.status_code == 200
        assert r.json()["type"] == "deliverable"


# ---------------------------------------------------------------------------
# GET /api/v1/checkpoints/{module_id}
# ---------------------------------------------------------------------------


class TestListCheckpoints:
    def test_list_no_submissions(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/checkpoints/shell-basics")
        assert r.status_code == 200
        data = r.json()
        assert data["module_id"] == "shell-basics"
        assert len(data["checkpoints"]) == 3
        for cp in data["checkpoints"]:
            assert cp["submitted"] is False
            assert cp["self_evaluation"] is None
            assert cp["submitted_at"] is None

    def test_list_with_submission(self) -> None:
        prog = _prog(checkpoints=[{
            "module_id": "shell-basics",
            "checkpoint_index": 0,
            "type": "exit_criteria",
            "prompt": "Complete a blind navigation exercise without errors",
            "evidence": "cd /tmp && pwd => /tmp",
            "self_evaluation": "pass",
            "submitted_at": "2026-03-27T10:00:00+00:00",
        }])
        p_cur, p_load, p_write, _p, _w = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/checkpoints/shell-basics")
        data = r.json()
        assert data["checkpoints"][0]["submitted"] is True
        assert data["checkpoints"][0]["self_evaluation"] == "pass"
        assert data["checkpoints"][1]["submitted"] is False

    def test_list_shows_latest_submission(self) -> None:
        """When multiple submissions exist, the latest is shown."""
        prog = _prog(checkpoints=[
            {
                "module_id": "shell-basics", "checkpoint_index": 0,
                "type": "exit_criteria", "prompt": "p",
                "evidence": "first", "self_evaluation": "fail",
                "submitted_at": "2026-03-27T09:00:00+00:00",
            },
            {
                "module_id": "shell-basics", "checkpoint_index": 0,
                "type": "exit_criteria", "prompt": "p",
                "evidence": "second", "self_evaluation": "pass",
                "submitted_at": "2026-03-27T10:00:00+00:00",
            },
        ])
        p_cur, p_load, p_write, _p, _w = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/checkpoints/shell-basics")
        cp0 = r.json()["checkpoints"][0]
        assert cp0["self_evaluation"] == "pass"
        assert cp0["submitted_at"] == "2026-03-27T10:00:00+00:00"

    def test_list_unknown_module_404(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/checkpoints/nonexistent")
        assert r.status_code == 404

    def test_list_module_no_exit_criteria(self) -> None:
        """c-basics has no exit_criteria — should return empty list."""
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/checkpoints/c-basics")
        assert r.status_code == 200
        assert r.json()["checkpoints"] == []

    def test_list_different_modules_isolated(self) -> None:
        """Submissions for one module should not appear in another."""
        prog = _prog(checkpoints=[{
            "module_id": "shell-basics", "checkpoint_index": 0,
            "type": "exit_criteria", "prompt": "p",
            "evidence": "e", "self_evaluation": "pass",
            "submitted_at": "2026-03-27T10:00:00+00:00",
        }])
        p_cur, p_load, p_write, _p, _w = _patch_repo(prog)
        with p_cur, p_load, p_write:
            r = client.get("/api/v1/checkpoints/shell-streams")
        data = r.json()
        assert len(data["checkpoints"]) == 1
        assert data["checkpoints"][0]["submitted"] is False

    def test_list_checkpoint_has_correct_prompts(self) -> None:
        p_cur, p_load, p_write, _p, _w = _patch_repo()
        with p_cur, p_load, p_write:
            data = client.get("/api/v1/checkpoints/shell-basics").json()
        prompts = [cp["prompt"] for cp in data["checkpoints"]]
        assert prompts == [
            "Complete a blind navigation exercise without errors",
            "Recreate a given directory tree from a textual spec",
            "Explain the difference between cp and mv in own words",
        ]
