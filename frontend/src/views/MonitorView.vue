<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import http from '@/api/http'

interface DashboardData {
  task_count: number
  device_count: number
  task_status_counts: Record<string, number>
  device_status_counts: Record<string, number>
  platform_counts: Record<string, number>
  recent_tasks: Array<Record<string, unknown>>
  recent_audits: Array<Record<string, unknown>>
}

interface RealtimeStatus {
  enabled: boolean
  adapter: string
  mode: 'real' | 'demo'
  real_mode_allowed?: boolean
  gate_reason?: string | null
  adapter_ready: boolean
  project_dir: string | null
  last_output_exists: boolean
  last_output_file: string
  legal_ack: boolean
}

interface CrawlPreviewResponse {
  rows: Array<Record<string, unknown>>
  row_count: number
  mode: 'real' | 'demo'
  degraded: boolean
  reason: string
}

const loading = ref(true)
const errorMsg = ref('')
const data = ref<DashboardData | null>(null)
const realtimeStatus = ref<RealtimeStatus | null>(null)
const crawlKeyword = ref('')
const crawlLimit = ref(30)
const crawling = ref(false)
const crawlRows = ref<Array<Record<string, unknown>>>([])
const crawlMeta = ref<{ mode: 'real' | 'demo'; degraded: boolean; reason: string } | null>(null)

const taskEl = ref<HTMLDivElement | null>(null)
const deviceEl = ref<HTMLDivElement | null>(null)
const platformEl = ref<HTMLDivElement | null>(null)

let taskChart: echarts.ECharts | null = null
let deviceChart: echarts.ECharts | null = null
let platformChart: echarts.ECharts | null = null

function safeEntries(counts: Record<string, number> | null | undefined): Array<[string, number]> {
  const entries = Object.entries(counts || {})
  entries.sort((a, b) => b[1] - a[1])
  return entries
}

function getBarOption(title: string, counts: Record<string, number>): echarts.EChartsOption {
  const entries = safeEntries(counts)
  const categories = entries.map(([k]) => k)
  const values = entries.map(([, v]) => v)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { left: 30, right: 10, top: 28, bottom: 40, containLabel: true },
    title: { text: title, left: 10, top: 6, textStyle: { fontSize: 14, color: '#0f172a' } },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: 30 },
      axisTick: { alignWithLabel: true },
    },
    yAxis: { type: 'value', min: 0 },
    series: [
      {
        name: title,
        type: 'bar',
        data: values,
        barMaxWidth: 36,
        itemStyle: { color: '#3b82f6' },
      },
    ],
  }
}

function renderCharts() {
  if (!data.value) return

  if (taskEl.value) {
    taskChart = taskChart ?? echarts.init(taskEl.value)
    taskChart.setOption(getBarOption('任务状态分布', data.value.task_status_counts || {}), true)
  }
  if (deviceEl.value) {
    deviceChart = deviceChart ?? echarts.init(deviceEl.value)
    deviceChart.setOption(getBarOption('设备状态分布', data.value.device_status_counts || {}), true)
  }
  if (platformEl.value) {
    platformChart = platformChart ?? echarts.init(platformEl.value)
    const entries = safeEntries(data.value.platform_counts || {})
    const top = entries.slice(0, 8)
    const otherSum = entries.slice(8).reduce((acc, [, v]) => acc + v, 0)
    const pieData = otherSum > 0 ? [...top.map(([k, v]) => ({ name: k, value: v })), { name: '其他', value: otherSum }] : top.map(([k, v]) => ({ name: k, value: v }))

    platformChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 4, type: 'scroll' },
      title: { text: '平台分布', left: 10, top: 6, textStyle: { fontSize: 14, color: '#0f172a' } },
      series: [
        {
          name: '平台数量',
          type: 'pie',
          radius: ['45%', '70%'],
          avoidLabelOverlap: true,
          label: { formatter: '{b}: {d}%' },
          data: pieData,
        },
      ],
    })
  }
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [dashboardResp, realtimeResp] = await Promise.all([
      http.get<DashboardData>('/api/analytics/dashboard'),
      http.get<RealtimeStatus>('/api/realtime/status'),
    ])
    data.value = dashboardResp.data
    realtimeStatus.value = realtimeResp.data
    await nextTick()
    renderCharts()
  } catch {
    errorMsg.value = '监控总览加载失败'
    data.value = null
    realtimeStatus.value = null
  } finally {
    loading.value = false
  }
}

async function runCrawlPreview() {
  crawling.value = true
  try {
    const { data: resp } = await http.post<CrawlPreviewResponse>('/api/realtime/crawl-preview', {
      platform: 'douyin',
      keyword: crawlKeyword.value,
      limit: crawlLimit.value,
    })
    crawlRows.value = Array.isArray(resp.rows) ? resp.rows : []
    crawlMeta.value = {
      mode: resp.mode,
      degraded: resp.degraded,
      reason: resp.reason || '',
    }
  } catch (e) {
    crawlRows.value = []
    crawlMeta.value = null
    errorMsg.value = e instanceof Error ? e.message : '监测样本拉取失败'
  } finally {
    crawling.value = false
  }
}

onMounted(load)

onBeforeUnmount(() => {
  taskChart?.dispose()
  deviceChart?.dispose()
  platformChart?.dispose()
  taskChart = null
  deviceChart = null
  platformChart = null
})
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">监控总览</h1>
        <el-button type="primary" plain :loading="loading" @click="load">刷新</el-button>
      </div>
      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div v-if="realtimeStatus" class="realtime-card">
        <div class="realtime-head">
          <div>
            <div class="realtime-title">云监测适配器状态</div>
            <div class="realtime-subtitle">
              当前模式：
              <strong>{{ realtimeStatus.mode === 'real' ? '真实适配器' : '演示模式' }}</strong>
            </div>
          </div>
          <el-tag :type="realtimeStatus.enabled ? 'success' : 'info'">
            {{ realtimeStatus.enabled ? '已启用' : '未启用' }}
          </el-tag>
        </div>
        <div class="realtime-meta">
          <span>适配器：{{ realtimeStatus.adapter }}</span>
          <span>就绪：{{ realtimeStatus.adapter_ready ? '是' : '否' }}</span>
          <span>合规确认：{{ realtimeStatus.legal_ack ? '已确认' : '未确认' }}</span>
          <span>最近输出：{{ realtimeStatus.last_output_exists ? '存在' : '暂无' }}</span>
        </div>
        <p v-if="realtimeStatus.gate_reason" class="realtime-gate">真实模式未放行：{{ realtimeStatus.gate_reason }}</p>
      </div>

      <div class="realtime-card">
        <div class="realtime-head">
          <div>
            <div class="realtime-title">监测样本预览（含降级）</div>
            <div class="realtime-subtitle">真实模式不可用时会自动降级到演示数据。</div>
          </div>
          <el-button type="primary" plain :loading="crawling" @click="runCrawlPreview">拉取样本</el-button>
        </div>
        <div class="filters">
          <el-input v-model="crawlKeyword" placeholder="关键词（可选）" style="max-width: 220px" clearable />
          <el-input-number v-model="crawlLimit" :min="1" :max="200" />
        </div>
        <div v-if="crawlMeta" class="realtime-meta">
          <span>返回模式：{{ crawlMeta.mode === 'real' ? '真实适配器' : '演示模式' }}</span>
          <span>是否降级：{{ crawlMeta.degraded ? '是' : '否' }}</span>
          <span v-if="crawlMeta.reason">原因：{{ crawlMeta.reason }}</span>
          <span>样本数：{{ crawlRows.length }}</span>
        </div>
        <el-table v-if="crawlRows.length" :data="crawlRows" size="small" max-height="280">
          <el-table-column prop="user_id" label="用户ID" min-width="120" />
          <el-table-column prop="topic" label="主题" min-width="100" />
          <el-table-column prop="text" label="文本" min-width="300" show-overflow-tooltip />
        </el-table>
        <p v-else class="empty-hint">点击「拉取样本」后展示预览数据。</p>
      </div>

      <div v-if="data" class="stats">
        <el-statistic title="任务总数" :value="data.task_count" />
        <el-statistic title="设备总数" :value="data.device_count" />
      </div>

      <div v-if="data" class="grid">
        <div class="panel">
          <div ref="taskEl" class="chart" />
        </div>
        <div class="panel">
          <div ref="deviceEl" class="chart" />
        </div>
      </div>

      <div v-if="data" class="grid2">
        <div class="panel">
          <div ref="platformEl" class="chart" />
        </div>

        <div class="panel">
          <div class="panel-head">最近任务（任务列表）</div>
          <el-table :data="data.recent_tasks" size="small" style="width: 100%" row-key="task_id">
            <el-table-column prop="name" label="任务名" min-width="90" />
            <el-table-column prop="strategy" label="策略" min-width="90" />
            <el-table-column label="状态" min-width="80">
              <template #default="{ row }">
                <el-tag
                  :type="
                    row.status === 'completed'
                      ? 'success'
                      : row.status === 'running'
                        ? 'primary'
                        : row.status === 'failed'
                          ? 'danger'
                          : 'info'
                  "
                >
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rounds" label="轮次" min-width="60" />
            <el-table-column prop="created_at" label="创建时间" min-width="160" />
          </el-table>
        </div>
      </div>

      <div v-if="data" class="panel audit-panel">
        <div class="panel-head">最新审计日志（操作留痕）</div>
        <el-table :data="data.recent_audits" size="small" style="width: 100%" row-key="ts">
          <el-table-column prop="ts" label="时间" min-width="180" />
          <el-table-column prop="event" label="事件" min-width="160" />
          <el-table-column label="详情" min-width="420">
            <template #default="{ row }">
              <pre class="detail">{{ JSON.stringify(row.detail || row.detail || {}, null, 2) }}</pre>
            </template>
          </el-table-column>
        </el-table>
      </div>
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
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.title {
  margin: 0;
  font-size: 1.35rem;
  color: #0f172a;
}
.error {
  color: #dc2626;
  margin: 0 0 12px;
  font-size: 0.95rem;
}
.stats {
  display: flex;
  gap: 36px;
  margin-bottom: 18px;
}
.realtime-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f8fafc;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.realtime-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.realtime-title {
  color: #0f172a;
  font-weight: 700;
}
.realtime-subtitle {
  color: #475569;
  font-size: 13px;
  margin-top: 2px;
}
.realtime-meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  color: #334155;
  font-size: 13px;
}
.realtime-gate {
  margin: 10px 0 0;
  color: #b45309;
  font-size: 13px;
}
.empty-hint {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 13px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.grid2 {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 16px;
  margin-top: 16px;
}
.panel {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  background: #fafafa;
}
.chart {
  width: 100%;
  height: 340px;
}

.panel-head {
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
  margin: 2px 0 10px;
}

.audit-panel {
  margin-top: 16px;
}

.detail {
  margin: 0;
  white-space: pre-wrap;
  color: #334155;
  font-size: 0.78rem;
}
</style>

