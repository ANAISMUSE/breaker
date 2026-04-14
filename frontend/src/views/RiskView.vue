<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

interface RiskResult {
  s1_content_diversity: number
  s2_cross_domain: number
  s3_stance_diversity: number
  s4_cognitive_coverage: number
  cocoon_index: number
  mode: string
  llm_enhanced?: boolean
  semantic_rows?: number
  embedding_rows?: number
}

interface RiskDetailResponse {
  llm?: {
    llm_enhanced?: boolean
    embedding_rows?: number
    semantic_rows?: number
    evidence?: Array<{ content_id: string; topic: string; summary: string }>
  }
}

type RowsRow = {
  user_id?: string
  topic: string
  stance?: string
  emotion_score?: number
  like?: number
  comment?: number
  share?: number
  duration?: number
  embedding?: unknown
}

const loading = ref(false)
const errorMsg = ref('')
const result = ref<RiskResult | null>(null)
const llmEvidence = ref<Array<{ content_id: string; topic: string; summary: string }>>([])
const hard = ref<ReturnType<typeof buildHardDerived> | null>(null)
const actionPlan = ref<{
  s2: null | {
    severity: '高' | '中' | '低'
    targetS2: number
    alphaNow: number
    alphaTarget: number
    deltaAlpha: number
    top2Topics: string[]
    recommendedTopics: Array<{ topic: string; benchmark: number; actual: number; deficit: number }>
    expectedCDelta: number
    bullets: string[]
  }
  s4: null | {
    severity: '高' | '中' | '低'
    targetS4: number
    overlapNow: number
    overlapTarget: number
    deficitNow: number
    recommendedTopics: Array<{ topic: string; benchmark: number; actual: number; deficit: number }>
    expectedCDelta: number
    bullets: string[]
  }
} | null>(null)

const rows = ref<RowsRow[]>(demoRows as RowsRow[])
const benchmark = ref<Record<string, number>>(demoBenchmark)
const rowsReady = ref(true)
const benchmarkReady = ref(true)

const radarEl = ref<HTMLDivElement | null>(null)
const topicEl = ref<HTMLDivElement | null>(null)
const stanceEl = ref<HTMLDivElement | null>(null)
const alignEl = ref<HTMLDivElement | null>(null)

let radarChart: echarts.ECharts | null = null
let topicChart: echarts.ECharts | null = null
let stanceChart: echarts.ECharts | null = null
let alignChart: echarts.ECharts | null = null

function safeNum(v: unknown, fallback = 0): number {
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : fallback
}

function behaviorWeightRow(row: RowsRow): number {
  // 与后端 src/evaluation/metrics_v2.py::behavior_weight_row 保持一致
  const like = safeNum(row.like, 0)
  const comment = safeNum(row.comment, 0)
  const share = safeNum(row.share, 0)
  const duration = safeNum(row.duration, 0)

  let w =
    1.0 +
    Math.min(like, 50) * 0.08 +
    Math.min(comment, 30) * 0.25 +
    Math.min(share, 20) * 0.15
  w += Math.min(duration / 60.0, 5.0) * 0.05
  return Math.max(w, 0.1)
}

function weightedDist(items: RowsRow[], key: 'topic' | 'stance'): Record<string, number> {
  const dist: Record<string, number> = {}
  let totalW = 0
  for (const it of items) {
    const k = String((it as any)[key] ?? '')
    if (k === 'undefined' || k === 'null') continue
    if (!k) continue
    const w = behaviorWeightRow(it)
    dist[k] = (dist[k] ?? 0) + w
    totalW += w
  }
  if (totalW <= 0) return {}
  for (const k of Object.keys(dist)) dist[k] = dist[k] / totalW
  return dist
}

function normalizeObjDist(dist: Record<string, number>): Record<string, number> {
  const out: Record<string, number> = {}
  const keys = Object.keys(dist)
  let total = 0
  for (const k of keys) total += Math.max(0, safeNum(dist[k], 0))
  if (total <= 0) return {}
  for (const k of keys) out[k] = Math.max(0, safeNum(dist[k], 0)) / total
  return out
}

function l1AlignmentScore(a: Record<string, number>, b: Record<string, number>): number {
  // L1 距离归一化到 [0,1]：相同=1，不相交=0（对概率分布）
  const keys = new Set([...Object.keys(a), ...Object.keys(b)])
  let l1 = 0
  for (const k of keys) l1 += Math.abs((a[k] ?? 0) - (b[k] ?? 0))
  const score = 1 - l1 / 2
  return Math.max(0, Math.min(1, score))
}

function buildDerived() {
  const topicDist = weightedDist(rows.value, 'topic')
  const stanceDistRaw = weightedDist(rows.value, 'stance')
  const stanceDist: Record<string, number> = {}
  for (const [k, v] of Object.entries(stanceDistRaw)) stanceDist[k || 'unknown'] = v
  const benchmarkDist = normalizeObjDist(benchmark.value)
  const alignment = l1AlignmentScore(topicDist, benchmarkDist)
  return { topicDist, stanceDist, benchmarkDist, alignment }
}

function buildHardDerived() {
  const { topicDist, stanceDist, benchmarkDist, alignment } = buildDerived()

  // S1: topic 熵 H 与 H_max
  const topicKeys = Object.keys(topicDist)
  const k = topicKeys.length
  let h = 0
  for (const p of Object.values(topicDist)) h += -(p * Math.log(p + 1e-12) / Math.log(2))
  const hMax = k > 1 ? Math.log(k) / Math.log(2) : 1.0
  const ratio = k > 0 ? h / (hMax + 1e-12) : 0
  const s1Derived = 1.0 + 9.0 * Math.min(Math.max(ratio, 0), 1)

  // S2: cross-alpha = 1 - top2 概率和
  const sortedTopics = Object.entries(topicDist).sort((a, b) => b[1] - a[1])
  const top2Set = new Set(sortedTopics.slice(0, Math.min(2, sortedTopics.length)).map(([t]) => t))
  let top2Prob = 0
  for (const [t, p] of Object.entries(topicDist)) {
    if (top2Set.has(t)) top2Prob += p
  }
  const alpha = Math.min(Math.max(1.0 - top2Prob, 0), 1)
  const s2Derived = 1.0 + 9.0 * alpha

  // S3: Gini 型极化集中度
  const stanceKeys = Object.keys(stanceDist)
  const s = stanceKeys.length
  let gini = 1.0
  if (s > 1) {
    let sumSq = 0
    for (const p of Object.values(stanceDist)) sumSq += p * p
    const hMin = 1.0 / s
    gini = (sumSq - hMin) / (1.0 - hMin + 1e-12)
    gini = Math.min(Math.max(gini, 0), 1)
  }
  const s3Derived = 1.0 + 9.0 * (1.0 - gini)

  // S4: overlap 与 r_topic = min(1, 2*overlap/(sum(b_norm)+eps))
  const keys = new Set([...Object.keys(benchmarkDist), ...Object.keys(topicDist)])
  let overlap = 0
  for (const key of keys) overlap += Math.min(topicDist[key] ?? 0, benchmarkDist[key] ?? 0)
  const sumB = Object.values(benchmarkDist).reduce((acc, v) => acc + (v ?? 0), 0)
  const rTopic = Math.min(1.0, (2.0 * overlap) / (sumB + 1e-12))
  const s4Derived = 1.0 + 9.0 * rTopic

  return {
    topicDist,
    stanceDist,
    benchmarkDist,
    alignment,
    s1Entropy: { h, hMax, ratio, k },
    s2Cross: { top2Prob, alpha, top2: sortedTopics.slice(0, 2).map(([t]) => t) },
    s3Gini: { s, gini },
    s4Overlap: { overlap, rTopic },
    derivedScores: { s1Derived, s2Derived, s3Derived, s4Derived },
  }
}

function severityLabel(score: number): '高' | '中' | '低' {
  if (score < 4) return '高'
  if (score < 7) return '中'
  return '低'
}

function buildActionPlanFromHard(ev: RiskResult, hardDerived: ReturnType<typeof buildHardDerived>) {
  const { topicDist, benchmarkDist } = hardDerived

  const topicEntries = Object.entries(topicDist).sort((a, b) => b[1] - a[1])
  const top2Topics = topicEntries.slice(0, 2).map(([t]) => t)

  // ---- S2（跨域）建议 ----
  const s2Now = ev.s2_cross_domain
  const s2Sev = severityLabel(s2Now)
  const targetS2 = s2Sev === '高' ? 8 : s2Sev === '中' ? 7 : s2Now

  const alphaNow = hardDerived.s2Cross.alpha // alpha = 1 - top2Prob
  const alphaTarget = (targetS2 - 1) / 9
  const deltaAlpha = Math.max(0, alphaTarget - alphaNow)

  const nonTop2Set = new Set(top2Topics)
  const recommendedTopicsForS2 = Object.keys(benchmarkDist)
    .filter((t) => !nonTop2Set.has(t))
    .map((t) => {
      const b = benchmarkDist[t] ?? 0
      const u = topicDist[t] ?? 0
      const deficit = Math.max(0, b - u)
      return { topic: t, benchmark: b, actual: u, deficit }
    })
    .filter((x) => x.deficit > 0)
    .sort((a, b) => b.deficit - a.deficit)
    .slice(0, 5)

  const expectedCDeltaS2 = 0.2 * Math.max(0, targetS2 - s2Now)
  const s2Section =
    s2Sev === '低'
      ? null
      : {
          severity: s2Sev,
          targetS2,
          alphaNow,
          alphaTarget,
          deltaAlpha,
          top2Topics,
          recommendedTopics: recommendedTopicsForS2,
          expectedCDelta: Number(expectedCDeltaS2.toFixed(2)),
          bullets: [
            `量化口径：C = 10 - (0.2*S1 + 0.2*S2 + 0.35*S3 + 0.25*S4)，提升 S2 会使 C 理论下降约 ${Number(expectedCDeltaS2.toFixed(2))}（权重 0.2）。`,
            `跨域目标：让“非 Top2 主题”占比从 ${(alphaNow * 100).toFixed(1)}% 提升到 ${(alphaTarget * 100).toFixed(1)}%（至少增加 ${(deltaAlpha * 100).toFixed(1)}%）。`,
            `优先扩展主题（基于 benchmark 缺口，最多 5 个）：${
              recommendedTopicsForS2.length
                ? recommendedTopicsForS2
                    .map((t) => {
                      const bPct = (t.benchmark * 100).toFixed(1)
                      const uPct = (t.actual * 100).toFixed(1)
                      return t.topic + `（目标 ${bPct}%，当前 ${uPct}%）`
                    })
                    .join('；')
                : '当前分布与 benchmark 基本一致，可换用其它非 Top2 主题池扩展。'
            }`,
          ],
        }

  // ---- S4（覆盖）建议 ----
  const s4Now = ev.s4_cognitive_coverage
  const s4Sev = severityLabel(s4Now)
  const targetS4 = s4Sev === '高' ? 8 : s4Sev === '中' ? 7 : s4Now

  const overlapNow = hardDerived.s4Overlap.overlap
  // rTopic = 2*overlap（无 embedding 时），S4 = 1 + 9*rTopic
  // 因为 rTopic 被 cap 到 1，所以 overlapTarget 也不会超过 0.5。
  const rTopicTarget = (targetS4 - 1) / 9
  const overlapTarget = Math.min(0.5, Math.max(0, rTopicTarget / 2))

  const deficitNow = Math.max(0, 1 - overlapNow)
  const expectedCDeltaS4 = 0.25 * Math.max(0, targetS4 - s4Now)

  const keys = Array.from(new Set([...Object.keys(benchmarkDist), ...Object.keys(topicDist)]))
  const recommendedTopicsForS4 = keys
    .map((t) => {
      const b = benchmarkDist[t] ?? 0
      const u = topicDist[t] ?? 0
      const deficit = Math.max(0, b - u)
      return { topic: t, benchmark: b, actual: u, deficit }
    })
    .filter((x) => x.deficit > 0)
    .sort((a, b) => b.deficit - a.deficit)
    .slice(0, 6)

  const s4Section =
    s4Sev === '低'
      ? null
      : {
          severity: s4Sev,
          targetS4,
          overlapNow,
          overlapTarget,
          deficitNow,
          recommendedTopics: recommendedTopicsForS4,
          expectedCDelta: Number(expectedCDeltaS4.toFixed(2)),
          bullets: [
            `量化口径：提升 S4 会使 C 理论下降约 ${Number(expectedCDeltaS4.toFixed(2))}（权重 0.25）。`,
            `覆盖目标：让 benchmark 覆盖 overlap 从 ${(overlapNow * 100).toFixed(1)}% 提升到 ${(overlapTarget * 100).toFixed(1)}%（当前缺口 deficit≈${(deficitNow * 100).toFixed(1)}%）。`,
            `优先补齐主题（基于 benchmark 缺口，最多 6 个）：${
              recommendedTopicsForS4.length
                ? recommendedTopicsForS4
                    .map((t) => {
                      const bPct = (t.benchmark * 100).toFixed(1)
                      const uPct = (t.actual * 100).toFixed(1)
                      return t.topic + `（目标 ${bPct}%，当前 ${uPct}%）`
                    })
                    .join('；')
                : '已经高度对齐，S4 的提升空间很小。'
            }`,
          ],
        }

  return { s2: s2Section, s4: s4Section }
}

function getOrInit(chart: echarts.ECharts | null, el: HTMLDivElement | null) {
  if (!el) return null
  if (chart) return chart
  return echarts.init(el)
}

function drawRadar(ev: RiskResult) {
  radarChart = getOrInit(radarChart, radarEl.value)
  if (!radarChart) return

  const categories = [
    'S1 内容多样性',
    'S2 跨领域暴露',
    'S3 立场分布多样性',
    'S4 认知盲区覆盖',
  ]
  const data = [ev.s1_content_diversity, ev.s2_cross_domain, ev.s3_stance_diversity, ev.s4_cognitive_coverage]

  radarChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: categories.map((name) => ({ name, max: 10 })),
      radius: '70%',
      splitNumber: 5,
      shape: 'polygon',
      axisName: { color: '#334155', fontSize: 12 },
      splitLine: { lineStyle: { color: '#e5e7eb' } },
      splitArea: { areaStyle: { color: ['rgba(59,130,246,0.04)', 'rgba(139,92,246,0.04)'] } },
    },
    series: [
      {
        name: '维度得分',
        type: 'radar',
        data: [{ value: data, name: '当前评估' }],
        itemStyle: { color: '#8b5cf6' },
        lineStyle: { color: '#3b82f6', width: 2 },
        areaStyle: { color: 'rgba(139,92,246,0.15)' },
      },
    ],
  })
}

function toPieSeries(dist: Record<string, number>) {
  const entries = Object.entries(dist)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
  return entries.map(([name, value]) => ({ name, value }))
}

function drawPie(chart: echarts.ECharts | null, el: HTMLDivElement | null, dist: Record<string, number>, title: string) {
  if (!el) return
  const c = chart ?? echarts.init(el)
  const seriesData = toPieSeries(dist)
  c.setOption({
    title: { text: title, left: 'center', top: 6, textStyle: { fontSize: 14, color: '#0f172a' } },
    tooltip: { trigger: 'item' },
    legend: { bottom: 4, left: 'center', type: 'scroll' },
    series: [
      {
        name: title,
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: true,
        label: { formatter: '{b}: {d}%' },
        labelLine: { length: 10, length2: 10 },
        data: seriesData,
      },
    ],
  })
  return c
}

function drawAlignment(derived: ReturnType<typeof buildDerived>) {
  alignChart = getOrInit(alignChart, alignEl.value)
  if (!alignChart) return

  const keys = Array.from(new Set([...Object.keys(derived.topicDist), ...Object.keys(derived.benchmarkDist)])).sort()
  const p = keys.map((k) => derived.topicDist[k] ?? 0)
  const q = keys.map((k) => derived.benchmarkDist[k] ?? 0)

  alignChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['实际分布', '参考分布'], bottom: 4 },
    grid: { left: 36, right: 16, top: 40, bottom: 46, containLabel: true },
    xAxis: {
      type: 'category',
      data: keys,
      axisLabel: { rotate: 30 },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: { formatter: '{value}' },
    },
    title: {
      text: `Benchmark 对齐度：${(derived.alignment * 100).toFixed(1)}%（越高越接近）`,
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, color: '#0f172a' },
    },
    series: [
      { name: '实际分布', type: 'bar', data: p, barGap: '20%', itemStyle: { color: '#3b82f6' } },
      { name: '参考分布', type: 'bar', data: q, itemStyle: { color: '#8b5cf6' } },
    ],
  })
}

function cleanupCharts() {
  radarChart?.dispose()
  topicChart?.dispose()
  stanceChart?.dispose()
  alignChart?.dispose()
  radarChart = null
  topicChart = null
  stanceChart = null
  alignChart = null
}

async function evaluateAuto() {
  if (loading.value) return
  if (!rowsReady.value || !benchmarkReady.value) return

  loading.value = true
  errorMsg.value = ''
  try {
    const payload = { rows: rows.value, benchmark: benchmark.value }
    const { data } = await http.post<RiskResult>('/api/risk/overview', payload)
    result.value = data
    const detail = await http.post<RiskDetailResponse>('/api/risk/detail', payload)
    llmEvidence.value = detail.data?.llm?.evidence ?? []

    const derived = buildDerived()
    hard.value = buildHardDerived()
    if (hard.value) {
      actionPlan.value = buildActionPlanFromHard(data, hard.value)
    } else {
      actionPlan.value = null
    }
    await nextTick()
    drawRadar(data)

    topicChart = drawPie(topicChart, topicEl.value, derived.topicDist, 'Topic 分布（加权）') ?? topicChart
    stanceChart = drawPie(stanceChart, stanceEl.value, derived.stanceDist, '立场分布（加权）') ?? stanceChart
    drawAlignment(derived)
  } catch (e) {
    result.value = null
    llmEvidence.value = []
    hard.value = null
    actionPlan.value = null
    errorMsg.value = e instanceof Error ? e.message : '计算风险概览失败'
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
  await evaluateAuto()
}

async function onImportedRows(records: Record<string, unknown>[]) {
  errorMsg.value = ''
  rows.value = records as RowsRow[]
  rowsReady.value = true
  await evaluateAuto()
}

function onImportError(message: string) {
  rowsReady.value = false
  errorMsg.value = message
}

async function onPickRows(file: File | null) {
  errorMsg.value = ''
  if (!file) return
  try {
    const parsed = await loadJsonFile<unknown>(file)
    if (!Array.isArray(parsed)) throw new Error('rows 文件必须是 JSON 数组')
    rows.value = parsed as RowsRow[]
    rowsReady.value = true
    await evaluateAuto()
  } catch (e) {
    rowsReady.value = false
    errorMsg.value = e instanceof Error ? e.message : 'rows 文件解析失败'
  }
}

async function onPickBenchmark(file: File | null) {
  errorMsg.value = ''
  if (!file) return
  try {
    const parsed = await loadJsonFile<unknown>(file)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('benchmark 文件必须是 JSON 对象')
    benchmark.value = parsed as Record<string, number>
    benchmarkReady.value = true
    await evaluateAuto()
  } catch (e) {
    benchmarkReady.value = false
    errorMsg.value = e instanceof Error ? e.message : 'benchmark 文件解析失败'
  }
}

let resizeHandler: (() => void) | null = null
onMounted(() => {
  // demo 默认就绪 -> 自动出图
  evaluateAuto()
  resizeHandler = () => {
    radarChart?.resize()
    topicChart?.resize()
    stanceChart?.resize()
    alignChart?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  cleanupCharts()
})
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">现状评估 · Risk（可视化）</h1>
        <div class="head-right">
          <el-button :disabled="loading" @click="onPickDemo">使用演示数据</el-button>
        </div>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="inputs">
        <el-card class="input-card" shadow="never">
          <template #header>
            <div class="card-title">数据导入</div>
          </template>
          <div class="row">
            <div class="label">rows（统一导入 CSV / JSON / 抖音导出）</div>
            <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept="application/json"
              :on-change="(file: any) => onPickRows((file?.raw as File) ?? null)"
            >
              <el-button plain>仅本地解析 .json</el-button>
            </el-upload>
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
          <p class="hint">
            统一导入走 <code>/api/ingestion/import</code>（自动识别抖音导出或标准表头）；完成后将自动调用
            <code>/api/risk/overview</code>。标准行至少需能归一化出 <code>topic</code> 与 <code>stance</code>。
          </p>
        </el-card>

        <el-card class="summary-card" shadow="never">
          <template #header>
            <div class="card-title">茧房指数概览</div>
          </template>
          <div v-if="result" class="summary">
            <div class="big">
              <div class="big-value">{{ result.cocoon_index.toFixed(2) }}</div>
              <div class="big-unit">/ 10</div>
            </div>
            <div class="summary-text">
              茧房指数越高，表示风险/封闭性越严重（建议优先关注 S4 与 S2）。
            </div>
            <div class="llm-box">
              <div class="llm-title">LLM增强状态</div>
              <div class="llm-meta">
                <span>向量增强：{{ result.llm_enhanced ? '已启用' : '未启用' }}</span>
                <span>语义条数：{{ result.semantic_rows ?? 0 }}</span>
                <span>向量条数：{{ result.embedding_rows ?? 0 }}</span>
              </div>
              <ul v-if="llmEvidence.length" class="llm-evidence">
                <li v-for="item in llmEvidence" :key="`${item.content_id}-${item.topic}`">
                  [{{ item.topic }}] {{ item.summary }}
                </li>
              </ul>
            </div>
        <div class="c-focus">
          <div class="c-title">C 贡献拆解（更难维度）</div>
          <div class="c-eq">
            C = 10 - (0.2*S1 + 0.2*S2 + 0.35*S3 + 0.25*S4)
          </div>
          <div class="c-grid">
            <div class="c-cell">
              <div class="c-k">0.2*S1</div>
              <div class="c-v">{{ (0.2 * result.s1_content_diversity).toFixed(2) }}</div>
            </div>
            <div class="c-cell">
              <div class="c-k">0.2*S2</div>
              <div class="c-v">{{ (0.2 * result.s2_cross_domain).toFixed(2) }}</div>
            </div>
            <div class="c-cell">
              <div class="c-k">0.35*S3</div>
              <div class="c-v">{{ (0.35 * result.s3_stance_diversity).toFixed(2) }}</div>
            </div>
            <div class="c-cell">
              <div class="c-k">0.25*S4</div>
              <div class="c-v">{{ (0.25 * result.s4_cognitive_coverage).toFixed(2) }}</div>
            </div>
          </div>
          <div class="c-sub">
            敏感性：把某一维度提升 +1，将使 C 下降对应权重（例如提升 S3 +1 => C 降 0.35）
          </div>
        </div>

            <div class="bars">
              <div class="bar-row">
                <span class="bar-label">S1</span>
                <el-progress :percentage="(result.s1_content_diversity / 10) * 100" :stroke-width="10" />
              </div>
              <div class="bar-row">
                <span class="bar-label">S2</span>
                <el-progress :percentage="(result.s2_cross_domain / 10) * 100" :stroke-width="10" />
              </div>
              <div class="bar-row">
                <span class="bar-label">S3</span>
                <el-progress :percentage="(result.s3_stance_diversity / 10) * 100" :stroke-width="10" />
              </div>
              <div class="bar-row">
                <span class="bar-label">S4</span>
                <el-progress :percentage="(result.s4_cognitive_coverage / 10) * 100" :stroke-width="10" />
              </div>
            </div>

        <div v-if="hard" class="hard-breakdown">
          <div class="c-title2">S1~S4 内部判别量（用于解释“为什么是这个 C”）</div>
          <div class="hard-grid">
            <div class="hard-item">
              <div class="hard-h">S1 熵（Topic 多样性）</div>
              <div class="hard-b">
                H={{ hard.s1Entropy.h.toFixed(3) }}, Hmax={{ hard.s1Entropy.hMax.toFixed(3) }},
                ratio={{ (hard.s1Entropy.ratio * 100).toFixed(1) }}%, k={{ hard.s1Entropy.k }}
              </div>
              <div class="hard-b">S1 ≈ {{ hard.derivedScores.s1Derived.toFixed(2) }}（后端返回 {{ result.s1_content_diversity.toFixed(2) }}）</div>
            </div>
            <div class="hard-item">
              <div class="hard-h">S2 跨域 α（Exposure）</div>
              <div class="hard-b">
                top2 概率和={{ hard.s2Cross.top2Prob.toFixed(3) }}, α={{ hard.s2Cross.alpha.toFixed(3) }}
              </div>
              <div class="hard-b">S2 ≈ {{ hard.derivedScores.s2Derived.toFixed(2) }}（后端返回 {{ result.s2_cross_domain.toFixed(2) }}）</div>
            </div>
            <div class="hard-item">
              <div class="hard-h">S3 Gini（立场极化）</div>
              <div class="hard-b">
                stances={{ hard.s3Gini.s }}, gini={{ hard.s3Gini.gini.toFixed(3) }}
              </div>
              <div class="hard-b">S3 ≈ {{ hard.derivedScores.s3Derived.toFixed(2) }}（后端返回 {{ result.s3_stance_diversity.toFixed(2) }}）</div>
            </div>
            <div class="hard-item">
              <div class="hard-h">S4 覆盖（Benchmark 对齐）</div>
              <div class="hard-b">
                overlap={{ hard.s4Overlap.overlap.toFixed(3) }}, rTopic={{ hard.s4Overlap.rTopic.toFixed(3) }}
              </div>
              <div class="hard-b">S4 ≈ {{ hard.derivedScores.s4Derived.toFixed(2) }}（后端返回 {{ result.s4_cognitive_coverage.toFixed(2) }}）</div>
            </div>
          </div>
        </div>
          </div>

        <div v-if="actionPlan" class="action-breakdown">
          <div class="c-title2">推荐破茧动作映射（重点 S2/S4）</div>
          <div class="action-sections">
            <div v-if="actionPlan.s2" class="action-section">
              <div class="action-head">S2 跨域暴露（当前 {{ result?.s2_cross_domain.toFixed(2) }}，建议提升到 {{ actionPlan.s2.targetS2 }}）</div>
              <div class="action-sub">
                目标 alpha：{{ actionPlan.s2.alphaNow.toFixed(3) }} -> {{ actionPlan.s2.alphaTarget.toFixed(3) }}（至少增加 {{ (actionPlan.s2.deltaAlpha * 100).toFixed(1) }}% 的非 Top2 占比）
              </div>
              <div class="action-sub">理论 C 下降：{{ actionPlan.s2.expectedCDelta }}（权重 0.2）</div>
              <ul class="bullet">
                <li v-for="(b, idx) in actionPlan.s2.bullets" :key="idx">
                  {{ b }}
                </li>
              </ul>
            </div>

            <div v-if="actionPlan.s4" class="action-section">
              <div class="action-head">S4 覆盖（当前 {{ result?.s4_cognitive_coverage.toFixed(2) }}，建议提升到 {{ actionPlan.s4.targetS4 }}）</div>
              <div class="action-sub">
                覆盖 overlap：{{ (actionPlan.s4.overlapNow * 100).toFixed(1) }}% -> {{ (actionPlan.s4.overlapTarget * 100).toFixed(1) }}%（缺口 {{ (actionPlan.s4.deficitNow * 100).toFixed(1) }}%）
              </div>
              <div class="action-sub">理论 C 下降：{{ actionPlan.s4.expectedCDelta }}（权重 0.25）</div>
              <ul class="bullet">
                <li v-for="(b, idx) in actionPlan.s4.bullets" :key="idx">
                  {{ b }}
                </li>
              </ul>
            </div>
          </div>
          <div v-if="!actionPlan.s2 && !actionPlan.s4" class="action-empty">
            当前 S2/S4 已较高，可把破茧重点放到 S1/S3（内容多样性与立场分布）或直接进行动态模拟验证。
          </div>
        </div>
          <div v-else class="empty">导入数据后自动显示评估结果</div>
        </el-card>
      </div>

      <div class="charts-grid">
        <div class="chart-card">
          <div ref="radarEl" class="chart" />
        </div>
        <div class="chart-card">
          <div ref="topicEl" class="chart" />
        </div>
        <div class="chart-card">
          <div ref="stanceEl" class="chart" />
        </div>
        <div class="chart-card">
          <div ref="alignEl" class="chart" />
        </div>
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.title {
  margin: 0;
  font-size: 1.35rem;
  color: #0f172a;
}

.llm-box {
  margin: 12px 0;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
}

.llm-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.llm-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #334155;
}

.llm-evidence {
  margin: 8px 0 0;
  padding-left: 16px;
  color: #334155;
  font-size: 13px;
}

.error {
  margin: 0 0 12px;
  color: #dc2626;
  font-size: 0.9rem;
}

.head-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.inputs {
  display: grid;
  grid-template-columns: 1fr 0.9fr;
  gap: 16px;
  margin-bottom: 16px;
}

.input-card {
  border-radius: 12px;
  padding: 0;
}

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
  padding: 8px 0 0;
}

.big {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.big-value {
  font-size: 2.2rem;
  font-weight: 800;
  color: #8b5cf6;
}

.big-unit {
  font-size: 0.95rem;
  color: #64748b;
  font-weight: 600;
}

.summary-text {
  margin-top: 6px;
  color: #334155;
  font-size: 0.92rem;
  line-height: 1.5;
}

.bars {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bar-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  align-items: center;
  gap: 10px;
}

.bar-label {
  font-size: 0.86rem;
  font-weight: 700;
  color: #334155;
}

.empty {
  color: #64748b;
  padding: 24px 0 0;
  font-size: 0.95rem;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.chart {
  width: 100%;
  height: 320px;
}

.c-focus {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 12px 10px;
  background: linear-gradient(180deg, rgba(139, 92, 246, 0.06) 0%, rgba(59, 130, 246, 0.03) 100%);
}

.c-title {
  font-size: 0.98rem;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 6px;
}

.c-eq {
  font-size: 0.86rem;
  color: #334155;
  font-weight: 700;
}

.c-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.c-cell {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
}

.c-k {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 700;
}

.c-v {
  margin-top: 6px;
  font-size: 1.1rem;
  color: #0f172a;
  font-weight: 900;
}

.c-sub {
  margin-top: 10px;
  font-size: 0.82rem;
  color: #475569;
  line-height: 1.4;
}

.c-title2 {
  font-size: 0.98rem;
  font-weight: 800;
  color: #0f172a;
  margin: 16px 0 10px;
}

.hard-breakdown {
  margin-top: 8px;
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
}

.hard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.hard-item {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  background: #fff;
}

.hard-h {
  font-size: 0.88rem;
  font-weight: 900;
  color: #0f172a;
  margin-bottom: 8px;
}

.hard-b {
  font-size: 0.82rem;
  color: #334155;
  line-height: 1.5;
  margin-top: 4px;
}

.action-breakdown {
  margin-top: 10px;
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
}

.action-sections {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.action-section {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  background: #fff;
}

.action-head {
  font-size: 0.92rem;
  font-weight: 900;
  color: #0f172a;
  margin-bottom: 6px;
}

.action-sub {
  font-size: 0.82rem;
  color: #334155;
  line-height: 1.5;
  margin-top: 6px;
  font-weight: 700;
}

.bullet {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.6;
}

.action-empty {
  margin-top: 10px;
  color: #64748b;
  font-size: 0.9rem;
}
</style>

