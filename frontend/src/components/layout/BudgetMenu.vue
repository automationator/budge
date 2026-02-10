<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'

defineProps<{
  variant?: 'sidebar' | 'bottomsheet'
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const authStore = useAuthStore()

// Menu state
const menuOpen = ref(false)

// Create budget dialog state
const showCreateDialog = ref(false)
const budgetName = ref('')
const creating = ref(false)

// Computed
const currentBudgetName = computed(() => authStore.currentBudget?.name || 'Select Budget')
const username = computed(() => authStore.user?.username || '')
const budgets = computed(() => authStore.budgets)

// Methods
async function switchBudget(budgetId: string) {
  if (budgetId === authStore.currentBudgetId) {
    menuOpen.value = false
    emit('close')
    return
  }

  try {
    await authStore.selectBudget(budgetId)
  } catch {
    showSnackbar('Failed to switch budget', 'error')
  }
  menuOpen.value = false
  emit('close')
}

async function handleCreateBudget() {
  if (!budgetName.value.trim()) return

  try {
    creating.value = true
    await authStore.createBudget(budgetName.value.trim())
    showCreateDialog.value = false
    budgetName.value = ''
    emit('close')
  } catch {
    showSnackbar('Failed to create budget', 'error')
  } finally {
    creating.value = false
  }
}

function openCreateDialog() {
  menuOpen.value = false
  showCreateDialog.value = true
}

function navigateTo(path: string) {
  router.push(path)
  menuOpen.value = false
  emit('close')
}

function handleLogout() {
  authStore.logout()
  menuOpen.value = false
  emit('close')
}
</script>

<template>
  <div>
    <!-- Budget Header with Dropdown -->
    <v-menu
      v-model="menuOpen"
      location="bottom start"
      :close-on-content-click="false"
    >
      <template #activator="{ props }">
        <v-list-item
          v-bind="props"
          class="budget-selector-header"
          :class="{ 'pa-4': variant === 'sidebar', 'pa-3': variant === 'bottomsheet' }"
        >
          <template #prepend>
            <v-icon color="primary">
              mdi-account-group
            </v-icon>
          </template>
          <v-list-item-title class="font-weight-bold">
            {{ currentBudgetName }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-body-2">
            @{{ username }}
          </v-list-item-subtitle>
          <template #append>
            <v-icon>{{ menuOpen ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
          </template>
        </v-list-item>
      </template>

      <!-- Dropdown Menu -->
      <v-list
        density="compact"
        min-width="250"
      >
        <!-- Budget List -->
        <v-list-subheader>Budgets</v-list-subheader>
        <v-list-item
          v-for="budget in budgets"
          :key="budget.id"
          :active="budget.id === authStore.currentBudgetId"
          @click="switchBudget(budget.id)"
        >
          <template #prepend>
            <v-icon size="small">
              mdi-account-group-outline
            </v-icon>
          </template>
          <v-list-item-title>{{ budget.name }}</v-list-item-title>
          <template #append>
            <v-icon
              v-if="budget.id === authStore.currentBudgetId"
              color="primary"
              size="small"
            >
              mdi-check
            </v-icon>
          </template>
        </v-list-item>

        <!-- Create New Budget -->
        <v-list-item @click="openCreateDialog">
          <template #prepend>
            <v-icon
              size="small"
              color="primary"
            >
              mdi-plus
            </v-icon>
          </template>
          <v-list-item-title class="text-primary">
            Create New Budget
          </v-list-item-title>
        </v-list-item>

        <v-divider class="my-2" />

        <!-- Navigation Items -->
        <v-list-item @click="navigateTo('/settings')">
          <template #prepend>
            <v-icon size="small">
              mdi-cog
            </v-icon>
          </template>
          <v-list-item-title>Settings</v-list-item-title>
        </v-list-item>

        <v-list-item @click="navigateTo('/settings/locations')">
          <template #prepend>
            <v-icon size="small">
              mdi-map-marker
            </v-icon>
          </template>
          <v-list-item-title>Manage Locations</v-list-item-title>
        </v-list-item>

        <v-list-item @click="navigateTo('/settings/payees')">
          <template #prepend>
            <v-icon size="small">
              mdi-account-cash
            </v-icon>
          </template>
          <v-list-item-title>Manage Payees</v-list-item-title>
        </v-list-item>

        <v-list-item @click="navigateTo('/settings/budget-settings')">
          <template #prepend>
            <v-icon size="small">
              mdi-cog-outline
            </v-icon>
          </template>
          <v-list-item-title>Budget Settings</v-list-item-title>
        </v-list-item>

        <v-list-item @click="navigateTo('/settings/start-fresh')">
          <template #prepend>
            <v-icon
              size="small"
              color="error"
            >
              mdi-delete-sweep
            </v-icon>
          </template>
          <v-list-item-title class="text-error">
            Start Fresh
          </v-list-item-title>
        </v-list-item>

        <v-divider class="my-2" />

        <v-list-item @click="handleLogout">
          <template #prepend>
            <v-icon size="small">
              mdi-logout
            </v-icon>
          </template>
          <v-list-item-title>Log Out</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- Create Budget Dialog -->
    <v-dialog
      v-model="showCreateDialog"
      max-width="400"
    >
      <v-card>
        <v-card-title>Create New Budget</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="budgetName"
            label="Budget Name"
            placeholder="e.g., Personal, Family, Business"
            :disabled="creating"
            autofocus
            @keyup.enter="handleCreateBudget"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="creating"
            @click="showCreateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="creating"
            :disabled="!budgetName.trim()"
            @click="handleCreateBudget"
          >
            Create
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.budget-selector-header {
  cursor: pointer;
}

.budget-selector-header:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}
</style>
