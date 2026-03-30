# Release Rollback Procedure

## When to rollback

Trigger a rollback when a released version causes any of:

- **P0**: service outage (health endpoints return non-200, crash loops)
- **P0**: data corruption (progression loss, broken DB migrations)
- **P1**: blocking regression (auth broken, mentor unresponsive, defense sessions fail)
- **P1**: security vulnerability in released code

Do **not** rollback for: UI glitches, non-blocking bugs, performance issues that don't cause outages. Fix forward instead.

## Prerequisites

- `gh` CLI authenticated with write access to `decarvalhoe/42-training`
- Docker with access to `ghcr.io/decarvalhoe/42-training-*` images
- SSH access to deployment target (if self-hosted)

## Procedure

### Step 1 — Identify the bad and good versions

```bash
# List recent tags
git tag --sort=-creatordate | head -10

# List recent releases
gh release list --limit 5

# Identify the broken tag (e.g. v0.2.0) and the last known good (e.g. v0.1.0)
BAD_TAG="v0.2.0"
GOOD_TAG="v0.1.0"
```

### Step 2 — Roll back running services (Docker)

Switch all containers to the last known good image tag.

```bash
# If using docker-compose.prod.yml with image tags:
export IMAGE_TAG="$GOOD_TAG"

# Pull the known-good images
docker pull ghcr.io/decarvalhoe/42-training-api:${GOOD_TAG}
docker pull ghcr.io/decarvalhoe/42-training-ai-gateway:${GOOD_TAG}
docker pull ghcr.io/decarvalhoe/42-training-web:${GOOD_TAG}

# Restart with the good version
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Verify health
curl -sf http://localhost:8000/health
curl -sf http://localhost:8100/health
curl -sf http://localhost:3000/
```

If the deployment uses `latest` tags, retag the good version:

```bash
# Re-tag good version as latest
for svc in api ai-gateway web; do
    docker pull ghcr.io/decarvalhoe/42-training-${svc}:${GOOD_TAG}
    docker tag ghcr.io/decarvalhoe/42-training-${svc}:${GOOD_TAG} \
               ghcr.io/decarvalhoe/42-training-${svc}:latest
    docker push ghcr.io/decarvalhoe/42-training-${svc}:latest
done
```

### Step 3 — Retract the GitHub release

Mark the bad release as a known-bad prerelease so it is no longer the latest.

```bash
# Edit the release: mark as prerelease and add warning
gh release edit "$BAD_TAG" \
    --prerelease \
    --title "${BAD_TAG} [RETRACTED]" \
    --notes "$(cat <<EOF
> **RETRACTED** — This release has been rolled back due to: [describe issue].
> Use ${GOOD_TAG} instead.

$(gh release view "$BAD_TAG" --json body --jq .body)
EOF
)"
```

Do **not** delete the release — it preserves audit trail and prevents tag reuse confusion.

### Step 4 — Revert the git tag (if needed)

Only do this if the tag must be reassigned to a different commit (rare).

```bash
# Delete remote tag
git push origin --delete "$BAD_TAG"

# Delete local tag
git tag -d "$BAD_TAG"

# Optionally re-tag the good commit with a patch version
git tag -a "v0.2.1" "$GOOD_TAG" -m "Rollback: skip ${BAD_TAG}"
git push origin "v0.2.1"
```

**Warning**: Deleting a tag that has published images means the image tag becomes orphaned. Only delete if images have been retracted too.

### Step 5 — Roll back database migrations (if applicable)

If the bad release included Alembic migrations that ran on the production database:

```bash
# Check current migration head
docker exec -it 42-training-api \
    /opt/42-training/services/api/.venv/bin/alembic current

# Downgrade to the last good migration
docker exec -it 42-training-api \
    /opt/42-training/services/api/.venv/bin/alembic downgrade <good_revision>
```

**Before downgrading**: verify the migration has a working `downgrade()` path. If it doesn't, a manual SQL fix is required — do not blindly run downgrade.

### Step 6 — Roll back GHCR images (if needed)

If the bad images must be fully removed from the registry:

```bash
# List image versions
gh api /user/packages/container/42-training-api/versions \
    --jq '.[] | select(.metadata.container.tags[] | contains("'"$BAD_TAG"'")) | .id'

# Delete the specific version (requires packages:delete scope)
VERSION_ID="<id from above>"
gh api --method DELETE /user/packages/container/42-training-api/versions/${VERSION_ID}
```

Repeat for `42-training-ai-gateway` and `42-training-web`.

**Note**: This is destructive and irreversible. Only do this for security incidents where the image itself must not be pullable.

### Step 7 — Communicate the incident

Post on all relevant channels within 15 minutes of the rollback decision.

#### Immediate notification (within 15 min)

```
[INCIDENT] 42-training release ${BAD_TAG} rolled back

Status: services restored to ${GOOD_TAG}
Impact: [describe user-facing impact]
Cause: [one-line root cause or "investigating"]
ETA for fix: [estimate or "TBD"]

Tracking: [link to GitHub issue]
```

#### Post-incident (within 24h)

Create a GitHub issue with label `incident` containing:

```bash
gh issue create \
    --title "Postmortem: ${BAD_TAG} rollback" \
    --label "incident" \
    --body "$(cat <<EOF
## Timeline
- HH:MM — Bad release ${BAD_TAG} deployed
- HH:MM — Issue detected: [how]
- HH:MM — Rollback initiated
- HH:MM — Services restored on ${GOOD_TAG}

## Root cause
[What went wrong and why it wasn't caught by CI]

## Impact
- Duration: X minutes
- Users affected: [scope]
- Data impact: [none / describe]

## Prevention
- [ ] Add test for the specific regression
- [ ] Update CI to catch this class of issue
- [ ] Review release checklist
EOF
)"
```

## Quick reference

| Action | Command |
|--------|---------|
| List releases | `gh release list --limit 10` |
| View release | `gh release view v0.1.0` |
| Retract release | `gh release edit v0.2.0 --prerelease --title "v0.2.0 [RETRACTED]"` |
| Pull good image | `docker pull ghcr.io/decarvalhoe/42-training-api:v0.1.0` |
| Check DB migration | `alembic current` |
| Downgrade DB | `alembic downgrade <revision>` |
| Delete remote tag | `git push origin --delete v0.2.0` |

## Checklist

Use this during an active rollback:

- [ ] Identified bad version and last known good version
- [ ] Containers rolled back to good images
- [ ] Health checks passing on all 3 services
- [ ] GitHub release marked as retracted prerelease
- [ ] Git tag handled (kept or deleted as appropriate)
- [ ] Database migration rolled back (if applicable)
- [ ] GHCR images removed (only if security incident)
- [ ] Incident notification sent (within 15 min)
- [ ] Postmortem issue created (within 24h)
- [ ] Regression test added before next release
