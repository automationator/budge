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
  type BudgetMember,
} from '@/api/budgets'
import type { BudgetRole } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const members = ref<BudgetMember[]>([])

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

// Remove dialog
const showRemoveDialog = ref(false)
const memberToRemove = ref<BudgetMember | null>(null)
const removing = ref(false)

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

onMounted(async () => {
  await loadMembers()
})

watch(
  () => authStore.currentBudgetId,
  () => {
    loadMembers()
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
  return member.username
}

function getMemberInitials(member: BudgetMember): string {
  return member.username.charAt(0).toUpperCase()
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
      Back to Settings
    </v-btn>

    <div class="d-flex align-center mb-4">
      <div>
        <h1 class="text-h4">
          Budget Members
        </h1>
        <p class="text-subtitle-1 text-medium-emphasis">
          {{ authStore.currentBudget?.name }}
        </p>
      </div>
      <v-spacer />
      <v-btn
        v-if="canManageMembers"
        color="primary"
        prepend-icon="mdi-account-plus"
        @click="showInviteDialog = true"
      >
        Add Member
      </v-btn>
    </div>

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

    <!-- Members List -->
    <v-card v-else>
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
            @{{ member.username }}
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

    <!-- Add Member Dialog -->
    <v-dialog
      v-model="showInviteDialog"
      max-width="500"
    >
      <v-card>
        <v-card-title>Add Budget Member</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="inviteMember">
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
              class="mt-4"
            >
              <template #item="{ item, props }">
                <v-list-item v-bind="props">
                  <v-list-item-subtitle>{{ item.raw.description }}</v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-select>
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
      <v-card>
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
      <v-card>
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
  </div>
</template>
