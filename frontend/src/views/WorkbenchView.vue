<script setup lang="ts">
import { onMounted, ref } from 'vue'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const benchmarkText = ref(JSON.stringify(demoBenchmark, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const planText = ref('')
const reportPath = ref('')
const trainingTopic = ref('AI是否应该取代部分人类工作')
const trainingPro = ref('支持：提升效率、降低重复劳动成本、释放创造力。')
const trainingCon = ref('反对：岗位替代与技能断层风险，伦理责任归属不清。')
const trainingId = ref('')
const trainingSummary = ref('')
const trainingReflection = ref('')
const trainingScore = ref<number | null>(null)
const trainingRecords = ref<Array<Record<string, unknown>>>([])

function onImportedRows(
  rows: Record<string, unknown>[],
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
  rowsText.value = JSON.stringify(rows, null, 2)
}

function onImportError(message: string) {
  errorMsg.value = message
}

async function genPlan() {
  loading.value = true
  errorMsg.value = ''
  try {
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const benchmark = JSON.parse(benchmarkText.value) as Record<string, number>
    const { data } = await http.post('/api/workbench/plan', { rows, benchmark })
    planText.value = JSON.stringify(data, null, 2)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '生成计划失败'
  } finally {
    loading.value = false
  }
}

async function exportReport() {
  loading.value = true
  errorMsg.value = ''
  try {
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const benchmark = JSON.parse(benchmarkText.value) as Record<string, number>
    const { data } = await http.post<{ path: string }>('/api/workbench/report', { rows, benchmark })
    reportPath.value = data.path
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '导出报告失败'
  } finally {
    loading.value = false
  }
}

async function startTraining() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.post<{
      training_id: string
    }>('/api/workbench/training/start', {
      topic: trainingTopic.value,
      pro_view: trainingPro.value,
      con_view: trainingCon.value,
    })
    trainingId.value = data.training_id
    trainingScore.value = null
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '启动认知训练失败'
  } finally {
    loading.value = false
  }
}

async function submitTraining() {
  if (!trainingId.value) {
    errorMsg.value = '请先启动训练任务'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.post<{ score: number }>(`/api/workbench/training/${trainingId.value}/submit`, {
      summary: trainingSummary.value,
      reflection: trainingReflection.value,
    })
    trainingScore.value = Number(data.score ?? 0)
    await loadTrainingRecords()
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '提交训练结果失败'
  } finally {
    loading.value = false
  }
}

async function loadTrainingRecords() {
  try {
    const { data } = await http.get<Array<Record<string, unknown>>>('/api/workbench/training/records?limit=20')
    trainingRecords.value = Array.isArray(data) ? data : []
  } catch {
    trainingRecords.value = []
  }
}

onMounted(loadTrainingRecords)
</script>

<template>
  <div class="card">
    <div class="head">
      <h1 class="title">算法工作台</h1>
      <div class="actions">
        <el-button :loading="loading" @click="genPlan">生成阶梯计划</el-button>
        <el-button type="primary" :loading="loading" @click="exportReport">导出 Word 报告</el-button>
      </div>
    </div>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
    <p v-if="reportPath" class="ok">报告已生成：{{ reportPath }}</p>
    <div class="toolbar">
      <span class="tb-label">rows</span>
      <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
    </div>
    <div class="grid3">
      <el-input v-model="rowsText" type="textarea" :rows="10" />
      <el-input v-model="benchmarkText" type="textarea" :rows="10" />
      <el-input :model-value="planText" type="textarea" :rows="10" readonly />
    </div>

    <div class="training">
      <h3>认知灵活性训练（最小闭环）</h3>
      <div class="training-grid">
        <el-input v-model="trainingTopic" placeholder="训练议题" />
        <el-input v-model="trainingPro" placeholder="正方观点" />
        <el-input v-model="trainingCon" placeholder="反方观点" />
      </div>
      <div class="actions">
        <el-button :loading="loading" @click="startTraining">启动训练</el-button>
        <span v-if="trainingId">训练ID：{{ trainingId }}</span>
      </div>
      <el-input v-model="trainingSummary" type="textarea" :rows="4" placeholder="请写出你对双方观点的综合总结" />
      <el-input v-model="trainingReflection" type="textarea" :rows="3" placeholder="反思：这次训练改变了你什么看法？" />
      <div class="actions">
        <el-button type="primary" :loading="loading" @click="submitTraining">提交训练反馈</el-button>
        <span v-if="trainingScore !== null">训练得分：{{ trainingScore.toFixed(2) }}</span>
        <el-button plain @click="loadTrainingRecords">刷新训练记录</el-button>
      </div>
      <el-table :data="trainingRecords" size="small" stripe empty-text="暂无训练记录">
        <el-table-column prop="updated_at" label="时间" min-width="160" />
        <el-table-column prop="topic" label="议题" min-width="220" />
        <el-table-column prop="score" label="得分" width="90" />
        <el-table-column prop="status" label="状态" width="100" />
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.card { background:#fff; border-radius:12px; padding:24px 28px; box-shadow:0 1px 3px rgba(15,23,42,.06);}
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; gap:12px;}
.title { margin:0; font-size:1.35rem; color:#0f172a;}
.actions { display:flex; gap:10px;}
.error { color:#dc2626; margin:0 0 10px;}
.ok { color:#16a34a; margin:0 0 10px;}
.grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;}
.toolbar { display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap;}
.tb-label { font-size:13px; color:#334155;}
.training { margin-top:16px; border:1px solid #e5e7eb; border-radius:10px; padding:12px; background:#f8fafc;}
.training-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:8px;}
</style>

