import type {
  User,
  Budget,
  Account,
  Envelope,
  Transaction,
  Payee,
  LoginResponse,
  CursorPage,
  AllocationRule,
  Allocation,
  RecurringTransaction,
} from '@/types'
import type { BudgetMember } from '@/api/budgets'
import type { RulePreviewResponse } from '@/api/allocationRules'

// Factory functions for test data
export const factories = {
  user: (overrides: Partial<User> = {}): User => ({
    id: 'user-1',
    username: 'testuser',
    is_active: true,
    is_admin: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: null,
    ...overrides,
  }),

  budget: (overrides: Partial<Budget> = {}): Budget => ({
    id: 'budget-1',
    name: 'Personal',
    owner_id: 'user-1',
    default_income_allocation: 'rules',
    ...overrides,
  }),

  account: (overrides: Partial<Account> = {}): Account => ({
    id: 'account-1',
    budget_id: 'budget-1',
    name: 'Checking',
    account_type: 'checking',
    icon: null,
    description: null,
    sort_order: 0,
    include_in_budget: true,
    is_active: true,
    cleared_balance: 100000, // $1000.00
    uncleared_balance: 0,
    last_reconciled_at: null,
    ...overrides,
  }),

  envelope: (overrides: Partial<Envelope> = {}): Envelope => ({
    id: 'envelope-1',
    budget_id: 'budget-1',
    envelope_group_id: null,
    linked_account_id: null,
    name: 'Groceries',
    icon: null,
    description: null,
    sort_order: 0,
    is_active: true,
    is_starred: false,
    is_unallocated: false,
    current_balance: 50000, // $500.00
    target_balance: 60000, // $600.00
    ...overrides,
  }),

  transaction: (overrides: Partial<Transaction> = {}): Transaction => ({
    id: 'transaction-1',
    budget_id: 'budget-1',
    account_id: 'account-1',
    payee_id: 'payee-1',
    location_id: null,
    user_id: 'user-1',
    date: '2024-01-15',
    amount: -5000, // -$50.00
    is_cleared: true,
    is_reconciled: false,
    memo: null,
    transaction_type: 'standard',
    status: 'completed',
    recurring_transaction_id: null,
    linked_transaction_id: null,
    linked_account_id: null,
    occurrence_index: null,
    is_modified: false,
    ...overrides,
  }),

  payee: (overrides: Partial<Payee> = {}): Payee => ({
    id: 'payee-1',
    budget_id: 'budget-1',
    name: 'Grocery Store',
    icon: null,
    description: null,
    default_envelope_id: null,
    ...overrides,
  }),

  allocation: (overrides: Partial<Allocation> = {}): Allocation => ({
    id: 'allocation-1',
    budget_id: 'budget-1',
    envelope_id: 'envelope-1',
    transaction_id: 'transaction-1',
    allocation_rule_id: null,
    group_id: 'group-1',
    execution_order: 0,
    amount: 5000,
    memo: null,
    date: '2024-01-15',
    created_at: '2024-01-15T00:00:00Z',
    updated_at: null,
    ...overrides,
  }),

  loginResponse: (overrides: Partial<LoginResponse> = {}): LoginResponse => ({
    access_token: 'test-access-token',
    refresh_token: 'test-refresh-token',
    token_type: 'bearer',
    ...overrides,
  }),

  cursorPage: <T>(items: T[], overrides: Partial<CursorPage<T>> = {}): CursorPage<T> => ({
    items,
    next_cursor: null,
    has_more: false,
    ...overrides,
  }),

  allocationRule: (overrides: Partial<AllocationRule> = {}): AllocationRule => ({
    id: 'rule-1',
    budget_id: 'budget-1',
    envelope_id: 'envelope-1',
    priority: 0,
    rule_type: 'fixed',
    amount: 10000, // $100.00
    is_active: true,
    name: 'Savings Rule',
    respect_target: false,
    cap_period_value: 1,
    cap_period_unit: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: null,
    ...overrides,
  }),

  rulePreviewResponse: (overrides: Partial<RulePreviewResponse> = {}): RulePreviewResponse => ({
    income_amount: 100000, // $1000.00
    allocations: [
      {
        envelope_id: 'envelope-1',
        amount: 10000,
        rule_id: 'rule-1',
        rule_name: 'Savings Rule',
      },
    ],
    unallocated: 90000,
    ...overrides,
  }),

  // Convenience factory variants
  overspentEnvelope: (overrides: Partial<Envelope> = {}): Envelope =>
    factories.envelope({
      current_balance: -5000, // -$50.00 (overspent)
      target_balance: null,
      ...overrides,
    }),

  budgetAccount: (overrides: Partial<Account> = {}): Account =>
    factories.account({
      include_in_budget: true,
      ...overrides,
    }),

  offBudgetAccount: (overrides: Partial<Account> = {}): Account =>
    factories.account({
      include_in_budget: false,
      ...overrides,
    }),

  creditCardAccount: (overrides: Partial<Account> = {}): Account =>
    factories.account({
      account_type: 'credit_card',
      include_in_budget: true,
      cleared_balance: -50000, // -$500 (debt)
      ...overrides,
    }),

  staleAccount: (overrides: Partial<Account> = {}): Account => {
    const thirtyOneDaysAgo = new Date()
    thirtyOneDaysAgo.setDate(thirtyOneDaysAgo.getDate() - 31)
    return factories.account({
      last_reconciled_at: thirtyOneDaysAgo.toISOString(),
      ...overrides,
    })
  },

  recentlyReconciledAccount: (overrides: Partial<Account> = {}): Account => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    return factories.account({
      last_reconciled_at: yesterday.toISOString(),
      ...overrides,
    })
  },

  transferTransaction: (overrides: Partial<Transaction> = {}): Transaction =>
    factories.transaction({
      transaction_type: 'transfer',
      payee_id: null,
      linked_transaction_id: 'linked-transaction-1',
      ...overrides,
    }),

  unclearedTransaction: (overrides: Partial<Transaction> = {}): Transaction =>
    factories.transaction({
      is_cleared: false,
      ...overrides,
    }),

  unallocatedTransaction: (overrides: Partial<Transaction> = {}): Transaction =>
    factories.transaction({
      allocations: [],
      ...overrides,
    }),

  recurringTransaction: (overrides: Partial<RecurringTransaction> = {}): RecurringTransaction => ({
    id: 'recurring-1',
    budget_id: 'budget-1',
    account_id: 'account-1',
    destination_account_id: null,
    payee_id: 'payee-1',
    location_id: null,
    envelope_id: null,
    frequency_value: 1,
    frequency_unit: 'months',
    start_date: '2024-01-01',
    end_date: null,
    amount: -5000, // -$50.00
    memo: null,
    next_occurrence_date: '2024-02-01',
    next_scheduled_date: '2024-02-01',
    is_active: true,
    ...overrides,
  }),

  inactiveRecurring: (overrides: Partial<RecurringTransaction> = {}): RecurringTransaction =>
    factories.recurringTransaction({
      is_active: false,
      ...overrides,
    }),

  recurringIncome: (overrides: Partial<RecurringTransaction> = {}): RecurringTransaction =>
    factories.recurringTransaction({
      amount: 200000, // +$2,000.00
      ...overrides,
    }),

  recurringTransfer: (overrides: Partial<RecurringTransaction> = {}): RecurringTransaction =>
    factories.recurringTransaction({
      destination_account_id: 'account-2',
      payee_id: null,
      ...overrides,
    }),

  budgetMember: (overrides: Partial<BudgetMember> = {}): BudgetMember => ({
    id: 'user-1',
    username: 'testuser',
    email: undefined,
    first_name: undefined,
    last_name: undefined,
    role: 'owner' as const,
    effective_scopes: [],
    ...overrides,
  }),
}
