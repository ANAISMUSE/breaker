export interface NavChild {
  title: string
  path: string
  roles?: string[]
}

export interface NavGroup {
  title: string
  children: NavChild[]
}

/** 与原 Streamlit product_app NAV_GROUPS 对齐 */
export const navGroups: NavGroup[] = [
  {
    title: '调度中心',
    children: [
      { title: '设备管理', path: '/app/dispatch/devices' },
      { title: '任务管理', path: '/app/dispatch/tasks' },
      { title: '实时监测', path: '/app/dispatch/monitor' },
    ],
  },
  {
    title: '分析中心',
    children: [
      { title: '风险详情', path: '/app/analytics/risk-detail' },
      { title: '语义图谱', path: '/app/analytics/semantic-graph' },
      { title: '应用画像', path: '/app/analytics/profile' },
      { title: '平台对比', path: '/app/analytics/compare' },
      { title: '对比历史', path: '/app/analytics/compare-history' },
    ],
  },
  {
    title: '数据与治理',
    children: [
      { title: '人设数据库', path: '/app/data/persona' },
      { title: '合规与审计', path: '/app/data/compliance' },
    ],
  },
  {
    title: '研发',
    children: [{ title: '算法工作台', path: '/app/research/workbench' }],
  },
  {
    title: '账户',
    children: [
      { title: '个人信息', path: '/app/account/profile' },
      { title: '用户权限管理', path: '/app/account/users', roles: ['admin'] },
      { title: '修改密码', path: '/app/account/change-password' },
    ],
  },
]
