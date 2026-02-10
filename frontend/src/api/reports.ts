import apiClient from './client'

// Spending by Category
export interface SpendingByCategoryItem {
  envelope_id: string
  envelope_name: string
  total_spent: number
  total_received: number
  net: number
  transaction_count: number
  // Average spending based on days_in_period (positive cents)
  average_daily: number
  average_weekly: number
  average_monthly: number
  average_yearly: number
}

export interface SpendingByCategoryResponse {
  start_date: string | null
  end_date: string | null
  days_in_period: number
  items: SpendingByCategoryItem[]
}

// Income vs Expenses
export interface IncomeVsExpensesPeriod {
  period_start: string
  income: number
  expenses: number
  net: number
}

export interface IncomeVsExpensesResponse {
  start_date: string | null
  end_date: string | null
  total_income: number
  total_expenses: number
  total_net: number
  periods: IncomeVsExpensesPeriod[]
}

// Payee Analysis
export interface PayeeAnalysisItem {
  payee_id: string
  payee_name: string
  total_spent: number
  transaction_count: number
  average_amount: number
  last_transaction_date: string | null
}

export interface PayeeAnalysisResponse {
  start_date: string | null
  end_date: string | null
  items: PayeeAnalysisItem[]
}

// Spending Trends
export interface SpendingTrendPeriod {
  period_start: string
  amount: number
  transaction_count: number
}

export interface SpendingTrendsEnvelope {
  envelope_id: string
  envelope_name: string
  periods: SpendingTrendPeriod[]
  total_spent: number
  average_per_period: number
}

export interface SpendingTrendsResponse {
  start_date: string
  end_date: string
  period_count: number
  envelopes: SpendingTrendsEnvelope[]
}

// Upcoming Expenses
export interface UpcomingExpenseItem {
  transaction_id: string
  date: string
  amount: number
  memo: string | null
  payee_name: string | null
  envelope_id: string | null
  envelope_name: string | null
  envelope_balance: number | null
  days_away: number
  funding_status: 'funded' | 'needs_attention' | 'not_linked'
}

export interface UpcomingExpensesResponse {
  as_of_date: string
  items: UpcomingExpenseItem[]
}

// Recurring Expense Coverage
export interface RecurringExpenseItem {
  recurring_transaction_id: string
  payee_name: string | null
  amount: number
  frequency: string
  next_occurrence: string
  envelope_id: string | null
  envelope_name: string | null
  envelope_balance: number | null
  funding_status: 'funded' | 'partially_funded' | 'not_linked'
  shortfall: number
}

export interface RecurringExpenseCoverageResponse {
  as_of_date: string
  total_recurring: number
  fully_funded_count: number
  partially_funded_count: number
  not_linked_count: number
  total_shortfall: number
  items: RecurringExpenseItem[]
}

// Location Spending
export interface LocationSpendingItem {
  location_id: string | null
  location_name: string
  total_spent: number
  transaction_count: number
  average_amount: number
}

export interface LocationSpendingResponse {
  start_date: string | null
  end_date: string | null
  include_no_location: boolean
  items: LocationSpendingItem[]
}

// Envelope Balance History
export interface EnvelopeBalanceHistoryItem {
  date: string
  balance: number
}

export interface EnvelopeBalanceHistoryResponse {
  envelope_id: string
  envelope_name: string
  start_date: string
  end_date: string
  current_balance: number
  target_balance: number | null
  items: EnvelopeBalanceHistoryItem[]
}

// Account Balance History
export interface AccountBalanceHistoryItem {
  date: string
  balance: number
}

export interface AccountBalanceHistoryResponse {
  account_id: string
  account_name: string
  start_date: string
  end_date: string
  current_balance: number
  items: AccountBalanceHistoryItem[]
}

// Allocation Rule Effectiveness
export interface AllocationRuleEffectivenessItem {
  rule_id: string
  rule_name: string | null
  envelope_id: string
  envelope_name: string
  rule_type: 'FIXED' | 'PERCENTAGE' | 'FILL_TO_TARGET' | 'REMAINDER' | 'PERIOD_CAP'
  priority: number
  configured_amount: number
  has_period_cap: boolean
  total_allocated: number
  times_triggered: number
  period_cap_limited: boolean
  average_per_trigger: number
}

export interface AllocationRuleEffectivenessResponse {
  start_date: string | null
  end_date: string | null
  active_rules_only: boolean
  items: AllocationRuleEffectivenessItem[]
}

// Days of Runway
export interface DaysOfRunwayItem {
  envelope_id: string
  envelope_name: string
  current_balance: number
  average_daily_spending: number
  days_of_runway: number | null
}

export interface DaysOfRunwayResponse {
  start_date: string
  end_date: string
  calculation_period_days: number
  total_balance: number
  total_average_daily_spending: number
  total_days_of_runway: number | null
  items: DaysOfRunwayItem[]
}

// Savings Goal Progress
export interface SavingsGoalItem {
  envelope_id: string
  envelope_name: string
  current_balance: number
  target_balance: number
  progress_percent: number
  monthly_contribution_rate: number
  months_to_goal: number | null
}

export interface SavingsGoalProgressResponse {
  as_of_date: string
  items: SavingsGoalItem[]
}

// Runway Trend
export interface RunwayTrendDataPoint {
  date: string
  balance: number
  average_daily_spending: number
  days_of_runway: number | null
}

export interface RunwayTrendResponse {
  start_date: string
  end_date: string
  lookback_days: number
  envelope_id: string | null
  envelope_name: string | null
  data_points: RunwayTrendDataPoint[]
}

// Net Worth
export interface NetWorthAccountItem {
  account_id: string
  account_name: string
  account_type: string
  is_liability: boolean
  balance: number // in cents
}

export interface NetWorthPeriod {
  period_start: string // ISO date string (first of month)
  total_assets: number
  total_liabilities: number
  net_worth: number
  accounts: NetWorthAccountItem[]
}

export interface NetWorthResponse {
  start_date: string
  end_date: string
  current_net_worth: number
  current_total_assets: number
  current_total_liabilities: number
  net_worth_change: number
  periods: NetWorthPeriod[]
}

// API Functions
export async function getSpendingByCategory(
  budgetId: string,
  startDate?: string,
  endDate?: string
): Promise<SpendingByCategoryResponse> {
  const response = await apiClient.get<SpendingByCategoryResponse>(
    `/budgets/${budgetId}/reports/spending-by-category`,
    { params: { start_date: startDate, end_date: endDate } }
  )
  return response.data
}

export async function getIncomeVsExpenses(
  budgetId: string,
  startDate?: string,
  endDate?: string
): Promise<IncomeVsExpensesResponse> {
  const response = await apiClient.get<IncomeVsExpensesResponse>(
    `/budgets/${budgetId}/reports/income-vs-expenses`,
    { params: { start_date: startDate, end_date: endDate } }
  )
  return response.data
}

export async function getPayeeAnalysis(
  budgetId: string,
  startDate?: string,
  endDate?: string
): Promise<PayeeAnalysisResponse> {
  const response = await apiClient.get<PayeeAnalysisResponse>(
    `/budgets/${budgetId}/reports/payee-analysis`,
    { params: { start_date: startDate, end_date: endDate } }
  )
  return response.data
}

export async function getSpendingTrends(
  budgetId: string,
  startDate: string,
  endDate: string,
  envelopeIds?: string[]
): Promise<SpendingTrendsResponse> {
  const response = await apiClient.get<SpendingTrendsResponse>(
    `/budgets/${budgetId}/reports/spending-trends`,
    { params: { start_date: startDate, end_date: endDate, envelope_id: envelopeIds } }
  )
  return response.data
}

export async function getDaysOfRunway(
  budgetId: string,
  calculationPeriodDays = 30
): Promise<DaysOfRunwayResponse> {
  const response = await apiClient.get<DaysOfRunwayResponse>(
    `/budgets/${budgetId}/reports/days-of-runway`,
    { params: { calculation_period_days: calculationPeriodDays } }
  )
  return response.data
}

export async function getSavingsGoalProgress(
  budgetId: string,
  calculationPeriodDays = 90
): Promise<SavingsGoalProgressResponse> {
  const response = await apiClient.get<SavingsGoalProgressResponse>(
    `/budgets/${budgetId}/reports/savings-goal-progress`,
    { params: { calculation_period_days: calculationPeriodDays } }
  )
  return response.data
}

export async function getRunwayTrend(
  budgetId: string,
  startDate: string,
  endDate: string,
  lookbackDays = 30,
  envelopeId?: string
): Promise<RunwayTrendResponse> {
  const response = await apiClient.get<RunwayTrendResponse>(
    `/budgets/${budgetId}/reports/runway-trend`,
    {
      params: {
        start_date: startDate,
        end_date: endDate,
        lookback_days: lookbackDays,
        envelope_id: envelopeId,
      },
    }
  )
  return response.data
}

export async function getNetWorth(
  budgetId: string,
  startDate: string | null,
  endDate: string
): Promise<NetWorthResponse> {
  const params: Record<string, string> = { end_date: endDate }
  if (startDate) {
    params.start_date = startDate
  }
  const response = await apiClient.get<NetWorthResponse>(
    `/budgets/${budgetId}/reports/net-worth`,
    { params }
  )
  return response.data
}

export async function getUpcomingExpenses(
  budgetId: string,
  daysAhead = 90
): Promise<UpcomingExpensesResponse> {
  const response = await apiClient.get<UpcomingExpensesResponse>(
    `/budgets/${budgetId}/reports/upcoming-expenses`,
    { params: { days_ahead: daysAhead } }
  )
  return response.data
}

export async function getRecurringExpenseCoverage(
  budgetId: string
): Promise<RecurringExpenseCoverageResponse> {
  const response = await apiClient.get<RecurringExpenseCoverageResponse>(
    `/budgets/${budgetId}/reports/recurring-expense-coverage`
  )
  return response.data
}

export async function getLocationSpending(
  budgetId: string,
  startDate?: string,
  endDate?: string,
  includeNoLocation = true
): Promise<LocationSpendingResponse> {
  const response = await apiClient.get<LocationSpendingResponse>(
    `/budgets/${budgetId}/reports/location-spending`,
    {
      params: {
        start_date: startDate,
        end_date: endDate,
        include_no_location: includeNoLocation,
      },
    }
  )
  return response.data
}

export async function getEnvelopeBalanceHistory(
  budgetId: string,
  envelopeId: string,
  startDate: string,
  endDate: string
): Promise<EnvelopeBalanceHistoryResponse> {
  const response = await apiClient.get<EnvelopeBalanceHistoryResponse>(
    `/budgets/${budgetId}/reports/envelope-balance-history`,
    {
      params: {
        envelope_id: envelopeId,
        start_date: startDate,
        end_date: endDate,
      },
    }
  )
  return response.data
}

export async function getAccountBalanceHistory(
  budgetId: string,
  accountId: string,
  startDate: string,
  endDate: string
): Promise<AccountBalanceHistoryResponse> {
  const response = await apiClient.get<AccountBalanceHistoryResponse>(
    `/budgets/${budgetId}/reports/account-balance-history`,
    {
      params: {
        account_id: accountId,
        start_date: startDate,
        end_date: endDate,
      },
    }
  )
  return response.data
}

export async function getAllocationRuleEffectiveness(
  budgetId: string,
  startDate?: string,
  endDate?: string,
  activeOnly = true
): Promise<AllocationRuleEffectivenessResponse> {
  const response = await apiClient.get<AllocationRuleEffectivenessResponse>(
    `/budgets/${budgetId}/reports/allocation-rule-effectiveness`,
    {
      params: {
        start_date: startDate,
        end_date: endDate,
        active_only: activeOnly,
      },
    }
  )
  return response.data
}
