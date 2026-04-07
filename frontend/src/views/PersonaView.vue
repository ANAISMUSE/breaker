<script setup lang="ts">
import { ref } from 'vue'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import PersonaTwinPreview, { type TwinBuildPayload } from '@/components/PersonaTwinPreview.vue'
import { demoRows } from '@/constants/demoData'
import { personaPresets } from '@/constants/personaPresets'

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const resultText = ref('')
const twinData = ref<TwinBuildPayload | null>(null)
const rightMode = ref<'visual' | 'json'>('visual')

function onImportedRows(rows: Record<string, unknown>[]) {
  errorMsg.value = ''
  rowsText.value = JSON.stringify(rows, null, 2)
}

function onImportError(message: string) {
  errorMsg.value = message
}

function applyPreset(rows: Record<string, unknown>[]) {
  errorMsg.value = ''
  rowsText.value = JSON.stringify(rows, null, 2)
}

async function build() {
  loading.value = true
  errorMsg.value = ''
  try {
    const rows = JSON.parse(rowsText.value) as Array<Record<string, unknown>>
    const { data } = await http.post<TwinBuildPayload>('/api/persona/build', { rows })
    twinData.value = data
    resultText.value = JSON.stringify(data, null, 2)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '构建失败'
    twinData.value = null
    resultText.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card">
    <div class="head">
      <div class="head-left">
        <h1 class="title">人设数据库</h1>
        <p class="subtitle">
          左侧为<strong>行为行数据</strong>（JSON 数组，与采集/导出字段对齐）；点击构建后，右侧为孪生画像结果——底层仍是 JSON，默认可视化展示；也可切换查看原始 JSON。
          若行内包含字段 <code>persona_preset</code>（如 <code>elderly</code> / <code>youth</code> / <code>child</code>
          / <code>explore_heavy</code>），会与智能体动作打分联动，便于做信息茧房对比实验。
        </p>
      </div>
      <div class="head-actions">
        <RowsFileImport format="auto" @imported="onImportedRows" @error="onImportError" />
        <el-button type="primary" :loading="loading" @click="build">构建并预览孪生画像</el-button>
      </div>
    </div>

    <div class="preset-bar">
      <span class="preset-title">预设人设（写入 JSON，含模拟特质）</span>
      <div class="preset-btns">
        <el-tooltip v-for="p in personaPresets" :key="p.id" :content="p.blurb" placement="top">
          <el-button size="small" @click="applyPreset(p.rows)">{{ p.label }}</el-button>
        </el-tooltip>
      </div>
    </div>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div class="cols-labels">
      <span>输入 rows</span>
      <span class="right-head">
        孪生画像输出
        <el-radio-group v-model="rightMode" size="small" class="mode-switch">
          <el-radio-button label="visual">可视化</el-radio-button>
          <el-radio-button label="json">原始 JSON</el-radio-button>
        </el-radio-group>
      </span>
    </div>
    <div class="grid">
      <el-input v-model="rowsText" type="textarea" :rows="14" class="left-ta" />
      <PersonaTwinPreview :data="twinData" :raw-json="resultText" :view-mode="rightMode" />
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px 28px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 16px;
  flex-wrap: wrap;
}
.head-left {
  flex: 1;
  min-width: 240px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.title {
  margin: 0 0 8px;
  font-size: 1.35rem;
  color: #0f172a;
}
.subtitle {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #64748b;
  max-width: 720px;
}
.subtitle code {
  font-size: 12px;
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
}
.preset-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  margin-bottom: 14px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}
.preset-title {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}
.preset-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.error {
  color: #dc2626;
  margin: 0 0 12px;
}
.cols-labels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #64748b;
}
.right-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.mode-switch {
  flex-shrink: 0;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: start;
}
.left-ta :deep(textarea) {
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .cols-labels {
    grid-template-columns: 1fr;
  }
}
</style>
