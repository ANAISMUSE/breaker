<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

interface TaskRow {
  task_id: string
  name: string
  strategy: string
  status: string
  created_at: string
  rounds: number
  snapshot: Record<string, unknown>
  task_logs?: TaskLog[]
}

interface TaskLog {
  ts: string
  level: string
  event: string
  detail: Record<string, unknown>
}

interface TaskLogsPayload {
  task_id: string
  logs: TaskLog[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

interface DeviceRow {
  device_id: string
  name: string
  platform: string
  status: string
  last_seen: string
}

const tasks = ref<TaskRow[]>([])
const devices = ref<DeviceRow[]>([])
const loading = ref(true)
const errorMsg = ref('')

const taskStatuses = ['pending', 'running', 'completed', 'stopped'] as const
const taskStrategies = ['baseline', 'aggressive', 'ladder', 'mixed'] as const

const creating = ref(false)
const updatingTaskId = ref<string | null>(null)
const runningTaskId = ref<string | null>(null)

const createForm = ref({
  name: '',
  strategy: 'baseline',
  rounds: 14,
  rowsText: JSON.stringify(demoRows, null, 2),
  benchmarkText: JSON.stringify(demoBenchmark, null, 2),
  extraSnapshotText: '{}',
})

const taskDialogVisible = ref(false)
const taskDialogTask = ref<TaskRow | null>(null)
const taskLogs = ref<TaskLog[]>([])
const taskDetailLoading = ref(false)
const snapshotAppendText = ref('{}')
const snapshotAppending = ref(false)
const runDeviceId = ref('')
const logQueryLevel = ref('')
const logQueryEvent = ref('')
const logQueryTimeRange = ref<string[]>([])
const logPage = ref(1)
const logPageSize = ref(10)
const logTotal = ref(0)

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

function downloadBlob(filename: string, blob: Blob) {
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
    const [{ data: taskRows }, { data: deviceRows }] = await Promise.all([
      http.get<TaskRow[]>('/api/tasks'),
      http.get<DeviceRow[]>('/api/devices'),
    ])
    tasks.value = Array.isArray(taskRows) ? taskRows : []
    devices.value = Array.isArray(deviceRows) ? deviceRows : []
  } catch {
    errorMsg.value = '加载任务列表失败'
    tasks.value = []
    devices.value = []
  } finally {
    loading.value = false
  }
}

async function createTask() {
  if (!createForm.value.name.trim()) {
    errorMsg.value = '请填写任务名称'
    return
  }

  let rows: Record<string, unknown>[] = []
  let benchmark: Record<string, unknown> = {}
  let extraSnapshot: Record<string, unknown> = {}
  try {
    const parsedRows = JSON.parse(createForm.value.rowsText || '[]') as unknown
    if (!Array.isArray(parsedRows)) {
      throw new Error('样本数据必须是 JSON 数组')
    }
    rows = parsedRows as Record<string, unknown>[]
    const parsedBenchmark = JSON.parse(createForm.value.benchmarkText || '{}') as unknown
    if (!parsedBenchmark || typeof parsedBenchmark !== 'object' || Array.isArray(parsedBenchmark)) {
      throw new Error('参考值必须是 JSON 对象')
    }
    benchmark = parsedBenchmark as Record<string, unknown>
    const parsedExtra = JSON.parse(createForm.value.extraSnapshotText || '{}') as unknown
    extraSnapshot =
      parsedExtra && typeof parsedExtra === 'object' && !Array.isArray(parsedExtra)
        ? (parsedExtra as Record<string, unknown>)
        : {}
  } catch {
    errorMsg.value = '任务配置解析失败：请检查样本数据、参考值和附加信息的 JSON 格式'
    return
  }
  if (!rows.length || !Object.keys(benchmark).length) {
    errorMsg.value = '创建任务前请先配置样本数据和参考值'
    return
  }

  creating.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/tasks', {
      name: createForm.value.name.trim(),
      strategy: createForm.value.strategy,
      rounds: createForm.value.rounds,
      snapshot: {
        ...extraSnapshot,
        rows,
        benchmark,
      },
    })

    createForm.value.name = ''
    createForm.value.strategy = 'baseline'
    createForm.value.rounds = 14
    createForm.value.rowsText = JSON.stringify(demoRows, null, 2)
    createForm.value.benchmarkText = JSON.stringify(demoBenchmark, null, 2)
    createForm.value.extraSnapshotText = '{}'
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

async function runTask(task: TaskRow, useSelectedDevice = false) {
  runningTaskId.value = task.task_id
  errorMsg.value = ''
  try {
    const payload: Record<string, unknown> = useSelectedDevice ? { device_id: runDeviceId.value || undefined } : {}
    await http.post(`/api/tasks/${task.task_id}/run`, payload)
    await load()
    if (taskDialogTask.value?.task_id === task.task_id) {
      await loadTaskDetail(task.task_id)
    }
  } catch (e) {
    if (axios.isAxiosError(e)) {
      const detail = e.response?.data?.detail
      errorMsg.value = detail ? String(detail) : e.message
    } else {
      errorMsg.value = e instanceof Error ? e.message : '运行任务失败'
    }
  } finally {
    runningTaskId.value = null
  }
}

async function loadTaskDetail(task_id: string) {
  taskDetailLoading.value = true
  errorMsg.value = ''
  try {
    const [{ data: taskDetail }, { data: logsPayload }] = await Promise.all([
      http.get<TaskRow>(`/api/tasks/${task_id}`),
      http.get<TaskLogsPayload>(`/api/tasks/${task_id}/logs`, {
        params: {
          level: logQueryLevel.value || undefined,
          event: logQueryEvent.value || undefined,
          start_ts: logQueryTimeRange.value[0] || undefined,
          end_ts: logQueryTimeRange.value[1] || undefined,
          page: logPage.value,
          page_size: logPageSize.value,
        },
      }),
    ])
    taskDialogTask.value = taskDetail
    taskLogs.value = Array.isArray(logsPayload?.logs) ? logsPayload.logs : []
    logTotal.value = Number.isFinite(logsPayload?.total) ? logsPayload.total : taskLogs.value.length
  } catch {
    errorMsg.value = '加载任务详情失败'
  } finally {
    taskDetailLoading.value = false
  }
}

async function openDetail(task: TaskRow) {
  taskLogs.value = []
  snapshotAppendText.value = '{}'
  logQueryLevel.value = ''
  logQueryEvent.value = ''
  logQueryTimeRange.value = []
  logPage.value = 1
  logPageSize.value = 10
  logTotal.value = 0
  runDeviceId.value = ''
  taskDialogTask.value = task
  taskDialogVisible.value = true
  await loadTaskDetail(task.task_id)
}

function taskRowsCount(task: TaskRow): number {
  const rows = task.snapshot?.rows
  return Array.isArray(rows) ? rows.length : 0
}

function taskBenchmarkCount(task: TaskRow): number {
  const benchmark = task.snapshot?.benchmark
  return benchmark && typeof benchmark === 'object' && !Array.isArray(benchmark) ? Object.keys(benchmark).length : 0
}

function applyDemoConfig() {
  createForm.value.rowsText = JSON.stringify(demoRows, null, 2)
  createForm.value.benchmarkText = JSON.stringify(demoBenchmark, null, 2)
}

function onImportedRows(
  rows: Record<string, unknown>[],
  _meta?: {
    format: string
    rowCount: number
    filename: string
    detectedPlatform: string
    invalidRowCount: number
    invalidRows: Array<{ row_index: number; reason: string; content_id: string }>
    warnings: string[]
  },
) {
  errorMsg.value = ''
  createForm.value.rowsText = JSON.stringify(rows, null, 2)
}

function onImportError(message: string) {
  errorMsg.value = message
}

async function applyLogFilter() {
  if (!taskDialogTask.value) {
    return
  }
  logPage.value = 1
  await loadTaskDetail(taskDialogTask.value.task_id)
}

async function onLogPageChange(page: number) {
  if (!taskDialogTask.value) {
    return
  }
  logPage.value = page
  await loadTaskDetail(taskDialogTask.value.task_id)
}

async function onLogPageSizeChange(size: number) {
  if (!taskDialogTask.value) {
    return
  }
  logPageSize.value = size
  logPage.value = 1
  await loadTaskDetail(taskDialogTask.value.task_id)
}

async function appendSnapshotFromDialog() {
  if (!taskDialogTask.value) {
    return
  }
  let parsed: Record<string, unknown> = {}
  try {
    const raw = JSON.parse(snapshotAppendText.value || '{}') as unknown
    parsed = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {}
  } catch {
    errorMsg.value = '追加 snapshot 失败：请输入合法 JSON 对象'
    return
  }
  snapshotAppending.value = true
  errorMsg.value = ''
  try {
    await http.post(`/api/tasks/${taskDialogTask.value.task_id}/snapshots`, { data: parsed })
    snapshotAppendText.value = '{}'
    await loadTaskDetail(taskDialogTask.value.task_id)
    await load()
  } catch {
    errorMsg.value = '追加 snapshot 失败'
  } finally {
    snapshotAppending.value = false
  }
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

async function exportTaskLogs(task_id: string) {
  errorMsg.value = ''
  try {
    const { data } = await http.get<TaskLogsPayload>(`/api/tasks/${task_id}/logs`, {
      params: { page: 1, page_size: 1000 },
    })
    if (!data || !Array.isArray(data.logs)) {
      errorMsg.value = '导出日志失败：返回内容异常'
      return
    }
    downloadJson(`task_logs_${task_id}.json`, data)
  } catch {
    errorMsg.value = '导出日志失败'
  }
}

async function exportTaskLogsCsv(task_id: string) {
  errorMsg.value = ''
  try {
    const response = await http.get<Blob>(`/api/tasks/${task_id}/logs/export.csv`, {
      params: { page: 1, page_size: 1000 },
      responseType: 'blob',
    })
    downloadBlob(`task_logs_${task_id}.csv`, response.data)
  } catch {
    errorMsg.value = '导出日志 CSV 失败'
  }
}

async function exportFilteredLogsCsv() {
  if (!taskDialogTask.value) {
    return
  }
  errorMsg.value = ''
  try {
    const response = await http.get<Blob>(`/api/tasks/${taskDialogTask.value.task_id}/logs/export.csv`, {
      params: {
        level: logQueryLevel.value || undefined,
        event: logQueryEvent.value || undefined,
        start_ts: logQueryTimeRange.value[0] || undefined,
        end_ts: logQueryTimeRange.value[1] || undefined,
      },
      responseType: 'blob',
    })
    downloadBlob(`task_logs_${taskDialogTask.value.task_id}_filtered.csv`, response.data)
  } catch {
    errorMsg.value = '导出筛选日志 CSV 失败'
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
        <el-form-item>
          <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
        </el-form-item>
        <el-form-item>
          <el-button plain @click="applyDemoConfig">填充演示任务数据</el-button>
        </el-form-item>
      </el-form>

      <div class="snapshot-box">
        <div class="snapshot-label">任务输入配置（创建时设置，运行时自动沿用）</div>
        <el-input
          v-model="createForm.rowsText"
          type="textarea"
          :rows="5"
          placeholder='样本数据（JSON 数组），例如：[{"content_id":"1","platform":"douyin","topic":"technology","text":"..."}]'
        />
        <el-input
          v-model="createForm.benchmarkText"
          type="textarea"
          :rows="3"
          placeholder='参考值设置（JSON 对象），例如：{"technology":0.4,"society":0.3}'
          style="margin-top: 8px"
        />
        <el-input
          v-model="createForm.extraSnapshotText"
          type="textarea"
          :rows="2"
          placeholder='可选附加信息（JSON 对象）'
          style="margin-top: 8px"
        />
      </div>

      <el-table v-loading="loading" :data="tasks" stripe empty-text="暂无任务" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="strategy" label="策略" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="rounds" label="轮次" width="80" />
        <el-table-column label="任务数据" min-width="150">
          <template #default="{ row }">
            样本={{ taskRowsCount(row) }} / 参考值={{ taskBenchmarkCount(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column prop="task_id" label="任务 ID" min-width="260" show-overflow-tooltip />
        <el-table-column label="操作" min-width="560">
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
              <el-button
                size="small"
                type="success"
                :loading="runningTaskId === row.task_id"
                @click="runTask(row)"
              >
                运行
              </el-button>
              <el-button size="small" @click="openDetail(row)">详情</el-button>
              <el-button size="small" @click="exportTaskJson(row.task_id)">导出JSON</el-button>
              <el-button size="small" @click="exportTaskLogs(row.task_id)">导出日志JSON</el-button>
              <el-button size="small" @click="exportTaskLogsCsv(row.task_id)">导出日志CSV</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="taskDialogVisible" title="任务详情" width="70%">
      <div v-loading="taskDetailLoading" v-if="taskDialogTask">
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
        <div class="dialog-snapshot">
          <div class="dialog-snapshot-title">追加 snapshot（JSON）</div>
          <el-input
            v-model="snapshotAppendText"
            type="textarea"
            :rows="4"
            placeholder='例如：{"round":1,"note":"manual check"}'
          />
          <div class="append-actions">
            <el-button type="primary" size="small" :loading="snapshotAppending" @click="appendSnapshotFromDialog">
              追加 snapshot
            </el-button>
          </div>
        </div>
        <div class="dialog-snapshot">
          <div class="dialog-snapshot-title">运行设置（仅选择设备，任务数据沿用创建配置）</div>
          <el-select
            v-model="runDeviceId"
            clearable
            placeholder="可选：指定设备（为空则自动调度 idle 设备）"
            style="width: 100%; margin-bottom: 8px"
          >
            <el-option
              v-for="d in devices"
              :key="d.device_id"
              :label="`${d.name} (${d.platform}) - ${d.status}`"
              :value="d.device_id"
              :disabled="d.status !== 'idle'"
            />
          </el-select>
          <div class="append-actions">
            <el-button
              type="success"
              size="small"
              :loading="runningTaskId === taskDialogTask.task_id"
              @click="runTask(taskDialogTask, true)"
            >
              运行当前任务
            </el-button>
          </div>
        </div>
        <div class="dialog-snapshot">
          <div class="dialog-snapshot-title">task logs（{{ taskLogs.length }}）</div>
          <div class="log-filters">
            <el-select v-model="logQueryLevel" placeholder="级别筛选" style="width: 140px" clearable>
              <el-option label="info" value="info" />
              <el-option label="warn" value="warn" />
              <el-option label="error" value="error" />
            </el-select>
            <el-input v-model="logQueryEvent" placeholder="事件关键字" style="width: 220px" clearable />
            <el-date-picker
              v-model="logQueryTimeRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
            <el-button size="small" type="primary" @click="applyLogFilter">筛选</el-button>
            <el-button size="small" @click="exportFilteredLogsCsv">导出筛选CSV</el-button>
          </div>
          <el-table :data="taskLogs" stripe empty-text="暂无任务日志" style="width: 100%">
            <el-table-column prop="ts" label="时间" min-width="180" />
            <el-table-column prop="level" label="级别" width="100" />
            <el-table-column prop="event" label="事件" min-width="180" />
            <el-table-column label="详情" min-width="320">
              <template #default="{ row }">
                <pre class="log-detail">{{ JSON.stringify(row.detail || {}, null, 2) }}</pre>
              </template>
            </el-table-column>
          </el-table>
          <div class="log-pagination">
            <el-pagination
              background
              layout="total, sizes, prev, pager, next"
              :total="logTotal"
              :page-size="logPageSize"
              :current-page="logPage"
              :page-sizes="[5, 10, 20, 50]"
              @current-change="onLogPageChange"
              @size-change="onLogPageSizeChange"
            />
          </div>
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

.log-detail {
  margin: 0;
  white-space: pre-wrap;
  font-size: 0.8rem;
  color: #334155;
}

.append-actions {
  margin-top: 10px;
}

.log-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.log-pagination {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>
