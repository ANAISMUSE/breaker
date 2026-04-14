<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

export interface AgentTraitsView {
  key: string
  display_name: string
  summary: string
  explore_delta: number
  echo_delta: number
  shallow_like_delta: number
  deep_social_delta: number
  skip_unfamiliar_delta: number
}

export interface TwinBuildPayload {
  interest: {
    topic_weights: Record<string, number>
    top_topics: string[]
    cluster_histogram: Record<string, number>
  }
  behavior: {
    like_rate: number
    comment_rate: number
    share_rate: number
    avg_duration: number
    weight_like: number
    weight_comment: number
  }
  cognitive: {
    stance_weights: Record<string, number>
    mean_emotion: number
    polarization_hint: number
  }
  memory_count: number
  memory_preview: Array<{
    topic: string
    stance: string
    text_summary?: string
    interaction_weight?: number
  }>
  agent_traits?: AgentTraitsView
}

const props = defineProps<{
  data: TwinBuildPayload | null
  rawJson: string
  viewMode: 'visual' | 'json'
}>()

const topicLabel: Record<string, string> = {
  technology: '科技',
  entertainment: '娱乐',
  society: '社会',
  health: '健康',
  finance: '财经',
  politics: '时政',
  education: '教育',
  sports: '体育',
  other: '其他',
}

const sortedTopics = computed(() => {
  const tw = props.data?.interest.topic_weights ?? {}
  const entries = Object.entries(tw).sort((a, b) => b[1] - a[1])
  const max = Math.max(...entries.map(([, v]) => v), 1e-9)
  return entries.map(([k, v]) => ({
    key: k,
    label: topicLabel[k] ?? k,
    pct: Math.round((v / max) * 100),
    weight: v,
  }))
})

const stanceEntries = computed(() => {
  const sw = props.data?.cognitive.stance_weights ?? {}
  return Object.entries(sw)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({ key: k, pct: Math.round(v * 1000) / 10 }))
})

const traitDeltas = computed(() => {
  const t = props.data?.agent_traits
  if (!t) return []
  return [
    { label: '探索 (search)', value: t.explore_delta },
    { label: '熟悉强化 (like×匹配)', value: t.echo_delta },
    { label: '轻互动 (like)', value: t.shallow_like_delta },
    { label: '深社交 (评/赞评)', value: t.deep_social_delta },
    { label: '陌生跳过', value: t.skip_unfamiliar_delta },
  ]
})

const donutEl = ref<HTMLDivElement | null>(null)
const radarEl = ref<HTMLDivElement | null>(null)
const trendEl = ref<HTMLDivElement | null>(null)
let donutChart: echarts.ECharts | null = null
let radarChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

const clusterEntries = computed(() => {
  const raw = props.data?.interest.cluster_histogram ?? {}
  return Object.entries(raw)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({ key: k, value: v }))
})

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v))
}

function ensureChart(el: HTMLDivElement | null, instance: echarts.ECharts | null) {
  if (!el) return null
  return instance ?? echarts.init(el)
}

function drawDonut() {
  donutChart = ensureChart(donutEl.value, donutChart)
  if (!donutChart) return
  const topicData = sortedTopics.value.map((item) => ({
    name: item.label,
    value: Number((item.weight * 100).toFixed(4)),
  }))
  donutChart.setOption({
    title: { text: '兴趣分布环状图', left: 'center', top: 4, textStyle: { fontSize: 13, color: '#0f172a' } },
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    legend: { bottom: 0, left: 'center', type: 'scroll' },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '52%'],
        label: { formatter: '{b}\n{d}%' },
        data: topicData,
      },
    ],
  })
}

function drawRadar() {
  radarChart = ensureChart(radarEl.value, radarChart)
  if (!radarChart || !props.data) return
  const d = props.data
  const avgDurationNorm = clamp01(d.behavior.avg_duration / 180)
  const emotionNorm = clamp01(d.cognitive.mean_emotion / 5)
  const antiPolarNorm = clamp01(1 - d.cognitive.polarization_hint)
  const topTopicWeight = sortedTopics.value.length ? clamp01(sortedTopics.value[0].weight) : 0
  const values = [
    d.behavior.like_rate,
    d.behavior.comment_rate,
    d.behavior.share_rate,
    avgDurationNorm,
    emotionNorm,
    antiPolarNorm,
    topTopicWeight,
  ].map((x) => Number((x * 100).toFixed(2)))
  radarChart.setOption({
    title: { text: '行为-认知雷达图', left: 'center', top: 4, textStyle: { fontSize: 13, color: '#0f172a' } },
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '点赞', max: 100 },
        { name: '评论', max: 100 },
        { name: '分享', max: 100 },
        { name: '停留深度', max: 100 },
        { name: '情感均值', max: 100 },
        { name: '反极化', max: 100 },
        { name: '核心兴趣强度', max: 100 },
      ],
      radius: '64%',
    },
    series: [
      {
        type: 'radar',
        data: [{ value: values, name: '画像指标' }],
        areaStyle: { color: 'rgba(59,130,246,0.2)' },
      },
    ],
  })
}

function drawTrend() {
  trendChart = ensureChart(trendEl.value, trendChart)
  if (!trendChart || !props.data) return
  const preview = props.data.memory_preview ?? []
  const x = preview.map((_, idx) => `M${idx + 1}`)
  const y = preview.map((item, idx) => {
    const v = typeof item.interaction_weight === 'number' ? item.interaction_weight : 1 - idx * 0.06
    return Number(Math.max(0, v).toFixed(4))
  })
  trendChart.setOption({
    title: { text: '记忆流互动趋势', left: 'center', top: 4, textStyle: { fontSize: 13, color: '#0f172a' } },
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 12, top: 38, bottom: 26, containLabel: true },
    xAxis: { type: 'category', data: x },
    yAxis: { type: 'value', min: 0, max: Math.max(1, ...y) },
    series: [
      {
        type: 'line',
        smooth: true,
        data: y,
        symbolSize: 7,
        areaStyle: { color: 'rgba(16,185,129,0.14)' },
        lineStyle: { width: 2 },
      },
    ],
  })
}

async function renderCharts() {
  await nextTick()
  if (!props.data) return
  drawDonut()
  drawRadar()
  drawTrend()
}

function disposeCharts() {
  donutChart?.dispose()
  radarChart?.dispose()
  trendChart?.dispose()
  donutChart = null
  radarChart = null
  trendChart = null
}

watch(
  () => [props.data, props.viewMode] as const,
  async ([data, mode]) => {
    if (!data || mode !== 'visual') {
      disposeCharts()
      return
    }
    await renderCharts()
  },
  { immediate: true, deep: true }
)

function onResize() {
  donutChart?.resize()
  radarChart?.resize()
  trendChart?.resize()
}

if (typeof window !== 'undefined') {
  window.addEventListener('resize', onResize)
}

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', onResize)
  }
  disposeCharts()
})
</script>

<template>
  <div class="preview-root">
    <template v-if="viewMode === 'json'">
      <pre class="json-block">{{ rawJson || '（尚未构建）' }}</pre>
    </template>
    <template v-else-if="!data">
      <div class="empty">构建成功后，此处展示孪生画像可视化；仍为 JSON 结构，只是用卡片与条形图呈现。</div>
    </template>
    <template v-else>
      <div v-if="data.agent_traits" class="traits-banner">
        <div class="traits-title">{{ data.agent_traits.display_name }}</div>
        <p class="traits-summary">{{ data.agent_traits.summary }}</p>
        <div class="delta-grid">
          <div v-for="d in traitDeltas" :key="d.label" class="delta-chip">
            <span class="d-label">{{ d.label }}</span>
            <span :class="['d-val', d.value > 0 ? 'pos' : d.value < 0 ? 'neg' : '']">
              {{ d.value > 0 ? '+' : '' }}{{ d.value.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel">
        <h3 class="sec-title">画像可视化总览</h3>
        <p class="sec-hint">环状图、雷达图、趋势图横向并排，减少上下滚动。</p>
        <div class="charts-row">
          <div ref="donutEl" class="chart-card chart" />
          <div ref="radarEl" class="chart-card chart" />
          <div ref="trendEl" class="chart-card chart" />
        </div>
      </div>

      <div class="cards-grid">
        <div class="panel">
          <h3 class="sec-title">行为习惯</h3>
          <ul class="stat-list">
            <li>点赞率 <strong>{{ (data.behavior.like_rate * 100).toFixed(0) }}%</strong></li>
            <li>评论率 <strong>{{ (data.behavior.comment_rate * 100).toFixed(0) }}%</strong></li>
            <li>分享率 <strong>{{ (data.behavior.share_rate * 100).toFixed(0) }}%</strong></li>
            <li>均停留 <strong>{{ data.behavior.avg_duration.toFixed(0) }}s</strong></li>
          </ul>
        </div>
        <div class="panel">
          <h3 class="sec-title">认知与情感</h3>
          <p class="sec-hint">立场分布 · 平均情感 {{ data.cognitive.mean_emotion.toFixed(1) }} / 5</p>
          <div class="tags">
            <el-tag v-for="s in stanceEntries" :key="s.key" class="tag" type="info" effect="plain">
              {{ s.key }} {{ s.pct }}%
            </el-tag>
          </div>
          <p class="muted small">极化提示 {{ data.cognitive.polarization_hint.toFixed(2) }}</p>
        </div>
        <div class="panel">
          <h3 class="sec-title">兴趣结构（细节）</h3>
          <p class="sec-hint">主题权重（相对峰值归一化）</p>
          <div v-for="t in sortedTopics" :key="t.key" class="bar-row">
            <span class="bar-label">{{ t.label }}</span>
            <el-progress :percentage="t.pct" :stroke-width="10" />
            <span class="bar-num">{{ (t.weight * 100).toFixed(1) }}%</span>
          </div>
          <p v-if="sortedTopics.length === 0" class="muted">无主题分布</p>
        </div>
        <div class="panel">
          <h3 class="sec-title">语义簇直方图（隐性兴趣）</h3>
          <p class="sec-hint">来自 embedding 聚类结果</p>
          <div v-if="clusterEntries.length" class="cluster-list">
            <div v-for="item in clusterEntries" :key="item.key" class="cluster-row">
              <span class="cluster-key">{{ item.key }}</span>
              <el-progress :percentage="Math.min(100, Math.round(item.value * 100))" :stroke-width="8" />
              <span class="cluster-val">{{ item.value.toFixed(2) }}</span>
            </div>
          </div>
          <p v-else class="muted">无聚类统计</p>
        </div>
      </div>

      <div class="cards-grid bottom-grid">
        <div class="panel">
          <h3 class="sec-title">记忆流预览</h3>
          <p class="sec-hint">共 {{ data.memory_count }} 条，展示前 {{ data.memory_preview.length }} 条摘要</p>
          <el-scrollbar max-height="220px">
            <div v-for="(m, i) in data.memory_preview" :key="i" class="mem-line">
              <el-tag size="small" effect="dark">{{ m.topic }}</el-tag>
              <span class="mem-stance">{{ m.stance }}</span>
              <span class="mem-text">{{ m.text_summary?.slice(0, 80) || '—' }}</span>
            </div>
          </el-scrollbar>
        </div>
        <div class="panel">
          <h3 class="sec-title">关键指标摘要</h3>
          <p class="sec-hint">用于快速判断“画像是否偏斜”</p>
          <div class="summary-grid">
            <div class="summary-item">
              <span>Top主题占比</span>
              <strong>{{ sortedTopics[0] ? (sortedTopics[0].weight * 100).toFixed(1) : '0.0' }}%</strong>
            </div>
            <div class="summary-item">
              <span>立场主导占比</span>
              <strong>{{ stanceEntries[0] ? stanceEntries[0].pct.toFixed(1) : '0.0' }}%</strong>
            </div>
            <div class="summary-item">
              <span>点赞/评论权重</span>
              <strong>{{ data.behavior.weight_like.toFixed(2) }} / {{ data.behavior.weight_comment.toFixed(2) }}</strong>
            </div>
            <div class="summary-item">
              <span>均情感值</span>
              <strong>{{ data.cognitive.mean_emotion.toFixed(2) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.preview-root {
  min-height: 280px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
  background: #f8fafc;
}
.json-block {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 480px;
  overflow: auto;
}
.empty {
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
  padding: 24px 8px;
}
.traits-banner {
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.traits-title {
  font-weight: 600;
  color: #1e3a5f;
  font-size: 15px;
}
.traits-summary {
  margin: 6px 0 10px;
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}
.delta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.delta-chip {
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
  align-items: center;
}
.d-label {
  color: #64748b;
}
.d-val {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.d-val.pos {
  color: #059669;
}
.d-val.neg {
  color: #dc2626;
}
.section {
  margin-bottom: 16px;
}
.panel {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
}
.charts-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.chart-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.chart {
  height: 236px;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.bottom-grid {
  margin-top: 12px;
}
@media (max-width: 720px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
}
.sec-title {
  margin: 0 0 4px;
  font-size: 14px;
  color: #0f172a;
}
.sec-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: #64748b;
}
.bar-row {
  display: grid;
  grid-template-columns: 72px 1fr 52px;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}
.bar-label {
  font-size: 12px;
  color: #334155;
}
.bar-num {
  font-size: 11px;
  color: #64748b;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.cluster-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cluster-row {
  display: grid;
  grid-template-columns: 90px 1fr 56px;
  gap: 8px;
  align-items: center;
}
.cluster-key {
  color: #334155;
  font-size: 12px;
}
.cluster-val {
  color: #64748b;
  font-size: 11px;
  text-align: right;
}
.stat-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #334155;
  line-height: 1.7;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag {
  margin: 0;
}
.mem-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
}
.mem-stance {
  color: #64748b;
  flex-shrink: 0;
  width: 56px;
}
.mem-text {
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted {
  color: #94a3b8;
  font-size: 13px;
}
.muted.small {
  font-size: 12px;
  margin: 8px 0 0;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.summary-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.summary-item span {
  font-size: 12px;
  color: #64748b;
}
.summary-item strong {
  color: #0f172a;
  font-size: 16px;
}
</style>
