"""Service for Start Fresh data deletion."""

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.allocation_rules.models import AllocationRule
from src.allocations.models import Allocation
from src.budgets.models import Budget
from src.envelope_groups.models import EnvelopeGroup
from src.envelopes.models import Envelope
from src.locations.models import Location
from src.payees.models import Payee
from src.recurring_transactions.models import RecurringTransaction
from src.start_fresh.schemas import DataCategory, StartFreshPreview
from src.transactions.models import Transaction


async def get_deletion_preview(
    session: AsyncSession,
    budget_id: UUID,
    categories: list[DataCategory],
) -> StartFreshPreview:
    """Get counts of what will be deleted based on selected categories."""
    preview = StartFreshPreview()

    # Helper to get count for a model
    async def count_model(model: type) -> int:
        result = await session.execute(
            select(func.count()).select_from(model).where(model.budget_id == budget_id)
        )
        return result.scalar() or 0

    # Helper to count unlinked payees (not referenced by transactions or recurring)
    async def count_unlinked_payees() -> int:
        # Get payee IDs referenced by transactions
        txn_payee_ids = (
            select(Transaction.payee_id)
            .where(
                Transaction.budget_id == budget_id,
                Transaction.payee_id.isnot(None),
            )
            .distinct()
        )

        # Get payee IDs referenced by recurring transactions
        recurring_payee_ids = (
            select(RecurringTransaction.payee_id)
            .where(
                RecurringTransaction.budget_id == budget_id,
                RecurringTransaction.payee_id.isnot(None),
            )
            .distinct()
        )

        # Count payees not in either set
        result = await session.execute(
            select(func.count())
            .select_from(Payee)
            .where(
                Payee.budget_id == budget_id,
                ~Payee.id.in_(txn_payee_ids),
                ~Payee.id.in_(recurring_payee_ids),
            )
        )
        return result.scalar() or 0

    is_all = DataCategory.ALL in categories

    # Accounts - also counts transactions if accounts selected
    if is_all or DataCategory.ACCOUNTS in categories:
        preview.accounts_count = await count_model(Account)
        # Accounts cascade to transactions
        preview.transactions_count = await count_model(Transaction)
        preview.allocations_count = await count_model(Allocation)
        preview.recurring_transactions_count = await count_model(RecurringTransaction)

    # Transactions (only if not already counted via accounts)
    if (
        DataCategory.TRANSACTIONS in categories
        and not is_all
        and DataCategory.ACCOUNTS not in categories
    ):
        preview.transactions_count = await count_model(Transaction)
        preview.allocations_count = await count_model(Allocation)

    # Recurring transactions (only if not already counted)
    if (
        DataCategory.RECURRING in categories
        and not is_all
        and DataCategory.ACCOUNTS not in categories
    ):
        preview.recurring_transactions_count = await count_model(RecurringTransaction)

    # Envelopes
    if is_all or DataCategory.ENVELOPES in categories:
        preview.envelopes_count = await count_model(Envelope)
        preview.envelope_groups_count = await count_model(EnvelopeGroup)
        preview.allocation_rules_count = await count_model(AllocationRule)

    # Payees
    if is_all or DataCategory.PAYEES in categories:
        if is_all or DataCategory.TRANSACTIONS in categories:
            # If deleting transactions too, can delete all payees
            preview.payees_count = await count_model(Payee)
        else:
            # Only count unlinked payees
            preview.payees_count = await count_unlinked_payees()

    # Locations
    if is_all or DataCategory.LOCATIONS in categories:
        preview.locations_count = await count_model(Location)

    # Allocations (clear allocations and reset envelope balances)
    # Only count if not already counted via TRANSACTIONS, ENVELOPES, or ACCOUNTS
    if (
        DataCategory.ALLOCATIONS in categories
        and not is_all
        and DataCategory.TRANSACTIONS not in categories
        and DataCategory.ENVELOPES not in categories
        and DataCategory.ACCOUNTS not in categories
    ):
        preview.allocations_count = await count_model(Allocation)
        # Count envelopes with non-zero balances (excluding unallocated)
        result = await session.execute(
            select(func.count())
            .select_from(Envelope)
            .where(
                Envelope.budget_id == budget_id,
                Envelope.is_unallocated == False,  # noqa: E712
                Envelope.current_balance != 0,
            )
        )
        preview.envelopes_cleared_count = result.scalar() or 0

    return preview


async def delete_budget_data(
    session: AsyncSession,
    budget_id: UUID,
    categories: list[DataCategory],
) -> StartFreshPreview:
    """Delete budget data in correct order respecting FK constraints.

    Returns counts of what was deleted.
    """
    deleted = StartFreshPreview()
    is_all = DataCategory.ALL in categories

    # Determine what to delete
    delete_transactions = is_all or DataCategory.TRANSACTIONS in categories
    delete_accounts = is_all or DataCategory.ACCOUNTS in categories
    delete_recurring = is_all or DataCategory.RECURRING in categories
    delete_envelopes = is_all or DataCategory.ENVELOPES in categories
    delete_payees = is_all or DataCategory.PAYEES in categories
    delete_locations = is_all or DataCategory.LOCATIONS in categories
    delete_allocations_only = DataCategory.ALLOCATIONS in categories

    # If deleting accounts, also delete transactions and recurring
    if delete_accounts:
        delete_transactions = True
        delete_recurring = True

    # 1. Delete allocations (references transactions and envelopes)
    if delete_transactions or delete_envelopes or delete_allocations_only:
        result = await session.execute(
            delete(Allocation)
            .where(Allocation.budget_id == budget_id)
            .returning(Allocation.id)
        )
        deleted.allocations_count = len(result.all())

    # 1b. Reset envelope balances if clearing allocations or deleting transactions
    # (but not if deleting envelopes entirely, since they'll be gone)
    if (delete_allocations_only or delete_transactions) and not delete_envelopes:
        # Count envelopes that will be cleared (for response)
        count_result = await session.execute(
            select(func.count())
            .select_from(Envelope)
            .where(
                Envelope.budget_id == budget_id,
                Envelope.is_unallocated == False,  # noqa: E712
                Envelope.current_balance != 0,
            )
        )
        deleted.envelopes_cleared_count = count_result.scalar() or 0

        # Reset all regular envelope balances to 0
        # (Unallocated is calculated dynamically, so we skip it)
        await session.execute(
            update(Envelope)
            .where(
                Envelope.budget_id == budget_id,
                Envelope.is_unallocated == False,  # noqa: E712
            )
            .values(current_balance=0)
        )

    # 2. Delete transactions (references accounts, payees, locations)
    if delete_transactions:
        result = await session.execute(
            delete(Transaction)
            .where(Transaction.budget_id == budget_id)
            .returning(Transaction.id)
        )
        deleted.transactions_count = len(result.all())

        # Reset all account balances to 0 since all transactions are deleted
        await session.execute(
            update(Account)
            .where(Account.budget_id == budget_id)
            .values(cleared_balance=0, uncleared_balance=0)
        )

    # 3. Delete recurring transactions
    if delete_recurring:
        result = await session.execute(
            delete(RecurringTransaction)
            .where(RecurringTransaction.budget_id == budget_id)
            .returning(RecurringTransaction.id)
        )
        deleted.recurring_transactions_count = len(result.all())

    # 4. Delete allocation rules (references envelopes)
    if delete_envelopes:
        result = await session.execute(
            delete(AllocationRule)
            .where(AllocationRule.budget_id == budget_id)
            .returning(AllocationRule.id)
        )
        deleted.allocation_rules_count = len(result.all())

    # 5. Delete locations (transactions.location_id is SET NULL)
    if delete_locations:
        result = await session.execute(
            delete(Location)
            .where(Location.budget_id == budget_id)
            .returning(Location.id)
        )
        deleted.locations_count = len(result.all())

    # 6. Delete payees
    if delete_payees:
        if delete_transactions:
            # All transactions deleted, can delete all payees
            result = await session.execute(
                delete(Payee).where(Payee.budget_id == budget_id).returning(Payee.id)
            )
            deleted.payees_count = len(result.all())
        else:
            # Only delete unlinked payees
            txn_payee_ids = (
                select(Transaction.payee_id)
                .where(
                    Transaction.budget_id == budget_id,
                    Transaction.payee_id.isnot(None),
                )
                .distinct()
            )
            recurring_payee_ids = (
                select(RecurringTransaction.payee_id)
                .where(
                    RecurringTransaction.budget_id == budget_id,
                    RecurringTransaction.payee_id.isnot(None),
                )
                .distinct()
            )
            result = await session.execute(
                delete(Payee)
                .where(
                    Payee.budget_id == budget_id,
                    ~Payee.id.in_(txn_payee_ids),
                    ~Payee.id.in_(recurring_payee_ids),
                )
                .returning(Payee.id)
            )
            deleted.payees_count = len(result.all())

    # 7. Delete envelopes
    if delete_envelopes:
        result = await session.execute(
            delete(Envelope)
            .where(Envelope.budget_id == budget_id)
            .returning(Envelope.id)
        )
        deleted.envelopes_count = len(result.all())

    # 8. Delete envelope groups
    if delete_envelopes:
        result = await session.execute(
            delete(EnvelopeGroup)
            .where(EnvelopeGroup.budget_id == budget_id)
            .returning(EnvelopeGroup.id)
        )
        deleted.envelope_groups_count = len(result.all())

    # 9. Delete accounts (must be last as transactions reference them)
    if delete_accounts:
        result = await session.execute(
            delete(Account).where(Account.budget_id == budget_id).returning(Account.id)
        )
        deleted.accounts_count = len(result.all())

    await session.flush()
    return deleted


async def get_owned_budgets(session: AsyncSession, user_id: UUID) -> list[Budget]:
    """Get all budgets owned by a user."""
    result = await session.execute(select(Budget).where(Budget.owner_id == user_id))
    return list(result.scalars().all())


async def get_all_user_data_preview(
    session: AsyncSession,
    user_id: UUID,
    categories: list[DataCategory],
) -> StartFreshPreview:
    """Get preview counts for all data across all budgets the user owns."""
    owned_budgets = await get_owned_budgets(session, user_id)

    total = StartFreshPreview()
    for budget in owned_budgets:
        preview = await get_deletion_preview(session, budget.id, categories)
        # Aggregate counts
        total.transactions_count += preview.transactions_count
        total.allocations_count += preview.allocations_count
        total.recurring_transactions_count += preview.recurring_transactions_count
        total.envelopes_count += preview.envelopes_count
        total.envelope_groups_count += preview.envelope_groups_count
        total.allocation_rules_count += preview.allocation_rules_count
        total.accounts_count += preview.accounts_count
        total.payees_count += preview.payees_count
        total.locations_count += preview.locations_count
        total.envelopes_cleared_count += preview.envelopes_cleared_count

    return total


async def delete_all_user_data(
    session: AsyncSession,
    user_id: UUID,
    categories: list[DataCategory],
) -> StartFreshPreview:
    """Delete data from all budgets the user owns.

    Returns aggregated counts of what was deleted.
    """
    owned_budgets = await get_owned_budgets(session, user_id)

    total = StartFreshPreview()
    for budget in owned_budgets:
        deleted = await delete_budget_data(session, budget.id, categories)
        # Aggregate counts
        total.transactions_count += deleted.transactions_count
        total.allocations_count += deleted.allocations_count
        total.recurring_transactions_count += deleted.recurring_transactions_count
        total.envelopes_count += deleted.envelopes_count
        total.envelope_groups_count += deleted.envelope_groups_count
        total.allocation_rules_count += deleted.allocation_rules_count
        total.accounts_count += deleted.accounts_count
        total.payees_count += deleted.payees_count
        total.locations_count += deleted.locations_count
        total.envelopes_cleared_count += deleted.envelopes_cleared_count

    return total
