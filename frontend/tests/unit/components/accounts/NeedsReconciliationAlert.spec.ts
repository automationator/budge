import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import NeedsReconciliationAlert from '@/components/accounts/NeedsReconciliationAlert.vue'
import { createComponentTestContext, populateStores } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import { mockRouterInstance } from '@test/setup'
import type { Account } from '@/types'

describe('NeedsReconciliationAlert', () => {
  function mountComponent(accounts: Account[] = []) {
    const testContext = createComponentTestContext()
    populateStores(testContext.pinia, { accounts })

    return {
      wrapper: mount(NeedsReconciliationAlert, {
        global: testContext.global,
      }),
      pinia: testContext.pinia,
    }
  }

  // Helper to create a date string N days ago
  function daysAgo(days: number): string {
    const date = new Date()
    date.setDate(date.getDate() - days)
    return date.toISOString()
  }

  beforeEach(() => {
    mockRouterInstance.push.mockClear()
  })

  describe('visibility', () => {
    it('hides when no accounts need reconciliation', () => {
      const { wrapper } = mountComponent([
        factories.recentlyReconciledAccount({ id: 'a1', name: 'Checking' }),
      ])
      expect(wrapper.find('[data-testid="needs-reconciliation-alert"]').exists()).toBe(false)
    })

    it('shows when account has never been reconciled', () => {
      const { wrapper } = mountComponent([
        factories.account({ id: 'a1', name: 'Checking', last_reconciled_at: null }),
      ])
      expect(wrapper.find('[data-testid="needs-reconciliation-alert"]').exists()).toBe(true)
    })

    it('shows when account reconciled over 30 days ago', () => {
      const { wrapper } = mountComponent([
        factories.staleAccount({ id: 'a1', name: 'Checking' }),
      ])
      expect(wrapper.find('[data-testid="needs-reconciliation-alert"]').exists()).toBe(true)
    })

    it('hides when account reconciled exactly 30 days ago', () => {
      const { wrapper } = mountComponent([
        factories.account({
          id: 'a1',
          name: 'Checking',
          last_reconciled_at: daysAgo(30),
        }),
      ])
      expect(wrapper.find('[data-testid="needs-reconciliation-alert"]').exists()).toBe(false)
    })

    it('does not count inactive accounts', () => {
      const { wrapper } = mountComponent([
        factories.account({
          id: 'a1',
          name: 'Old Account',
          is_active: false,
          last_reconciled_at: null,
        }),
      ])
      expect(wrapper.find('[data-testid="needs-reconciliation-alert"]').exists()).toBe(false)
    })
  })

  describe('content', () => {
    it('displays account names needing reconciliation', () => {
      const { wrapper } = mountComponent([
        factories.staleAccount({ id: 'a1', name: 'Checking' }),
        factories.staleAccount({ id: 'a2', name: 'Savings' }),
      ])
      expect(wrapper.text()).toContain('Checking')
      expect(wrapper.text()).toContain('Savings')
    })

    it('displays title', () => {
      const { wrapper } = mountComponent([
        factories.staleAccount(),
      ])
      expect(wrapper.text()).toContain('Accounts Need Reconciliation')
    })

    it('displays instructional text', () => {
      const { wrapper } = mountComponent([
        factories.staleAccount(),
      ])
      expect(wrapper.text()).toContain("haven't been reconciled in over 30 days")
    })

    it('displays "Never" for accounts never reconciled', () => {
      const { wrapper } = mountComponent([
        factories.account({ id: 'a1', name: 'New Account', last_reconciled_at: null }),
      ])
      expect(wrapper.text()).toContain('Never')
    })

    it('displays days ago for stale accounts', () => {
      const { wrapper } = mountComponent([
        factories.account({
          id: 'a1',
          name: 'Old Account',
          last_reconciled_at: daysAgo(45),
        }),
      ])
      expect(wrapper.text()).toContain('45 days ago')
    })
  })

  describe('navigation', () => {
    it('navigates to account page when clicking days button', async () => {
      const { wrapper } = mountComponent([
        factories.staleAccount({ id: 'test-account-id', name: 'Checking' }),
      ])
      const button = wrapper.find('.v-btn')
      await button.trigger('click')
      expect(mockRouterInstance.push).toHaveBeenCalledWith('/accounts/test-account-id')
    })
  })

  describe('multiple accounts', () => {
    it('only lists accounts needing reconciliation', () => {
      const { wrapper } = mountComponent([
        factories.account({ id: 'a1', name: 'Healthy', last_reconciled_at: daysAgo(5) }),
        factories.staleAccount({ id: 'a2', name: 'Stale' }),
        factories.account({ id: 'a3', name: 'Never', last_reconciled_at: null }),
        factories.recentlyReconciledAccount({ id: 'a4', name: 'Recent' }),
      ])
      expect(wrapper.text()).toContain('Stale')
      expect(wrapper.text()).toContain('Never')
      expect(wrapper.text()).not.toContain('Healthy')
      expect(wrapper.text()).not.toContain('Recent')
    })
  })
})
