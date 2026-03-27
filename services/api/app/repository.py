from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
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
