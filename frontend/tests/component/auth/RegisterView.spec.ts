import { describe, it, expect, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import RegisterView from '@/views/auth/RegisterView.vue'
import { mountAuthView, flushPromises } from '@test/helpers/component-test-utils'
import { snackbar } from '@/composables/useSnackbar'

function mountRegister(options?: Parameters<typeof mountAuthView>[1]) {
  return mountAuthView(RegisterView, options)
}

describe('RegisterView', () => {
  beforeEach(() => {
    snackbar.show = false
    snackbar.message = ''
    snackbar.color = 'info'
  })

  it('displays registration form with all three fields', () => {
    const { wrapper } = mountRegister()

    expect(wrapper.find('input[name="username"]').exists()).toBe(true)
    expect(wrapper.find('input[name="password"]').exists()).toBe(true)
    expect(wrapper.find('input[name="confirmPassword"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Register')
    expect(wrapper.text()).toContain('Create Account')
  })

  it('password fields toggle visibility together', async () => {
    const { wrapper } = mountRegister()

    const passwordInput = wrapper.find('input[name="password"]')
    const confirmInput = wrapper.find('input[name="confirmPassword"]')

    expect(passwordInput.attributes('type')).toBe('password')
    expect(confirmInput.attributes('type')).toBe('password')

    // Vuetify renders append-icon in .v-input__append
    const passwordField = wrapper.findAll('.v-text-field').find((f) => f.find('input[name="password"]').exists())!
    const appendIcon = passwordField.find('.v-input__append .v-icon')
    await appendIcon.trigger('click')

    expect(passwordInput.attributes('type')).toBe('text')
    expect(confirmInput.attributes('type')).toBe('text')
  })

  it('shows login link', () => {
    const { wrapper } = mountRegister()

    const cardActions = wrapper.find('.v-card-actions')
    expect(cardActions.exists()).toBe(true)
    expect(cardActions.text()).toContain('Already have an account?')
    expect(cardActions.text()).toContain('Login')
  })

  it('does not submit when fields are empty', async () => {
    const { wrapper, authStore } = mountRegister()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(authStore.register).not.toHaveBeenCalled()
  })

  it('does not submit when passwords do not match', async () => {
    const { wrapper, authStore } = mountRegister({ stubActions: true })

    const usernameInput = wrapper.find('input[name="username"]').element as HTMLInputElement
    usernameInput.value = 'newuser'
    usernameInput.dispatchEvent(new Event('input', { bubbles: true }))

    const passwordInput = wrapper.find('input[name="password"]').element as HTMLInputElement
    passwordInput.value = 'password123'
    passwordInput.dispatchEvent(new Event('input', { bubbles: true }))

    const confirmInput = wrapper.find('input[name="confirmPassword"]').element as HTMLInputElement
    confirmInput.value = 'different123'
    confirmInput.dispatchEvent(new Event('input', { bubbles: true }))

    await flushPromises()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(authStore.register).not.toHaveBeenCalled()
  })

  it('shows error snackbar on registration failure', async () => {
    // Override the registration endpoint to return 409 conflict
    server.use(
      http.post('/api/v1/users', () => {
        return HttpResponse.json({ detail: 'Username already taken' }, { status: 409 })
      })
    )

    const { wrapper } = mountRegister()

    const usernameInput = wrapper.find('input[name="username"]').element as HTMLInputElement
    usernameInput.value = 'existinguser'
    usernameInput.dispatchEvent(new Event('input', { bubbles: true }))

    const passwordInput = wrapper.find('input[name="password"]').element as HTMLInputElement
    passwordInput.value = 'password123'
    passwordInput.dispatchEvent(new Event('input', { bubbles: true }))

    const confirmInput = wrapper.find('input[name="confirmPassword"]').element as HTMLInputElement
    confirmInput.value = 'password123'
    confirmInput.dispatchEvent(new Event('input', { bubbles: true }))

    await flushPromises()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()
    await flushPromises()
    await flushPromises()

    expect(snackbar.show).toBe(true)
    expect(snackbar.color).toBe('error')
  })

  it('calls authStore.register on valid form submit', async () => {
    const { wrapper, authStore } = mountRegister({ stubActions: true })

    const usernameInput = wrapper.find('input[name="username"]').element as HTMLInputElement
    usernameInput.value = 'newuser'
    usernameInput.dispatchEvent(new Event('input', { bubbles: true }))

    const passwordInput = wrapper.find('input[name="password"]').element as HTMLInputElement
    passwordInput.value = 'password123'
    passwordInput.dispatchEvent(new Event('input', { bubbles: true }))

    const confirmInput = wrapper.find('input[name="confirmPassword"]').element as HTMLInputElement
    confirmInput.value = 'password123'
    confirmInput.dispatchEvent(new Event('input', { bubbles: true }))

    await flushPromises()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(authStore.register).toHaveBeenCalledWith('newuser', 'password123')
  })
})
