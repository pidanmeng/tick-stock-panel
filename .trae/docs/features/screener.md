---
title: Screener 选股功能
description: TSP 选股 Screener 的完整功能参考，包含策略引擎、结果缓存、前端交互、扩展方式等。
---

# 选股 Screener — 功能文档

> 本文档是 Screener 选股功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

Screener 是 TSP 的核心选股功能，菜单名"策略"，路由 `/screener`。用户通过内置策略策略、自定义 SQL 或 AI 策略对全市场 A 股/ETF 进行条件筛选，结果以表格展示并支持排序、过滤、加自选、导出到监控等操作。后端基于 enriched 数据即时计算指标，通过 StrategyEngine 执行策略，结果写入策略缓存文件供秒级加载，支持日线（盘后缓存）和分钟线（实时分区）双周期。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | [api/screener.py](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py) | 全部 Screener 端点定义（6 个核心端点 + 2 个辅助端点） |
| 核心服务 | [services/screener.py](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py) | ScreenerService：数据加载、策略上下文构建、自定义 SQL 选股 |
| 策略缓存 | [services/strategy_cache.py](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py) | 策略结果缓存读写（文件级），支持今日命中行持久化 |
| 策略运行队列 | [services/strategy_run_queue.py](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_run_queue.py) | 渐进式 run_all 后台执行管理器 |
| 策略引擎 | [strategy/engine.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py) | StrategyEngine：策略加载、执行、评分核心 |
| 策略配置覆盖 | [strategy/config.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/config.py) | 策略用户参数覆盖持久化 |
| 评分模块 | [strategy/scoring.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/scoring.py) | 评分函数定义与依赖 |
| 指标流水线 | [indicators/pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py) | enriched 数据流水线：14 列存储 + 68 列指标即时计算 |
| 应用装配 | [main.py](file:///c:/Code/tick-stock-panel/backend/app/main.py) | StrategyEngine、ScreenerService 初始化与注入 |
| 内置策略目录 | [strategy/builtin/](file:///c:/Code/tick-stock-panel/backend/app/strategy/builtin/) | 26 个内置策略文件 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | [pages/Screener.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Screener.tsx) | 主页面（1165行），路由 `/screener` |
| 策略卡片 | [components/screener/StrategyCard.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/StrategyCard.tsx) | 策略卡片展示（4 种尺寸） |
| 结果表格 | [components/screener/ScreenerTable.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/ScreenerTable.tsx) | 选股结果表格（日K/分时图/策略标签/失效行） |
| 筛选面板 | [components/screener/ScreenerFilter.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/ScreenerFilter.tsx) | 筛选面板（11 个筛选条件） |
| 策略设置弹窗 | [components/screener/StrategySettingsDialog.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/StrategySettingsDialog.tsx) | 策略参数设置弹窗 |
| 策略池管理弹窗 | [components/screener/StrategyPoolDialog.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/StrategyPoolDialog.tsx) | 策略池增加/删除弹窗 |
| AI 策略创建弹窗 | [components/screener/StrategyBuilderDialog.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/StrategyBuilderDialog.tsx) | AI 策略创建弹窗 |
| 叠加策略弹窗 | [components/screener/CompositeStrategyDialog.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/CompositeStrategyDialog.tsx) | 叠加策略创建/编辑弹窗 |
| 策略商店弹窗 | [components/screener/StrategyStoreDialog.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/StrategyStoreDialog.tsx) | 策略商店（占位，`SHOW_STRATEGY_STORE = false`） |
| 信号选择器 | [components/screener/SignalPicker.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/screener/SignalPicker.tsx) | 自定义信号选择组件 |
| 路由 | [router.tsx](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx) | 路由注册 `/screener` → `<Screener />` |
| 查询键 | [lib/queryKeys.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts) | 查询键定义（screener 系列 key） |
| API 客户端 | [lib/api.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts) | API 客户端（偏好 `screener_auto_run`） |
| 策略池 Hook | [lib/useStrategyPool.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/useStrategyPool.ts) | 策略池管理 Hook（localStorage 持久化） |
| 列配置 | [lib/screener-columns.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/screener-columns.ts) | 表格列配置定义 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 策略缓存文件 | `data/user_data/strategy_cache.json` | 策略结果缓存（文件级持久化） |
| 策略参数覆盖 | `data/user_data/strategy_overrides/{strategy_id}.json` | 策略用户参数覆盖存储 |
| 自定义策略目录 | `data/user_data/strategies/` | 用户自定义策略文件存放 |

### 测试

| 文件 | 路径 | 用途 |
|------|------|------|
| 渐进式 run_all 测试 | [tests/test_screener_run_all_progressive.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_run_all_progressive.py) | 渐进式执行测试 |
| 缓存 API 测试 | [tests/test_screener_cache_api.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_cache_api.py) | 缓存读写/过期 API 测试 |
| 内置策略参数测试 | [tests/test_screener_builtin_params.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_builtin_params.py) | 内置策略参数兼容性测试 |
| 外部访问安全测试 | [tests/test_screener_external_access.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_external_access.py) | 自定义 SQL 注入防护测试 |
| JIT 换手率测试 | [tests/test_screener_jit_turnover.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_jit_turnover.py) | 即时换手率计算测试 |
| ETF 筛选测试 | [tests/test_screener_etf.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_etf.py) | ETF 资产类型筛选测试 |
| 分钟策略测试 | [tests/test_minute_strategy.py](file:///c:/Code/tick-stock-panel/backend/tests/test_minute_strategy.py) | 分钟周期策略执行测试 |
| 涨跌停梯队测试 | [tests/test_limit_ladder_one_word.py](file:///c:/Code/tick-stock-panel/backend/tests/test_limit_ladder_one_word.py) | 涨跌停梯队 API 测试 |
| 策略历史需求测试 | [tests/test_strategy_required_history.py](file:///c:/Code/tick-stock-panel/backend/tests/test_strategy_required_history.py) | 策略历史数据需求声明测试 |
| 因子排名测试 | [tests/backtest/test_factor_rank_research.py](file:///c:/Code/tick-stock-panel/backend/tests/backtest/test_factor_rank_research.py) | 因子排名策略回测测试 |

## 业务逻辑

### 核心流程

```text
[用户打开 Screener 页面] → [加载策略缓存 (GET /cached)]
  → 缓存命中 → [秒级渲染表格]
  → 缓存未命中 → [自动触发 run_all (POST /run_all)]
    → [StrategyEngine 批量执行]
      → 快策略先返回（渐进式逐个写入缓存）
      → 慢策略后台计算（前端轮询 /cached-summary 逐个点亮）
    → [所有策略完成 → 完整渲染]
[用户操作] → [筛选/排序/加自选/策略监控/策略设置/策略池管理/AI 策略创建]
```

### 数据流

1. **输入来源**：
   - enriched Parquet 数据（`data/enriched/{symbol}/` 或 `data/enriched/combined/`），由 `indicators.pipeline` 盘后流水线产出
   - 分钟级数据：当日分钟 K 分区（`data/kline/1m/{symbol}/`），直读最近分区文件
   - 扩展列：通过 `_load_ext_value_maps`([api/screener.py:106](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L106)) 从板块/财务数据加载，缓存在 `_ext_value_map_cache`([api/screener.py:90](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L90))
   - 策略参数覆盖：用户保存的 `strategy_overrides/{strategy_id}.json` 文件

2. **处理过程**：
   - `ScreenerService._load_enriched_for_date`([screener.py:51](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L51))：优先从内存缓存读取 enriched 数据，回退到 `_compute_enriched_full`([screener.py:143](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L143)) 从 14 列基础 Parquet 即时计算完整指标（含 150 天 warmup）
   - `ScreenerService.build_strategy_context`([screener.py:378](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L378))：装配 `StrategyDataContext`，日线策略走 `_load_enriched_history`，分钟策略走 `_load_minute_history`
   - `StrategyEngine.run`([engine.py:877](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L877))：单策略执行 → 基础过滤 → 策略过滤 → 评分排序
   - `StrategyEngine.run_all`([engine.py:1117](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L1117))：批量执行，共享 context，线程池并发
   - `_run_all_progressive`([api/screener.py:505](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L505))：渐进式执行，通过 `strategy_run_queue.MANAGER` 管理后台任务

3. **输出去向**：
   - 策略缓存文件 `strategy_cache.json`([strategy_cache.py:37](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py#L37))：日线策略结果持久化（盘后写 + 盘中监控引擎覆盖）
   - 分钟策略结果直接返回（不缓存）
   - 前端通过 `GET /cached`、`GET /cached-summary`、`GET /cached-result/{strategy_id}` 读取缓存

### 调用链

```text
用户交互 → Screener.tsx (frontend)
  → API 客户端 (api.ts) → FastAPI 路由 (api/screener.py)
    → ScreenerService (services/screener.py)
      → KlineRepository (数据仓库) → Parquet 文件
      → indicators.pipeline (指标计算)
      → StrategyEngine (strategy/engine.py)
        → strategy/builtin/*.py (内置策略)
        → strategy/scoring.py (评分)
      → strategy_cache (services/strategy_cache.py) → strategy_cache.json
    → JSON 响应 → 前端 ScreenerTable 渲染
```

### 状态机

#### 策略执行状态（`StrategyRunHandle`）

```text
PENDING → RUNNING → COMPLETED
               ↓
            ERROR
```

- `PENDING`：排队等待执行（快策略先执行，[strategy_run_queue.py:67](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_run_queue.py#L67)）
- `RUNNING`：正在执行中，线程安全快照可查询（[strategy_run_queue.py:77](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_run_queue.py#L77)）
- `COMPLETED`：执行完成，结果写入缓存
- `ERROR`：执行异常，前端卡片显示错误状态

#### run_all 渐进式生命周期

```text
[POST /run_all] → 创建 StrategyRunManager 任务
  → 按历史耗时升序排列策略（order_strategy_ids）
  → 逐个执行，快策略先返回（单个策略完成即写入缓存）
  → 前端轮询 /cached-summary，逐个点亮策略卡片
  → 所有策略完成 → 前端停止轮询
```

#### 缓存生命周期

```text
[盘后 15:30 管道完成] → [策略引擎执行 run_all]
  → [写入 strategy_cache.json]
  → [页面加载直接读缓存，秒级渲染]
  → [盘中监控引擎实时结果覆盖缓存行（涨跌/价格/信号状态）]
  → [次日盘后管道刷新 → 缓存 as_of 过期 → 自动触发新 run_all]
```

## 关键数据结构

### API 契约

#### `GET /api/screener/strategies` ([api/screener.py:230](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L230))

**Query**: `asset_type: 'stock' | 'etf'`, `timeframe: '1d' | '1m' | 'all'`

**Response**: `StrategyDef[]` 数组，每个包含：
- `id`, `name`, `description`, `category`, `tags`
- `execution_backend`: `polars_expr | matrix_native | python_history_legacy | composite | minute_filter`
- `params`: 参数定义（`{key: {label, type, default, ...}}`）
- `required_history_days`: 所需历史数据天数
- `timeframe`: `'1d' | '1m'`
- `is_composite`: 是否叠加策略
- `scoring`: 评分配置

#### `POST /api/screener/run` ([api/screener.py:260](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L260))

**Body**: `{ sql: string, asset_type: 'stock' | 'etf', params?: {...} }`

**Response**: `{ rows: ScreenerRow[], total_count: int, columns: ColumnDef[] }`

使用独立 DuckDB 连接执行自定义 SQL（`enable_external_access=False` 防注入，[screener.py:310](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L310)）。

#### `POST /api/screener/run_preset` ([api/screener.py:280](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L280))

**Body**: `{ strategy_id: string, asset_type: 'stock' | 'etf', params?: {...}, scoring_config?: {...} }`

**Response**: `ScreenerRunResult`（命中行 + 列定义 + 元数据）

#### `POST /api/screener/run_all` ([api/screener.py:597](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L597))

**Body**: `{ asset_type: 'stock' | 'etf', timeframe: '1d' | '1m' | 'all' }`

**Response**（渐进式）：
- 首次返回：`{ status: 'started', strategy_ids: string[], mode: 'normal' | 'progressive' }`
- 前端轮询 `GET /cached-summary` 获取进度

#### `GET /api/screener/cached` ([api/screener.py:353](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L353))

**Query**: `asset_type: 'stock' | 'etf'`

**Response**: `{ as_of: string, results: { [strategy_id]: CachedStrategyResult }, today_ever_matched: string[] }`

叠加监控引擎实时结果（[api/screener.py:337-349](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L337-L349)）。

#### `GET /api/screener/cached-summary` ([api/screener.py:375](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L375))

**Response**: `{ as_of: string, strategies: { [strategy_id]: { match_count, is_stale, updated_at } } }`

轻量摘要，用于渐进式轮询。

#### `GET /api/screener/cached-result/{strategy_id}` ([api/screener.py:412](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L412))

**Response**: `CachedStrategyResult`（含 `rows` 明细 + `today_ever_rows` 失效行）

#### `GET /api/screener/market-snapshot` ([api/screener.py:470](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L470))

**Response**: 全市场行情快照（涨跌分布、成交额、涨跌停家数等）。

#### `GET /api/screener/limit-ladder` ([api/screener.py:726](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L726))

**Response**: 涨跌停梯队（连板/连跌板统计）。

### 存储结构

#### strategy_cache.json

```json
{
  "as_of": "2025-01-15",
  "enriched_mtime": 1736937600.0,
  "updated_at": 1736937700.0,
  "results": {
    "strategy_id_1": {
      "strategy_id": "strategy_id_1",
      "strategy_name": "策略名称",
      "match_count": 25,
      "total_count": 5000,
      "columns": ["symbol", "name", "close", "change_pct", "score", ...],
      "rows": [
        { "symbol": "000001", "name": "平安银行", "close": 12.34, "change_pct": 0.025, "score": 0.85, ... },
        ...
      ],
      "today_ever_rows": [
        { "symbol": "000002", "name": "万科A", "close": 15.67, ... },
        ...
      ],
      "is_stale": false,
      "updated_at": 1736937700.0
    }
  },
  "today_ever_matched": ["000001", "000002", ...],
  "today_ever_rows": { "symbol": { "name": "...", ... } }
}
```

- `today_ever_rows`：今日曾命中但已失效的行（盘中价格变化导致信号消失），前端灰色显示
- `today_ever_matched`：今日曾命中的 symbol 集合，用于跨策略快速查重
- `is_stale`：enriched 数据已更新但策略未重算时置为 `true`

#### 策略参数覆盖文件

`data/user_data/strategy_overrides/{strategy_id}.json` ([config.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/config.py))：

```json
{
  "params": { "ma_short": 10, "ma_long": 60 }
}
```

进程内带 mtime 签名缓存，避免每次读盘。

#### 自定义策略文件

`data/user_data/strategies/{strategy_name}.py`，格式与内置策略相同（`execution_backend` 声明 + `filter_fn`/`filter_polars_expr`/`matrix_filter` 等）。

#### enriched Parquet 存储列（14 列，[pipeline.py:93-102](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L93-L102)）

| 列名 | 说明 | 口径 |
|------|------|------|
| symbol | 股票代码 | |
| date | 交易日期 | |
| open/high/low/close | 前复权价 | 前复权 |
| volume | 成交量 | |
| amount | 成交额 | |
| raw_close/raw_high/raw_low | 原始价 | 不复权 |
| turnover_rate | 换手率 | 百分数（依赖 float_shares） |
| consecutive_limit_ups | 连板天数 | 递推状态 |
| consecutive_limit_downs | 连跌板天数 | 递推状态 |
| quote_ts | 行情时间戳(ms) | 盘后校验/量比折算 |

### 内存结构

#### StrategyDataContext ([engine.py:151](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L151))

```python
@dataclass
class StrategyDataContext:
    df: pl.DataFrame           # 主数据（日线 enriched 或分钟数据）
    target_date: date          # 目标日期
    all_data: dict[str, pl.DataFrame] | None  # 全历史数据（日线策略）
    daily_history: pl.DataFrame | None        # 日线历史（分钟策略引用）
    asset_type: str            # 'stock' | 'etf'
```

#### ext_value_map_cache ([api/screener.py:90](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L90))

```python
# 进程内缓存，按底层 parquet 文件 (路径, mtime) 签名 memoize
# 文件未变则复用上次的 {symbol: value} map；parquet 被重写 (mtime 变化) 时自动失效重算
_ext_value_map_cache: dict[tuple[str, str], tuple[Any, dict[str, Any]]] = {}
```

#### ScreenerService 内存缓存

```python
# 按 (target_date, asset_type) 键缓存 enriched 数据
_enriched_cache: dict[tuple[date, str], pl.DataFrame] = {}
```

#### StrategyRunManager ([strategy_run_queue.py:116](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_run_queue.py#L116))

```python
class StrategyRunManager:
    _lock: threading.Lock
    _current_run: StrategyRunHandle | None  # 当前执行中的 run_all
    _pending_key: str | None                # 等待中的 key
```

单飞管理器：相同 key 搭车现有执行，不同 key 排队等待。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

1. **自定义策略**：在 `data/user_data/strategies/` 下创建 `.py` 文件，使用 `@strategy` 装饰器声明 `execution_backend` 和 `filter_fn`/`filter_polars_expr`/`matrix_filter`。参考 [docs/secondary-development.md](file:///c:/Code/tick-stock-panel/docs/secondary-development.md) 的策略开发规范。

2. **策略参数覆盖**：通过 `StrategySettingsDialog` 修改策略参数，保存到 `data/user_data/strategy_overrides/{strategy_id}.json`([config.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/config.py))。

3. **策略池管理**：前端通过 `StrategyPoolDialog` 管理显示策略，通过 `useStrategyPool`([useStrategyPool.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/useStrategyPool.ts)) Hook 持久化到 localStorage。日线和分钟策略统一池管理。

4. **AI 策略创建**：通过 `StrategyBuilderDialog` 输入自然语言描述，后端生成策略代码并保存到 `data/user_data/strategies/`。

5. **前置筛选**：`ScreenerFilter` 面板支持 11 个筛选条件（价格/涨跌幅/动量/市值/量比/RSI/板块等），组合后影响策略执行范围。

### L2 扩展（插槽/路由/注册替换）

Screener 功能当前未开放 L2 前端插槽。后端扩展点：

- **策略加载**：`StrategyEngine._load_all`([engine.py:259](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L259)) 自动扫描 `strategy/builtin/` 和 `data/user_data/strategies/` 目录，新增策略文件即生效。
- **评分函数**：[strategy/scoring.py](file:///c:/Code/tick-stock-panel/backend/app/strategy/scoring.py) 定义 `effective_scoring`、`scoring_dependencies`、`scoring_value_expr`、`scoring_warmup_bars`，可通过 `scoring_config` 参数在策略调用时指定。

### L3 修改（直接改源码）

如果必须修改核心源码，建议的最小改动方式和注意事项：

- **新增指标**：修改 `indicators/pipeline.py` 中的 `ENRICHED_COLUMNS`([pipeline.py:110](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L110)) 和 `_compute_enriched_full`([screener.py:143](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L143)) 中的计算逻辑。注意：指标计算需要 150 天 warmup 数据，新指标需确认 warmup 是否足够（[screener.py:143](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L143)）。
- **新增策略类型**：修改 `StrategyEngine._load_file`([engine.py:374](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L374)) 支持新的 `execution_backend`。现有 5 种后端：`polars_expr`、`matrix_native`、`python_history_legacy`、`composite`、`minute_filter`。
- **修改基础过滤**：调整 `DEFAULT_BASIC_FILTER`([engine.py:38](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L38)) 或 `_basic_filter_expr`([engine.py:1547](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L1547))。
- **修改评分逻辑**：调整 `_apply_scoring`([engine.py:1683](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L1683)) 中的 min-max 归一化或加权求和逻辑。
- **修改缓存逻辑**：调整 `strategy_cache.py` 中的 `read_cache`([strategy_cache.py:63](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py#L63))、`write_cache`([strategy_cache.py:111](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py#L111)) 或 `_write_cache_locked`([strategy_cache.py:129](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py#L129))。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 策略缓存文件 (`strategy_cache.json`) | 盘后 15:30 管道完成自动触发 run_all 重写；手动 POST /run_all 覆盖 | 策略结果页面加载延迟 |
| 历史窗口 TTL 缓存 (`ScreenerService._history_cache`) | 进程重启、TTL 过期或 `clear_history_cache()`（清除数据后调用，[screener.py:44](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L44)） | 下次加载需重新计算 enriched 指标 |
| ext_value_map_cache | 底层 parquet 文件 mtime 变化时自动失效重算（[api/screener.py:90-103](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L90-L103)） | 扩展列需重新加载 |
| SSE/前端 | 策略结果不跟随 SSE 刷新（[queryKeys.ts:127-129](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L127-L129)）。策略缓存变化后前端需手动刷新或轮询 /cached-summary | 策略页不随行情 tick 自动刷新 |
| 策略参数覆盖缓存 | 文件 mtime 变化时自动失效（mtime 签名缓存） | 下次读取策略参数时重新加载 |
| 策略池 (localStorage) | 前端操作 `StrategyPoolDialog` 时更新 | 仅影响当前浏览器 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 增量策略测试 | [tests/test_screener_builtin_params.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_builtin_params.py) | 内置策略参数兼容性，新策略参数变化不破坏现有接口 |
| 渐进式 run_all | [tests/test_screener_run_all_progressive.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_run_all_progressive.py) | 渐进式执行，快策略先返回，慢策略后台计算 |
| 缓存 API | [tests/test_screener_cache_api.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_cache_api.py) | 缓存读写、过期逻辑、today_ever_rows 持久化 |
| 外部访问安全 | [tests/test_screener_external_access.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_external_access.py) | 自定义 SQL 注入防护，`enable_external_access=False` |
| JIT 换手率 | [tests/test_screener_jit_turnover.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_jit_turnover.py) | 即时换手率计算正确性 |
| ETF 筛选 | [tests/test_screener_etf.py](file:///c:/Code/tick-stock-panel/backend/tests/test_screener_etf.py) | ETF 资产类型独立筛选 |
| 分钟策略 | [tests/test_minute_strategy.py](file:///c:/Code/tick-stock-panel/backend/tests/test_minute_strategy.py) | 分钟周期策略数据加载与执行 |
| 涨跌停梯队 | [tests/test_limit_ladder_one_word.py](file:///c:/Code/tick-stock-panel/backend/tests/test_limit_ladder_one_word.py) | 涨跌停梯队 API 正确性 |
| 策略历史需求 | [tests/test_strategy_required_history.py](file:///c:/Code/tick-stock-panel/backend/tests/test_strategy_required_history.py) | 策略声明历史天数与实际需求匹配 |
| 因子排名 | [tests/backtest/test_factor_rank_research.py](file:///c:/Code/tick-stock-panel/backend/tests/backtest/test_factor_rank_research.py) | 因子排名策略在回测中的正确性 |

## 依赖关系

### 依赖的其他功能

- **Enriched 数据流水线** ([indicators/pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py))：Screener 依赖盘后 enriched 数据作为日线策略输入。管道未完成时策略结果标记为 `is_stale`。
- **KlineRepository**：Screener 通过 `KlineRepository` 读取 Parquet 数据，包括日线 enriched 和分钟 K 线。
- **数据源同步**：依赖数据源（TickFlow/fuyao/stock-sdk）同步完成，确保 enriched 数据包含最新交易日数据。
- **监控引擎**：`GET /cached` 叠加监控引擎实时结果（[api/screener.py:337-349](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L337-L349)），监控引擎盘中实时更新影响缓存结果展示。

### 被依赖的功能

- **监控引擎**：Screener 结果表格中的"发监控"按钮将策略结果导入监控引擎。
- **回测**：自定义策略可在回测中引用（[tests/backtest/test_factor_rank_research.py](file:///c:/Code/tick-stock-panel/backend/tests/backtest/test_factor_rank_research.py)）。

## 常见问题与注意事项

### 金融口径

1. **换手率口径**：enriched 中 `turnover_rate` 为百分数值（如 5.5 表示 5.5%），而实时源入口 `turnover_rate` 为小数制（如 0.055）。策略中使用时需确认口径，参见 [pipeline.py:98](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L98)。
2. **涨跌停判断**：用原始价（`raw_close`/`raw_high`/`raw_low`）而非前复权价判断涨跌停（[pipeline.py:96-97](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L96-L97)）。
3. **复权价**：enriched OHLC 为前复权价，`raw_*` 为不复权原始价（[pipeline.py:95-97](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L95-L97)）。
4. **交易日**：窗口计算按实际交易日，非自然日（取消周末过滤）。
5. **时区**：A 股统一北京时间；分钟 K `datetime` 为北京 naive 墙钟。

### 性能注意事项

1. **首次加载**：首次打开 Screener 页面（或缓存未命中时）自动触发 `run_all`，日线策略约 5-30 秒完成（取决于策略数量和复杂度）。分钟策略因需实时读取分钟分区，可能更慢。
2. **渐进式执行**：`run_all` 按历史耗时升序排列策略（[strategy_run_queue.py:67](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_run_queue.py#L67)），快策略先返回，慢策略后台计算，前端逐个点亮。
3. **enriched 即时计算**：`_compute_enriched_full`([screener.py:143](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L143)) 在内存缓存未命中时从 14 列基础数据即时计算完整指标，需 150 天 warmup 数据，首次耗时约 2-5 秒（5000 只股票）。
4. **扩展列加载**：`_load_ext_value_maps`([api/screener.py:106](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L106)) 按需加载板块/财务扩展列，结果缓存在 `_ext_value_map_cache` 中。
5. **前端缓存策略**：策略结果不跟随 SSE 行情刷新（[queryKeys.ts:127-129](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py#L127-L129)），避免每个 tick 双重刷新。用户可手动刷新或等盘后自动重算。
6. **策略商店**：`StrategyStoreDialog` 中 `SHOW_STRATEGY_STORE = false`，策略商店功能为占位状态，当前不可用。

### 安全注意事项

1. **SQL 注入防护**：`POST /api/screener/run` 使用独立 DuckDB 内存连接，`enable_external_access=False`([screener.py:310](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L310))，禁止读取文件系统或访问外部数据库。
2. **策略文件安全**：`StrategyEngine._load_file`([engine.py:374](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L374)) 对策略文件进行 AST 安全校验，防止执行恶意代码。
3. **自定义策略来源**：`StrategyBuilderDialog` 生成的 AI 策略和 `data/user_data/strategies/` 中的自定义策略本质上是 Python 代码执行，需要注意来源可信。

### 注意事项

1. **缓存过期**：`strategy_cache.json` 已移除 enriched mtime 过期校验（[strategy_cache.py:66-70](file:///c:/Code/tick-stock-panel/backend/app/services/strategy_cache.py#L66-L70) 注释说明），缓存过期依赖盘后管道触发 run_all 重写。
2. **叠加策略**：`CompositeStrategy` 子策略共享同一 `StrategyDataContext`，需确保子策略依赖的列在当前 context 中已计算。
3. **分钟策略**：分钟策略的 `StrategyDataContext` 包含 `daily_history` 字段（[engine.py:151](file:///c:/Code/tick-stock-panel/backend/app/strategy/engine.py#L151)），供分钟策略引用日线数据。分钟数据直读当日分钟分区，不支持跨日。
4. **策略池**：日线和分钟策略统一池（`useStrategyPool`），选择 `all` 周期时同时显示两类策略。策略卡片根据 `timeframe` 显示不同标识。
