<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { showSnackbar } from '@/App.vue'

const authStore = useAuthStore()
const appStore = useAppStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)

const rules = {
  required: (v: string) => !!v || 'Required',
}

async function handleLogin() {
  if (!username.value || !password.value) return

  loading.value = true
  try {
    await authStore.login(username.value, password.value)
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Login failed'
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
            <v-toolbar-title>Budge</v-toolbar-title>
          </v-toolbar>

          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Username"
                name="username"
                prepend-icon="mdi-account"
                :rules="[rules.required]"
                autocomplete="username"
              />

              <v-text-field
                v-model="password"
                label="Password"
                name="password"
                prepend-icon="mdi-lock"
                :type="showPassword ? 'text' : 'password'"
                :append-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                :rules="[rules.required]"
                autocomplete="current-password"
                @click:append="showPassword = !showPassword"
              />

              <v-btn
                type="submit"
                color="primary"
                block
                size="large"
                :loading="loading"
                class="mt-4"
              >
                Login
              </v-btn>
            </v-form>
          </v-card-text>

          <v-card-actions v-if="appStore.registrationEnabled">
            <v-spacer />
            <span class="text-body-2">Don't have an account?</span>
            <v-btn
              variant="text"
              color="primary"
              to="/register"
            >
              Register
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
