---
title: 异动监控 — Abnormal Moves
description: 全时段异动中心 — 竞价异动(盘前)、盘中异动(当日量价信号)、偏移异动(多日交易所偏离值)
---

# 异动监控 — Abnormal Moves

## 功能概述

异动监控是全时段异动中心，覆盖竞价（盘前 9:15–9:25）、盘中（当日量价信号聚合）、偏移（多日累计偏离值接近度）三类场景。核心定位是：

- **竞价异动**：同花顺盘前短线风向标名单（fuyao 专有），含当日/次日真实收益，用于当日观察
- **盘中异动**：从 enriched 最新快照当日信号列（涨停/炸板/跌停翘板/跌停/创60日新高/新低/放量）零新增采集聚合，按信号优先级排序展示
- **偏移异动**：按交易所异常波动/严重异常波动披露阈值实时计算个股偏离值接近度，找出处于异动边缘的标的

偏移异动计算量较大，默认关闭，开启后每 60s 轮询一次；结果保留在 localStorage 中，关闭后仍可查看。

## 文件清单

### 后端

| 文件 | 用途 |
|------|------|
| [api/abnormal.py](file:///c:/Code/tick-stock-panel/backend/app/api/abnormal.py) | 异动监控 API 路由注册（`/api/abnormal/intraday`、`/api/abnormal/overview`） |
| [services/abnormal_moves.py](file:///c:/Code/tick-stock-panel/backend/app/services/abnormal_moves.py) | 异动边缘统计核心服务：规则表、快照构建、盘中聚合、接近度计算 |
| [services/auction_benchmark.py](file:///c:/Code/tick-stock-panel/backend/app/services/auction_benchmark.py) | 竞价异动数据源：同花顺盘前风向标（fuyao 专有） |
| [api/market_recap.py](file:///c:/Code/tick-stock-panel/backend/app/api/market_recap.py) | 竞价异动 API 路由（`/api/market-recap/auction-benchmark`） |
| [indicators/pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py) | 偏离列计算（`deviate_3d`/`deviate_10d`/`deviate_30d`）、基准指数动量加载、盘中信号列生成 |
| [services/quote_service.py](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py) | 实时指数行情缓存（`get_index_quotes`）、监控轮询中异动规则评估入口 |
| [strategy/monitor.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/monitor.py) | 监控引擎中 `evaluate_abnormal` 方法：边缘触发判定、冷却抑制、告警消息 |
| [strategy/monitor_rules.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/monitor_rules.py) | 监控规则类型注册（`abnormal` 类型）、默认值与校验逻辑 |
| [tickflow/repository.py](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py) | `get_enriched_latest` 提供 enriched 最新日快照 |
| [main.py](file:///c:/Code/tick-stock-panel/backend/app/main.py) | 注册 `abnormal.router` 到 FastAPI 应用 |
| 测试 |  |
| [tests/test_abnormal_moves.py](file:///c:/Code/tick-stock-panel/backend/tests/test_abnormal_moves.py) | 偏离列附着、规则口径、快照接近度、监控规则接入（554 行） |
| [tests/test_abnormal_intraday.py](file:///c:/Code/tick-stock-panel/backend/tests/test_abnormal_intraday.py) | 盘中信号聚合：信号过滤、计数、优先级排序、空降级（75 行） |
| [tests/test_auction_benchmark.py](file:///c:/Code/tick-stock-panel/backend/tests/test_auction_benchmark.py) | 盘前风向标：交易日回退、缓存、收益 enrich、fuyao 降级（178 行） |

### 前端

| 文件 | 用途 |
|------|------|
| [pages/AbnormalMoves.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/AbnormalMoves.tsx) | 异动监控页面：三个 tab 的完整 UI（竞价/盘中/偏移） |
| [lib/api.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts) | API 类型定义（`AbnormalOverview`、`AbnormalIntradayPayload`、`AuctionBenchmarkPayload` 等）与调用函数 |
| [lib/queryKeys.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts) | TanStack Query keys：`abnormalOverview`、`abnormalIntraday` |
| [lib/storage.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/storage.ts) | localStorage 持久化：`abnormalEnabled`、`abnormalLastResult` |
| [router.tsx](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx) | 路由注册 `/abnormal` → `AbnormalMoves` |

### 数据/配置

| 文件 | 用途 |
|------|------|
| `data/auction_benchmark/date=YYYY-MM-DD.json` | 竞价历史名单 JSON 缓存（由 `auction_benchmark.py` 按日落盘） |

## 业务逻辑

### 核心流程

#### 偏移异动（Overview）

```text
[enriched 最新日快照] → [60s 进程内缓存 _hist_cache]
    → [按板块规则计算各窗口偏离值接近度]
    → [实时叠加: 今日个股涨跌 - 对应基准指数涨跌]
    → [按 min_closeness 过滤 (0.5/0.7/1.0)]
    → [按接近度降序排序 → 返回 rows]
```

1. **数据来源**：`repo.get_enriched_latest()` 返回 enriched 最新日 DataFrame，含 `deviate_3d`/`deviate_10d`/`deviate_30d` 偏离列、`change_pct` 今日涨跌幅 (`backend/app/tickflow/repository.py:1141`)
2. **历史缓存**：`_hist_snapshot()` 将 enriched 快照缓存在进程内 `_hist_cache`，TTL 60s (`backend/app/services/abnormal_moves.py:119-145`)
3. **基准指数实时涨跌**：`_bench_rt_pct()` 从 `quote_service.get_index_quotes()` 获取指数展示缓存，按板块基准键分别读取 (`backend/app/services/abnormal_moves.py:148-173`)；百分数口径显式 `/100` 转小数 (`backend/app/services/abnormal_moves.py:168`)
4. **实时叠加**：历史偏离 + 今日实时涨跌 - 对应基准指数涨跌；若 `cache_date >= 今天` 则跳过叠加（避免重复）(`backend/app/services/abnormal_moves.py:199-207`)
5. **接近度计算**：`|偏离值| / 该方向阈值`。阈值按板块：主板 3d±20%、创业板/科创板 3d±30%、北交所 3d±40%；严重异动 10d+100%/-50%、30d+200%/-70%（负向更严）(`backend/app/services/abnormal_moves.py:34-55`)
6. **状态划分**：`closeness ≥ 1.0 → triggered`、`≥ 0.7 → edge`、`≥ 0.5 → watch` (`backend/app/services/abnormal_moves.py:111-116`)
7. **过滤与排序**：按 `min_closeness` 过滤，按 `max_closeness` 降序，limit 限制行数 (`backend/app/services/abnormal_moves.py:225-253`)

#### 盘中异动（Intraday）

```text
[enriched 最新日快照] → [扫描 7 种信号列]
    → [any_horizontal 过滤信号命中行]
    → [按信号优先级排序 (涨停 > 炸板 > 翘板 > 跌停 > 新高 > 新低 > 放量)]
    → [同级按 |今日涨跌| 降序 → 返回 rows]
```

1. **数据来源**：与偏移异动同源，取 enriched 最新日快照 (`backend/app/services/abnormal_moves.py:279-281`)
2. **信号列**：7 种信号列 — `signal_limit_up`、`signal_broken_limit_up`、`signal_limit_down_recovery`、`signal_limit_down`、`signal_n_day_high`、`signal_n_day_low`、`signal_volume_surge` (`backend/app/services/abnormal_moves.py:265-273`)
3. **信号生成**：由 pipeline 在 enriched 计算时生成，`signal_limit_up` 等为布尔列 (`backend/app/indicators/pipeline.py:660-696`)
4. **过滤**：`pl.any_horizontal` 过滤出至少命中一个信号的行 (`backend/app/services/abnormal_moves.py:290`)
5. **排序**：按信号优先级（`_INTRADAY_PRIORITY`）为主序，同级按 `|change_pct|` 降序 (`backend/app/services/abnormal_moves.py:306`)
6. **计数**：返回各信号类型命中数供前端 chips 筛选 (`backend/app/services/abnormal_moves.py:293`)

#### 竞价异动（Auction）

```text
[fuyao 数据源] → [本地交易日缓存 JSON] → [收益 enrich: 本地日K现算]
    → [状态: ok / fallback_prev / source_unavailable / no_data]
```

1. **数据源**：同花顺盘前短线风向标名单，经 fuyao provider 的 `short_term_benchmark()` 获取 (`backend/app/services/auction_benchmark.py:207-208`)
2. **缓存策略**：历史日按 `date=YYYY-MM-DD.json` 缓存（不可变、纯本地，不触发插件注册表加载）；当日不缓存（竞价阶段名单可能变动）(`backend/app/services/auction_benchmark.py:194-218`)
3. **收益 enrich**：用本地 `kline_daily` 分区现算当日开盘买→收盘卖（`day0_oc`）、全天（`day0_pct`）、次日（`d1_pct`）(`backend/app/services/auction_benchmark.py:125-169`)
4. **降级**：fuyao 未配置 → `source_unavailable`；目标日拉取失败 → 回退上一交易日 `fallback_prev`；完全失败 → `no_data` (`backend/app/services/auction_benchmark.py:182-238`)
5. **回测支撑**：60 日回测 353 样本，名单当日开盘买均值 +0.54%（超额 +0.44%），高开 ≥5% 子集 -1.97%（追高陷阱）(`backend/app/services/auction_benchmark.py:6-10`)

### 数据流

#### 主路径：盘中实时热路径

```
quote_service 行情轮询 (backend/app/services/quote_service.py:1201-1217)
  → engine.has_rule_type("abnormal") 判断
  → abnormal_moves.build_overview(repo, self, min_closeness, limit=1000)
    → repo.get_enriched_latest() (backend/app/tickflow/repository.py:1141)
    → _hist_snapshot(): 60s 进程内缓存 enriched 快照 (backend/app/services/abnormal_moves.py:119)
    → _bench_rt_pct(): get_index_quotes() 获取指数实时涨跌 (backend/app/services/abnormal_moves.py:148)
    → 按板块叠加实时偏离 (backend/app/services/abnormal_moves.py:199-207)
    → 按规则计算接近度/状态 (backend/app/services/abnormal_moves.py:211-224)
  → engine.evaluate_abnormal(rows): 边缘触发判定 (backend/app/strategy/monitor.py:946)
    → 方向/窗口/scope 过滤 (backend/app/strategy/monitor.py:968-984)
    → 首轮观测不触发 (backend/app/strategy/monitor.py:1011-1012)
    → 冷却抑制 (backend/app/strategy/monitor.py:1016-1019)
    → 告警事件 (backend/app/strategy/monitor.py:1021-1047)
  → alert_handler 推送通知
```

#### 旁路：前端主动拉取

```
AbnormalMoves 页面 (frontend/src/pages/AbnormalMoves.tsx)
  → 盘中 tab: useQuery({ queryKey: QK.abnormalIntraday(500), refetchInterval: 60000 })
    → GET /api/abnormal/intraday?limit=500
      → build_intraday(repo) (backend/app/services/abnormal_moves.py:279)
  → 偏移 tab: useQuery({ queryKey: QK.abnormalOverview(minCloseness, 300), enabled })
    → GET /api/abnormal/overview?min_closeness=0.5&limit=200
      → build_overview(repo, quote_service) (backend/app/services/abnormal_moves.py:176)
  → 竞价 tab: useQuery({ queryKey: ['auction-benchmark', 'latest'], staleTime: 300000 })
    → GET /api/market-recap/auction-benchmark
      → auction_benchmark.get_auction_benchmark() (backend/app/services/auction_benchmark.py:182)
```

#### 旁路：定时任务

- 竞价异动无定时任务，由前端拉取触发
- 盘中/偏移异动由前端轮询（60s）或行情轮询线程（30s 限频）触发

### 调用链

#### 偏移异动 API

```
GET /api/abnormal/overview (backend/app/api/abnormal.py:26)
  → build_overview(repo, quote_service, min_closeness, limit) (backend/app/services/abnormal_moves.py:176)
    → _hist_snapshot(repo) (backend/app/services/abnormal_moves.py:119)
      → repo.get_enriched_latest() (backend/app/tickflow/repository.py:1141)
    → _bench_rt_pct(quote_service) (backend/app/services/abnormal_moves.py:148)
      → quote_service.get_index_quotes() (backend/app/services/quote_service.py:538)
    → rule_for(symbol, name) → AbnormalRule (backend/app/services/abnormal_moves.py:88)
    → 接近度计算 → 过滤排序 → 返回 dict
```

#### 盘中异动 API

```
GET /api/abnormal/intraday (backend/app/api/abnormal.py:16)
  → build_intraday(repo, limit) (backend/app/services/abnormal_moves.py:279)
    → repo.get_enriched_latest() (backend/app/tickflow/repository.py:1141)
    → 信号列过滤 + 优先级排序 → 返回 dict
```

#### 竞价异动 API

```
GET /api/market-recap/auction-benchmark (backend/app/api/market_recap.py:56)
  → auction_benchmark.get_auction_benchmark(data_dir, target) (backend/app/services/auction_benchmark.py:182)
    → _local_trading_days(data_dir) 确定交易日 (backend/app/services/auction_benchmark.py:41)
    → 缓存命中 → 返回缓存数据 (backend/app/services/auction_benchmark.py:195-198)
    → 缓存未命中 → provider.short_term_benchmark() (backend/app/services/auction_benchmark.py:207-208)
    → _enrich(data_dir, trade_date, items) 收益 enrich (backend/app/services/auction_benchmark.py:125)
    → 缓存落盘 → 返回前端容器 (backend/app/services/auction_benchmark.py:256-258)
```

#### 监控规则异动评估

```
quote_service 行情轮询 (backend/app/services/quote_service.py:1201-1217)
  → engine.has_rule_type("abnormal") (backend/app/strategy/monitor.py)
  → abnormal_moves.build_overview(..., min_closeness=engine.min_abnormal_closeness(), limit=1000)
  → engine.evaluate_abnormal(rows) (backend/app/strategy/monitor.py:946)
    → _evaluate_abnormal_rule(rule, rows, timestamp) (backend/app/strategy/monitor.py:968)
    → 边缘触发判定 → 告警事件 → alert_handler
```

### 偏离列计算（pipeline）

偏离列 `deviate_Nd` 在 enriched 计算中附着，有两种路径：

1. **全量冷路径**（`attach_deviation_columns`）：适用于历史全量重建，读取指数日K parquet 计算基准动量，已含 `momentum_Nd` 列的帧直接相减，缺失的按 `close.shift(N)` 补算 (`backend/app/indicators/pipeline.py:1183-1212`)
2. **盘中热路径**（`attach_deviation_columns_today`）：适用于仅今日的单日帧，使用 `momentum_Nd` + `benchmark_momentum_today` 实时外推 (`backend/app/indicators/pipeline.py:1295-1326`)

基准指数选择按板块路由（`_bench_key_expr`）：沪主板→上证A指/上证指数、科创板→科创50/上证A指、深主板→深证A指/深证成指、创业板→创业板综指/深证A指、北交所→北证50/上证指数 (`backend/app/indicators/pipeline.py:1069-1076`)

## 关键数据结构

### API 契约

#### GET /api/abnormal/overview

**请求参数**：`min_closeness`（float, 0.0–1.0, 默认 0.5）、`limit`（int, 1–1000, 默认 200）

**响应** (`frontend/src/lib/api.ts:902-916`)：
```typescript
interface AbnormalOverview {
  asof: number                    // 服务端计算时间戳（秒）
  cache_date: string | null       // enriched 数据日期
  bench_rt_pct: number            // 基准指数今日实时涨跌（小数制）
  includes_today: boolean         // 是否已含今日收盘
  rules: Array<{                  // 规则表
    board: string
    st: boolean
    thresholds: Record<string, { up: number; down: number }>
    note: string
  }>
  counts: { triggered: number; edge: number; watch: number }
  rows: AbnormalRow[]             // 个股列表
}
```

`AbnormalRow` (`frontend/src/lib/api.ts:890-900`)：
```typescript
interface AbnormalRow {
  symbol: string; board: string; st: boolean
  name: string | null; close: number | null; rt_pct: number | null
  windows: Record<string, { value: number; threshold: number; closeness: number }>
  max_closeness: number; status: 'triggered' | 'edge' | 'watch'
}
```

#### GET /api/abnormal/intraday

**请求参数**：`limit`（int, 1–2000, 默认 500）

**响应** (`frontend/src/lib/api.ts:934-937`)：
```typescript
interface AbnormalIntradayPayload {
  cache_date?: string | null
  counts?: Partial<Record<IntradaySignalKey, number>>
  rows?: AbnormalIntradayRow[]
}
```

`AbnormalIntradayRow` (`frontend/src/lib/api.ts:922-932`) — 含 `symbol`、`name`、`close`、`change_pct`（小数制）、`amplitude`（小数制）、`vol_ratio_5d`、`turnover_rate`（百分数原值）、`consecutive_limit_ups`、`signals`（按优先级排序）

#### GET /api/market-recap/auction-benchmark

**请求参数**：`date`（可选，YYYY-MM-DD）

**响应** (`frontend/src/lib/api.ts:730-737`)：
```typescript
interface AuctionBenchmarkPayload {
  state: 'ok' | 'fallback_prev' | 'source_unavailable' | 'no_data'
  requested_date?: string | null; trade_date?: string | null
  count?: number; message?: string
  items?: AuctionBenchmarkItem[]
}
```

`AuctionBenchmarkItem` (`frontend/src/lib/api.ts:719-728`) — 含 `thscode`、`ticker`、`name`、`auction_pct`（百分数原值）、`tags`、`day0_oc`（小数制）、`day0_pct`（小数制）、`d1_pct`（小数制）

### 存储结构

#### enriched Parquet

偏离列 `deviate_3d`、`deviate_10d`、`deviate_30d` 为运行时计算列，不存储在 Parquet 中（`ENRICHED_STORAGE_COLS` 不含偏离列，见 `backend/app/indicators/pipeline.py:94-103`）。由 `attach_deviation_columns`（全量）或 `attach_deviation_columns_today`（盘中）在 enriched 加载时现算。

#### 竞价缓存

`data/auction_benchmark/date=YYYY-MM-DD.json`，按日落盘不可变缓存 (`backend/app/services/auction_benchmark.py:89-90`)

### 内存结构

#### _hist_cache（异常服务进程内缓存）

`backend/app/services/abnormal_moves.py:102-105` — 线程安全全局字典，缓存 enriched 最新日快照，TTL 60s：
```python
_hist_cache: dict[str, Any] = {"data": {"_ts": float, "rows": dict, "cache_date": str}}
```

#### _benchmark_cache（pipeline 基准指数缓存）

`backend/app/indicators/pipeline.py:1086-1087` — 进程内 `(timestamp, pl.DataFrame)` 缓存，TTL 600s

#### localStorage（前端持久化）

`frontend/src/lib/storage.ts:81,84`：
- `abnormalEnabled`: boolean — 偏移异动监控开关
- `abnormalLastResult`: AbnormalOverview — 上次计算结果（关闭后展示）

## 规则口径

### 异常波动阈值

| 板块 | 3日 | 10日（严重） | 30日（严重） |
|------|-----|-------------|-------------|
| 主板 | ±20% | +100% / -50% | +200% / -70% |
| 创业板/科创板 | ±30% | +100% / -50% | +200% / -70% |
| 北交所 | ±40% | +100% / -50% | +200% / -70% |

规则来源：`backend/app/services/abnormal_moves.py:34-55`，对应上交所《交易规则(2026年修订)》5.4.2/5.4.3/6.10/6.11

**2026-07-06 起**：主板风险警示(ST)股票与普通股票同标准，原 3日±15% 特别规定已废止 (`backend/app/services/abnormal_moves.py:11-13`)

### 前端落地方案

`frontend/src/pages/AbnormalMoves.tsx:1068-1072` 有 `FALLBACK_RULES` 兜底规则表供后端数据未到时展示

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **异动监控规则**：可在监控中心创建 `type=abnormal` 的监控规则，设置接近度阈值 (`threshold_pct`)、方向 (`direction`)、窗口 (`abnormal_window`)、作用域 (`scope`/`symbols`) (`backend/app/strategy/monitor_rules.py:32-390`)
- **偏离列在选股/自选**：`deviate_3d`/`deviate_10d`/`deviate_30d` 可在自选/选股的「异动」列组中启用，并可作为监控规则与自定义信号的阈值字段 (`backend/app/indicators/pipeline.py:220`)

### L2 扩展（插槽/路由/注册替换）

- **竞价数据源**：`auction_benchmark.py` 通过 `custom_sources.get_provider("fuyao")` 获取数据源，如需替换为其他数据源，实现 `short_term_benchmark()` 方法并注册到 custom_sources 即可 (`backend/app/services/auction_benchmark.py:81-86`)
- **前端 tab**：`AbnormalMoves.tsx:55-59` 中 `TAB_META` 定义了三个 tab，可扩展新增 tab（需同步后端 API）

### L3 修改（直接改源码）

- **新增信号类型**：在 `_INTRADAY_SIGNALS` 元组添加新信号键，同步修改 pipeline 中信号列生成逻辑 (`backend/app/services/abnormal_moves.py:265-273`)
- **修改规则阈值**：直接修改 `_MAIN`/`_GEM_STAR`/`_BSE` 字典 (`backend/app/services/abnormal_moves.py:43-45`)
- **调整接近度过滤**：修改 `_status_of()` 函数中的阈值边界 (`backend/app/services/abnormal_moves.py:111-116`)

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| `_hist_cache`（进程内存） | 60s TTL 自动过期 | 偏移异动快照：`build_overview` 每次调用检查 `_ts` |
| `_benchmark_cache`（进程内存） | 600s TTL 自动过期 | 基准指数动量：`load_benchmark_momentum` 缓存 |
| 竞价 JSON 缓存（文件） | 历史日不可变，不失效；当日不缓存 | `auction_benchmark` 数据目录 |
| 前端 TanStack Query | 60s `refetchInterval` 自动刷新 | `abnormalOverview`、`abnormalIntraday` |
| 前端 localStorage | 手动关闭监控后保留，开启后更新 | `abnormalEnabled`、`abnormalLastResult` |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | [test_abnormal_moves.py](file:///c:/Code/tick-stock-panel/backend/tests/test_abnormal_moves.py) | `test_attach_deviation_columns_math`（偏离列数学）、`test_board_and_st_rules`（板块/ST 判定）、`test_build_overview_closeness_and_status`（接近度/状态）、`test_build_overview_negative_side_stricter_threshold`（负向更严阈值）、`test_bench_rt_pct_converts_percent_to_decimal`（#232 百分数转小数回归）、`test_build_overview_rt_overlay_uses_board_benchmark`（板块基准路由） |
| 单元测试 | [test_abnormal_moves.py](file:///c:/Code/tick-stock-panel/backend/tests/test_abnormal_moves.py) | `test_engine_abnormal_edge_trigger_and_cooldown`（监控规则边缘触发+冷却）、`test_engine_abnormal_direction_window_scope_filters`（方向/窗口/作用域过滤）、`test_engine_abnormal_stale_symbol_state_cleared`（跌出快照后状态清理） |
| 单元测试 | [test_abnormal_intraday.py](file:///c:/Code/tick-stock-panel/backend/tests/test_abnormal_intraday.py) | `test_counts_filter_and_priority`（信号过滤/计数/优先级）、`test_limit_truncates`（limit 截断）、`test_empty_snapshot`（空快照降级）、`test_missing_signal_columns_degrades`（缺信号列降级） |
| 单元测试 | [test_auction_benchmark.py](file:///c:/Code/tick-stock-panel/backend/tests/test_auction_benchmark.py) | `test_source_unavailable_without_fuyao`（fuyao 未配置）、`test_fetch_stores_cache_then_hits_cache`（缓存命中）、`test_failure_falls_back_to_prev`（回退上一期）、`test_enrich_math_with_local_kline`（收益 enrich 数学）、`test_build_recap_context_contains_summary`（AI 复盘摘要） |

## 依赖关系

### 依赖的其他功能

- **enriched 管道**：盘中/偏移异动强依赖 `repo.get_enriched_latest()` 提供的 enriched 最新日快照，含 `deviate_Nd` 偏离列和信号列 (`backend/app/indicators/pipeline.py`)
- **行情服务**：偏移异动依赖 `quote_service.get_index_quotes()` 获取基准指数实时涨跌 (`backend/app/services/quote_service.py:538`)
- **监控规则引擎**：`MonitorRuleEngine.evaluate_abnormal` 依赖 `build_overview` 输出的 rows 进行边缘触发判定 (`backend/app/strategy/monitor.py:946`)
- **fuyao 数据源**：竞价异动依赖 fuyao provider 的 `short_term_benchmark()` 接口 (`backend/app/services/auction_benchmark.py:207-208`)
- **本地日K**：竞价异动的收益 enrich 依赖 `kline_daily` 分区 (`backend/app/services/auction_benchmark.py:112-143`)

### 被依赖的功能

- 该功能暂未被其他功能依赖

## 常见问题与注意事项

1. **百分数/小数口径转换**：指数展示缓存（`get_index_quotes`）的 `change_pct` 列为百分数原值（如 `-1.88` 表示 -1.88%），`_bench_rt_pct` 在消费前显式 `/100` 转为小数制，与 enriched 侧 `change_pct` 小数制对齐。`#232` 回归测试覆盖该转换 (`backend/app/services/abnormal_moves.py:148-173`、`backend/tests/test_abnormal_moves.py:233-238`)

2. **实时叠加双重计数**：当 `cache_date >= today`（盘后已同步今日收盘）时，`includes_today=True`，跳过实时叠加，避免重复计入今日涨跌 (`backend/app/services/abnormal_moves.py:199`)

3. **严重异动负向阈值不对称**：10日 +100%/-50%、30日 +200%/-70%，跌方向更早触发。`threshold` 字段按偏离方向取对应侧值 (`backend/app/services/abnormal_moves.py:217`)

4. **监控规则首轮观测不触发**：为了防止新建规则刷屏，`evaluate_abnormal` 中首轮（`previous is None`）不产生告警事件 (`backend/app/strategy/monitor.py:1011-1012`)

5. **竞价异动缓存**：历史日竞价数据不可变，按 JSON 落盘缓存；当日不缓存（竞价阶段名单可能变动）。显式日期失败时回退上一交易日一次 (`backend/app/services/auction_benchmark.py:194-238`)

6. **前端开关与监控规则解耦**：偏移 tab 的「开启监控」开关仅控制前端轮询，与监控中心的「异动监控」规则互不影响；告警需要到监控中心创建规则 (`frontend/src/pages/AbnormalMoves.tsx:591-592`)