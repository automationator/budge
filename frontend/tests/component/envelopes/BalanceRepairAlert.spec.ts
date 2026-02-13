import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BalanceRepairAlert from '@/components/envelopes/BalanceRepairAlert.vue'
import { createComponentTestContext } from '@test/helpers/component-test-utils'
import { useAuthStore } from '@/stores/auth'

describe('BalanceRepairAlert', () => {
  function mountComponent(options: {
    needsRepair: boolean
    loading?: boolean
    isOwner?: boolean
  }) {
    const testContext = createComponentTestContext()

    const authStore = useAuthStore(testContext.pinia)
    authStore.user = {
      id: 'user-1',
      username: 'testuser',
      is_active: true,
      is_admin: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: null,
    }
    authStore.currentBudget = {
      id: 'budget-1',
      name: 'Test Budget',
      owner_id: options.isOwner !== false ? 'user-1' : 'other-user',
      default_income_allocation: 'unallocated',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: null,
    }

    return {
      wrapper: mount(BalanceRepairAlert, {
        props: {
          needsRepair: options.needsRepair,
          loading: options.loading ?? false,
        },
        global: testContext.global,
      }),
    }
  }

  describe('visibility', () => {
    it('hides when needsRepair is false', () => {
      const { wrapper } = mountComponent({ needsRepair: false })
      expect(wrapper.find('[data-testid="balance-repair-alert"]').exists()).toBe(false)
    })

    it('shows when needsRepair is true', () => {
      const { wrapper } = mountComponent({ needsRepair: true })
      expect(wrapper.find('[data-testid="balance-repair-alert"]').exists()).toBe(true)
    })
  })

  describe('content', () => {
    it('displays title', () => {
      const { wrapper } = mountComponent({ needsRepair: true })
      expect(wrapper.text()).toContain('Balance Mismatch Detected')
    })

    it('displays instructional text', () => {
      const { wrapper } = mountComponent({ needsRepair: true })
      expect(wrapper.text()).toContain('out of sync')
    })
  })

  describe('repair button', () => {
    it('shows repair button for budget owner', () => {
      const { wrapper } = mountComponent({ needsRepair: true, isOwner: true })
      expect(wrapper.text()).toContain('Repair Balances')
    })

    it('hides repair button for non-owner', () => {
      const { wrapper } = mountComponent({ needsRepair: true, isOwner: false })
      expect(wrapper.text()).not.toContain('Repair Balances')
      expect(wrapper.text()).toContain('Ask the budget owner')
    })

    it('clicking repair button emits repair event', async () => {
      const { wrapper } = mountComponent({ needsRepair: true, isOwner: true })
      const repairButton = wrapper.find('.v-btn')
      await repairButton.trigger('click')
      expect(wrapper.emitted('repair')).toBeTruthy()
    })
  })
})
