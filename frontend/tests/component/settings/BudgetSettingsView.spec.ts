// UI rendering tests for BudgetSettingsView.
// Data-mutation tests (rename, delete, export/import, member CRUD, navigation)
// remain in frontend/tests/e2e/tests/budget-settings.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import BudgetSettingsView from '@/views/settings/BudgetSettingsView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'

const API_BASE = '/api/v1'

// Helper: mount and settle
async function mountAndSettle(options?: Parameters<typeof mountView>[1]) {
  const result = mountView(BudgetSettingsView, options)
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

describe('BudgetSettingsView', () => {
  describe('Budget Name', () => {
    it('displays current budget name', async () => {
      const { wrapper, authStore } = await mountAndSettle()
      // authStore.currentBudget is not set by mountView; the budget name comes from the store
      // Set the budget so the template can render it
      authStore.budgets = [factories.budget({ id: 'budget-1', name: 'My Budget' })]
      await flushPromises()

      expect(wrapper.text()).toContain('My Budget')
    })

    it('can cancel rename without saving', async () => {
      const { wrapper, authStore } = await mountAndSettle()
      authStore.budgets = [factories.budget({ id: 'budget-1', name: 'Original Name' })]
      await flushPromises()

      // Find and click the edit (pencil) button
      const pencilBtn = wrapper.findAll('.v-btn').find((b) => b.html().includes('mdi-pencil'))
      expect(pencilBtn).toBeTruthy()
      await pencilBtn!.trigger('click')
      await flushPromises()

      // Should show editing form with Save and Cancel
      expect(wrapper.text()).toContain('Save')
      expect(wrapper.text()).toContain('Cancel')

      // Click Cancel
      const cancelBtn = wrapper.findAll('.v-btn').find((b) => b.text() === 'Cancel')
      await cancelBtn!.trigger('click')
      await flushPromises()

      // Should show original name, not editing form
      expect(wrapper.text()).toContain('Original Name')
      expect(wrapper.text()).not.toContain('Save')
    })
  })

  describe('Budget Members', () => {
    it('displays member list', async () => {
      const { wrapper } = await mountAndSettle()
      expect(wrapper.text()).toContain('Budget Members')
      expect(wrapper.text()).toContain('testuser')
    })

    it('shows add member button for owner', async () => {
      const { wrapper } = await mountAndSettle()
      const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Member'))
      expect(addBtn).toBeTruthy()
    })

    it('can open add member dialog', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Member'))
      await addBtn!.trigger('click')
      await flushPromises()

      expect(document.body.textContent).toContain('Add Budget Member')
      expect(document.body.innerHTML).toContain('Username')
      expect(document.body.innerHTML).toContain('Role')
      wrapper.unmount()
    })

    it('can cancel add member dialog', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      // Open dialog
      const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Member'))
      await addBtn!.trigger('click')
      await flushPromises()

      // Cancel
      const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
      const cancelBtn = Array.from(dialogButtons).find((b) => b.textContent?.trim() === 'Cancel') as HTMLElement
      expect(cancelBtn).toBeTruthy()
      cancelBtn.click()
      await flushPromises()

      const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
      expect(dialogOverlay).toBeNull()
      wrapper.unmount()
    })

    it('hides add member button for non-owner', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/members`, () => {
          return HttpResponse.json([
            factories.budgetMember({ role: 'viewer' }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle()
      const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Member'))
      expect(addBtn).toBeUndefined()
    })

    it('member list shows role chips', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/members`, () => {
          return HttpResponse.json([
            factories.budgetMember({ id: 'user-1', username: 'testuser', role: 'owner' }),
            factories.budgetMember({ id: 'user-2', username: 'otheruser', role: 'member' }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle()
      expect(wrapper.text()).toContain('owner')
      expect(wrapper.text()).toContain('member')
      expect(wrapper.text()).toContain('testuser')
      expect(wrapper.text()).toContain('otheruser')
    })

    it('shows "You" indicator for current user', async () => {
      const { wrapper } = await mountAndSettle()
      // The "You" chip appears next to the current user's name
      const chips = wrapper.findAll('.v-chip')
      const youChip = chips.find((c) => c.text() === 'You')
      expect(youChip).toBeTruthy()
    })
  })

  describe('Danger Zone', () => {
    it('shows danger zone for owner', async () => {
      const { wrapper } = await mountAndSettle()
      expect(wrapper.text()).toContain('Danger Zone')
      expect(wrapper.text()).toContain('Delete Budget')
    })

    it('hides danger zone for non-owner', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/members`, () => {
          return HttpResponse.json([
            factories.budgetMember({ role: 'viewer' }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle()
      expect(wrapper.text()).not.toContain('Danger Zone')
    })

    it('opens delete confirmation dialog', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      const deleteBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Delete Budget'))
      expect(deleteBtn).toBeTruthy()
      await deleteBtn!.trigger('click')
      await flushPromises()

      expect(document.body.textContent).toContain('This action cannot be undone')
      expect(document.body.innerHTML).toContain('password')
      wrapper.unmount()
    })

    it('can cancel delete dialog', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      // Open dialog
      const deleteBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Delete Budget'))
      await deleteBtn!.trigger('click')
      await flushPromises()

      // Cancel
      const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
      const cancelBtn = Array.from(dialogButtons).find((b) => b.textContent?.trim() === 'Cancel') as HTMLElement
      expect(cancelBtn).toBeTruthy()
      cancelBtn.click()
      await flushPromises()

      const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
      expect(dialogOverlay).toBeNull()
      wrapper.unmount()
    })

    it('delete button disabled without password, shows error on wrong password', async () => {
      // Override delete to return 401
      server.use(
        http.delete(`${API_BASE}/budgets/:budgetId`, () => {
          return HttpResponse.json({ detail: 'Invalid password' }, { status: 401 })
        })
      )

      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      // Open dialog
      const deleteBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Delete Budget'))
      await deleteBtn!.trigger('click')
      await flushPromises()

      // Confirm button should be disabled (no password)
      const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
      const confirmBtn = Array.from(dialogButtons).find(
        (b) => b.textContent?.trim() === 'Delete Budget'
      ) as HTMLButtonElement
      expect(confirmBtn).toBeTruthy()
      expect(confirmBtn.disabled).toBe(true)

      // Type a wrong password
      const passwordInput = document.querySelector('.v-dialog input[type="password"]') as HTMLInputElement
      expect(passwordInput).toBeTruthy()
      passwordInput.value = 'wrongpassword'
      passwordInput.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()

      // Button should now be enabled
      expect(confirmBtn.disabled).toBe(false)

      // Click confirm
      confirmBtn.click()
      await flushPromises()
      await flushPromises()

      // Should show error message
      const errorMessages = document.querySelector('.v-dialog .v-messages__message')
      expect(errorMessages?.textContent).toContain('Invalid password')
      wrapper.unmount()
    })
  })

  describe('Data Management', () => {
    it('shows data management section for owner', async () => {
      const { wrapper } = await mountAndSettle()
      expect(wrapper.text()).toContain('Data Management')
      expect(wrapper.text()).toContain('Export Budget Data')
      expect(wrapper.text()).toContain('Import Budget Data')
      expect(wrapper.text()).toContain('Repair Balances')
    })

    it('hides data management for non-owner', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/members`, () => {
          return HttpResponse.json([
            factories.budgetMember({ role: 'viewer' }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle()
      expect(wrapper.text()).not.toContain('Data Management')
    })

    it('opens import dialog', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      const importBtn = wrapper.find('[data-testid="import-button"]')
      expect(importBtn.exists()).toBe(true)
      await importBtn.trigger('click')
      await flushPromises()

      expect(document.body.textContent).toContain('Import Budget Data')
      expect(document.body.innerHTML).toContain('Select export file')
      wrapper.unmount()
    })

    it('import button disabled without file or password', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      // Open import dialog
      const importBtn = wrapper.find('[data-testid="import-button"]')
      await importBtn.trigger('click')
      await flushPromises()

      // Confirm button should be disabled
      const confirmBtn = document.querySelector('[data-testid="import-confirm-button"]') as HTMLButtonElement
      expect(confirmBtn).toBeTruthy()
      expect(confirmBtn.disabled).toBe(true)
      wrapper.unmount()
    })

    it('can cancel import dialog', async () => {
      const { wrapper } = await mountAndSettle({ attachTo: document.body })

      // Open import dialog
      const importBtn = wrapper.find('[data-testid="import-button"]')
      await importBtn.trigger('click')
      await flushPromises()

      // Cancel
      const cancelBtn = document.querySelector('[data-testid="import-cancel-button"]') as HTMLElement
      expect(cancelBtn).toBeTruthy()
      cancelBtn.click()
      await flushPromises()

      const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
      expect(dialogOverlay).toBeNull()
      wrapper.unmount()
    })
  })
})
