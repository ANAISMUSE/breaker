/** 预设人设：每行带 persona_preset，构建孪生体时合并 agent_traits，并驱动模拟动作打分。 */

const uid = (preset: string) => `preset_${preset}_001`

export type PersonaPresetId = 'elderly' | 'youth' | 'child' | 'explore_heavy'

export interface PersonaPreset {
  id: PersonaPresetId
  label: string
  blurb: string
  rows: Record<string, unknown>[]
}

function row(
  preset: PersonaPresetId,
  partial: Record<string, unknown>
): Record<string, unknown> {
  return {
    user_id: uid(preset),
    persona_preset: preset,
    ...partial,
  }
}

/** 老年人：健康/社会为主、互动偏轻、停留偏长，配合高 echo、低 explore 特质 */
const elderlyRows: Record<string, unknown>[] = [
  row('elderly', {
    topic: 'health',
    stance: 'neutral',
    emotion_score: 3,
    like: 8,
    comment: 1,
    share: 2,
    duration: 72,
  }),
  row('elderly', {
    topic: 'society',
    stance: 'neutral',
    emotion_score: 3,
    like: 5,
    comment: 0,
    share: 0,
    duration: 55,
  }),
  row('elderly', {
    topic: 'health',
    stance: 'neutral',
    emotion_score: 2,
    like: 12,
    comment: 2,
    share: 1,
    duration: 68,
  }),
  row('elderly', {
    topic: 'finance',
    stance: 'neutral',
    emotion_score: 3,
    like: 6,
    comment: 0,
    share: 0,
    duration: 48,
  }),
]

/** 青壮年：科技/社会参与深、评论多，对照组 */
const youthRows: Record<string, unknown>[] = [
  row('youth', {
    topic: 'technology',
    stance: 'neutral',
    emotion_score: 4,
    like: 22,
    comment: 8,
    share: 3,
    duration: 42,
  }),
  row('youth', {
    topic: 'society',
    stance: 'left',
    emotion_score: 4,
    like: 14,
    comment: 18,
    share: 4,
    duration: 65,
  }),
  row('youth', {
    topic: 'entertainment',
    stance: 'neutral',
    emotion_score: 4,
    like: 35,
    comment: 6,
    share: 5,
    duration: 28,
  }),
  row('youth', {
    topic: 'politics',
    stance: 'right',
    emotion_score: 3,
    like: 9,
    comment: 11,
    share: 2,
    duration: 52,
  }),
]

/** 少年儿童：娱乐主导、短时、轻评论 */
const childRows: Record<string, unknown>[] = [
  row('child', {
    topic: 'entertainment',
    stance: 'neutral',
    emotion_score: 5,
    like: 48,
    comment: 2,
    share: 6,
    duration: 18,
  }),
  row('child', {
    topic: 'entertainment',
    stance: 'neutral',
    emotion_score: 5,
    like: 52,
    comment: 1,
    share: 8,
    duration: 15,
  }),
  row('child', {
    topic: 'sports',
    stance: 'neutral',
    emotion_score: 4,
    like: 30,
    comment: 3,
    share: 2,
    duration: 22,
  }),
  row('child', {
    topic: 'technology',
    stance: 'neutral',
    emotion_score: 4,
    like: 20,
    comment: 1,
    share: 1,
    duration: 25,
  }),
]

/** 高探索：话题分散、主动参与异质内容，低茧房对照 */
const exploreHeavyRows: Record<string, unknown>[] = [
  row('explore_heavy', {
    topic: 'education',
    stance: 'neutral',
    emotion_score: 3,
    like: 10,
    comment: 5,
    share: 2,
    duration: 50,
  }),
  row('explore_heavy', {
    topic: 'politics',
    stance: 'left',
    emotion_score: 3,
    like: 6,
    comment: 14,
    share: 1,
    duration: 58,
  }),
  row('explore_heavy', {
    topic: 'finance',
    stance: 'neutral',
    emotion_score: 3,
    like: 8,
    comment: 7,
    share: 2,
    duration: 45,
  }),
  row('explore_heavy', {
    topic: 'health',
    stance: 'neutral',
    emotion_score: 3,
    like: 7,
    comment: 6,
    share: 1,
    duration: 40,
  }),
]

export const personaPresets: PersonaPreset[] = [
  {
    id: 'elderly',
    label: '老年人',
    blurb: '熟悉域内强化、少搜索陌生域，偏茧房敏感型',
    rows: elderlyRows,
  },
  {
    id: 'youth',
    label: '青壮年',
    blurb: '深度互动与观点参与，一般对照人群',
    rows: youthRows,
  },
  {
    id: 'child',
    label: '少年儿童',
    blurb: '娱乐向、轻评论，话题窄化风险观察',
    rows: childRows,
  },
  {
    id: 'explore_heavy',
    label: '高探索',
    blurb: '主动接触多元话题，破茧/对照基线',
    rows: exploreHeavyRows,
  },
]
