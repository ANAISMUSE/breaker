import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import AppLayout from '@/layouts/AppLayout.vue'
import CompareView from '@/views/CompareView.vue'
import ComplianceView from '@/views/ComplianceView.vue'
import DevicesView from '@/views/DevicesView.vue'
import LoginView from '@/views/LoginView.vue'
import MonitorView from '@/views/MonitorView.vue'
import PersonaView from '@/views/PersonaView.vue'
import ProfileView from '@/views/ProfileView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ChangePasswordView from '@/views/ChangePasswordView.vue'
import CompareHistoryView from '@/views/CompareHistoryView.vue'
import TasksView from '@/views/TasksView.vue'
import RiskDetailView from '@/views/RiskDetailView.vue'
import SemanticGraphView from '@/views/SemanticGraphView.vue'
import UserAdminView from '@/views/UserAdminView.vue'
import UserProfileView from '@/views/UserProfileView.vue'
import WorkbenchView from '@/views/WorkbenchView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/app' },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { public: true },
    },
    {
      path: '/app',
      component: AppLayout,
      meta: { requiresAuth: true },
      redirect: '/app/dispatch/monitor',
      children: [
        {
          path: 'dispatch/devices',
          component: DevicesView,
        },
        {
          path: 'dispatch/tasks',
          component: TasksView,
        },
        {
          path: 'dispatch/monitor',
          component: MonitorView,
        },
        {
          path: 'analytics/risk',
          redirect: '/app/analytics/risk-detail',
        },
        {
          path: 'analytics/risk-detail',
          component: RiskDetailView,
        },
        {
          path: 'analytics/semantic-graph',
          component: SemanticGraphView,
        },
        {
          path: 'analytics/profile',
          component: ProfileView,
        },
        {
          path: 'analytics/compare',
          component: CompareView,
        },
        {
          path: 'analytics/compare-history',
          component: CompareHistoryView,
        },
        {
          path: 'data/persona',
          component: PersonaView,
        },
        {
          path: 'data/compliance',
          component: ComplianceView,
        },
        {
          path: 'research/workbench',
          component: WorkbenchView,
        },
        {
          path: 'account/change-password',
          component: ChangePasswordView,
        },
        {
          path: 'account/profile',
          component: UserProfileView,
        },
        {
          path: 'account/users',
          component: UserAdminView,
          meta: { roles: ['admin'] },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const currentRole = (auth.role || 'user').toLowerCase()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  const requiredRoles = to.matched.flatMap((record) => {
    const roles = record.meta.roles
    return Array.isArray(roles) ? roles.map((role) => String(role).toLowerCase()) : []
  })
  if (requiredRoles.length > 0 && !requiredRoles.includes(currentRole)) {
    return '/app/account/profile'
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return '/app'
  }
  return true
})

export default router
