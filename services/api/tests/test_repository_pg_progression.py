from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.main as main_module
import app.repository as repository
from app.db import create_async_db_engine
from app.main import app
from app.models import Base, LearnerProfile, Progression

client = TestClient(app)

_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell",
            "summary": "Shell track",
            "why_it_matters": "Fundamentals",
            "modules": [
                {
                    "id": "shell-basics",
                    "title": "Basics",
                    "phase": "foundation",
                    "skills": [],
                    "deliverable": "",
                    "exit_criteria": ["Understand pwd"],
                },
                {
                    "id": "shell-streams",
                    "title": "Streams",
                    "phase": "foundation",
                    "skills": [],
                    "deliverable": "",
                    "exit_criteria": ["Build a pipeline"],
                },
            ],
        }
    ],
}


@pytest.fixture
def sqlite_progression_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, object]:
    db_path = tmp_path / "progression.db"
    engine = create_async_db_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())

    monkeypatch.setattr(repository, "get_session_factory", lambda: session_factory)
    monkeypatch.setattr(repository, "load_curriculum", lambda: _CURRICULUM)
    monkeypatch.setattr(main_module, "load_curriculum", lambda: _CURRICULUM)

    yield {"engine": engine, "session_factory": session_factory}

    asyncio.run(engine.dispose())


def test_repository_round_trip_persists_progression(sqlite_progression_repo: dict[str, object]) -> None:
    payload = {
        "learning_plan": {
            "active_course": "shell",
            "active_module": "shell-streams",
            "pace_mode": "intensive",
            "available_courses": ["shell", "c"],
        },
        "progress": {
            "current_exercise": "Ex2",
            "current_step": "2.1",
            "completed": ["pwd"],
            "in_progress": ["pipe"],
            "todo": ["grep"],
        },
        "next_command": "cat file.txt | grep foo",
        "module_status": {
            "shell-basics": {"status": "completed", "completed_at": "2026-03-29T10:00:00+00:00"},
            "shell-streams": {"status": "in_progress", "started_at": "2026-03-29T10:05:00+00:00"},
        },
        "checkpoints": [
            {
                "module_id": "shell-basics",
                "checkpoint_index": 0,
                "type": "exit_criteria",
                "prompt": "Understand pwd",
                "evidence": "pwd => /tmp",
                "self_evaluation": "pass",
                "submitted_at": "2026-03-29T10:01:00+00:00",
            }
        ],
    }

    repository.write_progression(payload)
    loaded = repository.load_progression()

    assert loaded["learning_plan"]["active_course"] == "shell"
    assert loaded["learning_plan"]["active_module"] == "shell-streams"
    assert loaded["learning_plan"]["pace_mode"] == "intensive"
    assert loaded["progress"]["current_exercise"] == "Ex2"
    assert loaded["next_command"] == "cat file.txt | grep foo"
    assert loaded["module_status"]["shell-basics"]["status"] == "completed"
    assert loaded["module_status"]["shell-streams"]["status"] == "in_progress"
    assert loaded["checkpoints"][0]["module_id"] == "shell-basics"
    assert loaded["checkpoints"][0]["evidence"] == "pwd => /tmp"

    session_factory = sqlite_progression_repo["session_factory"]

    async def fetch_rows() -> tuple[LearnerProfile, list[Progression]]:
        async with session_factory() as session:
            learner = await session.get(LearnerProfile, repository.DEFAULT_LEARNER_ID)
            result = await session.execute(select(Progression).order_by(Progression.module_id))
            return learner, list(result.scalars())

    learner, rows = asyncio.run(fetch_rows())
    assert learner is not None
    assert learner.track == "shell"
    assert learner.current_module == "shell-streams"
    assert learner.runtime_state["progress"]["current_step"] == "2.1"
    assert len(rows) == 2
    assert rows[0].module_id == "shell-basics"
    assert rows[0].evidence_summary["checkpoints"][0]["self_evaluation"] == "pass"


def test_repository_write_replaces_removed_module_rows(sqlite_progression_repo: dict[str, object]) -> None:
    repository.write_progression(
        {
            "learning_plan": {"active_course": "shell"},
            "progress": {},
            "module_status": {
                "shell-basics": {"status": "completed", "completed_at": "2026-03-29T10:00:00+00:00"},
                "shell-streams": {"status": "skipped", "skipped_at": "2026-03-29T10:05:00+00:00"},
            },
        }
    )

    repository.write_progression(
        {
            "learning_plan": {"active_course": "shell"},
            "progress": {"current_exercise": "Ex3"},
            "module_status": {"shell-basics": {"status": "completed", "completed_at": "2026-03-29T10:00:00+00:00"}},
        }
    )

    loaded = repository.load_progression()
    assert set(loaded["module_status"].keys()) == {"shell-basics"}
    assert loaded["progress"]["current_exercise"] == "Ex3"

    session_factory = sqlite_progression_repo["session_factory"]

    async def count_rows() -> list[str]:
        async with session_factory() as session:
            result = await session.execute(select(Progression.module_id).order_by(Progression.module_id))
            return list(result.scalars())

    assert asyncio.run(count_rows()) == ["shell-basics"]


def test_api_progression_and_checkpoints_use_database(sqlite_progression_repo: dict[str, object]) -> None:
    response = client.post(
        "/api/v1/progression",
        json={
            "active_course": "shell",
            "active_module": "shell-basics",
            "pace_mode": "normal",
            "current_exercise": "Ex1",
            "current_step": "1.2",
            "next_command": "pwd",
        },
    )
    assert response.status_code == 200
    assert response.json()["learning_plan"]["active_module"] == "shell-basics"

    checkpoint = client.post(
        "/api/v1/checkpoints/submit",
        json={
            "module_id": "shell-basics",
            "checkpoint_index": 0,
            "type": "exit_criteria",
            "evidence": "pwd => /workspace",
            "self_evaluation": "pass",
        },
    )
    assert checkpoint.status_code == 200

    progression = client.get("/api/v1/progression")
    assert progression.status_code == 200
    assert progression.json()["progress"]["current_step"] == "1.2"
    assert progression.json()["next_command"] == "pwd"

    checkpoints = client.get("/api/v1/checkpoints/shell-basics")
    assert checkpoints.status_code == 200
    assert checkpoints.json()["checkpoints"][0]["submitted"] is True
    assert checkpoints.json()["checkpoints"][0]["self_evaluation"] == "pass"
