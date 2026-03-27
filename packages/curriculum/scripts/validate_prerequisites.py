#!/usr/bin/env python3
"""Validate the prerequisite graph in 42_lausanne_curriculum.json.

Checks:
1. Every prerequisite reference points to an existing module id.
2. The prerequisite graph is acyclic (no circular dependencies).
3. Every module has a "prerequisites" field (list, may be empty).
"""

import json
import sys
from pathlib import Path

CURRICULUM = Path(__file__).resolve().parent.parent / "data" / "42_lausanne_curriculum.json"


def load_modules(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    modules = []
    for track in data["tracks"]:
        for mod in track["modules"]:
            modules.append(mod)
    return modules


def check_prerequisites_field(modules: list[dict]) -> list[str]:
    errors = []
    for mod in modules:
        if "prerequisites" not in mod:
            errors.append(f"Module '{mod['id']}' is missing the 'prerequisites' field.")
        elif not isinstance(mod["prerequisites"], list):
            errors.append(f"Module '{mod['id']}': prerequisites must be a list.")
    return errors


def check_references(modules: list[dict]) -> list[str]:
    ids = {m["id"] for m in modules}
    errors = []
    for mod in modules:
        for prereq in mod.get("prerequisites", []):
            if prereq not in ids:
                errors.append(f"Module '{mod['id']}' has unknown prerequisite '{prereq}'.")
    return errors


def check_acyclic(modules: list[dict]) -> list[str]:
    """Detect cycles using iterative DFS with three-color marking."""
    adj = {m["id"]: m.get("prerequisites", []) for m in modules}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {mid: WHITE for mid in adj}
    errors = []

    for start in adj:
        if color[start] != WHITE:
            continue
        stack = [(start, False)]
        while stack:
            node, backtrack = stack.pop()
            if backtrack:
                color[node] = BLACK
                continue
            if color[node] == GRAY:
                color[node] = BLACK
                continue
            color[node] = GRAY
            stack.append((node, True))
            for dep in adj[node]:
                if dep not in adj:
                    continue
                if color[dep] == GRAY:
                    errors.append(f"Cycle detected involving '{dep}' (reached from '{node}').")
                elif color[dep] == WHITE:
                    stack.append((dep, False))
    return errors


def main() -> int:
    if not CURRICULUM.exists():
        print(f"ERROR: curriculum file not found at {CURRICULUM}", file=sys.stderr)
        return 1

    modules = load_modules(CURRICULUM)
    errors = []
    errors.extend(check_prerequisites_field(modules))
    errors.extend(check_references(modules))
    errors.extend(check_acyclic(modules))

    if errors:
        print("Prerequisite validation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(modules)} modules validated, prerequisite graph is acyclic.")

    # Print the graph for visibility
    for mod in modules:
        prereqs = mod.get("prerequisites", [])
        label = ", ".join(prereqs) if prereqs else "(entry point)"
        print(f"  {mod['id']} <- {label}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
