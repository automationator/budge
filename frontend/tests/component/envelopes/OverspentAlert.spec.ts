import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OverspentAlert from '@/components/envelopes/OverspentAlert.vue'
import { createComponentTestContext, populateStores } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import type { Envelope } from '@/types'

describe('OverspentAlert', () => {
  function mountComponent(envelopes: Envelope[] = []) {
    const testContext = createComponentTestContext()
    populateStores(testContext.pinia, { envelopes })

    return {
      wrapper: mount(OverspentAlert, {
        global: testContext.global,
      }),
      pinia: testContext.pinia,
    }
  }

  describe('visibility', () => {
    it('hides when no overspent envelopes', () => {
      const { wrapper } = mountComponent([
        factories.envelope({ current_balance: 50000 }), // positive balance
        factories.envelope({ id: 'e2', current_balance: 0 }), // zero balance
      ])
      expect(wrapper.find('[data-testid="overspent-alert"]').exists()).toBe(false)
    })

    it('shows when envelopes have negative balance', () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope({ id: 'e1', name: 'Groceries' }),
      ])
      expect(wrapper.find('[data-testid="overspent-alert"]').exists()).toBe(true)
    })

    it('does not count inactive envelopes as overspent', () => {
      const { wrapper } = mountComponent([
        factories.envelope({
          current_balance: -5000,
          is_active: false, // inactive
        }),
      ])
      expect(wrapper.find('[data-testid="overspent-alert"]').exists()).toBe(false)
    })

    it('does not count unallocated envelope as overspent', () => {
      const { wrapper } = mountComponent([
        factories.envelope({
          current_balance: -5000,
          is_unallocated: true, // unallocated
        }),
      ])
      expect(wrapper.find('[data-testid="overspent-alert"]').exists()).toBe(false)
    })
  })

  describe('content', () => {
    it('displays overspent envelope names', () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope({ id: 'e1', name: 'Groceries' }),
        factories.overspentEnvelope({ id: 'e2', name: 'Dining Out' }),
      ])
      expect(wrapper.text()).toContain('Groceries')
      expect(wrapper.text()).toContain('Dining Out')
    })

    it('displays overspent amounts', () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope({
          id: 'e1',
          name: 'Groceries',
          current_balance: -5000, // -$50
        }),
      ])
      expect(wrapper.text()).toContain('-$50.00')
    })

    it('displays title', () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope(),
      ])
      expect(wrapper.text()).toContain('Overspent Envelopes')
    })

    it('displays instructional text', () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope(),
      ])
      expect(wrapper.text()).toContain('spent more than budgeted')
    })
  })

  describe('cover button', () => {
    it('clicking cover button emits cover-envelope with that envelope id', async () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope({ id: 'first-overspent', name: 'Groceries' }),
        factories.overspentEnvelope({ id: 'second-overspent', name: 'Dining' }),
      ])

      // Find and click the second cover button
      const coverButtons = wrapper.findAll('.v-btn')
      expect(coverButtons.length).toBe(2)

      await coverButtons[1]!.trigger('click')
      expect(wrapper.emitted('cover-envelope')).toBeTruthy()
      expect(wrapper.emitted('cover-envelope')![0]).toEqual(['second-overspent'])
    })

    it('clicking first cover button emits that envelope id', async () => {
      const { wrapper } = mountComponent([
        factories.overspentEnvelope({ id: 'first-overspent', name: 'Groceries' }),
        factories.overspentEnvelope({ id: 'second-overspent', name: 'Dining' }),
      ])

      const coverButtons = wrapper.findAll('.v-btn')
      await coverButtons[0]!.trigger('click')
      expect(wrapper.emitted('cover-envelope')![0]).toEqual(['first-overspent'])
    })
  })

  describe('multiple overspent envelopes', () => {
    it('lists all overspent envelopes', () => {
      const { wrapper } = mountComponent([
        factories.envelope({ id: 'e1', name: 'Healthy', current_balance: 1000 }),
        factories.overspentEnvelope({ id: 'e2', name: 'Groceries', current_balance: -2500 }),
        factories.overspentEnvelope({ id: 'e3', name: 'Dining', current_balance: -1500 }),
        factories.envelope({ id: 'e4', name: 'Entertainment', current_balance: 500 }),
      ])
      expect(wrapper.text()).toContain('Groceries')
      expect(wrapper.text()).toContain('Dining')
      expect(wrapper.text()).not.toContain('Healthy')
      expect(wrapper.text()).not.toContain('Entertainment')
    })
  })
})
