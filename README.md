# 茧评

基于《完整技术方案（PDF）》对齐的实现：用户数字孪生体、类人行为模拟（5 评估器 + Softmax + 轮盘赌）、多策略破茧模拟、**PDF 3.6** 四维多样性得分与茧房指数（0–10）、任务记录与本地合规清理。

## 快速开始

1. Python 3.10+
2. `pip install -r requirements.txt`（可选：`pip install -r requirements-optional-privacy.txt`）
3. 复制 `.env.example` 为 `.env`，填写 `DASHSCOPE_API_KEY`
4. **后端**：在项目根目录执行  
   `uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000`
5. **前端（开发）**：另开终端  
   `cd frontend && npm install && npm run dev`  
   浏览器打开 Vite 提示的地址（一般为 `http://localhost:5173`）。`/api` 由 Vite 代理到本机 `8000` 端口。
6. **单端口（生产预览）**：先 `cd frontend && npm run build`，再启动上述 uvicorn；若存在 `frontend/dist`，后端会自动托管静态资源，可直接访问 `http://127.0.0.1:8000/`。
7. 登录默认账号：`admin / admin123`（请上线前修改 `data/users.json` 与 `APP_SECRET`）

旧版 Streamlit 界面已移除；若需本地回看依赖，可使用 `pip install -r requirements-legacy-streamlit.txt`（无入口脚本）。

## 前后端目录

| 路径 | 说明 |
|------|------|
| `frontend/` | Vue 3 + Vite + TypeScript，登录页与左侧导航主布局 |
| `src/api/` | FastAPI 应用，接口前缀 `/api` |
| `src/web/task_store.py` 等 | 任务存储与图表/报告工具函数，供服务层与后续 API 复用 |

## 数据采集与合规（工程降险版）

| 路径 | 说明 |
|------|------|
| **路径 1（推荐）** | 各平台官方「个人信息导出」JSON/CSV，在应用内上传或使用演示数据。 |
| **路径 2（可选）** | 通过 `.env` 外接本机 MediaCrawler 等工具；**须自行保证合法授权**。 |

**本项目明确不实现**：验证码识别/绕过、浏览器指纹对抗、多账号 Cookie 池轮换等高风险能力（与 PDF 3.10 类扩展区分，默认不落地）。

外接采集前建议确认：平台用户协议/robots/开发者条款、数据最小必要与目的限制、是否涉及他人个人信息。界面勾选风险提示**不能替代**法务或校方合规审查。设置 `CRAWLER_LEGAL_ACK=true` 与 `CRAWLER_ALLOWED_PURPOSES=academic_research,...` 仅用于工程门禁（不免除法律责任）。

## 核心模块（与 PDF 对应）

- `src/evaluation/metrics_v2.py` + `index_pipeline.evaluate_cocoon_pdf36`：S1–S4（1–10）与 C（0–10），静态/动态共用公式
- `src/twin/`：孪生体三大模型、记忆流、时间衰减检索、60/30/10 分层采样
- `src/simulation/`：动作生成、多策略模拟与对比
- `src/compliance/audit.py`：操作留痕、一键清理本地数据
- `src/web/task_store.py`：轻量任务记录（`data/tasks_store.json`）
- `frontend/`：产品化 Web UI（Vue，左侧导航与模块占位；任务管理已接 `GET /api/tasks`）
- `src/api` + `src/services` + `src/repositories` + `src/security`：产品化后端分层骨架

## 语义向量链路

- `src/embedding/pipeline.py`：Omni 结构化描述 + 多模态嵌入，写入 `data/vector_store.json`，并在 DataFrame 中保留 `embedding` 列供 S2/S4 使用。

## 目录说明

- `src/data_ingestion`：导入与 MediaCrawler 适配
- `src/privacy`：脱敏
- `src/preprocess`：清洗
- `src/embedding`：向量与检索
- `src/evaluation`：指标与管道（含旧版 `evaluate_user_cocoon` 供测试兼容）
- `src/twin`、`src/simulation`：孪生与模拟
- `src/compliance`：审计与清理
- `src/agents`：破茧计划策略
- `src/web`：任务存储与图表/报告导出辅助（无 Streamlit 页面）
- `data`：演示数据、对标分布、审计日志

## 报告与扩展位

- Word 报告含 PDF 口径四维与茧房指数；**平台画像 / 多平台对比**需在合规数据源确定后接入（报告中已保留说明段落）。
- 详细架构说明见 `docs/PRODUCT_ARCHITECTURE.md`。
