# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Release workflow with multi-platform validation (Linux, Windows, macOS) and Docker packaging (#232)
- AI mentor chat page with source policy badges and terminal context (#189)
- Tmux session state endpoint and dashboard display (#178)
- Operator runbook for AI gateway (#176)
- Figma-to-code workflow documentation (#214)
- jsx-a11y ESLint plugin and component quality checklist (#213)
- React component convention normalization (#212)
- Oral defense session MVP with timed questions and scoring
- Librarian resource search with source governance tiers
- Reviewer code review with guardrail scrubbing
- Intent classification routing (mentor, librarian, reviewer, examiner)
- Module progression endpoints (start, complete, skip, validate)
- Checkpoint submission and evidence persistence
- Pedagogical event tracking and analytics dashboard
- Authentication with JWT and learner profiles
- Docker Compose setup (dev and production)
- Curriculum data model for shell, C and Python+AI tracks

### Changed
- Integration tests in release workflow now use docker-compose.prod.yml (#244)

### Fixed
- JWT tamper helper now deterministically invalidates tokens in tests
- ESLint peer dependency conflict with eslint-plugin-jsx-a11y on ESLint 10
