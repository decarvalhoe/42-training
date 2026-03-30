from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from .defense import DefenseQuestion, DefenseSession, compute_session_result
from .terminal_context import TerminalContext

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "http://localhost:8000"
SESSION_STATE_ARTIFACT = "defense_session_state"
SESSION_RESULT_ARTIFACT = "defense_session_result"

MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5


class DefensePersistenceError(RuntimeError):
    """Raised when the API backend cannot persist or restore defense state."""


def _is_transient(exc: Exception) -> bool:
    """Return True for errors worth retrying (5xx, timeouts, connection errors)."""
    if isinstance(exc, httpx.TimeoutException | httpx.ConnectError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


def _retry_request(fn: Any, *args: Any, **kwargs: Any) -> httpx.Response:
    """Execute an httpx call with retry on transient failures."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = fn(*args, **kwargs)
            if response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                logger.warning(
                    "Transient %d from backend (attempt %d/%d), retrying",
                    response.status_code,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(RETRY_BASE_DELAY * (2**attempt))
                continue
            return response
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    "Transient error %s (attempt %d/%d), retrying",
                    type(exc).__name__,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(RETRY_BASE_DELAY * (2**attempt))
            else:
                raise DefensePersistenceError(f"Backend unreachable after {MAX_RETRIES} attempts") from exc
    raise DefensePersistenceError(f"Backend unreachable after {MAX_RETRIES} attempts") from last_exc


def _api_base_url() -> str:
    return os.getenv("AI_GATEWAY_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


def _parse_datetime(value: str | None, fallback: datetime | None = None) -> datetime:
    if value is None:
        return fallback or datetime.now(UTC)
    return datetime.fromisoformat(value)


def _session_status(session: DefenseSession) -> str:
    if not session.completed:
        return "in_progress"
    result = compute_session_result(session)
    return "passed" if result["passed"] else "failed"


def _question_payload(question: DefenseQuestion) -> dict[str, Any]:
    return {
        "id": question.id,
        "text": question.text,
        "skill": question.skill,
        "expected_keywords": question.expected_keywords,
        "answer": question.answer,
        "answered": question.answered,
        "score": question.score,
        "feedback": question.feedback,
        "timed_out": question.timed_out,
        "elapsed_seconds": question.elapsed_seconds,
    }


def _terminal_context_payload(ctx: TerminalContext | None) -> dict[str, Any] | None:
    if ctx is None:
        return None
    return {
        "cwd": ctx.cwd,
        "git_status": ctx.git_status,
        "panes": ctx.panes,
        "git_diff_summary": ctx.git_diff_summary,
    }


def _restore_terminal_context(data: dict[str, Any] | None) -> TerminalContext | None:
    if data is None:
        return None
    return TerminalContext(
        cwd=data.get("cwd", ""),
        git_status=data.get("git_status", ""),
        panes=dict(data.get("panes", {})),
        git_diff_summary=data.get("git_diff_summary", ""),
    )


def _session_state_payload(session: DefenseSession) -> dict[str, Any]:
    return {
        "type": SESSION_STATE_ARTIFACT,
        "source_service": "ai_gateway",
        "track_id": session.track_id,
        "phase": session.phase,
        "learner_id": session.learner_id,
        "reviewer_id": session.reviewer_id,
        "question_time_limit_seconds": session.question_time_limit_seconds,
        "started_at": session.started_at.isoformat(),
        "current_question_started_at": session.current_question_started_at.isoformat(),
        "completed": session.completed,
        "review_attempt_persisted": session.review_attempt_persisted,
        "questions": [_question_payload(question) for question in session.questions],
        "terminal_context": _terminal_context_payload(session.terminal_context),
    }


def _session_result_payload(session: DefenseSession) -> dict[str, Any] | None:
    if not session.completed:
        return None
    result = compute_session_result(session)
    return {
        "type": SESSION_RESULT_ARTIFACT,
        "source_service": "ai_gateway",
        "overall_score": result["overall_score"],
        "passed": result["passed"],
        "summary": result["summary"],
        "timed_out_questions": result["timed_out_questions"],
        "question_results": result["question_results"],
    }


def _defense_session_payload(session: DefenseSession) -> dict[str, Any]:
    evidence_artifacts = [_session_state_payload(session)]
    result_artifact = _session_result_payload(session)
    if result_artifact is not None:
        evidence_artifacts.append(result_artifact)

    return {
        "session_id": session.session_id,
        "learner_id": session.learner_id,
        "module_id": session.module_id,
        "questions": [question.text for question in session.questions],
        "answers": [question.answer for question in session.questions if question.answered],
        "scores": [question.score for question in session.questions if question.answered],
        "status": _session_status(session),
        "evidence_artifacts": evidence_artifacts,
    }


def _defense_session_update_payload(session: DefenseSession) -> dict[str, Any]:
    payload = _defense_session_payload(session)
    payload.pop("session_id")
    return payload


def _find_artifact(payload: dict[str, Any], artifact_type: str) -> dict[str, Any] | None:
    for artifact in payload.get("evidence_artifacts", []):
        if isinstance(artifact, dict) and artifact.get("type") == artifact_type:
            return cast(dict[str, Any], artifact)
    return None


def restore_defense_session(payload: dict[str, Any]) -> DefenseSession:
    state = _find_artifact(payload, SESSION_STATE_ARTIFACT) or {}
    question_payloads = state.get("questions", [])
    questions = [
        DefenseQuestion(
            id=question["id"],
            text=question["text"],
            skill=question["skill"],
            expected_keywords=list(question.get("expected_keywords", [])),
            answer=question.get("answer", ""),
            answered=bool(question.get("answered", False)),
            score=float(question.get("score", 0.0)),
            feedback=question.get("feedback", ""),
            timed_out=bool(question.get("timed_out", False)),
            elapsed_seconds=float(question.get("elapsed_seconds", 0.0)),
        )
        for question in question_payloads
    ]

    status = payload.get("status", "in_progress")
    return DefenseSession(
        session_id=payload["session_id"],
        track_id=state.get("track_id", "shell"),
        module_id=payload["module_id"],
        phase=state.get("phase", "foundation"),
        learner_id=payload.get("learner_id") or state.get("learner_id"),
        reviewer_id=state.get("reviewer_id"),
        questions=questions,
        question_time_limit_seconds=int(state.get("question_time_limit_seconds", 60)),
        started_at=_parse_datetime(state.get("started_at"), _parse_datetime(payload.get("created_at"))),
        current_question_started_at=_parse_datetime(
            state.get("current_question_started_at"),
            _parse_datetime(payload.get("updated_at")),
        ),
        completed=bool(state.get("completed", status in {"passed", "failed"})),
        review_attempt_persisted=bool(state.get("review_attempt_persisted", False)),
        terminal_context=_restore_terminal_context(state.get("terminal_context")),
    )


def create_defense_session(session: DefenseSession) -> dict[str, Any]:
    response = _retry_request(
        httpx.post,
        f"{_api_base_url()}/api/v1/defense-sessions",
        json=_defense_session_payload(session),
        timeout=2.0,
    )
    if response.status_code == 409:
        return sync_defense_session(session, allow_create=False)
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DefensePersistenceError("Failed to create defense session") from exc
    return cast(dict[str, Any], response.json())


def sync_defense_session(session: DefenseSession, *, allow_create: bool = True) -> dict[str, Any]:
    response = _retry_request(
        httpx.put,
        f"{_api_base_url()}/api/v1/defense-sessions/{session.session_id}",
        json=_defense_session_update_payload(session),
        timeout=2.0,
    )
    if response.status_code == 404:
        if not allow_create:
            raise DefensePersistenceError("Defense session create/update race could not be reconciled")
        return create_defense_session(session)
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DefensePersistenceError("Failed to update defense session") from exc
    return cast(dict[str, Any], response.json())


def load_defense_session(session_id: str) -> DefenseSession | None:
    response = _retry_request(
        httpx.get,
        f"{_api_base_url()}/api/v1/defense-sessions/{session_id}",
        timeout=2.0,
    )
    if response.status_code == 404:
        return None
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DefensePersistenceError("Failed to load defense session") from exc
    return restore_defense_session(response.json())


def persist_review_attempt(session: DefenseSession) -> dict[str, Any] | None:
    actor_id = session.reviewer_id or session.learner_id
    if actor_id is None:
        logger.info(
            "Skipping review-attempt persistence for defense session %s without profile context", session.session_id
        )
        return None
    if not session.completed or session.review_attempt_persisted:
        return None

    result = compute_session_result(session)
    transcript_lines: list[str] = []
    for index, question in enumerate(session.questions, start=1):
        transcript_lines.append(f"Q{index}: {question.text}")
        transcript_lines.append(f"A{index}: {question.answer}")

    payload = {
        "learner_id": session.learner_id,
        "reviewer_id": actor_id,
        "module_id": session.module_id,
        "code_snippet": "\n".join(transcript_lines),
        "feedback": result["summary"],
        "questions": [question.text for question in session.questions],
        "score": round(result["overall_score"] * 100),
        "evidence_artifacts": [
            {
                "type": "defense_review_projection",
                "source_service": "ai_gateway",
                "session_id": session.session_id,
                "track_id": session.track_id,
                "phase": session.phase,
                "overall_score": result["overall_score"],
                "passed": result["passed"],
                "timed_out_questions": result["timed_out_questions"],
                "question_results": result["question_results"],
            }
        ],
    }

    response = _retry_request(
        httpx.post,
        f"{_api_base_url()}/api/v1/review-attempts",
        json=payload,
        timeout=2.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DefensePersistenceError("Failed to create review attempt") from exc

    session.review_attempt_persisted = True
    sync_defense_session(session)
    return cast(dict[str, Any], response.json())
