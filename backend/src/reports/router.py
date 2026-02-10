from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.budgets.dependencies import BudgetContext, BudgetSecurity
from src.budgets.scopes import BudgetScope
from src.database import get_async_session
from src.reports import service
from src.reports.schemas import (
    AccountBalanceHistoryResponse,
    AllocationRuleEffectivenessResponse,
    DaysOfRunwayResponse,
    EnvelopeBalanceHistoryResponse,
    IncomeVsExpensesResponse,
    LocationSpendingResponse,
    NetWorthResponse,
    PayeeAnalysisResponse,
    RecurringExpenseCoverageResponse,
    RunwayTrendResponse,
    SavingsGoalProgressResponse,
    SpendingByCategoryResponse,
    SpendingTrendsResponse,
    UpcomingExpensesResponse,
)

router = APIRouter(prefix="/budgets/{budget_id}/reports", tags=["reports"])


@router.get(
    "/spending-by-category",
    response_model=SpendingByCategoryResponse,
)
async def get_spending_by_category(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    envelope_id: Annotated[list[UUID] | None, Query()] = None,
) -> SpendingByCategoryResponse:
    """Get spending aggregated by envelope (category) for a date range.

    Returns total spent, total received, and net amounts per envelope,
    along with transaction counts and average spending rates.
    Only includes posted transactions.
    """
    # Calculate days in period for average calculations (default 30 if no range)
    days_in_period = (end_date - start_date).days + 1 if start_date and end_date else 30

    items = await service.get_spending_by_category(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        envelope_ids=envelope_id,
        days_in_period=days_in_period,
    )
    return SpendingByCategoryResponse(
        start_date=start_date,
        end_date=end_date,
        days_in_period=days_in_period,
        items=items,
    )


@router.get(
    "/upcoming-expenses",
    response_model=UpcomingExpensesResponse,
)
async def get_upcoming_expenses(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    days_ahead: Annotated[int, Query(ge=1, le=365)] = 90,
) -> UpcomingExpensesResponse:
    """Get upcoming scheduled expenses with funding status.

    Returns scheduled expense transactions within the specified horizon,
    along with their linked envelope information and funding status.

    Funding status indicates whether the linked envelope has sufficient
    balance to cover the expense:
    - "funded": envelope balance >= expense amount
    - "needs_attention": envelope balance < expense amount
    - "not_linked": no envelope linked to the recurring transaction
    """
    items = await service.get_upcoming_expenses(
        session,
        ctx.budget.id,
        days_ahead=days_ahead,
    )
    return UpcomingExpensesResponse(
        as_of_date=date.today(),
        items=items,
    )


@router.get(
    "/envelope-balance-history",
    response_model=EnvelopeBalanceHistoryResponse,
)
async def get_envelope_balance_history(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    envelope_id: Annotated[UUID, Query()],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> EnvelopeBalanceHistoryResponse:
    """Get daily envelope balance history for a date range.

    Calculates historical balances by walking through all allocations
    for the specified envelope. Returns one data point per day showing
    the end-of-day balance.

    Useful for visualizing balance trends and understanding whether
    an envelope is building a buffer or trending down over time.
    """
    envelope, items = await service.get_envelope_balance_history(
        session,
        ctx.budget.id,
        envelope_id,
        start_date,
        end_date,
    )
    return EnvelopeBalanceHistoryResponse(
        envelope_id=envelope.id,
        envelope_name=envelope.name,
        start_date=start_date,
        end_date=end_date,
        current_balance=envelope.current_balance,
        target_balance=envelope.target_balance,
        items=items,
    )


@router.get(
    "/income-vs-expenses",
    response_model=IncomeVsExpensesResponse,
)
async def get_income_vs_expenses(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    account_id: Annotated[list[UUID] | None, Query()] = None,
) -> IncomeVsExpensesResponse:
    """Get income vs expenses aggregated by month.

    Returns monthly totals for income and expenses, useful for
    understanding cash flow and whether you're spending more than
    you earn.

    Only includes posted transactions from budget accounts.
    Excludes transfers (which are not real income/expenses).
    """
    periods = await service.get_income_vs_expenses(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        account_ids=account_id,
    )

    # Calculate totals
    total_income = sum(p.income for p in periods)
    total_expenses = sum(p.expenses for p in periods)
    total_net = sum(p.net for p in periods)

    return IncomeVsExpensesResponse(
        start_date=start_date,
        end_date=end_date,
        total_income=total_income,
        total_expenses=total_expenses,
        total_net=total_net,
        periods=periods,
    )


@router.get(
    "/days-of-runway",
    response_model=DaysOfRunwayResponse,
)
async def get_days_of_runway(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    calculation_period_days: Annotated[int, Query(ge=7, le=365)] = 30,
    exclude_envelope_id: Annotated[list[UUID] | None, Query()] = None,
) -> DaysOfRunwayResponse:
    """Calculate days of runway based on current balances and spending rate.

    Returns how many days each envelope's balance could cover expenses
    based on average daily spending over the calculation period.

    Useful for understanding:
    - Which envelopes are running low
    - Overall financial runway
    - Planning for upcoming expenses

    The calculation uses only posted transactions with negative amounts
    (actual spending) from the calculation period.
    """
    return await service.get_days_of_runway(
        session,
        ctx.budget.id,
        calculation_period_days=calculation_period_days,
        exclude_envelope_ids=exclude_envelope_id,
    )


@router.get(
    "/allocation-rule-effectiveness",
    response_model=AllocationRuleEffectivenessResponse,
)
async def get_allocation_rule_effectiveness(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    active_only: Annotated[bool, Query()] = True,
) -> AllocationRuleEffectivenessResponse:
    """Analyze effectiveness of allocation rules.

    Returns metrics on how each allocation rule has performed:
    - Total amount allocated via the rule
    - Number of times triggered
    - How often the cap was hit (if applicable)
    - Average allocation per trigger

    Useful for understanding:
    - Which rules are being utilized
    - Whether caps are set appropriately
    - If low-priority rules are receiving funds
    """
    return await service.get_allocation_rule_effectiveness(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        active_rules_only=active_only,
    )


@router.get(
    "/spending-trends",
    response_model=SpendingTrendsResponse,
)
async def get_spending_trends(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    envelope_id: Annotated[list[UUID] | None, Query()] = None,
) -> SpendingTrendsResponse:
    """Get monthly spending trends by envelope.

    Returns spending aggregated by month for each envelope over the
    specified date range. Useful for identifying:
    - Spending increases over time (lifestyle creep)
    - Seasonal patterns
    - Anomalies or one-time large purchases

    Each envelope shows spending per month with totals and averages.
    Envelopes are sorted by total spending (highest first).
    """
    return await service.get_spending_trends(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        envelope_ids=envelope_id,
    )


@router.get(
    "/payee-analysis",
    response_model=PayeeAnalysisResponse,
)
async def get_payee_analysis(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    envelope_id: Annotated[list[UUID] | None, Query()] = None,
    min_total: Annotated[int | None, Query(ge=0)] = None,
) -> PayeeAnalysisResponse:
    """Analyze spending by payee.

    Returns spending aggregated by payee, showing where your money
    actually goes. Useful for identifying:
    - Top merchants by spending
    - Frequency of purchases at each payee
    - Recent activity per payee

    Results are sorted by total spending (highest first).
    """
    return await service.get_payee_analysis(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        envelope_ids=envelope_id,
        min_total=min_total,
    )


@router.get(
    "/location-spending",
    response_model=LocationSpendingResponse,
)
async def get_location_spending(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    location_id: Annotated[list[UUID] | None, Query()] = None,
    include_no_location: Annotated[bool, Query()] = True,
) -> LocationSpendingResponse:
    """Analyze spending by location.

    Returns spending aggregated by location, useful for:
    - Tracking travel expenses
    - Comparing cost of living between locations
    - Identifying location-based spending patterns

    Results are sorted by total spending (highest first).
    Optionally includes a "(No location)" entry for transactions
    without a location assigned.
    """
    return await service.get_location_spending(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        location_ids=location_id,
        include_no_location=include_no_location,
    )


@router.get(
    "/account-balance-history",
    response_model=AccountBalanceHistoryResponse,
)
async def get_account_balance_history(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    account_id: Annotated[UUID, Query()],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> AccountBalanceHistoryResponse:
    """Get daily account balance history for a date range.

    Calculates historical balances by walking through all transactions
    for the specified account. Returns one data point per day showing
    the end-of-day balance.

    Useful for:
    - Visualizing cash flow patterns
    - Verifying reconciliation
    - Tracking debt paydown progress
    """
    return await service.get_account_balance_history(
        session,
        ctx.budget.id,
        account_id,
        start_date,
        end_date,
    )


@router.get(
    "/savings-goal-progress",
    response_model=SavingsGoalProgressResponse,
)
async def get_savings_goal_progress(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    calculation_period_days: Annotated[int, Query(ge=30, le=365)] = 90,
) -> SavingsGoalProgressResponse:
    """Get progress toward savings goals.

    Returns envelopes that have a target_balance set with:
    - Current progress percentage
    - Monthly contribution rate (based on recent allocations)
    - Estimated months until goal is reached

    Useful for tracking progress on:
    - Emergency fund goals
    - Vacation savings
    - Large purchase savings
    """
    return await service.get_savings_goal_progress(
        session,
        ctx.budget.id,
        calculation_period_days=calculation_period_days,
    )


@router.get(
    "/recurring-expense-coverage",
    response_model=RecurringExpenseCoverageResponse,
)
async def get_recurring_expense_coverage(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RecurringExpenseCoverageResponse:
    """Get coverage status of recurring expenses.

    Returns a summary of all active recurring expenses and their
    funding status based on linked envelope balances:
    - Fully funded: envelope balance >= expense amount
    - Partially funded: envelope balance < expense amount
    - Not linked: no envelope assigned

    Useful for ensuring all bills are covered before the next occurrence.
    """
    return await service.get_recurring_expense_coverage(
        session,
        ctx.budget.id,
    )


@router.get(
    "/runway-trend",
    response_model=RunwayTrendResponse,
)
async def get_runway_trend(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
    lookback_days: Annotated[int, Query(ge=7, le=365)] = 30,
    envelope_id: Annotated[UUID | None, Query()] = None,
) -> RunwayTrendResponse:
    """Get days of runway trend over time.

    Calculates days of runway at weekly intervals within the date range,
    showing how financial runway has changed over time.

    For each snapshot point:
    - Balance: Sum of all allocations up to that date
    - Daily spending rate: Average based on lookback period before that date
    - Days of runway: Balance / daily rate

    Args:
        start_date: Start of trend period
        end_date: End of trend period
        lookback_days: Days to use for spending rate calculation (7-365, default 30)
        envelope_id: Optional specific envelope (omit for overall)

    Useful for:
    - Tracking if financial health is improving or declining
    - Identifying trends in spending behavior
    - Visualizing impact of budget changes over time
    """
    return await service.get_runway_trend(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
        lookback_days=lookback_days,
        envelope_id=envelope_id,
    )


@router.get(
    "/net-worth",
    response_model=NetWorthResponse,
)
async def get_net_worth(
    ctx: Annotated[
        BudgetContext,
        Security(BudgetSecurity(), scopes=[BudgetScope.TRANSACTIONS_READ]),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    end_date: Annotated[date, Query()],
    start_date: Annotated[date | None, Query()] = None,
) -> NetWorthResponse:
    """Get net worth history aggregated by month.

    Returns monthly net worth snapshots showing:
    - Total assets (checking, savings, cash, investments, etc.)
    - Total liabilities (credit cards, loans)
    - Net worth (assets - liabilities)
    - Per-account breakdown for drill-down capability

    All accounts are included regardless of the include_in_budget setting.
    Only active accounts are included.

    Args:
        end_date: End of date range
        start_date: Start of date range. If not provided, uses earliest transaction date.

    Useful for:
    - Tracking overall financial health over time
    - Understanding asset vs liability composition
    - Visualizing net worth growth or decline
    """
    return await service.get_net_worth(
        session,
        ctx.budget.id,
        start_date=start_date,
        end_date=end_date,
    )
