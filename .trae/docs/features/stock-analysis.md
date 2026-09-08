---
title: 个股分析（StockAnalysis）
description: 日K + 11类关键价位 + AI 四维分析（技术面/基本面/财务面/消息面），含报告持久化与价格点位提醒。
---

# 个股分析（StockAnalysis）— 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

个股分析提供「行情 + 关键价位 + AI 分析」三位一体的个股研究工具。用户选择一只股票后，可查看含 11 类关键价位（压力/支撑/枢轴/前高前低/布林带/Keltner 通道/ATR 波动通道/缺口/斐波那契/整数关口）的日 K 图，并让 AI 基于 K 线技术指标、关键价位与财务数据，生成客观中立的技术分析报告（技术面→基本面→财务面→消息面四维）。报告持久化到本地 JSON 文件，支持历史查看、删除与重新生成。功能与财务分析（financial-analysis）解耦，独立的状态池、配色（蓝色系）与对话框。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `backend/app/api/stock_analysis.py` | 4 个端点：`GET /levels`（关键价位）、`POST /analyze`（AI 流式分析）、`GET/POST/DELETE /reports`（报告 CRUD） |
| 服务 | `backend/app/services/stock_analyzer.py` | AI 四维分析核心：加载 K 线 + 财务数据 → 构建提示词 → 流式调用 LLM |
| 服务 | `backend/app/services/stock_reports.py` | 个股分析报告持久化，委托 `JsonReportStore`，存于 `ai_stock_reports.json` |
| 服务 | `backend/app/services/json_report_store.py` | AI 报告 JSON 存储共享底座（原子写、实例锁、自动裁剪） |
| 服务 | `backend/app/services/ai_provider.py` | AI 提供方抽象：`stream_ai_text` 流式调用 LLM、`build_focus_instruction` 关注点指令构建 |
| 服务 | `backend/app/services/financial_sync.py` | `get_financial_df` 读取本地财务 Parquet（`data/financials/{table}/part.parquet`） |
| 指标 | `backend/app/indicators/levels.py` | 11 类关键价位计算：`compute_levels` / `summarize_levels`（纯函数，无 IO） |
| 数据 | `backend/app/tickflow/repository.py` | `get_daily_asset` 按资产类型分流（股票/ETF/指数）读取日 K enriched 数据 |
| 主入口 | `backend/app/main.py` | `app.include_router(stock_analysis.router)` 注册路由（行 487） |
| 测试 | `backend/tests/test_stock_analyzer_index.py` | 验证指数无财务时 AI prompt 文案正确 |
| 测试 | `backend/tests/test_ai_analysis_focus.py` | 验证关注点指令在个股分析 prompt 中的集成 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/StockAnalysis.tsx` | 个股分析页面入口：搜索栏 + AI 分析按钮 + 历史侧栏 + 看板（日 K+价位） |
| 组件 | `frontend/src/components/stock-analysis/StockAnalysisHost.tsx` | 对话框宿主，单点挂载在 Layout 中，读取 store 驱动对话框显隐 |
| 组件 | `frontend/src/components/stock-analysis/StockAnalysisDialog.tsx` | AI 分析结果对话框：蓝色主题，流式渲染 Markdown，关注点输入 |
| 组件 | `frontend/src/components/stock-analysis/StockAnalysisBubble.tsx` | 全局任务气泡：拖拽丝滑，蓝色系，显示分析进度（加载/流式/完成/失败） |
| 组件 | `frontend/src/components/stock-analysis/AnalysisKChart.tsx` | 个股分析专用日 K 图：ECharts 实现，11 组价位开关按钮 + 带状曲线 |
| 组件 | `frontend/src/components/stock-analysis/PriceAlertDialog.tsx` | 价格点位提醒设置对话框，基于关键价位推荐 |
| 组件 | `frontend/src/components/StockPreviewDialog.tsx` | 个股日 K 详情对话框（复用 StockPanel），从分析页点击名称打开 |
| 组件 | `frontend/src/components/financials/StockFinancialSearch.tsx` | 股票搜索组件，支持 assetTypes 筛选 |
| Store | `frontend/src/lib/stockAnalysisStore.ts` | 全局状态管理：activeTasks、history、对话框状态，流式接收 + 自动保存 |
| API 客户端 | `frontend/src/lib/api.ts` | 5 个 API 方法：`stockAnalysisLevels`、`stockAnalysisReportsList`、`stockAnalysisReportSave`、`stockAnalysisReportDelete`、`stockAnalyzeStream`（行 3151-3214） |
| 路由 | `frontend/src/router.tsx` | 注册 `/stock-analysis` 路由（行 131），lazy load StockAnalysis 页面 |
| Layout | `frontend/src/components/Layout.tsx` | 挂载 `StockAnalysisHost` 和 `StockAnalysisBubble`（行 1055-1056） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 报告存储 | `data/user_data/ai_stock_reports.json` | 个股分析报告持久化文件，上限 50 条，自动裁剪 |

## 业务逻辑

### 核心流程

```
用户选择股票 → 加载日 K + 关键价位 + 历史报告 → 用户点击"AI 个股分析"
  → 二次确认（当日已有报告？）→ 调用 POST /api/stock-analysis/analyze
  → 后端加载 K 线(90d) → 计算关键价位 → 加载财务数据 → 构建四维提示词
  → 流式调用 LLM(NDJSON) → 前端逐 chunk 渲染 Markdown
  → 完成后自动 POST /api/stock-analysis/reports 持久化
```

### 数据流

1. **关键价位加载**（主路径）：`StockAnalysisBoard` → `useQuery('kline')` 调用 `api.klineDaily(symbol, 250)` → `GET /api/kline/daily` → `KlineRepository.get_daily`（enriched 窄表）→ 同时 `useQuery('stock-levels')` 调用 `api.stockAnalysisLevels(symbol, 250)` → `GET /api/stock-analysis/levels` → `repo.get_daily_asset` → `compute_levels(df)` → 返回 11 类价位 + 带状曲线序列 + 摘要 → 前端 `AnalysisKChart` 渲染

2. **AI 分析**（流式）：用户点击按钮 → `startAnalysis()` → `api.stockAnalyzeStream(symbol, focus)` → `POST /api/stock-analysis/analyze` → `analyze_stock_stream()` → `_load_kline(repo, symbol)`（90 日）→ `compute_levels(df)` → `_load_financials(data_dir, symbol)`（metrics + income 表，各 2 期）→ `analyze_stock_stream` 构建 `_SYSTEM_PROMPT` + `_build_user_prompt` → `stream_ai_text(messages, temperature=0.5, max_tokens=None)` → 逐 chunk yield NDJSON → 前端 `runStream()` 按 `type` 分发（meta/delta/error/done）→ `patchTask` 更新 store → `StockAnalysisDialog` 渲染 Markdown

3. **报告持久化**（旁路）：AI 流式完成后 → `api.stockAnalysisReportSave(...)` → `POST /api/stock-analysis/reports` → `stock_reports.save_report()` → `JsonReportStore.save_report()` → 原子写入 `data/user_data/ai_stock_reports.json` → 前端 `history` 更新

### 调用链

```text
前端页面入口:
  router.tsx:131 → StockAnalysis.tsx:28
  → StockAnalysisBoard (行 177)
    → api.klineDaily(symbol, 250)  → GET /api/kline/daily (行 2274)
    → api.stockAnalysisLevels(symbol, 250) → GET /api/stock-analysis/levels (行 105)
      → repo.get_daily_asset (行 125) → compute_levels(df) (行 566)
      → _build_series(df) (行 47) → 返回 levels + series + summary
  → 用户点击"AI 个股分析"
    → startAnalysis(symbol, name) (stockAnalysisStore.ts:160)
    → api.stockAnalyzeStream(symbol) → POST /api/stock-analysis/analyze (行 154)
      → analyze_stock_stream(repo, data_dir, symbol) (stock_analyzer.py:272)
        → _load_kline (行 39) → repo.get_daily_asset
        → compute_levels (行 296)
        → _load_financials (行 79) → get_financial_df (financial_sync.py:287)
        → _build_user_prompt (行 194) → 含 _SYSTEM_PROMPT + K 线 JSON + 财务 JSON + 关注点
        → stream_ai_text (ai_provider.py:323) → 流式 NDJSON
      → 完成后自动保存: api.stockAnalysisReportSave → POST /api/stock-analysis/reports (行 199)
        → stock_reports.save_report (stock_reports.py:37) → JsonReportStore (json_report_store.py:85)
  → 历史侧栏: loadHistory (stockAnalysisStore.ts:134) → api.stockAnalysisReportsList → GET /api/stock-analysis/reports
```

### 状态机（AI 分析任务）

```text
                   ┌─────────┐
                   │ loading │ ← 创建任务
                   └────┬────┘
                        │ 收到第一个 delta
                        ↓
                   ┌───────────┐
       ┌────────── │ streaming │ ──────────┐
       │           └─────┬─────┘           │
       │ 收到 error      │ 收到 done       │ 异常断流
       ↓                 ↓                 ↓
   ┌───────┐       ┌────────┐       ┌───────┐
   │ error │       │  done  │       │ error │
   └───────┘       └───┬────┘       └───────┘
                       │ 自动保存报告
                       │ 成功 → savedReportId 写入
                       ↓
                 (历史记录)
```

## 关键数据结构

### API 契约

**`GET /api/stock-analysis/levels`**

请求参数：`symbol`（标的代码）、`days`（可选，默认 120，范围 30-500）

响应：
```json
{
  "levels": {
    "sr": [{"value": 12.34, "label": "成交密集区(POC)", "type": "sr", "side": "resistance", "strength": "strong"}, ...],
    "pivot": [{"value": 12.0, "label": "枢轴位 P", "type": "pivot", "side": "neutral", "strength": "strong", "rank": 0}, ...],
    "extreme": [...],
    "boll": [...],
    "keltner_s": [...],
    "keltner_m": [...],
    "keltner_l": [...],
    "atr_stop": [...],
    "gap": [...],
    "fib": [...],
    "round": [...]
  },
  "close": 12.34,
  "summary": "当前价 12.34 · 压力支撑: ...",
  "symbol": "000001.SZ",
  "dates": ["2026-01-01", ...],
  "series": {
    "boll": {"upper": [...], "lower": [...], "mid": [...]},
    "keltner_s": {"upper": [...], "lower": [...]},
    "atr": {"stop_loss": [...], "take_profit": [...]}
  }
}
```

**`POST /api/stock-analysis/analyze`**

请求：`{"symbol": "000001.SZ", "focus": "关注分红情况"}`

响应：NDJSON 流，每行一个 JSON 事件：
- `{"type": "meta", "symbol": "...", "summary": "...", "levels": {...}, "close": 12.34}`
- `{"type": "delta", "content": "## 1. 技术面分析..."}`
- `{"type": "error", "message": "..."}`
- `{"type": "done"}`

**`GET /api/stock-analysis/reports`** → `{"reports": [AiStockReport, ...]}`

**`POST /api/stock-analysis/reports`** → 请求：`{"symbol", "name", "focus", "content", "summary", "close", "levels"}` → 响应：`{"ok": true, "report": {...}}`

**`DELETE /api/stock-analysis/reports/{report_id}`** → `{"ok": true}`

### 存储结构

**报告 JSON**（`data/user_data/ai_stock_reports.json`）：
```json
{
  "id": "sar_1719300000000_600519.SH",
  "symbol": "600519.SH",
  "name": "贵州茅台",
  "focus": "",
  "content": "# 个股分析报告\n\n## 1. 技术面...",
  "summary": "当前价 1523.45 · 压力支撑...",
  "levels": {"sr": [...], ...},
  "close": 1523.45,
  "created_at": "2026-06-26T10:00:00"
}
```

**缓存键**（前端 TanStack Query）：
- `['kline', symbol, '']` — 日 K 数据，staleTime 60s
- `['stock-levels', symbol, 120]` — 关键价位，staleTime 60s（`queryKeys.ts:84`）
- `['monitor-rules']` — 监控规则（PriceAlertDialog 使用）

### 内存结构

**`stockAnalysisStore.ts`**（全局，sync external store）：
- `activeTasks: ActiveTask[]` — 当前活跃的分析任务（上限 3 个并发）
- `history: HistoryReport[]` — 历史报告列表
- `activeDialogTaskId: string | null` — 当前打开的对话框任务 ID
- `dialogMinimized: boolean` — 对话框是否最小化

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **AI 关注点**：用户可在分析时输入 `focus` 文本，影响 AI 输出重点（`stock_analyzer.py:241` → `build_focus_instruction`）
- **AI 提供方/模型**：通过设置页切换 AI Provider 和模型，影响分析质量（`ai_provider.py`）
- **关键价位组**：前端 `AnalysisKChart.tsx:47` 的 `LEVEL_GROUPS` 可配置默认显示哪些价位组（`defaultLevelTypes` prop）

### L2 扩展（插槽/路由/注册替换）

- 该功能**未暴露** L2 前端插槽（与 `docs/secondary-development.md` 中列出的 `layout.navigation.extra` 等无关）
- 报告持久化可通过替换 `JsonReportStore` 实现自定义存储后端（需修改 `stock_reports.py` 第 29 行的构造参数）

### L3 修改（直接改源码）

- **新增价位类型**：在 `backend/app/indicators/levels.py` 的 `LEVEL_TYPES` 中添加新 key，实现计算函数，在 `compute_levels` 中注册
- **修改 AI 分析维度**：编辑 `stock_analyzer.py` 的 `_SYSTEM_PROMPT`（行 119-187）和 `_KLINE_KEEP_COLS`（行 252-265）
- **修改报告上限**：修改 `stock_reports.py` 的 `MAX_REPORTS = 50`（行 27）
- **修改并发上限**：修改 `stockAnalysisStore.ts` 的 `MAX_ACTIVE = 3`（行 48）

### 缓存失效影响

该功能的写操作仅涉及报告存储，不涉及行情缓存。

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件存储 | `data/user_data/ai_stock_reports.json` 原子写入 | 报告 CRUD 持久化 |
| 前端 Store | `stockAnalysisStore.ts` 的 `history` 数组手动更新 | 历史报告列表即时刷新 |
| 前端 Query | 无 `stock-levels` 写操作，读缓存 staleTime=60s 自动失效 | 关键价位渲染 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_stock_analyzer_index.py` | 指数无财务时 prompt 文案正确（行 5-13） |
| 单元测试 | `backend/tests/test_ai_analysis_focus.py` | 关注点指令在个股分析 prompt 中的集成与优先级 |
| 缺失 | `backend/tests/` 无 `test_stock_analysis_api.py` | 待确认：API 端点（levels/analyze/reports）尚无直接测试 |
| 缺失 | `backend/tests/` 无 `test_levels.py` | 待确认：`compute_levels` 各价位类型计算尚无直接测试 |
| 缺失 | `frontend/` 无页面级测试 | 待确认：前端组件尚无 E2E 或组件测试 |

## 依赖关系

### 依赖的其他功能

- **日 K 行情数据**（KlineRepository）：通过 `get_daily_asset` 获取 enriched 日 K（含技术指标），是价位计算与 AI 分析的数据基础
- **财务数据**（FinancialSync）：通过 `get_financial_df` 获取 `metrics` 和 `income` 表，用于 AI 分析的基本面/财务面维度
- **AI 提供方**（ai_provider.py）：`stream_ai_text` 是流式分析的核心依赖，支持 OpenAI-compatible 和 Codex CLI 两种 Provider
- **股票搜索**（instrumentSearch）：StockFinancialSearch 组件用于选择标的，搜索 API 路径 `GET /api/search/instruments`

### 被依赖的功能

- 该功能**不被**其他功能依赖，是独立的页面级功能

## 常见问题与注意事项

1. **AI 分析不含实时新闻数据**：消息面维度基于 K 线价量异动推断，前端提示"消息面维度暂依据价量异动推断"（`StockAnalysisDialog.tsx:245`）
2. **AI 不输出买卖建议**：系统提示词明确禁止输出"买入/卖出/加仓/减仓"等操作指令（`stock_analyzer.py:119-187`），报告末尾附免责声明
3. **指数/ETF 无财务数据**：指数无财务是常态，走独立文案（`stock_analyzer.py:228-233`）；Free 模式股票无财务也走"接入中"文案
4. **并发上限**：同时进行的个股分析任务不超过 3 个（`stockAnalysisStore.ts:170`）
5. **报告上限**：历史报告最多保留 50 条（`stock_reports.py:27`），超出自动裁剪最旧的
6. **日 K 数据不足**：分析需要至少 90 个交易日 K 线，无数据时返回错误提示（`stock_analyzer.py:289-292`）
7. **与财务分析的关系**：个股分析是独立功能，与财务分析（financial-analysis）使用不同的 store、组件、配色和报告存储，互不干扰
8. **Asset 类型路由**：股票/ETF/指数通过 `repo.resolve_asset_type` 分流到不同的 enriched 存储路径，确保数据正确性（`repository.py:1354-1364`）