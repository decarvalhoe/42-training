# Auth Design

## Scope

This document prepares issue `#106`:

- user login with account credentials, not raw API keys
- usable from both the web app and the CLI
- compatible with the current modular monolith (`apps/web`, `services/api`, `services/ai_gateway`)
- linked to the learner model introduced by `LearnerProfile`

This design is intentionally staged because `#106` depends on:

- `#49` for the core persistence tables around `learner_profile`
- `#50` for the ORM + migration stack (`SQLAlchemy`/`SQLModel` + `Alembic`)

## Current State On `develop`

As of `develop` head `4ecd46c` on March 29, 2026:

- `services/api` has no auth endpoints
- learner state is still JSON-first for runtime usage
- `apps/web` renders server-side pages and fetches curriculum/progression data without a user session
- `services/ai_gateway` receives learning context (`track`, `module`, `pace_mode`) but no authenticated user identity
- there is no persistent `users` table, refresh-token store, or OAuth account mapping yet

So issue `#106` should not start by wiring UI forms alone. It needs a backend-first auth contract that can survive the move from JSON MVP state to persisted learner data.

## Design Goals

1. Keep `services/api` as the single source of truth for authentication and learner identity.
2. Avoid exposing long-lived secrets or API keys to browser clients.
3. Support both web and CLI without inventing two unrelated auth systems.
4. Link every authenticated user to exactly one learner profile once `#49` lands.
5. Keep `services/ai_gateway` downstream of authenticated context, not the place that authenticates users.

## Proposed Auth Model

Use one auth backend in `services/api`, with two client-facing session modes:

- `web`: cookie-based session, CSRF-protected
- `cli`: short-lived access token + rotating refresh token

Both modes share the same user store, password policy, refresh-session store, and learner-profile link.

### Why Hybrid Instead Of Browser JWT Everywhere

For the web app, cookie sessions are safer and fit the intended backend-owned architecture:

- `httpOnly` avoids token exposure to browser JavaScript
- `SameSite=Lax` or `Strict` reduces cross-site leakage
- CSRF protection is straightforward

For the CLI, cookies are awkward and fragile across shells and scripts. A token pair is a better fit:

- interactive login can return a short-lived access token
- the CLI can rotate a refresh token without keeping a permanent secret
- the server can revoke CLI refresh sessions independently

This keeps the browser off bearer tokens while still giving the CLI an operational login flow.

## Target Data Model

These tables should be added after `#49` and `#50` are merged.

### `user_account`

- `id` UUID PK
- `email` unique, normalized lowercase
- `password_hash`
- `status` (`active`, `pending_verification`, `disabled`)
- `email_verified_at` nullable
- `last_login_at` nullable
- `created_at`
- `updated_at`
- `learner_profile_id` unique FK to `learner_profile.id`

### `oauth_account`

- `id` UUID PK
- `user_id` FK to `user_account.id`
- `provider` (`github`, `google`, later `42` if relevant)
- `provider_user_id`
- `provider_email`
- `created_at`
- unique constraint on (`provider`, `provider_user_id`)

### `auth_session`

- `id` UUID PK
- `user_id` FK to `user_account.id`
- `client_type` (`web`, `cli`)
- `refresh_token_hash`
- `user_agent` nullable
- `ip_address` nullable
- `issued_at`
- `expires_at`
- `revoked_at` nullable
- `replaced_by_session_id` nullable

### `learner_profile`

Issue `#49` currently frames `learner_profile` as the core pedagogical identity. `#106` should not duplicate that concept. The auth layer should link `user_account` 1:1 to `learner_profile`.

That means:

- authentication owns credentials and session state
- learner profile owns pedagogy state and track context

## API Surface

All auth endpoints should live in `services/api`.

### Web/Auth Core

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

### OAuth

- `GET /api/v1/auth/oauth/{provider}/start`
- `GET /api/v1/auth/oauth/{provider}/callback`

### CLI

- `POST /api/v1/auth/cli/login`
- `POST /api/v1/auth/cli/refresh`
- `POST /api/v1/auth/cli/logout`

The CLI endpoints can internally reuse the same service layer as the web endpoints while returning JSON token payloads instead of browser cookies.

## Payloads And Session Artifacts

### Register/Login Request

```json
{
  "email": "student@example.com",
  "password": "plain-text-once-over-tls"
}
```

### `GET /api/v1/auth/me`

```json
{
  "user": {
    "id": "uuid",
    "email": "student@example.com",
    "status": "active"
  },
  "learner_profile": {
    "id": "uuid",
    "login": "student42",
    "track": "shell",
    "current_module": "shell-basics"
  }
}
```

### Web Cookies

- `rbok_session`: short-lived signed session or access token, `httpOnly`, `Secure`
- `rbok_refresh`: rotating refresh session, `httpOnly`, `Secure`
- `rbok_csrf`: readable CSRF cookie for double-submit protection

Even though the repo name is `42-training`, keeping the cookie prefix aligned with the existing RBOK-style naming is acceptable if it is already used elsewhere. If not, rename consistently before implementation.

### CLI Token Response

```json
{
  "access_token": "jwt-or-opaque-token",
  "refresh_token": "opaque-refresh-token",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "student@example.com"
  },
  "learner_profile": {
    "id": "uuid",
    "login": "student42",
    "track": "shell"
  }
}
```

## Security Decisions

### Password Hashing

- prefer `argon2id`
- allow `bcrypt` only if the team wants a smaller dependency surface initially

`argon2id` is the stronger default. If implementation speed wins for MVP, document the fallback explicitly and keep the hash format versioned for later migration.

### Token / Session Lifetimes

- web access/session: 15 minutes
- web refresh: 7 days, rotating
- CLI access: 15 minutes
- CLI refresh: 30 days, rotating

Every refresh should revoke the previous refresh record and issue a new one.

### CSRF

Required for cookie-authenticated web writes:

- `rbok_csrf` cookie
- matching `x-csrf-token` header

CLI token endpoints do not need CSRF because they are not cookie-authenticated browser requests.

### Basic Hardening

- login rate limit per IP and per email
- constant-shape error responses for bad credentials
- audit log for login success/failure and refresh revocation
- `Secure` cookies outside local dev
- no password hashes or refresh tokens in logs

## Web Flow

### Login

1. User submits email/password from a future `/login` page in `apps/web`.
2. `apps/web` calls `POST /api/v1/auth/login`.
3. `services/api` validates credentials and loads the linked `learner_profile`.
4. API sets `rbok_session`, `rbok_refresh`, and `rbok_csrf`.
5. Web redirects to dashboard and uses `GET /api/v1/auth/me` for authenticated shell chrome.

### Authenticated Requests

For browser calls:

- the browser automatically sends cookies
- mutating requests include `x-csrf-token`
- server components should prefer `GET /api/v1/auth/me` to derive the current learner

### Logout

1. Browser posts to `POST /api/v1/auth/logout`.
2. API revokes the refresh session.
3. API clears cookies.
4. Web redirects to public landing page or login page.

## CLI Flow

The CLI should use an interactive account login, not a pasted API key.

### Recommended MVP

1. `42t login`
2. prompt for email
3. prompt for password without echo
4. call `POST /api/v1/auth/cli/login`
5. store refresh token in OS keychain if available, otherwise a local file with strict permissions
6. use short-lived access token for subsequent API calls

### Refresh

1. access token expires
2. CLI calls `POST /api/v1/auth/cli/refresh`
3. API rotates the refresh session
4. CLI updates local secure storage

This is simpler than a full device-code flow and fits the issue scope. If OAuth for CLI is later required, add browser-assisted login as a second mode rather than the first implementation.

## AI Gateway Integration

The AI gateway should not authenticate end users directly.

Preferred flow:

1. web or CLI authenticates against `services/api`
2. client calls an API endpoint for mentor interaction
3. API resolves authenticated user + learner profile
4. API forwards a trusted internal payload to `services/ai_gateway`

The forwarded context should include:

- `user_id`
- `learner_profile_id`
- `login`
- `active_course`
- `pace_mode`
- `module_id`

This avoids direct public auth logic inside `services/ai_gateway` and keeps user identity anchored in the system of record.

If direct client-to-`ai_gateway` calls remain during transition, they should be considered temporary and protected by an internal verification mechanism, not treated as the final architecture.

## Implementation Sequence

### Phase 0: This Document

- agree on auth mode
- agree on table split between `user_account` and `learner_profile`
- agree on web vs CLI session behavior

### Phase 1: Persistence Prerequisites

Blocked on:

- `#49` learner tables
- `#50` ORM + Alembic

Deliverables:

- migrations for `user_account`, `oauth_account`, `auth_session`
- repository/service abstraction for loading current user and learner profile

### Phase 2: Password Auth In API

- register/login/logout/refresh/me endpoints
- password hashing
- cookie handling
- CLI token handling
- unit and API tests

### Phase 3: Web Integration

- login page
- auth-aware nav state
- protected pages or server-side redirects
- CSRF header plumbing for mutations

### Phase 4: AI Gateway Integration

- authenticated mentor request path via API
- user context propagation
- regression tests showing the mentor receives the connected learner context

### Phase 5: OAuth

- provider selection
- callback handling
- account linking rules

OAuth should remain optional until local account auth is stable.

## Open Questions

1. Should `login` in `LearnerProfile` remain a 42-style display identifier while email lives only in `user_account`? Recommended: yes.
2. Should unverified email users be blocked from login, or allowed with limited actions? Recommended MVP: allow login, block sensitive future actions if needed.
3. Should the CLI store refresh tokens in keychain only, or permit a local fallback file? Recommended MVP: keychain first, file fallback with `0600`.
4. Should the browser call `services/ai_gateway` directly at all after auth lands? Recommended: no, route mentor traffic through `services/api`.

## Recommended Next Step After `#49` And `#50`

Implement the backend auth service first:

- models
- migrations
- `/api/v1/auth/*`
- tests

Only after that should the login UI and CLI UX be wired.
