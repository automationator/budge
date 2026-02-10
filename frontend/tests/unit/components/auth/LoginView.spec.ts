import { describe, it, expect, beforeEach } from 'vitest'
import LoginView from '@/views/auth/LoginView.vue'
import { mountAuthView, flushPromises } from '@test/helpers/component-test-utils'
import { snackbar } from '@/composables/useSnackbar'

function mountLogin(options?: Parameters<typeof mountAuthView>[1]) {
  return mountAuthView(LoginView, options)
}

describe('LoginView', () => {
  beforeEach(() => {
    snackbar.show = false
    snackbar.message = ''
    snackbar.color = 'info'
  })

  it('displays login form with username and password fields', () => {
    const { wrapper } = mountLogin()

    expect(wrapper.find('input[name="username"]').exists()).toBe(true)
    expect(wrapper.find('input[name="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Login')
    expect(wrapper.text()).toContain('Budge')
  })

  it('password field toggles visibility', async () => {
    const { wrapper } = mountLogin()

    const passwordInput = wrapper.find('input[name="password"]')
    expect(passwordInput.attributes('type')).toBe('password')

    // Vuetify renders append-icon in .v-input__append
    const passwordField = wrapper.findAll('.v-text-field').find((f) => f.find('input[name="password"]').exists())!
    const appendIcon = passwordField.find('.v-input__append .v-icon')
    await appendIcon.trigger('click')

    expect(passwordInput.attributes('type')).toBe('text')

    // Toggle back
    await appendIcon.trigger('click')
    expect(passwordInput.attributes('type')).toBe('password')
  })

  it('shows register link when registration is enabled', () => {
    const { wrapper } = mountLogin({ registrationEnabled: true })

    const cardActions = wrapper.find('.v-card-actions')
    expect(cardActions.exists()).toBe(true)
    expect(cardActions.text()).toContain("Don't have an account?")
    expect(cardActions.text()).toContain('Register')
  })

  it('hides register link when registration is disabled', () => {
    const { wrapper } = mountLogin({ registrationEnabled: false })

    expect(wrapper.find('.v-card-actions').exists()).toBe(false)
  })

  it('empty form does not call login API', async () => {
    const { wrapper, authStore } = mountLogin()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    // handleLogin returns early if fields are empty
    expect(authStore.login).not.toHaveBeenCalled()
  })

  it('shows error snackbar on invalid credentials', async () => {
    const { wrapper } = mountLogin()

    // Fill in credentials that will fail (MSW returns 401 for non-testuser)
    const usernameInput = wrapper.find('input[name="username"]').element as HTMLInputElement
    usernameInput.value = 'wronguser'
    usernameInput.dispatchEvent(new Event('input', { bubbles: true }))

    const passwordInput = wrapper.find('input[name="password"]').element as HTMLInputElement
    passwordInput.value = 'wrongpassword'
    passwordInput.dispatchEvent(new Event('input', { bubbles: true }))

    await flushPromises()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()
    await flushPromises()
    await flushPromises()

    expect(snackbar.show).toBe(true)
    expect(snackbar.color).toBe('error')
  })

  it('calls authStore.login on valid form submit', async () => {
    // Stub actions so login doesn't actually execute
    const { wrapper, authStore } = mountLogin({ stubActions: true })

    const usernameInput = wrapper.find('input[name="username"]').element as HTMLInputElement
    usernameInput.value = 'testuser'
    usernameInput.dispatchEvent(new Event('input', { bubbles: true }))

    const passwordInput = wrapper.find('input[name="password"]').element as HTMLInputElement
    passwordInput.value = 'password'
    passwordInput.dispatchEvent(new Event('input', { bubbles: true }))

    await flushPromises()

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await flushPromises()

    expect(authStore.login).toHaveBeenCalledWith('testuser', 'password')
  })
})
