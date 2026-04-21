<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoRows } from '@/constants/demoData'

type JsonRow = Record<string, unknown>

interface TwinProfile {
  interest?: {
    topic_weights?: Record<string, number>
    cluster_histogram?: Record<string, number>
    top_topics?: string[]
  }
  behavior?: {
    like_rate?: number
    comment_rate?: number
    share_rate?: number
    avg_duration?: number
    weight_like?: number
    weight_comment?: number
  }
  cognitive?: {
    stance_weights?: Record<string, number>
    mean_emotion?: number
    polarization_hint?: number
  }
  memory_count?: number
  memory_preview?: Array<{
    content_id?: string
    topic?: string
    stance?: string
    text_summary?: string
    timestamp?: string
    interaction_weight?: number
  }>
  agent_traits?: {
    key?: string
    display_name?: string
    summary?: string
  }
}

interface PersonaBuildResponse {
  profile_id?: string
  user_id?: string
  created_at?: string
  profile?: TwinProfile
}

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const parsedRows = ref<JsonRow[]>(demoRows as JsonRow[])
const profile = ref<TwinProfile | null>(null)
const buildMeta = ref<{ profileId: string; userId: string; createdAt: string } | null>(null)
const showRaw = ref(false)
const showSource = ref(false)

const builtinPlatforms = ['all', 'douyin', 'weibo', 'xiaohongshu', 'kuaishou', 'bilibili']
const selectedPlatform = ref('all')

const topicChartEl = ref<HTMLDivElement | null>(null)
const stanceChartEl = ref<HTMLDivElement | null>(null)
const dimensionChartEl = ref<HTMLDivElement | null>(null)

let topicChart: echarts.ECharts | null = null
let stanceChart: echarts.ECharts | null = null
let dimensionChart: echarts.ECharts | null = null

function safeNum(v: unknown, fallback = 0): number {
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : fallback
}

function normalizePlatform(raw: unknown): string {
  const v = String(raw ?? '')
    .trim()
    .toLowerCase()
  if (!v) return 'unknown'
  if (v.includes('抖音') || v.includes('douyin') || v.includes('tiktok')) return 'douyin'
  if (v.includes('微博') || v.includes('weibo')) return 'weibo'
  if (v.includes('小红书') || v.includes('xiaohongshu') || v.includes('redbook') || v.includes('xhs')) return 'xiaohongshu'
  if (v.includes('快手') || v.includes('kuaishou')) return 'kuaishou'
  if (v.includes('哔哩') || v.includes('bilibili') || v.includes('b站')) return 'bilibili'
  return v
}

const platformOptions = computed(() => {
  const detected = new Set<string>()
  for (const row of parsedRows.value) {
    const platform = normalizePlatform(row.platform ?? row.source_platform ?? row.app ?? row.channel)
    if (platform !== 'unknown') detected.add(platform)
  }
  return Array.from(new Set([...builtinPlatforms, ...Array.from(detected)])).map((value) => ({
    value,
    label: value === 'all' ? '全部平台' : value,
  }))
})

const activeRows = computed(() => {
  if (selectedPlatform.value === 'all') return parsedRows.value
  return parsedRows.value.filter((row) => {
    const p = normalizePlatform(row.platform ?? row.source_platform ?? row.app ?? row.channel)
    return p === selectedPlatform.value
  })
})

const topicWeights = computed(() => profile.value?.interest?.topic_weights ?? {})
const stanceWeights = computed(() => profile.value?.cognitive?.stance_weights ?? {})
const topTopics = computed(() => {
  const explicit = profile.value?.interest?.top_topics ?? []
  if (explicit.length) return explicit.slice(0, 8)
  return Object.entries(topicWeights.value)
    .sort((a, b) => b[1] - a[1])
    .map(([k]) => k)
    .slice(0, 8)
})

const riskScore = computed(() => {
  const polar = safeNum(profile.value?.cognitive?.polarization_hint, 0.5)
  const top1 = Math.max(0, ...Object.values(topicWeights.value).map((x) => safeNum(x)))
  const score = (polar * 0.6 + top1 * 0.4) * 100
  return Math.max(0, Math.min(100, score))
})

const ecologyScore = computed(() => {
  const entries = Object.values(topicWeights.value)
  if (!entries.length) return 0
  let entropy = 0
  for (const p of entries) {
    const v = Math.max(0, safeNum(p, 0))
    if (v > 0) entropy += -(v * Math.log(v + 1e-12))
  }
  const hMax = entries.length > 1 ? Math.log(entries.length) : 1
  const ratio = Math.max(0, Math.min(1, entropy / (hMax + 1e-12)))
  const score = ((1 - safeNum(profile.value?.cognitive?.polarization_hint, 0.5)) * 0.45 + ratio * 0.55) * 100
  return Math.max(0, Math.min(100, score))
})

const activityScore = computed(() => {
  const behavior = profile.value?.behavior
  if (!behavior) return 0
  const engagement =
    (safeNum(behavior.like_rate) + safeNum(behavior.comment_rate) + safeNum(behavior.share_rate)) / 3
  const dur = Math.min(1, safeNum(behavior.avg_duration) / 120)
  return Math.max(0, Math.min(100, (engagement * 0.8 + dur * 0.2) * 100))
})

const trendScore = computed(() => {
  const count = safeNum(profile.value?.memory_count, 0)
  return Math.max(0, Math.min(100, (count / 80) * 100))
})

const dimensionItems = computed(() => [
  { key: '内容生态', value: ecologyScore.value },
  { key: '风险评估', value: riskScore.value },
  { key: '活跃度', value: activityScore.value },
  { key: '历史沉淀', value: trendScore.value },
])

const insights = computed(() => {
  if (!profile.value) return []
  const behavior = profile.value.behavior ?? {}
  const cognitive = profile.value.cognitive ?? {}
  const mainTopic = topTopics.value[0] ?? '暂无主导主题'
  const mainStance =
    Object.entries(stanceWeights.value).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '未知'
  return [
    `主导主题为 ${mainTopic}，建议补充低曝光主题，避免内容过度单一。`,
    `当前立场倾向偏 ${mainStance}，极化提示值 ${safeNum(cognitive.polarization_hint, 0).toFixed(2)}。`,
    `平均停留时长约 ${safeNum(behavior.avg_duration, 0).toFixed(1)} 秒，互动活跃度得分 ${activityScore.value.toFixed(1)}。`,
    `记忆样本条数 ${safeNum(profile.value.memory_count, 0)}，可用于后续策略回放和报告追踪。`,
  ]
})

const riskLevelText = computed(() => {
  const score = riskScore.value
  if (score >= 75) return '高风险关注区'
  if (score >= 55) return '中风险预警区'
  return '低风险稳定区'
})

const overviewSummary = computed(() => {
  const score = riskScore.value
  const ecology = ecologyScore.value
  const activity = activityScore.value
  const topic = topTopics.value[0] ?? '暂无主导主题'
  return `当前综合风险评分 ${score.toFixed(1)}，生态健康度 ${ecology.toFixed(1)}，互动活跃度 ${activity.toFixed(1)}。主导内容主题集中在 ${topic}。`
})

const detailParagraphs = computed(() => [
  `风险判定：当前结果落在「${riskLevelText.value}」。建议围绕主导内容增加反向观点与多样主题供给，缓解内容收敛。`,
  `结构观察：内容生态分布与立场结构显示，受众偏好已有明显聚合趋势。若持续单一供给，极化提示值会继续抬升。`,
  `执行建议：按周追踪四项核心维度（内容生态、风险评估、活跃度、历史沉淀），并结合样本回放持续校准策略。`,
])

const memoryRows = computed(() => (profile.value?.memory_preview ?? []).slice(0, 6))
const rawResult = computed(() => JSON.stringify(profile.value ?? {}, null, 2))

function disposeCharts() {
  topicChart?.dispose()
  stanceChart?.dispose()
  dimensionChart?.dispose()
  topicChart = null
  stanceChart = null
  dimensionChart = null
}

function drawCharts() {
  if (!profile.value) return
  if (topicChartEl.value) {
    topicChart = topicChart ?? echarts.init(topicChartEl.value)
    topicChart.setOption({
      title: { text: '内容生态分布', left: 'center', textStyle: { fontSize: 14, color: '#0f172a' } },
      tooltip: { trigger: 'item' },
      legend: { bottom: 4, type: 'scroll' },
      series: [
        {
          type: 'pie',
          radius: ['42%', '70%'],
          data: Object.entries(topicWeights.value)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([name, value]) => ({ name, value })),
          label: { formatter: '{b}: {d}%' },
        },
      ],
    })
  }

  if (stanceChartEl.value) {
    stanceChart = stanceChart ?? echarts.init(stanceChartEl.value)
    stanceChart.setOption({
      title: { text: '立场与情绪结构', left: 'center', textStyle: { fontSize: 14, color: '#0f172a' } },
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['50%', '54%'],
          data: Object.entries(stanceWeights.value).map(([name, value]) => ({ name, value })),
          label: { formatter: '{b}: {d}%' },
        },
      ],
    })
  }

  if (dimensionChartEl.value) {
    dimensionChart = dimensionChart ?? echarts.init(dimensionChartEl.value)
    dimensionChart.setOption({
      title: { text: '维度趋势总览', left: 'center', textStyle: { fontSize: 14, color: '#0f172a' } },
      tooltip: { trigger: 'axis' },
      grid: { left: 32, right: 16, top: 44, bottom: 30, containLabel: true },
      xAxis: { type: 'category', data: dimensionItems.value.map((x) => x.key) },
      yAxis: { type: 'value', min: 0, max: 100 },
      series: [
        {
          type: 'bar',
          data: dimensionItems.value.map((x) => Number(x.value.toFixed(2))),
          itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
        },
      ],
    })
  }
}

async function runBuild(rows: JsonRow[]) {
  if (!rows.length) {
    profile.value = null
    errorMsg.value = '当前平台没有可用数据，请先切换平台或导入数据。'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.post<PersonaBuildResponse>('/api/persona/build', { rows })
    profile.value = data.profile ?? null
    buildMeta.value = {
      profileId: String(data.profile_id ?? '-'),
      userId: String(data.user_id ?? '-'),
      createdAt: String(data.created_at ?? '-'),
    }
    await nextTick()
    drawCharts()
  } catch (e) {
    profile.value = null
    errorMsg.value = e instanceof Error ? e.message : '构建画像失败'
  } finally {
    loading.value = false
  }
}

async function buildProfile() {
  errorMsg.value = ''
  try {
    const rows = JSON.parse(rowsText.value) as unknown
    if (!Array.isArray(rows)) throw new Error('样本数据必须是 JSON 数组')
    parsedRows.value = rows as JsonRow[]
    await runBuild(activeRows.value)
  } catch (e) {
    profile.value = null
    errorMsg.value = e instanceof Error ? e.message : '数据解析失败'
  }
}

function onImportedRows(
  rows: JsonRow[],
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
  parsedRows.value = rows
  rowsText.value = JSON.stringify(rows, null, 2)
  buildProfile()
}

function onImportError(message: string) {
  errorMsg.value = message
}

function scoreClass(score: number) {
  if (score >= 70) return 'high'
  if (score >= 45) return 'mid'
  return 'low'
}

watch(selectedPlatform, async () => {
  if (!parsedRows.value.length) return
  await runBuild(activeRows.value)
})

let resizeHandler: (() => void) | null = null
onMounted(async () => {
  await runBuild(activeRows.value)
  resizeHandler = () => {
    topicChart?.resize()
    stanceChart?.resize()
    dimensionChart?.resize()
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
    <div class="shell-card">
      <div class="head">
        <div>
          <h1 class="title">应用画像分析</h1>
          <p class="subtitle">按“平台 -> 内容生态 -> 评测报告”的结构展示画像分析结果。</p>
        </div>
        <div class="actions">
          <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
          <el-button type="primary" :loading="loading" @click="buildProfile">刷新分析</el-button>
        </div>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="hero">
        <div class="hero-main">
          <div class="app-icon">
            <span class="app-emoji">🖌</span>
          </div>
          <div>
            <div class="hero-title">应用画像总览</div>
            <div class="hero-subtitle">{{ riskLevelText }}</div>
            <div class="hero-desc">
              {{ profile?.agent_traits?.display_name || '默认用户画像' }} ·
              {{ profile?.agent_traits?.summary || '基于当前导入数据生成' }}
            </div>
            <div class="hero-overview">{{ overviewSummary }}</div>
          </div>
        </div>
        <div class="hero-right">
          <div class="hero-actions">
            <el-select v-model="selectedPlatform" class="platform-select" size="large">
              <el-option v-for="item in platformOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-button size="large">导出</el-button>
            <el-button size="large">分享</el-button>
          </div>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi">
          <span>风险评分</span>
          <strong>{{ riskScore.toFixed(1) }}</strong>
        </div>
        <div class="kpi">
          <span>生态健康度</span>
          <strong>{{ ecologyScore.toFixed(1) }}</strong>
        </div>
        <div class="kpi">
          <span>互动活跃度</span>
          <strong>{{ activityScore.toFixed(1) }}</strong>
        </div>
        <div class="kpi">
          <span>历史样本量</span>
          <strong>{{ profile?.memory_count ?? 0 }}</strong>
        </div>
      </div>

      <div class="content-grid">
        <div class="chart-box overview-side">
          <div class="score-card">
            <div class="score-ring" :class="scoreClass(riskScore)">
              <span>{{ riskScore.toFixed(0) }}</span>
            </div>
            <div class="score-meta">
              <div class="score-title">整体风险评估</div>
              <div class="score-text">分值越高，内容收敛和认知极化风险越高。</div>
            </div>
          </div>

          <div class="bars">
            <div v-for="item in dimensionItems" :key="item.key" class="bar-row">
              <div class="bar-label">{{ item.key }}</div>
              <el-progress :percentage="Number(item.value.toFixed(1))" :stroke-width="10" />
            </div>
          </div>

          <div class="topic-cloud">
            <div class="panel-title">关键词洞察</div>
            <div class="chips">
              <span v-for="(topic, idx) in topTopics" :key="topic" class="chip" :style="{ fontSize: `${16 - idx}px` }">
                {{ topic }}
              </span>
            </div>
          </div>
        </div>

        <div class="chart-box"><div ref="topicChartEl" class="chart" /></div>
        <div class="chart-box"><div ref="stanceChartEl" class="chart" /></div>
      </div>

      <div class="chart-box full trend-box">
        <div ref="dimensionChartEl" class="chart short" />
      </div>

      <div class="report-card">
        <div class="panel-head">
          <div class="panel-title">详细风险报告</div>
          <el-switch v-model="showRaw" inline-prompt active-text="JSON" inactive-text="报告" />
        </div>

        <div v-if="showRaw" class="raw-wrap">
          <el-input :model-value="rawResult" type="textarea" :rows="14" readonly />
        </div>
        <div v-else class="report-content">
          <div class="analysis-text">
            <p v-for="text in detailParagraphs" :key="text">{{ text }}</p>
          </div>
          <div class="report-bottom">
            <div>
              <div class="meta-grid" v-if="buildMeta">
                <div>记录ID：{{ buildMeta.profileId }}</div>
                <div>用户ID：{{ buildMeta.userId }}</div>
                <div>生成时间：{{ buildMeta.createdAt }}</div>
                <div>平台：{{ selectedPlatform }}</div>
              </div>
              <ul class="insights">
                <li v-for="text in insights" :key="text">{{ text }}</li>
              </ul>
            </div>
            <el-table :data="memoryRows" size="small" stripe empty-text="暂无预览样本">
              <el-table-column prop="topic" label="主题" width="120" />
              <el-table-column prop="stance" label="立场" width="100" />
              <el-table-column prop="interaction_weight" label="权重" width="100">
                <template #default="{ row }">{{ safeNum(row.interaction_weight, 0).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column prop="text_summary" label="内容摘要" min-width="260" show-overflow-tooltip />
            </el-table>
          </div>
        </div>
      </div>

      <div class="source-card">
        <div class="panel-head">
          <div class="panel-title">源数据</div>
          <el-switch v-model="showSource" inline-prompt active-text="展开" inactive-text="收起" />
        </div>
        <el-input
          v-if="showSource"
          v-model="rowsText"
          type="textarea"
          :rows="8"
          placeholder="行为样本数据（JSON 数组）"
        />
      </div>
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
  padding: 18px 20px 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  margin: 0;
  font-size: 1.48rem;
  color: #0f172a;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 0.94rem;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.error {
  margin: 10px 0 0;
  color: #dc2626;
}

.hero {
  margin-top: 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1f2937 0%, #334155 100%);
  color: #f8fafc;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  min-height: 120px;
}

.hero-main {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 1;
  min-width: 420px;
}

.app-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 800;
  background: rgba(255, 255, 255, 0.2);
  margin-top: 4px;
}

.app-emoji {
  font-size: 20px;
  line-height: 1;
}

.hero-title {
  font-size: 1.25rem;
  font-weight: 700;
}

.hero-subtitle {
  margin-top: 4px;
  font-size: 1rem;
  font-weight: 600;
  color: #fde68a;
}

.hero-desc {
  margin-top: 6px;
  font-size: 0.88rem;
  color: #dbeafe;
}

.hero-overview {
  margin-top: 8px;
  max-width: 720px;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #e2e8f0;
}

.hero-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.platform-select {
  width: 172px;
}

.kpi-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.kpi {
  border: 1px solid #edf2f7;
  border-radius: 10px;
  padding: 12px;
  background: #f8fafc;
}

.kpi span {
  font-size: 0.84rem;
  color: #64748b;
}

.kpi strong {
  margin-top: 6px;
  display: block;
  font-size: 1.4rem;
  color: #0f172a;
}

.content-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1.05fr 1fr 1fr;
  gap: 10px;
}

.score-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.score-ring {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  border: 6px solid #cbd5e1;
  display: grid;
  place-items: center;
  font-size: 1.2rem;
  font-weight: 800;
}

.score-ring.high {
  border-color: #f43f5e;
  color: #be123c;
}

.score-ring.mid {
  border-color: #f59e0b;
  color: #b45309;
}

.score-ring.low {
  border-color: #10b981;
  color: #047857;
}

.score-title {
  font-weight: 700;
  color: #0f172a;
  font-size: 1rem;
}

.score-text {
  margin-top: 5px;
  font-size: 0.86rem;
  color: #64748b;
  line-height: 1.5;
}

.bars {
  padding: 12px 0 8px;
}

.bar-row {
  margin-bottom: 8px;
}

.bar-row:last-child {
  margin-bottom: 0;
}

.bar-label {
  margin-bottom: 6px;
  font-size: 0.86rem;
  color: #334155;
  font-weight: 600;
}

.panel-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.topic-cloud {
  margin-top: 6px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.chips {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 4px 9px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-weight: 600;
  font-size: 13px;
}

.chart-box {
  border: 1px solid #edf2f7;
  border-radius: 10px;
  padding: 8px;
  background: #fff;
}

.overview-side {
  display: flex;
  flex-direction: column;
}

.trend-box {
  margin-top: 10px;
}

.chart {
  width: 100%;
  height: 290px;
}

.chart.short {
  height: 240px;
}

.report-card,
.source-card {
  margin-top: 12px;
  border: 1px solid #edf2f7;
  border-radius: 10px;
  padding: 12px 14px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
  font-size: 0.86rem;
  color: #475569;
}

.analysis-text {
  margin-bottom: 10px;
}

.analysis-text p {
  margin: 0 0 8px;
  color: #334155;
  font-size: 0.94rem;
  line-height: 1.75;
}

.analysis-text p:last-child {
  margin-bottom: 0;
}

.report-bottom {
  display: grid;
  grid-template-columns: 1fr 1.35fr;
  gap: 10px;
  align-items: start;
}

.insights {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 0.88rem;
  line-height: 1.65;
}

.raw-wrap :deep(textarea),
.source-card :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

@media (max-width: 900px) {
  .report-bottom,
  .content-grid,
  .kpi-grid,
  .meta-grid {
    grid-template-columns: 1fr;
  }

  .hero-main {
    min-width: 0;
  }

  .hero-right {
    align-items: flex-start;
    flex-direction: column;
    margin-left: 0;
  }
}
</style>

