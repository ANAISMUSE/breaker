<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
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
  overview: RiskResult
  llm?: {
    llm_enhanced?: boolean
    embedding_rows?: number
    semantic_rows?: number
    evidence?: Array<{ content_id: string; topic: string; summary: string }>
  }
  cohort?: {
    group_key: string
    delta_vs_cohort?: { s1: number; s2: number; s3: number; s4: number; c: number }
  }
  trend_30d?: {
    points: Array<{ date: string; cocoon_index: number; s1: number; s2: number; s3: number; s4: number }>
    window_days: number
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
const cohortInfo = ref<{ groupKey: string; deltaC: number } | null>(null)
const trendPoints = ref<Array<{ date: string; cocoon_index: number; s1: number; s2: number; s3: number; s4: number }>>([])

const rows = ref<RowsRow[]>(demoRows as RowsRow[])
const benchmark = ref<Record<string, number>>(demoBenchmark)
const rowsReady = ref(true)
const benchmarkReady = ref(true)

const riskLevel = computed(() => {
  const c = result.value?.cocoon_index ?? 0
  if (c >= 7) return '高风险预警'
  if (c >= 5) return '中风险关注'
  return '低风险稳定'
})

const overviewText = computed(() => {
  if (!result.value) return '导入数据后自动生成风险评估结果。'
  const c = result.value.cocoon_index
  const s2 = result.value.s2_cross_domain
  const s4 = result.value.s4_cognitive_coverage
  return `当前茧房指数 ${c.toFixed(2)} / 10，建议优先关注跨域暴露 S2(${s2.toFixed(2)}) 与认知覆盖 S4(${s4.toFixed(2)})。`
})

const analysisParagraphs = computed(() => {
  if (!result.value) return []
  const hardText = hard.value
    ? `结构解释上，S1 熵比值 ${(hard.value.s1Entropy.ratio * 100).toFixed(1)}%，S2 非Top2占比 ${(hard.value.s2Cross.alpha * 100).toFixed(1)}%，S4 覆盖 ${(hard.value.s4Overlap.overlap * 100).toFixed(1)}%。`
    : '当前样本已完成基础评分，可进一步开启结构解释查看内部判别量。'
  const cohortText = cohortInfo.value
    ? `与群体基线 ${cohortInfo.value.groupKey} 相比，C 差值为 ${cohortInfo.value.deltaC.toFixed(2)}。`
    : '暂无群体基线对照，建议在同类用户集合下对比波动。'
  const actionText =
    actionPlan.value?.s2 || actionPlan.value?.s4
      ? '动作建议上可优先补齐 benchmark 缺口主题，并提高非头部主题曝光，先压降 S2/S4 再做精细化内容配比。'
      : 'S2/S4 当前已接近健康区间，可把优化重点转向 S1/S3，提升内容与立场多样性。'
  return [overviewText.value, hardText, cohortText, actionText]
})

const radarEl = ref<HTMLDivElement | null>(null)
const topicEl = ref<HTMLDivElement | null>(null)
const stanceEl = ref<HTMLDivElement | null>(null)
const alignEl = ref<HTMLDivElement | null>(null)
const trendEl = ref<HTMLDivElement | null>(null)

let radarChart: echarts.ECharts | null = null
let topicChart: echarts.ECharts | null = null
let stanceChart: echarts.ECharts | null = null
let alignChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

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

function drawTrend(points: Array<{ date: string; cocoon_index: number }>) {
  trendChart = getOrInit(trendChart, trendEl.value)
  if (!trendChart) return
  const x = points.map((p) => p.date)
  const y = points.map((p) => p.cocoon_index)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    title: {
      text: '最近30天茧房指数趋势',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, color: '#0f172a' },
    },
    grid: { left: 40, right: 16, top: 40, bottom: 40, containLabel: true },
    xAxis: { type: 'category', data: x, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', min: 0, max: 10 },
    series: [{ type: 'line', data: y, smooth: true, areaStyle: { opacity: 0.12 } }],
  })
}

function cleanupCharts() {
  radarChart?.dispose()
  topicChart?.dispose()
  stanceChart?.dispose()
  alignChart?.dispose()
  trendChart?.dispose()
  radarChart = null
  topicChart = null
  stanceChart = null
  alignChart = null
  trendChart = null
}

async function evaluateAuto() {
  if (loading.value) return
  if (!rowsReady.value || !benchmarkReady.value) return

  loading.value = true
  errorMsg.value = ''
  try {
    const payload = { rows: rows.value, benchmark: benchmark.value }
    const { data: detail } = await http.post<RiskDetailResponse>('/api/risk/detail', payload)
    const overview = detail.overview
    result.value = {
      ...overview,
      llm_enhanced: detail.llm?.llm_enhanced,
      embedding_rows: detail.llm?.embedding_rows,
      semantic_rows: detail.llm?.semantic_rows,
    }
    llmEvidence.value = detail.llm?.evidence ?? []
    cohortInfo.value = {
      groupKey: detail.cohort?.group_key ?? 'global',
      deltaC: detail.cohort?.delta_vs_cohort?.c ?? 0,
    }
    trendPoints.value = detail.trend_30d?.points ?? []

    const derived = buildDerived()
    hard.value = buildHardDerived()
    if (hard.value) {
      actionPlan.value = buildActionPlanFromHard(overview, hard.value)
    } else {
      actionPlan.value = null
    }
    await nextTick()
    drawRadar(overview)

    topicChart = drawPie(topicChart, topicEl.value, derived.topicDist, 'Topic 分布（加权）') ?? topicChart
    stanceChart = drawPie(stanceChart, stanceEl.value, derived.stanceDist, '立场分布（加权）') ?? stanceChart
    drawAlignment(derived)
    drawTrend(trendPoints.value)
  } catch (e) {
    result.value = null
    llmEvidence.value = []
    hard.value = null
    actionPlan.value = null
    cohortInfo.value = null
    trendPoints.value = []
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
    trendChart?.resize()
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
    <div class="shell-card">
      <div class="head">
        <div>
          <h1 class="title">风险评估详情</h1>
          <p class="subtitle">按“概览-图表-分析”结构展示风险结果，减少冗余滚动与信息堆叠。</p>
        </div>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="toolbar">
        <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept="application/json"
          :on-change="(file: any) => onPickRows((file?.raw as File) ?? null)"
        >
          <el-button plain>导入 rows.json</el-button>
        </el-upload>
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept="application/json"
          :on-change="(file: any) => onPickBenchmark((file?.raw as File) ?? null)"
        >
          <el-button>导入 benchmark.json</el-button>
        </el-upload>
        <el-button :disabled="loading" @click="onPickDemo">使用演示数据</el-button>
        <div class="ready">
          <span>rows：{{ rowsReady ? '已就绪' : '未就绪' }}</span>
          <span>benchmark：{{ benchmarkReady ? '已就绪' : '未就绪' }}</span>
        </div>
      </div>

      <div v-if="result" class="overview-card">
        <div class="overview-main">
          <div>
            <div class="overview-title">风险评估总览 · {{ riskLevel }}</div>
            <p class="overview-desc">{{ overviewText }}</p>
            <p v-if="cohortInfo" class="overview-note">
              同群体基线：{{ cohortInfo.groupKey }} · C差值（本人-群体）= {{ cohortInfo.deltaC.toFixed(2) }}
            </p>
          </div>
          <div class="score-circle">
            <div class="score">{{ result.cocoon_index.toFixed(2) }}</div>
            <div class="unit">/10</div>
          </div>
        </div>
        <div class="kpi-row">
          <div class="kpi-item">
            <span>S1 内容多样性</span>
            <strong>{{ result.s1_content_diversity.toFixed(2) }}</strong>
          </div>
          <div class="kpi-item">
            <span>S2 跨域暴露</span>
            <strong>{{ result.s2_cross_domain.toFixed(2) }}</strong>
          </div>
          <div class="kpi-item">
            <span>S3 立场多样性</span>
            <strong>{{ result.s3_stance_diversity.toFixed(2) }}</strong>
          </div>
          <div class="kpi-item">
            <span>S4 认知覆盖</span>
            <strong>{{ result.s4_cognitive_coverage.toFixed(2) }}</strong>
          </div>
        </div>
      </div>

      <div class="charts-grid">
        <div class="chart-card"><div ref="radarEl" class="chart" /></div>
        <div class="chart-card"><div ref="topicEl" class="chart" /></div>
        <div class="chart-card"><div ref="stanceEl" class="chart" /></div>
        <div class="chart-card"><div ref="alignEl" class="chart" /></div>
        <div class="chart-card full-width">
          <div ref="trendEl" class="chart short" />
        </div>
      </div>

      <div v-if="result" class="analysis-card">
        <div class="analysis-left">
          <div class="section-title">详细分析结果</div>
          <p v-for="text in analysisParagraphs" :key="text" class="analysis-text">{{ text }}</p>
          <div class="formula-card">
            C = 10 - (0.2*S1 + 0.2*S2 + 0.35*S3 + 0.25*S4)
          </div>
        </div>
        <div class="analysis-right">
          <div class="section-title">增强与动作建议</div>
          <div class="llm-box">
            <div class="llm-meta">
              <span>向量增强：{{ result.llm_enhanced ? '已启用' : '未启用' }}</span>
              <span>语义条数：{{ result.semantic_rows ?? 0 }}</span>
              <span>向量条数：{{ result.embedding_rows ?? 0 }}</span>
            </div>
            <ul v-if="llmEvidence.length" class="llm-evidence">
              <li v-for="item in llmEvidence" :key="`${item.content_id}-${item.topic}`">[{{ item.topic }}] {{ item.summary }}</li>
            </ul>
          </div>
          <ul class="bullet" v-if="actionPlan?.s2">
            <li v-for="(b, idx) in actionPlan.s2.bullets" :key="`s2-${idx}`">{{ b }}</li>
          </ul>
          <ul class="bullet" v-if="actionPlan?.s4">
            <li v-for="(b, idx) in actionPlan.s4.bullets" :key="`s4-${idx}`">{{ b }}</li>
          </ul>
          <div v-if="!actionPlan?.s2 && !actionPlan?.s4" class="action-empty">
            当前 S2/S4 已较高，可优先优化 S1/S3 并通过动态模拟验证。
          </div>
        </div>
      </div>

      <div v-else class="empty">导入数据后自动显示评估结果</div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
}

.shell-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px 18px 18px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.title {
  margin: 0;
  font-size: 1.42rem;
  color: #0f172a;
}

.subtitle {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.92rem;
}

.error {
  margin: 10px 0 0;
  color: #dc2626;
}

.toolbar {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
}

.ready {
  margin-left: auto;
  display: flex;
  gap: 12px;
  font-size: 0.84rem;
  color: #475569;
}

.overview-card {
  margin-top: 12px;
  border-radius: 12px;
  padding: 14px;
  color: #f8fafc;
  background: linear-gradient(135deg, #1f2937 0%, #334155 100%);
}

.overview-main {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
}

.overview-title {
  font-size: 1.2rem;
  font-weight: 800;
}

.overview-desc {
  margin: 8px 0 0;
  font-size: 0.92rem;
  line-height: 1.6;
  color: #dbeafe;
}

.overview-note {
  margin: 8px 0 0;
  font-size: 0.84rem;
  color: #e2e8f0;
}

.score-circle {
  min-width: 92px;
  min-height: 92px;
  border-radius: 50%;
  border: 4px solid rgba(255, 255, 255, 0.45);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.score {
  font-size: 1.6rem;
  font-weight: 900;
}

.unit {
  font-size: 0.82rem;
  color: #dbeafe;
}

.kpi-row {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.kpi-item {
  padding: 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.kpi-item span {
  display: block;
  font-size: 0.8rem;
  color: #dbeafe;
}

.kpi-item strong {
  margin-top: 4px;
  display: block;
  font-size: 1.08rem;
  color: #fff;
}

.charts-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.chart-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.chart {
  width: 100%;
  height: 300px;
}

.chart.short {
  height: 250px;
}

.full-width {
  grid-column: 1 / -1;
}

.analysis-card {
  margin-top: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  background: #fff;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 12px;
}

.section-title {
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 8px;
}

.analysis-text {
  margin: 0 0 8px;
  font-size: 0.9rem;
  color: #334155;
  line-height: 1.65;
}

.formula-card {
  margin-top: 8px;
  padding: 10px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-size: 0.84rem;
  color: #334155;
  background: #f8fafc;
  font-weight: 700;
}

.llm-box {
  margin: 0;
  padding: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
}

.llm-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 0.82rem;
  color: #334155;
}

.llm-evidence {
  margin: 8px 0 0;
  padding-left: 16px;
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.6;
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

.empty {
  margin-top: 12px;
  color: #64748b;
  padding: 24px 0 0;
  font-size: 0.95rem;
}

@media (max-width: 960px) {
  .ready {
    width: 100%;
    margin-left: 0;
  }

  .kpi-row,
  .charts-grid,
  .analysis-card {
    grid-template-columns: 1fr;
  }

  .overview-main {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

