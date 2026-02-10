"""add_cc_envelope_link

Revision ID: 321e1c2010cd
Revises: c4d5e6f7g8h9
Create Date: 2025-12-20 22:21:37.046847

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "321e1c2010cd"
down_revision: str | None = "c4d5e6f7g8h9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("envelopes", sa.Column("linked_account_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_envelopes_linked_account",
        "envelopes",
        ["linked_account_id"],
        unique=True,
        postgresql_where=sa.text("linked_account_id IS NOT NULL"),
    )
    op.create_foreign_key(
        "fk_envelopes_linked_account",
        "envelopes",
        "accounts",
        ["linked_account_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_envelopes_linked_account", "envelopes", type_="foreignkey")
    op.drop_index(
        "ix_envelopes_linked_account",
        table_name="envelopes",
        postgresql_where=sa.text("linked_account_id IS NOT NULL"),
    )
    op.drop_column("envelopes", "linked_account_id")
