---
title: 指数 Indices — 功能文档
description: 指数功能（核心四只指数实时行情、日K/分时走势、日K同步）的完整实现参考。
---

# 指数 Indices — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

指数功能提供 A 股核心四只指数（上证指数 000001.SH、深证成指 399001.SZ、创业板指 399006.SZ、科创综指 000680.SH）的实时行情概览、日K（含技术指标）走势图、分钟分时走势图，以及手动/定时日K同步能力。指数数据使用独立 `kline_index_*` Parquet 存储，与股票数据完全隔离，不进入选股、策略、回测链路。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `backend/app/api/indices.py` | 指数日K/分钟K读取、标的同步、日K同步三个端点 |
| 实时行情 API | `backend/app/api/intraday.py` | `/api/intraday/indices` 实时指数行情缓存读取（含兜底回退） |
| 核心常量 | `backend/app/services/index_const.py` | 核心四只指数 symbol/name 映射单一权威 |
| 同步服务 | `backend/app/services/index_sync.py` | 指数/ETF 标的维表同步、日K同步与 enriched 写入 |
| 实时行情服务 | `backend/app/services/quote_service.py` | 实时指数行情缓存管理、fetch 循环中构建指数缓存 |
| 日K实时补拉 | `backend/app/services/kline_sync.py` | `sync_daily_batch` 批量日K拉取、`fetch_minute_single` 分钟K实时拉取 |
| 仓库层 | `backend/app/tickflow/repository.py` | 指数日K/维表读写、DuckDB 视图刷新、enriched 即时计算 |
| 指标管道 | `backend/app/indicators/pipeline.py` | `compute_indicators`/`compute_signals`/`compute_enriched`、`ENRICHED_STORAGE_COLS`、`BENCHMARK_INDEX_SYMBOLS` |
| 盘后管道 | `backend/app/jobs/daily_pipeline.py` | 定时同步指数维表与日K（盘后 15:35 默认） |
| 偏好配置 | `backend/app/services/preferences.py` | `get_index_daily_batch_size` 指数同步批次大小 |
| 策略层 | `backend/app/strategy/market_data.py` | `get_index_daily` 策略层只读指数日K封装 |
| 大盘总览 | `backend/app/services/market_overview_builder.py` | 看板总览消费核心四只指数实时行情 |
| 大盘总览 API | `backend/app/api/overview.py` | `/api/overview/market` 返回核心指数行情块 |
| 大盘复盘 | `backend/app/services/market_recap.py` | AI 复盘报告包含指数涨跌板块 |
| 概念轮动 | `backend/app/services/concept_rotation_analyzer.py` | 消费总览中的指数数据 |
| 能力路由 | `backend/app/tickflow/capabilities.py` | `Cap.KLINE_DAILY_BATCH` 等门控 |
| 应用入口 | `backend/app/main.py` | `include_router(indices.router)` 注册 API 路由 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Indices.tsx` | 指数页面主体：实时行情栏、日K蜡烛图、分时图、同步按钮 |
| 布局 | `frontend/src/components/Layout.tsx` | 侧边栏指数条（固定四只指数实时行情） |
| API 客户端 | `frontend/src/lib/api.ts` | `indexQuotes`/`indexDaily`/`indexMinute`/`syncIndexDaily`/`syncIndexInstruments` |
| Query Key | `frontend/src/lib/queryKeys.ts` | `QK.indexQuotes`/`indexDaily`/`indexMinute`、SSE 失效前缀 `index-quotes` |
| 路由 | `frontend/src/router.tsx` | `/indices` 路由懒加载 `Indices` 组件 |
| 数据管理页 | `frontend/src/pages/Data.tsx` | 数据管理页也使用 `syncIndexDaily` 发起指数同步 |
| 蜡烛图组件 | `frontend/src/components/EChartsCandlestick.tsx` | 日K蜡烛图渲染 |
| 分时图组件 | `frontend/src/components/EChartsIntraday.tsx` | 分钟分时图渲染 |
| 能力查询 | `frontend/src/lib/useSharedQueries.ts` | `useCapabilities` 判断 `kline.minute.batch` 能力 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| Parquet 目录 | `data/kline_index_daily/` | 指数日K原始数据（日分区） |
| Parquet 目录 | `data/kline_index_enriched/` | 指数日K enriched 数据（14 列窄表，含通用技术指标） |
| Parquet 目录 | `data/kline_etf_daily/` | ETF 日K原始数据 |
| Parquet 目录 | `data/kline_etf_enriched/` | ETF 日K enriched 数据 |
| 维表文件 | `data/instruments_index/instruments_index.parquet` | 指数标的维表 |
| 维表文件 | `data/instruments_etf/instruments_etf.parquet` | ETF 标的维表 |

### 测试

| 文件 | 路径 | 用途 |
|------|------|------|
| 自定义源指数协议 | `backend/tests/test_custom_provider_indices.py` | 自定义数据源 `get_realtime_indices` 协议测试 |
| Fuyao 指数快照 | `backend/tests/test_fuyao_provider.py` | Fuyao 插件指数快照映射、BJ 过滤、错误处理 |
| 策略层指数日K | `backend/tests/test_strategy_market_data.py` | `get_index_daily` 委托与日期归一化 |
| 资产路由日K | `backend/tests/test_daily_batch_asset.py` | 资产类型路由 `get_index_daily` |

## 业务逻辑

### 核心流程

指数功能分为三条独立路径：

**路径 A：实时行情（指数条 + 页面顶部行情块）**

```text
TickFlow 轮询(fetch 循环) → 过滤出指数记录 → _build_index_quotes → _index_quotes_cache
    → API /api/intraday/indices → 前端 api.indexQuotes() → Layout 侧边栏 + Indices 页面
```

**路径 B：日K 读取（蜡烛图 + 技术指标）**

```text
前端选择指数 → GET /api/index/daily → repo.get_index_daily()
    → 快路径(列下推，仅需存储列) / 慢路径(scan enriched + 即时 compute_indicators/signals)
    → 本地无数据且有能力 → 实时补拉 sync_daily_batch + compute_enriched → 返回 "live"
```

**路径 C：日K 同步（手动/定时）**

```text
手动：前端按钮 → POST /api/index/sync_daily → 维表同步 → 分批次拉取 → 写入
    kline_index_daily + compute_enriched → 写入 kline_index_enriched → refresh_index_views
定时：daily_pipeline 盘后 15:35 → run_now → 同上流程
```

### 数据流

1. **实时行情输入来源**：`quote_service._fetch_loop` 从 TickFlow 轮询全市场行情，过滤出指数记录（包含 `CORE_INDEX_SYMBOLS` + `BENCHMARK_INDEX_SYMBOLS` + 监控规则中的指数标的），构建 `_index_quotes_cache`。`quote_service.py:1008-1039`
2. **实时行情输出**：`/api/intraday/indices` 直接返回缓存，不触发 TickFlow 请求。缓存为空时，从 `kline_index_daily` DuckDB 视图取最近收盘价做兜底（`_fallback_index_quotes_from_daily`，[intraday.py:27-84](file:///c:/Code/tick-stock-panel/backend/app/api/intraday.py#L27-L84)）。
3. **日K 输入**：`repo.get_index_daily` 优先从本地 `kline_index_enriched` Parquet 读取（`_scan_index_daily_symbol`），无数据时通过 TickFlow `kline_sync.sync_daily_batch` 实时补拉。
4. **日K 处理**：指数 enriched 只计算通用技术指标（`compute_indicators` + `compute_signals`），跳过涨跌停/股本/市值逻辑（`_compute_index_enriched_range`，[repository.py:1708-1718](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L1708-L1718)）。
5. **分钟K**：实时拉取，不写入本地 Parquet。依赖 `kline.minute.batch` 能力（`kline_sync.fetch_minute_single`，[kline_sync.py:1219-1255](file:///c:/Code/tick-stock-panel/backend/app/services/kline_sync.py#L1219-L1255)）。
6. **日K 同步写路径**：`sync_and_persist_index_daily`（[index_sync.py:192-254](file:///c:/Code/tick-stock-panel/backend/app/services/index_sync.py#L192-L254)）先同步维表，然后按 `batch_size` 分批次调用 `sync_daily_batch`，依次写入 `kline_index_daily`、计算 enriched、写入 `kline_index_enriched`，最后 `refresh_index_views` 重建 DuckDB 视图。

### 调用链

**实时行情（盘中热路径）**

```text
quote_service._fetch_loop (quote_service.py:670-857)
  → 拉取全市场行情，过滤指数记录
  → _build_index_quotes (quote_service.py:1008-1039) → _index_quotes_cache
  → API /api/intraday/indices (intraday.py:97-113)
    → 兜底: _fallback_index_quotes_from_daily (intraday.py:27-84)
  → 前端 api.indexQuotes() (api.ts:2111-2114)
    → Layout 侧边栏 (Layout.tsx:474-479)
    → Indices 页面 (Indices.tsx:93-97)
  → SSE quotes_updated → invalidate 'index-quotes' 前缀 (queryKeys.ts:139)
```

**日K 读取（用户交互）**

```text
前端 Indices.tsx:99-104 → api.indexDaily() → GET /api/index/daily (indices.py:31-62)
  → _index_info (indices.py:20-27) 读取指数维表元信息
  → repo.get_index_daily (repository.py:1488-1514)
    → 快路径: _scan_index_daily_symbol (列下推)
    → 慢路径: _scan_index_daily_symbol (全列) → _compute_index_enriched_range (repository.py:1708-1718)
      → compute_indicators + compute_signals (pipeline.py)
  → 本地空且有能力: kline_sync.sync_daily_batch (kline_sync.py) → compute_enriched (pipeline.py:1002)
  → 返回 {symbol, rows, source}
```

**分钟K（用户交互）**

```text
前端 Indices.tsx:106-111 → api.indexMinute() → GET /api/index/minute (indices.py:65-83)
  → kline_sync.fetch_minute_single (kline_sync.py:1219-1255, asset_type="index")
    → 优先自定义分钟源 → 回退 TickFlow klines.batch 1m
  → 返回 {symbol, date, rows, source}
```

**日K 同步（手动/定时）**

```text
手动触发: 前端按钮 (Indices.tsx:113-119) → POST /api/index/sync_daily (indices.py:94-108)
定时触发: daily_pipeline (daily_pipeline.py:520-561) → run_now
  → index_sync.sync_index_instruments (index_sync.py:115-179)
    → _fetch_instruments_by_type (index_sync.py:77-112)
      → tf.exchanges.get_instruments(SH/SZ/BJ, "index")
      → 付费补充: tf.quotes.get_by_universes(CN_Index)
    → repo.save_index_instruments (repository.py:2051-2061)
  → index_sync.sync_and_persist_index_daily (index_sync.py:192-254)
    → chunked(symbols, batch_size) + sleep_between_batches
    → kline_sync.sync_daily_batch (kline_sync.py)
    → repo.append_index_daily (repository.py:2003-2007)
    → compute_enriched (pipeline.py:1002)
    → repo.append_index_enriched (repository.py:2009-2016)
    → repo.refresh_index_views (repository.py:2076-2100)
  → 前端: invalidate QK.indexQuotes + ['index-daily'] (Indices.tsx:115-118)
```

### 状态机

指数功能本身无状态机，但 `quote_service` 的实时行情轮询有运行/暂停状态（`_paused`、`_enabled`、`_running`）。指数同步有"正在同步"状态（`syncDaily.isPending`）、"本地有数据" / "本地无数据" / "实时补拉"等响应状态。

## 关键数据结构

### API 契约

**GET /api/intraday/indices** — 实时指数行情（[intraday.py:97-113](file:///c:/Code/tick-stock-panel/backend/app/api/intraday.py#L97-L113)）

```jsonc
{
  "rows": [{
    "symbol": "000001.SH",
    "name": "上证指数",
    "last_price": 3150.25,
    "prev_close": 3140.50,
    "open": 3145.00,
    "high": 3160.00,
    "low": 3140.00,
    "volume": 123456789,
    "amount": 23456789012.34,
    "change_pct": 0.31,            // 百分数（如 0.31 = 0.31%）
    "change_amount": 9.75,
    "amplitude": 0.64,
    "timestamp": 1700000000000,
    "session": "afternoon"
  }],
  "count": 4,
  "source": "realtime" | "index_daily"
}
```

**GET /api/index/daily** — 指数日K（[indices.py:31-62](file:///c:/Code/tick-stock-panel/backend/app/api/indices.py#L31-L62)）

```jsonc
{
  "symbol": "000001.SH",
  "name": "上证指数",
  "index_info": { "symbol": "000001.SH", "name": "上证指数", "code": "000001", "asset_type": "index" },
  "rows": [{
    "symbol": "000001.SH",
    "date": "2024-01-15",
    "open": 3145.00,
    "high": 3160.00,
    "low": 3140.00,
    "close": 3150.25,
    "volume": 123456789,
    "amount": 23456789012.34,
    "ma5": 3120.50,
    "ma10": 3100.80,
    "ma20": 3080.20,
    "ma60": 3050.10,
    "macd_dif": 12.5,
    "macd_dea": 10.2,
    "macd_hist": 2.3,
    "rsi_6": 55.5,
    "rsi_14": 52.0,
    "rsi_24": 50.1,
    "kdj_k": 60.0,
    "kdj_d": 55.0,
    "kdj_j": 70.0,
    "boll_upper": 3200.0,
    "boll_lower": 3080.0
  }],
  "source": "index_enriched" | "live" | "none"
}
```

**GET /api/index/minute** — 指数分钟K（[indices.py:65-83](file:///c:/Code/tick-stock-panel/backend/app/api/indices.py#L65-L83)）

```jsonc
{
  "symbol": "000001.SH",
  "name": "上证指数",
  "index_info": {},
  "date": "2024-01-15",
  "rows": [{
    "datetime": "2024-01-15 09:31:00",
    "open": 3145.00,
    "high": 3146.00,
    "low": 3144.50,
    "close": 3145.50,
    "volume": 123456,
    "amount": 23456789.01
  }],
  "source": "live" | "none"
}
```

### 存储结构

**kline_index_enriched Parquet（14 列存储窄表）** — 复用 [pipeline.py:94-103](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L94-L103) 的 `ENRICHED_STORAGE_COLS`：

| 列名 | 口径 | 说明 |
|------|------|------|
| symbol | str | 指数代码，如 `000001.SH` |
| date | date | 交易日期 |
| open/high/low/close | float64 | 前复权价 |
| volume/amount | float64 | 成交量/成交额 |
| raw_close/raw_high/raw_low | float64 | 不复权原始价（指数无复权，与 close 一致） |
| turnover_rate | float64 | 百分数（如 `5.0` = 5%） |
| consecutive_limit_ups/downs | int32 | 指数无涨跌停，恒为 0 |
| quote_ts | int64 | 行情时间戳(ms) |

**kline_index_daily Parquet** — 原始日K数据，列结构类似但无技术指标。

**instruments_index/instruments_index.parquet** — 指数标的维表（[repository.py:2051-2061](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L2051-L2061)）：

| 列名 | 口径 | 说明 |
|------|------|------|
| symbol | str | 指数代码 |
| name | str | 指数名称 |
| code | str | 纯数字代码 |
| asset_type | str | `"index"` |

### 内存结构

**quote_service 指数缓存**（[quote_service.py:538-546](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py#L538-L546)）：

- `_index_quotes_cache: pl.DataFrame` — 每轮 fetch 刷新，含 `symbol`/`name`/`last_price`/`prev_close`/`open`/`high`/`low`/`volume`/`amount`/`change_pct`(百分数)/`change_amount`/`amplitude`/`timestamp`/`session`
- `_index_symbol_count: int` — 缓存中的指数数量
- `_index_instruments_cache: pl.DataFrame` — 指数维表内存缓存，懒加载，文件变更时失效（[repository.py:1307-1313](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L1307-L1313)）
- `_index_symbol_set_cache: set[str]` — 指数 symbol 集合 memo（[repository.py:1336-1343](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L1336-L1343)）

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

目前**无** L1 扩展点：核心四只指数是产品级固定契约，不可通过配置或策略文件修改。`index_const.py` 注释明确注释"不开放配置"（[index_const.py:1-8](file:///c:/Code/tick-stock-panel/backend/app/services/index_const.py#L1-L8)）。

`index_daily_batch_size` 可通过偏好配置调整（[preferences.py:537-539](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L537-L539)），但只影响同步性能，不改变功能行为。

### L2 扩展（插槽/路由/注册替换）

- **自定义数据源中的指数实时行情**：自定义 Provider 可实现 `get_realtime_indices(symbols) -> list[dict] | None` 协议，TSP 将其纳入实时行情轮询。测试见 [test_custom_provider_indices.py](file:///c:/Code/tick-stock-panel/backend/tests/test_custom_provider_indices.py)。
- **Fuyao 插件**：实现了 `get_realtime_indices`，将 Fuyao 指数快照映射为统一格式（[fuyao/provider.py:443](file:///c:/Code/tick-stock-panel/backend/app/plugins/fuyao/provider.py#L443)）。
- 指数功能本身**没有**提供前端插槽或后端注册替换点。

### L3 修改（直接改源码）

**增加/减少核心指数**：需同步修改 4 处：

1. 后端权威常量 [index_const.py:11-16](file:///c:/Code/tick-stock-panel/backend/app/services/index_const.py#L11-L16)（`CORE_INDEX_NAMES`）
2. 前端页面硬编码 [Indices.tsx:57-62](file:///c:/Code/tick-stock-panel/frontend/src/pages/Indices.tsx#L57-L62)（`PINNED_INDEXES`）
3. 前端侧边栏硬编码 [Layout.tsx:75-80](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L75-L80)（`CORE_INDEXES`）
4. 如果新指数还需要出现在大盘总览/复盘等功能中，需确认 `market_overview_builder.py` 和 `overview.py` 是否也引用了 `CORE_INDEX_SYMBOLS`（它们已引用 `index_const.py`，因此只需改第 1 步即可）

**修改指数日K enriched 计算逻辑**：修改 [repository.py:1708-1718](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L1708-L1718) 的 `_compute_index_enriched_range`，当前只调用 `compute_indicators` + `compute_signals`（跳过涨跌停/股本/市值逻辑）。如需添加指数特有指标，在此处添加。

**修改指数同步批次大小**：通过偏好设置或直接改 [preferences.py:537-539](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L537-L539) 默认值。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件 Parquet | `append_index_daily`/`append_index_enriched` 追加写入分区 | 持久化数据，影响所有后续读取 |
| DuckDB 视图 | `refresh_index_views` 重建 6 张视图（[repository.py:2076-2100](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L2076-L2100)） | 影响所有通过视图的查询（`kline_index_daily`/`kline_index_enriched`/`kline_etf_daily`/`kline_etf_enriched`/`instruments_index`/`instruments_etf`） |
| 维表内存缓存 | `save_index_instruments` 清空 `_index_instruments_cache`/`_etf_instruments_cache`/`_name_map_cache`（[repository.py:2058-2060](file:///c:/Code/tick-stock-panel/backend/app/tickflow/repository.py#L2058-L2060)） | 影响 `get_index_instruments`/`get_index_symbol_set`/`resolve_asset_type` |
| 实时行情内存缓存 | fetch 循环每轮重新构建 `_index_quotes_cache`（[quote_service.py:850-852](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py#L850-L852)） | 影响 `/api/intraday/indices` 实时行情 |
| SSE 前端 | `quotes_updated` → invalidate `'index-quotes'` 前缀（[queryKeys.ts:139](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L139)） | 影响 Layout 侧边栏指数条 + Indices 页面顶部行情 |
| 前端手动失效 | `syncDaily.mutate` 成功后 `invalidateQueries(['index-quotes'])` + `invalidateQueries(['index-daily'])`（[Indices.tsx:115-118](file:///c:/Code/tick-stock-panel/frontend/src/pages/Indices.tsx#L113-L119)） | 影响所有指数日K查询 + 实时行情 |
| 盘后管道失效 | `_invalidate("index_daily")`/`"index_enriched"`/`"index_instruments"`（[daily_pipeline.py:559-561](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L559-L561)） | 影响 `/api/data/status` 数据状态 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 自定义源指数协议 | `backend/tests/test_custom_provider_indices.py` | 核心四只指数传入传出（L88）；监控规则指数标的联合拉取（L91-106）；未实现 `get_realtime_indices` 时静默跳过（L109-139） |
| Fuyao 指数快照 | `backend/tests/test_fuyao_provider.py` | 指数快照映射与成交量单位（L296-311）；BJ 代码过滤（L313-319）；API 错误返回 None（L322-326） |
| 策略层日K | `backend/tests/test_strategy_market_data.py` | `get_index_daily` 委托仓库并归一化日期（L64）；非法/空 symbol 返回空 DataFrame（L89-97） |
| 资产路由日K | `backend/tests/test_daily_batch_asset.py` | 注入 `fake_index_daily` 验证资产路由（L32） |

**待确认**：未找到直接测试 `api/indices.py` 端点（`/api/index/daily`、`/api/index/minute`、`/api/index/sync_daily`）的测试文件。当前测试覆盖了底层服务层和 provider 协议，但 API 层的集成测试缺失。

## 依赖关系

### 依赖的其他功能

- [实时行情](dashboard.md)：`quote_service` 的 fetch 循环提供指数实时行情源
- [数据同步](data-management.md)：`kline_sync.sync_daily_batch` 提供日K拉取能力
- [指标管道](architecture-and-infrastructure.md)：`indicators.pipeline` 提供 enriched 计算
- [能力路由](architecture-and-infrastructure.md)：`Cap.KLINE_DAILY_BATCH` 等门控决定日K同步是否可用
- [偏好配置](architecture-and-infrastructure.md)：`preferences.get_index_daily_batch_size` 控制同步批次大小
- [盘后管道](data-management.md)：`daily_pipeline` 提供定时同步调度

### 被依赖的功能

- [大盘总览/看板](dashboard.md)：`market_overview_builder` 消费 `CORE_INDEX_SYMBOLS` 实时行情构建看板指数块
- [大盘复盘 AI 报告](review.md)：`market_recap` 消费总览中的指数数据生成复盘报告
- [概念分析](concept-analysis.md)：`concept_rotation_analyzer` 消费总览中的指数行情
- [策略层](screener.md)：`strategy/market_data.get_index_daily` 供策略读取指数日K
- 侧边栏指数条：Layout 消费 `indexQuotes` 展示四只指数实时涨跌

## 常见问题与注意事项

1. **核心四只固定不可配置**：`index_const.py` 是后端单一权威，但前端 `Indices.tsx:57-62` 和 `Layout.tsx:75-80` 各自维护了同一份硬编码副本。修改时必须同步更新 4 处，否则侧边栏与指数页面展示不一致。

2. **指数实时行情百分数口径**：`_build_index_quotes` 将 TickFlow 返回的小数 `change_pct`（如 `0.0031` = 0.31%）转换为百分数（`0.31`），`_fallback_index_quotes_from_daily` 也计算百分数。前端 `fmtPct` 直接 `toFixed(2) + "%"` 展示。**注意**：此处与 enriched 中 `change_pct` 的小数制不同（enriched 存储 `0.05` = 5%）。实时指数缓存是百分数，enriched 指数日K 的 `change_pct` 列仍为小数制。

3. **指数日K enriched 不包含涨跌停/股本/市值**：`_compute_index_enriched_range` 跳过了 `compute_limit_hit` 等逻辑，`consecutive_limit_ups/downs` 恒为 0。策略层不可用指数数据做连板判断。

4. **分钟K 不持久化**：`fetch_minute_single` 实时拉取后直接返回，不写入本地 Parquet。每次页面加载或日期切换都会重新拉取。

5. **指数与 ETF 分开存储**：`index_sync.py` 将指数和 ETF 的维表与日K 分开存储为独立的 Parquet 目录和 DuckDB 视图。`sync_and_persist_index_daily` 默认过滤掉 `asset_type='etf'` 的标的，ETF 由 `sync_and_persist_etf_daily` 处理。

6. **日K 读取的快/慢路径**：`get_index_daily` 如果请求的列全是存储列（OHLCV 等），直接通过 `_scan_index_daily_symbol` 列下推快速返回；如果请求了技术指标列（MA/MACD/RSI/KDJ/BOLL），需要先 scan 150 天 warmup 窗口数据，再调用 `compute_indicators` + `compute_signals` 即时计算。前端 Indices 页面请求全指标列，因此走慢路径。

7. **实时补拉时的 source 标识**：`/api/index/daily` 返回的 `source` 字段区分 `"index_enriched"`（本地数据）、`"live"`（实时补拉）、`"none"`（无数据），前端用 `daily.data?.source` 展示数据来源标签。

8. **同步频率与限流**：`sync_and_persist_index_daily` 使用 `chunked` + `sleep_between_batches` 控制请求频率，`batch_size` 由 `min_batch(preferences.get_index_daily_batch_size(), limit)` 决定，默认 100。