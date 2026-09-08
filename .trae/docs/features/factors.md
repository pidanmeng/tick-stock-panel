---
title: 因子 Factors — 功能文档
description: 因子功能完整参考，覆盖因子注册表、DSL 公式编辑器、批量检验、因子挖掘与自定义/复合因子生命周期管理。
---

# 因子 Factors — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

**功能名**：因子（Factors）
**建议文件名**：`features/factors.md`
**检索范围**：`frontend/src/pages/Factors.tsx`、`frontend/src/pages/factors/`、`frontend/src/pages/backtest/{FactorDiscovery,MiningWorkbench}.tsx`、`frontend/src/lib/{api,queryKeys}.ts`、`backend/app/api/{factors,mining,backtest,screener}.py`、`backend/app/factors/`、`backend/app/services/{mining_*,auto_mining}.py`、`backend/app/backtest/factor.py`、`backend/app/strategy/{scoring,engine}.py`、`backend/tests/test_factor_*`、`backend/tests/test_mining_*`、`backend/tests/test_auto_mining.py`

## 功能概述

因子功能为 A 股量化工作台提供"因子即资产"的研究闭环：内置/虚拟/复合/自定义四类因子经统一注册表管理，通过 DSL 公式编辑器编写自定义因子，经校验与 IC 试算后进入生命周期（draft→active→watch→retired）；批量检验页对全量因子做 IC/IR/Newey-West t/BH-q 统计筛选；挖掘工作台在嵌套样本外框架下做逐折训练与束搜索组合，候选因子可提升（promote）入库或发布（publish）为可交易策略。全链路共享 `app/factors/registry.py` 注册表与 `FactorBacktestService` 补算路径，禁止第二套因子计算逻辑。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 入口 | `backend/app/api/factors.py` | 因子注册表 API：列表/校验/试算/自定义 CRUD/复合因子/状态与分组管理 |
| 入口 | `backend/app/api/mining.py` | 挖掘 API：可用性/启动/事件流/结果/取消/自动挖掘/候选提升与发布/调度配置 |
| 入口 | `backend/app/api/backtest.py` | 因子批量检验 `POST /factor/batch`、单因子回测 `POST /factor/run`、因子列 `GET /factor/columns`（`backtest.py:129-243`） |
| 注册表 | `backend/app/factors/registry.py` | 因子元数据单一权威：目录定义、注册/查询/注销、依赖展开、评分预热视图 |
| DSL | `backend/app/factors/dsl.py` | 因子公式 DSL 编译器：tokenizer→解析→语义检查→依赖/预热推导→Polars Expr |
| 存储 | `backend/app/factors/store.py` | 自定义/复合因子 JSON 持久化与启动加载（`data/user_data/custom_factors/*.json`） |
| 扩展 | `backend/app/factors/ext_factors.py` | 扩展表数值字段→base 因子注册、帧列注入、缓存失效 |
| 服务 | `backend/app/backtest/factor.py` | FactorBacktestService：IC/IR 计算、批量检验、分层/多空回测、缺失因子补算 |
| 服务 | `backend/app/strategy/scoring.py` | 评分字段解析、虚拟因子表达式分发、composite 值计算 |
| 服务 | `backend/app/strategy/engine.py` | 策略引擎：评分物化、`materialize_scoring_columns` 调用 |
| 服务 | `backend/app/services/mining_manager.py` | 挖掘任务线程编排：签名去重、容量限制、取消与中断恢复 |
| 服务 | `backend/app/services/mining_jobs.py` | 挖掘运行持久化：manifest/事件日志/签名/状态机 |
| 服务 | `backend/app/services/mining_candidates.py` | 挖掘候选提升（promote）与发布（publish）为策略 |
| 服务 | `backend/app/services/mining_schedule.py` | 周度定时挖掘编排与数据指纹 |
| 服务 | `backend/app/services/auto_mining.py` | 自动挖掘 L1 全量因子统计筛选 → 达标池 |
| 装配 | `backend/app/main.py` | 启动期加载自定义因子进注册表（`main.py:109-115`）、初始化 MiningJobManager（`main.py:117-123`）、挂载 router（`main.py:475-476`） |
| 测试 | `backend/tests/test_factor_registry.py` | 注册表快照/依赖展开/预热窗口 |
| 测试 | `backend/tests/test_factor_dsl.py` | DSL 编译正反例、窗口纪律、错误码 |
| 测试 | `backend/tests/test_factor_store.py` | 自定义因子持久化/多轮加载/循环引用 |
| 测试 | `backend/tests/test_factor_api.py` | 因子 API：校验/试算/CRUD/状态机 |
| 测试 | `backend/tests/test_factor_library_v2.py` | 因子库 v2 列表/详情 |
| 测试 | `backend/tests/test_mining_api.py` | 挖掘 API 全链路 |
| 测试 | `backend/tests/test_mining_manager.py` | 任务管理/签名去重/取消 |
| 测试 | `backend/tests/test_mining_jobs.py` | 运行存储/事件/状态转移 |
| 测试 | `backend/tests/test_mining_candidates.py` | 候选提升/发布门槛 |
| 测试 | `backend/tests/test_mining_schedule.py` | 周度调度门控 |
| 测试 | `backend/tests/test_auto_mining.py` | L1 自动筛选 |
| 测试 | `backend/tests/test_ext_factors.py` | 扩展表因子注册/列注入/缓存失效 |
| 测试 | `backend/tests/test_strategy_scoring.py` | 评分字段/虚拟因子/依赖 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Factors.tsx` | 因子功能主入口：5 个 Tab（inspect 检验 / library 因子库 / editor 编辑器 / composite 组合 / mining 挖掘） |
| 组件 | `frontend/src/pages/factors/FactorLibrary.tsx` | 因子库：目录浏览/搜索过滤/详情/状态与删除管理 |
| 组件 | `frontend/src/pages/factors/FactorEditor.tsx` | DSL 公式编辑器：算子插入/校验/IC 试算/保存自定义因子 |
| 组件 | `frontend/src/pages/factors/FactorComposite.tsx` | 复合因子构建：选成员/权重/等权或手动 |
| 组件 | `frontend/src/pages/factors/GenerateFactorStrategyDialog.tsx` | 由因子生成单因子排名策略代码 |
| 组件 | `frontend/src/pages/backtest/FactorDiscovery.tsx` | 批量检验 + 单因子检验页（预设场景/排序表/判读） |
| 组件 | `frontend/src/pages/backtest/MiningWorkbench.tsx` | 挖掘工作台：任务启动/进度/结果表格/候选提升发布/自动挖掘入口 |
| 组件 | `frontend/src/pages/backtest/AddFactorSignalDialog.tsx` | 把检验达标因子加入监控信号 |
| 组件 | `frontend/src/pages/backtest/AutoMiningDialog.tsx` | 自动挖掘配置弹窗（L1 筛选+挖掘） |
| 图表 | `frontend/src/pages/backtest/charts/` | 挖掘可视化：RegimeComparisonChart / MiningOosChart / FactorCorrelationHeatmap |
| API | `frontend/src/lib/api.ts` | 因子/挖掘 API 客户端（`factorLibrary/factorValidate/factorTrial/factorCustom*/factorComposite*/mining*`） |
| 状态 | `frontend/src/lib/queryKeys.ts` | TanStack Query 键定义与 SSE 失效前缀 |
| 任务 | `frontend/src/lib/miningTask.ts` | 挖掘任务 SSE 跟踪 hook（`useMiningTask/startMining/cancelMining`） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 数据 | `data/user_data/custom_factors/*.json` | 自定义/复合因子定义持久化 |
| 数据 | `data/research/mining/runs/*` | 挖掘运行 manifest/事件/结果 artifact |
| 文档 | `docs/secondary-development.md` | 二开扩展契约（因子相关 L1/L2/L3 扩展边界） |

## 业务逻辑

### 核心流程

```text
[因子库浏览] → [自定义因子: DSL公式 → /validate校验 → /trial IC试算 → /custom保存(draft)] → [状态迁移 active]
                                                        → [复合因子: /composite 组合成员]
[批量检验 /factor/batch] → IC/IR/NW-t/BH-q 统计 → 判读 valid/edge/invalid/error → [加入信号 | 生成策略]
[挖掘 /mining/runs] → L1自动筛选(可选) → 逐折训练+嵌套样本外 → 候选 → promote入库 | publish为策略
```

### 数据流

1. **输入来源**：
   - 用户在前端编辑器输入 DSL 公式（`FactorEditor.tsx`）或选择因子成员构建复合因子（`FactorComposite.tsx`）；
   - 批量检验与挖掘复用 enriched parquet 面板（`engine.load_panel`），无独立数据通路。
2. **处理过程**：
   - 公式经 `compile_formula()` 编译为 Polars Expr（`dsl.py:558`），依赖/预热由编译期推导（`dsl.py:589-607`）；
   - 试算与检验复用 `FactorBacktestService` 补算路径：`_compute_missing_factors()` 物化虚拟/缺失列（`factor.py:644`），`materialize_scoring_columns` 注入评分列；
   - 批量检验在同一 Panel 上依次评估多因子并共享下期收益（`factor.py:208-243`）；统计口径含 NW HAC t（lag=1）与 BH-FDR q（`factor.py:141-146`）；
   - 挖掘按预算档位（exploratory/balanced/strict）走相关性剪枝→束搜索→嵌套样本外验证→达标门槛（`evaluate_candidate_gate`）。
3. **输出去向**：
   - 自定义因子写入 `data/user_data/custom_factors/{id}.json`（`store.py:47-50`）；
   - 检验结果即时返回前端排序表，达标因子可加入监控信号或生成策略；
   - 挖掘结果落盘 `data/research/mining/runs/`，候选 promote 进 `CandidateStore`、publish 生成 `mined_factor_*` 策略。

### 调用链

```text
前端 Factors.tsx → api.ts(factorLibrary/factorValidate/factorTrial/factorCustomCreate/factorCompositeCreate)
  → backend/app/api/factors.py:59-443 → app/factors/dsl.py:compile_formula → app/factors/registry.py:get_factor
  → app/factors/store.py:to_spec/register_definition → app/factors/registry.py:register_factor

批量检验: api/backtest.py:200 factor_batch → app/backtest/factor.py:208 run_batch
  → app/backtest/factor.py:644 _compute_missing_factors → app/strategy/scoring.py:materialize_scoring_columns
  → app/factors/registry.py:factor_columns_view → stats_v2 (NW/BH) → FactorBatchItem

挖掘: api/mining.py:202 start_run → app/services/mining_manager.py:57 start
  → app/services/mining_jobs.py:134 create → app/backtest/mining.py (束搜索/嵌套样本外)
  → app/services/mining_candidates.py:83 promote / :112 publish → StrategyEngine → strategy_cache

启动加载: app/main.py:109 load_into_registry → app/factors/store.py:165 → register_definition
```

### 状态机

自定义因子生命周期（`store.py:23` STATUSES，`api/factors.py:404` 状态迁移接口）：

```text
draft → active → watch → retired
  │        ↑          │
  └────────┴──────────┘   (任一状态可回退/前进，无跨级限制)
```

- 公式修改后强制回到 `draft`（`api/factors.py:320-355` 更新逻辑），重新试算达标后再激活；
- `active` 状态的因子 `stability="stable"`，其余为 `experimental`（`store.py:99`）。

挖掘运行状态机（`mining_jobs.py:53-83` `_ALLOWED_TRANSITIONS`）：

```text
queued → running → succeeded / succeeded_with_budget_exhausted / failed / cancelled / interrupted / skipped_prerequisite
   └──→ cancelling → (终态之一)
```

## 关键数据结构

### API 契约

**因子注册表（`api/factors.py`）**：

| 端点 | 方法 | 请求 | 响应要点 |
|------|------|------|----------|
| `/api/factors` | GET | `asset_type` 可选 | `{factors: FactorSpec[]}` |
| `/api/factors/validate` | POST | `{formula}` | `{ok, errors[], dependencies[], referenced_factors[], warmup_bars, cross_sectional}` |
| `/api/factors/trial` | POST | `{formula, asset_type, days(20-120)}` | `{ok, n_dates, null_ratio, ic_mean, ic_std, ir, ic_win_rate, t_newey_west, ic_series[]}` |
| `/api/factors/custom` | POST | `{id?, label, group, formula, description, direction}` | `{ok, id, version}` |
| `/api/factors/composite` | POST | `{id?, label, group, members: {id: weight}(2-8), ...}` | `{ok, id, version}` |
| `/api/factors/custom/{id}/update` | POST | 同上 | 公式变更→回 draft，版本自增 |
| `/api/factors/custom/{id}` | DELETE | `force` 可选 | 有引用时需 force |
| `/api/factors/custom/{id}/status` | POST | `{status: draft\|active\|watch\|retired}` | — |
| `/api/factors/custom/{id}/group` | POST | `{group}` | 分组重命名 |

**批量检验（`api/backtest.py:187-243`）**：

| 端点 | 方法 | 请求 | 响应要点 |
|------|------|------|----------|
| `/api/backtest/factor/columns` | GET | — | `{columns: FactorColumn[]}`（注册表兼容视图） |
| `/api/backtest/factor/run` | POST | `FactorBacktestRequest` | `FactorResult`（IC/分层/多空/regime） |
| `/api/backtest/factor/batch` | POST | `FactorBatchRequest`（factor_names 上限由前端预设） | `FactorBatchResult`，每项含 `t_newey_west/q_value`（`factor.py:141-146`） |

**挖掘（`api/mining.py`）**：

| 端点 | 方法 | 请求 | 响应要点 |
|------|------|------|----------|
| `/api/backtest/mining/availability` | GET | — | 按预算档位返回可运行交易日 |
| `/api/backtest/mining/runs` | POST | `MiningStartRequest`（factor_names≤48、strategy_ids、symbols、budget_profile、cost 参数） | `{run_id, status: queued}` |
| `/api/backtest/mining/runs/{id}/events` | GET | — | SSE 事件流 |
| `/api/backtest/mining/runs/{id}/result` | GET | — | `MiningResult`（factors/candidates/folds/regimes/telemetry） |
| `/api/backtest/mining/runs/{id}/cancel` | POST | — | 取消（终态幂等） |
| `/api/backtest/mining/auto` | POST | `MiningAutoStartRequest` | 自动筛选达标池 → 启动挖掘 |
| `/api/backtest/mining/runs/{id}/candidates/{sig}/promote` | POST | — | 候选入库（CandidateStore, status=pending） |
| `/api/backtest/mining/runs/{id}/candidates/{sig}/publish` | POST | — | 生成 `mined_factor_*` 策略，含达标门槛校验 |
| `/api/backtest/mining/config` | GET/PATCH | `MiningSchedulePatch` | 周度调度配置（preferences 持久化） |

### 存储结构

**自定义因子 JSON（`data/user_data/custom_factors/{id}.json`）**：

```json
{
  "id": "uf_xxx",           // ^uf_[a-z0-9_]{1,40}$ (composite 为 ^cf_)
  "label": "名称",
  "group": "自定义",
  "kind": "custom",         // custom | composite
  "version": 1,
  "status": "draft",        // draft|active|watch|retired
  "formula": "ts_mean(close,5)",      // custom 专用
  "members": {"mom_5d": 0.5},         // composite 专用 (2~8 成员)
  "direction": "none",      // high|low|none
  "description": ""
}
```

**挖掘运行（`data/research/mining/runs/{run_id}/`）**：`manifest.json`（请求/状态/签名）、`events.jsonl`（有界 256 条）、summary、artifacts（factors/correlation/candidates/folds parquet）。

### 内存结构

- 因子注册表 `_REGISTRY: dict[str, FactorSpec]`（`registry.py:303`），内置目录 `_CATALOG` 顺序即历史 `FACTOR_COLUMNS` 顺序，前 48 个供挖掘默认池（`registry.py:77` 注释）；
- `FactorSpec`（`registry.py:30-52`）：id/label/group/formula_text/kind/version/dependencies/direction/unit/warmup_bars/pit/asset_types/stability/components；
- DSL 编译缓存 `compile_formula_cached` LRU（`dsl.py:743-749`）；
- 扩展表帧缓存 `_frame_cache`（`ext_factors.py:44`）与注册同步状态 `_sync_state`（`ext_factors.py:48`）；
- Screener 历史窗口缓存 `_history_cache`（`screener.py:23`，TTL 120s）。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- 新增扩展表数值字段：`data/ext_data/{config_id}/` 下的数值字段自动注册为 `ext_` 前缀 base 因子（`ext_factors.py:100-127`），出现在因子库列表与批量检验候选池；
- 自定义因子/复合因子：通过编辑器或 `/api/factors/custom`、`/api/factors/composite` 创建，无需改代码；
- 挖掘预算档位门槛：`auto_mining.py:50-54` `SCREEN_GATES` 可按档调整筛选门槛。

### L2 扩展（插槽/路由/注册替换）

- 因子注册表 `register_factor()`（`registry.py:306`）是运行时注册入口，重复 id 且版本未升时 fail-closed 拒绝；`unregister_factor()` 禁止注销内置目录因子（`registry.py:322-326`）；
- 评分表达式分发仍保留在 `scoring.py`（`scoring_value_expr`，`scoring.py:99`），注册表仅收口元数据 —— 新增虚拟因子需同时改注册表依赖声明与 scoring 表达式分发两处；
- 扩展表 string 字段仅走信号条件通道，不注册为因子（`ext_factors.py:84-97`）。

### L3 修改（直接改源码）

- 修改 DSL 算子：同时更新 `dsl.py:43-69` `OPERATORS`（参数签名/常量参数）、`TS_OPERATORS/CROSS_OPERATORS` 归属、`_rolling_apply/_compile_call` 代码生成与错误码表；
- 新增内置因子：在 `registry.py:_CATALOG` 追加 `_base/_virtual/_financial` 条目，注意目录顺序影响 `FACTOR_COLUMNS[:48]` 挖掘默认池；
- 修改挖掘引擎：`backend/app/backtest/mining.py`（束搜索/嵌套样本外/达标门槛），需同步 `FACTOR_METHODOLOGY_VERSION` 与 `MINING_ALGORITHM_VERSION`（`mining_schedule.py:29`）以触发数据指纹变化。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件缓存 | 自定义因子写入 `custom_factors/*.json`（`store.py:47`），启动 `load_into_registry` 重载（`store.py:165`） | 注册表动态条目 |
| 内存缓存 | `register_factor`/`unregister_factor` 直接改 `_REGISTRY`；扩展表变更走 `invalidate_ext_caches`（`ext_factors.py:329`）清 `_frame_cache`+`_sync_state`+策略结果缓存 | 因子列表/批量检验/AI 提示词 |
| 数据 generation | enriched 数据变更由 repo generation 版本驱动，`FactorBacktestService` 断言 `_assert_data_generation`（`factor.py:188,242`） | 检验/挖掘结果 |
| SSE/前端 | mining 运行经 SSE 推送事件，前端按 `queryKeys.ts` 前缀（`miningRuns/miningRun/miningResult`）精确失效 | 挖掘工作台 |
| 策略缓存 | publish 策略后由 `MiningCandidateService` 调 `strategy_cache_invalidator`（`mining_candidates.py:76-80`） | 策略列表/详情 |

## 依赖关系

### 依赖的其他功能

- **回测引擎**（`app/backtest/engine.py`）：因子检验/挖掘共享 `BacktestEngine.load_panel` 面板；
- **数据管道**（enriched parquet）：因子计算依赖盘后管道产出的窄表数据；
- **财务数据**（fundamentals）：财务因子（`pb_latest/roe_latest` 等）依赖本地财务同步，缺失时 fail-closed 报错（`factor.py:181-185`）；
- **扩展数据**（ext_data）：扩展因子依赖扩展表配置与数据；
- **策略引擎**（`strategy/scoring.py`）：因子物化经 `materialize_scoring_columns` 复用评分路径。

### 被依赖的功能

- **监控**：检验达标因子可经 `AddFactorSignalDialog` 加入监控信号；
- **策略生成**：因子可生成 `FactorRankResearchMatrixStrategy` 单因子排名策略（`GenerateFactorStrategyDialog.tsx`）或由挖掘候选 publish 为 `mined_factor_*` 策略；
- **AI 研究**：注册表因子清单进入 AI 提示词（`ext_factors.py` 注释提及）。

## 常见问题与注意事项

- **窗口纪律**：`ts_*` 算子只允许向后看（负 shift 编译期 E005 拒绝）；截面算子（rank/zscore/winsorize）嵌在时序窗口内 E009 拒绝 —— 修改 DSL 时不得放宽该约束，否则 Polars 嵌套窗口静默全 null；
- **试算空输出**：保存自定义因子前有 `_trial_nonempty` 门禁（`api/factors.py:232-254`），公式在最近 40 个交易日全为空时拒绝保存（fail-closed）；
- **版本与引用**：删除被引用的因子（策略/复合因子）需 `force=true`（`api/factors.py:357-398` `_find_references`）；composite 循环引用在 `store.py:125-134` 编译期拒绝；
- **口径红线**：IC 为 Rank IC（`api/factors.py:136`）；t 为 Newey-West HAC lag=1（`stats_v2.newey_west_t`），样本 <5 不给 t（fail-closed）；q 值缺失按"通过"处理仅限探索档（`auto_mining.py:12`）；
- **挖掘请求维度**：重复请求（同签名+同数据指纹）返回已有运行（`mining_manager.py:70-81`），如需强制重跑需 `force=true`；
- **性能**：批量检验默认整市场面板共享下期收益列（`factor.py:240-247`）；扩展表多日历史帧禁止注入 snapshot 模式（未来函数风险，`ext_factors.py:276-278`）；
- **前 48 因子约束**：挖掘默认因子池取 `FACTOR_COLUMNS[:48]`（`mining_schedule.py:60`），`_CATALOG` 顺序变更会改变默认挖掘池内容，属于影响面较大的改动。
