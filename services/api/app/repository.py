from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any


class CurriculumRepository(ABC):
    """Abstract data access for curriculum and learner progression.

    Implementations can back this with JSON files, PostgreSQL, or any
    other storage.  Endpoints depend only on this interface.
    """

    # -- curriculum reads --

    @abstractmethod
    def get_curriculum(self) -> dict[str, Any]:
        """Return the full curriculum document."""

    @abstractmethod
    def get_tracks(self) -> list[dict[str, Any]]:
        """Return track summaries (id, title, summary, why_it_matters, module_count)."""

    @abstractmethod
    def get_track(self, track_id: str) -> dict[str, Any] | None:
        """Return a single track with its modules, or None if not found."""

    @abstractmethod
    def get_modules(self, track_id: str) -> list[dict[str, Any]]:
        """Return all modules for a given track."""

    @abstractmethod
    def get_module(self, module_id: str) -> dict[str, Any] | None:
        """Return a single module by id, or None if not found."""

    # -- progression --

    @abstractmethod
    def get_progression(self, learner_id: str = "default") -> dict[str, Any]:
        """Return progression state for a learner."""

    @abstractmethod
    def update_progression(
        self, data: dict[str, Any], learner_id: str = "default"
    ) -> dict[str, Any]:
        """Merge *data* into the learner's progression and return the updated state."""


# ---------------------------------------------------------------------------
# JSON file implementation
# ---------------------------------------------------------------------------


def _find_root() -> Path:
    """Find project root: use DATA_ROOT env var (Docker) or traverse up from __file__."""
    env_root = os.environ.get("DATA_ROOT")
    if env_root:
        return Path(env_root)
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "packages" / "curriculum" / "data").exists():
        return candidate
    return Path("/")


ROOT = _find_root()
CURRICULUM_PATH = (
    ROOT / "packages" / "curriculum" / "data" / "42_lausanne_curriculum.json"
)
PROGRESSION_PATH = ROOT / "progression.json"


class JsonCurriculumRepository(CurriculumRepository):
    """Reads curriculum from a JSON file and progression from another."""

    def __init__(
        self,
        curriculum_path: Path = CURRICULUM_PATH,
        progression_path: Path = PROGRESSION_PATH,
    ) -> None:
        self._curriculum_path = curriculum_path
        self._progression_path = progression_path

    @lru_cache(maxsize=1)  # noqa: B019
    def get_curriculum(self) -> dict[str, Any]:
        return json.loads(self._curriculum_path.read_text(encoding="utf-8"))

    def reload_curriculum(self) -> dict[str, Any]:
        self.get_curriculum.cache_clear()
        return self.get_curriculum()

    def get_tracks(self) -> list[dict[str, Any]]:
        curriculum = self.get_curriculum()
        result: list[dict[str, Any]] = []
        for track in curriculum["tracks"]:
            result.append(
                {
                    "id": track["id"],
                    "title": track["title"],
                    "summary": track["summary"],
                    "why_it_matters": track["why_it_matters"],
                    "module_count": len(track.get("modules", [])),
                }
            )
        return result

    def get_track(self, track_id: str) -> dict[str, Any] | None:
        curriculum = self.get_curriculum()
        for track in curriculum["tracks"]:
            if track["id"] == track_id:
                return track
        return None

    def get_modules(self, track_id: str) -> list[dict[str, Any]]:
        track = self.get_track(track_id)
        if track is None:
            return []
        return track.get("modules", [])

    def get_module(self, module_id: str) -> dict[str, Any] | None:
        curriculum = self.get_curriculum()
        for track in curriculum["tracks"]:
            for module in track.get("modules", []):
                if module["id"] == module_id:
                    return module
        return None

    def get_progression(self, learner_id: str = "default") -> dict[str, Any]:
        return json.loads(self._progression_path.read_text(encoding="utf-8"))

    def update_progression(
        self, data: dict[str, Any], learner_id: str = "default"
    ) -> dict[str, Any]:
        current = self.get_progression(learner_id)
        learning_plan = current.setdefault("learning_plan", {})
        progress = current.setdefault("progress", {})

        for key in ("active_course", "active_module", "pace_mode"):
            if key in data:
                learning_plan[key] = data[key]

        for key in ("current_exercise", "current_step"):
            if key in data:
                progress[key] = data[key]

        if "next_command" in data:
            current["next_command"] = data["next_command"]

        self._write_progression(current)
        return current

    def _write_progression(self, data: dict[str, Any]) -> None:
        self._progression_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Default instance — used by endpoints
# ---------------------------------------------------------------------------

repo = JsonCurriculumRepository()


# ---------------------------------------------------------------------------
# Legacy function API — kept for backward compatibility (ai_gateway, etc.)
# ---------------------------------------------------------------------------


def load_curriculum() -> dict[str, Any]:
    return repo.get_curriculum()


def reload_curriculum() -> dict[str, Any]:
    return repo.reload_curriculum()


def load_progression() -> dict[str, Any]:
    return repo.get_progression()


def write_progression(data: dict[str, Any]) -> None:
    repo._write_progression(data)
