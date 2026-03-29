# Develop To Main Synchronization

## Purpose

This repository follows a simple promotion rule:

- feature work lands on `develop`
- `main` moves only by promoting the current `develop`

Issue `#113` operationalizes that rule so the promotion is not just tribal knowledge.

## Recommended Flow

Use the GitHub Actions workflow:

- workflow: `Promote Develop To Main`
- trigger: manual (`workflow_dispatch`)
- optional input: `dry_run`

The workflow:

1. fetches the current `develop` and `main` heads
2. checks whether promotion is actually needed
3. verifies that the current `develop` head has a successful `CI` run
4. creates or reuses an open PR from `develop` to `main`
5. writes a summary with the exact SHAs and CI link

## Why Manual Instead Of Auto-Merge

Promotion to `main` is a release decision, not just a branch sync.

Manual dispatch keeps the release gate explicit while still removing the fragile parts:

- remembering the exact PR base/head
- checking whether `develop` CI passed on the current head
- avoiding duplicate promotion PRs

## Guardrails

The workflow refuses to proceed if:

- there is no completed `CI` run for the current `develop` head
- the `CI` run for the current `develop` head is not `success`

The workflow also does nothing destructive:

- no direct merge into `main`
- no rebase
- no force-push

It only opens or reuses a PR.

## Maintainer Checklist

Before merging the promotion PR:

1. confirm the release scope on `develop`
2. confirm no urgent hotfix is present only on `main`
3. confirm the promotion PR checks are green
4. confirm a maintainer has reviewed the promotion

## Dry Run Mode

Use `dry_run: true` when you want to validate the guardrails without opening a PR.

This is useful when:

- you want to confirm `develop` is release-ready
- you want to inspect SHAs and CI linkage first
- you are preparing a release window but not opening the promotion PR yet

## Manual Fallback

If GitHub Actions is unavailable, the manual fallback is:

```bash
git checkout develop
git pull origin develop
gh pr create --base main --head develop --title "chore: promote develop to main" --body "Manual promotion PR from develop to main."
```

The same guardrails should still be checked manually:

- current `develop` CI is green
- release scope is confirmed
- maintainer review happens before merge
