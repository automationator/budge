import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia } from 'pinia'
import { useAccountsStore } from '@/stores/accounts'
import { useAuthStore } from '@/stores/auth'
import { createTestPinia, factories } from '@test/setup'

// Mock the accounts API
vi.mock('@/api/accounts', () => ({
  listAccounts: vi.fn(),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
  reconcileAccount: vi.fn(),
}))

// Mock the auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}))

import * as accountsApi from '@/api/accounts'

describe('useAccountsStore', () => {
  const mockAuthStore = {
    currentBudgetId: 'budget-1',
  }

  beforeEach(() => {
    setActivePinia(createTestPinia())
    vi.clearAllMocks()

    // Set up auth store mock
    ;(useAuthStore as Mock).mockReturnValue(mockAuthStore)

    // Set up default API mock implementations
    ;(accountsApi.listAccounts as Mock).mockResolvedValue([
      factories.account(),
      factories.account({ id: 'account-2', name: 'Savings', account_type: 'savings' }),
    ])
    ;(accountsApi.getAccount as Mock).mockResolvedValue(factories.account())
    ;(accountsApi.createAccount as Mock).mockImplementation(async (_teamId, data) =>
      factories.account({ ...data, id: 'new-account-id' })
    )
    ;(accountsApi.updateAccount as Mock).mockImplementation(async (_teamId, accountId, data) =>
      factories.account({ ...data, id: accountId })
    )
    ;(accountsApi.deleteAccount as Mock).mockResolvedValue(undefined)
    ;(accountsApi.reconcileAccount as Mock).mockResolvedValue(undefined)
  })

  describe('initial state', () => {
    it('has correct initial values', () => {
      const store = useAccountsStore()

      expect(store.accounts).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('computed properties', () => {
    it('calculates totalBalance correctly', () => {
      const store = useAccountsStore()
      store.accounts = [
        factories.account({ cleared_balance: 8000, uncleared_balance: 2000, is_active: true, include_in_budget: true }),
        factories.account({ id: '2', cleared_balance: 5000, uncleared_balance: 0, is_active: true, include_in_budget: true }),
        factories.account({ id: '3', cleared_balance: 3000, uncleared_balance: 0, is_active: false, include_in_budget: true }),
        factories.account({ id: '4', cleared_balance: 2000, uncleared_balance: 0, is_active: true, include_in_budget: false }),
      ]

      expect(store.totalBalance).toBe(15000) // Only active + in budget
    })

    it('filters activeAccounts correctly', () => {
      const store = useAccountsStore()
      store.accounts = [
        factories.account({ is_active: true, sort_order: 2 }),
        factories.account({ id: '2', is_active: false, sort_order: 1 }),
        factories.account({ id: '3', is_active: true, sort_order: 0 }),
      ]

      expect(store.activeAccounts.length).toBe(2)
      expect(store.activeAccounts[0]!.sort_order).toBe(0) // Should be sorted
      expect(store.activeAccounts[1]!.sort_order).toBe(2)
    })

    it('groups accounts by type', () => {
      const store = useAccountsStore()
      store.accounts = [
        factories.account({ account_type: 'checking', is_active: true }),
        factories.account({ id: '2', account_type: 'savings', is_active: true }),
        factories.account({ id: '3', account_type: 'checking', is_active: true }),
      ]

      expect(store.accountsByType['checking']!.length).toBe(2)
      expect(store.accountsByType['savings']!.length).toBe(1)
    })

    it('excludes inactive accounts from accountsByType', () => {
      const store = useAccountsStore()
      store.accounts = [
        factories.account({ account_type: 'checking', is_active: true }),
        factories.account({ id: '2', account_type: 'checking', is_active: false }),
      ]

      expect(store.accountsByType['checking']!.length).toBe(1)
    })
  })

  describe('fetchAccounts', () => {
    it('does nothing when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAccountsStore()
      await store.fetchAccounts()

      expect(store.accounts).toEqual([])
      expect(accountsApi.listAccounts).not.toHaveBeenCalled()
    })

    it('fetches accounts for current budget', async () => {
      const store = useAccountsStore()
      await store.fetchAccounts()

      expect(accountsApi.listAccounts).toHaveBeenCalledWith('budget-1')
      expect(store.accounts.length).toBe(2)
      expect(store.loading).toBe(false)
    })

    it('sets loading state during fetch', async () => {
      const store = useAccountsStore()

      const fetchPromise = store.fetchAccounts()
      expect(store.loading).toBe(true)

      await fetchPromise
      expect(store.loading).toBe(false)
    })

    it('sets error on fetch failure', async () => {
      ;(accountsApi.listAccounts as Mock).mockRejectedValue(new Error('Network error'))

      const store = useAccountsStore()
      await expect(store.fetchAccounts()).rejects.toThrow()

      expect(store.error).toBeTruthy()
    })
  })

  describe('fetchAccount', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAccountsStore()
      await expect(store.fetchAccount('account-1')).rejects.toThrow('No budget selected')
    })

    it('fetches single account and updates cache', async () => {
      const store = useAccountsStore()
      store.accounts = [factories.account({ name: 'Old Name' })]

      const updatedAccount = factories.account({ name: 'Updated Name' })
      ;(accountsApi.getAccount as Mock).mockResolvedValue(updatedAccount)

      const result = await store.fetchAccount('account-1')

      expect(result.name).toBe('Updated Name')
      expect(store.accounts[0]!.name).toBe('Updated Name')
    })

    it('adds account to cache if not found', async () => {
      const store = useAccountsStore()
      store.accounts = []

      const newAccount = factories.account()
      ;(accountsApi.getAccount as Mock).mockResolvedValue(newAccount)

      await store.fetchAccount('account-1')

      expect(store.accounts.length).toBe(1)
    })
  })

  describe('createAccount', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAccountsStore()
      await expect(
        store.createAccount({ name: 'Test', account_type: 'checking' })
      ).rejects.toThrow('No budget selected')
    })

    it('creates account and adds to state', async () => {
      const store = useAccountsStore()
      store.accounts = []

      const account = await store.createAccount({
        name: 'New Account',
        account_type: 'savings',
      })

      expect(account.name).toBe('New Account')
      expect(store.accounts.length).toBe(1)
      expect(store.accounts[0]!.name).toBe('New Account')
    })

    it('calls API with correct parameters', async () => {
      const store = useAccountsStore()

      await store.createAccount({
        name: 'Test Account',
        account_type: 'checking',
        starting_balance: 10000,
      })

      expect(accountsApi.createAccount).toHaveBeenCalledWith('budget-1', {
        name: 'Test Account',
        account_type: 'checking',
        starting_balance: 10000,
      })
    })

    it('extracts error message from axios error', async () => {
      const axiosError = {
        response: { data: { detail: 'Account name already exists' } },
      }
      ;(accountsApi.createAccount as Mock).mockRejectedValue(axiosError)

      const store = useAccountsStore()

      await expect(
        store.createAccount({ name: 'Test', account_type: 'checking' })
      ).rejects.toThrow('Account name already exists')

      expect(store.error).toBe('Account name already exists')
    })
  })

  describe('updateAccount', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAccountsStore()
      await expect(store.updateAccount('account-1', { name: 'Updated' })).rejects.toThrow(
        'No budget selected'
      )
    })

    it('updates account in local cache', async () => {
      const store = useAccountsStore()
      store.accounts = [factories.account({ name: 'Original' })]

      ;(accountsApi.updateAccount as Mock).mockResolvedValue(
        factories.account({ name: 'Updated' })
      )

      await store.updateAccount('account-1', { name: 'Updated' })

      expect(store.accounts[0]!.name).toBe('Updated')
    })

    it('returns updated account', async () => {
      const store = useAccountsStore()
      store.accounts = [factories.account()]

      ;(accountsApi.updateAccount as Mock).mockResolvedValue(
        factories.account({ name: 'Updated' })
      )

      const result = await store.updateAccount('account-1', { name: 'Updated' })

      expect(result.name).toBe('Updated')
    })
  })

  describe('deleteAccount', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAccountsStore()
      await expect(store.deleteAccount('account-1')).rejects.toThrow('No budget selected')
    })

    it('removes account from state', async () => {
      const store = useAccountsStore()
      store.accounts = [
        factories.account({ id: 'account-1' }),
        factories.account({ id: 'account-2' }),
      ]

      await store.deleteAccount('account-1')

      expect(store.accounts.length).toBe(1)
      expect(store.accounts[0]!.id).toBe('account-2')
    })
  })

  describe('reconcileAccount', () => {
    it('throws when no budget selected', async () => {
      ;(useAuthStore as Mock).mockReturnValue({ currentBudgetId: null })

      const store = useAccountsStore()
      await expect(store.reconcileAccount('account-1', 10000)).rejects.toThrow(
        'No budget selected'
      )
    })

    it('calls reconcile API and refreshes account', async () => {
      const store = useAccountsStore()
      store.accounts = [factories.account({ cleared_balance: 5000, uncleared_balance: 0 })]

      ;(accountsApi.getAccount as Mock).mockResolvedValue(
        factories.account({ cleared_balance: 10000, uncleared_balance: 0 })
      )

      await store.reconcileAccount('account-1', 10000)

      expect(accountsApi.reconcileAccount).toHaveBeenCalledWith('budget-1', 'account-1', 10000)
      expect(store.accounts[0]!.cleared_balance).toBe(10000)
    })
  })

  describe('getAccountById', () => {
    it('returns account by id', () => {
      const store = useAccountsStore()
      store.accounts = [factories.account({ id: 'test-id', name: 'Test Account' })]

      const account = store.getAccountById('test-id')

      expect(account?.name).toBe('Test Account')
    })

    it('returns undefined for unknown id', () => {
      const store = useAccountsStore()
      store.accounts = []

      expect(store.getAccountById('unknown')).toBeUndefined()
    })
  })

  describe('reset', () => {
    it('clears all state', () => {
      const store = useAccountsStore()
      store.accounts = [factories.account()]
      store.error = 'Some error'

      store.reset()

      expect(store.accounts).toEqual([])
      expect(store.error).toBeNull()
    })
  })
})
