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
import TasksView from '@/views/TasksView.vue'
import RiskView from '@/views/RiskView.vue'
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
          component: RiskView,
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
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return '/app'
  }
  return true
})

export default router
