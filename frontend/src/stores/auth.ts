import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const TOKEN_KEY = 'jianping_token'
const USER_KEY = 'jianping_user'
const ROLE_KEY = 'jianping_role'
const normalizeRole = (role: string | null) => {
  const value = (role || '').toLowerCase()
  if (value === 'admin') return 'admin'
  return 'user'
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const username = ref<string | null>(localStorage.getItem(USER_KEY))
  const role = ref<string | null>(normalizeRole(localStorage.getItem(ROLE_KEY)))

  const isAuthenticated = computed(() => Boolean(token.value))

  function setSession(accessToken: string, user: string, userRole: string) {
    token.value = accessToken
    username.value = user
    role.value = normalizeRole(userRole)
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(USER_KEY, user)
    localStorage.setItem(ROLE_KEY, role.value)
  }

  function logout() {
    token.value = null
    username.value = null
    role.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(ROLE_KEY)
  }

  return { token, username, role, isAuthenticated, setSession, logout }
})
