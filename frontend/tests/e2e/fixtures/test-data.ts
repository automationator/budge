// Test data generators for E2E tests
// These create unique test data for each test run to avoid conflicts

export function generateTestUser() {
  const timestamp = Date.now()
  return {
    username: `testuser_${timestamp}`,
    password: 'TestPassword123!',
    email: `test_${timestamp}@example.com`,
  }
}

export function generateAccountName() {
  return `Test Account ${Date.now()}`
}

export function generateEnvelopeName() {
  return `Test Envelope ${Date.now()}`
}

// Known test credentials (for development database)
export const TEST_USER = {
  username: 'e2etest',
  password: 'e2epassword',
}

// Account types
export type AccountType = 'checking' | 'savings' | 'credit_card' | 'cash' | 'investment' | 'loan' | 'other'

export interface AccountData {
  name: string
  account_type: AccountType
  description?: string
  starting_balance?: number // In cents
  include_in_budget?: boolean
}

export function generateAccountData(overrides?: Partial<AccountData>): AccountData {
  const timestamp = Date.now()
  return {
    name: `Test Account ${timestamp}`,
    account_type: 'checking',
    description: 'Test account for e2e testing',
    starting_balance: 100000, // $1,000.00
    include_in_budget: true,
    ...overrides,
  }
}

export interface EnvelopeData {
  name: string
  target_balance?: number // In cents
  description?: string
  group_id?: string
}

export function generateEnvelopeData(overrides?: Partial<EnvelopeData>): EnvelopeData {
  const timestamp = Date.now()
  return {
    name: `Test Envelope ${timestamp}`,
    description: 'Test envelope for e2e testing',
    ...overrides,
  }
}

export interface TransactionData {
  account_id: string
  date: string
  amount: number // In cents (positive = income, negative = expense)
  payee_id?: string
  payee_name?: string
  memo?: string
  is_cleared?: boolean
}

export function generateTransactionData(accountId: string, overrides?: Partial<Omit<TransactionData, 'account_id'>>): TransactionData {
  const timestamp = Date.now()
  return {
    account_id: accountId,
    date: getToday(),
    amount: -2500, // -$25.00 expense
    payee_name: `Test Payee ${timestamp}`,
    memo: 'Test transaction',
    is_cleared: true,
    ...overrides,
  }
}

export interface TransferData {
  from_account_id: string
  to_account_id: string
  date: string
  amount: number // In cents (positive)
  memo?: string
  is_cleared?: boolean
}

export function generateTransferData(fromAccountId: string, toAccountId: string, overrides?: Partial<Omit<TransferData, 'from_account_id' | 'to_account_id'>>): TransferData {
  return {
    from_account_id: fromAccountId,
    to_account_id: toAccountId,
    date: getToday(),
    amount: 5000, // $50.00
    memo: 'Test transfer',
    is_cleared: true,
    ...overrides,
  }
}

export interface RecurringData {
  account_id: string
  payee_name?: string
  amount: number
  frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'yearly'
  start_date: string
  end_date?: string
  memo?: string
}

export function generateRecurringData(accountId: string, overrides?: Partial<Omit<RecurringData, 'account_id'>>): RecurringData {
  const timestamp = Date.now()
  return {
    account_id: accountId,
    payee_name: `Recurring Payee ${timestamp}`,
    amount: -10000, // -$100.00 expense
    frequency: 'monthly',
    start_date: getToday(),
    memo: 'Test recurring transaction',
    ...overrides,
  }
}

// Date helpers
export function getToday(): string {
  return new Date().toISOString().split('T')[0]
}

export function getYesterday(): string {
  const date = new Date()
  date.setDate(date.getDate() - 1)
  return date.toISOString().split('T')[0]
}

export function getFutureDate(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() + days)
  return date.toISOString().split('T')[0]
}

export function getPastDate(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().split('T')[0]
}

// Format money for display assertions (e.g., 10000 -> "$100.00")
export function formatMoneyForDisplay(cents: number): string {
  const dollars = Math.abs(cents) / 100
  const formatted = dollars.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return cents < 0 ? `-$${formatted}` : `$${formatted}`
}
