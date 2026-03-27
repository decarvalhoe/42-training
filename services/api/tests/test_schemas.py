"""Tests for LearnerProfile and ProgressState schemas (Issue #22)."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.schemas import Checkpoint, LearnerProfile, ProgressState


# -- LearnerProfile ----------------------------------------------------------


class TestLearnerProfile:
    def test_minimal_creation(self) -> None:
        profile = LearnerProfile(username="edecarva")
        assert profile.username == "edecarva"
        assert profile.active_track == "shell"
        assert profile.enrolled_on == date.today()
        assert len(profile.id) == 32  # uuid4 hex

    def test_full_creation(self) -> None:
        profile = LearnerProfile(
            id="abc123",
            username="jdoe",
            active_track="c",
            enrolled_on=date(2026, 3, 1),
        )
        assert profile.id == "abc123"
        assert profile.active_track == "c"
        assert profile.enrolled_on == date(2026, 3, 1)

    def test_invalid_track_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(username="x", active_track="rust")  # type: ignore[arg-type]

    def test_empty_username_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(username="")

    def test_long_username_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(username="a" * 65)


# -- ProgressState ------------------------------------------------------------


class TestProgressState:
    def test_minimal_creation(self) -> None:
        state = ProgressState(learner_id="abc123")
        assert state.learner_id == "abc123"
        assert state.completed_modules == []
        assert state.current_module is None
        assert state.acquired_skills == []
        assert state.validated_checkpoints == []
        assert state.phase == "foundation"

    def test_full_creation(self) -> None:
        cp = Checkpoint(module_id="shell-basics", validated_at=datetime(2026, 3, 15))
        state = ProgressState(
            learner_id="abc123",
            completed_modules=["shell-basics"],
            current_module="shell-permissions",
            acquired_skills=["ls", "cd", "pwd"],
            validated_checkpoints=[cp],
            phase="practice",
        )
        assert state.completed_modules == ["shell-basics"]
        assert state.current_module == "shell-permissions"
        assert len(state.acquired_skills) == 3
        assert state.validated_checkpoints[0].module_id == "shell-basics"
        assert state.phase == "practice"

    def test_invalid_phase_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProgressState(learner_id="x", phase="expert")  # type: ignore[arg-type]

    def test_learner_id_required(self) -> None:
        with pytest.raises(ValidationError):
            ProgressState()  # type: ignore[call-arg]


# -- Checkpoint ---------------------------------------------------------------


class TestCheckpoint:
    def test_creation(self) -> None:
        cp = Checkpoint(module_id="shell-basics", validated_at=datetime(2026, 3, 10, 14, 30))
        assert cp.module_id == "shell-basics"
        assert cp.validated_at.hour == 14
