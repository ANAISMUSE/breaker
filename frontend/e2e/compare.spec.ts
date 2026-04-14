import { expect, test } from '@playwright/test'

const TOKEN_KEY = 'jianping_token'
const USER_KEY = 'jianping_user'
const ROLE_KEY = 'jianping_role'

const successPayload = {
  result: {
    baseline: {
      cocoon_start: 7.1,
      cocoon_end: 6.4,
      drop: 0.7,
      series: [7.1, 6.9, 6.7, 6.6, 6.4],
    },
    aggressive: {
      cocoon_start: 7.1,
      cocoon_end: 5.6,
      drop: 1.5,
      series: [7.1, 6.8, 6.3, 5.9, 5.6],
    },
    ladder: {
      cocoon_start: 7.1,
      cocoon_end: 5.9,
      drop: 1.2,
      series: [7.1, 6.8, 6.5, 6.2, 5.9],
    },
    mixed: {
      cocoon_start: 7.1,
      cocoon_end: 6.1,
      drop: 1.0,
      series: [7.1, 6.8, 6.5, 6.3, 6.1],
    },
    _best: {
      name: 'aggressive',
      drop: 1.5,
      static_cocoon: 7.1,
    },
  },
  trend_option: {
    legend: { data: ['baseline', 'aggressive', 'ladder', 'mixed'] },
    xAxis: { type: 'category', data: ['R1', 'R2', 'R3', 'R4', 'R5'] },
    yAxis: { type: 'value', min: 0, max: 10 },
    series: [
      { name: 'baseline', type: 'line', data: [7.1, 6.9, 6.7, 6.6, 6.4] },
      { name: 'aggressive', type: 'line', data: [7.1, 6.8, 6.3, 5.9, 5.6] },
      { name: 'ladder', type: 'line', data: [7.1, 6.8, 6.5, 6.2, 5.9] },
      { name: 'mixed', type: 'line', data: [7.1, 6.8, 6.5, 6.3, 6.1] },
    ],
  },
}

const recordsPayload = [
  {
    record_id: 'rec-001',
    user_id: 'user_history_001',
    rounds: 9,
    benchmark: {
      technology: 0.2,
      entertainment: 0.3,
      society: 0.1,
      health: 0.1,
      education: 0.1,
      sports: 0.1,
      finance: 0.1,
    },
    rows: [
      {
        user_id: 'user_history_001',
        topic: 'technology',
        stance: 'neutral',
        emotion_score: 3,
        like: 8,
        comment: 2,
        share: 1,
        duration: 30,
      },
    ],
    result: successPayload,
    created_at: '2026-04-14T08:00:00Z',
  },
]

test.beforeEach(async ({ page }) => {
  await page.addInitScript(
    ({ token, username, role, tokenKey, userKey, roleKey }) => {
      localStorage.setItem(tokenKey, token)
      localStorage.setItem(userKey, username)
      localStorage.setItem(roleKey, role)
    },
    {
      token: 'e2e-token',
      username: 'admin',
      role: 'admin',
      tokenKey: TOKEN_KEY,
      userKey: USER_KEY,
      roleKey: ROLE_KEY,
    },
  )
})

test('平台对比 happy path：运行后展示推荐与图表容器', async ({ page }) => {
  await page.route('**/api/simulation/compare', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(successPayload),
    })
  })

  await page.goto('/app/analytics/compare')
  await expect(page.getByRole('heading', { name: '平台对比（多策略模拟 · 可视化）' })).toBeVisible()

  await page.getByRole('button', { name: '运行对比' }).click()

  await expect(page.getByText('模拟推荐')).toBeVisible()
  await expect(page.getByText('最优策略为')).toBeVisible()
  await expect(page.locator('.viz .chart')).toHaveCount(3)
  await expect(page.locator('.json-pre')).toContainText('"_best"')
})

test('平台对比 error path：接口失败时给出错误提示', async ({ page }) => {
  await page.route('**/api/simulation/compare', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'mock compare failed' }),
    })
  })

  await page.goto('/app/analytics/compare')
  await page.getByRole('button', { name: '运行对比' }).click()

  await expect(page.getByText('Request failed with status code 500')).toBeVisible()
  await expect(page.locator('.viz .chart')).toHaveCount(0)
})

test('对比历史回放：可跳转并填充到平台对比页', async ({ page }) => {
  await page.route('**/api/simulation/records**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(recordsPayload),
    })
  })

  await page.goto('/app/analytics/compare-history')
  await expect(page.getByRole('heading', { name: '平台对比历史记录' })).toBeVisible()
  await page.getByRole('button', { name: '回放' }).first().click()

  await expect(page).toHaveURL(/\/app\/analytics\/compare$/)
  await expect(page.getByRole('heading', { name: '平台对比（多策略模拟 · 可视化）' })).toBeVisible()

  const textareas = page.locator('textarea')
  await expect(textareas.first()).toHaveValue(/user_history_001/)
  await expect(textareas.nth(1)).toHaveValue(/"technology"/)
})
