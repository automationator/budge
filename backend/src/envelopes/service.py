from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocation_rules.models import AllocationCapPeriodUnit
from src.allocations.models import Allocation
from src.envelopes.exceptions import (
    CannotDeactivateUnallocatedEnvelopeError,
    CannotDeleteCCEnvelopeError,
    CannotDeleteUnallocatedEnvelopeError,
    CannotModifyUnallocatedEnvelopeError,
    DuplicateEnvelopeNameError,
    EnvelopeNotFoundError,
    InsufficientUnallocatedFundsError,
)
from src.envelopes.models import Envelope
from src.envelopes.schemas import EnvelopeCreate, EnvelopeUpdate
from src.transactions.models import Transaction, TransactionType

UNALLOCATED_ENVELOPE_NAME = "Unallocated"


def calculate_period_boundaries(
    reference_date: date,
    period_value: int,
    period_unit: AllocationCapPeriodUnit,
) -> tuple[date, date]:
    """Calculate the start and end dates for a calendar-aligned period.

    Periods are calendar-aligned for predictability:
    - WEEK: Monday through Sunday (ISO week)
    - MONTH: 1st through end of month
    - YEAR: Jan 1 through Dec 31

    For multi-unit periods (e.g., 3 months = quarterly):
    - Aligned to calendar boundaries (Q1, Q2, etc. for 3 months)

    Returns (period_start, period_end) where end is exclusive.
    """
    if period_unit == AllocationCapPeriodUnit.WEEK:
        # Find the start of the week period
        # Monday = 0, Sunday = 6
        days_since_monday = reference_date.weekday()
        week_start = reference_date - timedelta(days=days_since_monday)

        if period_value == 1:
            period_start = week_start
        else:
            # For multi-week periods, align to ISO week numbers
            # e.g., period_value=2: weeks 1-2, 3-4, 5-6, etc.
            iso_year, iso_week, _ = reference_date.isocalendar()
            # Calculate which period we're in (0-indexed)
            period_num = (iso_week - 1) // period_value
            first_week_of_period = period_num * period_value + 1
            # Find the Monday of that week
            jan_4 = date(iso_year, 1, 4)  # Jan 4 is always in week 1
            days_to_first_monday = (jan_4.weekday()) % 7
            first_monday_of_year = jan_4 - timedelta(days=days_to_first_monday)
            period_start = first_monday_of_year + timedelta(
                weeks=first_week_of_period - 1
            )

        period_end = period_start + timedelta(weeks=period_value)

    elif period_unit == AllocationCapPeriodUnit.MONTH:
        if period_value == 1:
            period_start = reference_date.replace(day=1)
            # End is first day of next month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        else:
            # Multi-month periods aligned to calendar year
            # e.g., 2 months: Jan-Feb, Mar-Apr, etc.
            # e.g., 3 months: Q1, Q2, Q3, Q4
            year = reference_date.year
            month = reference_date.month
            # Calculate which period we're in (0-indexed)
            period_num = (month - 1) // period_value
            first_month = period_num * period_value + 1
            period_start = date(year, first_month, 1)
            # Calculate end month
            end_month = first_month + period_value
            if end_month > 12:
                period_end = date(year + 1, end_month - 12, 1)
            else:
                period_end = date(year, end_month, 1)

    else:  # YEAR
        if period_value == 1:
            period_start = date(reference_date.year, 1, 1)
            period_end = date(reference_date.year + 1, 1, 1)
        else:
            # Multi-year periods
            # Calculate which period we're in
            # For simplicity, align to period_value boundaries starting from year 0
            period_num = reference_date.year // period_value
            start_year = period_num * period_value
            period_start = date(start_year, 1, 1)
            period_end = date(start_year + period_value, 1, 1)

    return period_start, period_end


async def get_period_to_date_allocation(
    session: AsyncSession,
    budget_id: UUID,
    envelope_id: UUID,
    period_value: int,
    period_unit: AllocationCapPeriodUnit,
    reference_date: date | None = None,
) -> int:
    """Calculate income allocations to an envelope in the current period.

    Counts allocations that:
    - Have positive amount (income/inflow)
    - Are linked to a positive transaction (income)
    - Have transaction date within the current period

    Does NOT count:
    - Envelope-to-envelope transfers (no transaction_id)
    - Expenses (negative amounts)
    - Manual redistributions

    Returns total in cents.
    """
    if reference_date is None:
        reference_date = date.today()

    period_start, period_end = calculate_period_boundaries(
        reference_date, period_value, period_unit
    )

    # Query allocations for this envelope within the period
    # Join to Transaction to filter by date and ensure it's income
    result = await session.execute(
        select(func.coalesce(func.sum(Allocation.amount), 0))
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.envelope_id == envelope_id,
            Allocation.amount > 0,  # Only positive (income) allocations
            Transaction.date >= period_start,
            Transaction.date < period_end,
            Transaction.amount > 0,  # Transaction is income
        )
    )

    return result.scalar_one() or 0


async def calculate_unallocated_balance(session: AsyncSession, budget_id: UUID) -> int:
    """Calculate unallocated balance (Ready to Assign) dynamically.

    Returns: sum(non-CC budget account balances) - sum(all envelope balances)

    Credit card accounts are EXCLUDED because CC spending is "borrowed money"
    with a net-zero effect on the budget. When you spend on a CC:
    - Checking stays the same (no cash left your account)
    - Spending envelope decreases (e.g., Groceries -$50)
    - CC envelope increases (+$50, tracking payment funds)
    - CC account debt increases (but excluded from this calculation)

    Net effect on Ready to Assign: $0

    Example:
    - Checking: $100, Groceries envelope: $100, Ready to Assign: $0
    - Spend $50 on CC from Groceries
    - Groceries: $50, CC envelope: $50, total envelopes still $100
    - Ready to Assign: $100 (checking) - $100 (envelopes) = $0 ✓

    This ensures Ready to Assign represents actual unallocated cash, not
    affected by credit card debt which is a separate liability.
    """
    # Sum NON-CC budget account balances only (cleared + uncleared = working balance)
    # Credit cards are excluded because CC debt is a liability, not a reduction
    # in available cash. The cash leaves when you PAY the card, not when you spend.
    account_result = await session.execute(
        select(
            func.coalesce(
                func.sum(Account.cleared_balance + Account.uncleared_balance), 0
            )
        ).where(
            Account.budget_id == budget_id,
            Account.include_in_budget == True,  # noqa: E712
            Account.account_type != AccountType.CREDIT_CARD,  # Exclude CC accounts
        )
    )
    total_accounts = account_result.scalar_one()

    # Sum ALL envelope balances (including CC envelopes, excluding unallocated)
    # CC envelopes are INCLUDED because they represent real money set aside
    # for card payments - just like any other envelope allocation.
    envelope_result = await session.execute(
        select(func.coalesce(func.sum(Envelope.current_balance), 0)).where(
            Envelope.budget_id == budget_id,
            Envelope.is_unallocated == False,  # noqa: E712
        )
    )
    total_envelopes = envelope_result.scalar_one()

    return total_accounts - total_envelopes


async def calculate_unfunded_cc_debt(session: AsyncSession, budget_id: UUID) -> int:
    """Calculate total unfunded credit card debt.

    Unfunded CC debt is the portion of credit card debt that isn't covered
    by the corresponding CC envelope balance. This happens when:
    - A CC account is added with existing debt (before using Budge)
    - Spending occurred without allocating to the CC envelope

    For each CC account: unfunded debt = max(0, |CC debt| - CC envelope balance)
    Returns total across all CC accounts (in cents).

    This is shown as a warning to users so they can plan to fund the debt.
    """
    # Get all CC accounts with their linked envelope balances
    result = await session.execute(
        select(
            Account.id,
            (Account.cleared_balance + Account.uncleared_balance).label("balance"),
            func.coalesce(Envelope.current_balance, 0).label("envelope_balance"),
        )
        .outerjoin(Envelope, Envelope.linked_account_id == Account.id)
        .where(
            Account.budget_id == budget_id,
            Account.include_in_budget == True,  # noqa: E712
            Account.account_type == AccountType.CREDIT_CARD,
        )
    )

    total_unfunded = 0
    for row in result:
        # CC balance is negative when there's debt
        cc_debt = -row.balance if row.balance < 0 else 0
        envelope_balance = row.envelope_balance if row.envelope_balance > 0 else 0
        unfunded = max(0, cc_debt - envelope_balance)
        total_unfunded += unfunded

    return total_unfunded


async def validate_unallocated_has_funds(
    session: AsyncSession, budget_id: UUID, amount: int
) -> None:
    """Validate that unallocated has sufficient funds.

    Raises InsufficientUnallocatedFundsError if balance < amount.
    """
    balance = await calculate_unallocated_balance(session, budget_id)
    if balance < amount:
        raise InsufficientUnallocatedFundsError(balance, amount)


async def list_envelopes(session: AsyncSession, budget_id: UUID) -> list[Envelope]:
    """List all envelopes for a budget, ordered by sort_order then name.

    The unallocated envelope's balance is calculated dynamically rather than
    using the stored value.
    """
    result = await session.execute(
        select(Envelope)
        .where(Envelope.budget_id == budget_id)
        .order_by(Envelope.sort_order, Envelope.name)
    )
    envelopes = list(result.scalars().all())

    # Override unallocated envelope balance with calculated value
    for envelope in envelopes:
        if envelope.is_unallocated:
            envelope.current_balance = await calculate_unallocated_balance(
                session, budget_id
            )
            break

    return envelopes


async def get_envelope_by_id(
    session: AsyncSession, budget_id: UUID, envelope_id: UUID
) -> Envelope:
    """Get an envelope by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Envelope).where(
            Envelope.id == envelope_id, Envelope.budget_id == budget_id
        )
    )
    envelope = result.scalar_one_or_none()
    if not envelope:
        raise EnvelopeNotFoundError(envelope_id)
    return envelope


async def get_unallocated_envelope(
    session: AsyncSession, budget_id: UUID
) -> Envelope | None:
    """Get the unallocated envelope for a budget, if it exists.

    The balance is calculated dynamically rather than using the stored value.
    """
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget_id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    envelope = result.scalar_one_or_none()
    if envelope:
        envelope.current_balance = await calculate_unallocated_balance(
            session, budget_id
        )
    return envelope


async def ensure_unallocated_envelope(
    session: AsyncSession, budget_id: UUID
) -> Envelope:
    """Get or create the Unallocated envelope for a budget.

    This is called automatically when creating the first regular envelope.
    """
    existing = await get_unallocated_envelope(session, budget_id)
    if existing:
        return existing

    envelope = Envelope(
        budget_id=budget_id,
        name=UNALLOCATED_ENVELOPE_NAME,
        is_unallocated=True,
        sort_order=-1,  # Always sort first
    )
    session.add(envelope)
    await session.flush()
    return envelope


async def create_cc_envelope(
    session: AsyncSession, budget_id: UUID, account: Account
) -> Envelope:
    """Create a linked envelope for a credit card account.

    The envelope has the same name as the account and is linked via
    the linked_account_id field. Money moves to this envelope when
    spending on the credit card, ensuring funds are set aside for payment.
    """
    # Ensure unallocated envelope exists first
    await ensure_unallocated_envelope(session, budget_id)

    envelope = Envelope(
        budget_id=budget_id,
        name=account.name,
        linked_account_id=account.id,
        icon="",
        sort_order=0,
        is_active=True,
    )
    session.add(envelope)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_envelope_name" in str(e):
            raise DuplicateEnvelopeNameError(account.name) from e
        raise
    return envelope


async def get_cc_envelope_by_account_id(
    session: AsyncSession, budget_id: UUID, account_id: UUID
) -> Envelope | None:
    """Get the linked envelope for a credit card account, if it exists."""
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget_id,
            Envelope.linked_account_id == account_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_cc_envelope(
    session: AsyncSession, budget_id: UUID, account_id: UUID
) -> bool:
    """Delete the linked envelope for a credit card account.

    Called when account type changes FROM credit_card.
    Returns True if deleted, False if none existed.
    """
    envelope = await get_cc_envelope_by_account_id(session, budget_id, account_id)
    if envelope:
        await session.delete(envelope)
        await session.flush()
        return True
    return False


async def update_cc_envelope_name(
    session: AsyncSession, budget_id: UUID, account_id: UUID, new_name: str
) -> Envelope | None:
    """Update linked CC envelope name to match account name."""
    envelope = await get_cc_envelope_by_account_id(session, budget_id, account_id)
    if envelope:
        envelope.name = new_name
        try:
            await session.flush()
        except IntegrityError as e:
            await session.rollback()
            if "uq_budget_envelope_name" in str(e):
                raise DuplicateEnvelopeNameError(new_name) from e
            raise
        return envelope
    return None


async def create_envelope(
    session: AsyncSession, budget_id: UUID, envelope_in: EnvelopeCreate
) -> Envelope:
    """Create a new envelope for a budget.

    Automatically creates the Unallocated envelope if it doesn't exist.
    """
    # Ensure the unallocated envelope exists (lazy creation)
    await ensure_unallocated_envelope(session, budget_id)

    # Prevent creating an envelope with the reserved name
    if envelope_in.name == UNALLOCATED_ENVELOPE_NAME:
        raise DuplicateEnvelopeNameError(envelope_in.name)

    envelope = Envelope(
        budget_id=budget_id,
        name=envelope_in.name,
        icon=envelope_in.icon,
        description=envelope_in.description,
        envelope_group_id=envelope_in.envelope_group_id,
        sort_order=envelope_in.sort_order,
        is_active=envelope_in.is_active,
        target_balance=envelope_in.target_balance,
    )
    session.add(envelope)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_envelope_name" in str(e):
            raise DuplicateEnvelopeNameError(envelope_in.name) from e
        raise
    return envelope


async def update_envelope(
    session: AsyncSession,
    budget_id: UUID,
    envelope_id: UUID,
    envelope_in: EnvelopeUpdate,
) -> Envelope:
    """Update an existing envelope."""
    envelope = await get_envelope_by_id(session, budget_id, envelope_id)

    # Prevent modifying the unallocated envelope's protected fields
    if envelope.is_unallocated:
        update_data = envelope_in.model_dump(exclude_unset=True)
        if "name" in update_data:
            raise CannotModifyUnallocatedEnvelopeError("rename")
        if "is_active" in update_data and not update_data["is_active"]:
            raise CannotDeactivateUnallocatedEnvelopeError()

    update_data = envelope_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(envelope, field, value)

    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_envelope_name" in str(e):
            raise DuplicateEnvelopeNameError(envelope_in.name or envelope.name) from e
        raise
    return envelope


async def delete_envelope(
    session: AsyncSession, budget_id: UUID, envelope_id: UUID
) -> None:
    """Delete an envelope.

    The envelope's balance automatically becomes unallocated since the
    unallocated balance is calculated dynamically.
    """
    envelope = await get_envelope_by_id(session, budget_id, envelope_id)

    if envelope.is_unallocated:
        raise CannotDeleteUnallocatedEnvelopeError()

    if envelope.linked_account_id is not None:
        raise CannotDeleteCCEnvelopeError()

    await session.delete(envelope)
    await session.flush()


async def adjust_balance(
    session: AsyncSession, budget_id: UUID, envelope_id: UUID, amount: int
) -> Envelope:
    """Adjust an envelope's balance by the given amount (positive or negative).

    This is used by allocation rules to move money between envelopes.
    """
    envelope = await get_envelope_by_id(session, budget_id, envelope_id)
    envelope.current_balance += amount
    await session.flush()
    return envelope


async def get_envelope_budget_summary(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date,
    end_date: date,
) -> dict:
    """Get budget summary with date-filtered allocated/activity amounts.

    Returns a dict with all data needed for EnvelopeBudgetSummaryResponse.

    For each envelope:
    - allocated: Sum of allocations without transaction_id (transfers) in date range
    - activity: Sum of allocations with transaction_id (spending/income) in date range
    - balance: Current envelope balance (not date-filtered)
    """
    from src.envelope_groups.models import EnvelopeGroup

    # Get all active envelopes with their groups
    envelope_result = await session.execute(
        select(
            Envelope.id,
            Envelope.name,
            Envelope.envelope_group_id,
            Envelope.linked_account_id,
            Envelope.icon,
            Envelope.sort_order,
            Envelope.current_balance,
            Envelope.target_balance,
            Envelope.is_unallocated,
            Envelope.is_starred,
            EnvelopeGroup.name.label("group_name"),
            EnvelopeGroup.icon.label("group_icon"),
            EnvelopeGroup.sort_order.label("group_sort_order"),
        )
        .outerjoin(EnvelopeGroup, Envelope.envelope_group_id == EnvelopeGroup.id)
        .where(
            Envelope.budget_id == budget_id,
            Envelope.is_active == True,  # noqa: E712
        )
        .order_by(EnvelopeGroup.sort_order.nulls_last(), Envelope.sort_order)
    )
    envelopes = envelope_result.all()

    # Get activity amounts (all allocations: transactions + transfers) per envelope
    activity_result = await session.execute(
        select(
            Allocation.envelope_id,
            func.coalesce(func.sum(Allocation.amount), 0).label("activity"),
        )
        .where(
            Allocation.budget_id == budget_id,
            Allocation.date >= start_date,
            Allocation.date <= end_date,
        )
        .group_by(Allocation.envelope_id)
    )
    activity_map = {row.envelope_id: row.activity for row in activity_result.all()}

    # Calculate Ready to Assign
    ready_to_assign = await calculate_unallocated_balance(session, budget_id)

    # Build the grouped response
    groups_dict: dict[UUID | None, dict] = {}

    for env in envelopes:
        # Skip unallocated envelope in the groups list
        if env.is_unallocated:
            continue

        group_key = env.envelope_group_id

        # Credit card envelopes use a special key to keep them separate
        is_credit_card = env.linked_account_id is not None
        if is_credit_card:
            group_key = "__credit_cards__"

        if group_key not in groups_dict:
            # Credit card envelopes get their own special group
            if is_credit_card:
                groups_dict[group_key] = {
                    "group_id": None,
                    "group_name": "Credit Cards",
                    "icon": "mdi-credit-card-outline",
                    "sort_order": -1,  # Show at top
                    "envelopes": [],
                    "total_activity": 0,
                    "total_balance": 0,
                }
            else:
                groups_dict[group_key] = {
                    "group_id": group_key,
                    "group_name": env.group_name,
                    "icon": env.group_icon,
                    "sort_order": (
                        env.group_sort_order
                        if env.group_sort_order is not None
                        else 999999
                    ),
                    "envelopes": [],
                    "total_activity": 0,
                    "total_balance": 0,
                }

        activity = activity_map.get(env.id, 0)
        balance = env.current_balance

        groups_dict[group_key]["envelopes"].append(
            {
                "envelope_id": env.id,
                "envelope_name": env.name,
                "envelope_group_id": env.envelope_group_id,
                "linked_account_id": env.linked_account_id,
                "icon": env.icon,
                "sort_order": env.sort_order,
                "is_starred": env.is_starred,
                "activity": activity,
                "balance": balance,
                "target_balance": env.target_balance,
            }
        )
        groups_dict[group_key]["total_activity"] += activity
        groups_dict[group_key]["total_balance"] += balance

    # Sort groups by sort_order
    groups = sorted(groups_dict.values(), key=lambda g: g["sort_order"])

    # Calculate totals
    total_activity = sum(g["total_activity"] for g in groups)
    total_balance = sum(g["total_balance"] for g in groups)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "ready_to_assign": ready_to_assign,
        "total_activity": total_activity,
        "total_balance": total_balance,
        "groups": groups,
    }


async def get_envelope_activity(
    session: AsyncSession,
    budget_id: UUID,
    envelope_id: UUID,
    start_date: date,
    end_date: date,
) -> dict:
    """Get activity details for an envelope in a date range.

    Returns both transaction-based allocations and manual transfers.
    """
    from src.accounts.models import Account
    from src.payees.models import Payee

    # Get envelope info
    envelope = await get_envelope_by_id(session, budget_id, envelope_id)

    items: list[dict] = []

    # Query 1: Transaction-based allocations
    txn_result = await session.execute(
        select(
            Allocation.id.label("allocation_id"),
            Allocation.transaction_id,
            Allocation.date,
            Allocation.amount,
            Transaction.account_id,
            Account.name.label("account_name"),
            Transaction.payee_id,
            Payee.name.label("payee_name"),
            Transaction.memo,
        )
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Payee, Transaction.payee_id == Payee.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.envelope_id == envelope_id,
            Allocation.transaction_id != None,  # noqa: E711
            Allocation.date >= start_date,
            Allocation.date <= end_date,
        )
    )
    for row in txn_result.all():
        items.append(
            {
                "allocation_id": row.allocation_id,
                "transaction_id": row.transaction_id,
                "date": row.date,
                "activity_type": "transaction",
                "account_id": row.account_id,
                "account_name": row.account_name,
                "payee_id": row.payee_id,
                "payee_name": row.payee_name,
                "memo": row.memo,
                "counterpart_envelope_name": None,
                "amount": row.amount,
            }
        )

    # Query 2: Manual transfers (allocations without transaction_id)
    transfer_result = await session.execute(
        select(
            Allocation.id.label("allocation_id"),
            Allocation.date,
            Allocation.amount,
            Allocation.group_id,
            Allocation.memo,
        ).where(
            Allocation.budget_id == budget_id,
            Allocation.envelope_id == envelope_id,
            Allocation.transaction_id == None,  # noqa: E711
            Allocation.date >= start_date,
            Allocation.date <= end_date,
        )
    )
    transfer_rows = transfer_result.all()

    # For each transfer, find the counterpart envelope
    for row in transfer_rows:
        counterpart_name = "Unallocated"  # Default if no counterpart found

        if row.group_id:
            # Find the counterpart allocation with the same group_id
            counterpart_result = await session.execute(
                select(Envelope.name)
                .join(Allocation, Allocation.envelope_id == Envelope.id)
                .where(
                    Allocation.group_id == row.group_id,
                    Allocation.id != row.allocation_id,  # Exclude self
                )
            )
            counterpart_row = counterpart_result.first()
            if counterpart_row:
                counterpart_name = counterpart_row.name

        items.append(
            {
                "allocation_id": row.allocation_id,
                "transaction_id": None,
                "date": row.date,
                "activity_type": "transfer",
                "account_id": None,
                "account_name": None,
                "payee_id": None,
                "payee_name": None,
                "memo": row.memo,
                "counterpart_envelope_name": counterpart_name,
                "amount": row.amount,
            }
        )

    # Sort all items by date desc, allocation_id desc
    items.sort(key=lambda x: (x["date"], x["allocation_id"]), reverse=True)

    total = sum(item["amount"] for item in items)

    return {
        "envelope_id": envelope.id,
        "envelope_name": envelope.name,
        "start_date": start_date,
        "end_date": end_date,
        "items": items,
        "total": total,
    }


async def recalculate_envelope_balances(
    session: AsyncSession, budget_id: UUID
) -> list[dict]:
    """Recalculate and fix envelope balances from allocations.

    First cleans up truly orphaned allocations (where transaction_id points
    to a transaction that no longer exists), then recalculates each
    non-unallocated envelope's balance from its remaining allocations.

    Returns list of envelopes that were corrected.
    """
    # Step 1: Delete truly orphaned allocations — those where transaction_id
    # is set but the referenced transaction row no longer exists.
    # This can happen if a transaction was deleted without proper cascade.
    # We never touch transaction_id=None allocations (envelope transfers,
    # CC payments) as those are legitimate.
    orphaned_result = await session.execute(
        select(Allocation)
        .outerjoin(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.transaction_id.isnot(None),
            Transaction.id.is_(None),
        )
    )
    orphaned = list(orphaned_result.scalars().all())
    for allocation in orphaned:
        await session.delete(allocation)
    if orphaned:
        await session.flush()

    # Step 1.5: Recreate missing CC payment allocations.
    # A previous bad fix deleted CC payment allocations in production.
    # Find CC payment destination transactions that are missing their allocation.
    from uuid import uuid7

    cc_dest_txns_result = await session.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.transaction_type == TransactionType.TRANSFER,
            Transaction.amount > 0,  # Dest side receives payment
            Account.account_type == AccountType.CREDIT_CARD,
        )
    )
    cc_dest_txns = list(cc_dest_txns_result.scalars().all())

    for dest_txn in cc_dest_txns:
        # Find the CC envelope linked to this account
        cc_envelope = await get_cc_envelope_by_account_id(
            session, budget_id, dest_txn.account_id
        )
        if not cc_envelope:
            continue

        # Check if a CC payment allocation already exists for this transaction
        existing_alloc_result = await session.execute(
            select(Allocation.id).where(
                Allocation.budget_id == budget_id,
                Allocation.envelope_id == cc_envelope.id,
                Allocation.transaction_id == dest_txn.id,
            )
        )
        if existing_alloc_result.scalar_one_or_none() is not None:
            continue

        # Missing — recreate the allocation
        alloc = Allocation(
            budget_id=budget_id,
            envelope_id=cc_envelope.id,
            transaction_id=dest_txn.id,
            amount=-dest_txn.amount,
            date=dest_txn.date,
            group_id=uuid7(),
            execution_order=0,
            memo="Credit card payment",
        )
        session.add(alloc)

    await session.flush()

    # Step 2: Recalculate envelope balances from remaining allocations
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget_id,
            Envelope.is_unallocated == False,  # noqa: E712
        )
    )
    envelopes = list(result.scalars().all())
    corrections = []

    for envelope in envelopes:
        alloc_result = await session.execute(
            select(func.coalesce(func.sum(Allocation.amount), 0)).where(
                Allocation.budget_id == budget_id,
                Allocation.envelope_id == envelope.id,
            )
        )
        correct_balance = alloc_result.scalar_one()

        if envelope.current_balance != correct_balance:
            corrections.append(
                {
                    "envelope_id": envelope.id,
                    "envelope_name": envelope.name,
                    "old_balance": envelope.current_balance,
                    "new_balance": correct_balance,
                }
            )
            envelope.current_balance = correct_balance

    await session.flush()

    # Step 3: Fix negative RTA from orphaned one-sided transfers.
    # This happens when income was allocated to Unallocated, distributed to
    # envelopes via one-sided transfers, then the income was deleted.
    rta = await calculate_unallocated_balance(session, budget_id)
    if rta < 0:
        from src.transactions.service import _claw_back_from_unallocated_transfers

        await _claw_back_from_unallocated_transfers(session, budget_id, -rta)

        # Re-check RTA and report as a correction if it changed
        new_rta = await calculate_unallocated_balance(session, budget_id)
        if new_rta != rta:
            corrections.append(
                {
                    "envelope_id": None,
                    "envelope_name": "Unallocated (Ready to Assign)",
                    "old_balance": rta,
                    "new_balance": new_rta,
                }
            )

    return corrections
