import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, Budget, BudgetMembership } from '@/types'
import { login as apiLogin, logout as apiLogout, getCurrentUser, register as apiRegister, updateCurrentUser } from '@/api/auth'
import type { UserUpdate } from '@/types'
import { getMyBudgets, createBudget as apiCreateBudget } from '@/api/budgets'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const budgets = ref<Budget[]>([])
  const currentBudgetId = ref<string | null>(null)
  const currentMembership = ref<BudgetMembership | null>(null)
  const initialized = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!user.value)
  const currentBudget = computed(() => budgets.value.find((b) => b.id === currentBudgetId.value) || null)

  // Actions
  async function initialize() {
    if (initialized.value) return

    try {
      loading.value = true
      // Try to get current user — if cookies exist, it succeeds; if not, it 401s
      user.value = await getCurrentUser()

      // Load budgets
      await loadBudgets()

      initialized.value = true
    } catch {
      // No valid session
      user.value = null
      initialized.value = true
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    try {
      loading.value = true
      error.value = null

      await apiLogin({ username, password })

      user.value = await getCurrentUser()

      // Load budgets
      await loadBudgets()

      // Redirect to dashboard or intended destination
      const redirect = router.currentRoute.value.query.redirect as string
      router.push(redirect || '/')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Login failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, password: string) {
    try {
      loading.value = true
      error.value = null

      await apiRegister({
        username,
        password,
      })

      // Auto-login after registration
      await login(username, password)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Registration failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await apiLogout()
    } catch {
      // Ignore logout errors
    } finally {
      user.value = null
      budgets.value = []
      currentBudgetId.value = null
      currentMembership.value = null
      router.push('/login')
    }
  }

  async function loadBudgets() {
    try {
      const response = await getMyBudgets()
      budgets.value = response.items

      // Restore previously selected budget from localStorage
      const savedBudgetId = localStorage.getItem('budge_current_budget')
      if (savedBudgetId && budgets.value.find((b) => b.id === savedBudgetId)) {
        currentBudgetId.value = savedBudgetId
      } else {
        // Auto-select first budget if none selected
        const firstBudget = budgets.value[0]
        if (firstBudget) {
          await selectBudget(firstBudget.id)
        }
      }
    } catch (e) {
      console.error('Failed to load budgets:', e)
      throw e
    }
  }

  async function selectBudget(budgetId: string) {
    currentBudgetId.value = budgetId
    // Store in localStorage for persistence
    localStorage.setItem('budge_current_budget', budgetId)

    // Load membership to get scopes
    // TODO: Implement this when needed
  }

  async function createBudget(name: string) {
    try {
      loading.value = true
      error.value = null

      const newBudget = await apiCreateBudget(name)

      // Refresh budget list and select the new budget
      await loadBudgets()
      await selectBudget(newBudget.id)

      return newBudget
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create budget'
      throw e
    } finally {
      loading.value = false
    }
  }

  function restoreBudgetSelection() {
    const savedBudgetId = localStorage.getItem('budge_current_budget')
    if (savedBudgetId && budgets.value.find((b) => b.id === savedBudgetId)) {
      currentBudgetId.value = savedBudgetId
    }
  }

  async function updateUser(data: UserUpdate) {
    try {
      loading.value = true
      error.value = null
      user.value = await updateCurrentUser(data)
      return user.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update profile'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    user,
    budgets,
    currentBudgetId,
    currentMembership,
    initialized,
    loading,
    error,
    // Getters
    isAuthenticated,
    currentBudget,
    // Actions
    initialize,
    login,
    register,
    logout,
    loadBudgets,
    selectBudget,
    createBudget,
    restoreBudgetSelection,
    updateUser,
  }
})
