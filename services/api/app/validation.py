"""Business validation for module progression (Issue #26).

Validates prerequisites, phase ordering and track enrollment before
allowing a learner to activate a module.
"""

from __future__ import annotations

from typing import Any

# Ordered phases — a module's phase must not precede the latest completed phase
# within the same track without all prior-phase modules being done.
PHASE_ORDER: dict[str, int] = {
    "foundation": 0,
    "practice": 1,
    "core": 2,
    "advanced": 3,
}


def find_module(
    curriculum: dict[str, Any], module_id: str
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return (track, module) for a given module_id, or None."""
    for track in curriculum.get("tracks", []):
        for module in track.get("modules", []):
            if module["id"] == module_id:
                return track, module
    return None


def check_prerequisites(
    curriculum: dict[str, Any],
    module_id: str,
    completed_modules: set[str],
) -> list[str]:
    """Return list of unmet prerequisite module IDs for *module_id*.

    Prerequisites come from the curriculum JSON ``prerequisites`` field.
    A prerequisite is considered met if its ID appears in *completed_modules*.
    """
    result = find_module(curriculum, module_id)
    if result is None:
        return []
    _track, module = result
    prereqs: list[str] = module.get("prerequisites", [])
    return [p for p in prereqs if p not in completed_modules]


def check_phase_ordering(
    curriculum: dict[str, Any],
    module_id: str,
    completed_modules: set[str],
) -> list[str]:
    """Validate that all modules of earlier phases in the same track are done.

    Returns a list of module IDs from earlier phases that are not yet in
    *completed_modules*. An empty list means the phase ordering is satisfied.

    This enforces the rule: foundation before practice before core before
    advanced — within a single track.
    """
    result = find_module(curriculum, module_id)
    if result is None:
        return []
    track, module = result
    target_phase_rank = PHASE_ORDER.get(module.get("phase", ""), 0)

    missing: list[str] = []
    for m in track.get("modules", []):
        m_phase_rank = PHASE_ORDER.get(m.get("phase", ""), 0)
        if m_phase_rank < target_phase_rank and m["id"] not in completed_modules:
            missing.append(m["id"])
    return missing


def check_track_enrollment(
    progression: dict[str, Any],
    module_id: str,
    curriculum: dict[str, Any],
) -> str | None:
    """Verify the learner's active_course matches the track of *module_id*.

    Returns an error message if the learner is not enrolled in the right track,
    or None if enrollment is valid.
    """
    result = find_module(curriculum, module_id)
    if result is None:
        return None
    track, _module = result
    active_course = (
        progression.get("learning_plan", {}).get("active_course", "")
    )
    if active_course != track["id"]:
        return (
            f"Module '{module_id}' belongs to track '{track['id']}', "
            f"but active course is '{active_course}'. "
            f"Switch active_course to '{track['id']}' first."
        )
    return None


def validate_module_activation(
    curriculum: dict[str, Any],
    progression: dict[str, Any],
    module_id: str,
    completed_modules: set[str] | None = None,
) -> list[dict[str, str]]:
    """Run all business validations for activating a module.

    Returns a list of error dicts, each with ``type`` and ``message`` keys.
    An empty list means all validations pass.
    """
    if completed_modules is None:
        completed_modules = set(progression.get("progress", {}).get("completed_modules", []))

    errors: list[dict[str, str]] = []

    # 1. Module must exist
    if find_module(curriculum, module_id) is None:
        errors.append({"type": "not_found", "message": f"Module '{module_id}' not found in curriculum"})
        return errors

    # 2. Track enrollment
    enrollment_err = check_track_enrollment(progression, module_id, curriculum)
    if enrollment_err:
        errors.append({"type": "track_enrollment", "message": enrollment_err})

    # 3. Prerequisites
    missing_prereqs = check_prerequisites(curriculum, module_id, completed_modules)
    if missing_prereqs:
        errors.append({
            "type": "prerequisites",
            "message": f"Missing prerequisites: {', '.join(missing_prereqs)}",
        })

    # 4. Phase ordering
    missing_phases = check_phase_ordering(curriculum, module_id, completed_modules)
    if missing_phases:
        errors.append({
            "type": "phase_ordering",
            "message": f"Earlier-phase modules not completed: {', '.join(missing_phases)}",
        })

    return errors
