import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const TOKEN_KEY = 'jianping_token'
const USER_KEY = 'jianping_user'
const ROLE_KEY = 'jianping_role'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const username = ref<string | null>(localStorage.getItem(USER_KEY))
  const role = ref<string | null>(localStorage.getItem(ROLE_KEY))

  const isAuthenticated = computed(() => Boolean(token.value))

  function setSession(accessToken: string, user: string, userRole: string) {
    token.value = accessToken
    username.value = user
    role.value = userRole
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(USER_KEY, user)
    localStorage.setItem(ROLE_KEY, userRole)
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
