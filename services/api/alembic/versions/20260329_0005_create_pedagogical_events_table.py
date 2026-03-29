"""create pedagogical events table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0005"
down_revision = "20260329_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pedagogical_event",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=True),
        sa.Column("track_id", sa.String(length=32), nullable=True),
        sa.Column("module_id", sa.String(length=128), nullable=True),
        sa.Column("checkpoint_index", sa.Integer(), nullable=True),
        sa.Column("source_service", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pedagogical_event_created_at"), "pedagogical_event", ["created_at"], unique=False)
    op.create_index(op.f("ix_pedagogical_event_event_type"), "pedagogical_event", ["event_type"], unique=False)
    op.create_index(op.f("ix_pedagogical_event_learner_id"), "pedagogical_event", ["learner_id"], unique=False)
    op.create_index(op.f("ix_pedagogical_event_module_id"), "pedagogical_event", ["module_id"], unique=False)
    op.create_index(op.f("ix_pedagogical_event_source_service"), "pedagogical_event", ["source_service"], unique=False)
    op.create_index(op.f("ix_pedagogical_event_track_id"), "pedagogical_event", ["track_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pedagogical_event_track_id"), table_name="pedagogical_event")
    op.drop_index(op.f("ix_pedagogical_event_source_service"), table_name="pedagogical_event")
    op.drop_index(op.f("ix_pedagogical_event_module_id"), table_name="pedagogical_event")
    op.drop_index(op.f("ix_pedagogical_event_learner_id"), table_name="pedagogical_event")
    op.drop_index(op.f("ix_pedagogical_event_event_type"), table_name="pedagogical_event")
    op.drop_index(op.f("ix_pedagogical_event_created_at"), table_name="pedagogical_event")
    op.drop_table("pedagogical_event")
