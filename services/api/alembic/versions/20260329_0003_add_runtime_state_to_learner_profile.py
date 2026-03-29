"""add runtime state json to learner profile"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0003"
down_revision = "20260329_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learner_profile",
        sa.Column("runtime_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("learner_profile", "runtime_state")
