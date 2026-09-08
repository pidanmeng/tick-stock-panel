# 财务分析 Financials

## 功能概述

财务分析模块（菜单：财务分析，路由 `/financials`）提供 A 股上市公司的财务报表数据同步、展示与 AI 智能分析能力：

- **数据同步**：按 5 张财务表（核心指标 metrics、利润表 income、资产负债表 balance_sheet、现金流量表 cash_flow、股本结构 shares）从数据源拉取，以 Parquet 全量覆盖写入 `data/financials/{table}/part.parquet`；对已有符号按 `announce_date` 做按列 PIT（公告日）合并，保留历史期间。
- **数据展示**：前端支持股票模糊搜索、5 个 Tab（核心指标 / 利润表 / 资产负债表 / 现金流量表 / 股本）浏览，字段按类型（百分比/金额/每股/数值）格式化。
- **AI 分析**：将最多 4 个报告期的财务数据打包为 JSON，经 AI Provider 流式生成 CFA/CPA 级 Markdown 研报（NDJSON 流），报告持久化至 `data/user_data/ai_reports.json`（最多 20 条），前端以全局对话框 + 悬浮气泡展示。
- **能力路由**：依赖 TickFlow `financial` 能力（Expert 档）或自定义财务数据 Provider；能力不可用时页面 fail-closed 提示，不展示空数据页。

## 文件清单

### 前端

| 文件 | 职责 |
| --- | --- |
| `frontend/src/pages/Financials.tsx` | 功能主页：能力门禁、同步状态卡片、股票搜索、详情、历史面板编排 |
| `frontend/src/router.tsx` | 路由注册（`/financials`，L138）与受保护路由守卫清单（L57） |
| `frontend/src/components/Layout.tsx` | 导航入口（L94）、全局挂载 AiAnalysisHost / AiReportBubble（L1053-1054） |
| `frontend/src/components/financials/StockFinancialSearch.tsx` | 股票模糊搜索输入框 |
| `frontend/src/components/financials/StockFinancialDetail.tsx` | 5-Tab 详情页、AI 分析入口、字段格式化定义 |
| `frontend/src/components/financials/ReportHistoryPanel.tsx` | 历史报告列表（20 条上限）、删除、进行中任务展示 |
| `frontend/src/components/financials/AiAnalysisHost.tsx` | AI 对话框唯一挂载点，读取全局 store |
| `frontend/src/components/financials/AiAnalysisDialog.tsx` | AI 分析对话框（4 阶段：加载/流式/完成/错误） |
| `frontend/src/components/financials/AiReportBubble.tsx` | 可拖拽的悬浮气泡（工作/完成/错误三态） |
| `frontend/src/components/financials/MarkdownRenderer.tsx` | 零依赖 Markdown 渲染器（供 AI 研报展示） |
| `frontend/src/lib/useFinancials.ts` | TanStack Query 数据请求钩子 + 同步 Mutation |
| `frontend/src/lib/aiReportStore.ts` | AI 分析全局外部 store（活动任务 + 历史报告） |
| `frontend/src/lib/api.ts` | API 客户端（financial 系列方法） |
| `frontend/src/lib/capability-labels.tsx` | 能力路由 `routeCapUsable('financial')`（L18） |

### 后端

| 文件 | 职责 |
| --- | --- |
| `backend/app/api/financials.py` | `/api/financials` 路由：状态、5 表查询、同步触发、AI 分析流、报告 CRUD |
| `backend/app/services/financial_sync.py` | 财务数据同步核心：拉取、写表、历史合并、调度器 |
| `backend/app/services/financial_analyzer.py` | AI 分析编排：加载数据、构建 Prompt、NDJSON 流式输出 |
| `backend/app/services/ai_reports.py` | 报告存储薄封装（`JsonReportStore` 包装） |
| `backend/app/services/json_report_store.py` | 原子写 JSON 存储（临时文件 + os.replace） |
| `backend/app/services/ai_provider.py` | AI Provider 抽象（OpenAI 兼容流式 / Codex CLI） |
| `backend/app/services/preferences.py` | 财务 Provider 配置与同步时间持久化（L303/L1099/L1104） |
| `backend/app/main.py` | 调度器启动（L238-239）、路由注册（L486） |
| `backend/app/data_providers/capabilities.py` | 能力注册表 `financial` 条目（L72-78） |
| `backend/app/tickflow/capabilities.py` | `Cap.FINANCIAL = "financial"`（L27） |
| `backend/tests/test_financial_shares.py` | 同步逻辑测试（6 个用例） |
| `backend/tests/test_fuyao_financial.py` | Provider 映射与 PIT 合并测试（9 个用例） |

### 数据存储

| 路径 | 说明 |
| --- | --- |
| `data/financials/{table}/part.parquet` | 5 张财务表数据（全量覆盖写，历史经合并保留） |
| `data/user_data/ai_reports.json` | AI 研报持久化（最多 20 条，原子写） |
| `data/user_data/preferences.json` | `financial_sync_times`（重启后恢复上次同步时间） |

## 业务逻辑

### 1. 能力门禁与页面准入

- `Financials.tsx` 通过 `routeCapUsable('financial')`（[capability-labels.tsx:L18](file:///c:/Code/tick-stock-panel/frontend/src/lib/capability-labels.tsx#L18)）判断当前数据源是否具备财务能力；不可用则渲染禁用提示而非空页面（fail-closed）。
- 后端能力来源二选一：TickFlow `financial`（Expert 档）或自定义财务 Provider（[capabilities.py:L72-78](file:///c:/Code/tick-stock-panel/backend/app/data_providers/capabilities.py#L72-L78)）；`get_financial_provider()` 返回实际 Provider（[preferences.py:L303](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L303)）。

### 2. 财务数据同步（FinancialScheduler）

核心在 `backend/app/services/financial_sync.py`：

- **表清单**：`FINANCIAL_TABLES = ("metrics", "income", "balance_sheet", "cash_flow", "shares")`。
- **调度器生命周期**：`main.py:238` 调用 `financial_scheduler.start(store.data_dir, capset)`（不自动定时，仅初始化）；`FinancialScheduler` 以 `_is_syncing` 标志防并发，`trigger()` 起后台线程异步同步，`run_now()` 阻塞同步。
- **拉取与写表**：`_fetch_table` 按 100 只批量拉取（TickFlow 或自定义 Provider）；`_write_table` 对 `data/financials/{table}/part.parquet` 做全量覆盖写。
- **历史合并**：`_sync_history_table_for_symbols` 对已有符号保留现有期间 + 补齐缺失全量历史 + 对现存符号拉取最新；`_merge_report_history` 实现按列 PIT 合并——以每列最近非空且 `announce_date` 最新的值优先，多源取并集。
- **同步进度记录**：`_record_sync` 将各表完成时间写入 preferences（`financial_sync_times`），重启后 `start()` 据其恢复状态。
- **前端同步状态**：`Financials.tsx` 以 `syncStartedAt` 时间戳与 `/api/financials/status` 返回的 `last_sync` 比较，渲染 3 态（同步中/已完成/等待）；`useFinancials.ts` 在同步中 3s 轮询刷新、数据表 300s staleTime。

### 3. 数据查询 API

`backend/app/api/financials.py` 提供 7 个端点：

- `GET /api/financials/status`：能力可用性、表列表、上次同步时间、同步中标志（**不校验 FINANCIAL 能力**，供能力门禁前展示）。
- `GET /metrics|/income|/balance-sheet|/cash-flow|/shares`：均要求 `FINANCIAL` 能力；`get_financial_df` 读 Parquet → 可选按 symbol 过滤 → 转 dict 列表。
- `POST /sync/{table}`：触发后台同步，返回 `{started, reason}`。
- `POST /analyze`：NDJSON 流式 AI 分析。
- `GET|POST /reports`、`DELETE /reports/{report_id}`：研报 CRUD。

### 4. AI 财务分析

- **数据装载**：`financial_analyzer._load_stock_financials` 取最多 4 个报告期，NaN 转 null；`_build_user_prompt` 将 JSON 数据 + 关注点指令打包。
- **系统提示词**：`_SYSTEM_PROMPT` 定位 CFA/CPA 15 年分析师，固定 5 节 Markdown 结构（核心摘要/亮点/风险提示/分项诊断/综合评估），正文 800-1500 字。
- **流式输出**：`analyze_financials_stream` 为异步生成器，产出 NDJSON 帧：`meta`（期间/符号）/ `delta`（增量文本）/ `error` / `done`；经 `ai_provider.stream_ai_text` 消费 LLM 流。
- **模型参数**：`temperature=0.4`、`max_tokens=None`（适配推理模型）、DeepSeek V4 关闭 `thinking`、OpenAI 兼容优先 `prefer_final_answer=True`。
- **报告持久化**：流完成自动经 `ai_reports.save_report` 写入；`JsonReportStore` 用临时文件 + `os.replace` 原子写，`id` 为时间戳 + 符号，上限 20 条。
- **前端消费**：`aiReportStore.ts` 为全局同步外部 store，`MAX_ACTIVE=3` 并发上限，`runStream` 逐帧消费 NDJSON；`AiAnalysisDialog` 四阶段渲染，`AiReportBubble` 三态可拖拽气泡（位置持久化 localStorage），二者均挂载于 `Layout.tsx:1053-1054` 全局单例。

### 5. 金融口径要点

- 金额字段单位为元，比率字段为百分点（如 12.3 → 12.3%）；前端 `StockFinancialDetail` 的 `FIELD_DEFS` 按 `FmtType`（pct/amount/perShare/num）格式化，禁止"数值<1 乘 100"启发式。
- 财务数据按 `(symbol, period_end)` 并集 + 公告日 PIT；公告前的空值不补 0（fail-closed 语义）。

## 数据流 / 调用链

```
[前端 Financials.tsx]
  ├─ 能力门禁 routeCapUsable('financial')  ── 不可用 → 禁用提示（fail-closed）
  ├─ GET /api/financials/status             → preferences.financial_sync_times
  ├─ 同步卡片 POST /api/financials/sync/{table} → financial_scheduler.trigger() → 后台线程
  │      _fetch_table(批量100) → _write_table → data/financials/{table}/part.parquet
  │      已有符号 → _merge_report_history(按列 announce_date PIT) → _record_sync → preferences
  ├─ GET /api/financials/{metrics|income|balance-sheet|cash-flow|shares}
  │      → get_financial_df → Parquet → dicts → useFinancials (3s 轮询 / 300s staleTime)
  └─ POST /api/financials/analyze
         → financial_analyzer.analyze_financials_stream
         → ai_provider.stream_ai_text (OpenAI兼容 / Codex CLI)
         → NDJSON: meta/delta/error/done → StreamingResponse
         → 前端 aiReportStore.runStream 逐帧消费
         → 完成后 auto-save → JsonReportStore → data/user_data/ai_reports.json
         → AiAnalysisDialog / AiReportBubble / ReportHistoryPanel 展示
```

## 关键数据结构

### 财务表（Parquet，每表一文件）

5 张表共用 `symbol` + `period_end` 定位报告期；股本表含 `announce_date` 驱动按列 PIT 合并。列结构由 Provider 映射（income/balance/cash_flow 直接透传，metrics 汇总 `eps_basic`、`bps` 等）。

### AI 研报（`ai_reports.json`）

```json
{ "id": "rpt-<timestamp>-<symbol>", "symbol": "...", "name": "...",
  "focus": "关注点", "content": "Markdown 正文", "periods": [...],
  "summary": "一句话摘要", "created_at": "ISO 时间" }
```

### 前端 store（`aiReportStore.ts`）

- `ActiveTask`：`{ id, symbol, name, focus, phase, content, error, meta }`，并发上限 `MAX_ACTIVE=3`。
- `HistoryReport`：`{ id, symbol, name, content, created_at }`，与后端报告对应，列表上限 20。

## 扩展与修改指南

- **更换/新增财务数据 Provider**：在 `data_providers/capabilities.py` 的能力注册表中扩展 `financial_data_provider` 字段；`financial_sync._fetch_table` 已对 Provider 能力缺失做显式提示（fail-closed），Provider 必须实现 `get_financial_data` 契约（见 `tests/test_financial_shares.py::test_custom_provider` 契约测试）。
- **调整同步频率**：`FinancialScheduler.start(..., auto_schedule=False)` 当前不自动定时；如需定时同步，改 `main.py:238` 调用并启用周期间隔（接口已具备 `add_job` 能力，行为待确认）。
- **修改 AI 分析提示词/结构**：改 `financial_analyzer._SYSTEM_PROMPT`（5 节 Markdown 结构与 800-1500 字数约束）与 `_build_user_prompt`；模型参数在 `ai_provider._openai_kwargs`。
- **修改报告上限**：`ai_reports.py` 的 `MAX_REPORTS=20` 与前端 `ReportHistoryPanel` 的 20 条展示需同步调整。
- **新增财务字段/表**：需同时改动 Provider 映射、`FINANCIAL_TABLES`、API 查询端点与前端 `FIELD_DEFS`；**禁止**平行新增第二套数据存储结构。
- **报表历史合并口径**：修改 `_merge_report_history` 的 PIT 逻辑时，须以 `tests/test_fuyao_financial.py::test_merge_report_history` 为回归基线，验证按列 `announce_date` 最近非空语义不变。

## 依赖关系

- **能力依赖**：`Cap.FINANCIAL`（TickFlow Expert 档）或自定义 `financial_data_provider`；能力缺失时页面/API 均 fail-closed。
- **服务依赖**：`financial_scheduler`（app.state）→ `preferences`（同步时间持久化）；`financial_analyzer` → `ai_provider` → AI 服务（OpenAI 兼容端点或 Codex CLI）。
- **存储依赖**：`data/financials/`（Parquet 表）、`data/user_data/ai_reports.json`、`data/user_data/preferences.json`；均受 `.gitignore` 数据目录约束，改动需考虑缓存链路（文件 → 前端轮询/查询缓存）。
- **前端依赖**：TanStack Query（useFinancials）、framer-motion（对话框动画）、无第三方 Markdown 库（自研 MarkdownRenderer）。

## 常见问题

- **页面提示能力不可用**：数据源非 TickFlow Expert 档且未配置自定义财务 Provider；检查 `data/user_data/preferences.json` 中数据源配置与 Provider 能力声明（`capabilities.py:72-78`）。
- **同步后数据不刷新**：前端在 `syncing` 状态才 3s 轮询；同步完成后手动刷新或等待 300s staleTime 过期（`useFinancials.ts`）。
- **同步并发触发被拒**：`FinancialScheduler._is_syncing` 防并发，`POST /sync/{table}` 返回 `{started: false, reason: ...}` 属预期行为。
- **AI 分析空数据**：`_load_stock_financials` 无数据时流返回 error 帧而非空报告（fail-closed），前端对话框进入错误阶段。
- **报告上限**：达到 20 条后 `save_report` 淘汰最旧记录；前端历史面板同步显示，无需手动清理。
- **复权与口径**：财务表为公告口径（非复权价），与行情前复权数据不可混用；比率字段为百分点直接使用，禁止 <1 乘 100。
