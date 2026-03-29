from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import repository
from .models import DefenseSession, Evidence, LearnerProfile, Progression, ReviewAttempt
from .schemas import CheckpointRecord

logger = logging.getLogger(__name__)

_TERMINAL_DEFENSE_STATUSES = {"passed", "failed"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _find_module_track(module_id: str) -> str:
    curriculum = repository.load_curriculum()
    for track in curriculum.get("tracks", []):
        track_id = str(track.get("id", repository.DEFAULT_TRACK))
        for module in track.get("modules", []):
            if module.get("id") == module_id:
                return track_id
    return repository.DEFAULT_TRACK


async def _ensure_learner(
    session: AsyncSession,
    *,
    learner_id: str | None,
    module_id: str,
) -> LearnerProfile:
    resolved_learner_id = learner_id or repository.DEFAULT_LEARNER_ID
    learner = await session.get(LearnerProfile, resolved_learner_id)
    if learner is not None:
        if learner.current_module in (None, ""):
            learner.current_module = module_id
        return learner

    track = _find_module_track(module_id)
    learner = LearnerProfile(
        id=resolved_learner_id,
        login=resolved_learner_id,
        track=track,
        current_module=module_id,
        runtime_state={"learning_plan": {"active_course": track, "active_module": module_id}, "progress": {}},
        started_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(learner)
    await session.flush()
    return learner


async def _find_progression(session: AsyncSession, *, learner_id: str, module_id: str) -> Progression | None:
    result = await session.execute(
        select(Progression).where(Progression.learner_id == learner_id, Progression.module_id == module_id)
    )
    return result.scalar_one_or_none()


async def _create_evidence(
    session: AsyncSession,
    *,
    learner_id: str | None,
    module_id: str,
    evidence_type: str,
    content: str,
    checkpoint_index: int | None = None,
    checkpoint_id: str | None = None,
    self_evaluation: str | None = None,
    description: str | None = None,
    expected_content: str | None = None,
) -> Evidence:
    learner = await _ensure_learner(session, learner_id=learner_id, module_id=module_id)
    progression = await _find_progression(session, learner_id=learner.id, module_id=module_id)

    evidence = Evidence(
        learner_id=learner.id,
        progression_id=progression.id if progression is not None else None,
        module_id=module_id,
        checkpoint_index=checkpoint_index,
        evidence_type=evidence_type,
        checkpoint_id=checkpoint_id,
        self_evaluation=self_evaluation,
        description=description,
        expected_content=expected_content,
        content=content,
    )
    session.add(evidence)
    await session.flush()
    return evidence


def persist_checkpoint_evidence(record: CheckpointRecord) -> str | None:
    async def _persist() -> str:
        async with repository.get_session_factory()() as session:
            evidence = await _create_evidence(
                session,
                learner_id=repository.DEFAULT_LEARNER_ID,
                module_id=record.module_id,
                evidence_type="checkpoint_submission",
                content=record.evidence,
                checkpoint_index=record.checkpoint_index,
                checkpoint_id=f"{record.module_id}:{record.checkpoint_index}",
                self_evaluation=record.self_evaluation,
                description=record.prompt,
                expected_content=record.prompt,
            )
            await session.commit()
            return str(evidence.id)

    try:
        return asyncio.run(_persist())
    except Exception:
        logger.warning("Checkpoint evidence persistence failed", exc_info=True)
        return None


def _append_artifact(
    artifacts: list[dict[str, Any]] | None,
    *,
    artifact_type: str,
    evidence_id: str,
) -> list[dict[str, Any]]:
    updated = list(artifacts or [])
    updated.append({"type": artifact_type, "evidence_id": evidence_id, "generated_by": "api"})
    return updated


async def persist_defense_evidence(session: AsyncSession, defense_session: DefenseSession) -> str | None:
    if defense_session.status not in _TERMINAL_DEFENSE_STATUSES:
        return None

    evidence = await _create_evidence(
        session,
        learner_id=defense_session.learner_id,
        module_id=defense_session.module_id,
        evidence_type="defense_session",
        content=json.dumps(
            {
                "session_id": defense_session.session_id,
                "answers": list(defense_session.answers or []),
                "scores": list(defense_session.scores or []),
                "evidence_artifacts": list(defense_session.evidence_artifacts or []),
            },
            ensure_ascii=True,
            sort_keys=True,
        ),
        self_evaluation="pass" if defense_session.status == "passed" else "fail",
        description=f"Defense session {defense_session.session_id} finished with status {defense_session.status}.",
        expected_content="\n".join(str(question) for question in list(defense_session.questions or [])),
    )
    evidence_id = str(evidence.id)
    defense_session.evidence_artifacts = _append_artifact(
        defense_session.evidence_artifacts,
        artifact_type="defense_summary",
        evidence_id=evidence_id,
    )
    return evidence_id


async def persist_review_evidence(session: AsyncSession, review_attempt: ReviewAttempt) -> str:
    evidence = await _create_evidence(
        session,
        learner_id=review_attempt.learner_id,
        module_id=review_attempt.module_id,
        evidence_type="review_feedback",
        content=review_attempt.code_snippet,
        description=review_attempt.feedback,
        expected_content="\n".join(str(question) for question in list(review_attempt.questions or [])),
    )
    evidence_id = str(evidence.id)
    review_attempt.evidence_artifacts = _append_artifact(
        review_attempt.evidence_artifacts,
        artifact_type="review_feedback",
        evidence_id=evidence_id,
    )
    return evidence_id
