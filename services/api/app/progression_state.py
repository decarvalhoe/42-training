"""Helpers to keep module progression in one canonical representation."""

from __future__ import annotations

from typing import Any

DONE_MODULE_STATUSES = {"completed", "skipped"}


def get_progress_block(progression: dict[str, Any]) -> dict[str, Any]:
    """Return the mutable progress block, normalizing invalid values."""

    progress = progression.setdefault("progress", {})
    if not isinstance(progress, dict):
        progress = {}
        progression["progress"] = progress
    return progress


def get_module_statuses(progression: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return canonical module statuses, backfilling legacy completed_modules."""

    statuses = progression.setdefault("module_status", {})
    if not isinstance(statuses, dict):
        statuses = {}
        progression["module_status"] = statuses

    legacy_completed = get_progress_block(progression).get("completed_modules", [])
    if isinstance(legacy_completed, list):
        for module_id in legacy_completed:
            key = str(module_id)
            if isinstance(statuses.get(key), dict):
                continue
            statuses[key] = {"status": "completed"}

    return statuses  # type: ignore[return-value]


def get_completed_module_ids(progression: dict[str, Any]) -> set[str]:
    """Return modules considered done for gating rules.

    A skipped module is considered done for prerequisite and phase checks.
    """

    statuses = get_module_statuses(progression)
    return {
        module_id
        for module_id, entry in statuses.items()
        if isinstance(entry, dict) and entry.get("status") in DONE_MODULE_STATUSES
    }


def canonicalize_progression(progression: dict[str, Any]) -> dict[str, Any]:
    """Normalize progression so module_status is the only persisted module source."""

    get_module_statuses(progression)
    get_progress_block(progression).pop("completed_modules", None)
    return progression
