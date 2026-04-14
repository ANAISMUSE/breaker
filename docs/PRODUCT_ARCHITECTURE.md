# 茧评产品化架构说明

## 分层

- `frontend/`: Vue + Vite 产品壳层（登录、左侧导航、模块占位与任务列表）
- `src/api/`: FastAPI 接口层（当前含 auth/tasks 骨架）
- `src/services/`: 业务服务层（task/risk/simulation/compliance）
- `src/repositories/`: 仓储接口与实现（当前 JSON 任务仓储，预留 SQLite/MySQL）
- `src/security/`: 本地账号认证与 RBAC
- 领域能力沿用并增强：
  - `src/evaluation/`
  - `src/twin/`
  - `src/simulation/`
  - `src/embedding/`

## 页面 IA

- 监控总览
- 设备管理（占位）
- 任务管理
- 人设数据库（占位）
- 风险评估
- 应用画像（占位）
- 平台对比
- 实时监测（云手机适配层，默认关闭）
- 合规与审计
- 算法工作台（占位，原 Streamlit 工作台已移除）

## API 合同（已落地骨架）

- `POST /api/auth/login`（返回 `access_token` JWT）
- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/health`

## 存储切换策略

- `settings.storage_backend` + `settings.mysql_url` 控制仓储后端选择
- 当前阶段默认 `JsonTaskRepository`
- 后续新增：
  - `SQLiteTaskRepository`
  - `MySQLTaskRepository`
  - Repository Factory 透明切换

## 合规与安全

- 默认导出数据路径，外接采集需 `.env` 开关并用户确认
- 高风险反爬能力不作为默认实现
- 本地账号 + 角色权限（admin/researcher/viewer）
- 审计日志：`data/audit_log.jsonl`
- 数据清理：向量/上传/任务可分别清理

## 分阶段实施路线（状态）

1. Phase A（已完成）：产品壳层 + API/Service/Repository/Security 骨架
2. Phase B（已完成）：设备管理与任务详情/快照/日志导出完善
3. Phase C（已完成）：人设库 CRUD 与风险详情页
4. Phase D（进行中）：应用画像与平台对比全量图表
5. Phase E（待做）：云手机监测适配器接入与安全/合规模块收口
