"""Service for data export/import functionality."""

from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.accounts.schemas import AccountResponse
from src.allocation_rules.models import AllocationRule
from src.allocation_rules.schemas import AllocationRuleResponse
from src.allocations.models import Allocation
from src.allocations.schemas import AllocationResponse
from src.budgets.models import Budget
from src.data_transfer.schemas import (
    BudgetExport,
    ExportData,
    ImportData,
    ImportResult,
    TransactionExport,
)
from src.envelope_groups.models import EnvelopeGroup
from src.envelope_groups.schemas import EnvelopeGroupResponse
from src.envelopes.models import Envelope
from src.envelopes.schemas import EnvelopeResponse
from src.locations.models import Location
from src.locations.schemas import LocationResponse
from src.notifications.models import Notification
from src.payees.models import Payee
from src.payees.schemas import PayeeResponse
from src.recurring_transactions.models import RecurringTransaction
from src.recurring_transactions.schemas import RecurringTransactionResponse
from src.transactions.models import Transaction


async def export_budget_data(
    session: AsyncSession,
    budget_id: UUID,
) -> ExportData:
    """Export all budget data to ExportData structure.

    Args:
        session: Database session
        budget_id: Budget to export

    Returns:
        ExportData with all budget data
    """
    # Get budget
    budget = await session.get(Budget, budget_id)
    if not budget:
        raise ValueError(f"Budget {budget_id} not found")

    # Export accounts
    accounts_result = await session.execute(
        select(Account)
        .where(Account.budget_id == budget_id)
        .order_by(Account.sort_order)
    )
    accounts = [
        AccountResponse.model_validate(a) for a in accounts_result.scalars().all()
    ]

    # Export envelope groups
    groups_result = await session.execute(
        select(EnvelopeGroup)
        .where(EnvelopeGroup.budget_id == budget_id)
        .order_by(EnvelopeGroup.sort_order)
    )
    envelope_groups = [
        EnvelopeGroupResponse.model_validate(g) for g in groups_result.scalars().all()
    ]

    # Export envelopes
    envelopes_result = await session.execute(
        select(Envelope)
        .where(Envelope.budget_id == budget_id)
        .order_by(Envelope.sort_order)
    )
    envelopes = [
        EnvelopeResponse.model_validate(e) for e in envelopes_result.scalars().all()
    ]

    # Export payees
    payees_result = await session.execute(
        select(Payee).where(Payee.budget_id == budget_id).order_by(Payee.name)
    )
    payees = [PayeeResponse.model_validate(p) for p in payees_result.scalars().all()]

    # Export locations
    locations_result = await session.execute(
        select(Location).where(Location.budget_id == budget_id).order_by(Location.name)
    )
    locations = [
        LocationResponse.model_validate(loc) for loc in locations_result.scalars().all()
    ]

    # Export allocation rules
    rules_result = await session.execute(
        select(AllocationRule)
        .where(AllocationRule.budget_id == budget_id)
        .order_by(AllocationRule.priority)
    )
    allocation_rules = [
        AllocationRuleResponse.model_validate(r) for r in rules_result.scalars().all()
    ]

    # Export recurring transactions
    recurring_result = await session.execute(
        select(RecurringTransaction)
        .where(RecurringTransaction.budget_id == budget_id)
        .order_by(RecurringTransaction.next_occurrence_date)
    )
    recurring_transactions = [
        RecurringTransactionResponse.model_validate(rt)
        for rt in recurring_result.scalars().all()
    ]

    # Export transactions (order by date for readability)
    transactions_result = await session.execute(
        select(Transaction)
        .where(Transaction.budget_id == budget_id)
        .order_by(Transaction.date, Transaction.id)
    )
    transactions = [
        TransactionExport.model_validate(t) for t in transactions_result.scalars().all()
    ]

    # Export allocations
    allocations_result = await session.execute(
        select(Allocation)
        .where(Allocation.budget_id == budget_id)
        .order_by(Allocation.group_id, Allocation.execution_order)
    )
    allocations = [
        AllocationResponse.model_validate(a) for a in allocations_result.scalars().all()
    ]

    return ExportData(
        version="1.0",
        exported_at=datetime.now(UTC),
        budget=BudgetExport(
            name=budget.name,
            default_income_allocation=budget.default_income_allocation,
        ),
        accounts=accounts,
        envelope_groups=envelope_groups,
        envelopes=envelopes,
        payees=payees,
        locations=locations,
        allocation_rules=allocation_rules,
        recurring_transactions=recurring_transactions,
        transactions=transactions,
        allocations=allocations,
    )


async def import_budget_data(
    session: AsyncSession,
    budget_id: UUID,
    data: ImportData,
    clear_existing: bool = False,
) -> ImportResult:
    """Import budget data from ImportData structure.

    Args:
        session: Database session
        budget_id: Budget to import into
        data: Import data
        clear_existing: If True, delete all existing budget data before import

    Returns:
        ImportResult with counts and any errors
    """
    errors: list[str] = []

    # Verify budget exists
    budget = await session.get(Budget, budget_id)
    if not budget:
        return ImportResult(
            success=False,
            accounts_imported=0,
            envelope_groups_imported=0,
            envelopes_imported=0,
            payees_imported=0,
            locations_imported=0,
            allocation_rules_imported=0,
            recurring_transactions_imported=0,
            transactions_imported=0,
            allocations_imported=0,
            errors=[f"Budget {budget_id} not found"],
        )

    # Apply budget-level settings from import
    budget.default_income_allocation = data.budget.default_income_allocation

    # Clear existing data if requested
    if clear_existing:
        await _clear_budget_data(session, budget_id)

    # Build ID mapping (old_id -> new_id)
    id_map: dict[UUID, UUID] = {}

    # Import in dependency order
    try:
        # 1. Accounts (no dependencies)
        for account_data in data.accounts:
            new_id = uuid7()
            id_map[account_data.id] = new_id
            account = Account(
                id=new_id,
                budget_id=budget_id,
                name=account_data.name,
                account_type=account_data.account_type,
                icon=account_data.icon,
                description=account_data.description,
                sort_order=account_data.sort_order,
                include_in_budget=account_data.include_in_budget,
                is_active=account_data.is_active,
                cleared_balance=account_data.cleared_balance,
                uncleared_balance=account_data.uncleared_balance,
                last_reconciled_at=account_data.last_reconciled_at,
            )
            session.add(account)

        # 2. Envelope Groups (no dependencies)
        for group_data in data.envelope_groups:
            new_id = uuid7()
            id_map[group_data.id] = new_id
            group = EnvelopeGroup(
                id=new_id,
                budget_id=budget_id,
                name=group_data.name,
                icon=group_data.icon,
                sort_order=group_data.sort_order,
            )
            session.add(group)

        # 3. Envelopes (depends on envelope_groups, accounts for linked_account_id)
        for envelope_data in data.envelopes:
            new_id = uuid7()
            id_map[envelope_data.id] = new_id
            envelope = Envelope(
                id=new_id,
                budget_id=budget_id,
                envelope_group_id=(
                    id_map.get(envelope_data.envelope_group_id)
                    if envelope_data.envelope_group_id
                    else None
                ),
                linked_account_id=(
                    id_map.get(envelope_data.linked_account_id)
                    if envelope_data.linked_account_id
                    else None
                ),
                name=envelope_data.name,
                icon=envelope_data.icon,
                description=envelope_data.description,
                sort_order=envelope_data.sort_order,
                is_active=envelope_data.is_active,
                is_starred=envelope_data.is_starred,
                is_unallocated=envelope_data.is_unallocated,
                current_balance=envelope_data.current_balance,
                target_balance=envelope_data.target_balance,
            )
            session.add(envelope)

        # 4. Payees (depends on envelopes for default_envelope_id)
        for payee_data in data.payees:
            new_id = uuid7()
            id_map[payee_data.id] = new_id
            payee = Payee(
                id=new_id,
                budget_id=budget_id,
                name=payee_data.name,
                icon=payee_data.icon,
                description=payee_data.description,
                default_envelope_id=(
                    id_map.get(payee_data.default_envelope_id)
                    if payee_data.default_envelope_id
                    else None
                ),
            )
            session.add(payee)

        # 5. Locations (no dependencies)
        for location_data in data.locations:
            new_id = uuid7()
            id_map[location_data.id] = new_id
            location = Location(
                id=new_id,
                budget_id=budget_id,
                name=location_data.name,
                icon=location_data.icon,
                description=location_data.description,
            )
            session.add(location)

        # Flush to satisfy FK constraints for allocation rules and recurring transactions
        await session.flush()

        # 6. Allocation Rules (depends on envelopes)
        for rule_data in data.allocation_rules:
            new_id = uuid7()
            id_map[rule_data.id] = new_id
            envelope_new_id = id_map.get(rule_data.envelope_id)
            if not envelope_new_id:
                errors.append(
                    f"Allocation rule references unknown envelope {rule_data.envelope_id}"
                )
                continue
            rule = AllocationRule(
                id=new_id,
                budget_id=budget_id,
                envelope_id=envelope_new_id,
                priority=rule_data.priority,
                rule_type=rule_data.rule_type,
                amount=rule_data.amount,
                is_active=rule_data.is_active,
                name=rule_data.name,
                respect_target=rule_data.respect_target,
                cap_period_value=rule_data.cap_period_value,
                cap_period_unit=rule_data.cap_period_unit,
            )
            session.add(rule)

        # 7. Recurring Transactions (depends on accounts, payees, locations, envelopes)
        for rt_data in data.recurring_transactions:
            new_id = uuid7()
            id_map[rt_data.id] = new_id
            account_new_id = id_map.get(rt_data.account_id)
            if not account_new_id:
                errors.append(
                    f"Recurring transaction references unknown account {rt_data.account_id}"
                )
                continue

            recurring = RecurringTransaction(
                id=new_id,
                budget_id=budget_id,
                account_id=account_new_id,
                user_id=None,  # Don't preserve user association on import
                destination_account_id=(
                    id_map.get(rt_data.destination_account_id)
                    if rt_data.destination_account_id
                    else None
                ),
                payee_id=(id_map.get(rt_data.payee_id) if rt_data.payee_id else None),
                location_id=(
                    id_map.get(rt_data.location_id) if rt_data.location_id else None
                ),
                envelope_id=(
                    id_map.get(rt_data.envelope_id) if rt_data.envelope_id else None
                ),
                frequency_value=rt_data.frequency_value,
                frequency_unit=rt_data.frequency_unit,
                start_date=rt_data.start_date,
                end_date=rt_data.end_date,
                amount=rt_data.amount,
                memo=rt_data.memo,
                next_occurrence_date=rt_data.next_occurrence_date,
                is_active=rt_data.is_active,
            )
            session.add(recurring)

        # Flush to get IDs before transactions (which reference recurring)
        await session.flush()

        # 8. Transactions (depends on accounts, payees, locations, recurring)
        # First pass: create all transactions
        for txn_data in data.transactions:
            new_id = uuid7()
            id_map[txn_data.id] = new_id
            account_new_id = id_map.get(txn_data.account_id)
            if not account_new_id:
                errors.append(
                    f"Transaction references unknown account {txn_data.account_id}"
                )
                continue

            transaction = Transaction(
                id=new_id,
                budget_id=budget_id,
                account_id=account_new_id,
                payee_id=(id_map.get(txn_data.payee_id) if txn_data.payee_id else None),
                location_id=(
                    id_map.get(txn_data.location_id) if txn_data.location_id else None
                ),
                user_id=None,  # Don't preserve user association on import
                date=txn_data.date,
                amount=txn_data.amount,
                is_cleared=txn_data.is_cleared,
                is_reconciled=txn_data.is_reconciled,
                memo=txn_data.memo,
                transaction_type=txn_data.transaction_type,
                status=txn_data.status,
                recurring_transaction_id=(
                    id_map.get(txn_data.recurring_transaction_id)
                    if txn_data.recurring_transaction_id
                    else None
                ),
                occurrence_index=txn_data.occurrence_index,
                is_modified=txn_data.is_modified,
                linked_transaction_id=None,  # Set in second pass
            )
            session.add(transaction)

        # Flush transactions
        await session.flush()

        # Second pass: update linked_transaction_id for transfers
        for txn_data in data.transactions:
            if txn_data.linked_transaction_id:
                new_txn_id = id_map.get(txn_data.id)
                new_linked_id = id_map.get(txn_data.linked_transaction_id)
                if new_txn_id and new_linked_id:
                    txn = await session.get(Transaction, new_txn_id)
                    if txn:
                        txn.linked_transaction_id = new_linked_id

        # 9. Allocations (depends on envelopes, transactions, allocation_rules)
        for alloc_data in data.allocations:
            new_id = uuid7()
            id_map[alloc_data.id] = new_id
            envelope_new_id = id_map.get(alloc_data.envelope_id)
            if not envelope_new_id:
                errors.append(
                    f"Allocation references unknown envelope {alloc_data.envelope_id}"
                )
                continue

            # Generate new group_id for allocations
            # If multiple allocations share the same old group_id, they should share the same new one
            if alloc_data.group_id not in id_map:
                id_map[alloc_data.group_id] = uuid7()

            allocation = Allocation(
                id=new_id,
                budget_id=budget_id,
                envelope_id=envelope_new_id,
                transaction_id=(
                    id_map.get(alloc_data.transaction_id)
                    if alloc_data.transaction_id
                    else None
                ),
                allocation_rule_id=(
                    id_map.get(alloc_data.allocation_rule_id)
                    if alloc_data.allocation_rule_id
                    else None
                ),
                group_id=id_map[alloc_data.group_id],
                execution_order=alloc_data.execution_order,
                amount=alloc_data.amount,
                date=alloc_data.date,
                memo=alloc_data.memo,
            )
            session.add(allocation)

        await session.flush()

    except Exception as e:
        errors.append(f"Import failed: {e!s}")
        return ImportResult(
            success=False,
            accounts_imported=0,
            envelope_groups_imported=0,
            envelopes_imported=0,
            payees_imported=0,
            locations_imported=0,
            allocation_rules_imported=0,
            recurring_transactions_imported=0,
            transactions_imported=0,
            allocations_imported=0,
            errors=errors,
        )

    return ImportResult(
        success=len(errors) == 0,
        accounts_imported=len(data.accounts),
        envelope_groups_imported=len(data.envelope_groups),
        envelopes_imported=len(data.envelopes),
        payees_imported=len(data.payees),
        locations_imported=len(data.locations),
        allocation_rules_imported=len(data.allocation_rules),
        recurring_transactions_imported=len(data.recurring_transactions),
        transactions_imported=len(data.transactions),
        allocations_imported=len(data.allocations),
        errors=errors,
    )


async def _clear_budget_data(session: AsyncSession, budget_id: UUID) -> None:
    """Delete all budget data (except budget itself and memberships).

    Deletion order respects foreign key constraints.
    """
    # Delete in reverse dependency order
    await session.execute(
        delete(Notification).where(Notification.budget_id == budget_id)
    )
    await session.execute(delete(Allocation).where(Allocation.budget_id == budget_id))
    await session.execute(delete(Transaction).where(Transaction.budget_id == budget_id))
    await session.execute(
        delete(RecurringTransaction).where(RecurringTransaction.budget_id == budget_id)
    )
    await session.execute(
        delete(AllocationRule).where(AllocationRule.budget_id == budget_id)
    )
    await session.execute(delete(Location).where(Location.budget_id == budget_id))
    await session.execute(delete(Payee).where(Payee.budget_id == budget_id))
    await session.execute(delete(Envelope).where(Envelope.budget_id == budget_id))
    await session.execute(
        delete(EnvelopeGroup).where(EnvelopeGroup.budget_id == budget_id)
    )
    await session.execute(delete(Account).where(Account.budget_id == budget_id))
    await session.flush()
