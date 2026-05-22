<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

const isDevMode = import.meta.env.DEV || String(import.meta.env.VITE_DEV_MODE || '').toLowerCase() === 'true'
const rowsText = ref(JSON.stringify(demoRows, null, 2))
const benchmarkText = ref(JSON.stringify(demoBenchmark, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const workbenchProgress = ref(0)
const workbenchStepLabel = ref('')

const dataReady = computed(() => {
  try {
    const r = JSON.parse(rowsText.value)
    return Array.isArray(r) && r.length > 0
  } catch {
    return false
  }
})
const planText = ref('')
const reportPath = ref('')
const trainingTopic = ref('AI是否应该取代部分人类工作')
const trainingPro = ref('支持：提升效率、降低重复劳动成本、释放创造力。')
const trainingCon = ref('反对：岗位替代与技能断层风险，伦理责任归属不清。')
const trainingId = ref('')
const trainingSummary = ref('')
const trainingReflection = ref('')
const trainingScore = ref<number | null>(null)
const trainingFeedback = ref('')
const trainingEvidence = ref<string[]>([])
const trainingMessage = ref('')
const trainingRecords = ref<Array<Record<string, unknown>>>([])
const llmHealthText = ref('')
const phase5Workdir = ref('outputs/phase5_ui')
const phase5BaselineModel = ref('Qwen/Qwen2.5-7B-Instruct')
const phase5LoraModel = ref('outputs/phase5_ui/adapter')
const phase5SkipTrain = ref(true)
const phase5ResultText = ref('')

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
  workbenchProgress.value = 0
  workbenchStepLabel.value = '正在分析用户数据特征…'
  try {
    const steps = [
      { label: '正在分析用户数据特征…', pct: 20 },
      { label: '正在匹配破茧策略…', pct: 45 },
      { label: '正在生成阶梯执行计划…', pct: 70 },
    ]
    for (const step of steps) {
      workbenchStepLabel.value = step.label
      workbenchProgress.value = step.pct
      await new Promise((r) => setTimeout(r, 300))
    }
    workbenchStepLabel.value = '正在获取计划结果…'
    workbenchProgress.value = 88
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const benchmark = JSON.parse(benchmarkText.value) as Record<string, number>
    const { data } = await http.post('/api/workbench/plan', { rows, benchmark })
    planText.value = JSON.stringify(data, null, 2)
    workbenchProgress.value = 100
    workbenchStepLabel.value = '计划生成完成'
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '生成计划失败'
  } finally {
    loading.value = false
    setTimeout(() => { workbenchProgress.value = 0; workbenchStepLabel.value = '' }, 1500)
  }
}

async function exportReport() {
  loading.value = true
  errorMsg.value = ''
  workbenchProgress.value = 0
  workbenchStepLabel.value = '正在汇总评估数据…'
  try {
    const steps = [
      { label: '正在汇总评估数据…', pct: 25 },
      { label: '正在生成 Word 文档…', pct: 55 },
      { label: '正在保存报告文件…', pct: 80 },
    ]
    for (const step of steps) {
      workbenchStepLabel.value = step.label
      workbenchProgress.value = step.pct
      await new Promise((r) => setTimeout(r, 300))
    }
    workbenchProgress.value = 90
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const benchmark = JSON.parse(benchmarkText.value) as Record<string, number>
    const { data } = await http.post<{ path: string }>('/api/workbench/report', { rows, benchmark })
    reportPath.value = data.path
    workbenchProgress.value = 100
    workbenchStepLabel.value = '报告导出完成'
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '导出报告失败'
  } finally {
    loading.value = false
    setTimeout(() => { workbenchProgress.value = 0; workbenchStepLabel.value = '' }, 1500)
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
    const { data } = await http.post<{ score: number; feedback?: string; evidence?: string[] }>(
      `/api/workbench/training/${trainingId.value}/submit`,
      {
        summary: trainingSummary.value,
        reflection: trainingReflection.value,
      },
    )
    trainingScore.value = Number(data.score ?? 0)
    trainingFeedback.value = String(data.feedback ?? '')
    trainingEvidence.value = Array.isArray(data.evidence) ? data.evidence.map((x) => String(x)) : []
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

async function sendTrainingMessage() {
  if (!trainingId.value || !trainingMessage.value.trim()) {
    return
  }
  loading.value = true
  try {
    await http.post(`/api/workbench/training/${trainingId.value}/message`, {
      role: 'user',
      content: trainingMessage.value.trim(),
    })
    trainingMessage.value = ''
    await loadTrainingRecords()
  } finally {
    loading.value = false
  }
}

async function checkLlmHealth() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get('/api/llm/health')
    llmHealthText.value = JSON.stringify(data, null, 2)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : 'LLM 健康检查失败'
  } finally {
    loading.value = false
  }
}

async function runPhase5FromBrowser() {
  loading.value = true
  errorMsg.value = ''
  try {
    const sourceRows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const { data } = await http.post('/api/workbench/phase5/run', {
      source_rows: sourceRows,
      workdir: phase5Workdir.value,
      baseline_model: phase5BaselineModel.value,
      lora_model: phase5LoraModel.value,
      skip_train: phase5SkipTrain.value,
    })
    phase5ResultText.value = JSON.stringify(data, null, 2)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : 'Phase5 闭环运行失败'
  } finally {
    loading.value = false
  }
}

function trainingScoreTrend() {
  return trainingRecords.value
    .slice()
    .reverse()
    .map((x) => Number(x.score ?? 0))
    .filter((x) => Number.isFinite(x))
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

    <!-- 进度条 -->
    <div v-if="loading && workbenchProgress > 0" class="progress-card">
      <el-progress :percentage="workbenchProgress" :stroke-width="14" :format="(p: number) => `${p}%`" />
      <div class="step-label">{{ workbenchStepLabel }}</div>
    </div>

    <div class="toolbar">
      <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
      <el-button :loading="loading" @click="genPlan">生成阶梯计划</el-button>
      <el-button type="primary" :loading="loading" @click="exportReport">导出 Word 报告</el-button>
      <span v-if="dataReady" class="data-ready-badge">数据已就绪</span>
    </div>

    <!-- 计划结果 -->
    <div v-if="planText" class="plan-result">
      <div class="plan-title">阶梯执行计划</div>
      <pre class="plan-pre">{{ planText }}</pre>
    </div>

    <!-- 高级调试区域（折叠） -->
    <details class="json-details">
      <summary>高级 / 调试数据</summary>
      <div class="grid3">
        <el-input v-model="rowsText" type="textarea" :rows="8" placeholder="rows 数据（JSON 数组）" />
        <el-input v-model="benchmarkText" type="textarea" :rows="8" placeholder="benchmark 数据（JSON 对象）" />
        <el-input :model-value="planText" type="textarea" :rows="8" readonly placeholder="计划输出" />
      </div>
    </details>

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
      <p v-if="trainingFeedback" class="feedback">LLM评语：{{ trainingFeedback }}</p>
      <ul v-if="trainingEvidence.length" class="evidence">
        <li v-for="(item, idx) in trainingEvidence" :key="idx">{{ item }}</li>
      </ul>
      <div class="actions">
        <el-input v-model="trainingMessage" placeholder="继续追问：请给我下一步训练建议" />
        <el-button :loading="loading" @click="sendTrainingMessage">发送训练消息</el-button>
      </div>
      <el-table :data="trainingRecords" size="small" stripe empty-text="暂无训练记录">
        <el-table-column prop="updated_at" label="时间" min-width="160" />
        <el-table-column prop="topic" label="议题" min-width="220" />
        <el-table-column prop="score" label="得分" width="90" />
        <el-table-column prop="status" label="状态" width="100" />
      </el-table>
      <div class="trend-box">
        <div class="trend-title">训练得分趋势</div>
        <div class="trend-line">
          <div
            v-for="(s, idx) in trainingScoreTrend()"
            :key="idx"
            class="trend-point"
            :style="{ height: `${Math.max(8, s * 36)}px` }"
            :title="`score=${s.toFixed(2)}`"
          />
        </div>
      </div>
    </div>

    <div v-if="isDevMode" class="training phase5-panel">
      <h3>Phase5 LoRA 闭环（浏览器直接调用 API）</h3>
      <div class="actions">
        <el-button :loading="loading" @click="checkLlmHealth">检查 LLM 健康</el-button>
        <el-button type="primary" :loading="loading" @click="runPhase5FromBrowser">运行 Phase5 闭环</el-button>
      </div>
      <div class="training-grid">
        <el-input v-model="phase5Workdir" placeholder="workdir，例如 outputs/phase5_ui" />
        <el-input v-model="phase5BaselineModel" placeholder="baseline model" />
        <el-input v-model="phase5LoraModel" placeholder="lora model / adapter path" />
      </div>
      <div class="actions">
        <el-checkbox v-model="phase5SkipTrain">跳过训练（仅联调预测与评估）</el-checkbox>
      </div>
      <div class="grid2">
        <el-input :model-value="llmHealthText" type="textarea" :rows="8" readonly placeholder="LLM health 输出" />
        <el-input :model-value="phase5ResultText" type="textarea" :rows="8" readonly placeholder="Phase5 运行结果输出" />
      </div>
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
.feedback { margin: 8px 0; color:#334155; }
.evidence { margin: 6px 0 8px 16px; color:#475569; }
.trend-box { margin-top: 10px; }
.trend-title { font-size: 12px; color:#64748b; margin-bottom: 6px; }
.trend-line { display:flex; align-items:flex-end; gap:6px; min-height:44px; padding:6px; background:#fff; border:1px solid #e2e8f0; border-radius:8px; }
.trend-point { width:10px; background:#60a5fa; border-radius:4px 4px 0 0; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px; }
.phase5-panel { margin-top:18px; }

.progress-card {
  margin-bottom: 14px;
  padding: 16px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.step-label {
  margin-top: 8px;
  font-size: 0.88rem;
  color: #475569;
  text-align: center;
}

.data-ready-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  background: #dcfce7;
  color: #166534;
  font-size: 12px;
  font-weight: 600;
}

.json-details {
  margin-top: 12px;
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

.plan-result {
  margin-top: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  background: #f8fafc;
}

.plan-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 8px;
}

.plan-pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  color: #334155;
}
</style>

