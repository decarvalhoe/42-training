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


class AuthMeResponse(BaseModel):
    user: AuthUserResponse
    learner_profile: AuthLearnerProfileResponse | None = None


class AuthSwitchProfileRequest(BaseModel):
    profile_id: str = Field(min_length=1, max_length=64)


class AuthLogoutResponse(BaseModel):
    success: bool = True


def get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-secret-change-me")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")  # type: ignore[no-any-return]


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))  # type: ignore[no-any-return]


def _get_available_profiles(user: UserAccount) -> list[LearnerProfile]:
    return [user.learner_profile] if user.learner_profile is not None else []


def get_active_profile(user: UserAccount) -> LearnerProfile | None:
    active_profile = getattr(user, "active_learner_profile", None)
    if isinstance(active_profile, LearnerProfile):
        return active_profile
    return user.learner_profile  # type: ignore[no-any-return]


def create_access_token(user: UserAccount, active_profile_id: str | None = None) -> str:
    now = datetime.now(UTC)
    resolved_active_profile_id = active_profile_id
    if resolved_active_profile_id is None:
        resolved_active_profile_id = user.learner_profile_id
    payload = {
        "sub": user.id,
        "email": user.email,
        "active_profile_id": resolved_active_profile_id,
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


def build_token_response(user: UserAccount, active_profile: LearnerProfile | None = None) -> AuthTokenResponse:
    resolved_profile = active_profile if active_profile is not None else get_active_profile(user)
    return AuthTokenResponse(
        access_token=create_access_token(user, resolved_profile.id if resolved_profile is not None else None),
        expires_in=ACCESS_TOKEN_TTL_MINUTES * 60,
        user=serialize_user(user),
        learner_profile=serialize_learner_profile(resolved_profile),
    )


def unauthorized(detail: str = "Invalid authentication credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


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

    result = await db.execute(
        select(UserAccount).options(selectinload(UserAccount.learner_profile)).where(UserAccount.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise unauthorized()

    active_profile_id = payload.get("active_profile_id")
    active_profile: LearnerProfile | None = None
    available_profiles = {profile.id: profile for profile in _get_available_profiles(user)}

    if active_profile_id is None:
        active_profile = user.learner_profile
    elif isinstance(active_profile_id, str) and active_profile_id:
        active_profile = available_profiles.get(active_profile_id)
        if active_profile is None:
            raise unauthorized("Active profile is no longer available")
    else:
        raise unauthorized()

    user.active_learner_profile = active_profile  # type: ignore[attr-defined]
    user.active_profile_id = active_profile.id if active_profile is not None else None  # type: ignore[attr-defined]
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
    return build_token_response(user, user.learner_profile)


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: AuthCredentials,
    db: AsyncSession = Depends(get_db_session),
) -> AuthTokenResponse:
    result = await db.execute(
        select(UserAccount).options(selectinload(UserAccount.learner_profile)).where(UserAccount.email == payload.email)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return build_token_response(user, user.learner_profile)


@router.get("/me", response_model=AuthMeResponse)
async def me(current_user: UserAccount = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(
        user=serialize_user(current_user),
        learner_profile=serialize_learner_profile(get_active_profile(current_user)),
    )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh(current_user: UserAccount = Depends(get_current_user)) -> AuthTokenResponse:
    return build_token_response(current_user, get_active_profile(current_user))


@router.post("/switch-profile", response_model=AuthTokenResponse)
async def switch_profile(
    payload: AuthSwitchProfileRequest,
    current_user: UserAccount = Depends(get_current_user),
) -> AuthTokenResponse:
    available_profiles = {profile.id: profile for profile in _get_available_profiles(current_user)}
    next_profile = available_profiles.get(payload.profile_id)
    if next_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not available for this account")

    current_user.active_learner_profile = next_profile  # type: ignore[attr-defined]
    current_user.active_profile_id = next_profile.id  # type: ignore[attr-defined]
    return build_token_response(current_user, next_profile)


@router.post("/logout", response_model=AuthLogoutResponse)
async def logout(_current_user: UserAccount = Depends(get_current_user)) -> AuthLogoutResponse:
    return AuthLogoutResponse()
