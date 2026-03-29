from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any
from uuid import uuid4

SQLALCHEMY_READY = False


class _MappedPlaceholder:
    def __class_getitem__(cls, _item: Any) -> Any:
        return Any


class _TypePlaceholder:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


class _FuncPlaceholder:
    @staticmethod
    def now() -> str:
        return "CURRENT_TIMESTAMP"


class _DeclarativeBasePlaceholder:
    metadata: Any = None


def _foreign_key_placeholder(*args: Any, **kwargs: Any) -> Any:
    return None


def _mapped_column_placeholder(*args: Any, **kwargs: Any) -> Any:
    return None


def _relationship_placeholder(*args: Any, **kwargs: Any) -> Any:
    return None


JSON: Any = _TypePlaceholder
DateTime: Any = _TypePlaceholder
Integer: Any = _TypePlaceholder
String: Any = _TypePlaceholder
Text: Any = _TypePlaceholder
UniqueConstraint: Any = _TypePlaceholder
ForeignKey: Any = _foreign_key_placeholder
func: Any = _FuncPlaceholder()
DeclarativeBase: Any = _DeclarativeBasePlaceholder
Mapped: Any = _MappedPlaceholder
mapped_column: Any = _mapped_column_placeholder
relationship: Any = _relationship_placeholder

try:
    sqlalchemy = importlib.import_module("sqlalchemy")
    sqlalchemy_orm = importlib.import_module("sqlalchemy.orm")

    JSON = sqlalchemy.JSON
    DateTime = sqlalchemy.DateTime
    Integer = sqlalchemy.Integer
    String = sqlalchemy.String
    Text = sqlalchemy.Text
    UniqueConstraint = sqlalchemy.UniqueConstraint
    ForeignKey = sqlalchemy.ForeignKey
    func = sqlalchemy.func
    DeclarativeBase = sqlalchemy_orm.DeclarativeBase
    Mapped = sqlalchemy_orm.Mapped
    mapped_column = sqlalchemy_orm.mapped_column
    relationship = sqlalchemy_orm.relationship
    SQLALCHEMY_READY = True
except ModuleNotFoundError:
    pass


class Base(DeclarativeBase):
    """Temporary declarative base for issue #49.

    This module is intentionally self-contained so issue #50 can wire the
    SQLAlchemy engine, session and Alembic metadata later without having to
    redesign the core table shapes first.
    """


def _uuid_str() -> str:
    return str(uuid4())


class LearnerProfile(Base):
    __tablename__ = "learner_profile"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    login: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    track: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    current_module: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_account_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("user_accounts.id"), nullable=True, index=True
    )
    runtime_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user_account: Mapped[UserAccount | None] = relationship(
        foreign_keys="LearnerProfile.user_account_id",
        uselist=False,
        viewonly=True,
    )
    progressions: Mapped[list[Progression]] = relationship(back_populates="learner")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="learner")
    reviews_authored: Mapped[list[Review]] = relationship(back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received: Mapped[list[Review]] = relationship(back_populates="learner", foreign_keys="Review.learner_id")
    defense_sessions: Mapped[list[DefenseSession]] = relationship(back_populates="learner")
    review_attempts_authored: Mapped[list[ReviewAttempt]] = relationship(
        back_populates="reviewer",
        foreign_keys="ReviewAttempt.reviewer_id",
    )
    review_attempts_received: Mapped[list[ReviewAttempt]] = relationship(
        back_populates="learner",
        foreign_keys="ReviewAttempt.learner_id",
    )


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    learner_profile_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("learner_profile.id"), nullable=True, unique=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    learner_profile: Mapped[LearnerProfile | None] = relationship(
        foreign_keys="UserAccount.learner_profile_id",
        uselist=False,
    )
    profiles: Mapped[list[LearnerProfile]] = relationship(
        back_populates="user_account",
        foreign_keys="LearnerProfile.user_account_id",
        viewonly=True,
    )


class Progression(Base):
    __tablename__ = "progression"
    __table_args__ = (UniqueConstraint("learner_id", "module_id", name="uq_progression_learner_module"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    learner_id: Mapped[str] = mapped_column(String(64), ForeignKey("learner_profile.id"), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    learner: Mapped[LearnerProfile] = relationship(back_populates="progressions")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="progression")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    learner_id: Mapped[str] = mapped_column(String(64), ForeignKey("learner_profile.id"), nullable=False, index=True)
    progression_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("progression.id"), nullable=True, index=True
    )
    module_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    checkpoint_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    skill_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    self_evaluation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    learner: Mapped[LearnerProfile] = relationship(back_populates="evidence_items")
    progression: Mapped[Progression | None] = relationship(back_populates="evidence_items")


class Review(Base):
    __tablename__ = "review"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    learner_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("learner_profile.id"), nullable=True, index=True
    )
    reviewer_id: Mapped[str] = mapped_column(String(64), ForeignKey("learner_profile.id"), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    learner: Mapped[LearnerProfile | None] = relationship(back_populates="reviews_received", foreign_keys=[learner_id])
    reviewer: Mapped[LearnerProfile] = relationship(back_populates="reviews_authored", foreign_keys=[reviewer_id])


class DefenseSession(Base):
    __tablename__ = "defense_session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    learner_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("learner_profile.id"), nullable=True, index=True
    )
    module_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    answers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scores: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", index=True)
    evidence_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    learner: Mapped[LearnerProfile | None] = relationship(back_populates="defense_sessions")


class ReviewAttempt(Base):
    __tablename__ = "review_attempt"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    learner_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("learner_profile.id"), nullable=True, index=True
    )
    reviewer_id: Mapped[str] = mapped_column(String(64), ForeignKey("learner_profile.id"), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    learner: Mapped[LearnerProfile | None] = relationship(
        back_populates="review_attempts_received",
        foreign_keys=[learner_id],
    )
    reviewer: Mapped[LearnerProfile] = relationship(
        back_populates="review_attempts_authored",
        foreign_keys=[reviewer_id],
    )


class PedagogicalEvent(Base):
    __tablename__ = "pedagogical_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    learner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    track_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    module_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    checkpoint_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_service: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
