// UI rendering tests for NavDrawer component.
// Navigation URL-verification tests remain in
// frontend/tests/e2e/tests/nav-drawer.spec.ts.

import { vi, describe, it, expect } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { VApp } from 'vuetify/components'

// Mock useDisplay to return desktop mode (mobile: false).
// NavDrawer has v-if="!mobile" so it only renders on non-mobile viewports.
vi.mock('vuetify', async (importOriginal) => {
  const { ref } = await import('vue')
  const actual = await importOriginal<typeof import('vuetify')>()
  return {
    ...actual,
    useDisplay: () => ({ mobile: ref(false) }),
  }
})

import NavDrawer from '@/components/layout/NavDrawer.vue'
import { mountView, populateStores, flushPromises } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'

// VNavigationDrawer requires a Vuetify layout provider (VApp).
const NavDrawerWrapper = defineComponent({
  components: { VApp, NavDrawer },
  template: '<v-app><NavDrawer /></v-app>',
})

function mountNavDrawer(options?: { attachTo?: Element }) {
  return mountView(NavDrawerWrapper, {
    stubs: { BudgetMenu: true },
    ...options,
  })
}

describe('NavDrawer', () => {
  describe('Budget Menu', () => {
    it('renders BudgetMenu at top of drawer', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()
      expect(wrapper.find('.v-navigation-drawer').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'BudgetMenu' }).exists()).toBe(true)
    })
  })

  describe('Main Navigation', () => {
    it('shows main navigation items', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()
      const text = wrapper.text()
      expect(text).toContain('Envelopes')
      expect(text).toContain('Transactions')
      expect(text).toContain('Reports')
    })

    it('shows correct icons for main nav items', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()
      expect(wrapper.find('.mdi-email-outline').exists()).toBe(true)
      expect(wrapper.find('.mdi-format-list-bulleted').exists()).toBe(true)
      expect(wrapper.find('.mdi-chart-bar').exists()).toBe(true)
    })
  })

  describe('More Section', () => {
    it('shows More section', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()
      expect(wrapper.text()).toContain('More')
    })

    it('More section starts collapsed', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()

      // v-list-group adds v-list-group--open class when expanded
      const listGroup = wrapper.find('.v-list-group')
      expect(listGroup.exists()).toBe(true)
      expect(listGroup.classes()).not.toContain('v-list-group--open')
    })

    it('expanding More section shows child items', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()

      // Click the More list-group activator
      const moreItem = wrapper.findAll('.v-list-item').find((item) => item.text().includes('More'))
      expect(moreItem).toBeTruthy()
      await moreItem!.trigger('click')
      await nextTick()
      await nextTick()

      expect(wrapper.text()).toContain('Allocation Rules')
      expect(wrapper.text()).toContain('Recurring Transactions')
    })
  })

  describe('Accounts Section', () => {
    it('shows All Accounts link', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()
      expect(wrapper.text()).toContain('All Accounts')
    })

    it('shows Budget section when budget accounts exist', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.budgetAccount({ name: 'My Checking' })],
      })
      await nextTick()

      expect(wrapper.text()).toContain('Budget')
      expect(wrapper.text()).toContain('My Checking')
    })

    it('hides Budget section when no budget accounts exist', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.offBudgetAccount({ name: 'Investment' })],
      })
      await nextTick()

      const listItems = wrapper.findAll('.v-list-item')
      const budgetHeader = listItems.find(
        (item) => item.text().includes('Budget') && !item.text().includes('All')
      )
      expect(budgetHeader).toBeUndefined()
    })

    it('Budget section expands and collapses', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.budgetAccount({ name: 'Test Checking' })],
      })
      await nextTick()

      // Account should be visible (expanded by default)
      expect(wrapper.text()).toContain('Test Checking')

      // Click the Budget header to collapse
      const budgetHeader = wrapper.findAll('.v-list-item').find(
        (item) => item.text().includes('Budget') && !item.text().includes('All')
      )
      expect(budgetHeader).toBeTruthy()
      await budgetHeader!.trigger('click')
      await nextTick()

      // Account should be hidden
      expect(wrapper.text()).not.toContain('Test Checking')

      // Click again to expand
      await budgetHeader!.trigger('click')
      await nextTick()

      // Account should be visible again
      expect(wrapper.text()).toContain('Test Checking')
    })

    it('shows multiple budget accounts', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [
          factories.budgetAccount({ id: 'a1', name: 'Checking' }),
          factories.budgetAccount({ id: 'a2', name: 'Savings' }),
        ],
      })
      await nextTick()

      expect(wrapper.text()).toContain('Checking')
      expect(wrapper.text()).toContain('Savings')
    })

    it('shows Tracking section when tracking accounts exist', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.offBudgetAccount({ name: 'Investment Account' })],
      })
      await nextTick()

      expect(wrapper.text()).toContain('Tracking')
      expect(wrapper.text()).toContain('Investment Account')
    })

    it('hides Tracking section when no tracking accounts exist', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.budgetAccount({ name: 'Checking' })],
      })
      await nextTick()

      const listItems = wrapper.findAll('.v-list-item')
      const trackingHeader = listItems.find((item) => item.text().includes('Tracking'))
      expect(trackingHeader).toBeUndefined()
    })

    it('Tracking section expands and collapses', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.offBudgetAccount({ name: 'My Investment' })],
      })
      await nextTick()

      // Account should be visible (expanded by default)
      expect(wrapper.text()).toContain('My Investment')

      // Click the Tracking header to collapse
      const trackingHeader = wrapper.findAll('.v-list-item').find(
        (item) => item.text().includes('Tracking')
      )
      expect(trackingHeader).toBeTruthy()
      await trackingHeader!.trigger('click')
      await nextTick()

      // Account should be hidden
      expect(wrapper.text()).not.toContain('My Investment')

      // Click again to expand
      await trackingHeader!.trigger('click')
      await nextTick()

      // Account should be visible again
      expect(wrapper.text()).toContain('My Investment')
    })

    it('shows chevron icons for expand/collapse state', async () => {
      const { wrapper, pinia } = mountNavDrawer()
      await flushPromises()
      populateStores(pinia, {
        accounts: [factories.budgetAccount({ name: 'Checking' })],
      })
      await nextTick()

      // Expanded by default - should show chevron-up
      expect(wrapper.find('.mdi-chevron-up').exists()).toBe(true)

      // Collapse
      const budgetHeader = wrapper.findAll('.v-list-item').find(
        (item) => item.text().includes('Budget') && !item.text().includes('All')
      )
      await budgetHeader!.trigger('click')
      await nextTick()

      // Should now show chevron-down
      expect(wrapper.find('.mdi-chevron-down').exists()).toBe(true)
    })
  })

  describe('Add Account Button', () => {
    it('shows Add Account button', async () => {
      const { wrapper } = mountNavDrawer()
      await flushPromises()
      expect(wrapper.text()).toContain('Add Account')
    })

    it('Add Account button opens create account dialog', async () => {
      const { wrapper } = mountNavDrawer({ attachTo: document.body })
      await flushPromises()

      const addBtn = wrapper.findAll('.v-btn').find((btn) => btn.text().includes('Add Account'))
      expect(addBtn).toBeTruthy()
      await addBtn!.trigger('click')
      await nextTick()
      await nextTick()

      const dialog = document.querySelector('.v-dialog')
      expect(dialog).toBeTruthy()
      expect(dialog!.textContent).toContain('Create Account')
      wrapper.unmount()
    })
  })
})
