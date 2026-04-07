<script setup lang="ts">
import { computed } from 'vue'

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

      <div class="section">
        <h3 class="sec-title">兴趣结构</h3>
        <p class="sec-hint">主题权重（相对峰值归一化），驱动「是否像你会点的内容」</p>
        <div v-for="t in sortedTopics" :key="t.key" class="bar-row">
          <span class="bar-label">{{ t.label }}</span>
          <el-progress :percentage="t.pct" :stroke-width="10" />
          <span class="bar-num">{{ (t.weight * 100).toFixed(1) }}%</span>
        </div>
        <p v-if="sortedTopics.length === 0" class="muted">无主题分布</p>
      </div>

      <div class="section two-col">
        <div>
          <h3 class="sec-title">行为习惯</h3>
          <ul class="stat-list">
            <li>点赞率 <strong>{{ (data.behavior.like_rate * 100).toFixed(0) }}%</strong></li>
            <li>评论率 <strong>{{ (data.behavior.comment_rate * 100).toFixed(0) }}%</strong></li>
            <li>分享率 <strong>{{ (data.behavior.share_rate * 100).toFixed(0) }}%</strong></li>
            <li>均停留 <strong>{{ data.behavior.avg_duration.toFixed(0) }}s</strong></li>
          </ul>
        </div>
        <div>
          <h3 class="sec-title">认知与情感</h3>
          <p class="sec-hint">立场分布 · 平均情感 {{ data.cognitive.mean_emotion.toFixed(1) }} / 5</p>
          <div class="tags">
            <el-tag v-for="s in stanceEntries" :key="s.key" class="tag" type="info" effect="plain">
              {{ s.key }} {{ s.pct }}%
            </el-tag>
          </div>
          <p class="muted small">极化提示 {{ data.cognitive.polarization_hint.toFixed(2) }}</p>
        </div>
      </div>

      <div class="section">
        <h3 class="sec-title">记忆流预览</h3>
        <p class="sec-hint">共 {{ data.memory_count }} 条，展示前 {{ data.memory_preview.length }} 条摘要</p>
        <el-scrollbar max-height="200px">
          <div v-for="(m, i) in data.memory_preview" :key="i" class="mem-line">
            <el-tag size="small" effect="dark">{{ m.topic }}</el-tag>
            <span class="mem-stance">{{ m.stance }}</span>
            <span class="mem-text">{{ m.text_summary?.slice(0, 80) || '—' }}</span>
          </div>
        </el-scrollbar>
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
.section.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 720px) {
  .section.two-col {
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
</style>
