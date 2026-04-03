<script setup lang="ts">
import { ref } from 'vue'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoBenchmark, demoRows } from '@/constants/demoData'

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const benchmarkText = ref(JSON.stringify(demoBenchmark, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const planText = ref('')
const reportPath = ref('')

function onImportedRows(rows: Record<string, unknown>[]) {
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
</style>

