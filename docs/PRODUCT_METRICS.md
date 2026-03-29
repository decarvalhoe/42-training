# Product and Pedagogical Metrics

Status: draft

Related work:
- Issue `#52` - define the first product and pedagogical metrics
- EPIC `#9` - PostgreSQL migration and pedagogical analytics
- Related backend issues: `#49`, `#50`, `#51`

## Purpose

This document defines the first analytics layer for `42-training`.

The goal is not to create vanity dashboards. The goal is to answer a small set
of product and pedagogical questions with data that can later be computed in
PostgreSQL without ad hoc business logic in the frontend.

The first metrics must help answer:

- Are learners making real progress, not just opening the app?
- Which modules or phases create the most friction?
- Is the mentor helping progression, or replacing it?
- Which tracks progress well, and which ones stall?

## Principles

1. Separate product adoption from pedagogical quality.
2. Prefer per-track and per-phase cuts over global averages.
3. Prefer median over mean when duration is skewed.
4. Count meaningful progression events, not page views.
5. Never optimize for mentor volume alone. More mentor traffic can signal learner friction.
6. Keep learner-level analytics private. Product dashboards are for system improvement, not public ranking.

## Metric Families

### Product Metrics

These measure whether the product is usable, sticky and operationally effective.

| Metric | Why it matters | Primary slice |
|---|---|---|
| Weekly active learners with meaningful progress | Distinguishes real usage from passive visits | track, phase |
| Time to first module start | Measures activation friction | track |
| Average and median time per module | Detects pacing and complexity issues | module, track, phase |
| Track completion rate | Measures end-to-end product utility | track |
| Most abandoned modules | Identifies major drop-off points | module, track |
| Mentor questions per completion | Detects dependency or confusion zones | module, track |

### Pedagogical Metrics

These measure whether the learning model is producing mastery rather than shallow throughput.

| Metric | Why it matters | Primary slice |
|---|---|---|
| Checkpoint submission rate | Measures whether learners reach validation moments | module, phase |
| Checkpoint pass rate | Measures whether completion reflects actual mastery | module, track |
| Phase distribution of active learners | Shows whether learners are trapped in foundation or progressing | phase, track |
| Completion after mentor usage | Helps estimate whether mentor support unblocks learning | module, track |
| Evidence volume per completed module | Detects thin completions with weak proof of mastery | module |

## Target Definitions

### 1. Weekly active learners with meaningful progress

Definition:
- Count learners with at least one of these events in the last 7 days:
- module started
- module completed
- checkpoint submitted
- mentor question asked

Reason:
- This is the main top-of-dashboard activity metric.
- It is stronger than login count because it tracks learning work.

### 2. Time to first module start

Definition:
- `first_module_started_at - learner_profile.started_at`

Reason:
- Measures how much friction exists between onboarding and first real action.

### 3. Average and median time per module

Definition:
- For completed modules only:
- `completed_at - started_at`

Reason:
- Mean shows planning impact.
- Median shows the typical learner experience.
- Comparing both reveals skew and outliers.

### 4. Track completion rate

Definition:
- Learners who completed all modules in a track / learners who started at least one module in that track

Reason:
- High-level product success metric by track.

### 5. Most abandoned modules

Definition:
- A module is considered abandoned when:
- status = `skipped`, or
- status = `in_progress` with no update for 14 days, or
- learner leaves the track without completing the module

Reason:
- This is the main friction metric.

### 6. Mentor questions per completion

Definition:
- `mentor_question_count / completed_module_count`

Interpretation:
- A high ratio can be healthy in difficult phases.
- A very high ratio with low completion usually signals unclear instructions, missing resources or weak prerequisite design.

### 7. Checkpoint submission rate

Definition:
- Learners with at least one checkpoint submission in a module / learners who started that module

Reason:
- Tells us whether validation steps are actually being used.

### 8. Checkpoint pass rate

Definition:
- Passed checkpoint submissions / total evaluated checkpoint submissions

Reason:
- Guards against fake completions and weak mastery.

### 9. Phase distribution of active learners

Definition:
- Distribution of active learners and completions across `foundation`, `practice`, `core`, `advanced`

Reason:
- If nearly all activity stays in `foundation`, the curriculum may be too sticky at the bottom.

### 10. Completion after mentor usage

Definition:
- Learners who complete a module within 7 days after at least one mentor interaction in that module / learners who asked the mentor in that module

Reason:
- Measures whether the mentor is unblocking work instead of becoming a dead-end conversation surface.

## Analytics-Ready Data Shape

The MVP still uses JSON for progression, but the queries below assume PostgreSQL.
To support the first dashboard without ad hoc transformations, analytics should
be computed from these relational sources.

### Core tables

`learner_profile`
- `id`
- `login`
- `track`
- `started_at`
- `updated_at`

`module_dim`
- `module_id`
- `track_id`
- `phase`
- `title`
- `prerequisites_count`

`progress_state`
- `learner_id`
- `module_id`
- `track_id`
- `phase`
- `status` (`not_started`, `in_progress`, `completed`, `skipped`)
- `started_at`
- `completed_at`
- `skipped_at`
- `updated_at`

`checkpoint_record`
- `id`
- `learner_id`
- `module_id`
- `checkpoint_index`
- `type`
- `self_evaluation`
- `result` (`pass`, `partial`, `fail`)
- `submitted_at`

`mentor_interaction`
- `id`
- `learner_id`
- `track_id`
- `module_id`
- `phase`
- `created_at`
- `response_status`
- `direct_solution_allowed`

Notes:
- `module_dim` can be materialized from `packages/curriculum/data/42_lausanne_curriculum.json`.
- `mentor_interaction` does not exist yet in the MVP backend. It should be added as a minimal log table before the analytics dashboard is implemented.
- `progress_state.updated_at` is required if we want a defensible definition of stale or abandoned modules.

## PostgreSQL Query Drafts

### A. Average and median time per module

```sql
SELECT
  module_id,
  track_id,
  phase,
  COUNT(*) AS completed_learners,
  AVG(completed_at - started_at) AS avg_time_to_complete,
  PERCENTILE_CONT(0.5) WITHIN GROUP (
    ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at))
  ) * INTERVAL '1 second' AS median_time_to_complete
FROM progress_state
WHERE status = 'completed'
  AND completed_at IS NOT NULL
  AND started_at IS NOT NULL
GROUP BY module_id, track_id, phase
ORDER BY track_id, phase, module_id;
```

### B. Track completion rate

```sql
WITH track_module_count AS (
  SELECT track_id, COUNT(*) AS total_modules
  FROM module_dim
  GROUP BY track_id
),
learner_track_completion AS (
  SELECT
    learner_id,
    track_id,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_modules,
    COUNT(*) FILTER (WHERE status IN ('in_progress', 'completed', 'skipped')) AS touched_modules
  FROM progress_state
  GROUP BY learner_id, track_id
)
SELECT
  ltc.track_id,
  COUNT(*) FILTER (WHERE ltc.touched_modules > 0) AS learners_started_track,
  COUNT(*) FILTER (
    WHERE ltc.completed_modules = tmc.total_modules
  ) AS learners_completed_track,
  ROUND(
    COUNT(*) FILTER (WHERE ltc.completed_modules = tmc.total_modules)::numeric
    / NULLIF(COUNT(*) FILTER (WHERE ltc.touched_modules > 0), 0),
    4
  ) AS track_completion_rate
FROM learner_track_completion ltc
JOIN track_module_count tmc ON tmc.track_id = ltc.track_id
GROUP BY ltc.track_id, tmc.total_modules
ORDER BY ltc.track_id;
```

### C. Most abandoned modules

```sql
SELECT
  ps.module_id,
  ps.track_id,
  ps.phase,
  COUNT(*) FILTER (WHERE ps.status = 'skipped') AS skipped_count,
  COUNT(*) FILTER (
    WHERE ps.status = 'in_progress'
      AND ps.updated_at < NOW() - INTERVAL '14 days'
  ) AS stale_in_progress_count,
  COUNT(*) FILTER (
    WHERE ps.status IN ('skipped', 'in_progress')
      AND ps.updated_at < NOW() - INTERVAL '14 days'
  ) AS abandonment_signal
FROM progress_state ps
GROUP BY ps.module_id, ps.track_id, ps.phase
ORDER BY abandonment_signal DESC, skipped_count DESC, stale_in_progress_count DESC
LIMIT 10;
```

### D. Mentor questions per completion

```sql
WITH mentor_questions AS (
  SELECT
    track_id,
    module_id,
    COUNT(*) AS question_count
  FROM mentor_interaction
  GROUP BY track_id, module_id
),
module_completions AS (
  SELECT
    track_id,
    module_id,
    COUNT(*) AS completion_count
  FROM progress_state
  WHERE status = 'completed'
  GROUP BY track_id, module_id
)
SELECT
  COALESCE(mq.track_id, mc.track_id) AS track_id,
  COALESCE(mq.module_id, mc.module_id) AS module_id,
  COALESCE(mq.question_count, 0) AS question_count,
  COALESCE(mc.completion_count, 0) AS completion_count,
  ROUND(
    COALESCE(mq.question_count, 0)::numeric
    / NULLIF(COALESCE(mc.completion_count, 0), 0),
    2
  ) AS mentor_questions_per_completion
FROM mentor_questions mq
FULL OUTER JOIN module_completions mc
  ON mq.track_id = mc.track_id
 AND mq.module_id = mc.module_id
ORDER BY mentor_questions_per_completion DESC NULLS LAST, question_count DESC;
```

### E. Phase distribution of active learners

```sql
WITH active_learners AS (
  SELECT DISTINCT learner_id, track_id, phase
  FROM progress_state
  WHERE updated_at >= NOW() - INTERVAL '7 days'
)
SELECT
  track_id,
  phase,
  COUNT(*) AS active_learners,
  ROUND(
    COUNT(*)::numeric
    / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY track_id), 0),
    4
  ) AS share_within_track
FROM active_learners
GROUP BY track_id, phase
ORDER BY track_id, phase;
```

### F. Checkpoint pass rate by module

```sql
SELECT
  module_id,
  COUNT(*) AS total_submissions,
  COUNT(*) FILTER (WHERE result = 'pass') AS passed_submissions,
  ROUND(
    COUNT(*) FILTER (WHERE result = 'pass')::numeric / NULLIF(COUNT(*), 0),
    4
  ) AS checkpoint_pass_rate
FROM checkpoint_record
GROUP BY module_id
ORDER BY checkpoint_pass_rate ASC, total_submissions DESC;
```

### G. Weekly active learners with meaningful progress

```sql
WITH activity AS (
  SELECT learner_id, track_id, started_at AS event_at
  FROM progress_state
  WHERE started_at IS NOT NULL

  UNION ALL

  SELECT learner_id, track_id, completed_at AS event_at
  FROM progress_state
  WHERE completed_at IS NOT NULL

  UNION ALL

  SELECT learner_id, NULL::text AS track_id, submitted_at AS event_at
  FROM checkpoint_record
  WHERE submitted_at IS NOT NULL

  UNION ALL

  SELECT learner_id, track_id, created_at AS event_at
  FROM mentor_interaction
  WHERE created_at IS NOT NULL
)
SELECT
  COALESCE(track_id, 'unknown') AS track_id,
  COUNT(DISTINCT learner_id) AS weekly_active_learners
FROM activity
WHERE event_at >= NOW() - INTERVAL '7 days'
GROUP BY COALESCE(track_id, 'unknown')
ORDER BY track_id;
```

## Dashboard Structure

The first analytics dashboard should have three sections.

### 1. Overview

Audience:
- product owner
- maintainer

Cards:
- weekly active learners with meaningful progress
- time to first module start
- track completion rate
- mentor questions per completion

Charts:
- active learners by track
- active learners by phase
- completions by week

### 2. Curriculum Health

Audience:
- product
- curriculum owner

Tables and charts:
- average and median time per module
- modules with highest abandonment signal
- checkpoint submission rate by module
- checkpoint pass rate by module

Primary use:
- identify unclear modules
- detect over-constrained prerequisites
- detect missing resources or weak deliverables

### 3. Mentor Impact

Audience:
- product
- AI owner

Tables and charts:
- mentor questions by module
- mentor questions per completion
- completion after mentor usage
- modules where mentor traffic is high but completions stay low

Primary use:
- identify modules where the mentor compensates for curriculum problems
- identify modules where mentor help actually unblocks progress

## Decision Rules

The metrics should drive action, not passive reporting.

Examples:

- High abandonment + high mentor ratio + low checkpoint pass rate:
  likely curriculum clarity problem or prerequisite problem.
- High mentor ratio + normal completion + normal pass rate:
  difficult but healthy module.
- Low mentor ratio + low completion + low checkpoint submission:
  learners may disengage before asking for help.
- Foundation phase dominates activity for too long:
  onboarding may be too sticky or progression expectations too fuzzy.

## Rollout Plan

### Phase 1 - now

- publish this KPI definition document
- keep the scope intentionally small
- align backend naming with analytics-ready table names

### Phase 2 - with PostgreSQL core tables

- create `module_dim`
- persist `progress_state` with `updated_at`
- persist `checkpoint_record` results
- add `mentor_interaction` logging

### Phase 3 - dashboard implementation

- expose a backend analytics endpoint or SQL-backed admin view
- build a simple internal dashboard before any polished learner-facing analytics
- add threshold-based alerts for abandonment and mentor dependency

## Non-Goals

- public learner ranking
- raw page-view analytics
- AI vanity metrics such as total tokens or total responses without learning context
- premature experimentation platforms before the first dashboard is stable
