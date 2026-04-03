<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'

const router = useRouter()

const oldPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  if (newPassword.value !== newPassword2.value) {
    errorMsg.value = '两次新密码不一致'
    return
  }
  loading.value = true
  try {
    await http.post('/api/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    ElMessage.success('密码已更新')
    oldPassword.value = ''
    newPassword.value = ''
    newPassword2.value = ''
    await router.push('/app/overview/dashboard')
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } } }
    const detail = ax.response?.data?.detail
    errorMsg.value = typeof detail === 'string' ? detail : '修改失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="panel">
      <h1 class="title">修改密码</h1>
      <p class="hint">修改成功后将跳转至总览</p>
      <form class="form" @submit.prevent="onSubmit">
        <label class="field">
          <span class="label">当前密码</span>
          <input
            v-model="oldPassword"
            type="password"
            autocomplete="current-password"
            class="input"
          />
        </label>
        <label class="field">
          <span class="label">新密码</span>
          <input
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            class="input"
            placeholder="至少 6 位"
          />
        </label>
        <label class="field">
          <span class="label">确认新密码</span>
          <input
            v-model="newPassword2"
            type="password"
            autocomplete="new-password"
            class="input"
          />
        </label>
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
        <button type="submit" class="submit" :disabled="loading">
          {{ loading ? '保存中…' : '保存' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 480px;
}

.panel {
  padding: 28px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}

.title {
  margin: 0 0 8px;
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
}

.hint {
  margin: 0 0 24px;
  font-size: 0.85rem;
  color: #94a3b8;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.95rem;
  outline: none;
}

.input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.error {
  margin: 0;
  font-size: 0.85rem;
  color: #dc2626;
}

.submit {
  margin-top: 8px;
  padding: 10px 18px;
  width: fit-content;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
}

.submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
