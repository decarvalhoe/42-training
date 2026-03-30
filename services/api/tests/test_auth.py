"""Auth API tests for issue #106."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from http.cookies import SimpleCookie
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import AUTH_COOKIE_NAME, JWT_ALGORITHM, get_jwt_secret
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


async def _create_profile_for_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    user_id: str,
    login: str,
    track: str,
    current_module: str | None = None,
    activate: bool = False,
) -> LearnerProfile:
    async with session_factory() as session:
        profile = LearnerProfile(
            login=login,
            track=track,
            current_module=current_module,
            user_account_id=user_id,
            started_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(profile)
        await session.flush()

        if activate:
            user = await session.get(UserAccount, user_id)
            assert user is not None
            user.active_profile_id = profile.id

        await session.commit()
        await session.refresh(profile)
        return profile


def _extract_access_token(response) -> str:
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    morsel = cookie.get(AUTH_COOKIE_NAME)
    assert morsel is not None
    return morsel.value


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
    assert data["user"]["email"] == "student@example.com"
    assert data["profiles"] == []
    assert "access_token" not in data
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None
    assert f"{AUTH_COOKIE_NAME}=" in cookie_header
    assert "httponly" in cookie_header.lower()

    token_payload = jwt.decode(_extract_access_token(response), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert token_payload["email"] == "student@example.com"
    assert token_payload["sub"] == data["user"]["id"]

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
    assert duplicate.json() == {
        "detail": "Email already registered",
        "code": "conflict",
        "status": 409,
    }


def test_login_returns_jwt_and_updates_last_login(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    client.post("/api/v1/auth/register", json={"email": "student@example.com", "password": "supersecret"})

    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "supersecret"})

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "student@example.com"
    assert "access_token" not in data
    assert _extract_access_token(response)

    user = asyncio.run(_get_user_by_email(session_factory, "student@example.com"))
    assert user.last_login_at is not None


def test_login_rejects_invalid_password(auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]]) -> None:
    client, _session_factory = auth_client
    client.post("/api/v1/auth/register", json={"email": "student@example.com", "password": "supersecret"})

    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "wrongpass"})

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
        "code": "unauthorized",
        "status": 401,
    }


def test_me_returns_current_user_from_bearer_token(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _session_factory = auth_client
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "supersecret"},
    )
    token = _extract_access_token(register_response)

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": register_response.json()["user"]["id"],
            "email": "student@example.com",
            "status": "active",
        },
        "learner_profile": None,
        "profiles": [],
    }


def test_me_accepts_session_cookie(auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]]) -> None:
    client, _session_factory = auth_client
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "cookie@example.com", "password": "supersecret"},
    )

    response = client.get("/api/v1/auth/me")

    assert register_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "cookie@example.com"


def test_me_requires_bearer_token(auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]]) -> None:
    client, _session_factory = auth_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid authentication credentials",
        "code": "unauthorized",
        "status": 401,
    }


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


def test_profiles_list_returns_active_profile_and_all_profiles(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "supersecret"},
    )
    token = _extract_access_token(register_response)
    user_id = register_response.json()["user"]["id"]

    active_profile = asyncio.run(
        _create_profile_for_user(
            session_factory,
            user_id=user_id,
            login="student-shell",
            track="shell",
            current_module="shell-basics",
            activate=True,
        )
    )
    asyncio.run(
        _create_profile_for_user(
            session_factory,
            user_id=user_id,
            login="student-c",
            track="c",
        )
    )

    response = client.get("/api/v1/profiles", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["active_profile_id"] == active_profile.id
    assert data["active_profile"]["track"] == "shell"
    assert {profile["track"] for profile in data["profiles"]} == {"shell", "c"}


def test_profiles_create_links_profile_to_current_user_and_activates_it(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _session_factory = auth_client
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "supersecret"},
    )
    token = _extract_access_token(register_response)

    response = client.post(
        "/api/v1/profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={"track": "python_ai"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["active_profile_id"] is not None
    assert data["active_profile"]["track"] == "python_ai"
    assert data["profiles"][0]["login"].startswith("student-python-ai")
    token_payload = jwt.decode(_extract_access_token(response), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert token_payload["profile_id"] == data["active_profile_id"]


def test_profiles_create_rejects_duplicate_track_for_same_user(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "student@example.com", "password": "supersecret"},
    )
    token = _extract_access_token(register_response)
    user_id = register_response.json()["user"]["id"]

    asyncio.run(
        _create_profile_for_user(
            session_factory,
            user_id=user_id,
            login="student-shell",
            track="shell",
            activate=True,
        )
    )

    response = client.post(
        "/api/v1/profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={"track": "shell"},
    )

    assert response.status_code == 409
    assert "already has a profile" in response.json()["detail"]


def test_profiles_switch_changes_active_profile_only_within_user_scope(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_client

    first_user = client.post("/api/v1/auth/register", json={"email": "first@example.com", "password": "supersecret"})
    first_token = _extract_access_token(first_user)
    first_user_id = first_user.json()["user"]["id"]

    shell_profile = asyncio.run(
        _create_profile_for_user(
            session_factory,
            user_id=first_user_id,
            login="first-shell",
            track="shell",
            activate=True,
        )
    )
    c_profile = asyncio.run(
        _create_profile_for_user(
            session_factory,
            user_id=first_user_id,
            login="first-c",
            track="c",
        )
    )

    second_user = client.post("/api/v1/auth/register", json={"email": "second@example.com", "password": "supersecret"})
    second_user_id = second_user.json()["user"]["id"]
    foreign_profile = asyncio.run(
        _create_profile_for_user(
            session_factory,
            user_id=second_user_id,
            login="second-python",
            track="python_ai",
            activate=True,
        )
    )

    switch_response = client.post(
        f"/api/v1/profiles/{c_profile.id}/switch",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert switch_response.status_code == 200
    switched = switch_response.json()
    assert switched["active_profile_id"] == c_profile.id
    assert switched["active_profile"]["track"] == "c"
    assert shell_profile.id != switched["active_profile_id"]
    token_payload = jwt.decode(_extract_access_token(switch_response), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert token_payload["profile_id"] == c_profile.id

    forbidden_response = client.post(
        f"/api/v1/profiles/{foreign_profile.id}/switch",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert forbidden_response.status_code == 404


# ---------------------------------------------------------------------------
# JWT profile-binding tests (issue #127)
# ---------------------------------------------------------------------------


def test_jwt_contains_active_profile_id_after_login(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """Login JWT should embed the active_profile_id when one exists."""
    client, session_factory = auth_client
    reg = client.post("/api/v1/auth/register", json={"email": "jwt@example.com", "password": "supersecret"})
    user_id = reg.json()["user"]["id"]

    asyncio.run(
        _create_profile_for_user(session_factory, user_id=user_id, login="jwt-shell", track="shell", activate=True)
    )

    login_resp = client.post("/api/v1/auth/login", json={"email": "jwt@example.com", "password": "supersecret"})
    assert login_resp.status_code == 200
    token_payload = jwt.decode(_extract_access_token(login_resp), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert "profile_id" in token_payload


def test_jwt_omits_profile_id_when_none_active(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """Register JWT (no profiles yet) should not contain profile_id."""
    client, _session_factory = auth_client
    reg = client.post("/api/v1/auth/register", json={"email": "noprofile@example.com", "password": "supersecret"})
    token_payload = jwt.decode(_extract_access_token(reg), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert "profile_id" not in token_payload


def test_auth_switch_profile_returns_new_jwt_with_profile_id(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """POST /auth/switch-profile should return a new JWT bound to the target profile."""
    client, session_factory = auth_client
    reg = client.post("/api/v1/auth/register", json={"email": "switch@example.com", "password": "supersecret"})
    token = _extract_access_token(reg)
    user_id = reg.json()["user"]["id"]

    asyncio.run(
        _create_profile_for_user(session_factory, user_id=user_id, login="switch-shell", track="shell", activate=True)
    )
    c_profile = asyncio.run(_create_profile_for_user(session_factory, user_id=user_id, login="switch-c", track="c"))

    resp = client.post(
        "/api/v1/auth/switch-profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_id": c_profile.id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["id"] == user_id

    new_payload = jwt.decode(_extract_access_token(resp), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert new_payload["profile_id"] == c_profile.id


def test_auth_switch_profile_rejects_foreign_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """Switching to another user's profile should return 404."""
    client, session_factory = auth_client
    first = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "supersecret"})
    first_token = _extract_access_token(first)

    second = client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "supersecret"})
    second_user_id = second.json()["user"]["id"]
    foreign = asyncio.run(
        _create_profile_for_user(
            session_factory, user_id=second_user_id, login="foreign-shell", track="shell", activate=True
        )
    )

    resp = client.post(
        "/api/v1/auth/switch-profile",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"profile_id": foreign.id},
    )
    assert resp.status_code == 404


def test_auth_refresh_preserves_profile_id(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """POST /auth/refresh should return a new JWT keeping the same profile_id."""
    client, session_factory = auth_client
    reg = client.post("/api/v1/auth/register", json={"email": "refresh@example.com", "password": "supersecret"})
    user_id = reg.json()["user"]["id"]

    profile = asyncio.run(
        _create_profile_for_user(session_factory, user_id=user_id, login="refresh-shell", track="shell", activate=True)
    )

    # Login to get a token with profile_id
    login_resp = client.post("/api/v1/auth/login", json={"email": "refresh@example.com", "password": "supersecret"})
    token = _extract_access_token(login_resp)

    resp = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    new_payload = jwt.decode(_extract_access_token(resp), get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    assert new_payload["profile_id"] == profile.id


def test_me_reflects_jwt_bound_profile(
    auth_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """GET /auth/me should show the profile from the JWT, not necessarily the DB active one."""
    client, session_factory = auth_client
    reg = client.post("/api/v1/auth/register", json={"email": "me-jwt@example.com", "password": "supersecret"})
    user_id = reg.json()["user"]["id"]

    asyncio.run(
        _create_profile_for_user(session_factory, user_id=user_id, login="me-shell", track="shell", activate=True)
    )
    c_profile = asyncio.run(_create_profile_for_user(session_factory, user_id=user_id, login="me-c", track="c"))

    # Switch to C profile via auth endpoint (gets new JWT)
    login_resp = client.post("/api/v1/auth/login", json={"email": "me-jwt@example.com", "password": "supersecret"})
    token = _extract_access_token(login_resp)

    switch_resp = client.post(
        "/api/v1/auth/switch-profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_id": c_profile.id},
    )
    new_token = _extract_access_token(switch_resp)

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["learner_profile"]["id"] == c_profile.id
