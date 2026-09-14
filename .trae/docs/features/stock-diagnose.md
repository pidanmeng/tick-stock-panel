---
title: 智能诊股 — 功能文档
description: 同花顺「智能诊股」二开扩展（L2）：A 股全量/指定集合的诊股评分快照落盘 + 单只实时详情浮层，复用扩展数据机制与前端扩展插槽。
---

# 智能诊股 — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

「智能诊股」是同花顺（10jqka）私有诊股接口（`eq/dq.10jqka.com.cn`，抓包文档化，见 `.trae/skills/10jqka-stock-diagnose/`）的 L2 二开扩展。它解决"对沪深 A 股批量获取/浏览六维诊股评分（资金/技术/估值/消息/财务 + 平均分）"，并支持对单只展开财务六能力/资金/估值/公告研报的实时详情。

- **定位**：全站新增一个独立扩展页面（`/diagnose`），长线价值口径，刷新仅由页面手动按钮触发（无自动定时）。
- **核心机制**：批量评分以**扩展数据快照表**落盘（`data/ext_data/ths_diagnose/`，复用 ext-data 机制）；单只详情实时调用外部接口（不落盘）。
- **实现形态**：后端 `backend/app/custom/ths_diagnose/` + 前端 `frontend/src/custom/diagnose/`，通过扩展自动发现装配，零核心接线改动。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 入口 | `backend/app/custom/ths_diagnose/__init__.py` | `EXTENSION_ID="ths.diagnose"`、`setup()` 注册路由；无 startup 钩子 |
| 客户端 | `backend/app/custom/ths_diagnose/client.py` | 9 个私有接口 HTTP 调用、双信封判据、单次退避重试、并发信号量 |
| 解析 | `backend/app/custom/ths_diagnose/parsers.py` | 接口响应→规范化结构 / 快照行（str→float、缺值→None） |
| 服务 | `backend/app/custom/ths_diagnose/service.py` | 标的过滤、批量拉取+进度、快照落盘、prefs 偏好 |
| API | `backend/app/custom/ths_diagnose/api.py` | `prefix=/api/custom/ths-diagnose` 全部端点 |
| 测试 | `backend/tests/custom/test_ths_diagnose_parsers.py` | 解析器单测 |
| 测试 | `backend/tests/custom/test_ths_diagnose_http.py` | HTTP 客户端单测（MockTransport） |
| 测试 | `backend/tests/custom/test_ths_diagnose_snapshot.py` | service 快照/进度/prefs 单测 |
| 测试 | `backend/tests/custom/test_ths_diagnose_api.py` | API 路由/校验/扩展发现/详情装配测试 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 注册 | `frontend/src/custom/diagnose/extension.tsx` | 路由、导航、两个插槽注册 |
| 页面 | `frontend/src/custom/diagnose/DiagnosePage.tsx` | 快照表格、分组、筛选排序、拉取操作 |
| 详情 | `frontend/src/custom/diagnose/DiagnoseDetailDialog.tsx` | 单只实时详情浮层（五分区） |
| 图表 | `frontend/src/custom/diagnose/EChart.tsx` | 轻量 echarts 容器 |
| 进度 | `frontend/src/custom/diagnose/useDiagnoseProgress.ts` | 全局拉取进度轮询 |
| 菜单条 | `frontend/src/custom/diagnose/SyncStatusNav.tsx` | 左侧菜单同步状态条 |
| 摘要 | `frontend/src/custom/diagnose/FooterSummary.tsx` | 个股弹窗底部诊股摘要入口 |
| API | `frontend/src/lib/api.ts` | `thsDiagnose*` 函数族 + 诊断类型 |
| 缓存键 | `frontend/src/lib/queryKeys.ts` | `diagnoseConfig/Snapshot/Progress/Stock` |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 快照配置 | `data/ext_data/ths_diagnose/config.json` | 扩展数据配置（首拉懒创建，snapshot 模式） |
| 快照数据 | `data/ext_data/ths_diagnose/part.parquet` | 评分快照行（按 symbol 去重 keep-last） |
| 偏好 | `data/user_data/ths_diagnose.json` | 记忆上次 universe 与 include_trend |
| 接口文档 | `.trae/skills/10jqka-stock-diagnose/SKILL.md` + `references/api.md` | 9 接口抓包文档与字段口径 |
| 计划书 | `.trae/documents/ths-diagnose-page-plan.md` | 实施计划（MVP 已实现，部分扩展规划中） |

## 业务逻辑

### 核心流程

**A. 批量快照拉取（手动触发）**

```text
页面「更新诊股快照」→ POST /snapshot/pull (scope=symbols|all)
  → filter_stock_symbols 经 instruments 维表过滤（fail-closed）
  → asyncio.create_task(pull_snapshot) → 逐只 fetch_one
      ├─ 必拉 get_score（六维分）
      └─ include_trend 时补 finance_ablility + fund_comprehensive
  → 收集行 → pl.DataFrame → rows_to_parquet(part.parquet) 落盘
  → 前端轮询 /snapshot/progress，完成后 invalidate 快照查询刷新表格
```

**B. 单只实时详情（打开详情浮层时）**

```text
行点击/FK 弹窗入口 → /diagnose?symbol= → DiagnoseDetailDialog
  → 并行拉 5 组端点：summary / finance / fund / message / valuation（实时，不落盘）
  → 分区级 loading/error 独立隔离展示
```

### 数据流

1. **输入来源**：
   - 快照拉取：页面手动 POST（`scope=all` 走 A 股全量维表，或给定 symbols 列表）[api.py:76-107](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/api.py#L76-L107)。
   - 标的合法性以 `data/instruments/instruments.parquet`（type=stock 且 exchange∈{SH,SZ}）为准，[service.py:116-158](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/service.py#L116-L158)。
2. **处理过程**：client 限流并发拉数 -> parsers 规范化（str 分数→float、缺字段→None）-> `to_snapshot_row` 组装快照行 [parsers.py:97-117](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/parsers.py#L97-L117)。
3. **输出去向**：`rows_to_parquet` 写 `part.parquet`（snapshot 模式按 symbol 去重，支持多批累积）[service.py:244-246](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/service.py#L244-L246)；`read_snapshot`/`snapshot_meta` 供 `/snapshot`、`/config` 读取 [service.py:278-305](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/service.py#L278-L305)。

### 调用链

**快照拉取链**

```text
DiagnosePage.doPull (DiagnosePage.tsx:155-165)
  → api.thsDiagnoseSnapshotPull (api.ts:3135)
  → POST /api/custom/ths-diagnose/snapshot/pull (api.py:76)
  → service.filter_stock_symbols / all_stock_symbols (service.py:138/161)
  → asyncio.create_task(service.pull_snapshot) (api.py:94-99)
  → service.fetch_one (service.py:252) → client.get_score / finance_ablility / fund_comprehensive
  → parsers.to_snapshot_row (parsers.py:97)
  → rows_to_parquet → part.parquet (service.py:244-246)
→ 前端轮询 useDiagnoseProgress (1.5s, useDiagnoseProgress.ts:16-19)
  → GET /snapshot/progress (api.py:113) → 完成后 invalidate QK.diagnoseSnapshot
```

**详情实时链**

```text
DiagnoseDetailDialog 并行 (DiagnoseDetailDialog.tsx:103-127)
  → api.thsDiagnoseStockSummary/Finance/Fund/Message/Valuation (api.ts:3156-3181)
  → GET /api/custom/ths-diagnose/stock/{symbol}/{summary|finance|fund|message|valuation} (api.py:145-217)
  → client.get_score / finance_ablility(+analysis/history) / fund_comprehensive(+summary/history) / message / valuation
  → parsers.summary/finance/fund/message/valuation_section  (parsers.py:123-287)
  → EChart / 文本渲染
```

### 状态机（拉取进度）

模块级 `service._progress` dict 记录拉取状态 [service.py:169-179](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/service.py#L169-L179)：

| 状态 | 判定 | 转换 |
|------|------|------|
| `running` | False→True | `pull_snapshot` 入口置 True；`finally` 置 False |
| `done` | 0→total | 逐只递增（含成功与失败） |
| `ok` | 成功行数 | row 非空则 +1 |
| `failed` / `failed_symbols` / `warnings` | 单只异常 | 记录失败 symbol 与截断原因 |
| `started_at` / `finished_at` | 时间戳 | 开始/结束写入 |

单次运行约定：任务进行中再次触发 `pull_snapshot` 抛 `RuntimeError`，由 api 层转 409 [api.py:100-101](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/api.py#L100-L101)。

## 关键数据结构

### API 契约

路由前缀 `prefix=/api/custom/ths-diagnose` [api.py:20](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/api.py#L20)：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/config` | 快照元信息 + running + universe + include_trend + cap + fields |
| GET | `/snapshot` | 返回快照 rows（上限 20000）与 date |
| POST | `/snapshot/pull` | body `{symbols, include_trend, scope}`；scope=all 走全 A（cap 6000） |
| GET | `/snapshot/progress` | 拉取进度 dict |
| POST | `/snapshot/clear` | 清空 part.parquet（保留 config） |
| GET | `/stock/{symbol}/summary` | 总评（六维分 + 亮点风险 + 财务/估值/消息概览） |
| GET | `/stock/{symbol}/finance?ability_id=` | 财务六能力 + 亮点/风险 + 可选历史 |
| GET | `/stock/{symbol}/fund?history=` | 资金评分 + 可选 one-month/one-year 序列 |
| GET | `/stock/{symbol}/message` | 公告/研报要点 |
| GET | `/stock/{symbol}/valuation?index=&period=` | 估值分位（index: pb/pe/pof/ps；period: 1/3/5/10） |
| GET/POST | `/prefs` | 偏好读写（universe / include_trend） |

前端类型定义见 [api.ts:320-407](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L320-L407)（`DiagnoseRow/Config/Progress/Snapshot/ScoreSet/SummarySection`）。外部接口信封判据（双信封）见 [client.py:40-46](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/client.py#L40-L46)。

### 存储结构

快照表 schema（ExtConfig `fields`，26 列，见 [service.py:37-64](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/service.py#L37-L64)；以源码为准）：

| 字段 | dtype | 说明 |
|------|-------|------|
| symbol / code / name | string | 代码（带后缀）/ 裸代码 / 名称 |
| snapshot_date | string | 快照日期（get_score `date`） |
| industry_name / industry_code | string | 同花顺行业 |
| rank_industry / rank_market | int | 行业/市场排名 |
| total_industry / total_market | int | 行业/市场总数 |
| score_fund / score_tech / score_valuation / score_message / score_finance | float | 五维分（满分 5） |
| score_average | float | 平均分 |
| score_delta | float | 变化分 |
| fund_chg | float | 资金较昨日（fund_score_minus） |
| finance_total / finance_prev | float | 财务总分 / 上年同期总分 |
| abl_profit / abl_growth / abl_operate / abl_cash / abl_pay / abl_asset | float | 六能力当期分 |

落盘位置：`data/ext_data/ths_diagnose/config.json` + `part.parquet`（snapshot 模式，按 symbol 去重 keep-last，支持多批累积）。

### 内存结构

- `service._progress`：模块级拉取进度 dict（见状态机节）。
- `client` 模块级单例 `_client`（惰性创建）+ `asyncio.Semaphore(32)` + 最小间隔锁 [client.py:201-211](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/client.py#L201-L211)。
- `api._tasks`：持有 asyncio task 引用防 GC（[api.py:98-99](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/api.py#L98-L99)）。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- 快照数据是一张标准 ext-data snapshot 表，可在「数据管理/扩展数据」中查看，也可被其他 ext-data 消费者读取。
- prefs 文件（`data/user_data/ths_diagnose.json`）可手动编辑记忆 universe 与 include_trend。

### L2 扩展（插槽/路由/注册替换）

- 前端路由 `/diagnose`、导航项与两个插槽（`stock-preview.footer`、`layout.navigation.extra`）均由 `extension.tsx` 注册 [extension.tsx:13-34](file:///c:/Code/tick-stock-panel/frontend/src/custom/diagnose/extension.tsx#L13-L34)，属本项目已开放的 L2 插槽。
- 后端所有路由挂在 `/api/custom/ths-diagnose`，通过扩展 loader 自动装配；替换 `client.py` 可切换到其他诊股数据源（保持同签名）。

### L3 修改（直接改源码）

- `client.py` 并发/间隔/重试参数（`_DEFAULT_CONCURRENCY`=32、`_INTERVAL`=0、`_RETRIES`=1，[client.py:32-35](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/client.py#L32-L35)）：私有接口无鉴权，禁止放大并发/重试，防风控。
- `service.FIELDS`（快照列）改动需同步前端 `DiagnoseRow` 类型与页面渲染列，避免 contract 漂移。
- 新增外部接口需同步 `.trae/skills/10jqka-stock-diagnose/` 文档并保持信封判据逐接口区分。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件/Parquet 缓存 | 拉取完成经 `rows_to_parquet` 重写 `part.parquet`；`/snapshot/clear` 删除 | ext-data 快照读取 |
| 内存缓存 | `_progress` dict 随任务生命周期更新 | `/snapshot/progress`、页面进度条 |
| query 缓存（前端） | 拉取 running→完成时 `invalidate` `QK.diagnoseConfig/Snapshot`（DiagnosePage.tsx:130-143） | 快照表格刷新 |
| SSE/前端推送 | **无**——本功能不进 `SSE_INVALIDATE_PREFIXES`（手动刷新，无 SSE 实时） | 无 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/custom/test_ths_diagnose_parsers.py` | 双信封判据、str→float、缺字段→None、快照行组装 |
| 单元测试 | `backend/tests/custom/test_ths_diagnose_http.py` | mock transport：URL/query/market 推导、status 差异、5xx 退避、拒绝非股票 |
| 单元测试 | `backend/tests/custom/test_ths_diagnose_snapshot.py` | 配置幂等、merge keep-last、分批累积、clear、进度、fail-closed、prefs round-trip |
| API 测试 | `backend/tests/custom/test_ths_diagnose_api.py` | 路由前缀、`_symbol_or_400`、空拉取 400、扩展发现、详情端点 stub client 装配 |
| 前端 | 无单测基建 → `pnpm build` 通过 + 手测 | 路由/导航出现、拉取进度与失败重试、分组筛选排序、详情五分区、FK 弹窗摘要入口 |

## 依赖关系

### 依赖的其他功能

- [数据管理 Data](data-management.md)：复用 ext-data 机制（`ExtConfigStore`、`rows_to_parquet`）做快照落盘。
- [整体架构与基础设施](architecture-and-infrastructure.md)：扩展 loader 自动发现 `app/custom/` 子包并注册路由。
- instruments 维表（`data/instruments/instruments.parquet`）：标的过滤数据源，缺失时 fail-closed。
- 前端扩展机制（`extensions/bootstrap`）：路由/导航/插槽装配。

### 被依赖的功能

- 暂无其他核心功能依赖本扩展；规划中"诊股分数并入 enriched 帧"（供 Screener/自定义信号/回测引用）**尚未实现**，属规划中能力。

## 常见问题与注意事项

- **外部接口可用性**：`eq/dq.10jqka.com.cn` 为无鉴权私有接口，可能随时风控；客户端限流+单次重试，429 直接报错不放大（[client.py:106-108](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/client.py#L106-L108)）。失败按单只记录在 `failed_symbols/warnings`，可仅重拉失败项。
- **数据结构完整性**：指标缺失不填 0，统一置 None（`float_or_none`，[parsers.py:27-43](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/parsers.py#L27-L43)），避免臆造金融结果。
- **数据新鲜度**：只手动刷新，跨交易日可能陈旧；页面展示快照 `snapshot_date`/`date` 并提示，由用户点更新。
- **性能**：全 A（约 5k 只）拉取耗时较长；`include_trend` 开启时每只 3 请求。关闭趋势列可显著加速（每只 1 请求）。
- **消息面口径**：`score_message` 常年 2.5（无消息刺激），筛选/展示时避免误解（详情弹窗有 tooltip 类提示）。
- **规划中（未实现）**：盘后自动定时刷新、跨日趋势筛选的下沉到过滤器、诊股分数列并入 enriched 帧供其他模块引用（见 `.trae/documents/ths-diagnose-page-plan.md` §8）。
- **市场映射**：仅沪深 A 股（SH→17、SZ→33），不含 ETF/指数/北交所；非股票输入在过滤阶段被拒绝（[service.py:99-113](file:///c:/Code/tick-stock-panel/backend/app/custom/ths_diagnose/service.py#L99-L113)）。