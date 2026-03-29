from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .auth import get_current_user
from .db import get_db_session
from .models import LearnerProfile, UserAccount
from .repository import load_curriculum
from .schemas import ProfileCreateRequest, ProfileResponse, ProfilesResponse

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def serialize_profile(profile: LearnerProfile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        login=profile.login,
        track=profile.track,
        current_module=profile.current_module,
        started_at=profile.started_at,
        updated_at=profile.updated_at,
    )


def serialize_profiles_response(user: UserAccount) -> ProfilesResponse:
    profiles = sorted(user.profiles, key=lambda profile: (profile.started_at, profile.id))
    profiles_by_id = {profile.id: profile for profile in profiles}
    active_profile = user.active_profile or (
        profiles_by_id.get(user.active_profile_id) if user.active_profile_id is not None else None
    )
    return ProfilesResponse(
        active_profile_id=user.active_profile_id,
        active_profile=serialize_profile(active_profile) if active_profile is not None else None,
        profiles=[serialize_profile(profile) for profile in profiles],
    )


def _valid_track_ids() -> set[str]:
    curriculum = load_curriculum()
    return {str(track["id"]) for track in curriculum.get("tracks", [])}


def _normalize_login(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Profile login is required")
    return normalized[:64]


async def _load_user_with_profiles(db: AsyncSession, user_id: str) -> UserAccount:
    result = await db.execute(
        select(UserAccount)
        .execution_options(populate_existing=True)
        .options(selectinload(UserAccount.active_profile), selectinload(UserAccount.profiles))
        .where(UserAccount.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")
    return user


async def _generate_profile_login(db: AsyncSession, user: UserAccount, track: str) -> str:
    base = _normalize_login(f"{user.email.split('@', 1)[0]}-{track}")
    candidate = base
    suffix = 2

    while True:
        result = await db.execute(select(LearnerProfile.id).where(LearnerProfile.login == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base[: max(1, 64 - len(str(suffix)) - 1)]}-{suffix}"
        suffix += 1


@router.get("", response_model=ProfilesResponse)
async def list_profiles(current_user: UserAccount = Depends(get_current_user)) -> ProfilesResponse:
    return serialize_profiles_response(current_user)


@router.post("", response_model=ProfilesResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfilesResponse:
    if payload.track not in _valid_track_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

    current_user = await _load_user_with_profiles(db, current_user.id)

    duplicate_track = next((profile for profile in current_user.profiles if profile.track == payload.track), None)
    if duplicate_track is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has a profile for track '{payload.track}'",
        )

    login = (
        _normalize_login(payload.login)
        if payload.login is not None
        else await _generate_profile_login(db, current_user, payload.track)
    )
    now = datetime.now(UTC)
    profile = LearnerProfile(
        login=login,
        track=payload.track,
        current_module=payload.current_module,
        user_account_id=current_user.id,
        started_at=now,
        updated_at=now,
    )
    db.add(profile)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile login already exists") from exc

    if current_user.active_profile_id is None or payload.activate:
        current_user.active_profile_id = profile.id

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to create profile") from exc

    user = await _load_user_with_profiles(db, current_user.id)
    return serialize_profiles_response(user)


@router.post("/{profile_id}/switch", response_model=ProfilesResponse)
async def switch_profile(
    profile_id: str,
    current_user: UserAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfilesResponse:
    current_user = await _load_user_with_profiles(db, current_user.id)

    result = await db.execute(
        select(LearnerProfile).where(LearnerProfile.id == profile_id, LearnerProfile.user_account_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    current_user.active_profile_id = profile.id
    await db.commit()

    user = await _load_user_with_profiles(db, current_user.id)
    return serialize_profiles_response(user)
