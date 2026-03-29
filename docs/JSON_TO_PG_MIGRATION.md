# JSON to PostgreSQL Migration Path

Status: draft

Related work:
- Issue `#51` - design the initial JSON to PostgreSQL import path
- Issue `#50` - choose and configure SQLAlchemy/SQLModel plus Alembic
- ADR `0004` - JSON-first progression state
- ADR `0005` - API as system of record
- ADR `0007` - PostgreSQL migration strategy

## Purpose

This document defines the initial migration path from the current JSON-backed
state to PostgreSQL.

The design is intentionally narrow:

- `curriculum` remains JSON-backed in v1
- `progression.json` is the first state to migrate
- the import must be idempotent
- the transition must be reversible
- the API must be able to keep using JSON as fallback during rollout

This is a documentation and architecture task. It does not introduce the ORM,
Alembic config or migration files themselves. Those belong to issue `#50`.

## Scope

### In scope

- import learner identity and track context from `progression.json`
- import module progression into PostgreSQL
- import checkpoint submissions already stored in `progression.json`
- validate imported module ids against the curriculum JSON
- keep JSON fallback during the transition period
- define the script shape, import order and rollback strategy

### Out of scope

- moving the curriculum itself to PostgreSQL in v1
- replacing the curriculum JSON as the system of record
- importing AI interaction logs
- changing learner-facing API behavior during the first import

## Current Source of Truth

### Curriculum

The curriculum lives in:

- `packages/curriculum/data/42_lausanne_curriculum.json`

In v1 it stays JSON-backed and read-only from the database point of view.
The import pipeline uses the curriculum only as:

- a validation source for `track_id`, `module_id` and `phase`
- a lookup source for module metadata needed during import

### Progression state

The learner state currently lives in:

- `progression.json`

Today it contains, depending on runtime path and feature usage:

- `learning_plan`
- `progress`
- `module_status`
- `checkpoints`
- legacy shell-first fields such as `mistakes`, `next_command`, `files_created`

Only the application state required by the API should be imported in the first
database migration.

## Design Decision

The first PostgreSQL import should move only the state that already maps cleanly
to existing backend concepts:

- `LearnerProfile`
- `ProgressState`
- `CheckpointRecord`

This keeps the first migration small, auditable and aligned with the current
Pydantic schema names already present in `services/api/app/schemas.py`.

The curriculum is not imported as the truth source in v1. Instead, the import
script reads curriculum JSON at runtime to validate references and derive
missing metadata such as `track_id` and `phase`.

Naming decision:

- use `progress_state` as the logical table name for the initial import path
- do not introduce a separate `module_progress` name if it duplicates `ProgressState`
- keep the SQL naming close to the current Pydantic models to reduce translation layers during the migration

## Target PostgreSQL Schema

The names below are the logical target names for the first migration and should
stay aligned with the backend schema work in issue `#50`.

### 1. `learner_profile`

Logical model aligned to `LearnerProfile`.

Columns:

- `id` `text primary key`
- `login` `text not null`
- `track` `text not null`
- `current_module` `text null`
- `started_at` `timestamptz not null`
- `updated_at` `timestamptz not null`
- `source_json_path` `text not null default 'progression.json'`
- `source_checksum` `text not null`

Notes:

- `id` should be deterministic for the initial import. For the current single-file
  MVP, `default` is acceptable if no stronger identity exists.
- `source_checksum` allows detecting whether the imported JSON content changed.

### 2. `progress_state`

Logical model aligned to `ProgressState`.

Columns:

- `learner_id` `text not null references learner_profile(id)`
- `module_id` `text not null`
- `track_id` `text not null`
- `phase` `text not null`
- `status` `text not null`
- `started_at` `timestamptz not null`
- `completed_at` `timestamptz null`
- `skipped_at` `timestamptz null`
- `skip_reason` `text null`
- `evidence` `jsonb not null default '{}'::jsonb`
- `source_checksum` `text not null`
- `imported_at` `timestamptz not null`

Constraints:

- primary key: `(learner_id, module_id)`
- `status` in `('not_started', 'in_progress', 'completed', 'skipped')`
- `completed_at` required when `status = 'completed'`
- `skipped_at` required when `status = 'skipped'`

Notes:

- `track_id` and `phase` are derived from curriculum JSON, not trusted directly from `progression.json`.
- `evidence` remains flexible as `jsonb` because the current app stores heterogeneous proof structures.

### 3. `checkpoint_record`

Logical model aligned to `CheckpointRecord`.

Columns:

- `id` `bigserial primary key`
- `learner_id` `text not null references learner_profile(id)`
- `module_id` `text not null`
- `checkpoint_index` `integer not null`
- `type` `text not null`
- `prompt` `text not null`
- `evidence` `text not null`
- `self_evaluation` `text not null`
- `submitted_at` `timestamptz not null`
- `source_checksum` `text not null`

Constraints:

- unique key: `(learner_id, module_id, checkpoint_index, submitted_at)`

Notes:

- this table captures imported checkpoint submissions already persisted in JSON
- future evaluated checkpoint fields such as `result`, `reviewer_id` or scoring can be added later without blocking the initial import

### 4. `import_run`

This table is not part of the product domain, but it is required for safe and
auditable migration.

Columns:

- `id` `bigserial primary key`
- `started_at` `timestamptz not null`
- `finished_at` `timestamptz null`
- `source_path` `text not null`
- `source_checksum` `text not null`
- `mode` `text not null`
- `status` `text not null`
- `rows_learner_profile` `integer not null default 0`
- `rows_progress_state` `integer not null default 0`
- `rows_checkpoint_record` `integer not null default 0`
- `error_message` `text null`

Recommended values:

- `mode`: `dry_run`, `upsert`, `replace`
- `status`: `started`, `succeeded`, `failed`, `rolled_back`

## Source Mapping

### A. `learning_plan` to `learner_profile`

`progression.json` source:

- `learning_plan.active_course` -> `learner_profile.track`
- `learning_plan.active_module` -> `learner_profile.current_module`

Imported defaults:

- `id` = `default`
- `login` = `default`
- `started_at` = `session.date_start` if available, else import timestamp
- `updated_at` = import timestamp

Reason:

- the MVP only contains one learner state file
- a deterministic placeholder identity is enough for the initial migration
- stronger learner identity can be introduced later without changing the import shape

### B. `module_status` to `progress_state`

`progression.json` source:

- each key in `module_status` is a `module_id`
- nested values provide `status`, `started_at`, `completed_at`, `skipped_at`, `skip_reason`

Derived from curriculum JSON:

- `track_id`
- `phase`

Imported defaults:

- `evidence` = `{}` unless a future JSON structure carries module-level evidence

### C. `checkpoints` to `checkpoint_record`

`progression.json` source:

- each object in `checkpoints` already resembles `CheckpointRecord`

Validated against curriculum JSON:

- module exists
- checkpoint index exists in module `exit_criteria`
- imported `prompt` matches or is at least compatible with curriculum prompt at that index

## Proposed ETL Script

Recommended script location:

- `services/api/scripts/import_progression_json.py`

This keeps the import logic close to the API repository layer and close to the
future SQLModel/Alembic stack.

### Command-line shape

```bash
python services/api/scripts/import_progression_json.py \
  --source progression.json \
  --mode dry-run
```

```bash
python services/api/scripts/import_progression_json.py \
  --source progression.json \
  --mode upsert
```

Optional flags:

- `--learner-id default`
- `--replace`
- `--fail-on-warning`
- `--json-report /tmp/import-report.json`

### ETL steps

1. Load curriculum JSON.
2. Build a lookup map:
   - `module_id -> track_id`
   - `module_id -> phase`
   - `module_id -> exit_criteria`
3. Load `progression.json`.
4. Compute a SHA-256 checksum of the source file.
5. Create an `import_run` row with status `started`.
6. Validate the source file structurally.
7. Transform source JSON into:
   - one `learner_profile` row
   - zero or more `progress_state` rows
   - zero or more `checkpoint_record` rows
8. Validate transformed rows against database-ready constraints.
9. If `--mode dry-run`, emit a report and mark the run `succeeded`.
10. If `--mode upsert`, write rows in one transaction.
11. Update `import_run` counters and mark the run `succeeded`.
12. If any write fails, roll back the transaction and mark the run `failed`.

## Validation Rules

### Structural validation

These checks run before any database write:

- `progression.json` parses as valid JSON
- `learning_plan` is an object if present
- `module_status` is an object if present
- `checkpoints` is an array if present

### Referential validation

These checks use curriculum JSON:

- every imported `module_id` exists in the curriculum
- every derived `track_id` exists in the curriculum
- every derived `phase` is one of `foundation`, `practice`, `core`, `advanced`
- every checkpoint `checkpoint_index` exists for the target module

### Semantic validation

These checks enforce consistency:

- `completed_at >= started_at` when both exist
- `skipped_at >= started_at` when both exist
- a row with `status = completed` must have `completed_at`
- a row with `status = skipped` must have `skipped_at`
- `self_evaluation` is one of `pass`, `partial`, `fail`
- checkpoint `prompt` should match the current module exit criterion at the same index

### Warning-level validation

These warnings should not necessarily block the import:

- legacy `progress.completed` content that cannot be mapped cleanly to module ids
- missing `session.date_start`
- checkpoint prompt drift where the module still exists and the index is still valid
- empty `module_status` with non-empty `progress.todo` or `progress.in_progress`

## Idempotency Strategy

The import must be safe to run multiple times on the same JSON file.

Recommended strategy:

- compute `source_checksum`
- store it on imported rows and in `import_run`
- use PostgreSQL upserts on natural keys

Upsert keys:

- `learner_profile.id`
- `(learner_id, module_id)` for `progress_state`
- `(learner_id, module_id, checkpoint_index, submitted_at)` for `checkpoint_record`

Behavior:

- identical source file imported twice should produce no duplicate rows
- a changed source file should update mutable rows via upsert
- `--replace` mode may delete previously imported rows for the same learner before reimporting, but only inside one transaction

## Reversibility Strategy

The first migration must remain reversible during the transition period.

This does not mean "generate a perfect JSON clone from PostgreSQL".
It means the product can safely fall back to JSON if the PostgreSQL path is not ready.

### Operational reversibility

- do not delete `progression.json`
- keep current JSON repository code path available
- gate database-backed reads and writes behind a feature flag

Suggested environment flag:

- `PROGRESSION_BACKEND=json|postgres`

Default during transition:

- `json`

### Data rollback

Two rollback modes are sufficient for the initial migration:

1. Runtime rollback:
   - switch `PROGRESSION_BACKEND` back to `json`
   - keep PostgreSQL rows for inspection
2. Data rollback:
   - delete imported rows linked to a specific `source_checksum` or `learner_id`
   - mark the corresponding `import_run` as `rolled_back`

## Import Report

The script should emit a machine-readable report in dry-run and write modes.

Recommended fields:

- `source_path`
- `source_checksum`
- `mode`
- `warnings`
- `errors`
- `learner_profile_rows`
- `progress_state_rows`
- `checkpoint_record_rows`
- `unknown_module_ids`
- `legacy_fields_ignored`

## Transitional Repository Design

To support the rollout cleanly, the API repository layer should expose one
stable contract with two implementations:

- `JsonProgressionRepository`
- `PostgresProgressionRepository`

Common responsibilities:

- load learner profile
- load progression state
- update module status
- append checkpoint submission

This keeps the API as system of record while allowing backend storage to switch
behind a narrow interface.

## Recommended Rollout Sequence

### Phase 1

- issue `#50` introduces SQLModel or SQLAlchemy models and Alembic
- create the target tables without changing runtime behavior

### Phase 2

- add `import_progression_json.py`
- support `dry-run`
- support `upsert`
- validate import on local development data

### Phase 3

- add `PostgresProgressionRepository`
- keep `JsonProgressionRepository` as default
- compare outputs from both backends in tests

### Phase 4

- switch non-destructive read paths behind feature flag
- then switch write paths
- keep JSON fallback until confidence is established

## Open Questions for Backend Implementation

- Should `learner_profile.id` remain `default` for the single-user MVP, or should it derive from a stable hash of source path plus login?
- Should prompt drift in checkpoint imports be warning-only or blocking?
- Should skipped modules be considered valid prerequisites immediately in PostgreSQL, as they are today in JSON-backed logic?
- Do we want one import script per source type later, or a single migration CLI with subcommands?

## Recommended Decisions for Now

- use `default` as initial learner id
- make prompt drift a warning, not a blocker
- preserve current prerequisite semantics where `skipped` unblocks dependent modules
- keep the first import limited to `progression.json` plus curriculum validation lookups
