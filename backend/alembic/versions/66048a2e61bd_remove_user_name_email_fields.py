"""remove_user_name_email_fields

Revision ID: 66048a2e61bd
Revises: 3056c438361b
Create Date: 2026-01-04 01:46:16.863566

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "66048a2e61bd"
down_revision: str | None = "3056c438361b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the email unique index first
    op.drop_index("ix_users_email", table_name="users")

    # Drop the columns
    op.drop_column("users", "email")
    op.drop_column("users", "first_name")
    op.drop_column("users", "last_name")


def downgrade() -> None:
    # Re-add columns
    op.add_column(
        "users",
        sa.Column("last_name", sa.VARCHAR(100), autoincrement=False, nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("first_name", sa.VARCHAR(100), autoincrement=False, nullable=True),
    )
    op.add_column(
        "users", sa.Column("email", sa.VARCHAR(255), autoincrement=False, nullable=True)
    )

    # Re-create email unique index
    op.create_index("ix_users_email", "users", ["email"], unique=True)
