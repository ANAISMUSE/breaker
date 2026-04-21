<script setup lang="ts">
import { ref } from 'vue'
import http from '@/api/http'

const props = withDefaults(
  defineProps<{
    /** Query param for POST /api/ingestion/import */
    format?: 'auto' | 'douyin' | 'xiaohongshu' | 'weibo' | 'standard'
    accept?: string
    buttonText?: string
  }>(),
  {
    format: 'auto',
    accept: '.json,.csv,application/json,text/csv',
    buttonText: '从文件导入样本数据',
  },
)

const emit = defineEmits<{
  imported: [
    rows: Record<string, unknown>[],
    meta: {
      format: string
      rowCount: number
      filename: string
      detectedPlatform: string
      invalidRowCount: number
      invalidRows: Array<{ row_index: number; reason: string; content_id: string }>
      warnings: string[]
    },
  ]
  error: [message: string]
}>()

const busy = ref(false)
const lastMeta = ref<{
  format: string
  rowCount: number
  filename: string
  detectedPlatform: string
  invalidRowCount: number
  invalidRows: Array<{ row_index: number; reason: string; content_id: string }>
  warnings: string[]
} | null>(null)

async function onFile(file: File | null) {
  if (!file || busy.value) return
  busy.value = true
  lastMeta.value = null
  try {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await http.post<{
      rows: Record<string, unknown>[]
      format: string
      row_count: number
      filename: string
      detected_platform: string
      invalid_row_count: number
      invalid_rows: Array<{ row_index: number; reason: string; content_id: string }>
      warnings: string[]
    }>(`/api/ingestion/import?format=${encodeURIComponent(props.format)}`, fd)
    lastMeta.value = {
      format: data.format,
      rowCount: data.row_count,
      filename: data.filename,
      detectedPlatform: data.detected_platform,
      invalidRowCount: data.invalid_row_count ?? 0,
      invalidRows: data.invalid_rows ?? [],
      warnings: data.warnings ?? [],
    }
    emit('imported', data.rows, lastMeta.value)
  } catch (e: unknown) {
    let msg = ''
    if (e && typeof e === 'object' && 'response' in e) {
      const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d)) msg = d.map((x) => JSON.stringify(x)).join('; ')
    }
    emit('error', msg || (e instanceof Error ? e.message : '导入失败'))
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <span class="wrap">
    <el-upload
      :auto-upload="false"
      :show-file-list="false"
      :accept="accept"
      :disabled="busy"
      :on-change="(f: { raw?: File }) => onFile(f.raw ?? null)"
    >
      <el-button :loading="busy" type="primary" plain>{{ buttonText }}</el-button>
    </el-upload>
    <span v-if="lastMeta" class="meta">
      {{ lastMeta.filename }} · {{ lastMeta.rowCount }} 行 · {{ lastMeta.detectedPlatform }}
      <template v-if="lastMeta.invalidRowCount > 0"> · 过滤 {{ lastMeta.invalidRowCount }} 行坏数据</template>
    </span>
    <span v-if="lastMeta?.warnings?.length" class="warn">{{ lastMeta.warnings.join('；') }}</span>
  </span>
</template>

<style scoped>
.wrap {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.warn {
  font-size: 12px;
  color: var(--el-color-warning);
}
</style>
