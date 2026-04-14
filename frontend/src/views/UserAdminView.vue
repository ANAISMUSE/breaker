<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listUsers, updateUserRole, type UserProfile } from '@/api/user'

const loading = ref(false)
const users = ref<UserProfile[]>([])
const updatingUser = ref<string | null>(null)

async function loadUsers() {
  loading.value = true
  try {
    users.value = await listUsers()
  } finally {
    loading.value = false
  }
}

async function onRoleChange(row: UserProfile, role: 'admin' | 'user') {
  updatingUser.value = row.username
  try {
    await updateUserRole(row.username, role)
    ElMessage.success(`已更新 ${row.username} 的角色`)
    await loadUsers()
  } catch (error) {
    const err = error as { response?: { data?: { detail?: string } } }
    ElMessage.error(err.response?.data?.detail || '角色更新失败')
  } finally {
    updatingUser.value = null
  }
}

function onRoleSelectChange(row: UserProfile, value: string) {
  if (value !== 'admin' && value !== 'user') {
    return
  }
  void onRoleChange(row, value)
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <div class="page">
    <div class="panel">
      <div class="header">
        <h1>用户权限管理</h1>
        <p>仅管理员可访问，用于区分管理员与普通用户</p>
      </div>

      <el-table :data="users" border stripe v-loading="loading">
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column label="昵称" min-width="140">
          <template #default="{ row }">{{ row.nickname || '-' }}</template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="220">
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column label="手机号" min-width="140">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-select
              :model-value="row.role"
              :disabled="updatingUser === row.username"
              style="width: 140px"
              @change="onRoleSelectChange(row, $event)"
            >
              <el-option label="管理员" value="admin" />
              <el-option label="普通用户" value="user" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 960px;
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
</style>
