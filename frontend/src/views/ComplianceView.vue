<script setup lang="ts">
import { onMounted, ref } from 'vue'
import http from '@/api/http'

const audits = ref<Array<Record<string, unknown>>>([])
const loading = ref(true)
const wiping = ref(false)
const policySaving = ref(false)
const autoCleaning = ref(false)
const errorMsg = ref('')
const wipeForm = ref({ vector_store: true, uploads: true, tasks: true })
const policyForm = ref({ auto_cleanup_enabled: false, retention_hours: 24 })
const evidencePath = ref('')

async function loadAudits() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await http.get<Array<Record<string, unknown>>>('/api/compliance/audit?limit=200')
    audits.value = Array.isArray(data) ? data : []
  } catch {
    errorMsg.value = '加载审计日志失败'
    audits.value = []
  } finally {
    loading.value = false
  }
}

async function loadPolicy() {
  try {
    const { data } = await http.get<{ auto_cleanup_enabled: boolean; retention_hours: number }>('/api/compliance/policy')
    policyForm.value = {
      auto_cleanup_enabled: Boolean(data.auto_cleanup_enabled),
      retention_hours: Number(data.retention_hours || 24),
    }
  } catch {
    // keep default policy form
  }
}

async function wipeData() {
  wiping.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/compliance/wipe', wipeForm.value)
    await loadAudits()
  } catch {
    errorMsg.value = '清理失败'
  } finally {
    wiping.value = false
  }
}

async function savePolicy() {
  policySaving.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/compliance/policy', policyForm.value)
    await loadAudits()
  } catch {
    errorMsg.value = '保存自动清理策略失败'
  } finally {
    policySaving.value = false
  }
}

async function runAutoCleanup() {
  autoCleaning.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/compliance/auto-cleanup')
    await loadAudits()
  } catch {
    errorMsg.value = '自动清理执行失败'
  } finally {
    autoCleaning.value = false
  }
}

async function exportEvidence() {
  errorMsg.value = ''
  try {
    const { data } = await http.get<{ path: string }>('/api/compliance/evidence?limit=300')
    evidencePath.value = data.path
    await loadAudits()
  } catch {
    errorMsg.value = '导出合规证据失败'
  }
}

onMounted(async () => {
  await Promise.all([loadAudits(), loadPolicy()])
})
</script>

<template>
  <div class="card">
    <div class="head">
      <h1 class="title">合规与审计</h1>
      <el-button type="primary" plain :loading="loading" @click="loadAudits">刷新日志</el-button>
    </div>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div class="wipe">
      <el-checkbox v-model="wipeForm.vector_store">清理向量库</el-checkbox>
      <el-checkbox v-model="wipeForm.uploads">清理上传缓存</el-checkbox>
      <el-checkbox v-model="wipeForm.tasks">清理任务记录</el-checkbox>
      <el-button type="danger" :loading="wiping" @click="wipeData">执行一键清理</el-button>
    </div>

    <div class="policy">
      <el-checkbox v-model="policyForm.auto_cleanup_enabled">启用自动清理</el-checkbox>
      <span class="lb">保留时长（小时）</span>
      <el-input-number v-model="policyForm.retention_hours" :min="1" :max="720" />
      <el-button :loading="policySaving" @click="savePolicy">保存策略</el-button>
      <el-button :loading="autoCleaning" @click="runAutoCleanup">立即执行自动清理</el-button>
      <el-button @click="exportEvidence">导出合规证据</el-button>
    </div>
    <p v-if="evidencePath" class="path">证据已导出：{{ evidencePath }}</p>

    <el-table v-loading="loading" :data="audits" stripe empty-text="暂无审计日志" style="width: 100%">
      <el-table-column prop="ts" label="时间" min-width="180" />
      <el-table-column prop="event" label="事件" min-width="180" />
      <el-table-column label="详情" min-width="360">
        <template #default="{ row }">
          <pre class="detail">{{ JSON.stringify(row.detail || {}, null, 2) }}</pre>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.card { background:#fff; border-radius:12px; padding:24px 28px; box-shadow:0 1px 3px rgba(15,23,42,.06);}
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;}
.title { margin:0; font-size:1.35rem; color:#0f172a;}
.error { color:#dc2626; margin:0 0 12px;}
.wipe { display:flex; align-items:center; gap:16px; margin:0 0 14px; flex-wrap:wrap;}
.policy { display:flex; align-items:center; gap:12px; margin:0 0 12px; flex-wrap:wrap;}
.lb { color:#475569; font-size:13px; }
.path { margin:0 0 12px; color:#16a34a; font-size:13px; }
.detail { margin:0; white-space:pre-wrap; color:#334155; font-size:.8rem;}
</style>

