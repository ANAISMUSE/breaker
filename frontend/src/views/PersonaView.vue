<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'
import RowsFileImport from '@/components/RowsFileImport.vue'
import PersonaTwinPreview, { type TwinBuildPayload } from '@/components/PersonaTwinPreview.vue'
import { demoRows } from '@/constants/demoData'
import { personaPresets } from '@/constants/personaPresets'

interface PersonaRecord {
  profile_id: string
  user_id: string
  created_at: string
  profile: Record<string, unknown>
}

const rowsText = ref(JSON.stringify(demoRows, null, 2))
const loading = ref(false)
const errorMsg = ref('')
const resultText = ref('')
const twinData = ref<TwinBuildPayload | null>(null)
const rightMode = ref<'visual' | 'json'>('visual')
const records = ref<PersonaRecord[]>([])
const recordsLoading = ref(false)
const previewingRecordId = ref('')

const createVisible = ref(false)
const createUserId = ref('unknown')
const createProfileText = ref('{}')
const creatingProfile = ref(false)

const editVisible = ref(false)
const editingRecordId = ref('')
const editUserId = ref('')
const editProfileText = ref('{}')
const savingEdit = ref(false)

function isTwinBuildPayload(v: unknown): v is TwinBuildPayload {
  if (!v || typeof v !== 'object' || Array.isArray(v)) {
    return false
  }
  const obj = v as Record<string, unknown>
  return (
    'interest' in obj &&
    'behavior' in obj &&
    'cognitive' in obj &&
    'memory_count' in obj &&
    'memory_preview' in obj
  )
}

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
    const { data } = await http.post<{
      profile_id: string
      user_id: string
      created_at: string
      profile: TwinBuildPayload
    }>('/api/persona/build', { rows })
    twinData.value = data.profile
    resultText.value = JSON.stringify(data.profile, null, 2)
    ElMessage.success('人设画像已生成并入库')
    await loadRecords()
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '构建失败'
    twinData.value = null
    resultText.value = ''
  } finally {
    loading.value = false
  }
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const { data } = await http.get<PersonaRecord[]>('/api/persona/profiles', { params: { limit: 100 } })
    records.value = Array.isArray(data) ? data : []
  } catch {
    records.value = []
  } finally {
    recordsLoading.value = false
  }
}

function openCreate() {
  createUserId.value = 'unknown'
  createProfileText.value = '{}'
  createVisible.value = true
}

async function createRecord() {
  let parsed: Record<string, unknown> = {}
  try {
    const raw = JSON.parse(createProfileText.value || '{}') as unknown
    parsed = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {}
  } catch {
    errorMsg.value = 'profile JSON 解析失败'
    return
  }

  creatingProfile.value = true
  errorMsg.value = ''
  try {
    await http.post('/api/persona/profiles', {
      user_id: createUserId.value.trim() || 'unknown',
      profile: parsed,
    })
    createVisible.value = false
    ElMessage.success('人设记录已创建')
    await loadRecords()
  } catch {
    errorMsg.value = '创建人设失败'
  } finally {
    creatingProfile.value = false
  }
}

function openEdit(row: PersonaRecord) {
  editingRecordId.value = row.profile_id
  editUserId.value = row.user_id
  editProfileText.value = JSON.stringify(row.profile ?? {}, null, 2)
  editVisible.value = true
}

async function saveEdit() {
  if (!editingRecordId.value) return
  let parsed: Record<string, unknown> = {}
  try {
    const raw = JSON.parse(editProfileText.value || '{}') as unknown
    parsed = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {}
  } catch {
    errorMsg.value = 'profile JSON 解析失败'
    return
  }
  savingEdit.value = true
  errorMsg.value = ''
  try {
    await http.patch(`/api/persona/profiles/${editingRecordId.value}`, {
      user_id: editUserId.value.trim() || 'unknown',
      profile: parsed,
    })
    editVisible.value = false
    ElMessage.success('人设记录已更新')
    await loadRecords()
  } catch {
    errorMsg.value = '更新人设失败'
  } finally {
    savingEdit.value = false
  }
}

async function removeRecord(row: PersonaRecord) {
  try {
    await ElMessageBox.confirm('确认删除该人设记录吗？', '删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await http.delete(`/api/persona/profiles/${row.profile_id}`)
    ElMessage.success('人设记录已删除')
    await loadRecords()
  } catch {
    errorMsg.value = '删除人设失败'
  }
}

async function previewRecord(row: PersonaRecord) {
  previewingRecordId.value = row.profile_id
  errorMsg.value = ''
  try {
    const { data } = await http.get<PersonaRecord>(`/api/persona/profiles/${row.profile_id}`)
    twinData.value = isTwinBuildPayload(data.profile) ? data.profile : null
    resultText.value = JSON.stringify(data.profile ?? {}, null, 2)
    rightMode.value = 'visual'
  } catch {
    errorMsg.value = '加载人设详情失败'
  } finally {
    previewingRecordId.value = ''
  }
}

onMounted(loadRecords)
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

    <div class="records">
      <div class="records-head">
        <div class="records-title">人设记录库（CRUD）</div>
        <div class="records-actions">
          <el-button size="small" type="primary" @click="openCreate">新建记录</el-button>
          <el-button size="small" :loading="recordsLoading" @click="loadRecords">刷新</el-button>
        </div>
      </div>
      <el-table v-loading="recordsLoading" :data="records" stripe empty-text="暂无人设记录" style="width: 100%">
        <el-table-column prop="user_id" label="用户ID" min-width="140" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column prop="profile_id" label="记录ID" min-width="240" show-overflow-tooltip />
        <el-table-column label="操作" min-width="260">
          <template #default="{ row }">
            <div class="row-ops">
              <el-button size="small" :loading="previewingRecordId === row.profile_id" @click="previewRecord(row)">
                预览
              </el-button>
              <el-button size="small" type="primary" plain @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="removeRecord(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>

  <el-dialog v-model="createVisible" title="新建人设记录" width="60%">
    <el-form label-width="90px">
      <el-form-item label="用户ID">
        <el-input v-model="createUserId" />
      </el-form-item>
      <el-form-item label="Profile">
        <el-input v-model="createProfileText" type="textarea" :rows="12" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button type="primary" :loading="creatingProfile" @click="createRecord">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editVisible" title="编辑人设记录" width="60%">
    <el-form label-width="90px">
      <el-form-item label="用户ID">
        <el-input v-model="editUserId" />
      </el-form-item>
      <el-form-item label="Profile">
        <el-input v-model="editProfileText" type="textarea" :rows="12" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">取消</el-button>
      <el-button type="primary" :loading="savingEdit" @click="saveEdit">保存</el-button>
    </template>
  </el-dialog>
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
.records {
  margin-top: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
}
.records-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.records-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.records-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}
.row-ops {
  display: flex;
  align-items: center;
  gap: 8px;
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
