"""create user accounts table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0002"
down_revision = "20260329_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("learner_profile_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["learner_profile_id"], ["learner_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_user_accounts_email"),
        sa.UniqueConstraint("learner_profile_id", name="uq_user_accounts_learner_profile_id"),
    )
    op.create_index(op.f("ix_user_accounts_email"), "user_accounts", ["email"], unique=True)
    op.create_index(op.f("ix_user_accounts_learner_profile_id"), "user_accounts", ["learner_profile_id"], unique=True)
    op.create_index(op.f("ix_user_accounts_status"), "user_accounts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_accounts_status"), table_name="user_accounts")
    op.drop_index(op.f("ix_user_accounts_learner_profile_id"), table_name="user_accounts")
    op.drop_index(op.f("ix_user_accounts_email"), table_name="user_accounts")
    op.drop_table("user_accounts")
