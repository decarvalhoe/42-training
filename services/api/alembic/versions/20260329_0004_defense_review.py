"""create defense session and review attempt tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0004"
down_revision = "20260329_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "defense_session",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=True),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_artifacts", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profile.id"]),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(op.f("ix_defense_session_learner_id"), "defense_session", ["learner_id"], unique=False)
    op.create_index(op.f("ix_defense_session_module_id"), "defense_session", ["module_id"], unique=False)
    op.create_index(op.f("ix_defense_session_status"), "defense_session", ["status"], unique=False)

    op.create_table(
        "review_attempt",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=True),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("evidence_artifacts", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profile.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["learner_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_attempt_learner_id"), "review_attempt", ["learner_id"], unique=False)
    op.create_index(op.f("ix_review_attempt_module_id"), "review_attempt", ["module_id"], unique=False)
    op.create_index(op.f("ix_review_attempt_reviewer_id"), "review_attempt", ["reviewer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_attempt_reviewer_id"), table_name="review_attempt")
    op.drop_index(op.f("ix_review_attempt_module_id"), table_name="review_attempt")
    op.drop_index(op.f("ix_review_attempt_learner_id"), table_name="review_attempt")
    op.drop_table("review_attempt")

    op.drop_index(op.f("ix_defense_session_status"), table_name="defense_session")
    op.drop_index(op.f("ix_defense_session_module_id"), table_name="defense_session")
    op.drop_index(op.f("ix_defense_session_learner_id"), table_name="defense_session")
    op.drop_table("defense_session")
