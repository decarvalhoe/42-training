"""create learner_profiles table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learner_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("login", sa.String(length=64), nullable=False),
        sa.Column("track", sa.String(length=32), nullable=False),
        sa.Column("current_module", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learner_profiles_login"), "learner_profiles", ["login"], unique=True)
    op.create_index(op.f("ix_learner_profiles_track"), "learner_profiles", ["track"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_learner_profiles_track"), table_name="learner_profiles")
    op.drop_index(op.f("ix_learner_profiles_login"), table_name="learner_profiles")
    op.drop_table("learner_profiles")
