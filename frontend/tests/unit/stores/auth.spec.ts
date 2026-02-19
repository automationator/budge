import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { createTestPinia, factories } from '@test/setup'

// Mock the router
vi.mock('@/router', () => ({
  default: {
    push: vi.fn(),
    currentRoute: {
      value: {
        query: {},
      },
    },
  },
}))

// Mock the auth API
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  getCurrentUser: vi.fn(),
  updateCurrentUser: vi.fn(),
}))

// Mock the budgets API
vi.mock('@/api/budgets', () => ({
  getMyBudgets: vi.fn(),
}))

import * as authApi from '@/api/auth'
import * as budgetsApi from '@/api/budgets'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createTestPinia())
    vi.clearAllMocks()

    // Set up default mock implementations
    ;(authApi.login as Mock).mockResolvedValue(undefined)
    ;(authApi.getCurrentUser as Mock).mockResolvedValue(factories.user())
    ;(authApi.logout as Mock).mockResolvedValue(undefined)
    ;(authApi.register as Mock).mockResolvedValue(factories.user())
    ;(authApi.updateCurrentUser as Mock).mockImplementation(async (data) =>
      factories.user(data)
    )
    ;(budgetsApi.getMyBudgets as Mock).mockResolvedValue(
      factories.cursorPage([factories.budget()])
    )
  })

  describe('initial state', () => {
    it('has correct initial values', () => {
      const store = useAuthStore()

      expect(store.user).toBeNull()
      expect(store.budgets).toEqual([])
      expect(store.currentBudgetId).toBeNull()
      expect(store.currentMembership).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.initialized).toBe(false)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('computes isAuthenticated based on user', () => {
      const store = useAuthStore()

      expect(store.isAuthenticated).toBe(false)

      store.user = factories.user()
      expect(store.isAuthenticated).toBe(true)
    })

    it('computes currentBudget based on currentBudgetId', () => {
      const store = useAuthStore()
      store.budgets = [factories.budget({ id: 'budget-1' }), factories.budget({ id: 'budget-2', name: 'Work' })]

      expect(store.currentBudget).toBeNull()

      store.currentBudgetId = 'budget-2'
      expect(store.currentBudget?.name).toBe('Work')
    })
  })

  describe('login', () => {
    it('authenticates with valid credentials', async () => {
      const store = useAuthStore()

      await store.login('testuser', 'password')

      expect(store.isAuthenticated).toBe(true)
      expect(store.user).toBeDefined()
      expect(store.user?.username).toBe('testuser')
      expect(store.budgets.length).toBeGreaterThan(0)
      expect(store.error).toBeNull()
    })

    it('rejects invalid credentials', async () => {
      const store = useAuthStore()
      ;(authApi.login as Mock).mockRejectedValue(new Error('Invalid credentials'))

      await expect(store.login('wrong', 'wrong')).rejects.toThrow()

      expect(store.isAuthenticated).toBe(false)
      expect(store.user).toBeNull()
      expect(store.error).toBeTruthy()
    })

    it('sets loading state during login', async () => {
      const store = useAuthStore()

      // Start login but don't await
      const loginPromise = store.login('testuser', 'password')

      // Check loading is true during login
      expect(store.loading).toBe(true)

      await loginPromise

      expect(store.loading).toBe(false)
    })

    it('clears previous error on new login attempt', async () => {
      const store = useAuthStore()
      ;(authApi.login as Mock).mockRejectedValueOnce(new Error('Invalid credentials'))

      // First attempt - should fail
      try {
        await store.login('wrong', 'wrong')
      } catch {
        // Expected
      }
      expect(store.error).toBeTruthy()

      // Second attempt - should clear error
      const loginPromise = store.login('testuser', 'password')
      expect(store.error).toBeNull()

      await loginPromise
    })

    it('auto-selects first budget after login', async () => {
      const store = useAuthStore()

      await store.login('testuser', 'password')

      expect(store.currentBudgetId).toBe('budget-1')
    })
  })

  describe('logout', () => {
    it('clears user state', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      await store.logout()

      expect(store.user).toBeNull()
      expect(store.budgets).toEqual([])
      expect(store.currentBudgetId).toBeNull()
      expect(store.currentMembership).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })

    it('calls logout API', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      await store.logout()

      expect(authApi.logout).toHaveBeenCalled()
    })

    it('handles logout API errors gracefully', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      // Override the logout handler to fail
      ;(authApi.logout as Mock).mockRejectedValue(new Error('Server error'))

      // Should not throw and still clear state
      await store.logout()

      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('register', () => {
    it('registers and auto-logs in', async () => {
      const store = useAuthStore()

      await store.register('newuser', 'password123')

      expect(store.isAuthenticated).toBe(true)
      expect(store.user).toBeDefined()
    })

    it('sets error on registration failure', async () => {
      const store = useAuthStore()
      ;(authApi.register as Mock).mockRejectedValue(new Error('Username already exists'))

      await expect(store.register('existing', 'password')).rejects.toThrow()

      expect(store.error).toBeTruthy()
    })
  })

  describe('initialize', () => {
    it('restores session when cookies are valid', async () => {
      const store = useAuthStore()
      await store.initialize()

      expect(store.initialized).toBe(true)
      expect(store.isAuthenticated).toBe(true)
      expect(store.user).toBeDefined()
    })

    it('clears state when no valid session', async () => {
      ;(authApi.getCurrentUser as Mock).mockRejectedValue(new Error('Unauthorized'))

      const store = useAuthStore()
      await store.initialize()

      expect(store.initialized).toBe(true)
      expect(store.isAuthenticated).toBe(false)
      expect(store.user).toBeNull()
    })

    it('only initializes once', async () => {
      const store = useAuthStore()
      await store.initialize()
      await store.initialize()

      // Should have only called the API once
      expect(authApi.getCurrentUser).toHaveBeenCalledTimes(1)
      expect(store.initialized).toBe(true)
    })
  })

  describe('selectBudget', () => {
    it('updates current budget', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      await store.selectBudget('budget-1')

      expect(store.currentBudgetId).toBe('budget-1')
    })

    it('persists budget selection to localStorage', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      await store.selectBudget('budget-1')

      expect(localStorage.setItem).toHaveBeenCalledWith('budge_current_budget', 'budget-1')
    })
  })

  describe('loadBudgets', () => {
    it('loads budgets for user', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      expect(store.budgets.length).toBeGreaterThan(0)
    })

    it('restores previously selected budget from localStorage', async () => {
      vi.mocked(localStorage.getItem).mockReturnValue('budget-1')

      const store = useAuthStore()
      await store.login('testuser', 'password')

      // Should restore the budget from localStorage
      expect(store.currentBudgetId).toBe('budget-1')
    })
  })

  describe('updateUser', () => {
    it('updates user profile', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')

      const updatedUser = await store.updateUser({ username: 'updateduser' })

      expect(updatedUser.username).toBe('updateduser')
      expect(store.user?.username).toBe('updateduser')
    })

    it('sets error on update failure', async () => {
      const store = useAuthStore()
      await store.login('testuser', 'password')
      ;(authApi.updateCurrentUser as Mock).mockRejectedValue(new Error('Validation error'))

      await expect(store.updateUser({ username: 'x' })).rejects.toThrow()

      expect(store.error).toBeTruthy()
    })
  })
})
