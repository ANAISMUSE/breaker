<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

type RowsRow = {
  topic?: string
  semantic_summary?: string
}

type RiskDetailResponse = {
  llm?: {
    semantic_rows?: number
    evidence?: Array<{ content_id: string; topic: string; summary: string }>
  }
  distributions: {
    topic: Record<string, number>
    benchmark: Record<string, number>
    alignment: number
  }
  derived: {
    s2_cross: { top2: string[] }
  }
  suggestions: {
    s4: null | {
      recommended_topics: Array<{ topic: string; benchmark: number; actual: number; deficit: number }>
    }
  }
}

const rows = ref<RowsRow[]>(demoRows as RowsRow[])
const benchmark = ref<Record<string, number>>(demoBenchmark)
const rowsReady = ref(true)
const benchmarkReady = ref(true)
const loading = ref(false)
const errorMsg = ref('')
const detail = ref<RiskDetailResponse | null>(null)
const selectedNode = ref('')

const graphEl = ref<HTMLDivElement | null>(null)
let graphChart: echarts.ECharts | null = null
let resizeHandler: (() => void) | null = null

function toPercent(v: number) {
  return `${(v * 100).toFixed(1)}%`
}

function buildGraphFromDetail(payload: RiskDetailResponse) {
  const topicDist = payload.distributions.topic ?? {}
  const benchmarkDist = payload.distributions.benchmark ?? {}
  const top2 = new Set(payload.derived?.s2_cross?.top2 ?? [])
  const gapMap = new Map(
    (payload.suggestions?.s4?.recommended_topics ?? []).map((item) => [item.topic, Math.max(0, item.deficit)])
  )

  const topicEntries = Object.entries(topicDist).sort((a, b) => b[1] - a[1])
  const benchmarkEntries = Object.entries(benchmarkDist).sort((a, b) => b[1] - a[1])
  const allTopics = Array.from(new Set([...topicEntries.map(([k]) => k), ...benchmarkEntries.map(([k]) => k)]))

  const nodes = allTopics.map((name) => {
    const topicValue = topicDist[name] ?? 0
    const benchmarkValue = benchmarkDist[name] ?? 0
    const deficit = Math.max(0, benchmarkValue - topicValue)
    return {
      id: `topic:${name}`,
      name,
      category: top2.has(name) ? 1 : 0,
      value: Number(topicValue.toFixed(4)),
      benchmarkValue: Number(benchmarkValue.toFixed(4)),
      deficit: Number(deficit.toFixed(4)),
      symbolSize: Math.min(56, 16 + topicValue * 120),
    }
  })

  const links: Array<{ source: string; target: string; value: number; lineStyle: { width: number; opacity: number } }> =
    []
  const top2Topics = Array.from(top2)
  for (const topic of allTopics) {
    if (top2.has(topic)) continue
    const p = topicDist[topic] ?? 0
    for (const core of top2Topics) {
      const coreP = topicDist[core] ?? 0
      const weight = Math.max(0, Math.min(p, coreP))
      if (weight <= 0) continue
      links.push({
        source: `topic:${core}`,
        target: `topic:${topic}`,
        value: Number(weight.toFixed(4)),
        lineStyle: { width: Math.max(1, weight * 16), opacity: 0.7 },
      })
    }
  }

  for (const [topic, deficit] of gapMap.entries()) {
    if (deficit <= 0) continue
    const gapId = `gap:${topic}`
    nodes.push({
      id: gapId,
      name: `${topic} 缺口`,
      category: 2,
      value: Number(deficit.toFixed(4)),
      benchmarkValue: Number((benchmarkDist[topic] ?? 0).toFixed(4)),
      deficit: Number(deficit.toFixed(4)),
      symbolSize: Math.min(36, 12 + deficit * 100),
    })
    links.push({
      source: gapId,
      target: `topic:${topic}`,
      value: Number(deficit.toFixed(4)),
      lineStyle: { width: Math.max(1.2, deficit * 20), opacity: 0.8 },
    })
  }

  return { nodes, links }
}

async function renderGraph(payload: RiskDetailResponse) {
  await nextTick()
  if (!graphEl.value) return
  graphChart = graphChart ?? echarts.init(graphEl.value)
  const { nodes, links } = buildGraphFromDetail(payload)
  graphChart.setOption({
    title: { text: '语义关联图谱（统一 detail 数据源）', left: 'center', top: 8 },
    tooltip: { trigger: 'item' },
    legend: { data: ['主题分布', 'Top2主题', '覆盖缺口'], top: 38 },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        categories: [{ name: '主题分布' }, { name: 'Top2主题' }, { name: '覆盖缺口' }],
        force: { repulsion: 280, edgeLength: [80, 180] },
        data: nodes,
        links,
        label: { show: true, formatter: '{b}' },
        lineStyle: { color: 'source', curveness: 0.1 },
      },
    ],
  })
  graphChart.off('click')
  graphChart.on('click', (params) => {
    const datum = params.data as { name?: unknown } | undefined
    const value = datum?.name
    if (typeof value === 'string') selectedNode.value = value
  })
}

async function evaluateGraph() {
  if (loading.value || !rowsReady.value || !benchmarkReady.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    const payload = { rows: rows.value, benchmark: benchmark.value }
    const { data } = await http.post<RiskDetailResponse>('/api/risk/detail', payload)
    detail.value = data
    await renderGraph(data)
  } catch (e) {
    detail.value = null
    errorMsg.value = e instanceof Error ? e.message : '语义图谱生成失败'
  } finally {
    loading.value = false
  }
}

async function loadJsonFile<T>(file: File): Promise<T> {
  const text = await file.text()
  return JSON.parse(text) as T
}

async function onPickDemo() {
  rows.value = demoRows as RowsRow[]
  benchmark.value = demoBenchmark
  rowsReady.value = true
  benchmarkReady.value = true
  selectedNode.value = ''
  await evaluateGraph()
}

async function onImportedRows(
  records: Record<string, unknown>[],
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
  rows.value = records as RowsRow[]
  rowsReady.value = true
  selectedNode.value = ''
  await evaluateGraph()
}

function onImportError(message: string) {
  rowsReady.value = false
  errorMsg.value = message
}

async function onPickBenchmark(file: File | null) {
  errorMsg.value = ''
  if (!file) return
  try {
    const parsed = await loadJsonFile<unknown>(file)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('benchmark 文件必须是 JSON 对象')
    benchmark.value = parsed as Record<string, number>
    benchmarkReady.value = true
    selectedNode.value = ''
    await evaluateGraph()
  } catch (e) {
    benchmarkReady.value = false
    errorMsg.value = e instanceof Error ? e.message : 'benchmark 文件解析失败'
  }
}

onMounted(() => {
  evaluateGraph()
  resizeHandler = () => graphChart?.resize()
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  graphChart?.dispose()
  graphChart = null
})
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">语义关联图谱</h1>
        <el-button :disabled="loading" @click="onPickDemo">使用演示数据</el-button>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="inputs">
        <el-card class="input-card" shadow="never">
          <template #header>
            <div class="card-title">数据导入</div>
          </template>
          <div class="row">
            <div class="label">rows（统一导入）</div>
            <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
            <div class="meta">{{ rowsReady ? '已就绪' : '未就绪' }}</div>
          </div>
          <div class="row">
            <div class="label">benchmark（JSON 对象）</div>
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept="application/json"
              :on-change="(file: any) => onPickBenchmark((file?.raw as File) ?? null)"
            >
              <el-button>选择 benchmark.json</el-button>
            </el-upload>
            <div class="meta">{{ benchmarkReady ? '已就绪' : '未就绪' }}</div>
          </div>
          <p class="hint">与风险详情页统一：自动请求 <code>/api/risk/detail</code>，图谱节点来自 detail 的 topic/benchmark/suggestions。</p>
        </el-card>

        <el-card class="summary-card" shadow="never">
          <template #header>
            <div class="card-title">图谱摘要</div>
          </template>
          <div v-if="detail" class="summary">
            <div class="summary-item">Benchmark 对齐度：{{ toPercent(detail.distributions.alignment) }}</div>
            <div class="summary-item">Top2 主题：{{ detail.derived.s2_cross.top2.join(' / ') || '-' }}</div>
            <div class="summary-item">语义摘要条数：{{ detail.llm?.semantic_rows ?? 0 }}</div>
            <div class="summary-item">覆盖缺口主题：{{ detail.suggestions.s4?.recommended_topics.length ?? 0 }}</div>
            <div v-if="selectedNode" class="selected">当前选中：{{ selectedNode }}</div>
          </div>
          <div v-else class="empty">导入数据后自动生成图谱</div>
        </el-card>
      </div>

      <div ref="graphEl" class="graph" />
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
  margin-bottom: 14px;
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

.inputs {
  display: grid;
  grid-template-columns: 1fr 0.9fr;
  gap: 16px;
  margin-bottom: 16px;
}

.input-card,
.summary-card {
  border-radius: 12px;
}

.card-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.row {
  display: grid;
  grid-template-columns: 160px 1fr 90px;
  align-items: center;
  gap: 10px;
  margin: 10px 0;
}

.label {
  font-size: 0.92rem;
  color: #334155;
  font-weight: 600;
}

.meta {
  font-size: 0.85rem;
  color: #64748b;
}

.hint {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.5;
}

.summary {
  padding-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-item {
  color: #334155;
  font-size: 0.9rem;
}

.selected {
  margin-top: 4px;
  color: #1d4ed8;
  font-weight: 700;
  font-size: 0.88rem;
}

.empty {
  color: #64748b;
  padding: 18px 0 0;
  font-size: 0.95rem;
}

.graph {
  height: 620px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}
</style>
