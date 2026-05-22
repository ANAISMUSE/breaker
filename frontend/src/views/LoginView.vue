<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    const { data } = await http.post<{
      access_token: string
      token_type: string
      username: string
      role: string
    }>('/api/auth/login', {
      username: username.value.trim(),
      password: password.value,
    })
    auth.setSession(data.access_token, data.username, data.role)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/app'
    await router.replace(redirect)
  } catch {
    errorMsg.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="bg-pattern" />
    <div class="login-card">
      <div class="brand-area">
        <h1 class="login-title">茧评</h1>
        <p class="login-subtitle">信息茧房综合评估系统</p>
        <p class="login-desc">Cocoon Insight — 基于LLM语义嵌入与智能体模拟的茧房评估平台</p>
      </div>

      <form class="login-form" @submit.prevent="onSubmit">
        <label class="field">
          <span class="label">用户名</span>
          <input v-model="username" type="text" autocomplete="username" class="input" placeholder="请输入用户名" />
        </label>
        <label class="field">
          <span class="label">密码</span>
          <input v-model="password" type="password" autocomplete="current-password" class="input" placeholder="请输入密码" />
        </label>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <button type="submit" class="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>

      <RouterLink class="register-link" to="/register">没有账号？去注册</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background-image: url('/login-bg.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.bg-pattern {
  position: absolute;
  inset: 0;
  background: rgba(8, 16, 32, 0.40);
  backdrop-filter: blur(3px);
  pointer-events: none;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 40px 36px 32px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  border-radius: 20px;
  box-shadow:
    0 20px 60px rgba(18, 127, 237, 0.10),
    0 4px 16px rgba(15, 23, 42, 0.06);
  position: relative;
  z-index: 1;
}

.brand-area {
  text-align: center;
  margin-bottom: 32px;
}

.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, #127fed 0%, #60affe 100%);
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(18, 127, 237, 0.30);
}

.login-title {
  margin: 0 0 4px;
  font-size: 1.65rem;
  font-weight: 800;
  letter-spacing: 2px;
  color: #0f172a;
}

.login-subtitle {
  margin: 0 0 6px;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
}

.login-desc {
  margin: 0;
  font-size: 0.78rem;
  color: #94a3b8;
  line-height: 1.5;
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
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.95rem;
  background: #fafbfc;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input:focus {
  border-color: #127fed;
  box-shadow: 0 0 0 3px rgba(18, 127, 237, 0.12);
}

.error {
  margin: 0;
  font-size: 0.85rem;
  color: #dc2626;
  text-align: center;
}

.submit {
  margin-top: 6px;
  width: 100%;
  padding: 13px 16px;
  border: none;
  border-radius: 11px;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 4px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(135deg, #127fed 0%, #60affe 100%);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 6px 20px rgba(18, 127, 237, 0.28);
}

.submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 26px rgba(18, 127, 237, 0.38);
}

.submit:active:not(:disabled) {
  transform: translateY(0);
}

.submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.register-link {
  display: block;
  text-align: center;
  margin-top: 22px;
  font-size: 0.9rem;
  color: #127fed;
  text-decoration: none;
  font-weight: 500;
}

.register-link:hover {
  text-decoration: underline;
}
</style>