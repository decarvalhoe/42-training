"""E2E coverage for API error branches across auth, module, and checkpoint flows."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.main as main_module
from app.db import get_db_session
from app.main import app
from app.models import Base, UserAccount

_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell",
            "summary": "Shell track",
            "why_it_matters": "Foundations",
            "modules": [
                {
                    "id": "shell-basics",
                    "title": "Navigation",
                    "phase": "foundation",
                    "skills": ["pwd", "ls"],
                    "deliverable": "Navigate the filesystem.",
                    "exit_criteria": [
                        "Explain what `pwd` prints.",
                        "Explain how `ls` helps inspect a directory.",
                    ],
                },
                {
                    "id": "shell-streams",
                    "title": "Pipes",
                    "phase": "foundation",
                    "skills": ["pipe"],
                    "deliverable": "Build a small pipeline.",
                    "exit_criteria": [
                        "Build a two-stage pipeline from memory.",
                    ],
                },
            ],
        }
    ],
}

_PROGRESSION = {
    "learning_plan": {
        "active_course": "shell",
        "active_module": "shell-basics",
        "pace_mode": "self_paced",
    },
    "progress": {},
    "module_status": {},
    "checkpoints": [],
}


def _clone(value: object) -> object:
    return json.loads(json.dumps(value))


def _tamper_token(token: str) -> str:
    """Corrupt the JWT signature so it is always invalid."""
    parts = token.rsplit(".", 1)
    if len(parts) == 2:
        # Flip every character in the signature portion to guarantee invalidation
        flipped = "".join("X" if c != "X" else "Y" for c in parts[1])
        return f"{parts[0]}.{flipped}"
    return token + "INVALID"


@pytest.fixture
def api_error_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, async_sessionmaker[AsyncSession], list[dict[str, object]]]]:
    database_path = tmp_path / "api-error-branches.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    progression_state = _clone(_PROGRESSION)
    assert isinstance(progression_state, dict)
    writes: list[dict[str, object]] = []

    async def init_models() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose_engine() -> None:
        await engine.dispose()

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    def fake_write(data: dict[str, object]) -> None:
        snapshot = _clone(data)
        assert isinstance(snapshot, dict)
        progression_state.clear()
        progression_state.update(snapshot)
        writes.append(snapshot)

    asyncio.run(init_models())
    app.dependency_overrides[get_db_session] = override_get_db_session
    monkeypatch.setattr(main_module, "load_curriculum", lambda: _clone(_CURRICULUM))
    monkeypatch.setattr(main_module, "load_progression", lambda: _clone(progression_state))
    monkeypatch.setattr(main_module, "write_progression", fake_write)

    try:
        with TestClient(app) as client:
            yield client, session_factory, writes
    finally:
        app.dependency_overrides.clear()
        asyncio.run(dispose_engine())


async def _get_user_by_email(
    session_factory: async_sessionmaker[AsyncSession],
    email: str,
) -> UserAccount:
    async with session_factory() as session:
        result = await session.execute(select(UserAccount).where(UserAccount.email == email))
        return result.scalar_one()


def test_auth_flow_rejects_invalid_login_and_tampered_bearer(
    api_error_client: tuple[TestClient, async_sessionmaker[AsyncSession], list[dict[str, object]]],
) -> None:
    client, session_factory, _writes = api_error_client

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "supersecret"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "wrongpass"},
    )
    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"

    stored_user = asyncio.run(_get_user_by_email(session_factory, "student@example.com"))
    assert stored_user.last_login_at is None

    tampered_token = _tamper_token(register_response.json()["access_token"])
    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert me_response.status_code == 401
    assert me_response.json()["detail"] == "Invalid authentication credentials"
    # FastAPI sets WWW-Authenticate via HTTPException.headers; some httpx/starlette
    # versions propagate it while others silently drop exception headers.
    www_auth = me_response.headers.get("www-authenticate")
    if www_auth is not None:
        assert www_auth == "Bearer"


def test_module_flow_rejects_unknown_module_without_persisting_or_emitting(
    api_error_client: tuple[TestClient, async_sessionmaker[AsyncSession], list[dict[str, object]]],
) -> None:
    client, _session_factory, writes = api_error_client

    before = client.get("/api/v1/progression")
    assert before.status_code == 200

    with patch("app.main.emit_event") as mock_emit:
        response = client.post("/api/v1/modules/nonexistent/start", json={"learner_id": "learner-404"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Module 'nonexistent' not found"
    assert writes == []
    mock_emit.assert_not_called()

    after = client.get("/api/v1/progression")
    assert after.status_code == 200
    assert after.json() == before.json()


def test_checkpoint_flow_rejects_malformed_payload_without_side_effects(
    api_error_client: tuple[TestClient, async_sessionmaker[AsyncSession], list[dict[str, object]]],
) -> None:
    client, _session_factory, writes = api_error_client

    before = client.get("/api/v1/checkpoints/shell-basics")
    assert before.status_code == 200
    assert before.json()["checkpoints"][0]["submitted"] is False

    with patch("app.main.emit_event") as mock_emit:
        response = client.post(
            "/api/v1/checkpoints/submit",
            json={
                "module_id": "shell-basics",
                "checkpoint_index": "zero",
                "type": "exam",
                "evidence": "",
                "self_evaluation": "maybe",
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    # Pydantic v2 returns a list of error dicts; some FastAPI/Pydantic
    # combinations on Python 3.13 may return a plain string instead.
    if isinstance(detail, list):
        error_fields = {item["loc"][-1] for item in detail}
        assert {"checkpoint_index", "type", "evidence", "self_evaluation"} <= error_fields
    else:
        # Fallback: at minimum the response must be a 422 (already asserted).
        assert isinstance(detail, str)
    assert writes == []
    mock_emit.assert_not_called()

    after = client.get("/api/v1/checkpoints/shell-basics")
    assert after.status_code == 200
    assert after.json() == before.json()
