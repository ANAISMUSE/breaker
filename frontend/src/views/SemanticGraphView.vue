<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoRows } from '@/constants/demoData'

type DataRow = {
  topic?: string
  semantic_summary?: string
}

const rows = ref<DataRow[]>(demoRows as DataRow[])
const errorMsg = ref('')
const loading = ref(false)
const graphEl = ref<HTMLDivElement | null>(null)
let graphChart: echarts.ECharts | null = null

function normalizeTopic(value: unknown) {
  const s = String(value ?? '').trim().toLowerCase()
  return s || 'other'
}

function buildGraph(rowsInput: DataRow[]) {
  const topicCount = new Map<string, number>()
  const coCount = new Map<string, number>()

  for (const row of rowsInput) {
    const primary = normalizeTopic(row.topic)
    topicCount.set(primary, (topicCount.get(primary) ?? 0) + 1)
    const summary = String(row.semantic_summary ?? '').toLowerCase()
    const tags = [primary]
    if (summary.includes('科技')) tags.push('tech')
    if (summary.includes('教育')) tags.push('education')
    if (summary.includes('历史')) tags.push('history')
    if (summary.includes('社会')) tags.push('society')
    if (summary.includes('经济')) tags.push('economy')
    const uniq = Array.from(new Set(tags))
    for (const t of uniq) topicCount.set(t, (topicCount.get(t) ?? 0) + 1)
    for (let i = 0; i < uniq.length; i++) {
      for (let j = i + 1; j < uniq.length; j++) {
        const a = uniq[i]
        const b = uniq[j]
        const key = a < b ? `${a}|${b}` : `${b}|${a}`
        coCount.set(key, (coCount.get(key) ?? 0) + 1)
      }
    }
  }

  const nodes = Array.from(topicCount.entries()).map(([name, value]) => ({
    id: name,
    name,
    value,
    symbolSize: Math.min(50, 14 + value * 2),
  }))
  const links = Array.from(coCount.entries()).map(([key, value]) => {
    const [source, target] = key.split('|')
    return { source, target, value, lineStyle: { width: Math.min(6, 1 + value) } }
  })
  return { nodes, links }
}

async function renderGraph() {
  await nextTick()
  if (!graphEl.value) return
  graphChart = graphChart ?? echarts.init(graphEl.value)
  const { nodes, links } = buildGraph(rows.value)
  graphChart.setOption({
    title: { text: '语义关联图谱（Topic + Semantic Tags）', left: 'center' },
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        force: { repulsion: 220, edgeLength: [60, 150] },
        data: nodes,
        links,
        label: { show: true },
      },
    ],
  })
}

async function onImportedRows(records: Record<string, unknown>[]) {
  rows.value = records as DataRow[]
  errorMsg.value = ''
  await renderGraph()
}

function onImportError(message: string) {
  errorMsg.value = message
}

async function onUseDemo() {
  loading.value = true
  try {
    rows.value = demoRows as DataRow[]
    await renderGraph()
    ElMessage.success('已加载演示数据')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  renderGraph()
  window.addEventListener('resize', () => graphChart?.resize())
})

onBeforeUnmount(() => {
  graphChart?.dispose()
  graphChart = null
})
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">语义关联图谱</h1>
        <el-button :loading="loading" @click="onUseDemo">使用演示数据</el-button>
      </div>
      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
      <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
      <div ref="graphEl" class="graph" />
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.title {
  margin: 0;
}
.error {
  color: #dc2626;
}
.graph {
  margin-top: 16px;
  height: 640px;
}
</style>
