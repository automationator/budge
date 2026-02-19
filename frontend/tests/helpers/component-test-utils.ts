import { mount, type ComponentMountingOptions } from '@vue/test-utils'
import { createTestingPinia, type TestingPinia } from '@pinia/testing'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { vi } from 'vitest'
import type { Component } from 'vue'
import type { Account, Envelope, Payee, Transaction, AllocationRule } from '@/types'
import { useAccountsStore } from '@/stores/accounts'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useEnvelopesStore } from '@/stores/envelopes'
import { usePayeesStore } from '@/stores/payees'
import { useTransactionsStore } from '@/stores/transactions'
import { useAllocationRulesStore } from '@/stores/allocationRules'

// Create a Vuetify instance for tests
export function createTestVuetify() {
  return createVuetify({
    components,
    directives,
  })
}

// Create a testing Pinia instance
export function createTestPinia(options?: { stubActions?: boolean }) {
  return createTestingPinia({
    createSpy: vi.fn,
    stubActions: options?.stubActions ?? false,
  })
}

// Component test context with Vuetify and Pinia configured
export interface ComponentTestContext {
  vuetify: ReturnType<typeof createVuetify>
  pinia: TestingPinia
  global: {
    plugins: [ReturnType<typeof createVuetify>, TestingPinia]
    stubs?: Record<string, boolean | Component>
  }
}

export function createComponentTestContext(options?: {
  stubActions?: boolean
  stubs?: Record<string, boolean | Component>
}): ComponentTestContext {
  const vuetify = createTestVuetify()
  const pinia = createTestPinia({ stubActions: options?.stubActions })

  return {
    vuetify,
    pinia,
    global: {
      plugins: [vuetify, pinia],
      stubs: options?.stubs,
    },
  }
}

// Helper to mount a component with test context
export function mountWithContext<T extends Component>(
  component: T,
  options?: Omit<ComponentMountingOptions<T>, 'global'> & {
    stubActions?: boolean
    stubs?: Record<string, boolean | Component>
  }
) {
  const { stubActions, stubs, ...mountOptions } = options || {}
  const context = createComponentTestContext({ stubActions, stubs })

  return {
    wrapper: mount(component, {
      ...mountOptions,
      global: {
        ...context.global,
        stubs: {
          ...context.global.stubs,
          ...stubs,
        },
      },
    } as ComponentMountingOptions<T>),
    pinia: context.pinia,
    vuetify: context.vuetify,
  }
}

// Store data population interface
export interface StoreData {
  accounts?: Account[]
  envelopes?: Envelope[]
  payees?: Payee[]
  transactions?: Transaction[]
  allocationRules?: AllocationRule[]
}

// Populate stores with test data
export function populateStores(pinia: TestingPinia, data: StoreData): void {
  if (data.accounts) {
    const accountsStore = useAccountsStore(pinia)
    accountsStore.accounts = data.accounts
    accountsStore.loading = false
  }

  if (data.envelopes) {
    const envelopesStore = useEnvelopesStore(pinia)
    envelopesStore.envelopes = data.envelopes
    envelopesStore.loading = false
  }

  if (data.payees) {
    const payeesStore = usePayeesStore(pinia)
    payeesStore.payees = data.payees
    payeesStore.loading = false
  }

  if (data.transactions) {
    const transactionsStore = useTransactionsStore(pinia)
    transactionsStore.transactions = data.transactions
    transactionsStore.loading = false
  }

  if (data.allocationRules) {
    const rulesStore = useAllocationRulesStore(pinia)
    rulesStore.allocationRules = data.allocationRules
    rulesStore.loading = false
  }
}

// Helper to wait for Vue to process updates
export async function flushPromises(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

// Helper to mount auth view components (LoginView, RegisterView) without pre-authenticated user
export function mountAuthView<T extends Component>(
  component: T,
  options?: Omit<ComponentMountingOptions<T>, 'global'> & {
    stubActions?: boolean
    stubs?: Record<string, boolean | Component>
    registrationEnabled?: boolean
  }
) {
  const { stubActions, stubs, registrationEnabled = true, ...mountOptions } = options || {}
  const context = createComponentTestContext({ stubActions, stubs })

  const appStore = useAppStore(context.pinia)
  appStore.registrationEnabled = registrationEnabled

  const authStore = useAuthStore(context.pinia)

  return {
    wrapper: mount(component, {
      ...mountOptions,
      global: {
        ...context.global,
        stubs: {
          ...context.global.stubs,
          ...stubs,
        },
      },
    } as ComponentMountingOptions<T>),
    pinia: context.pinia,
    vuetify: context.vuetify,
    authStore,
    appStore,
  }
}

// Helper to mount view components that require auth store (currentBudgetId)
export function mountView<T extends Component>(
  component: T,
  options?: Omit<ComponentMountingOptions<T>, 'global'> & {
    stubActions?: boolean
    stubs?: Record<string, boolean | Component>
    budgetId?: string
  }
) {
  const { stubActions, stubs, budgetId, ...mountOptions } = options || {}
  const context = createComponentTestContext({ stubActions, stubs })

  // Set up auth store so views with onMounted can proceed
  const authStore = useAuthStore(context.pinia)
  authStore.currentBudgetId = budgetId ?? 'budget-1'
  authStore.user = { id: 'user-1', username: 'testuser', is_active: true, is_admin: false, created_at: '2024-01-01T00:00:00Z', updated_at: null }

  return {
    wrapper: mount(component, {
      ...mountOptions,
      global: {
        ...context.global,
        stubs: {
          ...context.global.stubs,
          ...stubs,
        },
      },
    } as ComponentMountingOptions<T>),
    pinia: context.pinia,
    vuetify: context.vuetify,
    authStore,
  }
}
