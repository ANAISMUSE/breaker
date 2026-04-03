<script setup lang="ts">
import { onMounted, ref } from 'vue'
import http from '@/api/http'

interface DashboardData {
  task_count: number
  device_count: number
  task_status_counts: Record<string, number>
  device_status_counts: Record<string, number>
  platform_counts: Record<string, number>
  recent_tasks: Array<Record<string, unknown>>
  recent_audits: Array<Record<string, unknown>>
}

const loading = ref(true)
const errorMsg = ref('')
const data = ref<DashboardData | null>(null)

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const resp = await http.get<DashboardData>('/api/analytics/dashboard')
    data.value = resp.data
  } catch {
    errorMsg.value = '加载总览失败'
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <h1 class="title">监控总览</h1>
        <el-button type="primary" plain :loading="loading" @click="load">刷新</el-button>
      </div>
      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <div v-if="data" class="stats">
        <el-statistic title="任务总数" :value="data.task_count" />
        <el-statistic title="设备总数" :value="data.device_count" />
      </div>

      <div v-if="data" class="grid">
        <div class="panel">
          <h3>任务状态分布</h3>
          <pre>{{ data.task_status_counts }}</pre>
        </div>
        <div class="panel">
          <h3>设备状态分布</h3>
          <pre>{{ data.device_status_counts }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card { background:#fff; border-radius:12px; padding:24px 28px; box-shadow:0 1px 3px rgba(15,23,42,.06);}
.head { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;}
.title { margin:0; font-size:1.35rem; color:#0f172a;}
.error { color:#dc2626; margin:0 0 12px;}
.stats { display:flex; gap:36px; margin-bottom:18px;}
.grid { display:grid; grid-template-columns:1fr 1fr; gap:16px;}
.panel { border:1px solid #e5e7eb; border-radius:10px; padding:12px; background:#fafafa;}
.panel h3 { margin:0 0 8px; font-size:1rem;}
.panel pre { margin:0; white-space:pre-wrap; color:#334155;}
</style>

