"""Tests for Pydantic schemas (Issues #22, #36)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas import (
    Checkpoint,
    DefenseSession,
    LearnerProfile,
    ProgressState,
    ProgressUpdate,
    Review,
)

# -- LearnerProfile ----------------------------------------------------------


class TestLearnerProfile:
    def test_minimal_creation(self) -> None:
        started_at = datetime(2026, 3, 27, 8, 30, tzinfo=UTC)
        updated_at = datetime(2026, 3, 27, 9, 45, tzinfo=UTC)
        profile = LearnerProfile(
            id="learner-001",
            login="edecarva",
            track="shell",
            started_at=started_at,
            updated_at=updated_at,
        )
        assert profile.id == "learner-001"
        assert profile.login == "edecarva"
        assert profile.track == "shell"
        assert profile.current_module is None
        assert profile.started_at == started_at
        assert profile.updated_at == updated_at

    def test_full_creation(self) -> None:
        profile = LearnerProfile(
            id="learner-002",
            login="jdoe",
            track="c",
            current_module="c-pointers",
            started_at="2026-03-27T08:30:00Z",
            updated_at="2026-03-28T10:15:00Z",
        )
        assert profile.track == "c"
        assert profile.current_module == "c-pointers"
        assert profile.started_at == datetime(2026, 3, 27, 8, 30, tzinfo=UTC)
        assert profile.updated_at == datetime(2026, 3, 28, 10, 15, tzinfo=UTC)

    def test_invalid_track_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(
                id="learner-003",
                login="x",
                track="rust",  # type: ignore[arg-type]
                started_at="2026-03-27T08:30:00Z",
                updated_at="2026-03-27T08:45:00Z",
            )

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(
                id="",
                login="edecarva",
                track="shell",
                started_at="2026-03-27T08:30:00Z",
                updated_at="2026-03-27T08:45:00Z",
            )

    def test_long_login_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LearnerProfile(
                id="learner-004",
                login="a" * 65,
                track="shell",
                started_at="2026-03-27T08:30:00Z",
                updated_at="2026-03-27T08:45:00Z",
            )


# -- ProgressState ------------------------------------------------------------


class TestProgressState:
    def test_minimal_creation(self) -> None:
        started_at = datetime(2026, 3, 27, 8, 30, tzinfo=UTC)
        state = ProgressState(
            module_id="shell-basics",
            status="in_progress",
            started_at=started_at,
        )
        assert state.module_id == "shell-basics"
        assert state.status == "in_progress"
        assert state.started_at == started_at
        assert state.completed_at is None
        assert state.evidence == {}

    def test_full_creation(self) -> None:
        state = ProgressState(
            module_id="shell-basics",
            status="completed",
            started_at="2026-03-27T08:30:00Z",
            completed_at="2026-03-27T09:00:00Z",
            evidence={"checkpoint": "passed", "notes": "Command sequence reproduced"},
        )
        assert state.module_id == "shell-basics"
        assert state.status == "completed"
        assert state.completed_at == datetime(2026, 3, 27, 9, 0, tzinfo=UTC)
        assert state.evidence["checkpoint"] == "passed"

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProgressState(
                module_id="shell-basics",
                status="blocked",  # type: ignore[arg-type]
                started_at="2026-03-27T08:30:00Z",
            )

    def test_empty_module_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProgressState(
                module_id="",
                status="not_started",
                started_at="2026-03-27T08:30:00Z",
            )


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


# -- Checkpoint (Issue #36) ---------------------------------------------------


class TestCheckpoint:
    def test_minimal_creation(self) -> None:
        cp = Checkpoint(
            module_id="shell-basics",
            type="exit_criteria",
            prompt="Navigate to /tmp without errors",
            success_criteria=["cd /tmp succeeds"],
        )
        assert cp.module_id == "shell-basics"
        assert cp.type == "exit_criteria"
        assert cp.evidence == ""
        assert len(cp.success_criteria) == 1

    def test_full_creation(self) -> None:
        cp = Checkpoint(
            module_id="c-memory",
            type="deliverable",
            prompt="Explain malloc vs calloc",
            success_criteria=["mentions zeroing", "mentions size argument"],
            evidence="malloc allocates uninitialized memory, calloc zeros it.",
        )
        assert cp.type == "deliverable"
        assert len(cp.success_criteria) == 2
        assert "calloc" in cp.evidence

    def test_all_checkpoint_types(self) -> None:
        for t in ("exit_criteria", "deliverable", "skill_check"):
            cp = Checkpoint(
                module_id="m",
                type=t,
                prompt="test",
                success_criteria=["ok"],  # type: ignore[arg-type]
            )
            assert cp.type == t

    def test_invalid_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Checkpoint(
                module_id="m",
                type="exam",  # type: ignore[arg-type]
                prompt="test",
                success_criteria=["ok"],
            )

    def test_empty_module_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Checkpoint(
                module_id="",
                type="exit_criteria",
                prompt="test",
                success_criteria=["ok"],
            )

    def test_empty_success_criteria_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Checkpoint(
                module_id="m",
                type="exit_criteria",
                prompt="test",
                success_criteria=[],
            )

    def test_short_prompt_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Checkpoint(
                module_id="m",
                type="exit_criteria",
                prompt="ab",
                success_criteria=["ok"],
            )


# -- Review (Issue #36) -------------------------------------------------------


class TestReview:
    def test_minimal_creation(self) -> None:
        r = Review(
            reviewer_id="peer42",
            module_id="shell-streams",
            code_snippet="cat file.txt | grep hello",
            feedback="Good use of pipe but could use -i flag.",
        )
        assert r.reviewer_id == "peer42"
        assert r.questions == []
        assert r.score is None

    def test_full_creation(self) -> None:
        r = Review(
            reviewer_id="examiner",
            module_id="c-basics",
            code_snippet="int main() { return 0; }",
            feedback="Clean but lacks error handling.",
            questions=["What if argc > 1?", "Why return 0?"],
            score=75,
        )
        assert len(r.questions) == 2
        assert r.score == 75

    def test_score_boundaries(self) -> None:
        r_zero = Review(reviewer_id="r", module_id="m", code_snippet="x", feedback="ok!", score=0)
        assert r_zero.score == 0
        r_max = Review(reviewer_id="r", module_id="m", code_snippet="x", feedback="ok!", score=100)
        assert r_max.score == 100

    def test_score_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Review(reviewer_id="r", module_id="m", code_snippet="x", feedback="ok", score=-1)

    def test_score_above_100_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Review(reviewer_id="r", module_id="m", code_snippet="x", feedback="ok", score=101)

    def test_empty_reviewer_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Review(reviewer_id="", module_id="m", code_snippet="x", feedback="ok")

    def test_empty_code_snippet_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Review(reviewer_id="r", module_id="m", code_snippet="", feedback="ok")

    def test_short_feedback_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Review(reviewer_id="r", module_id="m", code_snippet="x", feedback="ab")


# -- DefenseSession (Issue #36) -----------------------------------------------


class TestDefenseSession:
    def test_minimal_creation(self) -> None:
        ds = DefenseSession(
            session_id="def-001",
            module_id="shell-basics",
            questions=["What does cd do?"],
        )
        assert ds.session_id == "def-001"
        assert ds.status == "scheduled"
        assert ds.answers == []
        assert ds.scores == []

    def test_full_creation(self) -> None:
        ds = DefenseSession(
            session_id="def-002",
            module_id="c-memory",
            questions=["Explain malloc", "What is a dangling pointer?"],
            answers=["malloc allocates heap memory", "A pointer to freed memory"],
            scores=[90, 85],
            status="passed",
        )
        assert len(ds.questions) == 2
        assert len(ds.answers) == 2
        assert len(ds.scores) == 2
        assert ds.status == "passed"

    def test_all_statuses(self) -> None:
        for s in ("scheduled", "in_progress", "passed", "failed"):
            ds = DefenseSession(
                session_id="s",
                module_id="m",
                questions=["q"],
                status=s,  # type: ignore[arg-type]
            )
            assert ds.status == s

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DefenseSession(
                session_id="s",
                module_id="m",
                questions=["q"],
                status="cancelled",  # type: ignore[arg-type]
            )

    def test_empty_questions_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DefenseSession(session_id="s", module_id="m", questions=[])

    def test_empty_session_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DefenseSession(session_id="", module_id="m", questions=["q"])

    def test_scores_are_integers(self) -> None:
        ds = DefenseSession(
            session_id="s",
            module_id="m",
            questions=["q1", "q2"],
            scores=[100, 0],
        )
        assert ds.scores == [100, 0]
