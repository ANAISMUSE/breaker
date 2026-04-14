<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance } from 'element-plus'
import http from '@/api/http'

interface DeviceRow {
  device_id: string
  name: string
  platform: string
  status: string
  last_seen: string
}

const devices = ref<DeviceRow[]>([])
const loading = ref(true)
const errorMsg = ref('')

const taskStatuses = ['idle', 'running', 'completed', 'stopped', 'error']
const createForm = ref({ name: '', platform: '' })
const creating = ref(false)
const updatingDeviceId = ref<string | null>(null)
const deletingDeviceId = ref<string | null>(null)
const batchDeleting = ref(false)
const selectedDeviceIds = ref<string[]>([])
const tableRef = ref<TableInstance>()

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<DeviceRow[]>('/api/devices')
    devices.value = Array.isArray(data) ? data : []
  } catch {
    errorMsg.value = '加载设备列表失败'
    devices.value = []
  } finally {
    loading.value = false
  }
  selectedDeviceIds.value = []
  tableRef.value?.clearSelection()
}

async function createDevice() {
  if (!createForm.value.name.trim() || !createForm.value.platform.trim()) {
    errorMsg.value = '请填写设备名与平台'
    return
  }

  creating.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/devices', {
      name: createForm.value.name.trim(),
      platform: createForm.value.platform.trim(),
    })
    createForm.value.name = ''
    createForm.value.platform = ''
    await load()
  } catch {
    errorMsg.value = '创建设备失败'
  } finally {
    creating.value = false
  }
}

async function updateDeviceStatus(device_id: string, status: string) {
  updatingDeviceId.value = device_id
  errorMsg.value = ''
  try {
    await http.patch(`/api/devices/${device_id}/status`, { status })
    await load()
  } catch {
    errorMsg.value = '更新设备状态失败'
  } finally {
    updatingDeviceId.value = null
  }
}

async function deleteDevice(row: DeviceRow) {
  try {
    await ElMessageBox.confirm(
      `确认删除设备 ${row.name}（${row.device_id}）吗？此操作不可恢复。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  deletingDeviceId.value = row.device_id
  errorMsg.value = ''
  try {
    await http.delete(`/api/devices/${row.device_id}`)
    ElMessage.success('设备已删除')
    await load()
  } catch {
    errorMsg.value = '删除设备失败'
  } finally {
    deletingDeviceId.value = null
  }
}

function onSelectionChange(rows: DeviceRow[]) {
  selectedDeviceIds.value = rows.map((r) => r.device_id)
}

async function batchDeleteDevices() {
  if (!selectedDeviceIds.value.length) {
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认批量删除已选中的 ${selectedDeviceIds.value.length} 台设备吗？此操作不可恢复。`,
      '批量删除确认',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  batchDeleting.value = true
  errorMsg.value = ''
  try {
    await http.delete('/api/devices', { data: { device_ids: selectedDeviceIds.value } })
    ElMessage.success('批量删除完成')
    await load()
  } catch {
    errorMsg.value = '批量删除设备失败'
  } finally {
    batchDeleting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">设备管理</h1>
        <div class="head-right">
          <el-button
            type="danger"
            plain
            :disabled="selectedDeviceIds.length === 0"
            :loading="batchDeleting"
            @click="batchDeleteDevices"
          >
            批量删除（{{ selectedDeviceIds.length }}）
          </el-button>
          <el-button type="primary" plain :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <el-form :inline="true" class="create-form">
        <el-form-item label="设备名">
          <el-input v-model="createForm.name" placeholder="例如：local-desktop" style="width: 220px" />
        </el-form-item>
        <el-form-item label="平台">
          <el-input v-model="createForm.platform" placeholder="例如：douyin" style="width: 220px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creating" @click="createDevice">创建</el-button>
        </el-form-item>
      </el-form>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="devices"
        stripe
        row-key="device_id"
        empty-text="暂无设备"
        style="width: 100%"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="platform" label="平台" width="120" />
        <el-table-column prop="status" label="状态" width="140" />
        <el-table-column prop="last_seen" label="最近在线" min-width="180" />
        <el-table-column prop="device_id" label="设备 ID" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" min-width="420">
          <template #default="{ row }">
            <div class="ops">
              <el-select v-model="row.status" size="small" style="width: 140px">
                <el-option v-for="s in taskStatuses" :key="s" :label="s" :value="s" />
              </el-select>
              <el-button
                size="small"
                type="primary"
                :loading="updatingDeviceId === row.device_id"
                @click="updateDeviceStatus(row.device_id, row.status)"
              >
                更新
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :loading="deletingDeviceId === row.device_id"
                @click="deleteDevice(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px 28px 28px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.head-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title {
  margin: 0;
  font-size: 1.35rem;
  color: #0f172a;
}

.error {
  margin: 0 0 12px;
  color: #dc2626;
  font-size: 0.9rem;
}

.create-form {
  margin: 0 0 18px;
}

.ops {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>

