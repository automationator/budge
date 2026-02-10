/**
 * Test API client for E2E test factories.
 *
 * This client communicates with the backend test endpoints
 * to set up and tear down test data. Only available when
 * the backend is running with ENV=e2e.
 */

const TEST_API_URL = 'http://localhost:8000/test'

export interface UserData {
  userId: string
  budgetId: string
  accessToken: string
  refreshToken: string
}

export interface AccountData {
  id: string
  name: string
  accountType: string
  includeInBudget: boolean
  clearedBalance: number
  unclearedBalance: number
}

export interface EnvelopeData {
  id: string
  name: string
  envelopeGroupId: string | null
  currentBalance: number
  targetBalance: number | null
  isStarred: boolean
}

export interface PayeeData {
  id: string
  name: string
}

export interface LocationData {
  id: string
  name: string
}

export interface TransactionData {
  id: string
  accountId: string
  amount: number
  payeeId: string | null
  date: string
  isCleared: boolean
  isReconciled: boolean
}

export interface ReconcileResult {
  transactionsReconciled: number
  adjustmentTransactionId: string | null
}

export interface BudgetData {
  id: string
  name: string
}

export interface AllocationRuleInput {
  envelopeId: string
  ruleType?: 'fixed' | 'percentage' | 'fill_to_target' | 'remainder'
  amount?: number // in cents or basis points (for percentage)
  priority?: number
  isActive?: boolean
  name?: string
}

export interface AllocationRuleData {
  id: string
  envelopeId: string
  ruleType: string
  amount: number
  priority: number
  isActive: boolean
}

export interface AccountInput {
  name: string
  accountType?: string
  includeInBudget?: boolean
  startingBalance?: number
}

export interface EnvelopeInput {
  name: string
  groupName?: string
  envelope_group_id?: string
  targetBalance?: number
  isStarred?: boolean
}

export interface EnvelopeGroupData {
  id: string
  name: string
  sortOrder: number
}

export interface TransactionInput {
  accountId: string
  amount: number
  payeeName?: string
  envelopeId?: string
  transactionDate?: string
  memo?: string
  isCleared?: boolean
}

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = 5,
  delay = 1500
): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, options)
      if (response.ok || response.status < 500) {
        return response
      }
      // Server error, retry
      if (i < retries - 1) {
        await new Promise((r) => setTimeout(r, delay))
      }
    } catch (error) {
      if (i === retries - 1) throw error
      await new Promise((r) => setTimeout(r, delay))
    }
  }
  throw new Error(`Failed to fetch ${url} after ${retries} retries`)
}

export class TestApi {
  private workerId: string

  constructor(workerIndex: number) {
    this.workerId = `w${workerIndex}`
  }

  get workerIdValue(): string {
    return this.workerId
  }

  /**
   * Reset the database schema for this worker.
   * Drops and recreates the schema, runs migrations.
   */
  async reset(): Promise<{ schemaName: string; status: string }> {
    const response = await fetchWithRetry(`${TEST_API_URL}/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ worker_id: this.workerId }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Reset failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      schemaName: data.schema_name,
      status: data.status,
    }
  }

  /**
   * Create a test user with budget and auth tokens.
   */
  async createUser(username?: string, isAdmin?: boolean): Promise<UserData> {
    const name = username || `e2e_${this.workerId}_${Date.now()}`

    const response = await fetchWithRetry(`${TEST_API_URL}/factory/user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        username: name,
        password: 'TestPassword123!',
        is_admin: isAdmin ?? null,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create user failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      userId: data.user_id,
      budgetId: data.budget_id,
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    }
  }

  /**
   * Create a test account.
   */
  async createAccount(budgetId: string, input: AccountInput): Promise<AccountData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/account`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        name: input.name,
        account_type: input.accountType ?? 'checking',
        include_in_budget: input.includeInBudget ?? true,
        starting_balance: input.startingBalance ?? 0,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create account failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      name: data.name,
      accountType: data.account_type,
      includeInBudget: data.include_in_budget,
      clearedBalance: data.cleared_balance,
      unclearedBalance: data.uncleared_balance,
    }
  }

  /**
   * Create a test envelope with optional group.
   */
  async createEnvelope(budgetId: string, input: EnvelopeInput): Promise<EnvelopeData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/envelope`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        name: input.name,
        group_name: input.groupName ?? null,
        target_balance: input.targetBalance ?? null,
        is_starred: input.isStarred ?? false,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create envelope failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      name: data.name,
      envelopeGroupId: data.envelope_group_id,
      currentBalance: data.current_balance,
      targetBalance: data.target_balance,
      isStarred: data.is_starred,
    }
  }

  /**
   * Create a test envelope group.
   */
  async createEnvelopeGroup(budgetId: string, name: string): Promise<EnvelopeGroupData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/envelope-group`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        name,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create envelope group failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      name: data.name,
      sortOrder: data.sort_order,
    }
  }

  /**
   * Create a test payee.
   */
  async createPayee(budgetId: string, name: string): Promise<PayeeData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/payee`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        name,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create payee failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      name: data.name,
    }
  }

  /**
   * Create a test location.
   */
  async createLocation(budgetId: string, name: string): Promise<LocationData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/location`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        name,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create location failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      name: data.name,
    }
  }

  /**
   * Create a test transaction with optional payee and allocation.
   */
  async createTransaction(budgetId: string, input: TransactionInput): Promise<TransactionData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/transaction`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        account_id: input.accountId,
        amount: input.amount,
        payee_name: input.payeeName ?? null,
        envelope_id: input.envelopeId ?? null,
        transaction_date: input.transactionDate ?? null,
        memo: input.memo ?? null,
        is_cleared: input.isCleared ?? false,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create transaction failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      accountId: data.account_id,
      amount: data.amount,
      payeeId: data.payee_id,
      date: data.date,
      isCleared: data.is_cleared,
      isReconciled: data.is_reconciled,
    }
  }

  /**
   * Reconcile an account - marks cleared transactions as reconciled.
   */
  async reconcileAccount(budgetId: string, accountId: string, actualBalance: number): Promise<ReconcileResult> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/reconcile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        account_id: accountId,
        actual_balance: actualBalance,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Reconcile account failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      transactionsReconciled: data.transactions_reconciled,
      adjustmentTransactionId: data.adjustment_transaction_id,
    }
  }

  /**
   * Create a new budget for an existing user.
   */
  async createBudget(userId: string, name: string): Promise<BudgetData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/budget`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        user_id: userId,
        name,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create budget failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      name: data.name,
    }
  }

  /**
   * Create a test allocation rule.
   */
  async createAllocationRule(budgetId: string, input: AllocationRuleInput): Promise<AllocationRuleData> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/allocation-rule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        budget_id: budgetId,
        envelope_id: input.envelopeId,
        rule_type: input.ruleType ?? 'fixed',
        amount: input.amount ?? 0,
        priority: input.priority ?? 1,
        is_active: input.isActive ?? true,
        name: input.name ?? null,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Create allocation rule failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return {
      id: data.id,
      envelopeId: data.envelope_id,
      ruleType: data.rule_type,
      amount: data.amount,
      priority: data.priority,
      isActive: data.is_active,
    }
  }

  /**
   * Enable or disable user registration.
   */
  async setRegistrationEnabled(enabled: boolean): Promise<boolean> {
    const response = await fetchWithRetry(`${TEST_API_URL}/factory/set-registration`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: this.workerId,
        enabled,
      }),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Set registration failed (${response.status}): ${text}`)
    }

    const data = await response.json()
    return data.registration_enabled
  }
}
