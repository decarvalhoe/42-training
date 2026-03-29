"""Draft tests for SQLAlchemy model preparation in issue #49."""

from app.models import Base, Evidence, LearnerProfile, Progression, Review


def test_core_model_classes_exist() -> None:
    assert Base is not None
    assert LearnerProfile.__tablename__ == "learner_profile"
    assert Progression.__tablename__ == "progression"
    assert Evidence.__tablename__ == "evidence"
    assert Review.__tablename__ == "review"
