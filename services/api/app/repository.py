"""Repository abstraction for curriculum and progression data access.

Defines an abstract interface that can be backed by JSON files (current)
or PostgreSQL (future). Endpoints depend on the abstract interface via
FastAPI's Depends mechanism, making the storage backend swappable.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any


class CurriculumRepository(ABC):
    """Abstract data-access interface for curriculum and progression."""

    # --- Curriculum (read-only) ---

    @abstractmethod
    def get_curriculum(self) -> dict[str, Any]:
        """Return the full curriculum document."""

    @abstractmethod
    def get_tracks(self) -> list[dict[str, Any]]:
        """Return all track summaries."""

    @abstractmethod
    def get_track(self, track_id: str) -> dict[str, Any] | None:
        """Return a single track by ID, or None if not found."""

    @abstractmethod
    def get_modules(self, track_id: str) -> list[dict[str, Any]]:
        """Return all modules for a given track."""

    @abstractmethod
    def get_module(self, module_id: str) -> dict[str, Any] | None:
        """Return a single module by ID (across all tracks), or None."""

    # --- Progression (read + write) ---

    @abstractmethod
    def get_progression(self, learner_id: str = "default") -> dict[str, Any]:
        """Return the progression state for a learner."""

    @abstractmethod
    def update_progression(self, data: dict[str, Any], learner_id: str = "default") -> None:
        """Persist updated progression state for a learner."""


# ---------------------------------------------------------------------------
# JSON file implementation
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]
CURRICULUM_PATH = ROOT / "packages" / "curriculum" / "data" / "42_lausanne_curriculum.json"
PROGRESSION_PATH = ROOT / "progression.json"


class JsonCurriculumRepository(CurriculumRepository):
    """JSON-file backed implementation reading from the local filesystem."""

    def __init__(
        self,
        curriculum_path: Path = CURRICULUM_PATH,
        progression_path: Path = PROGRESSION_PATH,
    ) -> None:
        self._curriculum_path = curriculum_path
        self._progression_path = progression_path

    @lru_cache(maxsize=1)
    def get_curriculum(self) -> dict[str, Any]:
        return json.loads(self._curriculum_path.read_text(encoding="utf-8"))

    def reload_curriculum(self) -> dict[str, Any]:
        self.get_curriculum.cache_clear()
        return self.get_curriculum()

    def get_tracks(self) -> list[dict[str, Any]]:
        return self.get_curriculum().get("tracks", [])

    def get_track(self, track_id: str) -> dict[str, Any] | None:
        for track in self.get_tracks():
            if track["id"] == track_id:
                return track
        return None

    def get_modules(self, track_id: str) -> list[dict[str, Any]]:
        track = self.get_track(track_id)
        if track is None:
            return []
        return track.get("modules", [])

    def get_module(self, module_id: str) -> dict[str, Any] | None:
        for track in self.get_tracks():
            for module in track.get("modules", []):
                if module["id"] == module_id:
                    return module
        return None

    def get_progression(self, learner_id: str = "default") -> dict[str, Any]:
        return json.loads(self._progression_path.read_text(encoding="utf-8"))

    def update_progression(self, data: dict[str, Any], learner_id: str = "default") -> None:
        self._progression_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Singleton & dependency injection helper
# ---------------------------------------------------------------------------

_repo: CurriculumRepository | None = None


def get_repository() -> CurriculumRepository:
    """Return the active repository instance (singleton)."""
    global _repo
    if _repo is None:
        _repo = JsonCurriculumRepository()
    return _repo


def set_repository(repo: CurriculumRepository) -> None:
    """Override the active repository (for testing or future backends)."""
    global _repo
    _repo = repo


# ---------------------------------------------------------------------------
# Backward-compatible module-level functions
# ---------------------------------------------------------------------------
# These thin wrappers keep existing imports working during migration.


def load_curriculum() -> dict[str, Any]:
    return get_repository().get_curriculum()


def load_progression() -> dict[str, Any]:
    return get_repository().get_progression()


def write_progression(data: dict[str, Any]) -> None:
    return get_repository().update_progression(data)
