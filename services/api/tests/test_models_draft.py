"""Draft tests for SQLAlchemy model preparation in issue #49 and #128."""

from app.models import Base, DefenseSession, Evidence, LearnerProfile, Progression, Review, ReviewAttempt


def test_core_model_classes_exist() -> None:
    assert Base is not None
    assert LearnerProfile.__tablename__ == "learner_profile"
    assert Progression.__tablename__ == "progression"
    assert Evidence.__tablename__ == "evidence"
    assert Review.__tablename__ == "review"
    assert DefenseSession.__tablename__ == "defense_session"
    assert ReviewAttempt.__tablename__ == "review_attempt"
