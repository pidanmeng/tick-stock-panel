# TSP 项目架构文档

> 本文档是 TSP 项目的**架构目录文档**：正文描述项目整体架构与模块地图（只描述已存在的实现，关键结论均可在标注的 `文件:行号` 处复核）；各功能的详细说明通过 §0 索引到具体文档。如与代码不符，以代码为准；能力边界与二开契约以 [CONTRIBUTING.md](../../CONTRIBUTING.md) 与 [docs/secondary-development.md](../../docs/secondary-development.md) 为准（该文档区分"已可用/按需扩展"，不得把示例当实现）。

## 0. 功能文档索引（目录）

> 以下是本文档索引的全部文档。**用户文档**面向终端用户（如何使用/配置/部署），**开发者文档**面向开发者/贡献者（如何修改/扩展/贡献）。新功能文档产出后必须在 §0.5 登记；已有文档变更时同步更新链接与标题。功能文档模板见 [features/_template.md](features/_template.md)，使用 `/understand-feature` 命令生成。

### 0.1 用户文档（面向终端用户：如何使用、配置、部署 TSP）

| 功能域 | 文档 |
| --- | --- |
| 功能总览 | [features.md](../../docs/features.md) |
| 配置 | [configuration.md](../../docs/configuration.md) |
| 部署 | [deployment.md](../../docs/deployment.md)、[deploy-password.md](../../docs/deploy-password.md) |
| 策略 | [strategy.md](../../docs/strategy.md)、[strategy-iteration.md](../../docs/strategy-iteration.md) |
| 自定义数据源 | [custom-data-source.md](../../docs/custom-data-source.md)（含 [examples/](../../docs/examples/custom-data-source/README.md)） |
| 市场阶段 | [market-phase.md](../../docs/market-phase.md) |
| 挖掘 | [mining.md](../../docs/mining.md) |
| 因子平台 | [factor-system-design.md](../../docs/factor-system-design.md)、[factor-platform-plan.md](../../docs/factor-platform-plan.md) |
| TickFlow Pro | [tickflow-pro-phase1-probe.md](../../docs/tickflow-pro-phase1-probe.md)、[tickflow-pro-shared-rate-limit.md](../../docs/tickflow-pro-shared-rate-limit.md) |

### 0.2 开发者文档（面向开发者/贡献者：如何修改、扩展、贡献代码）

#### 0.2.1 开发指南（`docs/`）

| 功能域 | 文档 |
| --- | --- |
| 二次开发 | [secondary-development.md](../../docs/secondary-development.md) |
| 插件开发 | [plugin-development.md](../../docs/plugin-development.md) |
| 贡献规范 | [CONTRIBUTING.md](../../CONTRIBUTING.md) |
| AI 开发入口 | [AGENTS.md](../../AGENTS.md) |

### 0.3 TRAE 文档归档

| 文档 | 说明 |
| --- | --- |
| [documents/architecture-docs-and-trae-toolchain.md](../documents/architecture-docs-and-trae-toolchain.md) | 原始架构文档与 TRAE 工具链规划（历史归档，持续演进以 architecture.md 为准） |

### 0.4 设计文档索引

| 文档 | 受众 | 说明 |
| --- | --- | --- |
| [design.md](design.md) | 开发者 | 前端设计风格指南（色板/字体/组件/图表/格式化约定，新增前端界面必读） |

### 0.5 功能文档（`.trae/docs/features/`）

逐篇产出的功能级详细文档，覆盖文件位置、业务逻辑、数据流、调用链、扩展指南、测试，是各功能修改/扩展时的第一参考。已创建条目登记如下（模板：[features/_template.md](features/_template.md)）：

| 功能文档 | 覆盖功能域 | 受众 | 状态 |
| --- | --- | --- | --- |
| （暂无） | 行情总览 / 选股 / 策略 / 监控 / 回测 / 挖掘 / 财务 / 复盘 / 自选 / 扩展数据 / 数据源 / 数据管道 | 开发者 | 待用 `/understand-feature` 逐篇生成并登记 |

### 0.6 索引 ↔ 正文章节对应

各功能域在正文中的模块地图位置（便于从文档跳回正文）：行情/数据源 §3/§6 · 后端模块 §4 · API×前端路由 §5 · 存储与缓存 §7 · 前端结构 §8 · 扩展与二开 §9 · 生命周期 §10 · 数据契约 §11。

## 1. 定位与技术栈

TSP（Tick Stock Panel）是自托管、单容器的 A 股「选股 + 监控 + 回测」量化工作台：多数据源按能力独立路由、分钟级策略执行、全时段异动监控、AI 辅助研究。

| 层 | 选型 |
| --- | --- |
| 后端 | Python 3.11+ · FastAPI · Pydantic v2 · APScheduler · sse-starlette · uvicorn |
| 数据 | Polars（计算）· DuckDB（内存视图查询）· Parquet（分区存储） |
| 前端 | React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · ECharts · lightweight-charts |
| 数据源 | TickFlow SDK（内置）· fuyao 插件（同花顺 REST）· stock-sdk 插件（Node bridge，可选）· YAML 自定义源 |
| AI（可选） | OpenAI 兼容接口（DeepSeek/通义/Ollama 等）+ 本地 Codex CLI |
| 包管理/验证 | 后端 `uv`；前端 `pnpm` |
| 部署 | Docker 单容器（前端 dist 由 FastAPI 托管，默认端口 3018）；Dev 模式后端 3018 / 前端 Vite 3011 |

启动入口：
- 服务端应用装配：[backend/app/main.py](../../backend/app/main.py)（`app = FastAPI` main.py:387，lifespan main.py:376）。
- 桌面版：[backend/app/desktop.py](../../backend/app/desktop.py)（uvicorn 线程 + pywebview，单实例锁）。
- 仓库版本号：根 [VERSION](../../VERSION)。

## 2. 目录总览

```text
tick-stock-panel/
├── AGENTS.md            # AI 开发入口（自动注入，本文档是其索引）
├── CONTRIBUTING.md      # 贡献/AI/复审规范：模块边界、数据契约、验证矩阵、复审流程
├── docs/                # 领域文档（配置/数据源/策略/挖掘/市场阶段/部署/二开…）
├── backend/
│   ├── app/             # 后端源码（api / services / tickflow / data_providers / plugins /
│   │                    #   indicators / strategy / backtest / jobs / extensions / custom）
│   ├── tests/           # pytest 测试（含 backtest/ 子套件、fixtures/）
│   └── pyproject.toml
├── frontend/
│   └── src/             # React 源码（pages / components / lib / extensions / custom）
├── data/                # 运行时数据目录（不提交 Git，首次启动由 DataStore 创建）
├── dev.ps1 / dev.sh     # Dev 模式启动脚本
├── Dockerfile / docker-compose.yml / packaging/   # 部署与桌面打包
└── .github/workflows/   # docker.yml / release.yml
```

`data/` 运行时目录布局固化在 [backend/app/tickflow/repository.py](../../backend/app/tickflow/repository.py)（DataStore 建目录循环，repository.py:96-124）：`kline_daily / kline_daily_enriched / kline_index_daily / kline_index_enriched / kline_etf_daily / kline_etf_enriched / kline_minute / kline_etf_minute / adj_factor / adj_factor_etf / financials{metrics,income,balance_sheet,cash_flow,shares} / instruments / instruments_index / instruments_etf / instruments_ext / kline_ext / pools / backtest_results / screener_results / ai_cache / user_data / depth5`；用户策略在 `data/strategies/{custom,ai,composite}/`，自定义数据源在 `data/data_sources/*.yaml`。

## 3. 端到端数据流

```text
数据源（TickFlow / fuyao / stock-sdk / YAML 自定义源）
  -> services 同步与校验（kline_sync / quote_service / minute_refresh /
     index_sync / instrument_sync / financial_sync / ext_pull）
  -> DataStore / KlineRepository（Parquet 分区 + DuckDB 内存视图）
  -> indicators.pipeline 计算 enriched 窄表（仅存 14 列基础，指标现算）
  -> 消费方（ScreenerService / StrategyEngine / BacktestEngine /
     MonitorRuleEngine / QuoteService 盘中 _enriched_cache）
  -> FastAPI REST / SSE
  -> frontend（lib/api.ts + TanStack Query / 全局 SSE）
```

- 禁止绕过 services/repository 层直接读数据源或本地文件（API 层保持薄胶水，见 CONTRIBUTING §2.2/§2.3）。
- 盘中实时热路径：`QuoteService` 全局轮询线程（约 15s 一轮：拉取 → 写 `kline_daily` → 增量 enriched → SSE 通知），其 `_enriched_cache` 是盘中行情唯一数据源（[backend/app/services/quote_service.py](../../backend/app/services/quote_service.py)）。
- 回测/挖掘任务在 spawn worker 子进程执行（持久 run ID，刷新/切页重连不丢任务），进程内共享 `heavy_job_limiter` 并发配额；挖掘与主进程用 `MiningProcessLock` 互斥（main.py:378）。

## 4. 后端分层与模块地图（`backend/app/`）

### 4.1 应用装配 `main.py`

`_application_lifespan`（main.py:86）按序完成：auth bootstrap → `DataStore` + `KlineRepository` 挂 app.state（main.py:101-104）→ 挖掘任务恢复（main.py:108）→ 固定 managed generation（main.py:113-117）→ Polars 缓存预热（后台线程，`indicators_ready` 标记，main.py:119-124）→ 能力探测（main.py:127）→ 自定义数据源 `load_all()`（main.py:134）→ `QuoteService` boot（main.py:140-150）→ `StrategyMonitorService`（main.py:148）→ `DepthService` boot+poll（main.py:154-173）→ APScheduler 启动（main.py:162）→ `MinuteRefreshService`（main.py:177-181）→ 数据完整性延时自检（main.py:190-194）→ `WecomBotService`（main.py:200-204）→ 内置扩展表预设 + `pull_scheduler`（main.py:212-221）→ 财务调度器（仅手动同步用，main.py:225-227）→ `ScreenerService`（stock/etf 两实例）+ `StrategyEngine`（4 个策略目录，main.py:235-248）→ 回测矩阵缓存 prewarm owner（main.py:250+）→ `MonitorRuleEngine`/`SectorMonitorService` 注入（main.py:302-335）→ `configure_backend_extensions`（main.py:480）。

横切：访问认证中间件（main.py:418，仅拦 `/api/`，白名单 `/api/auth/*` 与 `/health` 等 main.py:414-415，公网未设密码 403、未登录 401）；`CapabilityDenied → 403` 异常处理器（main.py:493）；SPA 静态回退到 index.html（main.py:506）。

### 4.2 `api/` —— HTTP/SSE 薄胶水层

| 域 | 模块（router 前缀见正文标注） |
| --- | --- |
| 核心 | [routes.py](../../backend/app/api/routes.py)（core_router 无前缀：`/health`、`/api/capabilities`、`/api/capabilities/redetect`，routes.py:13/23/33） |
| 行情/K线 | kline.py(`/api/kline`)、intraday.py(`/api/intraday`，含 SSE)、indices.py(`/api/index`) |
| 选股/策略/信号/监控 | screener.py(`/api/screener`)、strategy.py(`/api/strategies`)、signals.py(`/api/custom-signals`)、monitor_rules.py(`/api/monitor-rules`)、alerts.py(`/api/alerts`)、lots.py(`/api/lots`)、watchlist.py(`/api/watchlist`) |
| 异动 | abnormal.py(`/api/abnormal`，竞价/盘中/偏移三类) |
| 回测/挖掘 | backtest.py(`/api/backtest`)、mining.py(`/api/backtest/mining`) |
| 分析/财务/复盘 | financials.py(`/api/financials`)、stock_analysis.py(`/api/stock-analysis`)、analysis.py(`/api/analysis-menus`)、market_recap.py(`/api/market-recap`)、regime.py(`/api/regime`)、rps.py(`/api/rps`)、overview.py(`/api/overview`) |
| 数据/设置/系统 | data.py(`/api/data`)、pipeline.py(`/api/pipeline`)、ext_data.py(`/api/ext-data`)、settings.py(`/api/settings`)、auth.py(`/api/auth`) |

路由注册顺序即 [main.py:452-477](../../backend/app/main.py#L452-L477) 的 `include_router` 清单；扩展路由在核心路由之后注册并禁止覆盖核心路径（main.py:480）。API 层不做重计算、不直连数据源，只做参数校验与响应映射。

### 4.3 `services/` —— 业务编排层（关键服务职责）

**同步/行情写路径**：`kline_sync`（日K批量同步，capability 门控，复用给盘后管道/历史扩展/修复）；`quote_service`（实时轮询线程，见 §3）；`minute_refresh`（盘中分钟增量落盘，full_minute）；`index_sync`/`instrument_sync`（指数/ETF/个股维表同步）；`extend_history`/`repair_daily`（历史扩展/修复，复用盘后管道）；`depth_service`（五档盘口 sealed 定版旁路）；`data_integrity`（停机缺口自检修复）。

**交易日与日历**：`trading_day`（交易日探针：fuyao 交易日历 → tickflow 时间戳探针 OR → 工作日兜底）；`market_time`（固定北京时间 `CN_TZ`）。

**查询/组装**：`screener`（`ScreenerService`：preset 内存策略即时扫描 + 自定义 SQL(DuckDB)，进程级历史窗口缓存）；`market_overview_builder`（市场总览聚合，概念/成分口径被 rps 与复盘复用）；`regime_builder`/`market_phase`/`market_mainline`（市场环境纯函数）；`rps_rotation`/`concept_rotation_analyzer`（概念涨幅轮动）；`sector_monitor`（板块实时聚合快照）；`abnormal_moves`（交易所异动偏离值口径）；`strategy_cache`（策略结果文件缓存）；`preferences`（偏好/数据源路由/调度时间持久化）；`ext_data`/`ext_presets`/`ext_pull`（扩展数据配置/内置预设/定时拉取）；`index_const`（实时指数核心四只单一权威）；`watchlist`/`watchlist_csv`/`watchlist_ocr`（自选分组/批量导入/截图 OCR）。

**财务/AI/复盘**：`financial_sync`（财务独立同步，手动触发，按 `financial_data_provider` 路由）；`financial_analyzer`/`stock_analyzer`/`market_recap`（AI 流式分析，均走 `ai_provider` 适配 OpenAI 兼容接口或本地 Codex CLI）；`stock_reports`/`market_recap_reports`/`ai_reports`（报告落盘，共用 `json_report_store.JsonReportStore`）；`auction_benchmark`/`dragon_tiger`（盘前风向标/龙虎榜，fuyao 专有直连，不经路由偏好）；`alert_store`（触发记录 JSONL 追加+滚动清理）。

**挖掘/回测编排（heavy 任务）**：`mining_manager`/`mining_jobs`/`mining_schedule`/`mining_candidates`/`mining_preflight`/`mining_process_lock`/`matrix_prewarm_owner`/`heavy_job_limiter`；`backtest.py`（旧信号回测服务，全项目唯一 pandas/vectorbt 使用点，与新 `backtest/` 包并存）。

**通知/横切**：`notify_adapter`（三平台原生通知中心）、`webhook_adapter`（飞书群 Webhook 单向 POST）、`wecom_bot_service`（企业微信机器人长连接，WS 双向）；`auth`（PBKDF2+session）；`fs_utils`（原子写）。

### 4.4 `tickflow/` + `data_providers/` + `plugins/` —— 数据源抽象

见 §6。

### 4.5 `indicators/` —— 指标流水线

[backend/app/indicators/pipeline.py](../../backend/app/indicators/pipeline.py)：enriched parquet **仅存储 14 列基础窄表**（pipeline.py:3-4、:90），68 列指标/信号由各服务即时现算（`compute_indicators` :362、`compute_signals` :614、`compute_limit_signals` :673、`compute_enriched` :991、`run_pipeline` :1290 全量盘后主入口、`compute_enriched_today` :1660）；自定义信号表达式带模块级缓存（pipeline.py:52-84）。`levels.py`：个股 9 类关键价位 `compute_levels`（供 stock_analyzer）。配套 [price_limits.py](../../backend/app/price_limits.py)（涨跌停规则，indicators/backtest/API 共享）、[share_capital.py](../../backend/app/share_capital.py)（历史股本 PIT）、[enriched_generation.py](../../backend/app/enriched_generation.py)（`.matrix_generation_{asset}.json` 原子发布）。

### 4.6 `strategy/` —— 策略体系

[backend/app/strategy/](../../backend/app/strategy/)：`engine.py`（`StrategyEngine` 文件系统加载，4 个目录：builtin / data 下 custom / ai / composite，两阶段过滤+评分）；`builtin/` 26 个内置策略模块；`monitor.py`（`StrategyMonitorService` 旧策略监控 + `MonitorRuleEngine` 通用规则引擎，四类 signal/price/market/strategy）；`monitor_rules.py`（MonitorRule 模型+文件 CRUD）；`config.py`（override 加载）、`composite.py`、`ai_generator.py`、`custom_signals.py`、`intraday_signals.py`、`scoring.py`、`lots.py`、`market_data.py`；`prompts/`（AI 策略生成规范）。策略开发完整规范见 [docs/strategy.md](../../docs/strategy.md)。

### 4.7 `backtest/` —— 回测/挖掘运行

[backend/app/backtest/](../../backend/app/backtest/)：`engine.py`（`BacktestEngine` 纯 Polars/NumPy 撮合+统计）、`worker.py`（spawn 隔离任务运行器）、`numba_runtime.py`、`matrix.py`（磁盘矩阵缓存）、`optimizer.py`/`walkforward.py`/`regime_alignment.py`（优化/样本外/环境对齐）、`minute_replay.py`/`minute_trigger.py`（分钟回放）、`fundamentals.py`（PIT 财务因子）、`candidates.py`、`mining.py`/`mining_runtime.py`（挖掘跑批）、`strategy.py`（矩阵预热）。

### 4.8 `jobs/` + `extensions/` + `custom/`

- `jobs/daily_pipeline.py`：APScheduler 定时任务注册（默认盘前 09:10 同步维表、盘后按偏好 15:30 跑盘后管道、盘后 15:02 depth_finalize、周期能力重探测、可选定时复盘，daily_pipeline.py:1023-1149）；`run_now`(:143) 供手动触发。
- `extensions/`：后端二开注册基础设施（loader/registry/contracts，`BACKEND_EXTENSION_API_VERSION=1`）。
- `custom/`：二开模块落地目录（模板 `_template.py.example`）。

## 5. API 域 × 前端页面路由对照

| 域 | 后端（服务为主） | 前端路由（`frontend/src/pages/`） |
| --- | --- | --- |
| 行情总览 | overview / market_overview_builder / regime / abnormal | `/` Dashboard、`/regime`、`/abnormal`、`/limit-ladder`、`/indices`、`/concept-analysis`、`/industry-analysis` |
| 自选 | watchlist / quote_service | `/watchlist` |
| 选股 | screener / strategy | `/screener` |
| 回测/挖掘 | backtest、mining | `/backtest`（factor/strategy/robustness 子视图）、`/mining` |
| 个股/财务 | stock_analysis / financials | `/stock-analysis`、`/financials` |
| 监控 | monitor_rules / alert_store | `/monitor`、`/lots` |
| 复盘 | market_recap | `/review` |
| 数据/设置 | data / pipeline / settings / ext_data | `/data`、`/settings`（8 个 Tab）、`/dev`（隐藏） |
| 扩展页面 | ext_data（动态菜单） | `/analysis/:menuId` + 扩展注入路由 |

前端所有路由定义在 [frontend/src/router.tsx](../../frontend/src/router.tsx)（lazy 加载；扩展路由经 `ExtensionBoundary` 注入）。SSE 事件驱动前端失效的白名单集中在 [frontend/src/lib/queryKeys.ts](../../frontend/src/lib/queryKeys.ts)（`SSE_INVALIDATE_PREFIXES` :130-140）。

## 6. 数据源插件化与能力路由

- **Provider 契约**：[backend/app/data_providers/base.py](../../backend/app/data_providers/base.py)（`AssetType`、`ProviderCapabilities`、`MarketDataProvider` Protocol：get_instruments/get_daily/get_adj_factors/get_minute/get_realtime）+ `normalizer.py`（统一 schema）+ `tickflow_provider.py`（内置 TickFlowProvider）。
- **能力注册表（数据集维度单一权威）**：[backend/app/data_providers/capabilities.py](../../backend/app/data_providers/capabilities.py) `CAPABILITY_REGISTRY`(:28-90)：`daily`(none)/`adj_factor`(starter)/`realtime`(starter)/`minute`(pro)/`depth5`(pro，仅 TickFlow)/`financial`(expert)/`full_minute`(expert)。每个能力独立路由（无跟随/派生特殊值），注册表声明展示元数据、偏好字段与 TickFlow 档位门槛。`build_capability_matrix`(:147) 合并注册表 + 插件/自定义源 `datasets` 声明 + 当前偏好 → `candidates/pending/usable` 契约，供设置页一次拉全与各页门控（以 `usable` 为准）。
- **能力真值源**：[backend/app/tickflow/capabilities.py](../../backend/app/tickflow/capabilities.py)（`Cap` 枚举 + `CapabilitySet`）；探测落盘与档位归一在 `tickflow/policy.py`（`capabilities.json`）；令牌桶按能力请求调度在 `tickflow/scheduler.py`/`rate_limits.py`。
- **注册与加载**：`registry.py` 内置注册表 `_PROVIDERS={"tickflow": ...}`；`data_providers/custom/` 扫描 `data/data_sources/*.yaml` + `backend/app/plugins/*/plugin.yaml`（loader.py:46），插件字段 `entry/check/datasets/api_key_env`。
- **插件**：`plugins/fuyao/`（纯 HTTP REST，datasets `[realtime, daily, adj_factor, financial]`，非路由直连项：龙虎榜/风向标/交易日历，见 trading_day.py:74 / dragon_tiger.py:75 / auction_benchmark.py:86）；`plugins/stocksdk/`（Node bridge，datasets `[daily, adj_factor, minute, realtime]`，Docker 默认不打包）。
- **红线**：上层只能通过 `get_provider()`/`provider_has_dataset()`/preferences 能力路由访问数据；provider 缺能力时明确提示/跳过/fail-closed，禁止静默换用错误数据。指数快照等特殊协议（自定义源 `get_realtime_indices`、fuyao 连坐过滤）见 CONTRIBUTING §4。

## 7. 存储与缓存分层

| 层 | 机制 | 位置 |
| --- | --- | --- |
| 持久化 | Parquet 按日/资产类型分区 | `data/`（见 §2 布局） |
| 查询 | DuckDB `:memory:` + parquet 视图（不落 db 文件） | `tickflow/repository.py` `DataStore`(:84) |
| 仓库热缓存 | Polars 缓存：enriched 最新日、instruments、live_agg 递推 | `KlineRepository`（repository.py:332+，`refresh_cache` :412） |
| 一致性 | enriched generation marker 原子发布（读侧一致性+预热替换） | `enriched_generation.py` |
| 指标 | enriched 窄表 14 列存储，68 列指标现算 + 自定义信号表达式缓存 | `indicators/pipeline.py` |
| 选股 | 策略结果文件缓存 | `services/strategy_cache.py`（`user_data/strategy_cache.json`） |
| 筛选 | Screener 进程级历史窗口 TTL 缓存 | `services/screener.py` |
| 回测 | backtest matrix 磁盘缓存（受 `backtest_matrix_disk_cache_enabled` 控制） | `backtest/matrix.py` |
| 实时 | QuoteService 盘中 `_enriched_cache`（唯一实时数据源）+ SSE 推送 | `services/quote_service.py` |
| 前端 | TanStack Query + `queryKeys.ts` + `SSE_INVALIDATE_PREFIXES` 精确失效 | `frontend/src/lib/` |

**缓存失效链（写路径必须核对）**：持久化文件 → 内存缓存 → generation/version → SSE 事件 → 前端 query invalidation。多步刷新优先构建新快照后原子替换，禁止"文件已写但返回旧内存对象"。详见 CONTRIBUTING §6。

## 8. 前端结构（`frontend/src/`）

- **路由**：`main.tsx` → `router.tsx`（lazy），`Layout.tsx` 为外壳（侧边导航 + 全局 SSE `useQuoteStream` 挂载 + 扩展导航插槽）。
- **数据层**：[lib/api.ts](../../frontend/src/lib/api.ts)（唯一 API 客户端，`request()` 封装 + 各域端点 + NDJSON 流式 async generator：`financialAnalyzeStream/stockAnalyzeStream/reviewStream/rotationAnalyzeStream`）；`lib/queryKeys.ts`（集中 `QK` 工厂 + SSE 失效前缀）；共享 hook：`useSharedQueries.ts`/`useSharedMutations.ts`/`useQuoteStream.ts`/`useStrategyPool.ts`/`useFinancials.ts`。
- **长任务状态机**：`backtestTask/miningTask/optimizerTask/walkforwardTask` + store：`aiReportStore/stockAnalysisStore/reviewStore`（后台累积、自动存报告）。
- **页面域**：`pages/`（约 24 主路由 + settings 8 Tab + backtest 3 子视图）+ 组件域目录 `components/{data,ext-data,financials,monitor,screener,signals,stock-analysis,stock-table,virtual-list}/`。
- **复用组件**：`StockPanel`（个股图表面板，被 StockPreviewDialog 与 TradeKlineModal 复用）、`StockDataTable`（虚拟滚动表格）、`Modal/Toast/PageHeader/EmptyState` 等。
- **样式系统**：Tailwind 深色 class 模式，语义色 `base/surface/elevated/border/accent` + A 股 bull/bear 色，CSS 变量在 `index.css`。

## 9. 扩展与二次开发（已实现 vs 按需）

以 [docs/secondary-development.md](../../docs/secondary-development.md) 为准，**区分已实现能力与目标契约，禁止虚构 API**。

- 分级：L1（配置/策略文件/扩展数据，最低风险）→ L2（前端插槽/路由注册、后端小粒度策略接口/注册替换）→ L3（直接改核心源码，必须最小化 + 回归）。
- 前端扩展：[frontend/src/extensions/](../../frontend/src/extensions/)（types.ts `FrontendSlotContextMap` :6-26、registry.ts、bootstrap.ts 约定 `src/custom/<ns>/extension.tsx`、`ExtensionBoundary` 错误隔离）。**已实现插槽仅 3 个**：`layout.navigation.extra`（Layout.tsx:866）、`stock-preview.footer`（StockPreviewDialog.tsx:643）、`watchlist.toolbar`（Watchlist.tsx:1491）；路由/导航/菜单注册已解耦；扩展路由不得覆盖核心路径。
- 后端扩展：`app/extensions/`（`BackendExtensionRegistrar`，支持 include_router/启动钩子/通知格式化器），落地目录 `app/custom/`；**已实现继承点**：`NotificationFormatter`（`NotificationFormatContext`）。下述接口**尚未实现，不得导入**：`CandidateFilter/ScoringPolicy/PositionSizingPolicy/RiskPolicy/StrategyProvider/MonitorConditionEvaluator/BacktestCostModel`。
- 高冲突热点（改源码需重点复核）：`backend/app/main.py`、`strategy/engine.py`、`backtest/engine.py`、`frontend/src/router.tsx`、`components/Layout.tsx`、`lib/api.ts`、`lib/queryKeys.ts`。

## 10. 生命周期与调度

- 主进程 lifespan 启动顺序见 §4.1；`MiningProcessLock` 保证单进程。
- APScheduler（`jobs/daily_pipeline.start_scheduler`，daily_pipeline.py:1045）：工作日盘前 09:10 维表同步 → 盘后 15:30（偏好可调）日K同步+除权+enriched+视图刷新 → 盘后 depth_finalize（默认 15:02，范围 15:01-18:00）→ 周期能力重探测 → 可选定时 AI 复盘；节假日由交易日探针自动停轮询与分钟增量。
- 常驻线程/服务：QuoteService 轮询、MinuteRefreshService（Expert）、DepthService 盘中轮询、ext_pull_scheduler、WecomBotService 长连接；关闭路径在 lifespan finally 逐一 shutdown，后台线程不阻止进程退出。

## 11. 数据契约红线（改代码必读）

- 比例/百分比：自定义实时数据源入口 `change_pct`/`turnover_rate` 为小数制；enriched `turnover_rate` 为百分数值；指数实时展示缓存存在百分数口径。跨边界必须显式转换并有单位测试，**禁止"数值<1 乘 100"启发式**。
- 价格与复权：enriched OHLC 为前复权；`raw_*` 为不复权原始价；涨跌停判断基于原始价；指标/收益序列价格口径必须与现有定义一致。
- 日期/交易日/时区：窗口与前 N 日按实际交易日；A 股统一北京时间；分钟 K `datetime` 为北京 naive 墙钟，入口强制归一（禁止 UTC 入库/下发）；日K/分钟/实时快照明确交易日归属；股票/ETF/指数分开存储路由，不凭代码格式猜资产类型。
- 历史股本：换手率优先公告日不晚于目标交易日的历史股本，缺省才降级最新维表；不得用报表期提前泄露未公告数据。
- 财务：按 `(symbol, period_end)` 多源取并集、逐列按公告日取最新（PIT）；公告前一律空值，绝不填 0。
- fail-closed：provider 缺能力、字段缺失、空数据必须明确提示或降级，禁止静默返回看似合理的错误金融结果。

详细口径表见 [CONTRIBUTING.md §3](../../CONTRIBUTING.md)。

## 12. 验证命令速查

```bash
cd backend
uv run pytest tests/path/to/test_x.py -q     # 定向测试（按 CONTRIBUTING §9 矩阵选择）
uv run ruff check app/path.py tests/path.py  # 静态检查

cd frontend
pnpm build                                    # tsc -b && vite build（前端任何改动必须跑）
pnpm lint                                     # eslint .

cd ..
git diff --check                              # 提交前必须执行
```

最小验证矩阵（改动类型 → 最低验证）与复审流程见 [CONTRIBUTING.md §9-§11](../../CONTRIBUTING.md)。二开额外矩阵见 [docs/secondary-development.md §7](../../docs/secondary-development.md)。

## 13. 关键文件索引

| 主题 | 位置（锚点） |
| --- | --- |
| 应用装配/路由注册/认证中间件 | [main.py](../../backend/app/main.py)（lifespan :376、装配 :86、include_router :452-477、auth :418、扩展注册 :480、CapabilityDenied :493） |
| 能力注册表与矩阵 | [capabilities.py](../../backend/app/data_providers/capabilities.py)（CAPABILITY_REGISTRY :28-90、build_capability_matrix :147） |
| Provider 契约 | [base.py](../../backend/app/data_providers/base.py)、[normalizer.py](../../backend/app/data_providers/normalizer.py)、[registry.py](../../backend/app/data_providers/registry.py) |
| 自定义源加载 | [custom/loader.py](../../backend/app/data_providers/custom/loader.py)（load_all :46、get_provider :297） |
| 存储/仓库 | [repository.py](../../backend/app/tickflow/repository.py)（DataStore :84、KlineRepository :332、refresh_cache :412） |
| 指标流水线 | [pipeline.py](../../backend/app/indicators/pipeline.py)（窄表 14 列 :90、compute_indicators :362、compute_signals :614、compute_limit_signals :673、run_pipeline :1290） |
| 策略引擎 | [strategy/engine.py](../../backend/app/strategy/engine.py) + `strategy/builtin/`（26 个内置） |
| 监控 | [strategy/monitor.py](../../backend/app/strategy/monitor.py)（StrategyMonitorService + MonitorRuleEngine） |
| 回测引擎 | [backtest/engine.py](../../backend/app/backtest/engine.py)、[worker.py](../../backend/app/backtest/worker.py) |
| 定时任务 | [jobs/daily_pipeline.py](../../backend/app/jobs/daily_pipeline.py)（start_scheduler :1045） |
| 前端路由 | [router.tsx](../../frontend/src/router.tsx) |
| 前端 API/查询键 | [lib/api.ts](../../frontend/src/lib/api.ts)、[lib/queryKeys.ts](../../frontend/src/lib/queryKeys.ts)（SSE_INVALIDATE_PREFIXES :130-140） |
| 全局 SSE | [lib/useQuoteStream.ts](../../frontend/src/lib/useQuoteStream.ts)（`/api/intraday/stream` :118） |
| 前端扩展契约 | [extensions/types.ts](../../frontend/src/extensions/types.ts)、[bootstrap.ts](../../frontend/src/extensions/bootstrap.ts) |

> 维护约定：本文件描述已存在的实现；新增能力落地后应同步更新本文档（保持"只描述现状、标注锚点"的纪律）。
