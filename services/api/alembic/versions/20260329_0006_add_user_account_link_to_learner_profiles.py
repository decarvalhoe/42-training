"""add user account link to learner profiles"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260329_0006"
down_revision = "20260329_0005"
branch_labels = None
depends_on = None

FK_NAME = "fk_learner_profile_user_account_id_user_accounts"


def upgrade() -> None:
    with op.batch_alter_table("learner_profile") as batch_op:
        batch_op.add_column(sa.Column("user_account_id", sa.String(length=64), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE learner_profile
            SET user_account_id = (
                SELECT user_accounts.id
                FROM user_accounts
                WHERE user_accounts.learner_profile_id = learner_profile.id
            )
            WHERE EXISTS (
                SELECT 1
                FROM user_accounts
                WHERE user_accounts.learner_profile_id = learner_profile.id
            )
            """
        )
    )

    with op.batch_alter_table("learner_profile") as batch_op:
        batch_op.create_foreign_key(FK_NAME, "user_accounts", ["user_account_id"], ["id"])
        batch_op.create_index(op.f("ix_learner_profile_user_account_id"), ["user_account_id"], unique=False)

    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.add_column(sa.Column("active_profile_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_user_accounts_active_profile_id", "learner_profile", ["active_profile_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.drop_constraint("fk_user_accounts_active_profile_id", type_="foreignkey")
        batch_op.drop_column("active_profile_id")

    with op.batch_alter_table("learner_profile") as batch_op:
        batch_op.drop_index(op.f("ix_learner_profile_user_account_id"))
        batch_op.drop_constraint(FK_NAME, type_="foreignkey")
        batch_op.drop_column("user_account_id")
