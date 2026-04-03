<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import http from '@/api/http'

interface TaskRow {
  task_id: string
  name: string
  strategy: string
  status: string
  created_at: string
  rounds: number
  snapshot: Record<string, unknown>
}

const tasks = ref<TaskRow[]>([])
const loading = ref(true)
const errorMsg = ref('')

const taskStatuses = ['pending', 'running', 'completed', 'stopped'] as const
const taskStrategies = ['baseline', 'aggressive', 'ladder', 'mixed'] as const

const creating = ref(false)
const updatingTaskId = ref<string | null>(null)

const createForm = ref({
  name: '',
  strategy: 'baseline',
  rounds: 14,
  snapshotText: '{}',
})

const taskDialogVisible = ref(false)
const taskDialogTask = ref<TaskRow | null>(null)

const snapshotText = computed(() =>
  taskDialogTask.value ? JSON.stringify(taskDialogTask.value.snapshot ?? {}, null, 2) : '',
)

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<TaskRow[]>('/api/tasks')
    tasks.value = Array.isArray(data) ? data : []
  } catch {
    errorMsg.value = '加载任务列表失败'
    tasks.value = []
  } finally {
    loading.value = false
  }
}

async function createTask() {
  if (!createForm.value.name.trim()) {
    errorMsg.value = '请填写任务名称'
    return
  }

  let snapshot: Record<string, unknown> = {}
  try {
    const parsed = JSON.parse(createForm.value.snapshotText || '{}') as unknown
    snapshot = parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {}
  } catch {
    errorMsg.value = 'snapshot 必须是合法 JSON 对象'
    return
  }

  creating.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/tasks', {
      name: createForm.value.name.trim(),
      strategy: createForm.value.strategy,
      rounds: createForm.value.rounds,
      snapshot,
    })

    createForm.value.name = ''
    createForm.value.strategy = 'baseline'
    createForm.value.rounds = 14
    createForm.value.snapshotText = '{}'
    await load()
  } catch {
    errorMsg.value = '创建任务失败'
  } finally {
    creating.value = false
  }
}

async function updateStatus(task: TaskRow) {
  updatingTaskId.value = task.task_id
  errorMsg.value = ''
  try {
    await http.patch(`/api/tasks/${task.task_id}/status`, { status: task.status })
    await load()
  } catch {
    errorMsg.value = '更新任务状态失败'
  } finally {
    updatingTaskId.value = null
  }
}

function openDetail(task: TaskRow) {
  taskDialogTask.value = task
  taskDialogVisible.value = true
}

async function exportTaskJson(task_id: string) {
  errorMsg.value = ''
  try {
    const { data } = await http.get(`/api/tasks/${task_id}`)
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      errorMsg.value = '导出任务失败：任务不存在或返回内容异常'
      return
    }
    downloadJson(`task_${task_id}.json`, data)
  } catch {
    errorMsg.value = '导出任务失败'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">任务管理</h1>
        <div class="head-right">
          <el-button type="primary" plain :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <el-form :inline="true" class="create-form">
        <el-form-item label="任务名">
          <el-input v-model="createForm.name" placeholder="例如：Cocoon-Check-001" style="width: 260px" />
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="createForm.strategy" style="width: 160px">
            <el-option v-for="s in taskStrategies" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="轮次">
          <el-input-number v-model="createForm.rounds" :min="1" :max="100" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creating" @click="createTask">创建</el-button>
        </el-form-item>
      </el-form>

      <div class="snapshot-box">
        <div class="snapshot-label">snapshot（JSON，对后端任务记录用；可留空/保持默认）</div>
        <el-input v-model="createForm.snapshotText" type="textarea" :rows="3" placeholder='例如：{"snapshots":[...]}'
        />
      </div>

      <el-table v-loading="loading" :data="tasks" stripe empty-text="暂无任务" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="strategy" label="策略" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="rounds" label="轮次" width="80" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column prop="task_id" label="任务 ID" min-width="260" show-overflow-tooltip />
        <el-table-column label="操作" min-width="460">
          <template #default="{ row }">
            <div class="ops">
              <el-select v-model="row.status" size="small" style="width: 140px">
                <el-option v-for="s in taskStatuses" :key="s" :label="s" :value="s" />
              </el-select>
              <el-button
                size="small"
                type="primary"
                :loading="updatingTaskId === row.task_id"
                @click="updateStatus(row)"
              >
                更新
              </el-button>
              <el-button size="small" @click="openDetail(row)">详情</el-button>
              <el-button size="small" @click="exportTaskJson(row.task_id)">导出JSON</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="taskDialogVisible" title="任务详情" width="70%">
      <div v-if="taskDialogTask">
        <div class="dialog-meta">
          <div><span class="k">任务名：</span>{{ taskDialogTask.name }}</div>
          <div><span class="k">策略：</span>{{ taskDialogTask.strategy }}</div>
          <div><span class="k">状态：</span>{{ taskDialogTask.status }}</div>
          <div><span class="k">轮次：</span>{{ taskDialogTask.rounds }}</div>
          <div><span class="k">创建时间：</span>{{ taskDialogTask.created_at }}</div>
          <div><span class="k">任务 ID：</span>{{ taskDialogTask.task_id }}</div>
        </div>
        <div class="dialog-snapshot">
          <div class="dialog-snapshot-title">snapshot</div>
          <el-input type="textarea" :rows="12" :model-value="snapshotText" readonly />
        </div>
      </div>
    </el-dialog>
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
  margin: 0 0 14px;
}

.snapshot-box {
  margin: 0 0 16px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
}

.snapshot-label {
  color: #334155;
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.ops {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dialog-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  margin-bottom: 12px;
  color: #0f172a;
}

.k {
  font-weight: 700;
  color: #334155;
}

.dialog-snapshot-title {
  font-weight: 700;
  margin-bottom: 8px;
  color: #334155;
}
</style>
