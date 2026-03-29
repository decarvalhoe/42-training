"""Tests for SQLModel and Alembic bootstrap setup (Issue #50)."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db import DEFAULT_DATABASE_URL, create_async_db_engine, get_database_url, is_async_database_url
from app.models import Base, LearnerProfile

API_ROOT = Path(__file__).resolve().parents[1]


class TestDatabaseConfig:
    def test_default_database_url_matches_env_example(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert get_database_url() == DEFAULT_DATABASE_URL

    def test_runtime_engine_requires_async_driver(self) -> None:
        with pytest.raises(ValueError, match="async SQLAlchemy driver"):
            create_async_db_engine("postgresql://training:training@localhost:5432/training")

    def test_async_driver_detection(self) -> None:
        assert is_async_database_url("postgresql+asyncpg://training:training@localhost:5432/training")
        assert is_async_database_url("sqlite+aiosqlite:///tmp/test.db")
        assert not is_async_database_url("sqlite:///tmp/test.db")


class TestSqlModelMetadata:
    def test_learner_profile_model_registered_in_metadata(self) -> None:
        table = Base.metadata.tables["learner_profile"]
        assert LearnerProfile.__table__.name == "learner_profile"
        assert {"id", "login", "track", "current_module", "started_at", "updated_at"} <= set(table.columns.keys())


class TestAlembicBootstrap:
    def test_upgrade_head_creates_learner_profiles_table(self, tmp_path: Path) -> None:
        db_path = tmp_path / "bootstrap.db"
        config = Config(str(API_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(API_ROOT / "alembic"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        command.upgrade(config, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        assert "learner_profiles" in inspector.get_table_names()

        columns = {column["name"] for column in inspector.get_columns("learner_profiles")}
        assert {"id", "login", "track", "current_module", "started_at", "updated_at"} <= columns
