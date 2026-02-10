<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'
import { openNewTransaction } from '@/composables/useGlobalTransactionDialog'
import BudgetMenu from '@/components/layout/BudgetMenu.vue'

const route = useRoute()
const { mobile } = useDisplay()

const showMoreMenu = ref(false)

const moreMenuItems = [
  { title: 'Transactions', icon: 'mdi-swap-horizontal', to: '/transactions' },
  { title: 'Recurring', icon: 'mdi-repeat', to: '/recurring' },
  { title: 'Allocation Rules', icon: 'mdi-tune-vertical', to: '/allocation-rules' },
  { title: 'Notifications', icon: 'mdi-bell-cog', to: '/settings/notifications' },
]

function closeMoreMenu() {
  showMoreMenu.value = false
}

const activeTab = computed(() => {
  const path = route.path
  if (path === '/') return 0
  if (path.startsWith('/accounts')) return 1
  // Index 2 is the "Add" button (not a navigation item)
  if (path.startsWith('/reports')) return 3
  return 4
})
</script>

<template>
  <v-bottom-navigation
    v-if="mobile"
    :model-value="activeTab"
    grow
    color="primary"
  >
    <!-- Envelopes -->
    <v-btn
      to="/"
      :value="0"
    >
      <v-icon>mdi-email-outline</v-icon>
      <span>Envelopes</span>
    </v-btn>

    <!-- Accounts -->
    <v-btn
      to="/accounts"
      :value="1"
    >
      <v-icon>mdi-bank</v-icon>
      <span>Accounts</span>
    </v-btn>

    <!-- Add Transaction (opens modal, not a navigation) -->
    <v-btn
      :value="2"
      @click="openNewTransaction()"
    >
      <v-icon>mdi-plus-circle</v-icon>
      <span>Add</span>
    </v-btn>

    <!-- Reports -->
    <v-btn
      to="/reports"
      :value="3"
    >
      <v-icon>mdi-chart-bar</v-icon>
      <span>Reports</span>
    </v-btn>

    <!-- More menu -->
    <v-btn
      :value="4"
      @click="showMoreMenu = true"
    >
      <v-icon>mdi-dots-horizontal</v-icon>
      <span>More</span>
    </v-btn>
  </v-bottom-navigation>

  <v-bottom-sheet v-model="showMoreMenu">
    <v-list nav>
      <BudgetMenu
        variant="bottomsheet"
        @close="closeMoreMenu"
      />

      <v-divider class="my-2" />

      <v-list-item
        v-for="item in moreMenuItems"
        :key="item.to"
        :to="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        @click="closeMoreMenu"
      />
    </v-list>
  </v-bottom-sheet>
</template>

<style scoped>
.v-bottom-navigation {
  left: 12px;
  right: 12px;
  bottom: calc(12px + env(safe-area-inset-bottom));
  width: auto;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}
</style>
