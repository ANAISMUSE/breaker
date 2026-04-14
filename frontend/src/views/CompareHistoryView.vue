<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '@/api/http'

interface StrategyBlock {
  cocoon_start: number
  cocoon_end: number
  drop: number
  series: number[]
}

interface CompareResult {
  result?: Record<string, StrategyBlock | { name: string; drop: number; static_cocoon: number }>
  trend_option?: Record<string, unknown>
}

interface CompareHistoryRecord {
  record_id: string
  user_id: string
  rounds: number
  benchmark: Record<string, number>
  result: CompareResult
  rows?: Array<Record<string, unknown>>
  created_at: string
}

interface ReplayPayload {
  rows: Array<Record<string, unknown>>
  benchmark: Record<string, number>
  rounds: number
}

const REPLAY_KEY = 'compare.replay.payload'

const router = useRouter()
const loading = ref(false)
const records = ref<CompareHistoryRecord[]>([])
const userFilter = ref('')
const bestStrategyFilter = ref('all')

const filteredRecords = computed(() => {
  return records.value.filter((row) => {
    const byUser = userFilter.value.trim()
      ? row.user_id.toLowerCase().includes(userFilter.value.trim().toLowerCase())
      : true
    const bestName = (row.result?.result?._best as { name?: string } | undefined)?.name ?? ''
    const byBest = bestStrategyFilter.value === 'all' ? true : bestName === bestStrategyFilter.value
    return byUser && byBest
  })
})

function bestName(row: CompareHistoryRecord) {
  const best = row.result?.result?._best as { name?: string } | undefined
  return best?.name ?? '-'
}

function bestDrop(row: CompareHistoryRecord) {
  const best = row.result?.result?._best as { drop?: number } | undefined
  return typeof best?.drop === 'number' ? best.drop.toFixed(3) : '-'
}

async function loadRecords() {
  loading.value = true
  try {
    const { data } = await http.get<CompareHistoryRecord[]>('/api/simulation/records', { params: { limit: 100 } })
    records.value = Array.isArray(data) ? data : []
  } catch {
    records.value = []
    ElMessage.error('加载对比历史失败')
  } finally {
    loading.value = false
  }
}

function replay(row: CompareHistoryRecord) {
  if (!Array.isArray(row.rows) || row.rows.length === 0) {
    ElMessage.warning('该记录未包含 rows，暂不可回放')
    return
  }
  const payload: ReplayPayload = {
    rows: row.rows,
    benchmark: row.benchmark ?? {},
    rounds: Number(row.rounds || 10),
  }
  localStorage.setItem(REPLAY_KEY, JSON.stringify(payload))
  router.push('/app/analytics/compare')
}

onMounted(loadRecords)
</script>

<template>
  <div class="card">
    <div class="head">
      <div>
        <h1 class="title">平台对比历史记录</h1>
        <p class="subtitle">支持筛选并一键回放到「平台对比」页，复现实验结论。</p>
      </div>
      <el-button :loading="loading" @click="loadRecords">刷新</el-button>
    </div>

    <div class="filters">
      <el-input v-model="userFilter" placeholder="按用户ID筛选" clearable style="max-width: 220px" />
      <el-select v-model="bestStrategyFilter" style="width: 220px">
        <el-option label="全部最优策略" value="all" />
        <el-option label="baseline" value="baseline" />
        <el-option label="aggressive" value="aggressive" />
        <el-option label="ladder" value="ladder" />
        <el-option label="mixed" value="mixed" />
      </el-select>
      <span class="count">记录数：{{ filteredRecords.length }}</span>
    </div>

    <el-table v-loading="loading" :data="filteredRecords" stripe empty-text="暂无对比历史记录">
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
      <el-table-column prop="user_id" label="用户ID" min-width="140" />
      <el-table-column prop="rounds" label="轮次" min-width="80" />
      <el-table-column label="最优策略" min-width="120">
        <template #default="{ row }">{{ bestName(row) }}</template>
      </el-table-column>
      <el-table-column label="改善Δ" min-width="100">
        <template #default="{ row }">{{ bestDrop(row) }}</template>
      </el-table-column>
      <el-table-column prop="record_id" label="记录ID" min-width="240" show-overflow-tooltip />
      <el-table-column label="操作" min-width="120">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="replay(row)">回放</el-button>
        </template>
      </el-table-column>
    </el-table>
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
  gap: 12px;
  flex-wrap: wrap;
}
.title {
  margin: 0;
  color: #0f172a;
  font-size: 1.35rem;
}
.subtitle {
  margin: 8px 0 0;
  font-size: 13px;
  color: #64748b;
}
.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 16px 0 12px;
}
.count {
  font-size: 13px;
  color: #475569;
}
</style>
