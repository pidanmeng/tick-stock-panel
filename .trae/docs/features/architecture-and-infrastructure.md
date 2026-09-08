---
title: 架构与基础设施
description: TSP 整体架构、启动流程、数据流、定时任务、缓存分层与能力路由机制的完整参考。
---

# 架构与基础设施 — 功能文档

> 本文档是 TSP（Tick Stock Panel）整体架构与基础设施的完整参考，涵盖应用启动装配、端到端数据流、APScheduler 定时任务、三层存储与缓存分层、能力路由机制、SSE 实时推送链路等核心系统级主题。修改或扩展任何系统级行为前请先阅读本文档。

## 功能概述

TSP 是一个自托管单容器 A 股量化工作台（选股 + 监控 + 回测 + AI 研究），后端以 FastAPI 为核心，通过 lifespan 生命周期按序装配数据层、服务层、策略层与调度层，盘后以 APScheduler 驱动定时管道（维表→日K→除权→enriched→指数/ETF→分钟→regime→refresh_cache），盘中以 `QuoteService` 轮询线程驱动实时行情热路径（轮询→compute_enriched_today→SSE 广播），前端以 TanStack Query + SSE 实现精确缓存失效与实时更新。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 应用入口 | `backend/app/main.py` | FastAPI 应用装配、lifespan 生命周期（所有服务初始化/关闭）、CORS、中间件、路由注册、SPA fallback |
| 定时任务 | `backend/app/jobs/daily_pipeline.py` | APScheduler 调度器启动、5 类定时 job 定义、盘后管道 `run_now`（6 阶段）、注册复盘 job |
| 存储层 | `backend/app/tickflow/repository.py` | `DataStore`（DuckDB 内存视图 + 目录布局），`KlineRepository`（Polars 缓存 + 读写接口） |
| 指标管道 | `backend/app/indicators/pipeline.py` | `run_pipeline`（全量/增量 enriched 计算 + 发布），`compute_enriched_today`（盘中增量热路径），`ENRICHED_STORAGE_COLS`（14 列窄表定义） |
| 发布协调 | `backend/app/enriched_generation.py` | `EnrichedPublication` 排他发布锁、generation marker 文件读取/自愈、孤儿发布恢复 |
| 能力路由 | `backend/app/data_providers/capabilities.py` | `CAPABILITY_REGISTRY`（5 档 7 能力数据集维度注册表），`build_capability_matrix`（矩阵构建） |
| 能力枚举 | `backend/app/tickflow/capabilities.py` | `Cap` 枚举（14 个能力常量），`CapabilitySet`，`CapabilityDenied` 异常 |
| 行情服务 | `backend/app/services/quote_service.py` | `QuoteService`（后台轮询线程、实时行情分片拉取、enriched 增量计算触发、SSE 广播），`QuoteSubscriber`（逐连接订阅者） |
| 盘口服务 | `backend/app/services/depth_service.py` | 五档盘口 sealed 服务（真假涨停/跌停判断，独立旁路线） |
| 分钟刷新 | `backend/app/services/minute_refresh.py` | 盘中分钟 K 线增量刷新（Expert 专有，线程常驻） |
| 数据完整性 | `backend/app/services/data_integrity.py` | 启动后 30s 延时自检，发现停机缺口自动修复 |
| 企业微信机器人 | `backend/app/services/wecom_bot_service.py` | 可选企业微信长连接通道 |
| 选股服务 | `backend/app/services/screener.py` | `ScreenerService`（stock/etf 双实例，三级缓存） |
| 扩展表预设 | `backend/app/services/ext_presets.py` | 内置概念/行业扩展表初始化 |
| 扩展拉取 | `backend/app/services/ext_pull.py` | 扩展数据定时拉取调度器 |
| 财务同步 | `backend/app/services/financial_sync.py` | 财务数据手动同步调度器（Expert 套餐） |
| 挖掘管理 | `backend/app/services/mining_manager.py` | `MiningJobManager`（回测挖掘任务管理，中断恢复） |
| 偏好设置 | `backend/app/services/preferences.py` | 用户偏好设置存取（调度时间、监控开关等） |
| 策略引擎 | `backend/app/strategy/engine.py` | `StrategyEngine`（4 目录策略加载，L1 策略运行） |
| 监控服务 | `backend/app/strategy/monitor.py` | `StrategyMonitorService`，`MonitorRuleEngine`（盘中监控规则引擎） |
| 监控规则 | `backend/app/strategy/monitor_rules.py` | 监控规则持久化存储 |
| 策略配置 | `backend/app/strategy/config.py` | 策略覆盖配置加载 |
| 看门狗 | `backend/app/watchdog.py` | 自愈看门狗（探测 Polars 闸与写锁，僵死时退出） |
| API 路由 | `backend/app/api/routes.py` | 健康检查、能力探测/重探测 API |
| 回测引擎 | `backend/app/backtest/engine.py` | `BacktestEngine` |
| 回测矩阵 | `backend/app/backtest/matrix.py` | `prewarm_matrix_cache`（矩阵缓存预热） |
| 自定义源 | `backend/app/data_providers/custom.py` | 自定义数据源插件加载 |
| 因子注册 | `backend/app/factors/store.py` | 自定义/复合因子载入注册表 |
| 后端扩展 | `backend/app/backend_extensions/` | 二次开发 L2 后端扩展注册机制 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| SSE 管理 | `frontend/src/lib/useQuoteStream.ts` | 全局 SSE 连接管理、自动重连、按 `SSE_INVALIDATE_PREFIXES` 精确失效 query cache |
| 查询键工厂 | `frontend/src/lib/queryKeys.ts` | QK 工厂（`SSE_INVALIDATE_PREFIXES` 定义），所有 TanStack Query 键集中管理 |
| API 客户端 | `frontend/src/lib/api.ts` | 唯一 API 客户端实例 |
| 路由 | `frontend/src/router.tsx` | 前端路由定义 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 架构文档 | `.trae/docs/architecture.md` | 架构总览（含过时行号，本文档为更精确引用源） |
| 项目规则 | `.trae/rules/project_rules.md` | 常驻精简规则 |
| 贡献指南 | `CONTRIBUTING.md` | 模块边界、数据契约、验证矩阵、复审流程 |
| 二开文档 | `docs/secondary-development.md` | 二次开发与扩展契约 |
| 数据目录 | `data/` | 运行时数据根目录（Parquet 文件、generation marker、自定义策略等） |

## 业务逻辑

### 核心流程

TSP 的运行分为三大流程：**应用启动装配**、**盘后定时管道**、**盘中实时热路径**。三者通过 `KlineRepository` 存储层和 `EnrichedPublication` 发布协调机制连接。

```text
[启动装配] → [服务层就绪] → [盘中: QuoteService 轮询 → compute_enriched_today → SSE 广播]
                              → [盘后: APScheduler 触发 → run_now(6 阶段) → refresh_cache]
                              → [按需: 手动触发管道 / 选股 / 回测 / 挖掘]
```

### 数据流

#### 1. 应用启动装配（main.py lifespan）

`main.py:88-390` 的 `_application_lifespan` 是唯一的应用生命周期，按固定顺序初始化所有服务：

1. **认证引导** (`main.py:98-101`): `auth.bootstrap_from_env()` 从环境变量初始化密码。
2. **数据层** (`main.py:103-106`): 创建 `DataStore`（DuckDB 内存视图 + 目录结构）和 `KlineRepository`（Polars 缓存层）。
3. **自定义因子** (`main.py:108-115`): `load_into_registry` 载入自定义/复合因子注册表（P3，fail-隔离）。
4. **挖掘管理** (`main.py:117-122`): `MiningJobManager` 初始化并恢复中断的回测挖掘任务。
5. **固定 generation** (`main.py:124-128`): 若 `backtest_matrix_disk_cache_enabled` 开启，固定 managed generation，避免并发 worker 各自创建版本。
6. **预热标记** (`main.py:130-131`): `app.state.indicators_ready = False`，enriched 预热完成后回调置 True。
7. **缓存预热** (`main.py:135`): `repo.refresh_cache(background=True)` — 同步预热 instruments/index/ETF 缓存，enriched 的重计算推后台线程。
8. **自定义数据源** (`main.py:139-143`): `custom_sources.load_all()` 加载自定义数据源插件。
9. **能力探测** (`main.py:146-148`): `detect_capabilities()` 构建当前能力矩阵，存入 `app.state.capabilities`。
10. **行情服务** (`main.py:151-154`): `QuoteService` 创建、注入 repo、boot_check。
11. **策略监控** (`main.py:159-161`): `StrategyMonitorService` 创建，注入 `app.state`。
12. **盘口服务** (`main.py:164-168`): `DepthService` 创建、注入 repo 和 app.state。
13. **调度器** (`main.py:172-177`): `daily_pipeline.start_scheduler()` 启动 APScheduler。
14. **盘口补跑+轮询** (`main.py:181-184`): `depth_service.boot_check()` + `start_polling()`。
15. **分钟刷新** (`main.py:188-194`): `MinuteRefreshService` 创建并启动（Expert 专有）。
16. **数据完整性自检** (`main.py:199-207`): 30s 后 `boot_integrity_check` 扫描停机缺口。
17. **企业微信机器人** (`main.py:211-217`): `WecomBotService` 初始化（可选通道）。
18. **扩展表预设** (`main.py:224-227`): `ensure_builtin_presets` 初始化内置概念/行业表。
19. **扩展数据拉取** (`main.py:230-233`): `pull_scheduler.start()` 启动扩展数据定时拉取。
20. **财务调度器** (`main.py:237-239`): `financial_scheduler.start()` 初始化财务手动同步调度器。
21. **看门狗** (`main.py:242-243`): `start_watchdog` 启动自愈看门狗。
22. **策略引擎** (`main.py:246-264`): `ScreenerService`×2（stock/etf）、`StrategyEngine`（4 目录加载策略）。
23. **矩阵缓存预热** (`main.py:266-313`): `_schedule_matrix_cache_prewarm` 在 `_on_refresh_done` 回调中触发。
24. **监控规则引擎** (`main.py:316-349`): `MonitorRuleEngine` 加载规则、`SectorMonitorService` 创建。
25. **后端扩展钩子** (`main.py:352-356`): `start_backend_extensions` 启动 L2 后端扩展。
26. **finally 关闭** (`main.py:358-390`): 按逆序关闭所有服务（看门狗→矩阵预热→挖掘→调度器→扩展拉取→财务→行情→盘口→机器人→分钟刷新）。

`main.py:394-401` 的 `lifespan` 包装器在 `_application_lifespan` 外层增加 `MiningProcessLock` 单进程锁（`settings.data_dir` 级，防止同一 data 目录多进程冲突）。

#### 2. 盘后定时管道（daily_pipeline.run_now）

`daily_pipeline.py:186-699` 的 `run_now` 是盘后核心管道，分 6 阶段执行：

- **Step 0 — 维表同步** (`daily_pipeline.py:207-212`): 同步 `instruments` 维表（股票列表、上市状态）。
- **Step 1 — 日K同步** (`daily_pipeline.py:218-343`): 按 `override_start_date`/实时覆写/batch 补缺口/首次 1 年四分支逻辑拉取日K，含 lagging 检测 (`daily_pipeline.py:365-374`)。
- **Step 1.5 — 除权因子** (`daily_pipeline.py:376-417`): 同步 `adj_factor`，为前复权计算做准备。
- **Step 2 — Enriched** (`daily_pipeline.py:419-508`): 调用 `pipeline.run_pipeline` 计算 enriched 指标（14 列存储 + 68+ 列指标现算），含 `EnrichedPublication` 发布协调。
- **Step 2.3 — 指数/ETF** (`daily_pipeline.py:510-637`): 指数成分股 en riched + 指数 K 线 + ETF K 线 + ETF enriched。
- **Step 2.5 — 分钟K** (`daily_pipeline.py:639-667`): 分钟 K 线同步。
- **Step 2.6 — Regime** (`daily_pipeline.py:669-699`): 市场状态标记计算。
- **最终** (`daily_pipeline.py:1154-1175`): `_pipeline_then_refresh` 在 `qs.paused()` 上下文内执行 `run_now`，完毕后 `repo.refresh_cache()` 刷新缓存。

#### 3. 盘中实时热路径

`QuoteService` 后台轮询线程 (`quote_service.py:594-641` `_poll_loop`):

```
_poll_loop → _should_fetch_for_phase (按市场阶段) → _fetch_quotes (quote_service.py:643-654)
→ _fetch_full_market_quotes (quote_service.py:656+) → 自定义源/TickFlow 拉取 → 写 kline_daily
→ compute_enriched_today (pipeline.py:1831+) → 10-50ms 增量计算 → _broadcast_quote_updated
→ SSE → 前端 SSE_INVALIDATE_PREFIXES 精确失效
```

- 轮询间隔取决于套餐等级：`quote_service.py:201-210`（expert 1s/pro 3s/starter 6s/free 6s，自定义源 1s）。
- `_paused` 上下文 (`quote_service.py:325-357`): 管道执行期间暂停行情轮询，防止写盘竞态。
- `compute_enriched_today` (`pipeline.py:1831+`): 盘中增量热路径，~5500 行约 10-50ms；依赖 `live_agg` 递推状态 + `prev_enriched` + 今日 OHLCV JOIN，前复权乘最近 `adj_factor`。

#### 4. APScheduler 定时任务

`daily_pipeline.py:1123-1249` 的 `start_scheduler` 注册 5 类 job：

| Job ID | 触发器 | 时间 | 用途 |
|--------|--------|------|------|
| `pre_market_instruments` (`daily_pipeline.py:1148`) | `CronTrigger` | 09:10 盘前 (mon-fri) | 盘前更新维表 |
| `daily_pipeline` (`daily_pipeline.py:1182`) | `CronTrigger` | 15:30 盘后 (mon-fri) | 盘后 6 阶段管道，`misfire_grace_time=7200` |
| `depth_finalize` (`daily_pipeline.py:1200`) | `CronTrigger` | 15:02 (mon-fri) | 盘口收盘 sealed |
| `reprobe_capabilities` (`daily_pipeline.py:1230`) | `IntervalTrigger` | 60 分钟 | 定期重新探测能力 |
| `scheduled_review` (`daily_pipeline.py:1241`) | `CronTrigger` | 20:00 (mon-fri) | 定时复盘任务 |

调度器在 `main.py:172-177` 中启动，若 enriched 数据为空，首次启动可手动 `POST /api/pipeline/run` 触发。

### 调用链

#### 启动装配调用链

```
lifespan (main.py:394) → MiningProcessLock.acquire (main.py:395-396)
→ _application_lifespan (main.py:88-390)
  → DataStore() (main.py:103) → DataStore.__init__ (repository.py:88-129)
  → KlineRepository(store) (main.py:104) → KlineRepository.__init__ (repository.py:336-389)
  → detect_capabilities() (main.py:146) → build_capability_matrix (capabilities.py:146-200)
  → QuoteService() (main.py:151) → QuoteService.__init__ (quote_service.py:197+)
  → daily_pipeline.start_scheduler(repo, capset) (main.py:173) → start_scheduler (daily_pipeline.py:1123-1249)
  → start_backend_extensions (main.py:353-356)
→ yield → finally 逆序关闭 (main.py:358-390)
→ MiningProcessLock.release (main.py:401)
```

#### 盘后管道调用链

```
APScheduler daily_pipeline job (daily_pipeline.py:1182)
→ _pipeline_then_refresh (daily_pipeline.py:1154-1175)
  → qs.paused() (quote_service.py:325-357) 暂停行情轮询
  → run_now (daily_pipeline.py:186-699)
    → Step 0: _run_instruments_sync (daily_pipeline.py:207-212)
    → Step 1: _run_kline_sync (daily_pipeline.py:218-343)
    → Step 1.5: _run_adj_factor_sync (daily_pipeline.py:376-417)
    → Step 2: pipeline.run_pipeline (pipeline.py:1428+)
      → EnrichedPublication.begin (enriched_generation.py:268+)
      → _invalidate (daily_pipeline.py:129-132)
    → Step 2.3: 指数/ETF enriched (daily_pipeline.py:510-637)
    → Step 2.5: 分钟K (daily_pipeline.py:639-667)
    → Step 2.6: regime (daily_pipeline.py:669-699)
  → finally: repo.refresh_cache() (daily_pipeline.py:1174)
```

#### 盘中实时热路径调用链

```
QuoteService._poll_loop (quote_service.py:594-641)
→ _should_fetch_for_phase (按市场阶段判断)
→ _fetch_quotes (quote_service.py:643-654) [_fetch_lock 串行化]
→ _fetch_full_market_quotes (quote_service.py:656+)
  → 自定义源: get_realtime (若有)
  → TickFlow: get_by_universes(CN_Equity_A, CN_ETF) (quote_service.py:678+)
  → 核心指数: 按码拉取 (quote_service.py:742+)
→ 写入 kline_daily
→ compute_enriched_today (pipeline.py:1831+)
  → live_agg 递推状态 + prev_enriched + 今日 OHLCV JOIN
  → _apply_adj_factor (pipeline.py:242+) 前复权
→ _broadcast_quote_updated (quote_service.py:415-424)
  → invalidate_overview_cache
  → QuoteSubscriber.notify_quote (quote_service.py:110-130)
→ SSE → 前端 EventSource (useQuoteStream.ts:74+)
→ SSE_INVALIDATE_PREFIXES (queryKeys.ts:132-142) 精确失效
```

### 状态机

#### 能力路由状态

`capabilities.py:146-200` `build_capability_matrix` 对每个能力生成三类状态：

- **candidates**: 能提供该能力的所有源（按优先级排序）
- **pending**: 可用但未启用（用户偏好选择）
- **usable**: 最终生效的源（candidates 中优先级最高的 `usable_if` 条件满足的源）

`CAPABILITY_REGISTRY` (`capabilities.py:28-90`) 定义每个能力的数据集维度、所需套餐档位、源选择偏好。`_TIER_RANK` (`capabilities.py:101`) 将套餐档位映射为数值（none=-1, free=0, starter=1, pro=2, expert=3），用于 fail-closed 比较。

#### 发布状态

`enriched_generation.py` 定义 enriched 数据的发布状态：

- **ready** (`get_enriched_generation` 返回 `(generation, True)`): 数据可用，generation 递增标记
- **pending** (`get_enriched_generation` 返回 `(generation, False)`): 正在计算中，消费者应等待或使用旧数据
- **unavailable** (`EnrichedGenerationUnavailableError`): 无可用数据
- **孤儿恢复** (`enriched_generation.py:166-193`): 检测到发布进程僵死，在锁内二次确认后恢复 ready 并换新 generation

## 关键数据结构

### API 契约

**健康检查** (`routes.py:13-20`):
```
GET /health → {"status": "ok", "mode": "self-hosted", "version": "x.y.z"}
```
三态 mode：正常 `ok`、依赖缺失 `degraded`、完全不可用 `unavailable`。

**能力探测** (`routes.py:23-30`):
```
GET /api/capabilities → {capabilities: {能力名: 源名}, ...}
POST /api/capabilities/redetect → {capabilities: {能力名: 源名}, ...}
```
`redetect` (`routes.py:33-44`) 强制重探能力 → 同步 `app.state` → `_sync_financial_scheduler_caps`。

### 存储结构

**Enriched 存储列** (`pipeline.py:93-103` `ENRICHED_STORAGE_COLS`，14 列窄表):

| 列名 | 类型 | 说明 |
|------|------|------|
| `symbol` | str | 股票代码 |
| `date` | date | 交易日 |
| `open`/`high`/`low`/`close` | f64 | 前复权 OHLC |
| `volume` | f64 | 成交量（股） |
| `amount` | f64 | 成交额（元） |
| `raw_close`/`raw_high`/`raw_low` | f64 | 不复权价 |
| `turnover_rate` | f64 | 换手率（**百分数值**，如 5.5 表示 5.5%） |
| `consecutive_limit_ups`/`consecutive_limit_downs` | i32 | 连续涨跌停天数 |
| `quote_ts` | datetime | 行情时间戳 |

**完整指标列** (`pipeline.py:111-205` `ENRICHED_COLUMNS`): 存储列 + 基础/MA/EMA/MACD/BOLL/KDJ/ATR/量价/极值/动量/偏离/波动率/RSI/信号列 + JOIN 列，按类别分在 `ENRICHED_COLUMNS_BY_CATEGORY` (`pipeline.py:208-225`)。

**Parquet 目录布局** (`repository.py:97-121`，`DataStore.__init__` 中创建):

```
data/
├── kline_daily/                  # 日K Parquet (symbol=XX/date=YYYY-MM-DD/*.parquet)
├── kline_daily_enriched/         # enriched 日K
├── kline_index_*/kline_etf_*/    # 指数/ETF K线
├── kline_minute/                 # 分钟K
├── adj_factor/                   # 除权因子
├── financials/                   # 财务数据
├── instruments*/                 # 维表
├── depth5/                       # 五档盘口
├── .matrix_generation_{asset_type}.json  # generation marker
└── .matrix_generation_{asset_type}.lock  # 排他写入锁
```

**DuckDB 视图** (`repository.py:189-246` `_register_views`，`repository.py:251-330` `_register_unified_views`):

- 13 个基础视图（`kline_daily`、`kline_daily_enriched`、`kline_index_*`、`kline_etf_*`、`kline_minute`、`adj_factor`、`financials`、`instruments`、`depth5`）
- 4 个统一视图（`kline_daily_all`、`kline_enriched_all`、`kline_minute_all`、`instruments_all`，跨类型 UNION ALL）

### 内存结构

**`KlineRepository` 缓存属性** (`repository.py:336-389`):

| 缓存属性 | 类型 | 说明 |
|----------|------|------|
| `_enriched_cache` | `dict[str, pl.DataFrame]` | 最新 enriched 行（key=symbol） |
| `_live_agg_cache` | `dict[str, pl.DataFrame]` | 实时聚合缓存 |
| `_instruments_cache` | `pl.DataFrame` | 维表全量缓存 |
| `_enriched_history_cache` | `dict[str, pl.DataFrame]` | 历史 enriched 缓存 |
| `_index_*_cache` / `_etf_*_cache` | `dict` | 指数/ETF 缓存 |
| `_write_lock` | `threading.Lock` | 串行化写入操作 |

**`QuoteService` 状态** (`quote_service.py:197+`):

| 属性 | 类型 | 说明 |
|----------|------|------|
| `_paused` | `threading.Event` | 行情暂停标志（管道期间置位） |
| `_fetch_lock` | `threading.Lock` | 拉取串行化锁 |
| `_subscribers` | `list[QuoteSubscriber]` | SSE 连接订阅者列表 |
| `_poll_thread` | `threading.Thread` | 后台轮询线程 |
| `_market_phase` | 函数 | 当前市场阶段判断（开盘/午休/收盘等） |

**SSE 失效前缀** (`queryKeys.ts:132-142`):

```typescript
SSE_INVALIDATE_PREFIXES = [
  'watchlist-quotes',  // 自选页实时行情
  'watchlist-enriched', // 自选页 enriched 数据
  'quote-status',      // 行情状态
  'index-quotes',      // 指数行情
  'overview-market',   // 大盘概览
  'limit-ladder',      // 涨跌停梯
] as const
```

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **自定义策略**: 在 `data/strategies/custom/` 下创建 Python 策略文件（`strategy` 目录），引擎自动加载 (`main.py:253-258`)。
- **自定义数据源**: 通过 `custom_sources` 插件机制注册 (`main.py:139-143`)，能力探测自动识别其能力。
- **扩展数据预设**: 在 `data/ext_presets/` 中配置，`pull_scheduler` 自动定时拉取 (`main.py:230-233`)。
- **策略覆盖配置**: 通过 `strategy_config.load_override` 指定策略覆盖参数 (`main.py:261`)。
- **偏好设置**: 通过 `preferences` 服务调整调度时间、监控开关等 (`main.py:333`)。

### L2 扩展（插槽/路由/注册替换）

- **前端插槽**: 已开放 3 个插槽（`layout.navigation.extra`、`stock-preview.footer`、`watchlist.toolbar`），见 `docs/secondary-development.md`。
- **后端扩展注册**: `start_backend_extensions` (`main.py:352-356`) 通过 `extension_registry` 启动已注册的后端扩展。
- **`NotificationFormatter`**: 后端通知格式化器可替换实现。
- **`MonitorRuleEngine`**: 监控规则引擎 (`main.py:316-349`) 可加载自定义规则。

### L3 修改（直接改源码）

- **新增能力**: 需同时修改 `CAPABILITY_REGISTRY` (`capabilities.py:28-90`) 和 `Cap` 枚举 (`tickflow/capabilities.py:11-28`)。
- **修改管道阶段**: 在 `run_now` (`daily_pipeline.py:186-699`) 中增减步骤，注意 `qs.paused()` 上下文和 `EnrichedPublication` 发布协调。
- **新增缓存层**: 需在 `KlineRepository.__init__` (`repository.py:336-389`) 中增加缓存属性，并在 `refresh_cache` 中注册预热逻辑。
- **修改 enriched 列**: 修改 `ENRICHED_STORAGE_COLS` (`pipeline.py:93-103`) 和 `ENRICHED_COLUMNS` (`pipeline.py:111-205`)，注意向后兼容（新增列而非删除/重命名）。
- **新增 SSE 事件**: 在 `queryKeys.ts:132-142` 的 `SSE_INVALIDATE_PREFIXES` 中添加前缀，前端自动接收失效。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| Parquet 文件（持久化） | 直接覆盖分区文件 (`replace_with_retry`，`repository.py:42-66`) | 对应日期的原始数据 |
| DuckDB 内存视图 | 重启后重建（`DataStore._register_views`，`repository.py:189-246`） | 同一进程内所有 SQL 查询 |
| Polars 内存缓存（`_enriched_cache` 等） | `refresh_cache()` 或 `clear_cache()`（`repository.py:413+`/`513+`） | 当前进程 API 响应 |
| Generation marker（`.matrix_generation_*.json`） | `bump_enriched_generation`（`enriched_generation.py:255-265`） | 回测引擎、所有读取方 |
| SSE 连接（逐连接订阅者） | `_broadcast_quote_updated`（`quote_service.py:415-424`） | 所有前端 SSE 连接 |
| 前端 TanStack Query cache | `SSE_INVALIDATE_PREFIXES`（`queryKeys.ts:132-142`） | 前端页面视图 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 后端单元测试 | `backend/tests/` | 按 `CONTRIBUTING.md` §9 验证矩阵执行 |
| 后端风格检查 | `ruff check app/ tests/` | P0/P1 必过 |
| 前端构建 | `pnpm build` | 前端改动必须通过 |
| Git 提交前 | `git diff --check` | 禁止空白字符错误 |

## 依赖关系

### 依赖的其他功能

- **数据源插件**: 架构依赖 `TickFlow`/`fuyao`/`stock-sdk` 数据源提供原始行情数据，经 `CAPABILITY_REGISTRY` 路由到各服务。
- **Polars + DuckDB**: 所有数据处理依赖 Polars DataFrame 和 DuckDB 内存引擎，`DataStore` 和 `KlineRepository` 为二者的封装层。
- **APScheduler**: 所有定时任务依赖 APScheduler `AsyncIOScheduler`，`start_scheduler` (`daily_pipeline.py:1123`) 注册所有 job。

### 被依赖的功能

- **所有业务功能**（选股、监控、回测、挖掘、投研）：依赖 `KlineRepository` 提供 enriched 数据，依赖 `QuoteService` 提供实时行情，依赖 `run_pipeline` 提供盘后指标。
- **前端 SSE 实时更新**: 依赖 `QuoteService._broadcast_quote_updated` 和 `SSE_INVALIDATE_PREFIXES` 机制。
- **回测引擎**: 依赖 `EnrichedPublication` 的 generation marker 判断数据版本一致性。
- **策略监控**: 依赖 `MonitorRuleEngine` 的规则加载和 `_screener_svc._load_enriched_history` 的历史窗口加载器。

## 常见问题与注意事项

- **主键行号过时**: `.trae/docs/architecture.md` 中的多处行号与当前代码不符（如 `main.py` lifespan 标 :376 实际 :88、`app` 标 :387 实际 :404、`pipeline.py` `run_pipeline` 标 :1290 实际 :1428、`compute_enriched_today` 标 :1660 实际 :1831、`daily_pipeline.py` `start_scheduler` 标 :1045 实际 :1123）。本文档使用实际行号，但代码持续演进，修改前请重新确认。
- **金融口径红线**: 前复权价（enriched OHLC）vs 原始价（`raw_*`）；`turnover_rate` 为百分数值（如 5.5 表示 5.5%）；`change_pct` 为小数制（实时源入口）；`datetime` 为北京 naive 墙钟；股票/ETF/指数分开存储与路由。
- **并发写防竞态**: `repository.py:42-66` `replace_with_retry` 使用 Windows 读锁重试（10 次×0.5s）；`quote_service.py:643-654` `_fetch_quotes` 使用 `_fetch_lock` 串行化；`enriched_generation.py:112-128` `_exclusive_generation_lock` 使用进程锁文件 + 线程 RLock。
- **管道与行情互斥**: `_pipeline_then_refresh` (`daily_pipeline.py:1154-1175`) 在 `qs.paused()` 上下文内执行，暂停行情轮询防写盘竞态；异常退出时 `finally` 确保 `resume()`。
- **首次启动无数据**: 若 enriched 数据为空，可手动 `POST /api/pipeline/run` 触发管道；调度器在 `main.py:172-177` 中启动，`daily_pipeline.py:1182` 的 `misfire_grace_time=7200` 允许盘后 2 小时内补跑。
- **SSE 失效策略白名单**: `queryKeys.ts:125-130` 注释说明策略页（`screener-cached`）不在 `SSE_INVALIDATE_PREFIXES` 中——行情刷新时策略结果不变，监控策略由独立的 `strategy_results_updated` 事件刷新，避免每个 tick 双重刷新策略页。
- **能力探测 fail-closed**: `capabilities.py:104-109` `_tier_base` 将未知套餐档位按 `none` 处理，确保缺能力时明确提示而非静默返回错误结果。
- **generation 孤儿恢复**: `enriched_generation.py:166-193` 检测到发布进程僵死时，在锁内二次确认后恢复 ready 并换新 generation，避免永久阻塞回测等消费者。