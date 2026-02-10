from datetime import date
from uuid import UUID

from pydantic import BaseModel


class SpendingByCategoryItem(BaseModel):
    envelope_id: UUID
    envelope_name: str
    total_spent: int  # Negative cents (expenses)
    total_received: int  # Positive cents (income/refunds)
    net: int  # total_spent + total_received
    transaction_count: int
    # Average spending based on days_in_period (positive cents)
    average_daily: int
    average_weekly: int
    average_monthly: int
    average_yearly: int

    model_config = {"from_attributes": True}


class SpendingByCategoryResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    days_in_period: int  # Number of days in the selected date range
    items: list[SpendingByCategoryItem]


class UpcomingExpenseItem(BaseModel):
    transaction_id: UUID
    date: date
    amount: int  # In cents (negative for expenses)
    memo: str | None
    payee_name: str | None
    envelope_id: UUID | None
    envelope_name: str | None
    envelope_balance: int | None  # Current balance if envelope linked
    days_away: int
    funding_status: str  # "funded", "needs_attention", "not_linked"

    model_config = {"from_attributes": True}


class UpcomingExpensesResponse(BaseModel):
    as_of_date: date
    items: list[UpcomingExpenseItem]


class EnvelopeBalanceHistoryItem(BaseModel):
    date: date
    balance: int  # Balance at end of day, in cents


class EnvelopeBalanceHistoryResponse(BaseModel):
    envelope_id: UUID
    envelope_name: str
    start_date: date
    end_date: date
    current_balance: int  # Current balance for reference
    target_balance: int | None  # Target/cap for reference line
    items: list[EnvelopeBalanceHistoryItem]


class IncomeVsExpensesPeriod(BaseModel):
    period_start: date  # First day of the period (e.g., 2024-01-01 for January)
    income: int  # Positive cents (income transactions)
    expenses: int  # Positive cents (absolute value of expense transactions)
    net: int  # income - expenses (positive = surplus, negative = deficit)
    transaction_count: int


class IncomeVsExpensesResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    total_income: int
    total_expenses: int
    total_net: int
    periods: list[IncomeVsExpensesPeriod]


class EnvelopeRunwayItem(BaseModel):
    envelope_id: UUID
    envelope_name: str
    current_balance: int  # Current balance in cents
    average_daily_spending: int  # Positive cents per day (0 if no spending)
    days_of_runway: int | None  # None if no spending history


class DaysOfRunwayResponse(BaseModel):
    calculation_period_days: int  # Number of days used for averaging (30, 60, 90)
    start_date: date  # Start of calculation period
    end_date: date  # End of calculation period (typically today)
    total_balance: int  # Sum of all envelope balances
    total_average_daily_spending: int  # Combined daily spending rate
    total_days_of_runway: int | None  # None if no spending history
    items: list[EnvelopeRunwayItem]


class RunwayTrendDataPoint(BaseModel):
    date: date  # The snapshot date
    balance: int  # Balance at this date in cents
    average_daily_spending: int  # Daily spending rate based on lookback period
    days_of_runway: int | None  # None if no spending in lookback period


class RunwayTrendResponse(BaseModel):
    start_date: date  # Start of the trend period
    end_date: date  # End of the trend period
    lookback_days: int  # Days used for spending rate calculation at each point
    envelope_id: UUID | None  # None for overall trend, UUID for specific envelope
    envelope_name: str | None  # None for overall trend
    data_points: list[RunwayTrendDataPoint]


class AllocationRuleEffectivenessItem(BaseModel):
    rule_id: UUID
    rule_name: str | None
    envelope_id: UUID
    envelope_name: str
    rule_type: str  # FIXED, PERCENTAGE, FILL_TO_TARGET, REMAINDER, PERIOD_CAP
    priority: int
    configured_amount: int  # The amount/percentage configured on the rule
    has_period_cap: bool  # Whether envelope has an active PERIOD_CAP rule
    total_allocated: int  # Total cents allocated via this rule
    times_triggered: int  # Number of distinct group_ids (trigger events)
    period_cap_limited: bool  # Whether allocations hit the period cap
    average_per_trigger: int  # Average allocation per trigger


class AllocationRuleEffectivenessResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    active_rules_only: bool
    items: list[AllocationRuleEffectivenessItem]


class SpendingTrendPeriod(BaseModel):
    period_start: date  # First day of the period (e.g., 2024-01-01)
    amount: int  # Total spending in cents (positive value)
    transaction_count: int


class SpendingTrendEnvelope(BaseModel):
    envelope_id: UUID
    envelope_name: str
    periods: list[SpendingTrendPeriod]
    total_spent: int  # Sum across all periods
    average_per_period: int  # Average spending per period


class SpendingTrendsResponse(BaseModel):
    start_date: date
    end_date: date
    period_count: int  # Number of periods in the range
    envelopes: list[SpendingTrendEnvelope]


class PayeeAnalysisItem(BaseModel):
    payee_id: UUID
    payee_name: str
    total_spent: int  # Total spending in cents (positive value)
    transaction_count: int
    average_amount: int  # Average per transaction
    last_transaction_date: date


class PayeeAnalysisResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    items: list[PayeeAnalysisItem]


class LocationSpendingItem(BaseModel):
    location_id: UUID | None  # None for transactions without location
    location_name: str  # "(No location)" for None
    total_spent: int  # Total spending in cents (positive value)
    transaction_count: int
    average_amount: int


class LocationSpendingResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    include_no_location: bool
    items: list[LocationSpendingItem]


class AccountBalanceHistoryItem(BaseModel):
    date: date
    balance: int  # Balance at end of day, in cents


class AccountBalanceHistoryResponse(BaseModel):
    account_id: UUID
    account_name: str
    start_date: date
    end_date: date
    current_balance: int
    items: list[AccountBalanceHistoryItem]


class SavingsGoalItem(BaseModel):
    envelope_id: UUID
    envelope_name: str
    target_balance: int  # Goal amount in cents
    current_balance: int
    progress_percent: int  # 0-100
    remaining: int  # Amount still needed
    monthly_contribution_rate: int  # Average monthly contribution in cents
    estimated_months_to_goal: int | None  # None if no contributions or already reached


class SavingsGoalProgressResponse(BaseModel):
    calculation_period_days: int  # Days used to calculate contribution rate
    items: list[SavingsGoalItem]


class RecurringExpenseItem(BaseModel):
    recurring_transaction_id: UUID
    payee_name: str | None
    amount: int  # Amount in cents (negative for expenses)
    frequency: str  # e.g., "Every 1 month", "Every 2 weeks"
    next_occurrence: date
    envelope_id: UUID | None
    envelope_name: str | None
    envelope_balance: int | None  # Current balance if envelope linked
    funding_status: str  # "funded", "partially_funded", "not_linked"
    shortfall: int  # Amount needed to fully fund (0 if funded)


class RecurringExpenseCoverageResponse(BaseModel):
    as_of_date: date
    total_recurring: int  # Total number of active recurring expenses
    fully_funded_count: int
    partially_funded_count: int
    not_linked_count: int
    total_shortfall: int  # Total amount needed across all partially funded
    items: list[RecurringExpenseItem]


class NetWorthAccountItem(BaseModel):
    """Per-account net worth data for a specific period."""

    account_id: UUID
    account_name: str
    account_type: str
    is_liability: bool
    balance: int  # Balance at end of period in cents

    model_config = {"from_attributes": True}


class NetWorthPeriod(BaseModel):
    """Net worth snapshot for a single month."""

    period_start: date  # First day of the month (e.g., 2024-01-01)
    total_assets: int  # Sum of asset account balances in cents
    total_liabilities: (
        int  # Sum of liability account balances in cents (positive value)
    )
    net_worth: int  # total_assets - total_liabilities
    accounts: list[NetWorthAccountItem]  # Per-account breakdown


class NetWorthResponse(BaseModel):
    """Complete net worth report response."""

    start_date: date
    end_date: date
    current_net_worth: int  # Current (today's) net worth
    current_total_assets: int
    current_total_liabilities: int
    net_worth_change: int  # Change from first to last period
    periods: list[NetWorthPeriod]
