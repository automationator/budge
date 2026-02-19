// API Response types

export interface User {
  id: string
  username: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  updated_at: string | null
}

export interface UserUpdate {
  username?: string
  password?: string
}

export type DefaultIncomeAllocation = 'rules' | 'envelope' | 'unallocated'

export interface Budget {
  id: string
  name: string
  owner_id: string
  default_income_allocation: DefaultIncomeAllocation
}

export interface BudgetMembership {
  id: string
  budget_id: string
  user_id: string
  role: BudgetRole
  scope_additions: string[]
  scope_removals: string[]
}

export type BudgetRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface Account {
  id: string
  budget_id: string
  name: string
  account_type: AccountType
  icon: string | null
  description: string | null
  sort_order: number
  include_in_budget: boolean
  is_active: boolean
  cleared_balance: number // in cents
  uncleared_balance: number // in cents
  last_reconciled_at: string | null // ISO datetime string
}

export type AccountType = 'checking' | 'savings' | 'credit_card' | 'cash' | 'investment' | 'loan' | 'other'

export interface EnvelopeGroup {
  id: string
  budget_id: string
  name: string
  icon: string | null
  sort_order: number
}

export type AllocationCapPeriodUnit = 'week' | 'month' | 'year'

export interface Envelope {
  id: string
  budget_id: string
  envelope_group_id: string | null
  linked_account_id: string | null // Credit card account link
  name: string
  icon: string | null
  description: string | null
  sort_order: number
  is_active: boolean
  is_starred: boolean
  is_unallocated: boolean
  current_balance: number // in cents
  target_balance: number | null // in cents
}

export interface Transaction {
  id: string
  budget_id: string
  account_id: string
  payee_id: string | null
  location_id: string | null
  user_id: string | null
  date: string // ISO date string
  amount: number // in cents (negative = expense, positive = income)
  is_cleared: boolean
  is_reconciled: boolean
  memo: string | null
  transaction_type: TransactionType
  status: TransactionStatus
  recurring_transaction_id: string | null
  linked_transaction_id: string | null
  linked_account_id: string | null
  occurrence_index: number | null
  is_modified: boolean
  // Expanded relations
  account?: Account
  payee?: Payee
  location?: Location
  allocations?: Allocation[]
}

export type TransactionType = 'standard' | 'transfer' | 'adjustment'
export type TransactionStatus = 'posted' | 'scheduled' | 'skipped'

export interface Allocation {
  id: string
  budget_id: string
  envelope_id: string
  transaction_id: string | null
  allocation_rule_id: string | null
  group_id: string
  execution_order: number
  amount: number // in cents
  memo: string | null
  envelope?: Envelope
  date: string // ISO date of the allocation
  created_at: string
  updated_at: string | null
}

export interface Payee {
  id: string
  budget_id: string
  name: string
  icon: string | null
  description: string | null
  default_envelope_id: string | null
}

export interface Location {
  id: string
  budget_id: string
  name: string
  icon: string | null
  description: string | null
}

export interface RecurringTransaction {
  id: string
  budget_id: string
  account_id: string
  destination_account_id: string | null
  payee_id: string | null
  location_id: string | null
  envelope_id: string | null
  frequency_value: number
  frequency_unit: FrequencyUnit
  start_date: string
  end_date: string | null
  amount: number // in cents
  memo: string | null
  next_occurrence_date: string
  next_scheduled_date: string | null // Earliest scheduled transaction date
  is_active: boolean
}

export type FrequencyUnit = 'days' | 'weeks' | 'months' | 'years'

export interface AllocationRule {
  id: string
  budget_id: string
  envelope_id: string
  priority: number
  rule_type: AllocationRuleType
  amount: number // in cents or basis points (for percentage)
  is_active: boolean
  name: string | null
  respect_target: boolean // stop allocating when envelope reaches target
  cap_period_value: number
  cap_period_unit: AllocationCapPeriodUnit | null
  created_at: string
  updated_at: string | null
}

export type AllocationRuleType = 'fill_to_target' | 'fixed' | 'percentage' | 'remainder' | 'period_cap'

export interface Notification {
  id: string
  budget_id: string
  user_id: string | null
  notification_type: NotificationType
  title: string
  message: string
  related_entity_type: string | null
  related_entity_id: string | null
  is_read: boolean
  is_dismissed: boolean
}

export type NotificationType = 'low_balance' | 'upcoming_expense' | 'recurring_not_funded' | 'goal_reached'

export interface NotificationPreference {
  id: string
  budget_id: string
  user_id: string
  notification_type: NotificationType
  is_enabled: boolean
  low_balance_threshold: number | null
  upcoming_expense_days: number | null
}

// Default Envelope Response
export interface DefaultEnvelope {
  envelope_id: string | null
}

// Auth types
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}

// Pagination
export interface CursorPage<T> {
  items: T[]
  next_cursor: string | null
  has_more: boolean
}

// API Error
export interface ApiError {
  detail: string
}

// System Settings (Admin)
export interface SystemSettings {
  registration_enabled: boolean
}

export interface RegistrationStatus {
  registration_enabled: boolean
}

export interface VersionInfo {
  current_version: string
  latest_version: string | null
  update_available: boolean
  release_url: string | null
  error: string | null
}
