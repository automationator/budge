import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Account } from '@/types'
import { useAuthStore } from './auth'
import {
  listAccounts,
  getAccount,
  createAccount as apiCreateAccount,
  updateAccount as apiUpdateAccount,
  deleteAccount as apiDeleteAccount,
  reconcileAccount as apiReconcileAccount,
  type AccountCreate,
  type AccountUpdate,
} from '@/api/accounts'

export const useAccountsStore = defineStore('accounts', () => {
  // State
  const accounts = ref<Account[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const isEditMode = ref(false)
  const reorderLoading = ref(false)

  // Getters
  const totalBalance = computed(() =>
    accounts.value
      .filter((a) => a.is_active && a.include_in_budget)
      .reduce((sum, a) => sum + a.cleared_balance + a.uncleared_balance, 0)
  )

  const activeAccounts = computed(() =>
    accounts.value.filter((a) => a.is_active).sort((a, b) => {
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
      return a.name.localeCompare(b.name)
    })
  )

  const budgetAccounts = computed(() =>
    activeAccounts.value.filter((a) => a.include_in_budget)
  )

  const trackingAccounts = computed(() =>
    activeAccounts.value.filter((a) => !a.include_in_budget)
  )

  const budgetTotalBalance = computed(() =>
    budgetAccounts.value.reduce(
      (sum, a) => sum + a.cleared_balance + a.uncleared_balance,
      0
    )
  )

  const trackingTotalBalance = computed(() =>
    trackingAccounts.value.reduce(
      (sum, a) => sum + a.cleared_balance + a.uncleared_balance,
      0
    )
  )

  const allAccountsTotalBalance = computed(() =>
    activeAccounts.value.reduce(
      (sum, a) => sum + a.cleared_balance + a.uncleared_balance,
      0
    )
  )

  const accountsByType = computed(() => {
    const grouped: Record<string, Account[]> = {}
    for (const account of activeAccounts.value) {
      const type = account.account_type
      if (!grouped[type]) {
        grouped[type] = []
      }
      grouped[type]!.push(account)
    }
    return grouped
  })

  // Actions
  async function fetchAccounts() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      accounts.value = await listAccounts(authStore.currentBudgetId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch accounts'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchAccount(accountId: string): Promise<Account> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const account = await getAccount(authStore.currentBudgetId, accountId)

      // Update in local cache
      const index = accounts.value.findIndex((a) => a.id === accountId)
      if (index >= 0) {
        accounts.value[index] = account
      } else {
        accounts.value.push(account)
      }

      return account
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch account'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createAccount(data: AccountCreate): Promise<Account> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const account = await apiCreateAccount(authStore.currentBudgetId, data)
      accounts.value.push(account)
      return account
    } catch (e: unknown) {
      // Extract error message from axios error or regular error
      let message = 'Failed to create account'
      if (e && typeof e === 'object' && 'response' in e) {
        const axiosError = e as { response?: { data?: { detail?: string } } }
        message = axiosError.response?.data?.detail || message
      } else if (e instanceof Error) {
        message = e.message
      }
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function updateAccount(accountId: string, data: AccountUpdate): Promise<Account> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const account = await apiUpdateAccount(authStore.currentBudgetId, accountId, data)

      // Update in local cache
      const index = accounts.value.findIndex((a) => a.id === accountId)
      if (index >= 0) {
        accounts.value[index] = account
      }

      return account
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update account'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteAccount(accountId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDeleteAccount(authStore.currentBudgetId, accountId)
      accounts.value = accounts.value.filter((a) => a.id !== accountId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete account'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function reconcileAccount(accountId: string, actualBalance: number): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiReconcileAccount(authStore.currentBudgetId, accountId, actualBalance)
      // Refresh the account to get updated balance
      await fetchAccount(accountId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to reconcile account'
      throw e
    } finally {
      loading.value = false
    }
  }

  function getAccountById(accountId: string): Account | undefined {
    return accounts.value.find((a) => a.id === accountId)
  }

  function reset() {
    accounts.value = []
    error.value = null
    isEditMode.value = false
  }

  // Edit mode and reordering
  function toggleEditMode() {
    isEditMode.value = !isEditMode.value
  }

  // Get accounts by section (budget vs tracking), sorted by sort_order
  function getAccountsInSection(isBudget: boolean): Account[] {
    return accounts.value
      .filter((a) => a.is_active && a.include_in_budget === isBudget)
      .sort((a, b) => {
        if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
        return a.name.localeCompare(b.name)
      })
  }

  // Initialize sort orders if any accounts have sort_order=0
  async function initializeSortOrders(): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    const needsInit = accounts.value.some((a) => a.is_active && a.sort_order === 0)
    if (!needsInit) return

    reorderLoading.value = true
    try {
      // Initialize budget accounts
      const budgetAccountsList = getAccountsInSection(true)
      for (let i = 0; i < budgetAccountsList.length; i++) {
        const account = budgetAccountsList[i]
        if (!account) continue
        const newOrder = (i + 1) * 10
        if (account.sort_order !== newOrder) {
          await updateAccount(account.id, { sort_order: newOrder })
        }
      }

      // Initialize tracking accounts
      const trackingAccountsList = getAccountsInSection(false)
      for (let i = 0; i < trackingAccountsList.length; i++) {
        const account = trackingAccountsList[i]
        if (!account) continue
        const newOrder = (i + 1) * 10
        if (account.sort_order !== newOrder) {
          await updateAccount(account.id, { sort_order: newOrder })
        }
      }

      // Refresh data
      await fetchAccounts()
    } finally {
      reorderLoading.value = false
    }
  }

  // Move account up within its section
  async function moveAccountUp(accountId: string): Promise<void> {
    const account = accounts.value.find((a) => a.id === accountId)
    if (!account) return

    const sectionAccounts = getAccountsInSection(account.include_in_budget)
    const currentIndex = sectionAccounts.findIndex((a) => a.id === accountId)
    if (currentIndex <= 0) return // Already at top

    const prevAccount = sectionAccounts[currentIndex - 1]
    if (!prevAccount) return
    await swapAccountSortOrders(account, prevAccount)
  }

  // Move account down within its section
  async function moveAccountDown(accountId: string): Promise<void> {
    const account = accounts.value.find((a) => a.id === accountId)
    if (!account) return

    const sectionAccounts = getAccountsInSection(account.include_in_budget)
    const currentIndex = sectionAccounts.findIndex((a) => a.id === accountId)
    if (currentIndex < 0 || currentIndex >= sectionAccounts.length - 1) return // Already at bottom

    const nextAccount = sectionAccounts[currentIndex + 1]
    if (!nextAccount) return
    await swapAccountSortOrders(account, nextAccount)
  }

  // Swap sort orders between two accounts
  async function swapAccountSortOrders(
    account1: Account,
    account2: Account
  ): Promise<void> {
    reorderLoading.value = true
    try {
      const temp = account1.sort_order
      await updateAccount(account1.id, { sort_order: account2.sort_order })
      await updateAccount(account2.id, { sort_order: temp })
    } finally {
      reorderLoading.value = false
    }
  }

  return {
    // State
    accounts,
    loading,
    error,
    isEditMode,
    reorderLoading,
    // Getters
    totalBalance,
    activeAccounts,
    budgetAccounts,
    trackingAccounts,
    budgetTotalBalance,
    trackingTotalBalance,
    allAccountsTotalBalance,
    accountsByType,
    // Actions
    fetchAccounts,
    fetchAccount,
    createAccount,
    updateAccount,
    deleteAccount,
    reconcileAccount,
    getAccountById,
    reset,
    // Reordering
    toggleEditMode,
    initializeSortOrders,
    moveAccountUp,
    moveAccountDown,
  }
})
