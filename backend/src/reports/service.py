from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import Date, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.accounts.models import Account, AccountType
from src.accounts.service import get_account_by_id
from src.allocation_rules.models import AllocationRule
from src.allocations.models import Allocation
from src.envelopes.models import Envelope
from src.envelopes.service import get_envelope_by_id
from src.locations.models import Location
from src.payees.models import Payee
from src.recurring_transactions.models import FrequencyUnit, RecurringTransaction
from src.reports.schemas import (
    AccountBalanceHistoryItem,
    AccountBalanceHistoryResponse,
    AllocationRuleEffectivenessItem,
    AllocationRuleEffectivenessResponse,
    DaysOfRunwayResponse,
    EnvelopeBalanceHistoryItem,
    EnvelopeRunwayItem,
    IncomeVsExpensesPeriod,
    LocationSpendingItem,
    LocationSpendingResponse,
    NetWorthAccountItem,
    NetWorthPeriod,
    NetWorthResponse,
    PayeeAnalysisItem,
    PayeeAnalysisResponse,
    RecurringExpenseCoverageResponse,
    RecurringExpenseItem,
    RunwayTrendDataPoint,
    RunwayTrendResponse,
    SavingsGoalItem,
    SavingsGoalProgressResponse,
    SpendingByCategoryItem,
    SpendingTrendEnvelope,
    SpendingTrendPeriod,
    SpendingTrendsResponse,
    UpcomingExpenseItem,
)
from src.transactions.models import Transaction, TransactionStatus, TransactionType


async def get_spending_by_category(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    envelope_ids: list[UUID] | None = None,
    days_in_period: int = 30,
) -> list[SpendingByCategoryItem]:
    """Aggregate allocations by envelope for date range.

    Returns spending totals grouped by envelope, including:
    - total_spent: Sum of negative allocations (expenses)
    - total_received: Sum of positive allocations (income/refunds)
    - net: Sum of all allocations
    - transaction_count: Number of distinct transactions
    - average_daily/weekly/monthly/yearly: Spending averages based on days_in_period

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Optional start of date range
        end_date: Optional end of date range
        envelope_ids: Optional list of envelope IDs to filter by
        days_in_period: Number of days in the selected period (for average calculations)
    """
    query = (
        select(
            Allocation.envelope_id,
            Envelope.name.label("envelope_name"),
            func.sum(case((Allocation.amount < 0, Allocation.amount), else_=0)).label(
                "total_spent"
            ),
            func.sum(case((Allocation.amount > 0, Allocation.amount), else_=0)).label(
                "total_received"
            ),
            func.sum(Allocation.amount).label("net"),
            # Only count transactions that have negative allocations (actual spending)
            func.count(
                func.distinct(
                    case((Allocation.amount < 0, Allocation.transaction_id), else_=None)
                )
            ).label("transaction_count"),
        )
        .join(Envelope, Allocation.envelope_id == Envelope.id)
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.transaction_id.isnot(None),
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            # Exclude linked credit card envelopes (they duplicate spending tracked elsewhere)
            Envelope.linked_account_id.is_(None),
        )
        .group_by(Allocation.envelope_id, Envelope.name)
        .order_by(Envelope.name)
    )

    # Add date filters
    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

    # Add envelope filter
    if envelope_ids:
        query = query.where(Allocation.envelope_id.in_(envelope_ids))

    result = await session.execute(query)

    items = []
    for row in result.all():
        total_spent = row.total_spent or 0
        # Calculate averages from absolute value of spending
        total_spent_abs = abs(total_spent)
        average_daily = total_spent_abs // days_in_period if days_in_period > 0 else 0

        items.append(
            SpendingByCategoryItem(
                envelope_id=row.envelope_id,
                envelope_name=row.envelope_name,
                total_spent=total_spent,
                total_received=row.total_received or 0,
                net=row.net or 0,
                transaction_count=row.transaction_count or 0,
                average_daily=average_daily,
                average_weekly=average_daily * 7,
                average_monthly=average_daily * 30,
                average_yearly=average_daily * 365,
            )
        )

    return items


async def get_upcoming_expenses(
    session: AsyncSession,
    budget_id: UUID,
    days_ahead: int = 90,
) -> list[UpcomingExpenseItem]:
    """Get scheduled expense transactions with funding status.

    Returns upcoming expenses (scheduled transactions with negative amounts)
    along with their linked envelope information and funding status.

    Funding status:
    - "funded": envelope balance >= expense amount
    - "needs_attention": envelope balance < expense amount
    - "not_linked": no envelope linked to the recurring transaction
    """
    today = date.today()
    horizon = today + timedelta(days=days_ahead)

    query = (
        select(
            Transaction.id.label("transaction_id"),
            Transaction.date,
            Transaction.amount,
            Transaction.memo,
            Payee.name.label("payee_name"),
            RecurringTransaction.envelope_id,
            Envelope.name.label("envelope_name"),
            Envelope.current_balance.label("envelope_balance"),
        )
        .outerjoin(Payee, Transaction.payee_id == Payee.id)
        .outerjoin(
            RecurringTransaction,
            Transaction.recurring_transaction_id == RecurringTransaction.id,
        )
        .outerjoin(Envelope, RecurringTransaction.envelope_id == Envelope.id)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.SCHEDULED,
            Transaction.date >= today,
            Transaction.date <= horizon,
            Transaction.amount < 0,  # Expenses only
        )
        .order_by(Transaction.date)
    )

    result = await session.execute(query)

    items = []
    for row in result.all():
        days_away = (row.date - today).days

        # Determine funding status
        if row.envelope_id is None:
            funding_status = "not_linked"
        elif row.envelope_balance is not None and row.envelope_balance >= abs(
            row.amount
        ):
            funding_status = "funded"
        else:
            funding_status = "needs_attention"

        items.append(
            UpcomingExpenseItem(
                transaction_id=row.transaction_id,
                date=row.date,
                amount=row.amount,
                memo=row.memo,
                payee_name=row.payee_name,
                envelope_id=row.envelope_id,
                envelope_name=row.envelope_name,
                envelope_balance=row.envelope_balance,
                days_away=days_away,
                funding_status=funding_status,
            )
        )

    return items


async def get_envelope_balance_history(
    session: AsyncSession,
    budget_id: UUID,
    envelope_id: UUID,
    start_date: date,
    end_date: date,
) -> tuple[Envelope, list[EnvelopeBalanceHistoryItem]]:
    """Calculate daily envelope balance history from allocations.

    Returns the envelope and a list of daily balance snapshots.
    Uses Transaction.date for allocation timing when available,
    falls back to UUID7 timestamp extraction for envelope transfers.
    """
    # Get envelope (verify exists and belongs to budget)
    envelope = await get_envelope_by_id(session, budget_id, envelope_id)

    # Query allocations with effective date
    # PostgreSQL 18's uuid_extract_timestamp() extracts timestamp from UUID7
    query = (
        select(
            Allocation.amount,
            func.coalesce(
                Transaction.date,
                func.date(func.uuid_extract_timestamp(Allocation.id)),
            ).label("effective_date"),
        )
        .outerjoin(Transaction, Allocation.transaction_id == Transaction.id)
        .where(Allocation.budget_id == budget_id, Allocation.envelope_id == envelope_id)
    )
    result = await session.execute(query)
    rows = result.all()

    # Build dict of date -> total change that day
    daily_changes: dict[date, int] = defaultdict(int)
    for amount, effective_date in rows:
        daily_changes[effective_date] += amount

    # Calculate starting balance (sum of all allocations before start_date)
    balance = sum(amt for d, amt in daily_changes.items() if d < start_date)

    # Generate daily balances for each day in range
    items = []
    current_date = start_date
    while current_date <= end_date:
        balance += daily_changes.get(current_date, 0)
        items.append(EnvelopeBalanceHistoryItem(date=current_date, balance=balance))
        current_date += timedelta(days=1)

    return envelope, items


async def get_income_vs_expenses(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    account_ids: list[UUID] | None = None,
) -> list[IncomeVsExpensesPeriod]:
    """Aggregate income and expenses by month.

    Returns monthly totals for income (positive transactions) and
    expenses (negative transactions). Excludes internal transfers (between
    budget accounts) but includes transfers to/from tracking accounts.
    Only includes posted transactions from budget accounts.

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Optional start of date range
        end_date: Optional end of date range
        account_ids: Optional list of account IDs to filter by

    Returns:
        List of monthly periods with income, expenses, and net totals
    """
    # Aliases for checking linked transaction's account (for transfers)
    LinkedTxn = aliased(Transaction)
    LinkedAccount = aliased(Account)

    # Subquery: does the linked transaction go to a budget account?
    # Used to exclude internal transfers (budget account → budget account)
    linked_to_budget_account = (
        select(1)
        .select_from(LinkedTxn)
        .join(LinkedAccount, LinkedTxn.account_id == LinkedAccount.id)
        .where(
            LinkedTxn.id == Transaction.linked_transaction_id,
            LinkedAccount.include_in_budget == True,  # noqa: E712
        )
        .correlate(Transaction)
        .exists()
    )

    # Use date_trunc to group by month
    period_start = func.date_trunc("month", Transaction.date).cast(Date)

    query = (
        select(
            period_start.label("period_start"),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                "income"
            ),
            func.sum(
                case((Transaction.amount < 0, func.abs(Transaction.amount)), else_=0)
            ).label("expenses"),
            func.sum(Transaction.amount).label("net"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            # Exclude internal transfers (budget → budget), include transfers to/from tracking
            or_(
                Transaction.transaction_type != TransactionType.TRANSFER,
                ~linked_to_budget_account,
            ),
            Account.include_in_budget == True,  # noqa: E712
        )
        .group_by(period_start)
        .order_by(period_start.desc())
    )

    # Add date filters
    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

    # Add account filter
    if account_ids:
        query = query.where(Transaction.account_id.in_(account_ids))

    result = await session.execute(query)

    return [
        IncomeVsExpensesPeriod(
            period_start=row.period_start,
            income=row.income or 0,
            expenses=row.expenses or 0,
            net=row.net or 0,
            transaction_count=row.transaction_count or 0,
        )
        for row in result.all()
    ]


async def get_days_of_runway(
    session: AsyncSession,
    budget_id: UUID,
    calculation_period_days: int = 30,
    exclude_envelope_ids: list[UUID] | None = None,
) -> DaysOfRunwayResponse:
    """Calculate days of runway based on current balances and spending rate.

    Returns how many days each envelope's balance could cover based on
    average daily spending over the calculation period.

    Args:
        session: Database session
        budget_id: Budget to query
        calculation_period_days: Number of days to use for averaging (default 30)
        exclude_envelope_ids: Envelopes to exclude (e.g., savings goals)

    Returns:
        Response with per-envelope and total runway calculations
    """
    today = date.today()
    start_date = today - timedelta(days=calculation_period_days)

    # Get all envelopes with their current balances
    envelope_query = select(Envelope).where(Envelope.budget_id == budget_id)
    if exclude_envelope_ids:
        envelope_query = envelope_query.where(Envelope.id.notin_(exclude_envelope_ids))
    envelope_result = await session.execute(envelope_query)
    envelopes = {e.id: e for e in envelope_result.scalars().all()}

    if not envelopes:
        return DaysOfRunwayResponse(
            calculation_period_days=calculation_period_days,
            start_date=start_date,
            end_date=today,
            total_balance=0,
            total_average_daily_spending=0,
            total_days_of_runway=None,
            items=[],
        )

    # Get total spending per envelope in the calculation period
    # Only count negative allocations (spending) from posted transactions
    spending_query = (
        select(
            Allocation.envelope_id,
            func.sum(func.abs(Allocation.amount)).label("total_spending"),
        )
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.envelope_id.in_(envelopes.keys()),
            Allocation.amount < 0,  # Only spending (negative allocations)
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            Transaction.date >= start_date,
            Transaction.date <= today,
        )
        .group_by(Allocation.envelope_id)
    )
    spending_result = await session.execute(spending_query)
    spending_by_envelope = {
        row.envelope_id: row.total_spending for row in spending_result.all()
    }

    # Build per-envelope runway items
    items = []
    for envelope_id, envelope in envelopes.items():
        total_spending = spending_by_envelope.get(envelope_id, 0)
        avg_daily_spending = (
            total_spending // calculation_period_days if total_spending else 0
        )

        if avg_daily_spending > 0:
            days_of_runway = envelope.current_balance // avg_daily_spending
        else:
            days_of_runway = None  # No spending history

        items.append(
            EnvelopeRunwayItem(
                envelope_id=envelope_id,
                envelope_name=envelope.name,
                current_balance=envelope.current_balance,
                average_daily_spending=avg_daily_spending,
                days_of_runway=days_of_runway,
            )
        )

    # Sort by days of runway (None values at end, then ascending)
    items.sort(key=lambda x: (x.days_of_runway is None, x.days_of_runway or 0))

    # Calculate totals
    total_balance = sum(e.current_balance for e in envelopes.values())
    total_spending = sum(spending_by_envelope.values())
    total_avg_daily_spending = (
        total_spending // calculation_period_days if total_spending else 0
    )

    if total_avg_daily_spending > 0:
        total_days_of_runway = total_balance // total_avg_daily_spending
    else:
        total_days_of_runway = None

    return DaysOfRunwayResponse(
        calculation_period_days=calculation_period_days,
        start_date=start_date,
        end_date=today,
        total_balance=total_balance,
        total_average_daily_spending=total_avg_daily_spending,
        total_days_of_runway=total_days_of_runway,
        items=items,
    )


async def get_allocation_rule_effectiveness(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    active_rules_only: bool = True,
) -> AllocationRuleEffectivenessResponse:
    """Analyze effectiveness of allocation rules.

    Returns metrics on how each allocation rule has performed:
    - Total amount allocated via the rule
    - Number of times triggered (distinct group_ids)
    - How often the cap was hit
    - Average allocation per trigger

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Optional start of date range
        end_date: Optional end of date range
        active_rules_only: Only include active rules (default True)

    Returns:
        Response with per-rule effectiveness metrics
    """
    # Get all rules with their envelope names
    rule_query = (
        select(AllocationRule, Envelope.name.label("envelope_name"))
        .join(Envelope, AllocationRule.envelope_id == Envelope.id)
        .where(AllocationRule.budget_id == budget_id)
        .order_by(AllocationRule.priority)
    )
    if active_rules_only:
        rule_query = rule_query.where(AllocationRule.is_active == True)  # noqa: E712

    rule_result = await session.execute(rule_query)
    rules_with_envelopes = rule_result.all()

    if not rules_with_envelopes:
        return AllocationRuleEffectivenessResponse(
            start_date=start_date,
            end_date=end_date,
            active_rules_only=active_rules_only,
            items=[],
        )

    rule_ids = [r.AllocationRule.id for r in rules_with_envelopes]

    # Build query for allocation aggregates
    # We need: total allocated, count of distinct groups, and per-group amounts to check caps
    alloc_query = (
        select(
            Allocation.allocation_rule_id,
            func.sum(Allocation.amount).label("total_allocated"),
            func.count(func.distinct(Allocation.group_id)).label("times_triggered"),
        )
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.allocation_rule_id.in_(rule_ids),
            Transaction.status == TransactionStatus.POSTED,
        )
        .group_by(Allocation.allocation_rule_id)
    )

    # Add date filters based on transaction date
    if start_date:
        alloc_query = alloc_query.where(Transaction.date >= start_date)
    if end_date:
        alloc_query = alloc_query.where(Transaction.date <= end_date)

    alloc_result = await session.execute(alloc_query)
    alloc_by_rule = {
        row.allocation_rule_id: {
            "total_allocated": row.total_allocated or 0,
            "times_triggered": row.times_triggered or 0,
        }
        for row in alloc_result.all()
    }

    # Build a set of envelope_ids that have an active PERIOD_CAP rule
    from src.allocation_rules.models import AllocationRuleType

    period_cap_envelopes: set[UUID] = set()
    period_cap_amounts: dict[UUID, int] = {}  # envelope_id -> cap amount
    for rule_row in rules_with_envelopes:
        rule = rule_row.AllocationRule
        if rule.rule_type == AllocationRuleType.PERIOD_CAP:
            period_cap_envelopes.add(rule.envelope_id)
            period_cap_amounts[rule.envelope_id] = rule.amount

    # For envelopes with PERIOD_CAP, check if allocations reached the cap
    # by summing allocations in the report's date range and comparing to cap
    period_cap_limited_envelopes: set[UUID] = set()
    if period_cap_envelopes:
        cap_check_query = (
            select(
                Allocation.envelope_id,
                func.sum(Allocation.amount).label("total_allocated"),
            )
            .join(Transaction, Allocation.transaction_id == Transaction.id)
            .where(
                Allocation.budget_id == budget_id,
                Allocation.envelope_id.in_(period_cap_envelopes),
                Allocation.amount > 0,  # Only positive (income) allocations
                Transaction.status == TransactionStatus.POSTED,
            )
            .group_by(Allocation.envelope_id)
        )

        if start_date:
            cap_check_query = cap_check_query.where(Transaction.date >= start_date)
        if end_date:
            cap_check_query = cap_check_query.where(Transaction.date <= end_date)

        cap_check_result = await session.execute(cap_check_query)
        for row in cap_check_result.all():
            cap_amount = period_cap_amounts.get(row.envelope_id, 0)
            if cap_amount > 0 and row.total_allocated >= cap_amount:
                period_cap_limited_envelopes.add(row.envelope_id)

    # Build response items
    items = []
    for rule_row in rules_with_envelopes:
        rule = rule_row.AllocationRule
        envelope_name = rule_row.envelope_name

        alloc_data = alloc_by_rule.get(
            rule.id, {"total_allocated": 0, "times_triggered": 0}
        )
        total_allocated = alloc_data["total_allocated"]
        times_triggered = alloc_data["times_triggered"]

        has_period_cap = rule.envelope_id in period_cap_envelopes
        period_cap_limited = rule.envelope_id in period_cap_limited_envelopes

        average_per_trigger = (
            total_allocated // times_triggered if times_triggered > 0 else 0
        )

        items.append(
            AllocationRuleEffectivenessItem(
                rule_id=rule.id,
                rule_name=rule.name,
                envelope_id=rule.envelope_id,
                envelope_name=envelope_name,
                rule_type=rule.rule_type.value,
                priority=rule.priority,
                configured_amount=rule.amount,
                has_period_cap=has_period_cap,
                total_allocated=total_allocated,
                times_triggered=times_triggered,
                period_cap_limited=period_cap_limited,
                average_per_trigger=average_per_trigger,
            )
        )

    return AllocationRuleEffectivenessResponse(
        start_date=start_date,
        end_date=end_date,
        active_rules_only=active_rules_only,
        items=items,
    )


async def get_spending_trends(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date,
    end_date: date,
    envelope_ids: list[UUID] | None = None,
) -> SpendingTrendsResponse:
    """Get monthly spending trends by envelope.

    Returns spending aggregated by month for each envelope, showing
    how spending patterns change over time.

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Start of date range
        end_date: End of date range
        envelope_ids: Optional list of envelope IDs to include

    Returns:
        Response with per-envelope monthly spending data
    """
    # Use date_trunc to group by month
    period_start = func.date_trunc("month", Transaction.date).cast(Date)

    # Query spending by envelope and month
    query = (
        select(
            Allocation.envelope_id,
            Envelope.name.label("envelope_name"),
            period_start.label("period_start"),
            func.sum(func.abs(Allocation.amount)).label("amount"),
            func.count(func.distinct(Allocation.transaction_id)).label(
                "transaction_count"
            ),
        )
        .join(Envelope, Allocation.envelope_id == Envelope.id)
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.amount < 0,  # Only spending (negative allocations)
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(Allocation.envelope_id, Envelope.name, period_start)
        .order_by(Envelope.name, period_start)
    )

    if envelope_ids:
        query = query.where(Allocation.envelope_id.in_(envelope_ids))

    result = await session.execute(query)
    rows = result.all()

    # Group by envelope
    envelope_data: dict[UUID, dict] = {}
    all_periods: set[date] = set()

    for row in rows:
        if row.envelope_id not in envelope_data:
            envelope_data[row.envelope_id] = {
                "envelope_name": row.envelope_name,
                "periods": {},
            }
        envelope_data[row.envelope_id]["periods"][row.period_start] = {
            "amount": row.amount,
            "transaction_count": row.transaction_count,
        }
        all_periods.add(row.period_start)

    # Calculate the expected periods in the range
    # Generate all months between start_date and end_date
    expected_periods: list[date] = []
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    while current <= end_month:
        expected_periods.append(current)
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    period_count = len(expected_periods)

    # Build response
    envelopes = []
    for envelope_id, data in envelope_data.items():
        periods = []
        total_spent = 0

        for period in expected_periods:
            period_data = data["periods"].get(
                period, {"amount": 0, "transaction_count": 0}
            )
            periods.append(
                SpendingTrendPeriod(
                    period_start=period,
                    amount=period_data["amount"],
                    transaction_count=period_data["transaction_count"],
                )
            )
            total_spent += period_data["amount"]

        average_per_period = total_spent // period_count if period_count > 0 else 0

        envelopes.append(
            SpendingTrendEnvelope(
                envelope_id=envelope_id,
                envelope_name=data["envelope_name"],
                periods=periods,
                total_spent=total_spent,
                average_per_period=average_per_period,
            )
        )

    # Sort envelopes by total spent (descending)
    envelopes.sort(key=lambda x: x.total_spent, reverse=True)

    return SpendingTrendsResponse(
        start_date=start_date,
        end_date=end_date,
        period_count=period_count,
        envelopes=envelopes,
    )


async def get_payee_analysis(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    envelope_ids: list[UUID] | None = None,
    min_total: int | None = None,
) -> PayeeAnalysisResponse:
    """Analyze spending by payee.

    Returns spending aggregated by payee, showing where money goes.

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Optional start of date range
        end_date: Optional end of date range
        envelope_ids: Optional list of envelope IDs to filter by
        min_total: Optional minimum total spending to include

    Returns:
        Response with per-payee spending metrics
    """
    query = (
        select(
            Transaction.payee_id,
            Payee.name.label("payee_name"),
            func.sum(func.abs(Transaction.amount)).label("total_spent"),
            func.count(Transaction.id).label("transaction_count"),
            func.max(Transaction.date).label("last_transaction_date"),
        )
        .join(Payee, Transaction.payee_id == Payee.id)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            Transaction.amount < 0,  # Only expenses
            Transaction.payee_id.isnot(None),
        )
        .group_by(Transaction.payee_id, Payee.name)
    )

    # Add date filters
    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

    # Filter by envelope if specified (requires joining allocations)
    if envelope_ids:
        query = query.join(
            Allocation, Transaction.id == Allocation.transaction_id
        ).where(Allocation.envelope_id.in_(envelope_ids))

    # Filter by minimum total
    if min_total:
        query = query.having(func.sum(func.abs(Transaction.amount)) >= min_total)

    # Order by total spent descending
    query = query.order_by(func.sum(func.abs(Transaction.amount)).desc())

    result = await session.execute(query)

    items = []
    for row in result.all():
        average_amount = (
            row.total_spent // row.transaction_count if row.transaction_count > 0 else 0
        )
        items.append(
            PayeeAnalysisItem(
                payee_id=row.payee_id,
                payee_name=row.payee_name,
                total_spent=row.total_spent,
                transaction_count=row.transaction_count,
                average_amount=average_amount,
                last_transaction_date=row.last_transaction_date,
            )
        )

    return PayeeAnalysisResponse(
        start_date=start_date,
        end_date=end_date,
        items=items,
    )


async def get_location_spending(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    location_ids: list[UUID] | None = None,
    include_no_location: bool = True,
) -> LocationSpendingResponse:
    """Analyze spending by location.

    Returns spending aggregated by location, useful for tracking
    travel expenses or comparing spending across different places.

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Optional start of date range
        end_date: Optional end of date range
        location_ids: Optional list of location IDs to include
        include_no_location: Whether to include transactions without a location

    Returns:
        Response with per-location spending metrics
    """
    # Aliases for checking linked transaction's account (for transfers)
    LinkedTxn = aliased(Transaction)
    LinkedAccount = aliased(Account)

    # Subquery: does the linked transaction go to a budget account?
    # Used to exclude internal transfers (budget account → budget account)
    linked_to_budget_account = (
        select(1)
        .select_from(LinkedTxn)
        .join(LinkedAccount, LinkedTxn.account_id == LinkedAccount.id)
        .where(
            LinkedTxn.id == Transaction.linked_transaction_id,
            LinkedAccount.include_in_budget == True,  # noqa: E712
        )
        .correlate(Transaction)
        .exists()
    )

    # Query for transactions WITH a location
    query_with_location = (
        select(
            Transaction.location_id,
            Location.name.label("location_name"),
            func.sum(func.abs(Transaction.amount)).label("total_spent"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .join(Location, Transaction.location_id == Location.id)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            # Exclude internal transfers (budget → budget), but include transfers to tracking
            or_(
                Transaction.transaction_type != TransactionType.TRANSFER,
                ~linked_to_budget_account,
            ),
            Transaction.amount < 0,  # Only expenses
            Transaction.location_id.isnot(None),
        )
        .group_by(Transaction.location_id, Location.name)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
    )

    # Add date filters
    if start_date:
        query_with_location = query_with_location.where(Transaction.date >= start_date)
    if end_date:
        query_with_location = query_with_location.where(Transaction.date <= end_date)

    # Filter by location if specified
    if location_ids:
        query_with_location = query_with_location.where(
            Transaction.location_id.in_(location_ids)
        )

    result_with_location = await session.execute(query_with_location)

    items = []
    for row in result_with_location.all():
        average_amount = (
            row.total_spent // row.transaction_count if row.transaction_count > 0 else 0
        )
        items.append(
            LocationSpendingItem(
                location_id=row.location_id,
                location_name=row.location_name,
                total_spent=row.total_spent,
                transaction_count=row.transaction_count,
                average_amount=average_amount,
            )
        )

    # Query for transactions WITHOUT a location (if requested)
    if include_no_location and not location_ids:
        query_no_location = select(
            func.sum(func.abs(Transaction.amount)).label("total_spent"),
            func.count(Transaction.id).label("transaction_count"),
        ).where(
            Transaction.budget_id == budget_id,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            # Exclude internal transfers (budget → budget), but include transfers to tracking
            or_(
                Transaction.transaction_type != TransactionType.TRANSFER,
                ~linked_to_budget_account,
            ),
            Transaction.amount < 0,
            Transaction.location_id.is_(None),
        )

        if start_date:
            query_no_location = query_no_location.where(Transaction.date >= start_date)
        if end_date:
            query_no_location = query_no_location.where(Transaction.date <= end_date)

        result_no_location = await session.execute(query_no_location)
        no_location_row = result_no_location.one()

        if no_location_row.transaction_count and no_location_row.transaction_count > 0:
            average_amount = (
                no_location_row.total_spent // no_location_row.transaction_count
            )
            items.append(
                LocationSpendingItem(
                    location_id=None,
                    location_name="(No location)",
                    total_spent=no_location_row.total_spent,
                    transaction_count=no_location_row.transaction_count,
                    average_amount=average_amount,
                )
            )

    return LocationSpendingResponse(
        start_date=start_date,
        end_date=end_date,
        include_no_location=include_no_location,
        items=items,
    )


async def get_account_balance_history(
    session: AsyncSession,
    budget_id: UUID,
    account_id: UUID,
    start_date: date,
    end_date: date,
) -> AccountBalanceHistoryResponse:
    """Calculate daily account balance history from transactions.

    Returns the account and a list of daily balance snapshots.
    Walks through transaction history to calculate balance over time.

    Args:
        session: Database session
        budget_id: Budget to query
        account_id: Account to calculate history for
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Response with account info and daily balances
    """
    # Get account (verify exists and belongs to budget)
    account = await get_account_by_id(session, budget_id, account_id)

    # Query all posted transactions for this account
    query = select(Transaction.date, Transaction.amount).where(
        Transaction.budget_id == budget_id,
        Transaction.account_id == account_id,
        Transaction.status == TransactionStatus.POSTED,
    )
    result = await session.execute(query)
    rows = result.all()

    # Build dict of date -> total change that day
    daily_changes: dict[date, int] = defaultdict(int)
    for txn_date, amount in rows:
        daily_changes[txn_date] += amount

    # Calculate starting balance (sum of all transactions before start_date)
    balance = sum(amt for d, amt in daily_changes.items() if d < start_date)

    # Generate daily balances for each day in range
    items = []
    current_date = start_date
    while current_date <= end_date:
        balance += daily_changes.get(current_date, 0)
        items.append(AccountBalanceHistoryItem(date=current_date, balance=balance))
        current_date += timedelta(days=1)

    return AccountBalanceHistoryResponse(
        account_id=account.id,
        account_name=account.name,
        start_date=start_date,
        end_date=end_date,
        current_balance=account.cleared_balance + account.uncleared_balance,
        items=items,
    )


async def get_savings_goal_progress(
    session: AsyncSession,
    budget_id: UUID,
    calculation_period_days: int = 90,
) -> SavingsGoalProgressResponse:
    """Get progress toward savings goals.

    Returns envelopes that have a target_balance set (savings goals)
    with current progress and estimated time to completion.

    Args:
        session: Database session
        budget_id: Budget to query
        calculation_period_days: Days to use for calculating contribution rate

    Returns:
        Response with per-goal progress metrics
    """
    # Get envelopes with target_balance set (savings goals)
    envelope_query = select(Envelope).where(
        Envelope.budget_id == budget_id,
        Envelope.target_balance.isnot(None),
        Envelope.target_balance > 0,
    )
    envelope_result = await session.execute(envelope_query)
    envelopes = envelope_result.scalars().all()

    if not envelopes:
        return SavingsGoalProgressResponse(
            calculation_period_days=calculation_period_days,
            items=[],
        )

    today = date.today()
    start_date = today - timedelta(days=calculation_period_days)

    # Get positive allocations (contributions) per envelope in the period
    # Use Transaction.date for timing when available
    contribution_query = (
        select(
            Allocation.envelope_id,
            func.sum(Allocation.amount).label("total_contributions"),
        )
        .outerjoin(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Allocation.envelope_id.in_([e.id for e in envelopes]),
            Allocation.amount > 0,  # Only positive allocations (contributions)
        )
        .where(
            func.coalesce(Transaction.date, func.current_date()) >= start_date,
            func.coalesce(Transaction.date, func.current_date()) <= today,
        )
        .group_by(Allocation.envelope_id)
    )

    contribution_result = await session.execute(contribution_query)
    contributions_by_envelope = {
        row.envelope_id: row.total_contributions for row in contribution_result.all()
    }

    # Build response items
    items = []
    months_in_period = calculation_period_days / 30.0

    for envelope in envelopes:
        target = envelope.target_balance
        current = envelope.current_balance
        remaining = max(0, target - current)
        progress_percent = min(100, (current * 100) // target) if target > 0 else 0

        total_contributions = int(contributions_by_envelope.get(envelope.id, 0) or 0)
        monthly_rate = (
            int(total_contributions / months_in_period) if months_in_period > 0 else 0
        )

        # Calculate estimated months to goal
        if current >= target:
            estimated_months = 0  # Already reached
        elif monthly_rate > 0:
            estimated_months = (
                remaining + monthly_rate - 1
            ) // monthly_rate  # Round up
        else:
            estimated_months = None  # No contributions, can't estimate

        items.append(
            SavingsGoalItem(
                envelope_id=envelope.id,
                envelope_name=envelope.name,
                target_balance=target,
                current_balance=current,
                progress_percent=progress_percent,
                remaining=remaining,
                monthly_contribution_rate=monthly_rate,
                estimated_months_to_goal=estimated_months,
            )
        )

    # Sort by progress percent descending (closest to goal first)
    items.sort(key=lambda x: x.progress_percent, reverse=True)

    return SavingsGoalProgressResponse(
        calculation_period_days=calculation_period_days,
        items=items,
    )


async def get_recurring_expense_coverage(
    session: AsyncSession,
    budget_id: UUID,
) -> RecurringExpenseCoverageResponse:
    """Get coverage status of recurring expenses.

    Returns a summary of all active recurring expenses and their
    funding status based on linked envelope balances.

    Funding status:
    - "funded": envelope balance >= expense amount
    - "partially_funded": envelope balance < expense amount
    - "not_linked": no envelope linked

    Args:
        session: Database session
        budget_id: Budget to query

    Returns:
        Response with summary counts and per-expense details
    """
    today = date.today()

    # Get all active recurring expenses (negative amounts)
    query = (
        select(
            RecurringTransaction.id,
            RecurringTransaction.amount,
            RecurringTransaction.frequency_value,
            RecurringTransaction.frequency_unit,
            RecurringTransaction.next_occurrence_date,
            RecurringTransaction.envelope_id,
            Payee.name.label("payee_name"),
            Envelope.name.label("envelope_name"),
            Envelope.current_balance.label("envelope_balance"),
        )
        .outerjoin(Payee, RecurringTransaction.payee_id == Payee.id)
        .outerjoin(Envelope, RecurringTransaction.envelope_id == Envelope.id)
        .where(
            RecurringTransaction.budget_id == budget_id,
            RecurringTransaction.is_active == True,  # noqa: E712
            RecurringTransaction.amount < 0,  # Expenses only
        )
        .order_by(RecurringTransaction.next_occurrence_date)
    )

    result = await session.execute(query)
    rows = result.all()

    # Build items and calculate counts
    items = []
    fully_funded_count = 0
    partially_funded_count = 0
    not_linked_count = 0
    total_shortfall = 0

    for row in rows:
        expense_amount = abs(row.amount)

        # Format frequency string
        unit = row.frequency_unit
        value = row.frequency_value
        if unit == FrequencyUnit.DAYS:
            unit_str = "day" if value == 1 else "days"
        elif unit == FrequencyUnit.WEEKS:
            unit_str = "week" if value == 1 else "weeks"
        elif unit == FrequencyUnit.MONTHS:
            unit_str = "month" if value == 1 else "months"
        else:  # YEARS
            unit_str = "year" if value == 1 else "years"
        frequency = f"Every {value} {unit_str}"

        # Determine funding status
        if row.envelope_id is None:
            funding_status = "not_linked"
            shortfall = expense_amount
            not_linked_count += 1
            total_shortfall += shortfall
        elif (
            row.envelope_balance is not None and row.envelope_balance >= expense_amount
        ):
            funding_status = "funded"
            shortfall = 0
            fully_funded_count += 1
        else:
            funding_status = "partially_funded"
            current_balance = row.envelope_balance or 0
            shortfall = expense_amount - current_balance
            partially_funded_count += 1
            total_shortfall += shortfall

        items.append(
            RecurringExpenseItem(
                recurring_transaction_id=row.id,
                payee_name=row.payee_name,
                amount=row.amount,  # Keep negative for expenses
                frequency=frequency,
                next_occurrence=row.next_occurrence_date,
                envelope_id=row.envelope_id,
                envelope_name=row.envelope_name,
                envelope_balance=row.envelope_balance,
                funding_status=funding_status,
                shortfall=shortfall,
            )
        )

    return RecurringExpenseCoverageResponse(
        as_of_date=today,
        total_recurring=len(items),
        fully_funded_count=fully_funded_count,
        partially_funded_count=partially_funded_count,
        not_linked_count=not_linked_count,
        total_shortfall=total_shortfall,
        items=items,
    )


async def get_runway_trend(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date,
    end_date: date,
    lookback_days: int = 30,
    envelope_id: UUID | None = None,
) -> RunwayTrendResponse:
    """Calculate days of runway over time as a trend.

    For each weekly snapshot within the date range, calculates the balance
    and average daily spending rate to determine runway at that point in time.

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Start of trend period
        end_date: End of trend period
        lookback_days: Days to use for spending rate calculation (default 30)
        envelope_id: Optional specific envelope (None for overall)

    Returns:
        Response with data points showing runway over time
    """
    # Get envelope info if specific envelope requested
    envelope_name: str | None = None
    if envelope_id:
        envelope = await get_envelope_by_id(session, budget_id, envelope_id)
        envelope_name = envelope.name

    # Generate weekly snapshot dates
    snapshot_dates: list[date] = []
    current = start_date
    while current <= end_date:
        snapshot_dates.append(current)
        current += timedelta(days=7)

    # Always include end_date if not already included
    if snapshot_dates[-1] != end_date:
        snapshot_dates.append(end_date)

    if not snapshot_dates:
        return RunwayTrendResponse(
            start_date=start_date,
            end_date=end_date,
            lookback_days=lookback_days,
            envelope_id=envelope_id,
            envelope_name=envelope_name,
            data_points=[],
        )

    # Get all allocations for the budget (or specific envelope) up to end_date
    # We need allocations from (start_date - lookback_days) to end_date
    earliest_date = start_date - timedelta(days=lookback_days)

    allocation_query = (
        select(
            Allocation.envelope_id,
            Transaction.date,
            Allocation.amount,
        )
        .join(Transaction, Allocation.transaction_id == Transaction.id)
        .where(
            Allocation.budget_id == budget_id,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.transaction_type != TransactionType.ADJUSTMENT,
            Transaction.date >= earliest_date,
            Transaction.date <= end_date,
        )
    )

    if envelope_id:
        allocation_query = allocation_query.where(Allocation.envelope_id == envelope_id)

    result = await session.execute(allocation_query)
    allocations = result.all()

    # Build dict of (envelope_id, date) -> amounts for quick lookup
    # and track all envelope_ids we see
    allocation_data: dict[tuple[UUID, date], list[int]] = defaultdict(list)
    envelope_ids: set[UUID] = set()
    for alloc in allocations:
        allocation_data[(alloc.envelope_id, alloc.date)].append(alloc.amount)
        envelope_ids.add(alloc.envelope_id)

    # If no envelope specified, also need allocations before earliest_date for balance
    # Query sum of all allocations before earliest_date for starting balance
    if envelope_id:
        balance_before_query = (
            select(func.coalesce(func.sum(Allocation.amount), 0))
            .select_from(Allocation)
            .outerjoin(Transaction, Allocation.transaction_id == Transaction.id)
            .where(
                Allocation.budget_id == budget_id,
                Allocation.envelope_id == envelope_id,
            )
            .where(
                (Transaction.id.is_(None))
                | (
                    (Transaction.status == TransactionStatus.POSTED)
                    & (Transaction.date < earliest_date)
                )
            )
        )
    else:
        balance_before_query = (
            select(func.coalesce(func.sum(Allocation.amount), 0))
            .select_from(Allocation)
            .outerjoin(Transaction, Allocation.transaction_id == Transaction.id)
            .where(Allocation.budget_id == budget_id)
            .where(
                (Transaction.id.is_(None))
                | (
                    (Transaction.status == TransactionStatus.POSTED)
                    & (Transaction.date < earliest_date)
                )
            )
        )

    balance_result = await session.execute(balance_before_query)
    starting_balance = balance_result.scalar() or 0

    # Calculate data points for each snapshot date
    data_points: list[RunwayTrendDataPoint] = []

    # Track running balance day by day from earliest_date
    running_balance = starting_balance
    current_date = earliest_date

    # Pre-calculate daily balance changes
    daily_balance_changes: dict[date, int] = defaultdict(int)
    daily_spending: dict[date, int] = defaultdict(int)  # Absolute value of negative

    for (env_id, txn_date), amounts in allocation_data.items():
        if envelope_id is None or env_id == envelope_id:
            for amount in amounts:
                daily_balance_changes[txn_date] += amount
                if amount < 0:
                    daily_spending[txn_date] += abs(amount)

    # Build balance at each date and spending in lookback window
    balance_at_date: dict[date, int] = {}
    current_date = earliest_date
    while current_date <= end_date:
        running_balance += daily_balance_changes.get(current_date, 0)
        balance_at_date[current_date] = running_balance
        current_date += timedelta(days=1)

    # Now calculate runway for each snapshot date
    for snapshot in snapshot_dates:
        # Balance at this snapshot
        balance = balance_at_date.get(snapshot, 0)

        # Spending in lookback period (snapshot - lookback_days to snapshot)
        lookback_start = snapshot - timedelta(days=lookback_days)
        total_spending = 0
        check_date = lookback_start
        while check_date <= snapshot:
            total_spending += daily_spending.get(check_date, 0)
            check_date += timedelta(days=1)

        # Calculate average daily spending and runway
        avg_daily_spending = total_spending // lookback_days if total_spending else 0

        if avg_daily_spending > 0:
            days_of_runway = balance // avg_daily_spending
        else:
            days_of_runway = None

        data_points.append(
            RunwayTrendDataPoint(
                date=snapshot,
                balance=balance,
                average_daily_spending=avg_daily_spending,
                days_of_runway=days_of_runway,
            )
        )

    return RunwayTrendResponse(
        start_date=start_date,
        end_date=end_date,
        lookback_days=lookback_days,
        envelope_id=envelope_id,
        envelope_name=envelope_name,
        data_points=data_points,
    )


# Liability account types (balances typically negative, shown as positive liabilities)
LIABILITY_TYPES = {AccountType.CREDIT_CARD, AccountType.LOAN}


async def get_net_worth(
    session: AsyncSession,
    budget_id: UUID,
    start_date: date | None,
    end_date: date,
) -> NetWorthResponse:
    """Calculate net worth history aggregated by month.

    Returns monthly net worth snapshots showing:
    - Total assets (checking, savings, cash, investments, etc.)
    - Total liabilities (credit cards, loans)
    - Net worth (assets - liabilities)
    - Per-account breakdown for drill-down capability

    All accounts are included regardless of include_in_budget setting.
    Only active accounts are included.

    Args:
        session: Database session
        budget_id: Budget to query
        start_date: Start of date range. If None, uses earliest transaction date.
        end_date: End of date range

    Returns:
        Response with monthly net worth data and per-account breakdown
    """
    # Get all active accounts for the budget (include ALL, not just budget accounts)
    account_query = select(Account).where(
        Account.budget_id == budget_id,
        Account.is_active == True,  # noqa: E712
    )
    account_result = await session.execute(account_query)
    accounts = {a.id: a for a in account_result.scalars().all()}

    if not accounts:
        return NetWorthResponse(
            start_date=start_date or end_date,
            end_date=end_date,
            current_net_worth=0,
            current_total_assets=0,
            current_total_liabilities=0,
            net_worth_change=0,
            periods=[],
        )

    # If start_date is None, find earliest transaction date for this budget
    if start_date is None:
        earliest_query = select(func.min(Transaction.date)).where(
            Transaction.budget_id == budget_id,
            Transaction.account_id.in_(accounts.keys()),
            Transaction.status == TransactionStatus.POSTED,
        )
        earliest_result = await session.execute(earliest_query)
        earliest_date = earliest_result.scalar()
        # Default to 1 year ago if no transactions exist
        start_date = earliest_date or (end_date - timedelta(days=365))

    # Query all posted transactions for these accounts
    txn_query = select(
        Transaction.account_id, Transaction.date, Transaction.amount
    ).where(
        Transaction.budget_id == budget_id,
        Transaction.account_id.in_(accounts.keys()),
        Transaction.status == TransactionStatus.POSTED,
    )
    txn_result = await session.execute(txn_query)
    transactions = txn_result.all()

    # Build dict of (account_id, date) -> daily_change
    # and calculate current balances directly from transactions
    # (this ensures consistency - balance = sum of all POSTED transactions)
    daily_changes: dict[tuple[UUID, date], int] = defaultdict(int)
    current_balances: dict[UUID, int] = dict.fromkeys(accounts, 0)
    for account_id, txn_date, amount in transactions:
        daily_changes[(account_id, txn_date)] += amount
        current_balances[account_id] += amount

    # Generate month-end dates for the range
    month_ends: list[date] = []
    current = end_date.replace(day=1)  # First of end month
    start_first = start_date.replace(day=1)

    while current >= start_first:
        # Get last day of month
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        month_end = next_month - timedelta(days=1)

        # Cap at end_date if month_end is after end_date
        if month_end > end_date:
            month_end = end_date

        month_ends.append(month_end)

        # Move to previous month
        current = (current - timedelta(days=1)).replace(day=1)

    month_ends.reverse()  # Chronological order (oldest first)

    # Calculate balance at each month-end for each account
    # Work backwards from current balance: subtract transactions that occurred after that month-end
    periods: list[NetWorthPeriod] = []

    for month_end in month_ends:
        account_items: list[NetWorthAccountItem] = []
        total_assets = 0
        total_liabilities = 0

        for account_id, account in accounts.items():
            # Calculate balance at month_end by subtracting transactions after that date
            current_balance = current_balances[account_id]

            # Sum of transactions AFTER this month_end
            future_changes = sum(
                amt
                for (acc_id, txn_date), amt in daily_changes.items()
                if acc_id == account_id and txn_date > month_end
            )

            # Balance at month_end = current - future changes
            balance_at_month_end = current_balance - future_changes

            is_liability = account.account_type in LIABILITY_TYPES

            account_items.append(
                NetWorthAccountItem(
                    account_id=account_id,
                    account_name=account.name,
                    account_type=account.account_type.value,
                    is_liability=is_liability,
                    balance=balance_at_month_end,
                )
            )

            if is_liability:
                # Liabilities are typically negative balances, store as positive
                total_liabilities += abs(balance_at_month_end)
            else:
                total_assets += balance_at_month_end

        # Sort accounts by absolute balance (highest first), then by name
        account_items.sort(key=lambda x: (-abs(x.balance), x.account_name))

        # First day of the month for period_start
        period_start = month_end.replace(day=1)

        periods.append(
            NetWorthPeriod(
                period_start=period_start,
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                net_worth=total_assets - total_liabilities,
                accounts=account_items,
            )
        )

    # Calculate current totals
    current_total_assets = 0
    current_total_liabilities = 0

    for account_id, account in accounts.items():
        balance = current_balances[account_id]
        if account.account_type in LIABILITY_TYPES:
            current_total_liabilities += abs(balance)
        else:
            current_total_assets += balance

    current_net_worth = current_total_assets - current_total_liabilities

    # Calculate net worth change (last period - first period)
    net_worth_change = 0
    if len(periods) >= 2:
        net_worth_change = periods[-1].net_worth - periods[0].net_worth
    elif len(periods) == 1:
        net_worth_change = 0

    return NetWorthResponse(
        start_date=start_date,
        end_date=end_date,
        current_net_worth=current_net_worth,
        current_total_assets=current_total_assets,
        current_total_liabilities=current_total_liabilities,
        net_worth_change=net_worth_change,
        periods=periods,
    )
