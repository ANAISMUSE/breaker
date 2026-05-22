/**
 * 演示用 mock 数据：模拟一个典型信息茧房用户
 * 特征：娱乐/搞笑占绝对主导，立场偏正面，极少跨领域，情绪偏高
 * → S1(内容多样性)低、S2(跨领域)低、S3(立场多样性)低、S4(认知覆盖)低 → 茧房指数高
 */
export const demoRows = [
  // ── 娱乐/搞笑（占 ~55%，高频互动）──
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_001', timestamp: '2025-05-01T10:00:00', content_type: 'video', text: '搞笑猫咪合集，笑到停不下来', image_url: '', video_url: '', like: 42, comment: 8, share: 5, duration: 45, topic: 'entertainment', stance: 'positive', emotion_score: 8.5, author_id: 'a_funny' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_002', timestamp: '2025-05-01T12:30:00', content_type: 'video', text: '沙雕日常翻车现场', image_url: '', video_url: '', like: 35, comment: 12, share: 3, duration: 30, topic: 'entertainment', stance: 'positive', emotion_score: 9.0, author_id: 'a_funny' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_003', timestamp: '2025-05-02T09:15:00', content_type: 'video', text: '宠物搞笑瞬间，太可爱了', image_url: '', video_url: '', like: 28, comment: 5, share: 7, duration: 60, topic: 'entertainment', stance: 'positive', emotion_score: 8.8, author_id: 'a_cute' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_004', timestamp: '2025-05-02T14:00:00', content_type: 'video', text: '整蛊室友大作战', image_url: '', video_url: '', like: 50, comment: 15, share: 8, duration: 90, topic: 'entertainment', stance: 'positive', emotion_score: 9.2, author_id: 'a_funny' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_005', timestamp: '2025-05-03T08:00:00', content_type: 'video', text: '方言搞笑配音合集', image_url: '', video_url: '', like: 22, comment: 3, share: 2, duration: 35, topic: 'entertainment', stance: 'positive', emotion_score: 8.0, author_id: 'a_dub' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_006', timestamp: '2025-05-03T20:30:00', content_type: 'video', text: '搞笑动画短片', image_url: '', video_url: '', like: 18, comment: 2, share: 1, duration: 25, topic: 'entertainment', stance: 'positive', emotion_score: 7.5, author_id: 'a_anim' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_007', timestamp: '2025-05-04T11:00:00', content_type: 'video', text: '萌娃搞笑日常', image_url: '', video_url: '', like: 30, comment: 6, share: 4, duration: 50, topic: 'entertainment', stance: 'positive', emotion_score: 8.6, author_id: 'a_kid' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_008', timestamp: '2025-05-04T16:45:00', content_type: 'video', text: '街头采访搞笑回答', image_url: '', video_url: '', like: 25, comment: 4, share: 3, duration: 40, topic: 'entertainment', stance: 'positive', emotion_score: 8.3, author_id: 'a_street' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_009', timestamp: '2025-05-05T10:20:00', content_type: 'video', text: '恶搞美食制作', image_url: '', video_url: '', like: 38, comment: 10, share: 6, duration: 55, topic: 'entertainment', stance: 'positive', emotion_score: 8.9, author_id: 'a_food' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_010', timestamp: '2025-05-05T22:00:00', content_type: 'video', text: '办公室摸鱼搞笑瞬间', image_url: '', video_url: '', like: 33, comment: 7, share: 4, duration: 38, topic: 'entertainment', stance: 'positive', emotion_score: 8.1, author_id: 'a_office' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_011', timestamp: '2025-05-06T09:00:00', content_type: 'video', text: '搞笑配音之经典电影片段', image_url: '', video_url: '', like: 20, comment: 3, share: 2, duration: 28, topic: 'entertainment', stance: 'positive', emotion_score: 7.8, author_id: 'a_dub' },

  // ── 娱乐（占 ~18%，中频互动）──
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_012', timestamp: '2025-05-01T18:00:00', content_type: 'video', text: '明星八卦最新动态', image_url: '', video_url: '', like: 15, comment: 3, share: 2, duration: 60, topic: 'entertainment', stance: 'positive', emotion_score: 7.0, author_id: 'a_gossip' },
  { user_id: 'demo_user_01', platform: 'xiaohongshu', content_id: 'xhs_001', timestamp: '2025-05-02T19:30:00', content_type: 'image', text: '追剧推荐：最近超好看的综艺', image_url: '', video_url: '', like: 12, comment: 2, share: 1, duration: 20, topic: 'entertainment', stance: 'positive', emotion_score: 7.5, author_id: 'a_show' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_013', timestamp: '2025-05-04T21:00:00', content_type: 'video', text: '偶像舞台直拍合集', image_url: '', video_url: '', like: 20, comment: 5, share: 3, duration: 180, topic: 'entertainment', stance: 'positive', emotion_score: 8.0, author_id: 'a_idol' },
  { user_id: 'demo_user_01', platform: 'weibo', content_id: 'wb_001', timestamp: '2025-05-05T12:00:00', content_type: 'text', text: '综艺名场面盘点', image_url: '', video_url: '', like: 8, comment: 1, share: 0, duration: 15, topic: 'entertainment', stance: 'positive', emotion_score: 6.5, author_id: 'a_variety' },

  // ── 体育（占 ~9%，低频）──
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_014', timestamp: '2025-05-02T22:00:00', content_type: 'video', text: 'NBA精彩扣篮集锦', image_url: '', video_url: '', like: 10, comment: 1, share: 0, duration: 45, topic: 'sports', stance: 'positive', emotion_score: 7.0, author_id: 'a_nba' },
  { user_id: 'demo_user_01', platform: 'douyin', content_id: 'dy_015', timestamp: '2025-05-05T18:00:00', content_type: 'video', text: '足球搞笑失误合集', image_url: '', video_url: '', like: 8, comment: 0, share: 1, duration: 30, topic: 'sports', stance: 'neutral', emotion_score: 6.0, author_id: 'a_soccer' },

  // ── 科技（占 ~9%，偶尔浏览）──
  { user_id: 'demo_user_01', platform: 'weibo', content_id: 'wb_002', timestamp: '2025-05-03T15:00:00', content_type: 'text', text: '新款手机发布，配置一览', image_url: '', video_url: '', like: 3, comment: 0, share: 0, duration: 10, topic: 'technology', stance: 'neutral', emotion_score: 5.0, author_id: 'a_tech' },
  { user_id: 'demo_user_01', platform: 'xiaohongshu', content_id: 'xhs_002', timestamp: '2025-05-06T14:00:00', content_type: 'image', text: '数码产品开箱体验', image_url: '', video_url: '', like: 2, comment: 0, share: 0, duration: 8, topic: 'technology', stance: 'neutral', emotion_score: 4.5, author_id: 'a_digi' },

  // ── 少量社会/时政（占 ~9%，几乎无互动）──
  { user_id: 'demo_user_01', platform: 'weibo', content_id: 'wb_003', timestamp: '2025-05-03T08:00:00', content_type: 'text', text: '今日社会热点新闻速览', image_url: '', video_url: '', like: 0, comment: 0, share: 0, duration: 5, topic: 'society', stance: 'neutral', emotion_score: 4.0, author_id: 'a_news' },
  { user_id: 'demo_user_01', platform: 'weibo', content_id: 'wb_004', timestamp: '2025-05-06T07:30:00', content_type: 'text', text: '政策解读：最新民生政策', image_url: '', video_url: '', like: 0, comment: 0, share: 0, duration: 3, topic: 'politics', stance: 'neutral', emotion_score: 3.5, author_id: 'a_policy' },
]

export const demoBenchmark = {
  entertainment: 0.20,
  politics: 0.15,
  society: 0.15,
  technology: 0.15,
  education: 0.10,
  finance: 0.10,
  sports: 0.10,
  health: 0.05,
}
