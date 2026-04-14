<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { compareReplayPresets } from '@/constants/compareReplayPresets'
import { demoBenchmark, demoRows } from '@/constants/demoData'

const STRAT_ORDER = ['baseline', 'aggressive', 'ladder', 'mixed'] as const
const REPLAY_KEY = 'compare.replay.payload'

const STRAT_ZH: Record<string, string> = {
  baseline: '基线（偏沉浸）',
  aggressive: '激进跨域',
  ladder: '阶梯破茧',
  mixed: '混合探索',
}

function stratLabel(key: string) {
  return STRAT_ZH[key] ?? key
}

interface StrategyBlock {
  cocoon_start: number
  cocoon_end: number
  drop: number
  series: number[]
}

interface BestBlock {
  name: string
  drop: number
  static_cocoon: number
  reason?: string
}

interface CompareResponse {
  result: Record<string, StrategyBlock | BestBlock>
  trend_option: Record<string, unknown>
}

function isStrategyBlock(v: unknown): v is StrategyBlock {
  if (!v || typeof v !== 'object' || !('series' in v)) return false
  const s = (v as { series: unknown }).series
  return Array.isArray(s) && 'cocoon_end' in v
}

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const benchmarkText = ref(JSON.stringify(demoBenchmark, null, 2))
const rounds = ref(10)
const resultText = ref('')
const loading = ref(false)
const errorMsg = ref('')
const comparePayload = ref<CompareResponse | null>(null)
const bestInfo = ref<{ name: string; drop: number; staticCocoon: number; reason: string } | null>(null)

const trendEl = ref<HTMLDivElement | null>(null)
const barEl = ref<HTMLDivElement | null>(null)
const dropEl = ref<HTMLDivElement | null>(null)

let trendChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null
let dropChart: echarts.ECharts | null = null

interface ReplayPayload {
  rows: Array<Record<string, unknown>>
  benchmark: Record<string, number>
  rounds: number
}

function getOrInit(chart: echarts.ECharts | null, el: HTMLDivElement | null) {
  if (!el) return null
  if (chart) return chart
  return echarts.init(el)
}

function localizeTrendOption(opt: Record<string, unknown>): Record<string, unknown> {
  const zh = (n: string) => stratLabel(n)
  const legend = opt.legend as { data?: string[] } | undefined
  const names = legend?.data
  const newLegend = names ? { ...legend, data: names.map((n) => zh(n)) } : legend
  const rawSeries = opt.series as Array<{ name?: string; type?: string; data?: unknown }> | undefined
  const series = rawSeries?.map((s) => ({ ...s, name: s.name != null ? zh(String(s.name)) : s.name }))
  return { ...opt, legend: newLegend, series }
}

function drawTrend(opt: Record<string, unknown>) {
  trendChart = getOrInit(trendChart, trendEl.value)
  if (!trendChart || !opt.series) return
  const localized = localizeTrendOption(opt)
  trendChart.setOption(
    {
      ...localized,
      color: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'],
      title: {
        text: '茧房指数随模拟轮次变化',
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, color: '#0f172a', fontWeight: 600 },
      },
      tooltip: { trigger: 'axis' },
      grid: { left: 52, right: 20, top: 48, bottom: 56, containLabel: true },
      legend: {
        ...(localized.legend as object),
        bottom: 8,
        type: 'scroll',
      },
      xAxis: {
        ...(typeof localized.xAxis === 'object' && localized.xAxis ? localized.xAxis : {}),
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b' },
      },
      yAxis: {
        ...(typeof localized.yAxis === 'object' && localized.yAxis ? localized.yAxis : {}),
        min: 0,
        max: 10,
        name: '茧房指数（越高风险越大）',
        nameTextStyle: { color: '#64748b', fontSize: 12 },
        splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
        axisLabel: { color: '#64748b' },
      },
      series: ((localized.series as object[]) ?? []).map((s) => ({
        ...s,
        smooth: true,
        symbolSize: 6,
        lineStyle: { width: 2 },
        emphasis: { focus: 'series' },
      })),
    },
    { notMerge: true },
  )
}

function drawEndBar(result: CompareResponse['result']) {
  barChart = getOrInit(barChart, barEl.value)
  if (!barChart) return
  const keys: string[] = []
  for (const k of STRAT_ORDER) {
    const b = result[k]
    if (b && isStrategyBlock(b)) keys.push(k)
  }
  if (!keys.length) return
  const labels = keys.map(stratLabel)
  const start = keys.map((k) => (result[k] as StrategyBlock).cocoon_start)
  const end = keys.map((k) => (result[k] as StrategyBlock).cocoon_end)
  barChart.setOption(
    {
      title: {
        text: '静态基线 vs 模拟末轮',
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, color: '#0f172a', fontWeight: 600 },
      },
      tooltip: { trigger: 'axis' },
      legend: { data: ['模拟前（静态）', '模拟后（末轮）'], bottom: 8 },
      grid: { left: 48, right: 16, top: 44, bottom: 48, containLabel: true },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: '#64748b', interval: 0, rotate: keys.length > 3 ? 18 : 0 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 10,
        name: '茧房指数',
        splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
        axisLabel: { color: '#64748b' },
      },
      series: [
        { name: '模拟前（静态）', type: 'bar', data: start, itemStyle: { color: '#94a3b8' }, barMaxWidth: 28 },
        { name: '模拟后（末轮）', type: 'bar', data: end, itemStyle: { color: '#3b82f6' }, barMaxWidth: 28 },
      ],
    },
    { notMerge: true },
  )
}

function drawDropRank(result: CompareResponse['result']) {
  dropChart = getOrInit(dropChart, dropEl.value)
  if (!dropChart) return
  const items: { label: string; drop: number }[] = []
  for (const k of STRAT_ORDER) {
    const b = result[k]
    if (b && isStrategyBlock(b)) items.push({ label: stratLabel(k), drop: b.drop })
  }
  items.sort((a, b) => b.drop - a.drop)
  if (!items.length) return
  dropChart.setOption(
    {
      title: {
        text: '相对静态基线的改善 Δ（静态指数 − 末轮指数）',
        left: 'center',
        top: 6,
        textStyle: { fontSize: 13, color: '#0f172a', fontWeight: 600 },
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 12, right: 28, top: 40, bottom: 16, containLabel: true },
      xAxis: {
        type: 'value',
        name: 'Δ',
        splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
        axisLabel: { color: '#64748b' },
      },
      yAxis: {
        type: 'category',
        data: items.map((i) => i.label),
        inverse: true,
        axisLabel: { color: '#64748b', width: 90, overflow: 'truncate' },
      },
      series: [
        {
          type: 'bar',
          data: items.map((i) => i.drop),
          barMaxWidth: 22,
          itemStyle: {
            color: (p: { dataIndex: number }) => {
              const rank = p.dataIndex
              return rank === 0 ? '#10b981' : rank === 1 ? '#3b82f6' : '#94a3b8'
            },
          },
          label: { show: true, position: 'right', formatter: (p: { value: number }) => p.value.toFixed(2) },
        },
      ],
    },
    { notMerge: true },
  )
}

function disposeCharts() {
  trendChart?.dispose()
  barChart?.dispose()
  dropChart?.dispose()
  trendChart = null
  barChart = null
  dropChart = null
}

async function refreshCharts() {
  const data = comparePayload.value
  if (!data?.result) return
  await nextTick()
  if (data.trend_option && Object.keys(data.trend_option).length) {
    drawTrend(data.trend_option as Record<string, unknown>)
  }
  drawEndBar(data.result)
  drawDropRank(data.result)
  trendChart?.resize()
  barChart?.resize()
  dropChart?.resize()
}

function onImportedRows(rows: Record<string, unknown>[]) {
  errorMsg.value = ''
  rowsText.value = JSON.stringify(rows, null, 2)
}

function onImportError(message: string) {
  errorMsg.value = message
}

function applyReplayPreset(payload: ReplayPayload) {
  rowsText.value = JSON.stringify(payload.rows ?? [], null, 2)
  benchmarkText.value = JSON.stringify(payload.benchmark ?? {}, null, 2)
  rounds.value = Math.max(1, Number(payload.rounds || 10))
}

function applyBuiltInPreset(id: string) {
  const preset = compareReplayPresets.find((x) => x.id === id)
  if (!preset) return
  errorMsg.value = ''
  applyReplayPreset({
    rows: preset.rows,
    benchmark: preset.benchmark,
    rounds: preset.rounds,
  })
}

function maybeLoadReplayPayload() {
  const raw = localStorage.getItem(REPLAY_KEY)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw) as ReplayPayload
    if (!Array.isArray(parsed.rows) || typeof parsed.benchmark !== 'object') return
    applyReplayPreset(parsed)
    ElMessage.success('已加载历史回放数据')
  } catch {
    ElMessage.warning('检测到回放数据，但解析失败')
  } finally {
    localStorage.removeItem(REPLAY_KEY)
  }
}

function toCsvText() {
  const payload = comparePayload.value
  if (!payload?.result) return ''
  const rows = ['strategy,cocoon_start,cocoon_end,drop,best_name,best_drop,static_cocoon']
  const best = payload.result._best as BestBlock | undefined
  for (const key of STRAT_ORDER) {
    const block = payload.result[key]
    if (!block || !isStrategyBlock(block)) continue
    rows.push(
      [
        key,
        block.cocoon_start.toFixed(4),
        block.cocoon_end.toFixed(4),
        block.drop.toFixed(4),
        best?.name ?? '',
        typeof best?.drop === 'number' ? best.drop.toFixed(4) : '',
        typeof best?.static_cocoon === 'number' ? best.static_cocoon.toFixed(4) : '',
      ].join(','),
    )
  }
  return rows.join('\n')
}

function downloadText(filename: string, text: string, mime = 'application/json;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function exportJson() {
  if (!resultText.value) {
    ElMessage.warning('请先运行对比，再导出 JSON')
    return
  }
  downloadText(`compare-result-${Date.now()}.json`, resultText.value)
}

function exportCsv() {
  const csv = toCsvText()
  if (!csv) {
    ElMessage.warning('请先运行对比，再导出 CSV')
    return
  }
  downloadText(`compare-result-${Date.now()}.csv`, csv, 'text/csv;charset=utf-8')
}

async function exportChartPng() {
  if (!trendChart && !barChart && !dropChart) {
    ElMessage.warning('请先运行对比，再导出图表')
    return
  }
  const charts = [trendChart, barChart, dropChart].filter(Boolean) as echarts.ECharts[]
  const images = charts.map((chart) => {
    const dom = chart.getDom()
    return {
      src: chart.getDataURL({ pixelRatio: 2, backgroundColor: '#ffffff' }),
      width: Math.max(320, dom.clientWidth * 2),
      height: Math.max(180, dom.clientHeight * 2),
    }
  })
  const width = Math.max(...images.map((x) => x.width))
  const gap = 20
  const height = images.reduce((sum, img) => sum + img.height, 0) + gap * (images.length - 1)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    ElMessage.error('导出图表失败：无法创建画布')
    return
  }
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)
  let y = 0
  for (const img of images) {
    const elem = await new Promise<HTMLImageElement>((resolve, reject) => {
      const tmp = new Image()
      tmp.onload = () => resolve(tmp)
      tmp.onerror = () => reject(new Error('load image failed'))
      tmp.src = img.src
    }).catch(() => null)
    if (!elem) {
      ElMessage.error('导出图表失败：图像加载异常')
      return
    }
    ctx.drawImage(elem, 0, y, img.width, img.height)
    y += img.height + gap
  }
  const link = document.createElement('a')
  link.href = canvas.toDataURL('image/png')
  link.download = `compare-charts-${Date.now()}.png`
  link.click()
}

async function runCompare() {
  loading.value = true
  errorMsg.value = ''
  comparePayload.value = null
  bestInfo.value = null
  try {
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const benchmark = JSON.parse(benchmarkText.value) as Record<string, number>
    const { data } = await http.post<CompareResponse>('/api/simulation/compare', {
      rows,
      benchmark,
      rounds: rounds.value,
    })
    resultText.value = JSON.stringify(data, null, 2)
    comparePayload.value = data
    const best = data.result._best as BestBlock | undefined
    if (best && typeof best.name === 'string') {
      bestInfo.value = {
        name: best.name,
        drop: best.drop,
        staticCocoon: best.static_cocoon,
        reason: String(best.reason ?? ''),
      }
    }
    await refreshCharts()
  } catch (e) {
    resultText.value = ''
    comparePayload.value = null
    bestInfo.value = null
    disposeCharts()
    errorMsg.value = e instanceof Error ? e.message : '策略对比失败'
  } finally {
    loading.value = false
  }
}

let resizeHandler: (() => void) | null = null
onMounted(() => {
  maybeLoadReplayPayload()
  resizeHandler = () => {
    trendChart?.resize()
    barChart?.resize()
    dropChart?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  disposeCharts()
})
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">平台对比（多策略模拟 · 可视化）</h1>
        <div class="head-actions">
          <span class="label">轮次</span>
          <el-input-number v-model="rounds" :min="1" :max="50" />
          <el-button style="margin-left: 6px" @click="exportJson">导出 JSON</el-button>
          <el-button @click="exportCsv">导出 CSV</el-button>
          <el-button @click="exportChartPng">导出图表</el-button>
          <el-button type="primary" :loading="loading" style="margin-left: 12px" @click="runCompare">运行对比</el-button>
        </div>
      </div>
      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="preset-bar">
        <span class="preset-title">固定回放模板</span>
        <el-tooltip v-for="preset in compareReplayPresets" :key="preset.id" :content="preset.description" placement="top">
          <el-button size="small" @click="applyBuiltInPreset(preset.id)">{{ preset.label }}</el-button>
        </el-tooltip>
      </div>

      <div v-if="bestInfo" class="best">
        <span class="best-tag">模拟推荐</span>
        <span class="best-line">
          静态茧房指数 <strong>{{ bestInfo.staticCocoon.toFixed(2) }}</strong>；
          当前样本下最优策略为 <strong>{{ stratLabel(bestInfo.name) }}</strong>，
          Δ = <strong>{{ bestInfo.drop.toFixed(3) }}</strong>（越大表示末轮相对静态改善越明显）。
        </span>
        <span v-if="bestInfo.reason" class="best-reason">{{ bestInfo.reason }}</span>
      </div>

      <div class="toolbar">
        <span class="tb-label">rows</span>
        <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
      </div>

      <div v-if="comparePayload" class="viz">
        <div ref="trendEl" class="chart trend" />
        <div ref="barEl" class="chart bar" />
        <div ref="dropEl" class="chart drop" />
      </div>
      <p v-else-if="!loading" class="viz-hint">点击「运行对比」后在此展示趋势、末轮对比与改善排名。</p>

      <div class="grid3">
        <el-input v-model="rowsText" type="textarea" :rows="8" placeholder="rows JSON" />
        <el-input v-model="benchmarkText" type="textarea" :rows="8" placeholder="benchmark JSON" />
        <details class="json-details">
          <summary>原始响应 JSON（调试用）</summary>
          <pre class="json-pre">{{ resultText || '（尚未运行）' }}</pre>
        </details>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 0;
}
.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px 28px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}
.head-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.title {
  margin: 0;
  font-size: 1.35rem;
  color: #0f172a;
}
.label {
  margin-right: 8px;
  color: #334155;
}
.error {
  color: #dc2626;
  margin: 0 0 12px;
}
.preset-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.preset-title {
  font-size: 13px;
  color: #334155;
  font-weight: 600;
  margin-right: 4px;
}
.best {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.08), rgba(59, 130, 246, 0.06));
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
  color: #334155;
  line-height: 1.5;
}
.best-line {
  display: block;
}
.best-tag {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 6px;
  background: #10b981;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.best-reason {
  color: #0f766e;
  font-size: 13px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tb-label {
  font-size: 13px;
  color: #334155;
}
.viz {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  grid-template-rows: minmax(300px, auto) minmax(220px, auto);
  gap: 16px;
  margin-bottom: 20px;
}
.viz .trend {
  grid-column: 1 / -1;
  min-height: 300px;
}
.viz .bar {
  min-height: 280px;
}
.viz .drop {
  min-height: 220px;
}
.chart {
  width: 100%;
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
}
.viz-hint {
  margin: 8px 0 20px;
  color: #64748b;
  font-size: 14px;
}
.grid3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
.json-details {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f8fafc;
}
.json-details summary {
  cursor: pointer;
  color: #475569;
  font-size: 13px;
  user-select: none;
}
.json-pre {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.4;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  color: #334155;
}
</style>
