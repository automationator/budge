// UI rendering tests for BottomNav component.
// Navigation URL-verification tests remain in
// frontend/tests/e2e/tests/bottom-nav.mobile.spec.ts.

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { VApp } from 'vuetify/components'
import BottomNav from '@/components/layout/BottomNav.vue'
import { showTransactionDialog } from '@/composables/useGlobalTransactionDialog'
import { mountWithContext } from '@test/helpers/component-test-utils'
import { mockRouteInstance, mockRouterInstance } from '@test/setup'

// In test env, Vuetify useDisplay() returns mobile=true since matchMedia
// returns matches:false, so the v-if="mobile" renders by default.

// VBottomNavigation requires a Vuetify layout provider (VApp).
// Wrap BottomNav in a VApp so the layout injection is available.
const BottomNavWrapper = defineComponent({
  components: { VApp, BottomNav },
  template: '<v-app><BottomNav /></v-app>',
})

function mountBottomNav(options?: { attachTo?: Element }) {
  return mountWithContext(BottomNavWrapper, {
    stubs: { BudgetMenu: true },
    ...options,
  })
}

function findBtnByText(wrapper: ReturnType<typeof mountWithContext>['wrapper'], text: string) {
  return wrapper.findAll('.v-btn').find((b) => b.text().includes(text))
}

describe('BottomNav', () => {
  beforeEach(() => {
    mockRouteInstance.path = '/'
    mockRouterInstance.push.mockClear()
    showTransactionDialog.value = false
  })

  describe('Visibility', () => {
    it('renders bottom navigation when mobile is true', () => {
      const { wrapper } = mountBottomNav()
      expect(wrapper.find('.v-bottom-navigation').exists()).toBe(true)
    })

    it('shows all five main tab buttons', () => {
      const { wrapper } = mountBottomNav()
      expect(findBtnByText(wrapper, 'Envelopes')).toBeTruthy()
      expect(findBtnByText(wrapper, 'Accounts')).toBeTruthy()
      expect(findBtnByText(wrapper, 'Add')).toBeTruthy()
      expect(findBtnByText(wrapper, 'Reports')).toBeTruthy()
      expect(findBtnByText(wrapper, 'More')).toBeTruthy()
    })
  })

  describe('Active Tab Highlighting', () => {
    it('highlights Envelopes tab when route is /', () => {
      mockRouteInstance.path = '/'
      const { wrapper } = mountBottomNav()
      const envelopesBtn = findBtnByText(wrapper, 'Envelopes')!
      expect(envelopesBtn.classes().some((c) => c.includes('active'))).toBe(true)
    })

    it('highlights Accounts tab when route is /accounts', () => {
      mockRouteInstance.path = '/accounts'
      const { wrapper } = mountBottomNav()
      const accountsBtn = findBtnByText(wrapper, 'Accounts')!
      expect(accountsBtn.classes().some((c) => c.includes('active'))).toBe(true)
    })

    it('highlights Reports tab when route is /reports', () => {
      mockRouteInstance.path = '/reports'
      const { wrapper } = mountBottomNav()
      const reportsBtn = findBtnByText(wrapper, 'Reports')!
      expect(reportsBtn.classes().some((c) => c.includes('active'))).toBe(true)
    })

    it('highlights More tab when route is /transactions', () => {
      mockRouteInstance.path = '/transactions'
      const { wrapper } = mountBottomNav()
      const moreBtn = findBtnByText(wrapper, 'More')!
      expect(moreBtn.classes().some((c) => c.includes('active'))).toBe(true)
    })
  })

  describe('Add Transaction Button', () => {
    it('opens transaction dialog when Add button clicked', async () => {
      const { wrapper } = mountBottomNav()
      const addBtn = findBtnByText(wrapper, 'Add')!
      await addBtn.trigger('click')
      expect(showTransactionDialog.value).toBe(true)
    })

    it('does not call router.push', async () => {
      const { wrapper } = mountBottomNav()
      const addBtn = findBtnByText(wrapper, 'Add')!
      await addBtn.trigger('click')
      expect(mockRouterInstance.push).not.toHaveBeenCalled()
    })
  })

  describe('More Menu', () => {
    it('More button opens bottom sheet', async () => {
      const { wrapper } = mountBottomNav({ attachTo: document.body })
      const moreBtn = findBtnByText(wrapper, 'More')!
      await moreBtn.trigger('click')
      await nextTick()
      await nextTick()

      const sheet = document.querySelector('.v-bottom-sheet')
      expect(sheet).toBeTruthy()
      wrapper.unmount()
    })

    it('bottom sheet shows navigation items', async () => {
      const { wrapper } = mountBottomNav({ attachTo: document.body })
      const moreBtn = findBtnByText(wrapper, 'More')!
      await moreBtn.trigger('click')
      await nextTick()
      await nextTick()

      const bodyText = document.body.textContent
      expect(bodyText).toContain('Transactions')
      expect(bodyText).toContain('Recurring')
      expect(bodyText).toContain('Allocation Rules')
      expect(bodyText).toContain('Notifications')
      wrapper.unmount()
    })

    it('bottom sheet closes on Escape key', async () => {
      const { wrapper } = mountBottomNav({ attachTo: document.body })
      const moreBtn = findBtnByText(wrapper, 'More')!
      await moreBtn.trigger('click')
      await nextTick()
      await nextTick()

      // Sheet should be open
      const sheetOverlay = document.querySelector('.v-bottom-sheet')
      expect(sheetOverlay).toBeTruthy()

      // Vuetify overlays listen for keydown on the overlay element
      sheetOverlay!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await nextTick()
      await nextTick()
      await nextTick()

      // The overlay should no longer be active
      const activeOverlay = document.querySelector('.v-overlay--active.v-bottom-sheet')
      expect(activeOverlay).toBeFalsy()
      wrapper.unmount()
    })
  })
})
