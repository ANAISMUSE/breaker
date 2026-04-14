# API 文档清单（答辩展示版）

用于答辩时快速说明“前端页面 -> 后端接口 -> 返回结果”的闭环。默认 API 前缀为 `/api`。

## 一、鉴权与账户

- `POST /auth/login`：账号登录，返回 token 与角色信息。
- `POST /auth/register`：注册新账号。
- `POST /auth/change-password`：修改当前账号密码。
- `GET /users/me`：获取当前用户资料。
- `PATCH /users/me`：更新当前用户资料。
- `PATCH /users/{username}/role`：管理员调整用户角色。

## 二、导入与实时采集

- `POST /ingestion/import`：统一导入入口（CSV/JSON/平台导出），前端 `RowsFileImport` 默认调用此接口。
- `GET /realtime/status`：实时任务状态查询。
- `POST /realtime/crawl-preview`：实时采集预览。

## 三、风险评估（第二阶段统一数据源）

- `POST /risk/overview`：仅返回 S1-S4 与茧房指数概览（轻量）。
- `POST /risk/detail`：统一详情数据源（建议前端主用）：
  - `overview`：S1-S4、`cocoon_index`、`mode`
  - `llm`：`llm_enhanced`、`semantic_rows`、`embedding_rows`、`evidence`
  - `distributions`：`topic`、`stance`、`benchmark`、`alignment`
  - `derived`：`s1_entropy`、`s2_cross`、`s3_gini`、`s4_overlap`
  - `suggestions`：S2/S4 动作建议（含目标值与缺口主题）

> 当前前端 `RiskView` 与 `SemanticGraphView` 已统一基于 `POST /risk/detail`。

## 四、模拟与画像

- `POST /simulation/compare`：多策略模拟对比。
- `GET /simulation/records`：模拟历史记录查询。
- `POST /persona/build`：构建画像。
- `POST /persona/profiles`：保存画像。
- `GET /persona/profiles`：画像列表。
- `GET /persona/profiles/{profile_id}`：画像详情。
- `PATCH /persona/profiles/{profile_id}`：更新画像。
- `DELETE /persona/profiles/{profile_id}`：删除画像。
- `GET /persona/records`：画像相关记录。

## 五、任务与设备

- `GET /tasks`：任务列表。
- `POST /tasks`：创建任务。
- `GET /tasks/{task_id}`：任务详情。
- `PATCH /tasks/{task_id}/status`：任务状态变更。
- `POST /tasks/{task_id}/snapshots`：写入快照。
- `GET /tasks/{task_id}/export`：任务导出。
- `GET /tasks/{task_id}/logs`：任务日志查询。
- `POST /tasks/{task_id}/logs`：新增任务日志。
- `GET /tasks/{task_id}/logs/export`：日志导出。
- `GET /tasks/{task_id}/logs/export.csv`：CSV 日志导出。
- `GET /devices`：设备列表。
- `POST /devices`：新增设备。
- `PATCH /devices/{device_id}/status`：设备状态更新。
- `DELETE /devices/{device_id}`：设备删除。

## 六、分析、工作台、合规

- `GET /analytics/dashboard`：分析大盘数据。
- `POST /workbench/plan`：工作台方案生成。
- `POST /workbench/report`：工作台报告生成。
- `GET /compliance/audit`：合规审计记录查询。
- `POST /compliance/audit`：写入审计记录。
- `POST /compliance/wipe`：本地数据清理。
- `POST /workflow/run`：工作流触发执行。
- `GET /llm/health`：LLM 链路健康检查。

## 七、健康检查

- `GET /health`：根路径健康检查。
- `GET /api/health`：API 健康检查。

## 八、答辩建议展示顺序（3 分钟版）

1. 登录后在 `风险评估` 上传同一份 rows + benchmark。
2. 展示 `RiskView`：S1-S4 + cocoon + LLM 证据 + 建议动作。
3. 切到 `语义图谱`：同一份数据自动复用，展示 Top2 主题与覆盖缺口节点。
4. 说明两页都来自 `POST /risk/detail`，指标解释与图谱交互完全一致。
5. 以 `simulation/compare` 衔接后续“策略验证”闭环。
