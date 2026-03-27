"""Tests for LearnerProfile, ProgressState and ProgressUpdate schemas (Issue #22)."""

import pytest
from pydantic import ValidationError

from app.schemas import LearnerProfile, ProgressState, ProgressUpdate


# -- LearnerProfile ----------------------------------------------------------


class TestLearnerProfile:
    def test_minimal_creation(self) -> None:
        profile = LearnerProfile(username="edecarva")
        assert profile.username == "edecarva"
        assert profile.active_course == "shell"
        assert profile.active_module is None
        assert profile.pace_mode == "normal"
        assert profile.profile == {}

    def test_full_creation(self) -> None:
        profile = LearnerProfile(
            username="jdoe",
            active_course="c",
            active_module="c-pointers",
            pace_mode="intensive",
            profile={"campus": "lausanne"},
        )
        assert profile.active_course == "c"
        assert profile.active_module == "c-pointers"
        assert profile.pace_mode == "intensive"
        assert profile.profile["campus"] == "lausanne"

    def test_invalid_track_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(username="x", active_course="rust")  # type: ignore[arg-type]

    def test_empty_username_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(username="")

    def test_long_username_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(username="a" * 65)


# -- ProgressState ------------------------------------------------------------


class TestProgressState:
    def test_minimal_creation(self) -> None:
        state = ProgressState()
        assert state.current_exercise is None
        assert state.current_step is None
        assert state.completed == []
        assert state.in_progress == []
        assert state.todo == []

    def test_full_creation(self) -> None:
        state = ProgressState(
            current_exercise="shell-basics-ex01",
            current_step="step-3",
            completed=["shell-basics-ex00"],
            in_progress=["shell-basics-ex01"],
            todo=["shell-basics-ex02"],
        )
        assert state.current_exercise == "shell-basics-ex01"
        assert state.completed == ["shell-basics-ex00"]
        assert len(state.in_progress) == 1
        assert len(state.todo) == 1


# -- ProgressUpdate -----------------------------------------------------------


class TestProgressUpdate:
    def test_empty_payload_valid(self) -> None:
        update = ProgressUpdate()
        dump = update.model_dump(exclude_none=True)
        assert dump == {}

    def test_partial_update(self) -> None:
        update = ProgressUpdate(active_course="c", current_step="step-1")
        dump = update.model_dump(exclude_none=True)
        assert dump == {"active_course": "c", "current_step": "step-1"}

    def test_invalid_track_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProgressUpdate(active_course="rust")  # type: ignore[arg-type]

    def test_invalid_pace_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProgressUpdate(pace_mode="turbo")  # type: ignore[arg-type]
