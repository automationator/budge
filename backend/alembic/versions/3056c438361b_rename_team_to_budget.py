"""rename_team_to_budget

Revision ID: 3056c438361b
Revises: ca00c6b0c8f2
Create Date: 2026-01-03 13:23:23.143900

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3056c438361b"
down_revision: str | None = "ca00c6b0c8f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables that have team_id -> budget_id column rename
TABLES_WITH_TEAM_ID = [
    "accounts",
    "allocations",
    "allocation_rules",
    "envelopes",
    "envelope_groups",
    "locations",
    "notifications",
    "notification_preferences",
    "payees",
    "recurring_transactions",
    "transactions",
]


def upgrade() -> None:
    # =========================================================================
    # Step 1: Drop foreign key constraints referencing teams.id
    # =========================================================================
    # Drop FK from user_teams.team_id -> teams.id
    op.drop_constraint("user_teams_team_id_fkey", "user_teams", type_="foreignkey")

    # Drop FK from each table's team_id -> teams.id
    for table in TABLES_WITH_TEAM_ID:
        op.drop_constraint(f"{table}_team_id_fkey", table, type_="foreignkey")

    # =========================================================================
    # Step 2: Drop indexes containing "team" in the name
    # =========================================================================
    # accounts
    op.drop_index("ix_accounts_team_id", table_name="accounts")

    # allocation_rules
    op.drop_index("ix_allocation_rules_team_priority", table_name="allocation_rules")
    op.drop_index("ix_allocation_rules_team_envelope", table_name="allocation_rules")

    # allocations
    op.drop_index("ix_allocations_team_envelope_id", table_name="allocations")
    op.drop_index("ix_allocations_team_transaction_id", table_name="allocations")
    op.drop_index("ix_allocations_team_group_id", table_name="allocations")
    op.drop_index("ix_allocations_team_rule_id", table_name="allocations")

    # envelopes
    op.drop_index("ix_envelopes_team_group_id", table_name="envelopes")

    # envelope_groups
    op.drop_index("ix_envelope_groups_team_id", table_name="envelope_groups")

    # locations
    op.drop_index("ix_locations_team_id", table_name="locations")

    # notifications
    op.drop_index("ix_notifications_team_user_read", table_name="notifications")
    op.drop_index("ix_notifications_team_type", table_name="notifications")

    # notification_preferences
    op.drop_index(
        "ix_notification_preferences_team_user", table_name="notification_preferences"
    )

    # payees
    op.drop_index("ix_payees_team_id", table_name="payees")

    # recurring_transactions
    op.drop_index(
        "ix_recurring_transactions_team_id", table_name="recurring_transactions"
    )
    op.drop_index(
        "ix_recurring_transactions_team_next_occurrence",
        table_name="recurring_transactions",
    )

    # transactions
    op.drop_index("ix_transactions_team_id", table_name="transactions")
    op.drop_index("ix_transactions_team_date_id", table_name="transactions")
    op.drop_index("ix_transactions_team_account_date_id", table_name="transactions")
    op.drop_index("ix_transactions_team_status_date_id", table_name="transactions")
    op.drop_index("ix_transactions_team_payee_id", table_name="transactions")
    op.drop_index("ix_transactions_team_location_id", table_name="transactions")
    op.drop_index("ix_transactions_team_reconciled_date_id", table_name="transactions")

    # =========================================================================
    # Step 3: Drop unique constraints containing "team" in the name
    # =========================================================================
    op.drop_constraint("uq_user_team", "user_teams", type_="unique")
    op.drop_constraint("uq_team_account_name", "accounts", type_="unique")
    op.drop_constraint("uq_team_envelope_name", "envelopes", type_="unique")
    op.drop_constraint("uq_team_envelope_group_name", "envelope_groups", type_="unique")
    op.drop_constraint("uq_team_location_name", "locations", type_="unique")
    op.drop_constraint("uq_team_payee_name", "payees", type_="unique")

    # =========================================================================
    # Step 4: Rename tables
    # =========================================================================
    op.rename_table("teams", "budgets")
    op.rename_table("user_teams", "user_budgets")

    # =========================================================================
    # Step 5: Rename enum type
    # =========================================================================
    op.execute("ALTER TYPE team_role RENAME TO budget_role")

    # =========================================================================
    # Step 6: Rename team_id columns to budget_id
    # =========================================================================
    op.alter_column("user_budgets", "team_id", new_column_name="budget_id")
    for table in TABLES_WITH_TEAM_ID:
        op.alter_column(table, "team_id", new_column_name="budget_id")

    # =========================================================================
    # Step 7: Recreate foreign key constraints with new names
    # =========================================================================
    op.create_foreign_key(
        "user_budgets_budget_id_fkey",
        "user_budgets",
        "budgets",
        ["budget_id"],
        ["id"],
        ondelete="CASCADE",
    )
    for table in TABLES_WITH_TEAM_ID:
        op.create_foreign_key(
            f"{table}_budget_id_fkey",
            table,
            "budgets",
            ["budget_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # =========================================================================
    # Step 8: Recreate unique constraints with new names
    # =========================================================================
    op.create_unique_constraint(
        "uq_user_budget", "user_budgets", ["user_id", "budget_id"]
    )
    op.create_unique_constraint(
        "uq_budget_account_name", "accounts", ["budget_id", "name"]
    )
    op.create_unique_constraint(
        "uq_budget_envelope_name", "envelopes", ["budget_id", "name"]
    )
    op.create_unique_constraint(
        "uq_budget_envelope_group_name", "envelope_groups", ["budget_id", "name"]
    )
    op.create_unique_constraint(
        "uq_budget_location_name", "locations", ["budget_id", "name"]
    )
    op.create_unique_constraint("uq_budget_payee_name", "payees", ["budget_id", "name"])

    # =========================================================================
    # Step 9: Recreate indexes with new names
    # =========================================================================
    # accounts
    op.create_index("ix_accounts_budget_id", "accounts", ["budget_id"], unique=False)

    # allocation_rules
    op.create_index(
        "ix_allocation_rules_budget_priority",
        "allocation_rules",
        ["budget_id", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_allocation_rules_budget_envelope",
        "allocation_rules",
        ["budget_id", "envelope_id"],
        unique=False,
    )

    # allocations
    op.create_index(
        "ix_allocations_budget_envelope_id",
        "allocations",
        ["budget_id", "envelope_id"],
        unique=False,
    )
    op.create_index(
        "ix_allocations_budget_transaction_id",
        "allocations",
        ["budget_id", "transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_allocations_budget_group_id",
        "allocations",
        ["budget_id", "group_id"],
        unique=False,
    )
    op.create_index(
        "ix_allocations_budget_rule_id",
        "allocations",
        ["budget_id", "allocation_rule_id"],
        unique=False,
    )

    # envelopes
    op.create_index(
        "ix_envelopes_budget_group_id",
        "envelopes",
        ["budget_id", "envelope_group_id"],
        unique=False,
    )

    # envelope_groups
    op.create_index(
        "ix_envelope_groups_budget_id",
        "envelope_groups",
        ["budget_id"],
        unique=False,
    )

    # locations
    op.create_index("ix_locations_budget_id", "locations", ["budget_id"], unique=False)

    # notifications
    op.create_index(
        "ix_notifications_budget_user_read",
        "notifications",
        ["budget_id", "user_id", "is_read"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_budget_type",
        "notifications",
        ["budget_id", "notification_type"],
        unique=False,
    )

    # notification_preferences
    op.create_index(
        "ix_notification_preferences_budget_user",
        "notification_preferences",
        ["budget_id", "user_id"],
        unique=False,
    )

    # payees
    op.create_index("ix_payees_budget_id", "payees", ["budget_id"], unique=False)

    # recurring_transactions
    op.create_index(
        "ix_recurring_transactions_budget_id",
        "recurring_transactions",
        ["budget_id"],
        unique=False,
    )
    op.create_index(
        "ix_recurring_transactions_budget_next_occurrence",
        "recurring_transactions",
        ["budget_id", "next_occurrence_date"],
        unique=False,
    )

    # transactions
    op.create_index(
        "ix_transactions_budget_id", "transactions", ["budget_id"], unique=False
    )
    op.create_index(
        "ix_transactions_budget_date_id",
        "transactions",
        ["budget_id", "date", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_budget_account_date_id",
        "transactions",
        ["budget_id", "account_id", "date", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_budget_status_date_id",
        "transactions",
        ["budget_id", "status", "date", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_budget_payee_id",
        "transactions",
        ["budget_id", "payee_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_budget_location_id",
        "transactions",
        ["budget_id", "location_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_budget_reconciled_date_id",
        "transactions",
        ["budget_id", "is_reconciled", "date", "id"],
        unique=False,
    )


def downgrade() -> None:
    # =========================================================================
    # Step 1: Drop foreign key constraints
    # =========================================================================
    op.drop_constraint(
        "user_budgets_budget_id_fkey", "user_budgets", type_="foreignkey"
    )
    for table in TABLES_WITH_TEAM_ID:
        op.drop_constraint(f"{table}_budget_id_fkey", table, type_="foreignkey")

    # =========================================================================
    # Step 2: Drop indexes containing "budget" in the name
    # =========================================================================
    # accounts
    op.drop_index("ix_accounts_budget_id", table_name="accounts")

    # allocation_rules
    op.drop_index("ix_allocation_rules_budget_priority", table_name="allocation_rules")
    op.drop_index("ix_allocation_rules_budget_envelope", table_name="allocation_rules")

    # allocations
    op.drop_index("ix_allocations_budget_envelope_id", table_name="allocations")
    op.drop_index("ix_allocations_budget_transaction_id", table_name="allocations")
    op.drop_index("ix_allocations_budget_group_id", table_name="allocations")
    op.drop_index("ix_allocations_budget_rule_id", table_name="allocations")

    # envelopes
    op.drop_index("ix_envelopes_budget_group_id", table_name="envelopes")

    # envelope_groups
    op.drop_index("ix_envelope_groups_budget_id", table_name="envelope_groups")

    # locations
    op.drop_index("ix_locations_budget_id", table_name="locations")

    # notifications
    op.drop_index("ix_notifications_budget_user_read", table_name="notifications")
    op.drop_index("ix_notifications_budget_type", table_name="notifications")

    # notification_preferences
    op.drop_index(
        "ix_notification_preferences_budget_user", table_name="notification_preferences"
    )

    # payees
    op.drop_index("ix_payees_budget_id", table_name="payees")

    # recurring_transactions
    op.drop_index(
        "ix_recurring_transactions_budget_id", table_name="recurring_transactions"
    )
    op.drop_index(
        "ix_recurring_transactions_budget_next_occurrence",
        table_name="recurring_transactions",
    )

    # transactions
    op.drop_index("ix_transactions_budget_id", table_name="transactions")
    op.drop_index("ix_transactions_budget_date_id", table_name="transactions")
    op.drop_index("ix_transactions_budget_account_date_id", table_name="transactions")
    op.drop_index("ix_transactions_budget_status_date_id", table_name="transactions")
    op.drop_index("ix_transactions_budget_payee_id", table_name="transactions")
    op.drop_index("ix_transactions_budget_location_id", table_name="transactions")
    op.drop_index(
        "ix_transactions_budget_reconciled_date_id", table_name="transactions"
    )

    # =========================================================================
    # Step 3: Drop unique constraints containing "budget" in the name
    # =========================================================================
    op.drop_constraint("uq_user_budget", "user_budgets", type_="unique")
    op.drop_constraint("uq_budget_account_name", "accounts", type_="unique")
    op.drop_constraint("uq_budget_envelope_name", "envelopes", type_="unique")
    op.drop_constraint(
        "uq_budget_envelope_group_name", "envelope_groups", type_="unique"
    )
    op.drop_constraint("uq_budget_location_name", "locations", type_="unique")
    op.drop_constraint("uq_budget_payee_name", "payees", type_="unique")

    # =========================================================================
    # Step 4: Rename budget_id columns back to team_id
    # =========================================================================
    op.alter_column("user_budgets", "budget_id", new_column_name="team_id")
    for table in TABLES_WITH_TEAM_ID:
        op.alter_column(table, "budget_id", new_column_name="team_id")

    # =========================================================================
    # Step 5: Rename enum type back
    # =========================================================================
    op.execute("ALTER TYPE budget_role RENAME TO team_role")

    # =========================================================================
    # Step 6: Rename tables back
    # =========================================================================
    op.rename_table("user_budgets", "user_teams")
    op.rename_table("budgets", "teams")

    # =========================================================================
    # Step 7: Recreate unique constraints with old names
    # =========================================================================
    op.create_unique_constraint("uq_user_team", "user_teams", ["user_id", "team_id"])
    op.create_unique_constraint("uq_team_account_name", "accounts", ["team_id", "name"])
    op.create_unique_constraint(
        "uq_team_envelope_name", "envelopes", ["team_id", "name"]
    )
    op.create_unique_constraint(
        "uq_team_envelope_group_name", "envelope_groups", ["team_id", "name"]
    )
    op.create_unique_constraint(
        "uq_team_location_name", "locations", ["team_id", "name"]
    )
    op.create_unique_constraint("uq_team_payee_name", "payees", ["team_id", "name"])

    # =========================================================================
    # Step 8: Recreate indexes with old names
    # =========================================================================
    # accounts
    op.create_index("ix_accounts_team_id", "accounts", ["team_id"], unique=False)

    # allocation_rules
    op.create_index(
        "ix_allocation_rules_team_priority",
        "allocation_rules",
        ["team_id", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_allocation_rules_team_envelope",
        "allocation_rules",
        ["team_id", "envelope_id"],
        unique=False,
    )

    # allocations
    op.create_index(
        "ix_allocations_team_envelope_id",
        "allocations",
        ["team_id", "envelope_id"],
        unique=False,
    )
    op.create_index(
        "ix_allocations_team_transaction_id",
        "allocations",
        ["team_id", "transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_allocations_team_group_id",
        "allocations",
        ["team_id", "group_id"],
        unique=False,
    )
    op.create_index(
        "ix_allocations_team_rule_id",
        "allocations",
        ["team_id", "allocation_rule_id"],
        unique=False,
    )

    # envelopes
    op.create_index(
        "ix_envelopes_team_group_id",
        "envelopes",
        ["team_id", "envelope_group_id"],
        unique=False,
    )

    # envelope_groups
    op.create_index(
        "ix_envelope_groups_team_id",
        "envelope_groups",
        ["team_id"],
        unique=False,
    )

    # locations
    op.create_index("ix_locations_team_id", "locations", ["team_id"], unique=False)

    # notifications
    op.create_index(
        "ix_notifications_team_user_read",
        "notifications",
        ["team_id", "user_id", "is_read"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_team_type",
        "notifications",
        ["team_id", "notification_type"],
        unique=False,
    )

    # notification_preferences
    op.create_index(
        "ix_notification_preferences_team_user",
        "notification_preferences",
        ["team_id", "user_id"],
        unique=False,
    )

    # payees
    op.create_index("ix_payees_team_id", "payees", ["team_id"], unique=False)

    # recurring_transactions
    op.create_index(
        "ix_recurring_transactions_team_id",
        "recurring_transactions",
        ["team_id"],
        unique=False,
    )
    op.create_index(
        "ix_recurring_transactions_team_next_occurrence",
        "recurring_transactions",
        ["team_id", "next_occurrence_date"],
        unique=False,
    )

    # transactions
    op.create_index(
        "ix_transactions_team_id", "transactions", ["team_id"], unique=False
    )
    op.create_index(
        "ix_transactions_team_date_id",
        "transactions",
        ["team_id", "date", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_team_account_date_id",
        "transactions",
        ["team_id", "account_id", "date", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_team_status_date_id",
        "transactions",
        ["team_id", "status", "date", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_team_payee_id",
        "transactions",
        ["team_id", "payee_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_team_location_id",
        "transactions",
        ["team_id", "location_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_team_reconciled_date_id",
        "transactions",
        ["team_id", "is_reconciled", "date", "id"],
        unique=False,
    )

    # =========================================================================
    # Step 9: Recreate foreign key constraints with old names
    # =========================================================================
    op.create_foreign_key(
        "user_teams_team_id_fkey",
        "user_teams",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    for table in TABLES_WITH_TEAM_ID:
        op.create_foreign_key(
            f"{table}_team_id_fkey",
            table,
            "teams",
            ["team_id"],
            ["id"],
            ondelete="CASCADE",
        )
