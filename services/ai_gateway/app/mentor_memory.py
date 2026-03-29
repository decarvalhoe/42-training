from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from fnmatch import fnmatch
from functools import lru_cache
from typing import Protocol, TypedDict

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_TTL_SECONDS = 1800
DEFAULT_MEMORY_MAX_TURNS = 10
_GENERAL_MODULE_ID = "general"


class MentorTurn(TypedDict):
    timestamp: str
    user_question: str
    mentor_observation: str
    mentor_question: str
    mentor_hint: str
    mentor_next_action: str


class ConversationStore(Protocol):
    def get(self, key: str) -> str | bytes | None: ...

    def setex(self, key: str, ttl_seconds: int, value: str) -> object: ...

    def keys(self, pattern: str) -> list[str] | list[bytes]: ...

    def delete(self, *keys: str) -> int: ...


@dataclass
class _InMemoryEntry:
    value: str
    expires_at: datetime


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._entries: dict[str, _InMemoryEntry] = {}

    def _prune(self) -> None:
        now = datetime.now(UTC)
        expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired:
            self._entries.pop(key, None)

    def get(self, key: str) -> str | None:
        self._prune()
        entry = self._entries.get(key)
        return entry.value if entry is not None else None

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self._entries[key] = _InMemoryEntry(
            value=value,
            expires_at=datetime.now(UTC).replace(microsecond=0) + _ttl_delta(ttl_seconds),
        )
        return True

    def keys(self, pattern: str) -> list[str]:
        self._prune()
        return [key for key in self._entries if fnmatch(key, pattern)]

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if self._entries.pop(key, None) is not None:
                deleted += 1
        return deleted


def _ttl_delta(ttl_seconds: int):
    from datetime import timedelta

    return timedelta(seconds=ttl_seconds)


def _memory_ttl_seconds() -> int:
    raw = os.getenv("MENTOR_MEMORY_TTL_SECONDS", str(DEFAULT_MEMORY_TTL_SECONDS))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MEMORY_TTL_SECONDS


def _memory_max_turns() -> int:
    raw = os.getenv("MENTOR_MEMORY_MAX_TURNS", str(DEFAULT_MEMORY_MAX_TURNS))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MEMORY_MAX_TURNS


def _module_key(module_id: str | None) -> str:
    return module_id or _GENERAL_MODULE_ID


def build_memory_key(learner_id: str, module_id: str | None) -> str:
    return f"mentor:conv:{learner_id}:{_module_key(module_id)}"


def _memory_pattern(learner_id: str) -> str:
    return f"mentor:conv:{learner_id}:*"


@lru_cache(maxsize=1)
def _fallback_store() -> InMemoryConversationStore:
    return InMemoryConversationStore()


@lru_cache(maxsize=1)
def get_conversation_store() -> ConversationStore:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis

        return redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        logger.warning("Redis unavailable for mentor memory, using in-memory fallback", exc_info=True)
        return _fallback_store()


def _store_get(key: str) -> str | bytes | None:
    try:
        return get_conversation_store().get(key)
    except Exception:
        logger.warning("Mentor memory read failed, using fallback store", exc_info=True)
        return _fallback_store().get(key)


def _store_set(key: str, value: str) -> None:
    ttl_seconds = _memory_ttl_seconds()
    try:
        get_conversation_store().setex(key, ttl_seconds, value)
        return
    except Exception:
        logger.warning("Mentor memory write failed, using fallback store", exc_info=True)
    _fallback_store().setex(key, ttl_seconds, value)


def _store_keys(pattern: str) -> list[str]:
    try:
        keys = get_conversation_store().keys(pattern)
    except Exception:
        logger.warning("Mentor memory key scan failed, using fallback store", exc_info=True)
        keys = _fallback_store().keys(pattern)

    normalized: list[str] = []
    for key in keys:
        if isinstance(key, bytes):
            normalized.append(key.decode("utf-8"))
        else:
            normalized.append(str(key))
    return normalized


def _store_delete(keys: list[str]) -> int:
    if not keys:
        return 0
    try:
        return int(get_conversation_store().delete(*keys))
    except Exception:
        logger.warning("Mentor memory delete failed, using fallback store", exc_info=True)
        return _fallback_store().delete(*keys)


def load_conversation_history(learner_id: str, module_id: str | None) -> list[MentorTurn]:
    raw = _store_get(build_memory_key(learner_id, module_id))
    if raw in (None, ""):
        return []

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Mentor memory payload invalid JSON, dropping history")
        return []

    if not isinstance(payload, list):
        return []

    history: list[MentorTurn] = []
    for item in payload[-_memory_max_turns() :]:
        if not isinstance(item, dict):
            continue
        required_keys = {
            "timestamp",
            "user_question",
            "mentor_observation",
            "mentor_question",
            "mentor_hint",
            "mentor_next_action",
        }
        if not required_keys <= set(item.keys()):
            continue
        history.append(
            MentorTurn(
                timestamp=str(item["timestamp"]),
                user_question=str(item["user_question"]),
                mentor_observation=str(item["mentor_observation"]),
                mentor_question=str(item["mentor_question"]),
                mentor_hint=str(item["mentor_hint"]),
                mentor_next_action=str(item["mentor_next_action"]),
            )
        )
    return history


def append_conversation_turn(
    learner_id: str,
    module_id: str | None,
    *,
    user_question: str,
    mentor_observation: str,
    mentor_question: str,
    mentor_hint: str,
    mentor_next_action: str,
) -> list[MentorTurn]:
    history = load_conversation_history(learner_id, module_id)
    history.append(
        MentorTurn(
            timestamp=datetime.now(UTC).isoformat(),
            user_question=user_question,
            mentor_observation=mentor_observation,
            mentor_question=mentor_question,
            mentor_hint=mentor_hint,
            mentor_next_action=mentor_next_action,
        )
    )
    trimmed_history = history[-_memory_max_turns() :]
    _store_set(build_memory_key(learner_id, module_id), json.dumps(trimmed_history, ensure_ascii=True))
    return trimmed_history


def clear_conversation_history(learner_id: str) -> int:
    keys = _store_keys(_memory_pattern(learner_id))
    return _store_delete(keys)
