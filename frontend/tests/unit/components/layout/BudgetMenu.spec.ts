// UI rendering tests for BudgetMenu component.
// Integration tests (switch budget, create budget, navigation, logout)
// remain in frontend/tests/e2e/tests/budget-menu.spec.ts.

import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import BudgetMenu from '@/components/layout/BudgetMenu.vue'
import { useAuthStore } from '@/stores/auth'
import { mountWithContext } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import { mockRouterInstance } from '@test/setup'

const MENU_LIST = '.v-overlay--active.v-menu .v-list'
const MENU_ITEMS = '.v-overlay--active.v-menu .v-list .v-list-item'

function mountBudgetMenu(options?: {
  variant?: 'sidebar' | 'bottomsheet'
  budgets?: ReturnType<typeof factories.budget>[]
  currentBudgetId?: string
  attachTo?: Element
}) {
  const {
    variant,
    budgets = [factories.budget()],
    currentBudgetId = budgets[0]?.id ?? 'budget-1',
    attachTo,
  } = options || {}

  const result = mountWithContext(BudgetMenu, {
    props: variant ? { variant } : {},
    attachTo,
  })

  const authStore = useAuthStore(result.pinia)
  authStore.user = factories.user()
  authStore.budgets = budgets
  authStore.currentBudgetId = currentBudgetId

  return result
}

async function openMenu(wrapper: ReturnType<typeof mountWithContext>['wrapper']) {
  await wrapper.find('.budget-selector-header').trigger('click')
  await nextTick()
  await nextTick()
}

describe('BudgetMenu', () => {
  beforeEach(() => {
    mockRouterInstance.push.mockClear()
  })

  describe('Header display', () => {
    it('displays current budget name and username in header', async () => {
      const { wrapper } = mountBudgetMenu()
      await nextTick()

      expect(wrapper.find('.v-list-item-title').text()).toBe('Personal')
      expect(wrapper.find('.v-list-item-subtitle').text()).toBe('@testuser')
    })

    it('sidebar variant applies pa-4 padding', async () => {
      const { wrapper } = mountBudgetMenu({ variant: 'sidebar' })
      await nextTick()

      const header = wrapper.find('.budget-selector-header')
      expect(header.classes()).toContain('pa-4')
    })

    it('bottomsheet variant applies pa-3 padding', async () => {
      const { wrapper } = mountBudgetMenu({ variant: 'bottomsheet' })
      await nextTick()

      const header = wrapper.find('.budget-selector-header')
      expect(header.classes()).toContain('pa-3')
    })
  })

  describe('Dropdown menu', () => {
    it('opens dropdown menu when clicking header', async () => {
      const { wrapper } = mountBudgetMenu({ attachTo: document.body })
      await nextTick()
      await openMenu(wrapper)

      const menuContent = document.querySelector(MENU_LIST)
      expect(menuContent).toBeTruthy()
      wrapper.unmount()
    })

    it('opens dropdown from bottomsheet variant', async () => {
      const { wrapper } = mountBudgetMenu({ variant: 'bottomsheet', attachTo: document.body })
      await nextTick()
      await openMenu(wrapper)

      const menuContent = document.querySelector(MENU_LIST)
      expect(menuContent).toBeTruthy()
      wrapper.unmount()
    })

    it('shows budget list with checkmark on active budget', async () => {
      const budget1 = factories.budget({ id: 'budget-1', name: 'Personal' })
      const budget2 = factories.budget({ id: 'budget-2', name: 'Business' })
      const { wrapper } = mountBudgetMenu({
        budgets: [budget1, budget2],
        currentBudgetId: 'budget-1',
        attachTo: document.body,
      })
      await nextTick()
      await openMenu(wrapper)

      const menuContent = document.querySelector(MENU_LIST)
      const bodyText = menuContent!.textContent
      expect(bodyText).toContain('Personal')
      expect(bodyText).toContain('Business')

      // Check icon exists on the active budget item
      const checkIcons = menuContent!.querySelectorAll('.mdi-check')
      expect(checkIcons.length).toBe(1)
      wrapper.unmount()
    })

    it('shows all navigation items in dropdown', async () => {
      const { wrapper } = mountBudgetMenu({ attachTo: document.body })
      await nextTick()
      await openMenu(wrapper)

      const menuContent = document.querySelector(MENU_LIST)
      const bodyText = menuContent!.textContent
      expect(bodyText).toContain('Settings')
      expect(bodyText).toContain('Manage Locations')
      expect(bodyText).toContain('Manage Payees')
      expect(bodyText).toContain('Budget Settings')
      expect(bodyText).toContain('Start Fresh')
      expect(bodyText).toContain('Log Out')
      wrapper.unmount()
    })

    it('toggles chevron icon based on menu state', async () => {
      const { wrapper } = mountBudgetMenu({ attachTo: document.body })
      await nextTick()

      // Closed: chevron-down
      expect(wrapper.find('.mdi-chevron-down').exists()).toBe(true)
      expect(wrapper.find('.mdi-chevron-up').exists()).toBe(false)

      await openMenu(wrapper)

      // Open: chevron-up
      expect(wrapper.find('.mdi-chevron-up').exists()).toBe(true)
      expect(wrapper.find('.mdi-chevron-down').exists()).toBe(false)
      wrapper.unmount()
    })
  })

  describe('Create budget dialog', () => {
    it('Create New Budget item opens create dialog', async () => {
      const { wrapper } = mountBudgetMenu({ attachTo: document.body })
      await nextTick()
      await openMenu(wrapper)

      // Click "Create New Budget"
      const menuItems = document.querySelectorAll(MENU_ITEMS)
      const createItem = Array.from(menuItems).find((el) => el.textContent?.includes('Create New Budget'))
      expect(createItem).toBeTruthy()
      ;(createItem as HTMLElement).click()
      await nextTick()
      await nextTick()

      // Dialog should be open
      const dialog = document.querySelector('.v-dialog')
      expect(dialog).toBeTruthy()
      expect(dialog!.textContent).toContain('Create New Budget')
      wrapper.unmount()
    })

    it('Create button disabled when budget name is empty', async () => {
      const { wrapper } = mountBudgetMenu({ attachTo: document.body })
      await nextTick()
      await openMenu(wrapper)

      // Open create dialog
      const menuItems = document.querySelectorAll(MENU_ITEMS)
      const createItem = Array.from(menuItems).find((el) => el.textContent?.includes('Create New Budget'))
      ;(createItem as HTMLElement).click()
      await nextTick()
      await nextTick()

      // Find the Create button in the dialog
      const dialogButtons = document.querySelectorAll('.v-dialog .v-card-actions .v-btn')
      const createBtn = Array.from(dialogButtons).find((el) => el.textContent?.includes('Create'))
      expect(createBtn).toBeTruthy()
      expect((createBtn as HTMLButtonElement).disabled).toBe(true)
      wrapper.unmount()
    })

    it('Cancel button closes create dialog', async () => {
      const { wrapper } = mountBudgetMenu({ attachTo: document.body })
      await nextTick()
      await openMenu(wrapper)

      // Open create dialog
      const menuItems = document.querySelectorAll(MENU_ITEMS)
      const createItem = Array.from(menuItems).find((el) => el.textContent?.includes('Create New Budget'))
      ;(createItem as HTMLElement).click()
      await nextTick()
      await nextTick()

      // Click Cancel
      const dialogButtons = document.querySelectorAll('.v-dialog .v-card-actions .v-btn')
      const cancelBtn = Array.from(dialogButtons).find((el) => el.textContent?.includes('Cancel'))
      expect(cancelBtn).toBeTruthy()
      ;(cancelBtn as HTMLElement).click()
      await nextTick()
      await nextTick()

      // Dialog should be closed
      const activeDialog = document.querySelector('.v-overlay--active.v-dialog')
      expect(activeDialog).toBeFalsy()
      wrapper.unmount()
    })
  })
})
