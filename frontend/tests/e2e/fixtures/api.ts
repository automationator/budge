import { test as base, type Page, type APIRequestContext, request } from '@playwright/test'
import type { AccountData, EnvelopeData, TransactionData } from './test-data'

const API_BASE_URL = 'http://localhost:8000/api/v1'

/**
 * API helper for directly interacting with the backend during tests.
 * Used to set up test data before UI interactions.
 *
 * Uses Playwright's APIRequestContext which can share auth state with the browser.
 */
export class ApiHelper {
  private teamId: string = ''
  private apiContext!: APIRequestContext

  constructor(
    private page: Page
  ) {}

  /**
   * Initialize the API helper by extracting team ID from page localStorage.
   * Must be called after page has authenticated state.
   */
  async init() {
    // First navigate to the app to access localStorage and let auth initialize
    await this.page.goto('/')
    await this.page.waitForLoadState('domcontentloaded')
    // Wait for Vue app to mount
    await this.page.locator('.v-main, .v-application').first().waitFor({
      state: 'visible',
      timeout: 20000,
    })

    // Get the team ID from localStorage
    const teamId = await this.page.evaluate(() => {
      return localStorage.getItem('budge_current_team')
    })

    this.teamId = teamId || ''

    // Create an API context that uses the browser's storage state
    // This shares cookies and other auth data with the browser
    this.apiContext = await request.newContext({
      baseURL: API_BASE_URL,
      storageState: await this.page.context().storageState(),
    })

    // Get an access token by triggering a page refresh (which will refresh tokens)
    // Then intercept the API calls to get the token
    // Actually, let's just make requests through the page's evaluate

    return this
  }

  /**
   * Make an authenticated API request using the page's JavaScript context.
   * This uses the app's existing auth infrastructure.
   */
  private async request(method: string, path: string, body?: unknown): Promise<unknown> {
    const url = path.startsWith('/') ? path : `/${path}`

    // Use page.evaluate to make the request with the app's auth context
    const result = await this.page.evaluate(
      async ({ url, method, body, baseUrl }) => {
        // Get the access token from memory via the api client module
        // @ts-expect-error - accessing window's module scope
        const token = window.__budge_access_token || localStorage.getItem('budge_access_token')

        const response = await fetch(`${baseUrl}${url}`, {
          method,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: body ? JSON.stringify(body) : undefined,
        })

        if (!response.ok) {
          const text = await response.text()
          throw new Error(`API ${response.status}: ${text}`)
        }

        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          return response.json()
        }
        return null
      },
      { url, method, body, baseUrl: API_BASE_URL }
    )

    return result
  }

  // ============ Accounts ============

  async createAccount(data: AccountData): Promise<{ id: string; name: string; cleared_balance: number; uncleared_balance: number }> {
    return await this.request('POST', `/teams/${this.teamId}/accounts`, {
      name: data.name,
      account_type: data.account_type,
      description: data.description,
      include_in_budget: data.include_in_budget ?? true,
    }) as { id: string; name: string; cleared_balance: number; uncleared_balance: number }
  }

  async listAccounts(): Promise<{ id: string; name: string; cleared_balance: number; uncleared_balance: number }[]> {
    return await this.request('GET', `/teams/${this.teamId}/accounts`) as { id: string; name: string; cleared_balance: number; uncleared_balance: number }[]
  }

  async deleteAccount(accountId: string): Promise<void> {
    await this.request('DELETE', `/teams/${this.teamId}/accounts/${accountId}`)
  }

  async deleteAllAccounts(): Promise<void> {
    const accounts = await this.listAccounts()
    for (const account of accounts) {
      await this.deleteAccount(account.id)
    }
  }

  // ============ Envelopes ============

  async createEnvelope(data: EnvelopeData): Promise<{ id: string; name: string; current_balance: number }> {
    return await this.request('POST', `/teams/${this.teamId}/envelopes`, {
      name: data.name,
      target_balance: data.target_balance,
      description: data.description,
      group_id: data.group_id,
    }) as { id: string; name: string; current_balance: number }
  }

  async listEnvelopes(): Promise<{ id: string; name: string; current_balance: number; is_unallocated: boolean }[]> {
    return await this.request('GET', `/teams/${this.teamId}/envelopes`) as { id: string; name: string; current_balance: number; is_unallocated: boolean }[]
  }

  async deleteEnvelope(envelopeId: string): Promise<void> {
    await this.request('DELETE', `/teams/${this.teamId}/envelopes/${envelopeId}`)
  }

  // ============ Transactions ============

  async createTransaction(data: TransactionData): Promise<{ id: string }> {
    return await this.request('POST', `/teams/${this.teamId}/transactions`, {
      account_id: data.account_id,
      date: data.date,
      amount: data.amount,
      payee_id: data.payee_id,
      payee_name: data.payee_name,
      memo: data.memo,
      is_cleared: data.is_cleared,
    }) as { id: string }
  }

  async listTransactions(accountId?: string): Promise<{ items: { id: string }[] }> {
    const params = accountId ? `?account_id=${accountId}` : ''
    return await this.request('GET', `/teams/${this.teamId}/transactions${params}`) as { items: { id: string }[] }
  }

  async deleteTransaction(transactionId: string): Promise<void> {
    await this.request('DELETE', `/teams/${this.teamId}/transactions/${transactionId}`)
  }

  // ============ Payees ============

  async createPayee(name: string): Promise<{ id: string; name: string }> {
    return await this.request('POST', `/teams/${this.teamId}/payees`, { name }) as { id: string; name: string }
  }

  async listPayees(): Promise<{ id: string; name: string }[]> {
    return await this.request('GET', `/teams/${this.teamId}/payees`) as { id: string; name: string }[]
  }

  // ============ Team Info ============

  get currentTeamId(): string {
    return this.teamId
  }
}

// Fixture that provides an initialized API helper
interface ApiFixtures {
  api: ApiHelper
}

export const test = base.extend<ApiFixtures>({
  api: async ({ page }, use) => {
    const api = new ApiHelper(page)
    await api.init()
    await use(api)
  },
})

export { expect } from '@playwright/test'
