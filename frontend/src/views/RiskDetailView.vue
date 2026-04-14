<script setup lang="ts">
import { ref } from 'vue'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

interface RiskDetailPayload {
  overview: {
    s1_content_diversity: number
    s2_cross_domain: number
    s3_stance_diversity: number
    s4_cognitive_coverage: number
    cocoon_index: number
    mode: string
  }
  distributions: {
    topic: Record<string, number>
    stance: Record<string, number>
    benchmark: Record<string, number>
    alignment: number
  }
  derived: {
    s1_entropy: { h: number; h_max: number; ratio: number }
    s2_cross: { top2: string[]; top2_prob: number; alpha: number }
    s3_gini: { count: number; gini: number }
    s4_overlap: { overlap: number; r_topic: number }
  }
  suggestions: {
    s2: null | {
      severity: string
      target_s2: number
      alpha_now: number
      alpha_target: number
      top2_topics: string[]
      recommended_topics: Array<{ topic: string; benchmark: number; actual: number; deficit: number }>
    }
    s4: null | {
      severity: string
      target_s4: number
      overlap_now: number
      overlap_target: number
      recommended_topics: Array<{ topic: string; benchmark: number; actual: number; deficit: number }>
    }
  }
}

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const benchmarkText = ref(JSON.stringify(demoBenchmark, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const detail = ref<RiskDetailPayload | null>(null)

function severityLabel(v: string) {
  if (v === 'high') return '高'
  if (v === 'medium') return '中'
  return '低'
}

function toRows(dist: Record<string, number>) {
  return Object.entries(dist)
    .map(([key, value]) => ({ key, value }))
    .sort((a, b) => b.value - a.value)
}

function onImportedRows(rows: Record<string, unknown>[]) {
  errorMsg.value = ''
  rowsText.value = JSON.stringify(rows, null, 2)
}

function onImportError(message: string) {
  errorMsg.value = message
}

async function runDetail() {
  loading.value = true
  errorMsg.value = ''
  try {
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const benchmark = JSON.parse(benchmarkText.value) as Record<string, number>
    const { data } = await http.post<RiskDetailPayload>('/api/risk/detail', { rows, benchmark })
    detail.value = data
  } catch (e) {
    detail.value = null
    errorMsg.value = e instanceof Error ? e.message : '风险详情计算失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">风险详情页</h1>
        <div class="head-actions">
          <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
          <el-button type="primary" :loading="loading" @click="runDetail">计算详情</el-button>
        </div>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div class="input-grid">
        <el-input v-model="rowsText" type="textarea" :rows="8" placeholder="rows JSON 数组" />
        <el-input v-model="benchmarkText" type="textarea" :rows="8" placeholder="benchmark JSON 对象" />
      </div>

      <div v-if="detail" class="sections">
        <el-card shadow="never">
          <template #header>概览指标</template>
          <div class="kpi-grid">
            <div class="kpi"><span>S1</span><strong>{{ detail.overview.s1_content_diversity.toFixed(2) }}</strong></div>
            <div class="kpi"><span>S2</span><strong>{{ detail.overview.s2_cross_domain.toFixed(2) }}</strong></div>
            <div class="kpi"><span>S3</span><strong>{{ detail.overview.s3_stance_diversity.toFixed(2) }}</strong></div>
            <div class="kpi"><span>S4</span><strong>{{ detail.overview.s4_cognitive_coverage.toFixed(2) }}</strong></div>
            <div class="kpi cocoon"><span>Cocoon</span><strong>{{ detail.overview.cocoon_index.toFixed(2) }}</strong></div>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>判别量细节</template>
          <div class="derived-grid">
            <div class="derived-item">S1 熵比值：{{ (detail.derived.s1_entropy.ratio * 100).toFixed(1) }}%</div>
            <div class="derived-item">S2 alpha：{{ detail.derived.s2_cross.alpha.toFixed(3) }}</div>
            <div class="derived-item">S3 gini：{{ detail.derived.s3_gini.gini.toFixed(3) }}</div>
            <div class="derived-item">S4 overlap：{{ detail.derived.s4_overlap.overlap.toFixed(3) }}</div>
            <div class="derived-item">对齐度：{{ (detail.distributions.alignment * 100).toFixed(1) }}%</div>
            <div class="derived-item">Top2 主题：{{ detail.derived.s2_cross.top2.join(' / ') || '-' }}</div>
          </div>
        </el-card>

        <div class="dist-grid">
          <el-card shadow="never">
            <template #header>Topic 分布</template>
            <el-table :data="toRows(detail.distributions.topic)" size="small" stripe>
              <el-table-column prop="key" label="主题" />
              <el-table-column prop="value" label="占比">
                <template #default="{ row }">{{ (row.value * 100).toFixed(1) }}%</template>
              </el-table-column>
            </el-table>
          </el-card>
          <el-card shadow="never">
            <template #header>Benchmark 分布</template>
            <el-table :data="toRows(detail.distributions.benchmark)" size="small" stripe>
              <el-table-column prop="key" label="主题" />
              <el-table-column prop="value" label="占比">
                <template #default="{ row }">{{ (row.value * 100).toFixed(1) }}%</template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <el-card v-if="detail.suggestions.s2 || detail.suggestions.s4" shadow="never">
          <template #header>行动建议</template>
          <div v-if="detail.suggestions.s2" class="suggestion">
            <div class="s-title">S2（跨域）风险级别：{{ severityLabel(detail.suggestions.s2.severity) }}</div>
            <div>目标 S2：{{ detail.suggestions.s2.target_s2 }}，alpha {{ detail.suggestions.s2.alpha_now.toFixed(3) }} -> {{ detail.suggestions.s2.alpha_target.toFixed(3) }}</div>
          </div>
          <div v-if="detail.suggestions.s4" class="suggestion">
            <div class="s-title">S4（覆盖）风险级别：{{ severityLabel(detail.suggestions.s4.severity) }}</div>
            <div>目标 S4：{{ detail.suggestions.s4.target_s4 }}，overlap {{ detail.suggestions.s4.overlap_now.toFixed(3) }} -> {{ detail.suggestions.s4.overlap_target.toFixed(3) }}</div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { min-height: 100%; }
.card { background:#fff; border-radius:12px; padding:24px 28px; box-shadow:0 1px 3px rgba(15,23,42,.06); }
.head { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:14px; flex-wrap:wrap; }
.head-actions { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.title { margin:0; font-size:1.35rem; color:#0f172a; }
.error { margin:0 0 12px; color:#dc2626; }
.input-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px; }
.sections { display:flex; flex-direction:column; gap:12px; }
.kpi-grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; }
.kpi { border:1px solid #e5e7eb; border-radius:8px; padding:10px; display:flex; flex-direction:column; gap:6px; }
.kpi span { color:#64748b; font-size:12px; }
.kpi strong { color:#0f172a; font-size:20px; }
.kpi.cocoon strong { color:#8b5cf6; }
.derived-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; }
.derived-item { background:#f8fafc; border-radius:6px; padding:8px; color:#334155; font-size:13px; }
.dist-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.suggestion { padding:8px 0; color:#334155; }
.s-title { font-weight:700; margin-bottom:4px; color:#0f172a; }
</style>
