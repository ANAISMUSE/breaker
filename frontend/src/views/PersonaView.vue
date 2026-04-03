<script setup lang="ts">
import { ref } from 'vue'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import { demoRows } from '@/constants/demoData'

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const resultText = ref('')

function onImportedRows(rows: Record<string, unknown>[]) {
  errorMsg.value = ''
  rowsText.value = JSON.stringify(rows, null, 2)
}

function onImportError(message: string) {
  errorMsg.value = message
}

async function build() {
  loading.value = true
  errorMsg.value = ''
  try {
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const { data } = await http.post('/api/persona/build', { rows })
    resultText.value = JSON.stringify(data, null, 2)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '构建失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card">
    <div class="head">
      <h1 class="title">人设数据库</h1>
      <div class="head-actions">
        <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
        <el-button type="primary" :loading="loading" @click="build">构建并预览孪生画像</el-button>
      </div>
    </div>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
    <div class="grid">
      <el-input v-model="rowsText" type="textarea" :rows="12" />
      <el-input :model-value="resultText" type="textarea" :rows="12" readonly />
    </div>
  </div>
</template>

<style scoped>
.card { background:#fff; border-radius:12px; padding:24px 28px; box-shadow:0 1px 3px rgba(15,23,42,.06);}
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; gap:12px; flex-wrap:wrap;}
.head-actions { display:flex; align-items:center; gap:10px; flex-wrap:wrap;}
.title { margin:0; font-size:1.35rem; color:#0f172a;}
.error { color:#dc2626; margin:0 0 12px;}
.grid { display:grid; grid-template-columns:1fr 1fr; gap:12px;}
</style>

