// UI rendering tests for settings views.
// Data-mutation tests (profile updates, CRUD operations, navigation URL checks)
// remain in frontend/tests/e2e/tests/settings.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import SettingsView from '@/views/settings/SettingsView.vue'
import NotificationSettingsView from '@/views/settings/NotificationSettingsView.vue'
import PayeesSettingsView from '@/views/settings/PayeesSettingsView.vue'
import LocationsSettingsView from '@/views/settings/LocationsSettingsView.vue'
import StartFreshView from '@/views/settings/StartFreshView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'

const API_BASE = '/api/v1'

// Helper: mount and settle
async function mountAndSettle<T extends Parameters<typeof mountView>[0]>(component: T, options?: Parameters<typeof mountView>[1]) {
  const result = mountView(component, options)
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

describe('SettingsView', () => {
  it('displays profile card with user info', async () => {
    const { wrapper } = await mountAndSettle(SettingsView)
    expect(wrapper.text()).toContain('testuser')
    expect(wrapper.text()).toContain('Edit Profile')
  })

  it('displays security card', async () => {
    const { wrapper } = await mountAndSettle(SettingsView)
    expect(wrapper.text()).toContain('Security')
    expect(wrapper.text()).toContain('Change Password')
  })

  it('displays navigation links', async () => {
    const { wrapper } = await mountAndSettle(SettingsView)
    expect(wrapper.text()).toContain('Budget Settings')
    expect(wrapper.text()).toContain('Notification Preferences')
    expect(wrapper.text()).toContain('Manage Locations')
    expect(wrapper.text()).toContain('Manage Payees')
    expect(wrapper.text()).toContain('Start Fresh')
  })

  it('can start editing profile', async () => {
    const { wrapper } = await mountAndSettle(SettingsView)

    const editBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Edit Profile'))
    expect(editBtn).toBeTruthy()
    await editBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Save Changes')
    expect(wrapper.text()).toContain('Cancel')
    // Username input should appear
    const usernameField = wrapper.findAll('.v-text-field').find(
      (f) => f.html().includes('Username')
    )
    expect(usernameField).toBeTruthy()
  })

  it('can cancel profile editing', async () => {
    const { wrapper } = await mountAndSettle(SettingsView)

    // Start editing
    const editBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Edit Profile'))
    await editBtn!.trigger('click')
    await flushPromises()

    // Cancel
    const cancelBtn = wrapper.findAll('.v-btn').find((b) => b.text() === 'Cancel')
    await cancelBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Edit Profile')
    expect(wrapper.text()).not.toContain('Save Changes')
  })

  it('can open password change dialog', async () => {
    const { wrapper } = await mountAndSettle(SettingsView, { attachTo: document.body })

    const changeBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Change Password'))
    expect(changeBtn).toBeTruthy()
    await changeBtn!.trigger('click')
    await flushPromises()

    // Dialog teleports to body
    expect(document.body.textContent).toContain('New Password')
    expect(document.body.textContent).toContain('Confirm Password')
    wrapper.unmount()
  })

  it('can cancel password change dialog', async () => {
    const { wrapper } = await mountAndSettle(SettingsView, { attachTo: document.body })

    // Open dialog
    const changeBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Change Password'))
    await changeBtn!.trigger('click')
    await flushPromises()

    // Find cancel button in the teleported dialog
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const cancelBtn = Array.from(dialogButtons).find((b) => b.textContent?.trim() === 'Cancel') as HTMLElement
    expect(cancelBtn).toBeTruthy()
    cancelBtn.click()
    await flushPromises()

    // Dialog should be hidden - check no "New Password" in dialog overlay
    const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
    expect(dialogOverlay).toBeNull()
    wrapper.unmount()
  })
})

describe('Admin Settings', () => {
  it('shows admin card for admin users', async () => {
    const { wrapper, authStore } = mountView(SettingsView)
    authStore.user = factories.user({ is_admin: true })
    await flushPromises()
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Admin Settings')
    expect(wrapper.text()).toContain('Allow new user registration')
  })

  it('hides admin card for non-admin users', async () => {
    const { wrapper } = await mountAndSettle(SettingsView)
    expect(wrapper.text()).not.toContain('Admin Settings')
  })

  it('registration switch reflects API state', async () => {
    server.use(
      http.get('/api/v1/admin/settings', () => {
        return HttpResponse.json({ registration_enabled: false })
      })
    )
    const { wrapper, authStore } = mountView(SettingsView)
    authStore.user = factories.user({ is_admin: true })
    await flushPromises()
    await flushPromises()
    await flushPromises()

    // Admin card should be visible
    expect(wrapper.text()).toContain('Admin Settings')

    // The switch should be unchecked (registration disabled)
    const switchInput = wrapper.find('.v-switch input[type="checkbox"]')
    expect(switchInput.exists()).toBe(true)
    expect((switchInput.element as HTMLInputElement).checked).toBe(false)
  })
})

describe('NotificationSettingsView', () => {
  it('displays notifications card', async () => {
    const { wrapper } = await mountAndSettle(NotificationSettingsView)
    // The main card should have notification list items
    expect(wrapper.text()).toContain('Low Balance Alerts')
  })

  it('displays about card', async () => {
    const { wrapper } = await mountAndSettle(NotificationSettingsView)
    expect(wrapper.text()).toContain('About Notifications')
  })

  it('shows all notification types', async () => {
    const { wrapper } = await mountAndSettle(NotificationSettingsView)
    expect(wrapper.text()).toContain('Low Balance Alerts')
    expect(wrapper.text()).toContain('Upcoming Expenses')
    expect(wrapper.text()).toContain('Recurring Not Funded')
    expect(wrapper.text()).toContain('Goal Reached')
  })
})

describe('PayeesSettingsView', () => {
  it('displays payees list', async () => {
    const { wrapper } = await mountAndSettle(PayeesSettingsView)
    expect(wrapper.text()).toContain('Manage Payees')
    // Default handler returns one payee
    expect(wrapper.text()).toContain('Grocery Store')
  })

  it('shows empty state when no payees', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
        return HttpResponse.json([])
      })
    )

    const { wrapper } = await mountAndSettle(PayeesSettingsView)
    expect(wrapper.text()).toContain('No payees yet')
  })

  it('shows add payee button', async () => {
    const { wrapper } = await mountAndSettle(PayeesSettingsView)
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Payee'))
    expect(addBtn).toBeTruthy()
  })

  it('can open add payee dialog', async () => {
    const { wrapper } = await mountAndSettle(PayeesSettingsView, { attachTo: document.body })

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Payee'))
    await addBtn!.trigger('click')
    await flushPromises()

    const body = document.body
    expect(body.textContent).toContain('Add Payee')
    expect(body.innerHTML).toContain('Name')
    expect(body.innerHTML).toContain('Icon')
    expect(body.querySelector('.v-dialog textarea')).toBeTruthy() // Description
    expect(body.textContent).toContain('Default Envelope')
    wrapper.unmount()
  })

  it('can cancel add payee dialog', async () => {
    const { wrapper } = await mountAndSettle(PayeesSettingsView, { attachTo: document.body })

    // Open dialog
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Payee'))
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
})

describe('LocationsSettingsView', () => {
  it('displays locations list', async () => {
    const { wrapper } = await mountAndSettle(LocationsSettingsView)
    expect(wrapper.text()).toContain('Manage Locations')
  })

  it('shows empty state when no locations', async () => {
    const { wrapper } = await mountAndSettle(LocationsSettingsView)
    // Default handler returns empty array
    expect(wrapper.text()).toContain('No locations yet')
  })

  it('shows add location button', async () => {
    const { wrapper } = await mountAndSettle(LocationsSettingsView)
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Location'))
    expect(addBtn).toBeTruthy()
  })

  it('can open add location dialog', async () => {
    const { wrapper } = await mountAndSettle(LocationsSettingsView, { attachTo: document.body })

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Location'))
    await addBtn!.trigger('click')
    await flushPromises()

    const body = document.body
    expect(body.textContent).toContain('Add Location')
    expect(body.innerHTML).toContain('Name')
    expect(body.innerHTML).toContain('Icon')
    expect(body.querySelector('.v-dialog textarea')).toBeTruthy() // Description
    wrapper.unmount()
  })

  it('can cancel add location dialog', async () => {
    const { wrapper } = await mountAndSettle(LocationsSettingsView, { attachTo: document.body })

    // Open dialog
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Location'))
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
})

describe('StartFreshView', () => {
  it('displays warning alert', async () => {
    const { wrapper } = await mountAndSettle(StartFreshView)
    expect(wrapper.text()).toContain('Danger Zone')
    expect(wrapper.text()).toContain('permanently delete')
  })

  it('shows category selection', async () => {
    const { wrapper } = await mountAndSettle(StartFreshView)
    expect(wrapper.text()).toContain('Delete ALL data')
    expect(wrapper.text()).toContain('Select specific data types')
  })

  it('shows selective checkboxes when selective mode selected', async () => {
    const { wrapper } = await mountAndSettle(StartFreshView)

    // Default mode is 'selective', so checkboxes should already be visible
    expect(wrapper.text()).toContain('Transactions')
    expect(wrapper.text()).toContain('Recurring Transactions')
    expect(wrapper.text()).toContain('Envelopes')
    expect(wrapper.text()).toContain('Clear envelope allocations')
    expect(wrapper.text()).toContain('Accounts')
    expect(wrapper.text()).toContain('Payees')
    expect(wrapper.text()).toContain('Locations')
  })
})
