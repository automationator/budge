"""add_admin_and_system_settings

Revision ID: b589155c376d
Revises: 0e3d8f7a42d8
Create Date: 2026-01-20 12:11:14.166022

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b589155c376d"
down_revision: str | None = "0e3d8f7a42d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_admin column to users table
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create system_settings table (single-row pattern)
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "registration_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            onupdate=sa.func.now(),
        ),
    )

    # Insert the default settings row
    op.execute(
        "INSERT INTO system_settings (id, registration_enabled) VALUES (1, true)"
    )


def downgrade() -> None:
    # Drop system_settings table
    op.drop_table("system_settings")

    # Drop is_admin column
    op.drop_column("users", "is_admin")
