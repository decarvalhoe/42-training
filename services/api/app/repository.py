from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any



def _find_root() -> Path:
    """Find project root: use DATA_ROOT env var (Docker) or traverse up from __file__."""
    env_root = os.environ.get("DATA_ROOT")
    if env_root:
        return Path(env_root)
    # Walk up from __file__ looking for the curriculum data directory.
    # Locally: .../services/api/app/repository.py -> repo root is parents[3]
    # Docker: /app/app/repository.py -> parents only go up to /
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "packages" / "curriculum" / "data").exists():
            return ancestor
    # Docker fallback: Dockerfile copies data to /packages/curriculum/data
    return Path("/")


ROOT = _find_root()
CURRICULUM_PATH = ROOT / "packages" / "curriculum" / "data" / "42_lausanne_curriculum.json"
PROGRESSION_PATH = ROOT / "progression.json"


@lru_cache(maxsize=1)
def load_curriculum() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    return result


def reload_curriculum() -> dict[str, Any]:
    load_curriculum.cache_clear()
    return load_curriculum()


def load_progression() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(PROGRESSION_PATH.read_text(encoding="utf-8"))
    return result


def write_progression(data: dict[str, Any]) -> None:
    PROGRESSION_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
