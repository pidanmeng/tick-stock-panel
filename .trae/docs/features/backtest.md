---
title: 回测 Backtest — 功能文档
description: 回测模块的完整参考，涵盖策略回测、因子回测、参数优化、Walk-Forward 分析、稳健性验证与因子挖掘。
---

# 回测 Backtest — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

回测模块是 TSP 的核心量化分析能力，提供从单标的信号回测到全市场矩阵化策略回测、因子 IC/IR 分析、参数网格优化、Walk-Forward 样本外验证、稳健性压力测试，以及基于嵌套交叉验证的因子挖掘与自动挖掘流水线。所有耗时计算通过 spawn 子进程隔离执行，结果通过 SSE 流式推送至前端。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 回测引擎 | `backend/app/backtest/engine.py` | 3400+ 行。核心撮合引擎：`MatcherConfig`、`SimulationOptions`、`PanelCache`(LRU+TTL+single-flight)、`BacktestEngine`（load_panel/simulate/simulate_independent_candidates 矩阵撮合） |
| 策略回测服务 | `backend/app/backtest/strategy.py` | 1400+ 行。`StrategyBacktestService` 编排策略回测全流程：矩阵准备、信号生成、撮合、结果组装 |
| 矩阵数据层 | `backend/app/backtest/matrix.py` | 2500+ 行。`MatrixComputeCache`（LRU+TTL+single-flight 字节限界缓存）、`MarketDataMatrix`、`SignalMatrix`、`build_market_data_matrix`、`.backtest_matrix_cache` 磁盘缓存 |
| 子进程运行器 | `backend/app/backtest/worker.py` | 395 行。`make_worker_task`/`run_worker_task`：spawn 进程隔离，支持 kind=backtest/optimize/walkforward/mining |
| 参数优化器 | `backend/app/backtest/optimizer.py` | `OptimizeConfig`、`expand_param_grid`、`GRID_MAX_COMBINATIONS=2000` |
| Walk-Forward | `backend/app/backtest/walkforward.py` | `WalkForwardConfig`、`generate_folds`（test_start=train_end+1 防前视泄漏）、`WalkForwardService` |
| 因子挖掘算法 | `backend/app/backtest/mining.py` | 嵌套交叉验证（NestedValidationConfig）、`evaluate_candidate_gate`、束搜索组合（beam_search_factor_combinations） |
| 挖掘运行时 | `backend/app/backtest/mining_runtime.py` | 仅 worker 内执行的挖掘运行时：`MatcherCandidateEvaluator`、`TrainingMetricProvider` |
| 研究候选存储 | `backend/app/backtest/candidates.py` | `CandidateStore`：JSON 文件 `data/user_data/research_candidates.json`，MAX_CANDIDATES=200 |
| 因子回测服务 | `backend/app/backtest/factor.py` | `FactorBacktestService`：IC/IR 分析、分层回测、多空组合、NW HAC t 值与 BH-FDR q 值 |
| 信号回测 API | `backend/app/api/backtest.py` | 1209 行。SSE 流式回测/优化/walk-forward，`_running_jobs` 任务表 + `_JOB_TTL=300` |
| 挖掘 API | `backend/app/api/mining.py` | 866 行。挖掘运行 CRUD、SSE 事件流、候选 promote/publish |
| 挖掘任务管理器 | `backend/app/services/mining_manager.py` | `MiningJobManager`：线程编排 + MiningRunStore 持久化 + spawn worker |
| 挖掘运行存储 | `backend/app/services/mining_jobs.py` | `MiningRunStore`：manifest/summary/events.jsonl/artifact parquet 持久化，状态机（9 状态） |
| 挖掘候选发布 | `backend/app/services/mining_candidates.py` | `MiningCandidateService`：promote（入候选池）/publish（发布为自定义策略），门控验证 |
| 挖掘预检 | `backend/app/services/mining_preflight.py` | `mining_availability`：enriched 分区日期检查 + 所需交易 bar 数验证 |
| 自动挖掘 | `backend/app/services/auto_mining.py` | `screen_all_factors`：L1 全量因子统计筛选（IC/IR/t/q 四维门控） |
| 挖掘定时调度 | `backend/app/services/mining_schedule.py` | `run_weekly_mining`：周度定时挖掘编排，`build_data_fingerprint` 数据指纹去重 |
| 挖掘进程锁 | `backend/app/services/mining_process_lock.py` | `MiningProcessLock`：文件锁 `.mining_process.lock`，防多进程并发 |
| 重型任务限制器 | `backend/app/services/heavy_job_limiter.py` | `shared_heavy_job_limiter`：capacity=2，normal=1 槽，mining=2 槽 |
| 信号回测服务 | `backend/app/services/backtest.py` | 427 行。`BacktestService`：vectorbt 旧信号回测，全项目唯一 pandas 边界 |
| 矩阵缓存预热 | `backend/app/services/matrix_prewarm_owner.py` | 启动时后台预热 matrix disk cache |
| 应用组装 | `backend/app/main.py` | 初始化 MiningJobManager、BacktestEngine、matrix_prewarm、scheduler |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 回测页面 | `frontend/src/pages/Backtest.tsx` | 136 行。Tab 路由（strategy/robustness），旧链接重定向（/factors） |
| 策略回测 | `frontend/src/pages/backtest/StrategyBacktest.tsx` | 主策略回测 UI：配置面板、参数输入、StockPoolPicker、SSE 流式结果显示、交易明细、Export CSV |
| 策略优化 | `frontend/src/pages/backtest/StrategyOptimizer.tsx` | 29 行。参数网格优化入口 |
| Walk-Forward | `frontend/src/pages/backtest/StrategyWalkForward.tsx` | Walk-Forward 分析 UI：OOS 折线图、各折统计 |
| 稳健性验证 | `frontend/src/pages/backtest/RobustnessValidation.tsx` | 8 行。稳健性验证入口 |
| 因子回测 | `frontend/src/pages/backtest/FactorBacktest.tsx` | 因子 IC/IR 分析 UI：StatCard、IC 序列、分层 NAV、多空统计 |
| 因子发现 | `frontend/src/pages/backtest/FactorDiscovery.tsx` | 因子发现 UI：`BatchDiscovery` 批量检验 + 排序筛选 |
| 挖掘工作台 | `frontend/src/pages/backtest/MiningWorkbench.tsx` | 挖掘工作台：运行管理、候选列表、因子表、OOS 图表 |
| 研究候选弹窗 | `frontend/src/pages/backtest/ResearchCandidatesDialog.tsx` | 科研候选池：跨页面载入复测 |
| 自动挖掘弹窗 | `frontend/src/pages/backtest/AutoMiningDialog.tsx` | 自动挖掘配置弹窗 |
| 因子信号添加 | `frontend/src/pages/backtest/AddFactorSignalDialog.tsx` | 添加因子信号条件弹窗 |
| 候选转换器 | `frontend/src/pages/backtest/researchCandidates.ts` | `factorResultCandidate`/`strategyResultCandidate` 转换器 |
| 图表 - 策略净值 | `frontend/src/pages/backtest/charts/StrategyNavChart.tsx` | 策略净值曲线（ECharts） |
| 图表 - 因子 IC | `frontend/src/pages/backtest/charts/FactorICChart.tsx` | IC 序列柱状图 |
| 图表 - 分层 NAV | `frontend/src/pages/backtest/charts/FactorGroupNavChart.tsx` | 分层组合净值曲线 |
| 图表 - 挖掘 OOS | `frontend/src/pages/backtest/charts/MiningOosChart.tsx` | 挖掘样本外折叠图表 |
| 图表 - 相关性热力 | `frontend/src/pages/backtest/charts/FactorCorrelationHeatmap.tsx` | 因子相关性热力图 |
| 图表 - 区制对比 | `frontend/src/pages/backtest/charts/RegimeComparisonChart.tsx` | 不同市场区制下绩效对比 |
| 图表 - 收益分布 | `frontend/src/pages/backtest/charts/ReturnDistributionChart.tsx` | 收益分布直方图 |
| 图表 - ECharts Hook | `frontend/src/pages/backtest/charts/useECharts.ts` | ECharts 懒加载 Hook |
| 组件 - 参数扫描 | `frontend/src/pages/backtest/components/paramSweep.tsx` | `useParamSweep` Hook、`StrategySelect`、`SweepParamList`、`CombosHint` |
| 组件 - K 线弹窗 | `frontend/src/pages/backtest/components/TradeKlineModal.tsx` | 交易 K 线详情弹窗 |
| 组件 - 选股 K 线 | `frontend/src/pages/backtest/components/PicksSymbolKlineModal.tsx` | 选股结果 K 线弹窗 |

### 测试

| 文件 | 路径 | 用途 |
|------|------|------|
| 策略回测正确性 | `backend/tests/backtest/test_strategy_backtest_correctness.py` | 策略回测撮合逻辑验证 |
| 引擎组合测试 | `backend/tests/backtest/test_engine_portfolio.py` | 组合级回测验证 |
| 全文模拟尾端 | `backend/tests/backtest/test_full_simulation_tail.py` | 模拟尾端行为验证 |
| 矩阵策略 | `backend/tests/backtest/test_matrix_strategy.py` | 矩阵策略信号生成验证 |
| 矩阵缓存 | `backend/tests/backtest/test_matrix_compute_cache.py` | MatrixComputeCache LRU+TTL 验证 |
| 市场矩阵 | `backend/tests/backtest/test_market_matrix.py` | MarketDataMatrix 构建验证 |
| 优化器运行 | `backend/tests/backtest/test_optimizer_run.py` | 参数优化执行验证 |
| 优化器网格 | `backend/tests/backtest/test_optimizer_grid.py` | 网格展开逻辑验证 |
| 优化器 API | `backend/tests/backtest/test_optimizer_api.py` | 优化 SSE 端点验证 |
| Walk-Forward | `backend/tests/backtest/test_walkforward.py` | 折生成与 OOS 聚合验证 |
| 因子指标 | `backend/tests/backtest/test_factor_metrics.py` | IC/IR/NW t/BH q 计算验证 |
| 因子批量 | `backend/tests/backtest/test_factor_batch.py` | 批量因子回测验证 |
| 因子默认范围 | `backend/tests/backtest/test_factor_default_range.py` | 默认日期范围验证 |
| 因子排名研究 | `backend/tests/backtest/test_factor_rank_research.py` | 因子排名策略验证 |
| 挖掘算法 | `backend/tests/backtest/test_mining.py` | 挖掘核心算法验证 |
| 挖掘运行时 | `backend/tests/backtest/test_mining_runtime.py` | 挖掘运行时执行验证 |
| 稳健性指标 | `backend/tests/backtest/test_robustness_metrics.py` | 稳健性指标计算验证 |
| 研究候选 | `backend/tests/backtest/test_research_candidates.py` | CandidateStore 增删查验证 |
| 研究 API | `backend/tests/backtest/test_research_api.py` | 候选 API 端点验证 |
| 成本模型 | `backend/tests/backtest/test_cost_model.py` | 佣金/印花税/滑点验证 |
| 分钟撮合 | `backend/tests/backtest/test_minute_fill.py` | 分钟级成交验证 |
| 分钟回测 | `backend/tests/backtest/test_minute_backtest.py` | 分钟 K 回测验证 |
| Numba 运行时 | `backend/tests/backtest/test_numba_runtime.py` | Numba JIT 加速验证 |
| 依赖解析 | `backend/tests/backtest/test_dependencies.py` | 策略依赖解析验证 |
| 复合策略 E2E | `backend/tests/backtest/test_composite_backtest_e2e.py` | 复合策略端到端验证 |
| 最大持仓退出 | `backend/tests/backtest/test_max_hold_exits.py` | max_hold_days 强制退出验证 |
| 子进程 | `backend/tests/backtest/test_worker_process.py` | spawn 进程隔离验证 |
| 挖掘管理器 | `backend/tests/test_mining_manager.py` | MiningJobManager 线程编排验证 |
| 挖掘运行存储 | `backend/tests/test_mining_jobs.py` | MiningRunStore 持久化验证 |
| 挖掘候选发布 | `backend/tests/test_mining_candidates.py` | promote/publish 门控验证 |
| 挖掘 API | `backend/tests/test_mining_api.py` | 挖掘 API 端点验证 |
| 自动挖掘 | `backend/tests/test_auto_mining.py` | screen_all_factors 筛选验证 |
| 挖掘调度 | `backend/tests/test_mining_schedule.py` | 定时挖掘编排与指纹验证 |
| 挖掘进程锁 | `backend/tests/test_mining_process_lock.py` | 文件锁验证 |
| 挖掘调度设置 | `backend/tests/test_settings_mining_schedule.py` | 调度偏好验证 |
| 生命周期集成 | `backend/tests/test_main_mining_lifespan.py` | mining_manager 初始化/恢复/关闭验证 |
| ETF 回测 | `backend/tests/test_backtest_etf.py` | ETF 回测路径验证 |
| 回测 Warmup | `backend/tests/test_backtest_warmup.py` | 指标预热窗口验证 |

## 业务逻辑

### 核心流程

回测模块按复杂度分为六个层级，对应不同的入口和执行路径：

```text
[信号回测] → BacktestService.run → vectorbt Portfolio.from_signals → 结果持久化
[因子回测] → FactorBacktestService.run → IC/IR 分析 + 分层回测 + 多空组合
[策略回测] → StrategyBacktestService.run → make_worker_task → spawn worker → _worker_entry
                → StrategyEngine → MarketDataMatrix → simulate_independent_candidates → SSE stream
[参数优化] → StrategyOptimizer.optimize → make_worker_task(kind=optimize) → spawn worker
                → expand_param_grid → StrategyBacktestService.prepare_matrix_optimization
                → 共享 base matrix → 网格 trials → objective_value → SSE stream
[Walk-Forward] → WalkForwardService.run → make_worker_task(kind=walkforward) → spawn worker
                → generate_folds → 逐折优化 → aggregate_oos → SSE stream
[因子挖掘] → MiningJobManager.start → threading + spawn worker(kind=mining)
                → nested cross-validation (outer/inner folds)
                → prune_correlated_factors → beam_search_factor_combinations
                → evaluate_candidate_gate → artifact parquet → SSE events
```

### 数据流

1. **输入来源**：
   - 用户请求：API 传入 strategy_id/factor_names/symbols/start/end/params 等
   - enriched 数据：`KlineRepository` → `indicators.pipeline.compute_all` → 14 列窄表 + 68 列指标现算
   - 财务因子：`financial_sync` → `load_fundamental_snapshot` → 按公告日门控附加
   - 策略定义：`StrategyEngine` 从 `strategy/` 目录加载（builtin/custom/ai/composite）

2. **处理过程**：
   - **信号回测**：Polars scan_enriched_parquet → compute_all → to_pandas → vectorbt 信号矩阵 → 组合统计
   - **策略回测**：`BacktestEngine.load_panel_for_backtest` → generation 快照断言 → feature_plan 窄列加载 → compute_indicators/compute_signals → `MarketDataMatrix` 构建 → `simulate_independent_candidates` 纯 NumPy 状态机撮合
   - **因子回测**：`load_factor_panel` → `_evaluate_panel` → IC 序列计算 → 分层组合回测 → 多空统计 → NW HAC t 值 / BH-FDR q 值
   - **参数优化**：`prepare_matrix_optimization` 共享 base matrix → 各 trial 覆盖 params → 逐 trial 回测 → objective 排序
   - **Walk-Forward**：`generate_folds`（test_start=train_end+1）→ 每折内调用 optimizer → `aggregate_oos` 计算退化/一致性
   - **因子挖掘**：`nested_fold_selection`（outer/inner 双层）→ `prune_correlated_factors`（correlation_threshold=0.75）→ `beam_search_factor_combinations`（beam_width=12, max_combination=4）→ `evaluate_candidate_gate`（6 维门控）

3. **输出去向**：
   - SSE 流：`/api/backtest/strategy/stream` → progress/done/error 事件类型
   - SSE 流：`/api/backtest/optimize/stream` → optimizer_progress/done/error，首个事件回吐 job_key
   - SSE 流：`/api/backtest/walkforward/stream` → 单折级别进度
   - SSE 流：`/api/backtest/mining/runs/{run_id}/events` → 挖掘事件（sse_starlette）
   - 持久化：`MiningRunStore` → manifest.json + events.jsonl + summary.json + artifacts（factors/correlation/candidates/folds parquet）
   - 研究候选池：`CandidateStore` → `data/user_data/research_candidates.json`
   - 策略发布：`MiningCandidateService.publish` → `data/strategies/custom/mined_factor_*.py`

### 调用链

```text
信号回测:
  POST /api/backtest/run → BacktestService.run → _load_panel (Polars scan_enriched + compute_all)
  → to_pandas → _build_signal_matrix → vectorbt Portfolio.from_signals → _persist parquet

策略回测:
  POST /api/backtest/strategy/run → make_worker_task(kind=backtest) → run_worker_task (spawn)
  → _worker_entry → StrategyBacktestService.run → prepare_matrix → load_market_data_matrix_for_backtest
  → simulate_independent_candidates (NumPy 状态机) → 结果回传父进程 → SSE stream

因子回测:
  POST /api/backtest/factor/run → FactorBacktestService.run → _load_factor_panel
  → _evaluate_panel → IC/IR/分层/多空 → FactorResult

参数优化:
  POST /api/backtest/optimize/stream → make_worker_task(kind=optimize) → spawn
  → expand_param_grid → prepare_matrix_optimization (共享 base matrix) → 逐 trial 回测
  → objective_value → SSE optimizer_progress

Walk-Forward:
  POST /api/backtest/walkforward/stream → make_worker_task(kind=walkforward) → spawn
  → generate_folds → 逐折 optimize → aggregate_oos → SSE stream

因子挖掘:
  POST /api/backtest/mining/runs → MiningJobManager.start → MiningRunStore.create
  → spawn worker(kind=mining) → nested_fold_selection → beam_search_factor_combinations
  → evaluate_candidate_gate → artifact parquet → SSE events
  → promote(入候选池) / publish(发布为自定义策略)
```

### 状态机（挖掘运行）

MiningRunStore 管理 9 种运行状态，状态转换在 [mining_jobs.py:53-83](file:///c:/Code/tick-stock-panel/backend/app/services/mining_jobs.py#L53-L83) 定义：

```text
queued → running / cancelling / cancelled / failed / interrupted / skipped_prerequisite
running → cancelling / succeeded / succeeded_with_budget_exhausted / failed / cancelled / interrupted / skipped_prerequisite
cancelling → succeeded / succeeded_with_budget_exhausted / failed / cancelled / interrupted
succeeded / succeeded_with_budget_exhausted / failed / cancelled / interrupted / skipped_prerequisite → 终态（无出边）
```

## 关键数据结构

### API 契约

**StrategyBacktestConfig**（[strategy.py:548](file:///c:/Code/tick-stock-panel/backend/app/backtest/strategy.py#L548-L577)）：
```python
strategy_id: str          # 策略 ID
symbols: list[str]        # 标的列表（None=全市场）
start/end: date           # 回测区间
params: dict              # 策略参数覆盖
overrides: dict           # 运行时覆盖
matching: "open_t+1"      # 撮合模式：close_t / open_t+1 / signal_next_minute
entry_fill/exit_fill: str # 成交价：close_t / open_t+1 / signal_next_minute
commission_pct: 0.0003    # 佣金（双边）
stamp_tax_pct: 0.0005     # 印花税（仅卖出）
slippage_bps: 5.0         # 滑点（双边 bps）
max_positions: 20         # 最大持仓数
max_exposure: 0.95        # 最大暴露
initial_capital: 1000000  # 初始资金
position_sizing: "equal"  # 仓位分配：equal / score_weight
holding_days: 5           # 持有天数（mode=full 时）
asset_type: "stock"       # 资产类型
minute_fill: False        # 分钟级成交
regime_filter: None       # 区制过滤器
```

**MatcherConfig**（[engine.py:48](file:///c:/Code/tick-stock-panel/backend/app/backtest/engine.py#L48-L96)）：
```python
# 撮合参数
matching: Literal["close_t", "open_t+1", "signal_next_minute"]
entry_fill: Literal["close_t", "open_t+1", "signal_next_minute"]
exit_fill: Literal["close_t", "open_t+1", "signal_next_minute"]
fees_pct: float = 0.0003        # 向后兼容
commission_pct: float = 0.0003  # 佣金
stamp_tax_pct: float = 0.0005   # 印花税
slippage_bps: float = 5.0       # 滑点
stop_loss: float | None         # 止损（如 -0.07）
take_profit: float | None       # 止盈
trailing_stop: float | None     # 移动止损
max_hold_days: int | None       # 最大持仓天数
max_positions: int | None       # 最大持仓数
max_exposure_pct: float | None  # 最大暴露比例
position_sizing: str            # equal / score_weight
# 成本计算
buy_cost_pct = commission + slippage            # 买入成本
sell_cost_pct = commission + stamp + slippage   # 卖出成本
```

**MiningStartRequest**（[api/mining.py:52](file:///c:/Code/tick-stock-panel/backend/app/api/mining.py#L52-L123)）：
```python
factor_names: list[str]       # 因子 ID 列表（≤48）
strategy_ids: list[str]       # 已有策略 ID 列表（≤8）
asset_type: str               # "stock" / "etf"
budget_profile: str           # "exploratory" / "balanced" / "strict"
correlation_threshold: 0.75   # 相关性剪枝阈值
max_combination_factors: 4    # 单组合最大因子数
beam_width: 12                # 束搜索宽度
max_finalists: int            # 最终候选上限
force: bool                   # 强制重新运行
```

**MiningCandidateGate**（[mining.py:198](file:///c:/Code/tick-stock-panel/backend/app/backtest/mining.py#L198-L233)）：
```python
GATE_MIN_VALID_FOLDS = 2
GATE_MIN_POSITIVE_FOLD_RATIO = 2/3
GATE_MIN_OOS_SHARPE = 0.5
GATE_MAX_DRAWDOWN = -0.25
GATE_MIN_TRADES = 60
```

### 存储结构

**挖掘运行目录**（[mining_jobs.py:131](file:///c:/Code/tick-stock-panel/backend/app/services/mining_jobs.py#L131-L132)）：
```
data/research/mining/runs/{run_id}/
├── manifest.json    # 运行元数据（schema_version/status/request/fingerprint/artifacts）
├── summary.json     # 汇总指标（由 worker 写入）
├── events.jsonl     # 事件日志（最多 256 条，每条 ≤16KB）
├── factors.parquet  # 因子评估结果
├── correlation.parquet  # 因子相关性矩阵
├── candidates.parquet   # 候选方案（含 gate 评估结果）
└── folds.parquet        # 嵌套交叉验证折叠明细
```

**研究候选池**（[candidates.py:135](file:///c:/Code/tick-stock-panel/backend/app/backtest/candidates.py#L135-L180)）：
```
data/user_data/research_candidates.json
# 最多 200 条，每条 payload ≤32KB
# 含 origin_run_id/candidate_signature/kind/name/source_id/config/metrics/status
```

**矩阵磁盘缓存**（[matrix.py:379](file:///c:/Code/tick-stock-panel/backend/app/backtest/matrix.py#L379-L387)）：
```
data/.backtest_matrix_cache/{asset_type}/{generation}/
# MatrixCacheProfile: field_columns/warmup_bars/forward_bars/max_disk_bytes/generation
```

### 内存结构

**MatrixComputeCache**（[matrix.py:111](file:///c:/Code/tick-stock-panel/backend/app/backtest/matrix.py#L111-L343)）：
- LRU OrderedDict + 字节限界（max_bytes=512MB, max_item_bytes=256MB）
- single-flight：`_InFlight` 防并发重复计算
- Counter-based 操作统计（calls/hits/misses/evictions）
- 线程级 `_ACTIVE_MATRIX_CACHE` contextvar 隔离

**PanelCache**（[engine.py:188](file:///c:/Code/tick-stock-panel/backend/app/backtest/engine.py#L188-L312)）：
- LRU(max_size=2) + TTL(180s) + single-flight（`_InFlight`）
- 实例锁保护 OrderedDict

**`_running_jobs`**（[api/backtest.py:440](file:///c:/Code/tick-stock-panel/backend/app/api/backtest.py#L440-L456)）：
- 模块级 dict：`{job_key: _BacktestJob}`，`_JOB_TTL=300` 秒
- `_cleanup_stale_jobs` 定期清理过期任务
- `_make_job_key`：MD5(request_json) 去重

**SSE 事件流**（[api/backtest.py:490](file:///c:/Code/tick-stock-panel/backend/app/api/backtest.py#L490-L686)）：
- sse_starlette StreamingResponse
- 事件类型：progress / done / error / optimizer_progress
- `Last-Event-ID` 重连支持
- 5 分钟 TTL 后自动清理

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **自定义策略**：在 `data/strategies/custom/` 下创建 `{strategy_id}.py`，实现 `matrix_native` 策略接口，`StrategyEngine` 自动加载
- **挖掘候选发布**：挖掘工作台 → promote（入候选池）→ publish（自动生成 `data/strategies/custom/mined_factor_*.py`）
- **因子注册**：`app/factors/registry.py` 的 `factor_columns_view()` 注册新因子，挖掘流程自动发现

### L2 扩展（插槽/路由/注册替换）

- **挖掘预算配置**：`preferences.get_mining_schedule()` 配置定时挖掘的 profile/weekday/开关
- **候选方案**：`ResearchCandidatesDialog` 支持跨页面载入复测，`pendingLoad` 机制
- **通知格式化**：见 `docs/secondary-development.md`，`NotificationFormatter` 插槽

### L3 修改（直接改源码）

- **撮合逻辑**：修改 `engine.py:simulate`（NumPy 状态机循环）或 `simulate_independent_candidates`（矩阵撮合），注意 `close_t`/`open_t+1`/`signal_next_minute` 三种成交口径的一致性
- **成本模型**：修改 `MatcherConfig` 的 `buy_cost_pct`/`sell_cost_pct` 计算（[engine.py:87-91](file:///c:/Code/tick-stock-panel/backend/app/backtest/engine.py#L87-L91)）
- **挖掘门控**：调整 `mining.py:27-31` 的 `GATE_*` 常量
- **挖掘预算**：调整 `mining.py:44` 的 `MiningBudget` 各 profile 的 `max_inner_folds`/`max_outer_folds`/`max_beam_widened`/`max_real_trials`
- **重型任务限制**：调整 `heavy_job_limiter.py:27` 的 `capacity` 或 `_WEIGHTS`

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 矩阵磁盘缓存 `.backtest_matrix_cache` | `MatrixCacheProfile.generation` 变更时自动重建；手动删除目录 | 所有 matrix_native 回测/优化/挖掘首次运行需重建 |
| MatrixComputeCache 内存 | 进程内 job-scoped，随任务结束自动释放 | 单次回测/优化内的矩阵计算 |
| PanelCache（LRU+TTL） | 180 秒 TTL 自动过期；`_OnFinalize` 清空缓存 | 跨回测请求的 panel 复用 |
| `_running_jobs` 任务表 | `_JOB_TTL=300` 秒自动清理 | API 层 SSE 重连能力 |
| MiningRunStore 持久化 | 写入 `_atomic_write_json`/`_atomic_write_text`（先写临时文件再 os.replace） | 挖掘运行状态持久化 |
| 策略缓存 `strategy_cache` | 发布候选时调用 `_strategy_cache_invalidator` | 新策略立即可见 |
| 监控状态 | 发布候选时调用 `monitor_state_invalidator` | 监控模块立即感知新策略 |
| 前端 TanStack Query | 按 `queryKeys.ts` 前缀精确失效 | 回测结果列表/挖掘运行列表 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/backtest/test_*.py`（26 个文件） | 撮合逻辑、成本模型、矩阵缓存 LRU、网格展开、NW t/BH q 计算、gate 评估 |
| 集成测试 | `backend/tests/backtest/test_*_api.py`、`backend/tests/backtest/test_*_e2e.py` | SSE 流式端点、worker 进程隔离、候选 promote/publish、复合策略 E2E |
| 服务测试 | `backend/tests/test_mining_*.py`（9 个文件） | MiningJobManager 线程编排、MiningRunStore 状态机、schedule 指纹、进程锁 |
| 前端测试 | 待确认 | 前端组件测试 |

## 依赖关系

### 依赖的其他功能

- **数据管道**（Pipeline/KlineRepository）：回测所需的 enriched 数据由 `indicators.pipeline.compute_all` 产出，`EnrichedGenerationUnavailableError` 时回测拒绝执行
- **策略引擎**（StrategyEngine）：策略回测/优化/walk-forward 依赖策略注册表中的策略定义
- **因子注册表**（Factors Registry）：因子回测与挖掘依赖 `app/factors/registry.py` 注册的因子
- **财务数据**（Financial Sync）：财务因子回测依赖 `financial_sync` 同步的财务数据
- **区制数据**（Regime Builder）：挖掘的 `require_regime` 选项依赖 `regime_path` 的区制历史
- **定时调度**（APScheduler）：`run_weekly_mining` 通过 `daily_pipeline.start_scheduler` 注册的定时任务触发
- **Instrument 同步**（Instrument Sync）：矩阵构建依赖 `get_instruments_asset` 返回的标的列表

### 被依赖的功能

- **监控模块**：监控模块可引用回测发布的策略（`mined_factor_*`）进行实时监控
- **选股模块**：选股模块可引用回测结果进行因子评估
- **研究模块**：`ResearchCandidatesDialog` 跨页面载入复测
- **AI 研究**：AI 研究模块可引用回测结果作为分析素材

## 常见问题与注意事项

1. **撮合口径一致性**：`close_t`（信号当日收盘价撮合）、`open_t+1`（信号次日开盘价撮合，信号右移 1 天 masked by same_prev_symbol）、`signal_next_minute`（分钟 K 的下一分钟触发）。修改撮合逻辑时需确保三种口径的一致性，见 [engine.py:672+](file:///c:/Code/tick-stock-panel/backend/app/backtest/engine.py#L672-L808)。

2. **Enriched generation 防并发**：enriched 数据世代切换期间回测调用会抛出 `EnrichedGenerationUnavailableError`，前端应提示"指标数据正在发布更新，请稍后重试"。worker 入口在 `_error_message` 中透出此信息（[worker.py:169](file:///c:/Code/tick-stock-panel/backend/app/backtest/worker.py#L169-L176)）。

3. **挖掘签名去重**：`compute_run_signature` 使用 BLAKE2b 哈希 `request + data_fingerprint`，相同签名的成功运行不会重复执行（[mining_jobs.py:105](file:///c:/Code/tick-stock-panel/backend/app/services/mining_jobs.py#L105-L120)）。

4. **挖掘进程锁**：`MiningProcessLock` 使用文件锁 `.mining_process.lock` 防止多进程并发挖掘，Windows 使用 `msvcrt.locking`，POSIX 使用 `fcntl.flock`（[mining_process_lock.py:45](file:///c:/Code/tick-stock-panel/backend/app/services/mining_process_lock.py#L45-L65)）。

5. **重型任务限制器**：`shared_heavy_job_limiter` 容量为 2，normal 回测占用 1 槽，mining 占用 2 槽，超出时等待或超时失败（[heavy_job_limiter.py:119](file:///c:/Code/tick-stock-panel/backend/app/services/heavy_job_limiter.py#L119-L121)）。

6. **子进程退出方式**：worker 子进程使用 `os._exit(0)` 跳过 Python 解释器 teardown（[worker.py:282](file:///c:/Code/tick-stock-panel/backend/app/backtest/worker.py#L282)），避免 multiprocessing 的 atexit 竞态。

7. **数据契约红线**：enriched OHLC 为前复权（`raw_*` 为不复权）、比例/百分数口径转换（实时源 `change_pct` 小数制 vs enriched `turnover_rate` 百分数）、股票/ETF/指数分开存储与路由、财务数据按公告日 PIT。

8. **候选方案 JSON 文件**：`CandidateStore` 使用 `_atomic_write_json` 写入 `research_candidates.json`，同时维护 `MAX_CANDIDATES=200` 和 `MAX_PAYLOAD_BYTES=32KB` 限制，超限时通过 `_evict_oldest` 淘汰最旧条目。