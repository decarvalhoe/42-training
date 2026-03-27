#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="${ROOT_DIR}/progression.json"

python3 - "${STATE_FILE}" "$@" <<'PY'
import argparse
import datetime as dt
import json
import os
import pathlib
import sys

state_path = pathlib.Path(sys.argv[1])
cli_args = sys.argv[2:]

parser = argparse.ArgumentParser(
    description="Update progression.json without manual editing."
)
parser.add_argument("--date", help="Session date in YYYY-MM-DD format")
parser.add_argument("--level", type=int, help="Current 42 preparation level")
parser.add_argument("--exercise", help="Current exercise label")
parser.add_argument("--step", help="Current step label")
parser.add_argument("--next-command", help="Next command to run")
parser.add_argument("--current-directory", help="Current working directory to store")
parser.add_argument("--sync-pwd", action="store_true", help="Use the current shell working directory")
parser.add_argument("--add-minutes", type=int, default=0, help="Increment time_spent_minutes")
parser.add_argument("--mark-complete", action="append", default=[], help="Mark an item complete")
parser.add_argument("--set-in-progress", action="append", default=[], help="Replace in_progress with these item(s)")
parser.add_argument("--add-todo", action="append", default=[], help="Append an item to todo")
parser.add_argument("--remove-todo", action="append", default=[], help="Remove an item from todo")
parser.add_argument("--add-file", action="append", default=[], help="Append a created file path")
parser.add_argument("--mistake-command", help="Command associated with a mistake")
parser.add_argument("--mistake-issue", help="What went wrong")
parser.add_argument("--mistake-learned", help="Lesson learned from the mistake")
parser.add_argument("--print", action="store_true", help="Print a short summary after writing")
args = parser.parse_args(cli_args)

if not state_path.exists():
    raise SystemExit(f"State file not found: {state_path}")

data = json.loads(state_path.read_text(encoding="utf-8"))
session = data.setdefault("session", {})
progress = data.setdefault("progress", {})
progress.setdefault("completed", [])
progress.setdefault("in_progress", [])
progress.setdefault("todo", [])
data.setdefault("mistakes", [])
data.setdefault("files_created", [])

def unique(items):
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered

def remove_items(items, to_remove):
    removal = set(to_remove)
    return [item for item in items if item not in removal]

updated = False

if args.level is not None:
    session["level"] = args.level
    updated = True

if args.exercise:
    progress["current_exercise"] = args.exercise
    updated = True

if args.step:
    progress["current_step"] = args.step
    updated = True

if args.next_command:
    data["next_command"] = args.next_command
    updated = True

if args.current_directory and args.sync_pwd:
    raise SystemExit("Use either --current-directory or --sync-pwd, not both")

if args.current_directory:
    data["current_directory"] = args.current_directory
    updated = True
elif args.sync_pwd:
    data["current_directory"] = os.getcwd()
    updated = True

if args.add_minutes:
    session["time_spent_minutes"] = int(session.get("time_spent_minutes", 0)) + args.add_minutes
    updated = True

if args.mark_complete:
    progress["completed"] = unique(progress["completed"] + args.mark_complete)
    progress["in_progress"] = remove_items(progress["in_progress"], args.mark_complete)
    progress["todo"] = remove_items(progress["todo"], args.mark_complete)
    updated = True

if args.set_in_progress:
    progress["in_progress"] = unique(args.set_in_progress)
    progress["todo"] = remove_items(progress["todo"], args.set_in_progress)
    updated = True

if args.add_todo:
    progress["todo"] = unique(progress["todo"] + args.add_todo)
    updated = True

if args.remove_todo:
    progress["todo"] = remove_items(progress["todo"], args.remove_todo)
    updated = True

if args.add_file:
    data["files_created"] = unique(data["files_created"] + args.add_file)
    updated = True

mistake_fields = [args.mistake_command, args.mistake_issue, args.mistake_learned]
if any(mistake_fields):
    if not all(mistake_fields):
      raise SystemExit("Mistake entries require --mistake-command, --mistake-issue and --mistake-learned")
    data["mistakes"].append(
        {
            "command": args.mistake_command,
            "issue": args.mistake_issue,
            "learned": args.mistake_learned,
        }
    )
    updated = True

if args.date:
    session["current_date"] = args.date
    updated = True
elif updated:
    session["current_date"] = dt.date.today().isoformat()

state_path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

if updated or args.print:
    print(f"Updated {state_path}")
    print(f"Current step: {progress.get('current_step', 'unknown')}")
    print(f"Next command: {data.get('next_command', 'unknown')}")
    current_items = progress.get("in_progress", [])
    if current_items:
        print("In progress:")
        for item in current_items:
            print(f"- {item}")
PY
