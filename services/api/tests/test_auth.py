"""Auth API tests for issue #106."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import JWT_ALGORITHM, create_access_token, get_jwt_secret, hash_password
from app.db import get_db_session
from app.main import app
from app.models import Base, LearnerProfile, UserAccount

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def auth_client(tmp_path: Path) -> Iterator[tuple[TestClient, async_sessionmaker[AsyncSession]]]:
    database_path = tmp_path / "auth.db"
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


async def _get_user_by_email(
    session_factory: async_sessionmaker[AsyncSession],
    email: str,
) -> UserAccount:
    async with session_factory() as session:
        result = await session.execute(select(UserAccount).where(UserAccount.email == email))
        return result.scalar_one()


async def _create_user_with_profile(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "student@example.com",
    password: str = "supersecret",
    profile_id: str = "profile-shell",
    login: str = "student-shell",
    track: str = "shell",
) -> tuple[UserAccount, LearnerProfile]:
    async with session_factory() as session:
        profile = LearnerProfile(
            id=profile_id,
            login=login,
            track=track,
            current_module="shell-basics",
            runtime_state={},
            started_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        user = UserAccount(
            email=email,
            password_hash=hash_password(password),
            status="active",
            learner_profile=profile,
        )
        session.add_all([profile, user])
        await session.commit()
        await session.refresh(user)
        await session.refresh(profile)
        return user, profile


def test_register_creates_user_with_bcrypt_hash(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "Student@Example.com", "password": "supersecret"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    assert data["user"]["email"] == "student@example.com"

    token_payload = jwt.decode(data["access_token"], get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert token_payload["email"] == "student@example.com"
    assert token_payload["sub"] == data["user"]["id"]
    assert token_payload["active_profile_id"] is None

    user = asyncio.run(_get_user_by_email(session_factory, "student@example.com"))
    assert user.password_hash != "supersecret"
    assert user.password_hash.startswith("$2")
    assert user.status == "active"


def test_register_rejects_duplicate_email(auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]]) -> None:
    client, _session_factory = auth_client

    first = client.post("/api/v1/auth/register", json={"email": "student@example.com", "password": "supersecret"})
    duplicate = client.post("/api/v1/auth/register", json={"email": "student@example.com", "password": "supersecret"})

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email already registered"


def test_login_returns_jwt_and_updates_last_login(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    client.post("/api/v1/auth/register", json={"email": "student@example.com", "password": "supersecret"})

    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "supersecret"})

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "student@example.com"
    assert data["access_token"]

    user = asyncio.run(_get_user_by_email(session_factory, "student@example.com"))
    assert user.last_login_at is not None


def test_login_rejects_invalid_password(auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]]) -> None:
    client, _session_factory = auth_client
    client.post("/api/v1/auth/register", json={"email": "student@example.com", "password": "supersecret"})

    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "wrongpass"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_returns_current_user_from_bearer_token(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _session_factory = auth_client
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "supersecret"},
    )
    token = register_response.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": register_response.json()["user"]["id"],
            "email": "student@example.com",
            "status": "active",
        },
        "learner_profile": None,
    }


def test_login_issues_token_bound_to_active_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    _user, profile = asyncio.run(_create_user_with_profile(session_factory))

    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "supersecret"})

    assert response.status_code == 200
    data = response.json()
    token_payload = jwt.decode(data["access_token"], get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert token_payload["active_profile_id"] == profile.id
    assert data["learner_profile"]["id"] == profile.id
    assert data["learner_profile"]["track"] == "shell"


def test_me_uses_active_profile_from_token(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, profile = asyncio.run(_create_user_with_profile(session_factory))
    token = create_access_token(user, profile.id)

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["learner_profile"] == {
        "id": profile.id,
        "login": profile.login,
        "track": profile.track,
        "current_module": "shell-basics",
    }


def test_me_falls_back_to_linked_profile_for_legacy_token(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, profile = asyncio.run(_create_user_with_profile(session_factory))
    now = datetime.now(UTC)
    legacy_token = jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})

    assert response.status_code == 200
    assert response.json()["learner_profile"]["id"] == profile.id


def test_me_rejects_token_with_unavailable_active_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, _profile = asyncio.run(_create_user_with_profile(session_factory))
    token = create_access_token(user, "missing-profile")

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Active profile is no longer available"


def test_refresh_returns_new_token_for_active_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, profile = asyncio.run(_create_user_with_profile(session_factory))
    token = create_access_token(user, profile.id)

    response = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    refreshed_payload = jwt.decode(data["access_token"], get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert refreshed_payload["sub"] == user.id
    assert refreshed_payload["active_profile_id"] == profile.id
    assert data["learner_profile"]["id"] == profile.id


def test_switch_profile_returns_new_token_for_selected_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, profile = asyncio.run(_create_user_with_profile(session_factory))
    token = create_access_token(user)

    response = client.post(
        "/api/v1/auth/switch-profile",
        json={"profile_id": profile.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    switched_payload = jwt.decode(data["access_token"], get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert switched_payload["active_profile_id"] == profile.id
    assert data["learner_profile"]["id"] == profile.id


def test_switch_profile_rejects_unavailable_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, profile = asyncio.run(_create_user_with_profile(session_factory))
    token = create_access_token(user, profile.id)

    response = client.post(
        "/api/v1/auth/switch-profile",
        json={"profile_id": "profile-c"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not available for this account"


def test_logout_requires_auth_and_returns_success(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    user, profile = asyncio.run(_create_user_with_profile(session_factory))
    token = create_access_token(user, profile.id)

    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_me_requires_bearer_token(auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]]) -> None:
    client, _session_factory = auth_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_alembic_upgrade_head_creates_user_accounts_table(tmp_path: Path) -> None:
    db_path = tmp_path / "auth-migration.db"
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert "user_accounts" in table_names

    columns = {column["name"] for column in inspector.get_columns("user_accounts")}
    assert {
        "id",
        "email",
        "password_hash",
        "status",
        "learner_profile_id",
        "last_login_at",
        "created_at",
        "updated_at",
    } <= columns
