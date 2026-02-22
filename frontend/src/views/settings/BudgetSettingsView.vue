<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import {
  getBudgetMembers,
  addBudgetMember,
  removeBudgetMember,
  updateMemberRole,
  updateBudget,
  deleteBudget,
  exportBudgetData,
  importBudgetData,
  type BudgetMember,
  type ExportData,
  type ImportResult,
} from '@/api/budgets'
import { recalculateBalances, type BalanceCorrection } from '@/api/accounts'
import { recalculateEnvelopeBalances, type EnvelopeBalanceCorrection } from '@/api/envelopes'
import type { BudgetRole } from '@/types'
import { toLocaleDateString } from '@/utils/date'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const members = ref<BudgetMember[]>([])

// Budget name editing
const editingName = ref(false)
const newBudgetName = ref('')
const savingName = ref(false)

// Invite dialog
const showInviteDialog = ref(false)
const inviteUsername = ref('')
const inviteRole = ref<BudgetRole>('member')
const inviting = ref(false)

// Role change dialog
const showRoleDialog = ref(false)
const selectedMember = ref<BudgetMember | null>(null)
const newRole = ref<BudgetRole>('member')
const changingRole = ref(false)

// Remove member dialog
const showRemoveDialog = ref(false)
const memberToRemove = ref<BudgetMember | null>(null)
const removing = ref(false)

// Delete budget dialog
const showDeleteDialog = ref(false)
const deletePassword = ref('')
const deletePasswordError = ref('')
const deleting = ref(false)

// Data Management state
const exporting = ref(false)
const showImportDialog = ref(false)
const importMode = ref<'merge' | 'replace'>('merge')
const importFile = ref<File | null>(null)
const importData = ref<ExportData | null>(null)
const importFileError = ref('')
const importPassword = ref('')
const importPasswordError = ref('')
const importing = ref(false)
const importResult = ref<ImportResult | null>(null)
const showImportResultDialog = ref(false)

// Data repair state
const repairing = ref(false)
const repairResult = ref<BalanceCorrection[]>([])
const envelopeRepairResult = ref<EnvelopeBalanceCorrection[]>([])
const showRepairResultDialog = ref(false)

const roleOptions: { value: BudgetRole; title: string; description: string }[] = [
  { value: 'owner', title: 'Owner', description: 'Full access, can delete budget' },
  { value: 'admin', title: 'Admin', description: 'Can manage budget settings and members' },
  { value: 'member', title: 'Member', description: 'Can view and edit budgets' },
  { value: 'viewer', title: 'Viewer', description: 'Read-only access' },
]

const currentUserMember = computed(() =>
  members.value.find((m) => m.id === authStore.user?.id)
)

const canManageMembers = computed(() => {
  const role = currentUserMember.value?.role
  return role === 'owner' || role === 'admin'
})

const canManageRoles = computed(() => {
  return currentUserMember.value?.role === 'owner'
})

const canRename = computed(() => {
  const role = currentUserMember.value?.role
  return role === 'owner' || role === 'admin'
})

const canDelete = computed(() => {
  return currentUserMember.value?.role === 'owner'
})

const canExportImport = computed(() => {
  return currentUserMember.value?.role === 'owner'
})

const isLastBudget = computed(() => {
  return authStore.budgets.length === 1
})

onMounted(async () => {
  await loadMembers()
})

watch(
  () => authStore.currentBudgetId,
  () => {
    loadMembers()
    editingName.value = false
  }
)

async function loadMembers() {
  if (!authStore.currentBudgetId) return

  try {
    loading.value = true
    members.value = await getBudgetMembers(authStore.currentBudgetId)
  } catch {
    showSnackbar('Failed to load budget members', 'error')
  } finally {
    loading.value = false
  }
}

// Budget name functions
function startEditingName() {
  newBudgetName.value = authStore.currentBudget?.name || ''
  editingName.value = true
}

function cancelEditingName() {
  editingName.value = false
  newBudgetName.value = ''
}

async function saveBudgetName() {
  if (!authStore.currentBudgetId || !newBudgetName.value.trim()) return

  try {
    savingName.value = true
    const updatedBudget = await updateBudget(authStore.currentBudgetId, { name: newBudgetName.value.trim() })
    // Update the budget in the auth store
    const budgetIndex = authStore.budgets.findIndex((t) => t.id === updatedBudget.id)
    if (budgetIndex !== -1) {
      authStore.budgets[budgetIndex] = updatedBudget
    }
    editingName.value = false
  } catch {
    showSnackbar('Failed to update budget name', 'error')
  } finally {
    savingName.value = false
  }
}

// Member functions
async function inviteMember() {
  if (!authStore.currentBudgetId) return

  try {
    inviting.value = true
    await addBudgetMember(authStore.currentBudgetId, {
      username: inviteUsername.value,
      role: inviteRole.value,
    })
    showInviteDialog.value = false
    inviteUsername.value = ''
    inviteRole.value = 'member'
    await loadMembers()
  } catch {
    showSnackbar('Failed to add member', 'error')
  } finally {
    inviting.value = false
  }
}

function openRoleDialog(member: BudgetMember) {
  selectedMember.value = member
  newRole.value = member.role
  showRoleDialog.value = true
}

async function changeRole() {
  if (!authStore.currentBudgetId || !selectedMember.value) return

  try {
    changingRole.value = true
    await updateMemberRole(authStore.currentBudgetId, selectedMember.value.id, newRole.value)
    showRoleDialog.value = false
    await loadMembers()
  } catch {
    showSnackbar('Failed to update role', 'error')
  } finally {
    changingRole.value = false
  }
}

function confirmRemove(member: BudgetMember) {
  memberToRemove.value = member
  showRemoveDialog.value = true
}

async function removeMember() {
  if (!authStore.currentBudgetId || !memberToRemove.value) return

  try {
    removing.value = true
    await removeBudgetMember(authStore.currentBudgetId, { username: memberToRemove.value.username })
    showRemoveDialog.value = false
    memberToRemove.value = null
    await loadMembers()
  } catch {
    showSnackbar('Failed to remove member', 'error')
  } finally {
    removing.value = false
  }
}

// Delete budget functions
function openDeleteDialog() {
  deletePassword.value = ''
  deletePasswordError.value = ''
  showDeleteDialog.value = true
}

async function confirmDeleteBudget() {
  if (!authStore.currentBudgetId || !deletePassword.value) return

  try {
    deleting.value = true
    deletePasswordError.value = ''

    await deleteBudget(authStore.currentBudgetId, deletePassword.value)

    // Remove the budget from the store
    const deletedBudgetId = authStore.currentBudgetId
    authStore.budgets = authStore.budgets.filter((t) => t.id !== deletedBudgetId)

    // Switch to another budget or clear current budget
    const firstBudget = authStore.budgets[0]
    if (firstBudget) {
      authStore.currentBudgetId = firstBudget.id
      localStorage.setItem('budge_current_budget', firstBudget.id)
    } else {
      authStore.currentBudgetId = null
      localStorage.removeItem('budge_current_budget')
    }

    showDeleteDialog.value = false

    // Navigate to dashboard or settings
    if (authStore.budgets.length === 0) {
      router.push('/settings')
    } else {
      router.push('/')
    }
  } catch (error: unknown) {
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { status?: number } }
      if (axiosError.response?.status === 401) {
        deletePasswordError.value = 'Invalid password'
      } else {
        showSnackbar('Failed to delete budget', 'error')
      }
    } else {
      showSnackbar('Failed to delete budget', 'error')
    }
  } finally {
    deleting.value = false
  }
}

function getRoleColor(role: BudgetRole): string {
  switch (role) {
    case 'owner':
      return 'primary'
    case 'admin':
      return 'info'
    case 'member':
      return 'success'
    case 'viewer':
      return 'grey'
    default:
      return 'grey'
  }
}

function getMemberName(member: BudgetMember): string {
  if (member.first_name || member.last_name) {
    return [member.first_name, member.last_name].filter(Boolean).join(' ')
  }
  return member.username
}

function getMemberInitials(member: BudgetMember): string {
  if (member.first_name) {
    const first = member.first_name.charAt(0).toUpperCase()
    const last = member.last_name?.charAt(0).toUpperCase() || ''
    return first + last
  }
  return member.username.charAt(0).toUpperCase()
}

// Data Management functions
async function handleExport() {
  if (!authStore.currentBudgetId || !authStore.currentBudget) return

  try {
    exporting.value = true
    const response = await exportBudgetData(authStore.currentBudgetId)

    // Generate filename: budget-name-export-YYYY-MM-DD.json
    const budgetName = authStore.currentBudget.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
    const date = toLocaleDateString()
    const filename = `${budgetName}-export-${date}.json`

    // Create and download file
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    showSnackbar('Budget data exported successfully', 'success')
  } catch {
    showSnackbar('Failed to export budget data', 'error')
  } finally {
    exporting.value = false
  }
}

function openImportDialog() {
  importMode.value = 'merge'
  importFile.value = null
  importData.value = null
  importFileError.value = ''
  importPassword.value = ''
  importPasswordError.value = ''
  showImportDialog.value = true
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  if (!file) {
    importFile.value = null
    importData.value = null
    return
  }

  importFile.value = file
  importFileError.value = ''

  // Read and validate JSON
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target?.result as string
      const data = JSON.parse(content) as ExportData

      // Basic validation
      if (!data.version || !data.budget || !Array.isArray(data.accounts)) {
        throw new Error('Invalid export file format')
      }

      importData.value = data
    } catch (error) {
      importFileError.value = error instanceof Error ? error.message : 'Invalid JSON file'
      importData.value = null
    }
  }
  reader.onerror = () => {
    importFileError.value = 'Failed to read file'
    importData.value = null
  }
  reader.readAsText(file)
}

async function confirmImport() {
  if (!authStore.currentBudgetId || !importData.value || !importPassword.value) return

  try {
    importing.value = true
    importPasswordError.value = ''

    const result = await importBudgetData(
      authStore.currentBudgetId,
      importData.value,
      importMode.value === 'replace',
      importPassword.value
    )

    importResult.value = result
    showImportDialog.value = false
    showImportResultDialog.value = true

    if (result.success && result.errors.length === 0) {
      showSnackbar('Budget data imported successfully', 'success')
    } else if (result.errors.length > 0) {
      showSnackbar('Import completed with some errors', 'warning')
    }
  } catch (error: unknown) {
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { status?: number; data?: { detail?: string } } }
      if (axiosError.response?.status === 401) {
        importPasswordError.value = 'Invalid password'
      } else if (axiosError.response?.data?.detail) {
        showSnackbar(axiosError.response.data.detail, 'error')
      } else {
        showSnackbar('Failed to import budget data', 'error')
      }
    } else {
      showSnackbar('Failed to import budget data', 'error')
    }
  } finally {
    importing.value = false
  }
}

function closeImportResultDialog() {
  showImportResultDialog.value = false
  importResult.value = null
}

// Data repair functions
async function handleRepairData() {
  if (!authStore.currentBudgetId) return

  try {
    repairing.value = true
    const [accountCorrections, envelopeCorrections] = await Promise.all([
      recalculateBalances(authStore.currentBudgetId),
      recalculateEnvelopeBalances(authStore.currentBudgetId),
    ])
    repairResult.value = accountCorrections
    envelopeRepairResult.value = envelopeCorrections

    const totalCorrections = accountCorrections.length + envelopeCorrections.length
    if (totalCorrections === 0) {
      showSnackbar('All balances are correct', 'success')
    } else {
      showRepairResultDialog.value = true
      showSnackbar(`${totalCorrections} balance(s) corrected`, 'success')
    }
  } catch {
    showSnackbar('Failed to repair balances', 'error')
  } finally {
    repairing.value = false
  }
}

function closeRepairResultDialog() {
  showRepairResultDialog.value = false
  repairResult.value = []
  envelopeRepairResult.value = []
}

function formatCurrency(cents: number): string {
  return (cents / 100).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
  })
}
</script>

<template>
  <div>
    <v-btn
      variant="text"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
      @click="router.back()"
    >
      Back
    </v-btn>

    <h1 class="text-h4 mb-6">
      Budget Settings
    </h1>

    <!-- Loading -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <template v-else>
      <!-- Budget Name Section -->
      <v-card class="mb-6">
        <v-card-title>Budget Name</v-card-title>
        <v-card-text>
          <div
            v-if="!editingName"
            class="d-flex align-center"
          >
            <span class="text-h6">{{ authStore.currentBudget?.name }}</span>
            <v-btn
              v-if="canRename"
              icon="mdi-pencil"
              variant="text"
              size="small"
              class="ml-2"
              @click="startEditingName"
            />
          </div>
          <div
            v-else
            class="d-flex align-center gap-2"
          >
            <v-text-field
              v-model="newBudgetName"
              label="Budget Name"
              density="compact"
              hide-details
              autofocus
              @keyup.enter="saveBudgetName"
              @keyup.escape="cancelEditingName"
            />
            <v-btn
              color="primary"
              :loading="savingName"
              :disabled="!newBudgetName.trim()"
              @click="saveBudgetName"
            >
              Save
            </v-btn>
            <v-btn
              variant="text"
              @click="cancelEditingName"
            >
              Cancel
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Budget Members Section -->
      <v-card class="mb-6">
        <v-card-title class="d-flex align-center">
          <span>Budget Members</span>
          <v-spacer />
          <v-btn
            v-if="canManageMembers"
            color="primary"
            size="small"
            prepend-icon="mdi-account-plus"
            @click="showInviteDialog = true"
          >
            Add Member
          </v-btn>
        </v-card-title>
        <v-list>
          <v-list-item
            v-for="member in members"
            :key="member.id"
          >
            <template #prepend>
              <v-avatar
                color="primary"
                variant="tonal"
              >
                {{ getMemberInitials(member) }}
              </v-avatar>
            </template>

            <v-list-item-title>
              {{ getMemberName(member) }}
              <v-chip
                v-if="member.id === authStore.user?.id"
                size="x-small"
                class="ml-2"
              >
                You
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              @{{ member.username }}<template v-if="member.email">
                · {{ member.email }}
              </template>
            </v-list-item-subtitle>

            <template #append>
              <v-chip
                :color="getRoleColor(member.role)"
                size="small"
                class="mr-2"
              >
                {{ member.role }}
              </v-chip>

              <v-menu
                v-if="canManageMembers && member.id !== authStore.user?.id"
                location="bottom end"
              >
                <template #activator="{ props }">
                  <v-btn
                    icon="mdi-dots-vertical"
                    variant="text"
                    size="small"
                    v-bind="props"
                  />
                </template>
                <v-list density="compact">
                  <v-list-item
                    v-if="canManageRoles"
                    prepend-icon="mdi-account-cog"
                    @click="openRoleDialog(member)"
                  >
                    <v-list-item-title>Change Role</v-list-item-title>
                  </v-list-item>
                  <v-list-item
                    prepend-icon="mdi-account-remove"
                    class="text-error"
                    @click="confirmRemove(member)"
                  >
                    <v-list-item-title>Remove</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </template>
          </v-list-item>

          <v-list-item v-if="members.length === 0">
            <v-list-item-title class="text-center text-grey py-4">
              No budget members found.
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Data Management Section (Owner Only) -->
      <v-card
        v-if="canExportImport"
        class="mb-6"
      >
        <v-card-title>Data Management</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <!-- Export Section -->
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="font-weight-medium">
                  Export Budget Data
                </div>
                <div class="text-medium-emphasis text-body-2">
                  Download all budget data as a JSON file for backup.
                </div>
              </div>
              <v-btn
                color="primary"
                variant="outlined"
                :loading="exporting"
                prepend-icon="mdi-download"
                data-testid="export-button"
                @click="handleExport"
              >
                Export
              </v-btn>
            </div>

            <v-divider />

            <!-- Import Section -->
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="font-weight-medium">
                  Import Budget Data
                </div>
                <div class="text-medium-emphasis text-body-2">
                  Restore data from a previously exported JSON file.
                </div>
              </div>
              <v-btn
                color="primary"
                variant="outlined"
                prepend-icon="mdi-upload"
                data-testid="import-button"
                @click="openImportDialog"
              >
                Import
              </v-btn>
            </div>

            <v-divider />

            <!-- Repair Section -->
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="font-weight-medium">
                  Repair Balances
                </div>
                <div class="text-medium-emphasis text-body-2">
                  Recalculate account and envelope balances from transaction history.
                </div>
              </div>
              <v-btn
                color="primary"
                variant="outlined"
                :loading="repairing"
                prepend-icon="mdi-wrench"
                data-testid="repair-button"
                @click="handleRepairData"
              >
                Repair
              </v-btn>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- Danger Zone Section -->
      <v-card
        v-if="canDelete"
        class="border-error"
        variant="outlined"
      >
        <v-card-title class="text-error">
          Danger Zone
        </v-card-title>
        <v-card-text>
          <div class="d-flex align-center justify-space-between">
            <div>
              <div class="font-weight-medium">
                Delete this budget
              </div>
              <div class="text-medium-emphasis text-body-2">
                Permanently delete this budget and all of its data.
                <span
                  v-if="isLastBudget"
                  class="text-warning"
                >
                  This is your only budget.
                </span>
              </div>
            </div>
            <v-btn
              color="error"
              variant="outlined"
              @click="openDeleteDialog"
            >
              Delete Budget
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </template>

    <!-- Add Member Dialog -->
    <v-dialog
      v-model="showInviteDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>Add Budget Member</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="inviteMember">
            <div class="form-fields">
              <v-text-field
                v-model="inviteUsername"
                label="Username"
                required
                hint="Enter the username of an existing user"
                persistent-hint
              />

              <v-select
                v-model="inviteRole"
                label="Role"
                :items="roleOptions"
                item-title="title"
                item-value="value"
              >
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-select>
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showInviteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="inviting"
            :disabled="!inviteUsername"
            @click="inviteMember"
          >
            Add Member
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Change Role Dialog -->
    <v-dialog
      v-model="showRoleDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Change Role</v-card-title>
        <v-card-text>
          <p class="mb-4">
            Change role for <strong>{{ selectedMember?.username }}</strong>
          </p>
          <v-select
            v-model="newRole"
            label="Role"
            :items="roleOptions"
            item-title="title"
            item-value="value"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props">
                <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showRoleDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="changingRole"
            @click="changeRole"
          >
            Update Role
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Remove Member Dialog -->
    <v-dialog
      v-model="showRemoveDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Remove Member</v-card-title>
        <v-card-text>
          Are you sure you want to remove <strong>{{ memberToRemove?.username }}</strong> from the
          budget? They will lose access to all budget data.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showRemoveDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="removing"
            @click="removeMember"
          >
            Remove
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Budget Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title class="text-error">
          Delete Budget
        </v-card-title>
        <v-card-text>
          <v-alert
            type="error"
            variant="tonal"
            class="mb-4"
          >
            <div class="font-weight-bold">
              This action cannot be undone
            </div>
            <div>
              This will permanently delete the budget "{{ authStore.currentBudget?.name }}" and all of
              its data including accounts, transactions, envelopes, and all other budget data.
            </div>
            <div
              v-if="isLastBudget"
              class="mt-2"
            >
              <strong>Warning:</strong> This is your only budget. You will need to create a new budget
              to continue using the app.
            </div>
          </v-alert>

          <v-text-field
            v-model="deletePassword"
            label="Enter your password to confirm"
            type="password"
            :error-messages="deletePasswordError"
            @keyup.enter="confirmDeleteBudget"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showDeleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deleting"
            :disabled="!deletePassword"
            @click="confirmDeleteBudget"
          >
            Delete Budget
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Import Budget Data Dialog -->
    <v-dialog
      v-model="showImportDialog"
      max-width="600"
    >
      <v-card rounded="xl">
        <v-card-title>Import Budget Data</v-card-title>
        <v-card-text>
          <!-- File Selection -->
          <v-file-input
            label="Select export file"
            accept=".json"
            prepend-icon="mdi-file-document"
            :error-messages="importFileError"
            data-testid="import-file-input"
            @change="handleFileSelect"
          />

          <!-- File Preview (when file is loaded) -->
          <v-alert
            v-if="importData"
            type="info"
            variant="tonal"
            class="mt-4"
            data-testid="import-preview"
          >
            <div class="font-weight-bold">
              {{ importData.budget.name }}
            </div>
            <div class="text-body-2">
              Exported on {{ new Date(importData.exported_at).toLocaleDateString() }}
            </div>
            <div class="text-body-2 mt-2">
              Contains: {{ importData.accounts.length }} accounts,
              {{ importData.envelopes.length }} envelopes,
              {{ importData.transactions.length }} transactions
            </div>
          </v-alert>

          <!-- Import Mode Selection -->
          <div
            v-if="importData"
            class="mt-4"
          >
            <div class="font-weight-medium mb-2">
              Import Mode
            </div>
            <v-radio-group v-model="importMode">
              <v-radio
                value="merge"
                data-testid="import-merge-radio"
              >
                <template #label>
                  <div>
                    <div>Merge with existing data</div>
                    <div class="text-body-2 text-medium-emphasis">
                      Imported data will be added alongside existing data.
                    </div>
                  </div>
                </template>
              </v-radio>
              <v-radio
                value="replace"
                color="error"
                data-testid="import-replace-radio"
              >
                <template #label>
                  <div>
                    <div class="text-error">
                      Replace all existing data
                    </div>
                    <div class="text-body-2 text-medium-emphasis">
                      All existing budget data will be deleted before import.
                    </div>
                  </div>
                </template>
              </v-radio>
            </v-radio-group>

            <v-alert
              v-if="importMode === 'replace'"
              type="warning"
              variant="tonal"
              class="mt-2"
            >
              Warning: This will permanently delete all existing data before importing.
            </v-alert>
          </div>

          <!-- Password Confirmation -->
          <v-text-field
            v-if="importData"
            v-model="importPassword"
            label="Enter your password to confirm"
            type="password"
            :error-messages="importPasswordError"
            class="mt-4"
            data-testid="import-password-input"
            @keyup.enter="confirmImport"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            data-testid="import-cancel-button"
            @click="showImportDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="importing"
            :disabled="!importData || !importPassword"
            data-testid="import-confirm-button"
            @click="confirmImport"
          >
            Import Data
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Import Result Dialog -->
    <v-dialog
      v-model="showImportResultDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>Import Complete</v-card-title>
        <v-card-text v-if="importResult">
          <v-list density="compact">
            <v-list-item v-if="importResult.accounts_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.accounts_imported }} account(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.envelope_groups_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.envelope_groups_imported }} envelope group(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.envelopes_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.envelopes_imported }} envelope(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.payees_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.payees_imported }} payee(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.locations_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.locations_imported }} location(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.allocation_rules_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.allocation_rules_imported }} allocation rule(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.recurring_transactions_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.recurring_transactions_imported }} recurring transaction(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.transactions_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.transactions_imported }} transaction(s) imported</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="importResult.allocations_imported > 0">
              <template #prepend>
                <v-icon
                  icon="mdi-check"
                  color="success"
                />
              </template>
              <v-list-item-title>{{ importResult.allocations_imported }} allocation(s) imported</v-list-item-title>
            </v-list-item>
          </v-list>

          <!-- Errors if any -->
          <v-alert
            v-if="importResult.errors.length > 0"
            type="warning"
            variant="tonal"
            class="mt-4"
          >
            <div class="font-weight-bold">
              Some items could not be imported:
            </div>
            <ul class="mt-2">
              <li
                v-for="error in importResult.errors"
                :key="error"
              >
                {{ error }}
              </li>
            </ul>
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            class="create-btn"
            data-testid="import-result-close-button"
            @click="closeImportResultDialog"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Repair Result Dialog -->
    <v-dialog
      v-model="showRepairResultDialog"
      max-width="600"
    >
      <v-card rounded="xl">
        <v-card-title>Balance Corrections Applied</v-card-title>
        <v-card-text>
          <div
            v-if="repairResult.length > 0"
            class="mb-4"
          >
            <p class="mb-2 font-weight-medium">
              Account Balances
            </p>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Account</th>
                  <th class="text-right">
                    Old Balance
                  </th>
                  <th class="text-right">
                    New Balance
                  </th>
                  <th class="text-right">
                    Difference
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="correction in repairResult"
                  :key="correction.account_id"
                >
                  <td>{{ correction.account_name }}</td>
                  <td class="text-right">
                    {{ formatCurrency(correction.old_cleared + correction.old_uncleared) }}
                  </td>
                  <td class="text-right">
                    {{ formatCurrency(correction.new_cleared + correction.new_uncleared) }}
                  </td>
                  <td class="text-right">
                    {{
                      formatCurrency(
                        (correction.new_cleared + correction.new_uncleared) -
                          (correction.old_cleared + correction.old_uncleared)
                      )
                    }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </div>
          <div v-if="envelopeRepairResult.length > 0">
            <p class="mb-2 font-weight-medium">
              Envelope Balances
            </p>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Envelope</th>
                  <th class="text-right">
                    Old Balance
                  </th>
                  <th class="text-right">
                    New Balance
                  </th>
                  <th class="text-right">
                    Difference
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="correction in envelopeRepairResult"
                  :key="correction.envelope_id"
                >
                  <td>{{ correction.envelope_name }}</td>
                  <td class="text-right">
                    {{ formatCurrency(correction.old_balance) }}
                  </td>
                  <td class="text-right">
                    {{ formatCurrency(correction.new_balance) }}
                  </td>
                  <td class="text-right">
                    {{ formatCurrency(correction.new_balance - correction.old_balance) }}
                  </td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            class="create-btn"
            data-testid="repair-result-close-button"
            @click="closeRepairResultDialog"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
