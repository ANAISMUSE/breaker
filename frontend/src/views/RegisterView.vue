<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const password2 = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  if (password.value !== password2.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const { data } = await http.post<{
      access_token: string
      token_type: string
      username: string
      role: string
    }>('/api/auth/register', {
      username: username.value.trim(),
      password: password.value,
    })
    auth.setSession(data.access_token, data.username, data.role)
    await router.replace('/app')
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } }; message?: string }
    const detail = ax.response?.data?.detail
    if (typeof detail === 'string') {
      errorMsg.value = detail
    } else {
      errorMsg.value = '注册失败，请检查网络或稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">注册</h1>
      <p class="login-hint">新账号默认为 viewer，管理员账号请在服务端配置</p>

      <form class="login-form" @submit.prevent="onSubmit">
        <label class="field">
          <span class="label">用户名</span>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            class="input"
            placeholder="3–32 位字母、数字或下划线"
          />
        </label>
        <label class="field">
          <span class="label">密码</span>
          <input
            v-model="password"
            type="password"
            autocomplete="new-password"
            class="input"
            placeholder="至少 6 位"
          />
        </label>
        <label class="field">
          <span class="label">确认密码</span>
          <input
            v-model="password2"
            type="password"
            autocomplete="new-password"
            class="input"
            placeholder="再次输入密码"
          />
        </label>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <button type="submit" class="submit" :disabled="loading">
          {{ loading ? '提交中…' : '注册并登录' }}
        </button>
      </form>

      <RouterLink class="register-link" to="/login">已有账号？去登录</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(180deg, #f0f7ff 0%, #e3eefc 45%, #d4e5fa 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 32px 28px 28px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
}

.login-title {
  margin: 0 0 8px;
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.login-hint {
  margin: 0 0 24px;
  font-size: 0.8rem;
  color: #94a3b8;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 0.85rem;
  color: #334155;
  font-weight: 500;
}

.input {
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  background: #eef5ff;
  color: #0f172a;
  outline: none;
}

.input:focus {
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.35);
}

.error {
  margin: 0;
  font-size: 0.85rem;
  color: #dc2626;
}

.submit {
  margin-top: 8px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
  transition: opacity 0.15s ease;
}

.submit:hover:not(:disabled) {
  opacity: 0.92;
}

.submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.register-link {
  display: inline-block;
  margin-top: 20px;
  font-size: 0.9rem;
  color: #3b82f6;
  text-decoration: none;
}

.register-link:hover {
  text-decoration: underline;
}
</style>
