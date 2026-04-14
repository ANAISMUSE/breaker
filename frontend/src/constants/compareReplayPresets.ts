import { demoBenchmark, demoRows } from '@/constants/demoData'

export interface CompareReplayPreset {
  id: string
  label: string
  description: string
  rows: Array<Record<string, unknown>>
  benchmark: Record<string, number>
  rounds: number
}

const youthRows = demoRows.map((row, idx) => ({
  ...row,
  user_id: 'preset_youth_001',
  persona_preset: 'youth',
  topic: idx % 2 === 0 ? 'entertainment' : row.topic,
  like: Number(row.like ?? 0) + 12,
  duration: Number(row.duration ?? 0) + 8,
}))

const elderlyRows = demoRows.map((row, idx) => ({
  ...row,
  user_id: 'preset_elderly_001',
  persona_preset: 'elderly',
  topic: idx % 2 === 0 ? 'health' : row.topic,
  like: Math.max(1, Number(row.like ?? 0) - 2),
  duration: Number(row.duration ?? 0) + 14,
}))

export const compareReplayPresets: CompareReplayPreset[] = [
  {
    id: 'youth-entertainment-heavy',
    label: '年轻娱乐偏好样本',
    description: '偏娱乐、互动较高，适合观察激进/混合策略改善幅度。',
    rows: youthRows,
    benchmark: {
      ...demoBenchmark,
      entertainment: 0.34,
      technology: 0.12,
      health: 0.06,
    },
    rounds: 12,
  },
  {
    id: 'elderly-health-heavy',
    label: '银发健康偏好样本',
    description: '偏健康与社会议题，适合验证阶梯策略在中轮次中的稳定性。',
    rows: elderlyRows,
    benchmark: {
      ...demoBenchmark,
      health: 0.2,
      society: 0.16,
      entertainment: 0.16,
    },
    rounds: 10,
  },
]
