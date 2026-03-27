"""Tests for the repository abstraction layer (Issue #28)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.repository import (
    CurriculumRepository,
    JsonCurriculumRepository,
    get_repository,
    set_repository,
)


# ---------------------------------------------------------------------------
# Abstract interface contract
# ---------------------------------------------------------------------------


class TestAbstractInterface:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            CurriculumRepository()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# JsonCurriculumRepository
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
                {"id": "shell-basics", "title": "Basics", "phase": "foundation"},
                {"id": "shell-streams", "title": "Streams", "phase": "foundation"},
            ],
        },
        {
            "id": "c",
            "title": "C",
            "summary": "C track",
            "why_it_matters": "Low-level",
            "modules": [
                {"id": "c-basics", "title": "Syntax", "phase": "foundation"},
            ],
        },
    ],
}

_PROGRESSION = {
    "learning_plan": {"active_course": "shell"},
    "progress": {"current_exercise": "Ex1"},
}


@pytest.fixture()
def json_repo(tmp_path: Path) -> JsonCurriculumRepository:
    cur_path = tmp_path / "curriculum.json"
    prog_path = tmp_path / "progression.json"
    cur_path.write_text(json.dumps(_CURRICULUM), encoding="utf-8")
    prog_path.write_text(json.dumps(_PROGRESSION), encoding="utf-8")
    return JsonCurriculumRepository(curriculum_path=cur_path, progression_path=prog_path)


class TestJsonCurriculumRepository:
    def test_get_curriculum(self, json_repo: JsonCurriculumRepository) -> None:
        cur = json_repo.get_curriculum()
        assert cur["metadata"]["campus"] == "42 Lausanne"
        assert len(cur["tracks"]) == 2

    def test_get_tracks(self, json_repo: JsonCurriculumRepository) -> None:
        tracks = json_repo.get_tracks()
        assert len(tracks) == 2
        assert tracks[0]["id"] == "shell"

    def test_get_track_found(self, json_repo: JsonCurriculumRepository) -> None:
        track = json_repo.get_track("shell")
        assert track is not None
        assert track["id"] == "shell"

    def test_get_track_not_found(self, json_repo: JsonCurriculumRepository) -> None:
        assert json_repo.get_track("nonexistent") is None

    def test_get_modules(self, json_repo: JsonCurriculumRepository) -> None:
        modules = json_repo.get_modules("shell")
        assert len(modules) == 2
        assert modules[0]["id"] == "shell-basics"

    def test_get_modules_unknown_track(self, json_repo: JsonCurriculumRepository) -> None:
        assert json_repo.get_modules("nonexistent") == []

    def test_get_module_found(self, json_repo: JsonCurriculumRepository) -> None:
        module = json_repo.get_module("c-basics")
        assert module is not None
        assert module["id"] == "c-basics"

    def test_get_module_not_found(self, json_repo: JsonCurriculumRepository) -> None:
        assert json_repo.get_module("nonexistent") is None

    def test_get_module_cross_track(self, json_repo: JsonCurriculumRepository) -> None:
        """get_module searches across all tracks."""
        assert json_repo.get_module("shell-basics") is not None
        assert json_repo.get_module("c-basics") is not None

    def test_get_progression(self, json_repo: JsonCurriculumRepository) -> None:
        prog = json_repo.get_progression()
        assert prog["learning_plan"]["active_course"] == "shell"

    def test_update_progression(self, json_repo: JsonCurriculumRepository) -> None:
        new_data: dict[str, Any] = {"learning_plan": {"active_course": "c"}, "progress": {}}
        json_repo.update_progression(new_data)
        reloaded = json_repo.get_progression()
        assert reloaded["learning_plan"]["active_course"] == "c"

    def test_curriculum_is_cached(self, json_repo: JsonCurriculumRepository) -> None:
        """Repeated calls should return the same object (lru_cache)."""
        a = json_repo.get_curriculum()
        b = json_repo.get_curriculum()
        assert a is b

    def test_reload_curriculum(self, json_repo: JsonCurriculumRepository) -> None:
        a = json_repo.get_curriculum()
        b = json_repo.reload_curriculum()
        # After reload, should be a fresh object
        assert a is not b
        assert a == b


# ---------------------------------------------------------------------------
# Singleton / set_repository
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_set_and_get_repository(self, json_repo: JsonCurriculumRepository) -> None:
        set_repository(json_repo)
        assert get_repository() is json_repo

    def test_override_repository(self, json_repo: JsonCurriculumRepository) -> None:
        set_repository(json_repo)
        other = JsonCurriculumRepository.__new__(JsonCurriculumRepository)
        set_repository(other)
        assert get_repository() is other
        # Clean up
        set_repository(json_repo)
