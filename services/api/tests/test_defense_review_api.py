"""API tests for persisted defense sessions and review attempts (Issue #128)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_db_session
from app.main import app
from app.models import Base, Evidence


@pytest.fixture
def persistence_context(tmp_path: Path) -> Iterator[tuple[TestClient, async_sessionmaker[AsyncSession]]]:
    database_path = tmp_path / "defense-review.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def init_models() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose_engine() -> None:
        await engine.dispose()

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    asyncio.run(init_models())
    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        asyncio.run(dispose_engine())


@pytest.fixture
def persistence_client(
    persistence_context: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> TestClient:
    return persistence_context[0]


def test_create_and_get_defense_session(persistence_client: TestClient) -> None:
    response = persistence_client.post(
        "/api/v1/defense-sessions",
        json={
            "session_id": "def-001",
            "learner_id": "learner-1",
            "module_id": "shell-basics",
            "questions": ["What does pwd do?"],
            "answers": ["It prints the current working directory."],
            "scores": [85],
            "status": "in_progress",
            "evidence_artifacts": [{"type": "command_output", "evidence_id": "ev-001"}],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "def-001"
    assert data["evidence_artifacts"] == [{"type": "command_output", "evidence_id": "ev-001"}]
    assert data["created_at"]
    assert data["updated_at"]

    get_response = persistence_client.get("/api/v1/defense-sessions/def-001")
    assert get_response.status_code == 200
    assert get_response.json()["module_id"] == "shell-basics"


def test_list_defense_sessions_can_filter_by_module(persistence_client: TestClient) -> None:
    persistence_client.post(
        "/api/v1/defense-sessions",
        json={
            "session_id": "def-002",
            "module_id": "shell-basics",
            "questions": ["q1"],
            "answers": [],
            "scores": [],
            "status": "scheduled",
            "evidence_artifacts": [],
        },
    )
    persistence_client.post(
        "/api/v1/defense-sessions",
        json={
            "session_id": "def-003",
            "module_id": "c-basics",
            "questions": ["q2"],
            "answers": [],
            "scores": [],
            "status": "scheduled",
            "evidence_artifacts": [],
        },
    )

    response = persistence_client.get("/api/v1/defense-sessions", params={"module_id": "shell-basics"})
    assert response.status_code == 200
    assert [item["session_id"] for item in response.json()] == ["def-002"]


def test_create_and_get_review_attempt(persistence_client: TestClient) -> None:
    response = persistence_client.post(
        "/api/v1/review-attempts",
        json={
            "learner_id": "learner-1",
            "reviewer_id": "reviewer-1",
            "module_id": "shell-basics",
            "code_snippet": "pwd\nls -la",
            "feedback": "Clear command usage and correct output expectations.",
            "questions": ["Why use -la here?"],
            "score": 92,
            "evidence_artifacts": [{"type": "peer_feedback", "source": "pair-review"}],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reviewer_id"] == "reviewer-1"
    assert data["score"] == 92
    assert data["id"]

    attempt_id = data["id"]
    get_response = persistence_client.get(f"/api/v1/review-attempts/{attempt_id}")
    assert get_response.status_code == 200
    assert get_response.json()["feedback"] == "Clear command usage and correct output expectations."


def test_list_review_attempts_can_filter_by_reviewer(persistence_client: TestClient) -> None:
    persistence_client.post(
        "/api/v1/review-attempts",
        json={
            "reviewer_id": "reviewer-a",
            "module_id": "shell-basics",
            "code_snippet": "pwd",
            "feedback": "Strong explanation with the right command.",
            "questions": [],
            "score": 80,
            "evidence_artifacts": [],
        },
    )
    persistence_client.post(
        "/api/v1/review-attempts",
        json={
            "reviewer_id": "reviewer-b",
            "module_id": "shell-basics",
            "code_snippet": "ls",
            "feedback": "Solid attempt with room for deeper explanation.",
            "questions": [],
            "score": 70,
            "evidence_artifacts": [],
        },
    )

    response = persistence_client.get("/api/v1/review-attempts", params={"reviewer_id": "reviewer-a"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["reviewer_id"] == "reviewer-a"


def test_terminal_defense_session_persists_evidence(
    persistence_context: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = persistence_context

    response = client.post(
        "/api/v1/defense-sessions",
        json={
            "session_id": "def-004",
            "learner_id": "learner-defense",
            "module_id": "shell-basics",
            "questions": ["What does pwd do?"],
            "answers": ["It prints the current working directory."],
            "scores": [88],
            "status": "passed",
            "evidence_artifacts": [],
        },
    )

    assert response.status_code == 201
    artifacts = response.json()["evidence_artifacts"]
    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "defense_summary"
    assert artifacts[0]["evidence_id"]

    async def fetch_evidence() -> Evidence:
        async with session_factory() as session:
            result = await session.execute(select(Evidence).where(Evidence.module_id == "shell-basics"))
            evidence_rows = list(result.scalars())
            assert len(evidence_rows) == 1
            return evidence_rows[0]

    evidence = asyncio.run(fetch_evidence())
    assert evidence.learner_id == "learner-defense"
    assert evidence.evidence_type == "defense_session"
    assert evidence.self_evaluation == "pass"
    assert '"session_id": "def-004"' in evidence.content


def test_scheduled_defense_session_does_not_persist_evidence(
    persistence_context: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = persistence_context

    response = client.post(
        "/api/v1/defense-sessions",
        json={
            "session_id": "def-005",
            "learner_id": "learner-defense",
            "module_id": "shell-basics",
            "questions": ["What does pwd do?"],
            "answers": [],
            "scores": [],
            "status": "scheduled",
            "evidence_artifacts": [],
        },
    )

    assert response.status_code == 201
    assert response.json()["evidence_artifacts"] == []

    async def count_evidence() -> int:
        async with session_factory() as session:
            result = await session.execute(select(Evidence))
            return len(list(result.scalars()))

    assert asyncio.run(count_evidence()) == 0


def test_review_attempt_persists_evidence(
    persistence_context: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = persistence_context

    response = client.post(
        "/api/v1/review-attempts",
        json={
            "learner_id": "learner-review",
            "reviewer_id": "reviewer-review",
            "module_id": "shell-basics",
            "code_snippet": "pwd\nls -la",
            "feedback": "Good shell commands and clear intent.",
            "questions": ["Why list hidden files?"],
            "score": 84,
            "evidence_artifacts": [],
        },
    )

    assert response.status_code == 201
    artifacts = response.json()["evidence_artifacts"]
    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "review_feedback"
    assert artifacts[0]["evidence_id"]

    async def fetch_evidence() -> Evidence:
        async with session_factory() as session:
            result = await session.execute(select(Evidence).where(Evidence.learner_id == "learner-review"))
            evidence_rows = list(result.scalars())
            assert len(evidence_rows) == 1
            return evidence_rows[0]

    evidence = asyncio.run(fetch_evidence())
    assert evidence.evidence_type == "review_feedback"
    assert evidence.description == "Good shell commands and clear intent."
    assert evidence.content == "pwd\nls -la"
