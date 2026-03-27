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
    # In Docker: /app/app/repository.py -> parents[3] = /
    # Locally: .../services/api/app/repository.py -> parents[3] = repo root
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "packages" / "curriculum" / "data").exists():
        return candidate
    # Docker fallback: data is at /
    return Path("/")


ROOT = _find_root()
CURRICULUM_PATH = ROOT / "packages" / "curriculum" / "data" / "42_lausanne_curriculum.json"
PROGRESSION_PATH = ROOT / "progression.json"


@lru_cache(maxsize=1)
def load_curriculum() -> dict[str, Any]:
    return json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))


def reload_curriculum() -> dict[str, Any]:
    load_curriculum.cache_clear()
    return load_curriculum()


def load_progression() -> dict[str, Any]:
    return json.loads(PROGRESSION_PATH.read_text(encoding="utf-8"))


def write_progression(data: dict[str, Any]) -> None:
    PROGRESSION_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
