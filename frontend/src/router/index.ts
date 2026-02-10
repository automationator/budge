import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const routes: RouteRecordRaw[] = [
  // Auth routes (public)
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },

  // Protected routes
  {
    path: '/',
    name: 'envelopes',
    component: () => import('@/views/envelopes/EnvelopesView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/accounts',
    name: 'accounts',
    component: () => import('@/views/accounts/AccountsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/accounts/:id',
    name: 'account-detail',
    component: () => import('@/views/accounts/AccountDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/transactions',
    name: 'transactions',
    component: () => import('@/views/transactions/TransactionsView.vue'),
    meta: { requiresAuth: true },
  },
  // Legacy routes - redirect to transactions page (transactions are now created/edited via dialog)
  {
    path: '/transactions/new',
    redirect: '/transactions',
  },
  {
    path: '/transactions/:id',
    redirect: '/transactions',
  },
  {
    path: '/transactions/:id/edit',
    redirect: '/transactions',
  },
  {
    path: '/envelopes',
    redirect: '/',
  },
  {
    path: '/envelopes/:id',
    name: 'envelope-detail',
    component: () => import('@/views/envelopes/EnvelopeDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/recurring',
    name: 'recurring',
    component: () => import('@/views/recurring/RecurringView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/allocation-rules',
    name: 'allocation-rules',
    component: () => import('@/views/allocation-rules/AllocationRulesView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/reports/ReportsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/settings/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/budget-settings',
    name: 'budget-settings',
    component: () => import('@/views/settings/BudgetSettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/team-settings',
    redirect: '/settings/budget-settings',
  },
  {
    path: '/settings/team',
    redirect: '/settings/budget-settings',
  },
  {
    path: '/settings/notifications',
    name: 'notification-settings',
    component: () => import('@/views/settings/NotificationSettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/payees',
    name: 'payees-settings',
    component: () => import('@/views/settings/PayeesSettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/locations',
    name: 'locations-settings',
    component: () => import('@/views/settings/LocationsSettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/start-fresh',
    name: 'start-fresh',
    component: () => import('@/views/settings/StartFreshView.vue'),
    meta: { requiresAuth: true },
  },

  // Catch-all redirect
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const appStore = useAppStore()

  // Initialize app store to check registration status
  if (!appStore.initialized) {
    await appStore.initialize()
  }

  // Try to restore session on first load
  if (!authStore.initialized) {
    await authStore.initialize()
  }

  const requiresAuth = to.meta.requiresAuth !== false

  // Block register page if registration is disabled
  if (to.name === 'register' && !appStore.registrationEnabled) {
    next({ name: 'login' })
    return
  }

  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login, save intended destination
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (!requiresAuth && authStore.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
    // Redirect authenticated users away from auth pages
    next({ name: 'envelopes' })
  } else {
    next()
  }
})

export default router
