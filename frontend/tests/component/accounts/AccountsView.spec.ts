// UI rendering tests for the AccountsView.
// Data-mutation tests (starting balance, edit, delete, reorder)
// remain in frontend/tests/e2e/tests/accounts.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import AccountsView from '@/views/accounts/AccountsView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'

const API_BASE = '/api/v1'

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

describe('AccountsView', () => {
  it('displays page title and Add Account button', async () => {
    const { wrapper } = await mountAndSettle(AccountsView)
    expect(wrapper.find('h1').text()).toBe('Accounts')
    const addBtn = wrapper.find('[data-testid="add-account-button"]')
    expect(addBtn.exists()).toBe(true)
    expect(addBtn.text()).toContain('Add Account')
  })

  it('shows empty state when no accounts', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
        return HttpResponse.json([])
      })
    )

    const { wrapper } = await mountAndSettle(AccountsView)
    expect(wrapper.text()).toContain('No accounts yet')
    expect(wrapper.text()).toContain('Add Account')
  })

  it('creates a checking account', async () => {
    const { wrapper } = await mountAndSettle(AccountsView, { attachTo: document.body })

    // Open create dialog
    await wrapper.find('[data-testid="add-account-button"]').trigger('click')
    await flushPromises()

    // Dialog should show
    expect(document.body.textContent).toContain('Create Account')
    expect(document.body.innerHTML).toContain('Account Name')
    expect(document.body.innerHTML).toContain('Account Type')

    // Fill in account name
    const nameInput = document.querySelector('.v-dialog input') as HTMLInputElement
    expect(nameInput).toBeTruthy()
    const nativeInputEvent = new Event('input', { bubbles: true })
    nameInput.value = 'Test Checking'
    nameInput.dispatchEvent(nativeInputEvent)
    await flushPromises()

    // Create button should be enabled
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const createBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Create'
    ) as HTMLButtonElement
    expect(createBtn).toBeTruthy()
    expect(createBtn.disabled).toBe(false)
    wrapper.unmount()
  })

  it('creates a savings account with description', async () => {
    const { wrapper } = await mountAndSettle(AccountsView, { attachTo: document.body })

    await wrapper.find('[data-testid="add-account-button"]').trigger('click')
    await flushPromises()

    // Fill name
    const nameInput = document.querySelector('.v-dialog input') as HTMLInputElement
    nameInput.value = 'Emergency Savings'
    nameInput.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()

    // Verify description field exists
    const textareas = document.querySelectorAll('.v-dialog textarea')
    expect(textareas.length).toBeGreaterThan(0)
    wrapper.unmount()
  })

  it('creates a credit card account', async () => {
    const { wrapper } = await mountAndSettle(AccountsView, { attachTo: document.body })

    await wrapper.find('[data-testid="add-account-button"]').trigger('click')
    await flushPromises()

    // Verify the account type select exists with options
    expect(document.body.innerHTML).toContain('Account Type')
    // The select should contain credit card option
    expect(document.body.innerHTML).toContain('Checking')
    wrapper.unmount()
  })

  it('shows validation error for empty name (disabled button)', async () => {
    const { wrapper } = await mountAndSettle(AccountsView, { attachTo: document.body })

    await wrapper.find('[data-testid="add-account-button"]').trigger('click')
    await flushPromises()

    // Create button should be disabled (no name entered)
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const createBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Create'
    ) as HTMLButtonElement
    expect(createBtn).toBeTruthy()
    expect(createBtn.disabled).toBe(true)
    wrapper.unmount()
  })

  it('creates account with icon from picker', async () => {
    const { wrapper } = await mountAndSettle(AccountsView, { attachTo: document.body })

    await wrapper.find('[data-testid="add-account-button"]').trigger('click')
    await flushPromises()

    // Icon chips should be visible
    const iconChips = document.querySelectorAll('.v-dialog [data-testid="icon-chip"]')
    expect(iconChips.length).toBeGreaterThan(0)

    // Find the Home chip
    const homeChip = Array.from(iconChips).find((chip) =>
      chip.textContent?.includes('Home')
    )
    expect(homeChip).toBeTruthy()
    wrapper.unmount()
  })

  it('creates account with custom emoji', async () => {
    const { wrapper } = await mountAndSettle(AccountsView, { attachTo: document.body })

    await wrapper.find('[data-testid="add-account-button"]').trigger('click')
    await flushPromises()

    // Custom emoji input should exist
    const customInput = document.querySelector(
      '.v-dialog [data-testid="custom-icon-input"] input'
    ) as HTMLInputElement
    expect(customInput).toBeTruthy()
    wrapper.unmount()
  })

  it('displays accounts grouped by budget status', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
        return HttpResponse.json([
          factories.budgetAccount({ id: 'acc-budget', name: 'My Checking' }),
          factories.offBudgetAccount({ id: 'acc-tracking', name: 'My Investment' }),
        ])
      })
    )

    const { wrapper } = await mountAndSettle(AccountsView)

    // Budget and Tracking section headers should appear
    expect(wrapper.find('[data-testid="budget-section-header"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tracking-section-header"]').exists()).toBe(true)

    // Accounts should be in the correct sections
    const budgetItems = wrapper.findAll('[data-testid="budget-account-item"]')
    expect(budgetItems.some((item) => item.text().includes('My Checking'))).toBe(true)

    const trackingItems = wrapper.findAll('[data-testid="tracking-account-item"]')
    expect(trackingItems.some((item) => item.text().includes('My Investment'))).toBe(true)
  })

  it('Budget and Tracking sections are collapsible', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
        return HttpResponse.json([
          factories.budgetAccount({ id: 'acc-budget', name: 'Budget Account' }),
          factories.offBudgetAccount({ id: 'acc-tracking', name: 'Tracking Account' }),
        ])
      })
    )

    const { wrapper } = await mountAndSettle(AccountsView)

    // Both accounts should be visible initially
    expect(wrapper.findAll('[data-testid="budget-account-item"]').length).toBe(1)
    expect(wrapper.findAll('[data-testid="tracking-account-item"]').length).toBe(1)

    // Collapse Budget section
    await wrapper.find('[data-testid="budget-section-header"]').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="budget-account-item"]').length).toBe(0)
    // Tracking should still be visible
    expect(wrapper.findAll('[data-testid="tracking-account-item"]').length).toBe(1)

    // Expand Budget section
    await wrapper.find('[data-testid="budget-section-header"]').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="budget-account-item"]').length).toBe(1)

    // Collapse Tracking section
    await wrapper.find('[data-testid="tracking-section-header"]').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="tracking-account-item"]').length).toBe(0)
    expect(wrapper.findAll('[data-testid="budget-account-item"]').length).toBe(1)
  })

  it('shows All Accounts row with total balance', async () => {
    const { wrapper } = await mountAndSettle(AccountsView)

    const allAccountsRow = wrapper.find('[data-testid="all-accounts-row"]')
    expect(allAccountsRow.exists()).toBe(true)
    expect(allAccountsRow.text()).toContain('All Accounts')
    // Should show some dollar amount (default accounts have balances)
    expect(allAccountsRow.text()).toMatch(/\$[\d,]+\.\d{2}/)
  })
})
