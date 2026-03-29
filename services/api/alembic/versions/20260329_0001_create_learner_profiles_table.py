"""create core learner progression tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learner_profile",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("login", sa.String(length=64), nullable=False),
        sa.Column("track", sa.String(length=32), nullable=False),
        sa.Column("current_module", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learner_profile_login"), "learner_profile", ["login"], unique=True)
    op.create_index(op.f("ix_learner_profile_track"), "learner_profile", ["track"], unique=False)

    op.create_table(
        "progression",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("track_id", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learner_id", "module_id", name="uq_progression_learner_module"),
    )
    op.create_index(op.f("ix_progression_learner_id"), "progression", ["learner_id"], unique=False)
    op.create_index(op.f("ix_progression_module_id"), "progression", ["module_id"], unique=False)
    op.create_index(op.f("ix_progression_status"), "progression", ["status"], unique=False)
    op.create_index(op.f("ix_progression_track_id"), "progression", ["track_id"], unique=False)

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("progression_id", sa.String(length=64), nullable=True),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_index", sa.Integer(), nullable=True),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=True),
        sa.Column("checkpoint_id", sa.String(length=128), nullable=True),
        sa.Column("self_evaluation", sa.String(length=16), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expected_content", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profile.id"]),
        sa.ForeignKeyConstraint(["progression_id"], ["progression.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_checkpoint_id"), "evidence", ["checkpoint_id"], unique=False)
    op.create_index(op.f("ix_evidence_evidence_type"), "evidence", ["evidence_type"], unique=False)
    op.create_index(op.f("ix_evidence_learner_id"), "evidence", ["learner_id"], unique=False)
    op.create_index(op.f("ix_evidence_module_id"), "evidence", ["module_id"], unique=False)
    op.create_index(op.f("ix_evidence_progression_id"), "evidence", ["progression_id"], unique=False)

    op.create_table(
        "review",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=True),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column("module_id", sa.String(length=128), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profile.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["learner_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_learner_id"), "review", ["learner_id"], unique=False)
    op.create_index(op.f("ix_review_module_id"), "review", ["module_id"], unique=False)
    op.create_index(op.f("ix_review_reviewer_id"), "review", ["reviewer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_reviewer_id"), table_name="review")
    op.drop_index(op.f("ix_review_module_id"), table_name="review")
    op.drop_index(op.f("ix_review_learner_id"), table_name="review")
    op.drop_table("review")

    op.drop_index(op.f("ix_evidence_progression_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_module_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_learner_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_evidence_type"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_checkpoint_id"), table_name="evidence")
    op.drop_table("evidence")

    op.drop_index(op.f("ix_progression_track_id"), table_name="progression")
    op.drop_index(op.f("ix_progression_status"), table_name="progression")
    op.drop_index(op.f("ix_progression_module_id"), table_name="progression")
    op.drop_index(op.f("ix_progression_learner_id"), table_name="progression")
    op.drop_table("progression")

    op.drop_index(op.f("ix_learner_profile_track"), table_name="learner_profile")
    op.drop_index(op.f("ix_learner_profile_login"), table_name="learner_profile")
    op.drop_table("learner_profile")
