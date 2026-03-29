from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db import get_db_session
from .models import LearnerProfile, UserAccount

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)

ACCESS_TOKEN_TTL_MINUTES = 15
JWT_ALGORITHM = "HS256"


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = normalize_email(value)
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email address")
        return normalized


class AuthUserResponse(BaseModel):
    id: str
    email: str
    status: str


class AuthLearnerProfileResponse(BaseModel):
    id: str
    login: str
    track: str
    current_module: str | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: AuthUserResponse
    learner_profile: AuthLearnerProfileResponse | None = None
    profiles: list[AuthLearnerProfileResponse] = Field(default_factory=list)


class AuthMeResponse(BaseModel):
    user: AuthUserResponse
    learner_profile: AuthLearnerProfileResponse | None = None
    profiles: list[AuthLearnerProfileResponse] = Field(default_factory=list)


def get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-secret-change-me")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # type: ignore[no-any-return]


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))  # type: ignore[no-any-return]


def create_access_token(user: UserAccount) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user.id,
        "email": user.email,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)  # type: ignore[no-any-return]


def serialize_user(user: UserAccount) -> AuthUserResponse:
    return AuthUserResponse(id=user.id, email=user.email, status=user.status)


def serialize_learner_profile(learner_profile: LearnerProfile | None) -> AuthLearnerProfileResponse | None:
    if learner_profile is None:
        return None

    return AuthLearnerProfileResponse(
        id=learner_profile.id,
        login=learner_profile.login,
        track=learner_profile.track,
        current_module=learner_profile.current_module,
    )


def serialize_profiles(profiles: list[LearnerProfile]) -> list[AuthLearnerProfileResponse]:
    return [
        AuthLearnerProfileResponse(
            id=profile.id,
            login=profile.login,
            track=profile.track,
            current_module=profile.current_module,
        )
        for profile in profiles
    ]


def build_token_response(user: UserAccount) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=create_access_token(user),
        expires_in=ACCESS_TOKEN_TTL_MINUTES * 60,
        user=serialize_user(user),
        learner_profile=serialize_learner_profile(user.active_profile),
        profiles=serialize_profiles(user.profiles),
    )


def unauthorized(detail: str = "Invalid authentication credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def load_user_with_profiles(
    db: AsyncSession, *, user_id: str | None = None, email: str | None = None
) -> UserAccount | None:
    query = select(UserAccount).options(selectinload(UserAccount.active_profile), selectinload(UserAccount.profiles))
    if user_id is not None:
        query = query.where(UserAccount.id == user_id)
    elif email is not None:
        query = query.where(UserAccount.email == email)
    else:
        raise ValueError("load_user_with_profiles requires user_id or email")

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> UserAccount:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        payload = jwt.decode(credentials.credentials, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise unauthorized() from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise unauthorized()

    user = await load_user_with_profiles(db, user_id=user_id)
    if user is None:
        raise unauthorized()

    return user


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthCredentials,
    db: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    result = await db.execute(select(UserAccount).where(UserAccount.email == payload.email))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = UserAccount(email=payload.email, password_hash=hash_password(payload.password), status="active")
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc

    await db.refresh(user)
    hydrated_user = await load_user_with_profiles(db, user_id=user.id)
    assert hydrated_user is not None
    return build_token_response(hydrated_user)


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: AuthCredentials,
    db: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    user = await load_user_with_profiles(db, email=payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return build_token_response(user)


@router.get("/me", response_model=AuthMeResponse)
async def me(current_user: UserAccount = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(
        user=serialize_user(current_user),
        learner_profile=serialize_learner_profile(current_user.active_profile),
        profiles=serialize_profiles(current_user.profiles),
    )
