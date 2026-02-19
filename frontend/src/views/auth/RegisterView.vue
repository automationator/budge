<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'

const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const loading = ref(false)

const rules = {
  required: (v: string) => !!v || 'Required',
  username: (v: string) => (v.length >= 3 && v.length <= 50) || 'Username must be 3-50 characters',
  minLength: (v: string) => v.length >= 8 || 'Minimum 8 characters',
  hasUppercase: (v: string) => /[A-Z]/.test(v) || 'Must contain an uppercase letter',
  hasLowercase: (v: string) => /[a-z]/.test(v) || 'Must contain a lowercase letter',
  hasDigit: (v: string) => /\d/.test(v) || 'Must contain a digit',
  hasSpecial: (v: string) => /[^A-Za-z0-9]/.test(v) || 'Must contain a special character',
  passwordMatch: () => password.value === confirmPassword.value || 'Passwords must match',
}

async function handleRegister() {
  if (!username.value || !password.value || password.value !== confirmPassword.value) {
    return
  }

  loading.value = true
  try {
    await authStore.register(username.value, password.value)
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Registration failed'
    showSnackbar(message, 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-container
    class="fill-height"
    fluid
  >
    <v-row
      align="center"
      justify="center"
    >
      <v-col
        cols="12"
        sm="8"
        md="4"
      >
        <v-card class="elevation-12">
          <v-toolbar
            color="primary"
            dark
            flat
          >
            <v-toolbar-title>Create Account</v-toolbar-title>
          </v-toolbar>

          <v-card-text>
            <v-form @submit.prevent="handleRegister">
              <v-text-field
                v-model="username"
                label="Username"
                name="username"
                prepend-icon="mdi-account"
                :rules="[rules.required, rules.username]"
                autocomplete="username"
                hint="3-50 characters"
              />

              <v-text-field
                v-model="password"
                label="Password"
                name="password"
                prepend-icon="mdi-lock"
                :type="showPassword ? 'text' : 'password'"
                :append-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :rules="[rules.required, rules.minLength, rules.hasUppercase, rules.hasLowercase, rules.hasDigit, rules.hasSpecial]"
                autocomplete="new-password"
                @click:append="showPassword = !showPassword"
              />

              <v-text-field
                v-model="confirmPassword"
                label="Confirm Password"
                name="confirmPassword"
                prepend-icon="mdi-lock-check"
                :type="showPassword ? 'text' : 'password'"
                :rules="[rules.required, rules.passwordMatch]"
                autocomplete="new-password"
              />

              <v-btn
                type="submit"
                color="primary"
                block
                size="large"
                :loading="loading"
                class="mt-4"
              >
                Register
              </v-btn>
            </v-form>
          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <span class="text-body-2">Already have an account?</span>
            <v-btn
              variant="text"
              color="primary"
              to="/login"
            >
              Login
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
