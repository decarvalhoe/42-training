# Figma Sign-off And Visual Regression

This document defines the lightweight parity gate used by `#279` to keep the web app aligned with the canonical Figma reference after the main corrective work has landed.

## Scope

The goal is not pixel-perfection for every screen on every commit. The goal is to make drift visible on the canonical surfaces before merge.

The current baseline covers:

- `/login`
- `/`
- `/dashboard`
- `/defense`
- `/mentor`

These routes represent the auth entry, learner home, skill graph, and the two flagship guided workflows.

## CI Gate

The CI workflow runs a dedicated `web-visual` job:

- installs Playwright Chromium
- starts the web app in deterministic demo mode through the dedicated visual Playwright config
- compares the canonical surfaces against committed baseline screenshots

If the screenshots differ, the job fails and the HTML report is uploaded as an artifact.

The runner uses the webpack dev server path instead of the default dev engine because it is more stable for these deterministic screenshot checks in CI.

## Local Commands

From the repo root:

```bash
npm --prefix apps/web run test:visual
```

To intentionally update baselines after a design-approved change:

```bash
npm --prefix apps/web run test:visual:update
```

Only update snapshots when the new rendering is explicitly validated against the canonical Figma nodes.

The screenshot matcher intentionally allows a tiny rasterization tolerance (`maxDiffPixels: 500`) so font anti-aliasing or other low-signal rendering noise does not hide the real visual regressions.

## PR Requirements

Frontend pull requests must include:

- linked issue
- canonical Figma file and node/page reference
- explicit note that the implementation was compared with Figma
- note that visual baselines were updated only when the design change was intentional

The repository PR template enforces these fields for contributors.

## Design Sign-off Rule

Major UI changes are not considered ready on green functional CI alone.

They require:

1. Figma reference link in the PR
2. visual regression passing or intentionally updated
3. explicit product/design sign-off captured in the issue or PR discussion

## Updating Coverage

Add routes to the visual baseline when:

- a new surface becomes canonical in Figma
- a workflow becomes stable enough that drift should be blocked
- product/design decides a route is release-critical

Avoid adding highly volatile screens unless the data can be made deterministic.
