<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getMyProfile, updateMyProfile } from '@/api/user'

const loading = ref(false)
const saving = ref(false)
const username = ref('')
const role = ref<'admin' | 'user'>('user')
const nickname = ref('')
const email = ref('')
const phone = ref('')
const avatar = ref('')
const PHONE_RE = /^\+?[0-9\- ]{6,20}$/
const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/
const avatarPreview = computed(() => avatar.value.trim() || '')

async function loadProfile() {
  loading.value = true
  try {
    const data = await getMyProfile()
    username.value = data.username
    role.value = data.role
    nickname.value = data.nickname || ''
    email.value = data.email || ''
    phone.value = data.phone || ''
    avatar.value = data.avatar || ''
  } finally {
    loading.value = false
  }
}

function validateBeforeSubmit() {
  const emailValue = email.value.trim()
  const phoneValue = phone.value.trim()
  const avatarValue = avatar.value.trim()
  if (emailValue && !EMAIL_RE.test(emailValue)) {
    ElMessage.warning('邮箱格式不合法')
    return false
  }
  if (phoneValue && !PHONE_RE.test(phoneValue)) {
    ElMessage.warning('手机号格式不合法')
    return false
  }
  if (avatarValue) {
    try {
      const parsed = new URL(avatarValue)
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        ElMessage.warning('头像 URL 仅支持 http/https')
        return false
      }
    } catch {
      ElMessage.warning('头像 URL 不合法')
      return false
    }
  }
  return true
}

async function onSubmit() {
  if (!validateBeforeSubmit()) {
    return
  }
  saving.value = true
  try {
    await updateMyProfile({
      nickname: nickname.value.trim() || null,
      email: email.value.trim() || null,
      phone: phone.value.trim() || null,
      avatar: avatar.value.trim() || null,
    })
    ElMessage.success('个人信息已保存')
    await loadProfile()
  } catch (error) {
    const err = error as { response?: { data?: { detail?: string } } }
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void loadProfile()
})
</script>

<template>
  <div class="page">
    <div class="panel">
      <div class="header">
        <h1>个人信息</h1>
        <p>维护头像、邮箱和手机号，保存前会做格式校验</p>
      </div>

      <el-skeleton :rows="4" animated v-if="loading" />

      <el-form v-else label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input :model-value="username" disabled />
        </el-form-item>
        <el-form-item label="当前角色">
          <el-tag :type="role === 'admin' ? 'danger' : 'info'">
            {{ role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="nickname" maxlength="64" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="email" maxlength="255" placeholder="name@example.com" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="phone" maxlength="32" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="头像 URL">
          <el-input v-model="avatar" maxlength="512" placeholder="https://..." />
          <div class="avatar-preview" v-if="avatarPreview">
            <el-avatar :size="56" :src="avatarPreview" />
          </div>
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 720px;
}

.panel {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
  padding: 24px;
}

.header {
  margin-bottom: 20px;
}

.header h1 {
  margin: 0 0 6px;
  font-size: 1.35rem;
  color: #0f172a;
}

.header p {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.avatar-preview {
  margin-top: 8px;
}
</style>
