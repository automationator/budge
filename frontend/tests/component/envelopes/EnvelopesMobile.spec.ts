// Mobile-specific UI tests for EnvelopesView.
// CSS @media tests (activity/action-buttons hidden, balance visible)
// remain in frontend/tests/e2e/tests/envelopes.mobile.spec.ts.

import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import EnvelopesView from '@/views/envelopes/EnvelopesView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import { mockRouterInstance } from '@test/setup'

const API_BASE = '/api/v1'

let originalInnerWidth: number

// Helper: mount and settle
async function mountAndSettle<T extends Parameters<typeof mountView>[0]>(
  component: T,
  options?: Parameters<typeof mountView>[1]
) {
  const result = mountView(component, options)
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

describe('EnvelopesView Mobile', () => {
  beforeEach(() => {
    originalInnerWidth = window.innerWidth
    Object.defineProperty(window, 'innerWidth', { value: 430, writable: true, configurable: true })
    mockRouterInstance.push.mockClear()
  })

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', { value: originalInnerWidth, writable: true, configurable: true })
  })

  describe('Action Sheet', () => {
    it('tapping envelope opens action sheet', async () => {
      const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

      // Click on the Groceries envelope row
      const rows = wrapper.findAll('.budget-row')
      expect(rows.length).toBeGreaterThan(0)
      await rows[0].trigger('click')
      await flushPromises()

      // Action sheet (v-bottom-sheet) should be visible
      const bottomSheet = document.querySelector('.v-bottom-sheet')
      expect(bottomSheet).toBeTruthy()
      expect(document.body.textContent).toContain('Groceries')

      wrapper.unmount()
    })

    it('action sheet shows correct options', async () => {
      const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

      // Click on an envelope row
      const rows = wrapper.findAll('.budget-row')
      await rows[0].trigger('click')
      await flushPromises()

      // Verify all options are present
      const body = document.body
      expect(body.textContent).toContain('Transfer Money')
      expect(body.textContent).toContain('Add Transaction')
      expect(body.textContent).toContain('View Activity')
      expect(body.textContent).toContain('View Details')

      wrapper.unmount()
    })

    it('Transfer option opens transfer dialog', async () => {
      const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

      // Open action sheet
      const rows = wrapper.findAll('.budget-row')
      await rows[0].trigger('click')
      await flushPromises()

      // Click Transfer Money option
      const listItems = document.querySelectorAll('.v-bottom-sheet .v-list-item')
      const transferItem = Array.from(listItems).find((item) =>
        item.textContent?.includes('Transfer Money')
      ) as HTMLElement
      expect(transferItem).toBeTruthy()
      transferItem.click()
      await flushPromises()

      // Transfer dialog should appear
      expect(document.body.textContent).toContain('Transfer Money')
      // The dialog should have From/To envelope selects
      const dialog = document.querySelector('.v-dialog')
      expect(dialog).toBeTruthy()

      wrapper.unmount()
    })

    it('View Activity opens activity dialog', async () => {
      // Add handler for the activity endpoint
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/envelopes/:envelopeId/activity`, () => {
          return HttpResponse.json({
            envelope_id: 'envelope-1',
            envelope_name: 'Groceries',
            start_date: '2024-01-01',
            end_date: '2024-01-31',
            items: [],
            total: 0,
          })
        })
      )

      const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

      // Open action sheet
      const rows = wrapper.findAll('.budget-row')
      await rows[0].trigger('click')
      await flushPromises()

      // Click View Activity option
      const listItems = document.querySelectorAll('.v-bottom-sheet .v-list-item')
      const activityItem = Array.from(listItems).find((item) =>
        item.textContent?.includes('View Activity')
      ) as HTMLElement
      expect(activityItem).toBeTruthy()
      activityItem.click()
      await flushPromises()

      // Activity dialog should appear
      expect(document.body.textContent).toContain('Groceries Activity')

      wrapper.unmount()
    })

    it('View Details navigates to envelope detail page', async () => {
      const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

      // Open action sheet
      const rows = wrapper.findAll('.budget-row')
      await rows[0].trigger('click')
      await flushPromises()

      // Click View Details option
      const listItems = document.querySelectorAll('.v-bottom-sheet .v-list-item')
      const detailsItem = Array.from(listItems).find((item) =>
        item.textContent?.includes('View Details')
      ) as HTMLElement
      expect(detailsItem).toBeTruthy()
      detailsItem.click()
      await flushPromises()

      // Should navigate to envelope detail page
      expect(mockRouterInstance.push).toHaveBeenCalledWith('/envelopes/envelope-1')

      wrapper.unmount()
    })
  })

  describe('Action Sheet Dismissal', () => {
    it('action sheet closes when an action is selected', async () => {
      const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

      // Open action sheet
      const rows = wrapper.findAll('.budget-row')
      await rows[0].trigger('click')
      await flushPromises()

      // Action sheet should be visible
      expect(document.querySelector('.v-bottom-sheet')).toBeTruthy()
      expect(document.body.textContent).toContain('Transfer Money')

      // Selecting an action should close the action sheet
      const listItems = document.querySelectorAll('.v-bottom-sheet .v-list-item')
      const viewDetailsItem = Array.from(listItems).find((item) =>
        item.textContent?.includes('View Details')
      ) as HTMLElement
      expect(viewDetailsItem).toBeTruthy()
      viewDetailsItem.click()
      await flushPromises()
      await flushPromises()

      // The action sheet's v-card should no longer render (v-if="envelope" when modelValue is false)
      const actionSheetComponent = wrapper.findComponent({ name: 'EnvelopeActionSheet' })
      expect(actionSheetComponent.props('modelValue')).toBe(false)

      wrapper.unmount()
    })
  })
})
