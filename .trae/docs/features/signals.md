---
title: 信号库 (Signals)
description: 信号库 — 内置预计算信号与自定义条件信号，供策略/回测/监控统一使用。
---

# 信号库 (Signals) — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

信号库是 TSP 的**统一买卖触发器信号系统**，提供两类信号：

- **内置信号（built-in）**：20 个系统预计算的原子信号（`signal_*` 列），在指标流水线（pipeline）中与指标一并计算，只读。
- **自定义信号（custom）**：用户通过「字段 + 运算符 + 值」组合条件定义的布尔信号（`csg_*` 列），由表达式引擎编译为 Polars 布尔表达式，注入 enriched 数据帧。
- **盘中信号（intraday）**：内置 4 个分时穿越信号 + 用户自定义的 `timeframe="intraday"` 信号（`csgi_*` 列），基于分钟 K 特征帧评估。

信号被策略选股、回测、监控规则统一消费：选股页弹窗和回测页设置中的「入场触发器/出场触发器」直接引用信号列，监控规则支持将信号作为触发条件，盘中信号实时注入监控引擎。

本次检索范围：`frontend/src/pages/Signals.tsx`、`frontend/src/components/signals/`、`frontend/src/lib/signals.ts`、`frontend/src/lib/api.ts`、`frontend/src/lib/queryKeys.ts`、`frontend/src/router.tsx`、`frontend/src/components/screener/SignalPicker.tsx`、`backend/app/api/signals.py`、`backend/app/strategy/custom_signals.py`、`backend/app/strategy/custom_signals_ai.py`、`backend/app/strategy/intraday_signals.py`、`backend/app/strategy/intraday_features.py`、`backend/app/indicators/pipeline.py`（`compute_signals`/`compute_enriched_today`/缓存）、`backend/app/backtest/strategy.py`（`_build_signal_mask`）、`backend/app/strategy/engine.py`（`_inject_intraday_signal_columns`）、`backend/app/strategy/monitor.py`（`intraday_signal_symbols`）、`backend/app/services/quote_service.py`（`_inject_intraday_signals`）、`backend/app/backtest/engine.py`、`backend/app/services/screener.py`、`backend/app/strategy/scoring.py`、`backend/app/factors/ext_factors.py`、`backend/tests/test_custom_signals_*.py`、`backend/tests/test_intraday_signals.py`、`backend/tests/test_intraday_monitor_signals.py`、`backend/tests/test_strategy_detail_signals.py`。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `backend/app/api/signals.py` | 自定义信号 CRUD + AI 生成 + 选项查询 + 盘中回放端点 |
| 核心模块 | `backend/app/strategy/custom_signals.py` | 信号校验、编译为 Polars 表达式、持久化/加载/删除、盘中信号表达式编译、因子列物化 |
| AI 生成 | `backend/app/strategy/custom_signals_ai.py` | 构建 AI 提示词、解析 LLM 返回的 JSON、校验字段白名单 |
| 盘中信号评估器 | `backend/app/strategy/intraday_signals.py` | `IntradaySignalEvaluator` 类：按分钟 K 评估边沿触发信号，注入 enriched 快照 |
| 分钟特征帧 | `backend/app/strategy/intraday_features.py` | `build_feature_frame()`：将分钟 K 编译为数值特征序列，供盘中信号条件求值 |
| 指标流水线 | `backend/app/indicators/pipeline.py` | `compute_signals()`: 计算 20 个内置信号 + 注入自定义信号列；`compute_enriched_today()`: 盘中日级路径注入自定义信号；模块级缓存管理 |
| 回测策略 | `backend/app/backtest/strategy.py` | `_build_signal_mask()`: 向量化合并多个信号列（OR），支持 `signal_`/`csg_` 前缀 |
| 回测引擎 | `backend/app/backtest/engine.py` | 调用 `compute_signals()` 准备回测数据 |
| 筛选服务 | `backend/app/services/screener.py` | 调用 `compute_signals()` 准备选股数据 |
| 策略引擎 | `backend/app/strategy/engine.py` | `_inject_intraday_signal_columns()`: 向分钟策略执行帧注入盘中信号列 |
| 监控引擎 | `backend/app/strategy/monitor.py` | `intraday_signal_symbols()`: 返回需盘中信号评估的标的集合 |
| 行情服务 | `backend/app/services/quote_service.py` | `_inject_intraday_signals()`: 实时行情轮中评估盘中信号并注入 enriched |
| 扩展数据 | `backend/app/factors/ext_factors.py` | `attach_ext_columns()`: 将扩展表数值/字符串列 join 到 enriched 帧供信号条件引用 |
| 评分物化 | `backend/app/strategy/scoring.py` | `materialize_scoring_columns()`: 被自定义信号复用，补算注册表因子列 |
| 策略缓存 | `backend/app/services/strategy_cache.py` | `clear_cache()`: 信号定义变更时清策略磁盘缓存 |
| 数据仓库 | `backend/app/tickflow/repository.py` | 多个 enriched 加载路径中调用 `compute_signals()` |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 信号库页面 | `frontend/src/pages/Signals.tsx` | 路由 `/signals`，分「自定义信号」和「内置信号」两栏展示 |
| 自定义信号对话框 | `frontend/src/components/signals/CustomSignalDialog.tsx` | 新建/编辑自定义信号的弹窗，含字段选择器、AI 生成条件面板 |
| 信号快捷操作栏 | `frontend/src/components/signals/SignalTriggerActions.tsx` | 策略/回测设置页中的快捷按钮（从因子创建、新建、跳转信号库） |
| 信号选择器 | `frontend/src/components/screener/SignalPicker.tsx` | 选股/回测/监控规则中共用的信号多选组件，按 kind 过滤自定义信号 |
| 信号定义 | `frontend/src/lib/signals.ts` | 20 个内置信号定义、4 个分时信号标签、中文名映射工具函数 `cnSignal()` |
| API 客户端 | `frontend/src/lib/api.ts` | 自定义信号相关接口：`customSignalsList`、`customSignalsOptions`、`customSignalSave`、`customSignalsAiGenerate` |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `customSignals` 和 `customSignalsOptions` 两个 TanStack Query 键 |
| 路由 | `frontend/src/router.tsx` | 注册 `/signals` 路由（lazy import `Signals` 组件） |
| 因子信号对话框 | `frontend/src/pages/backtest/AddFactorSignalDialog.tsx` | 从因子一键生成自定义信号条件 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 信号定义文件 | `data/user_data/custom_signals/*.json` | 每个自定义信号一个 JSON 文件，含 id/name/kind/conditions/enabled/timeframe 等字段 |

### 测试

| 文件 | 路径 | 用途 |
|------|------|------|
| 因子条件测试 | `backend/tests/test_custom_signals_factor_conditions.py` | 字段白名单动态化、因子列物化链路、校验与注入 |
| AI 生成测试 | `backend/tests/test_custom_signals_ai.py` | 提示词构建、JSON 解析（含容错）、API 端点 |
| 盘中信号测试 | `backend/tests/test_intraday_signals.py` | 特征帧计算、表达式编译、上升沿语义、引擎注入、回放 |
| 监控集成测试 | `backend/tests/test_intraday_monitor_signals.py` | 边沿触发不重放、流经监控引擎 |
| 策略详情测试 | `backend/tests/test_strategy_detail_signals.py` | entry/exit signals 的 overrides 合并回归 |

## 业务逻辑

### 核心流程

```text
[用户定义信号] → [校验字段白名单/运算符] → [编译为 Polars 布尔表达式]
  → [注入 enriched 数据帧] → [策略/回测/监控消费信号列]
```

内置信号：
```text
[指标流水线 compute_indicators] → [compute_signals: 20 个原子信号]
  → [enriched 帧含 signal_* 列] → [策略/回测/监控直接引用]
```

盘中信号：
```text
[分钟 K 数据] → [build_feature_frame: 特征序列]
  → [build_intraday_expressions + apply_intraday_edges: 条件上升沿]
  → [IntradaySignalEvaluator: 按分钟评估/注入 enriched 快照]
```

### 内置信号 (20 个)

在 `pipeline.py:574-591` 定义 `SIGNAL_DEPENDENCIES`，在 `pipeline.py:617-665` 的 `compute_signals()` 中实现。每个信号是一个 Polars 布尔表达式，多数为穿越/交叉判定（如 `close > ma20 AND prev_close <= prev_ma20`）。前端定义在 `signals.ts:19-160`，含中文名称、分类、描述。

**类型分布**：11 个入场（entry）、7 个出场（exit）、2 个出入通用（both）。

**额外信号**：4 个分时穿越信号（`signal_intraday_*`）在 `intraday_signals.py:24-29` 定义，通过 `_legacy_builtin_definitions()` 编译为等价表达式（`intraday_signals.py:46-65`）。

### 自定义信号

**表达式编译**：`custom_signals.py:283-323` 的 `build_expressions()` 将每个信号的多个条件用 `&`（AND）串联，编译为 `{column_name: pl.Expr}` 字典。列名前缀为 `csg_`（`custom_signals.py:28`）。

**字段白名单**：`custom_signals.py:38-60` 的 `ALLOWED_FIELDS` 定义了约 40 个允许引用的物化列。`allowed_fields()`（`:85-96`）动态合并注册表因子列和 string 扩展字段列。

**运算符集**：数值型支持 `> >= < <= == !=`（`OPS`，`custom_signals.py:30`）；字符串型支持 `contains == !=`（`STRING_OPS`，`custom_signals.py:33`）；盘中信号额外支持 `cross_up cross_down`（`INTRADAY_OPS`，`custom_signals.py:387`）。

**日期偏移**：每个操作数可配置 `leftDays`/`rightDays`，编译时通过 `shift(days).over("symbol")` 实现（`custom_signals.py:275-279`）。盘中路径不支持日期偏移（`allow_shift=False`）。

**持久化**：每个信号保存为 `data/user_data/custom_signals/{id}.json`（`custom_signals.py:131-164`）。`load_all()` 读取目录下所有 JSON 文件。

**校验**：`validate()` 检查 id 格式、name 非空、kind 合法、conditions 非空且 ≤8 条、字段在白名单内、运算符合法、右值可解析（`custom_signals.py:226-266`）。

**因子列物化**：`materialize_factor_columns()`（`custom_signals.py:99-127`）检测信号表达式引用的缺失列，若属于注册表因子则复用 `materialize_scoring_columns()` 补算。

**注入**：`inject()`（`custom_signals.py:332-361`）将编译好的表达式作为列加入 DataFrame。缺失依赖时告警跳过，不阻断。

### 盘中信号

**IntradaySignalEvaluator**（`intraday_signals.py:76-159`）：维护 `_last_bar` 状态，确保每个标的的同一天同一根 bar 不会重复触发。评估流程：

1. 过滤启用规则对应的标的集合
2. 调用 `build_feature_frame()` 构造特征帧
3. 调用 `build_intraday_expressions()` 编译条件表达式
4. 调用 `apply_intraday_edges()` 求值并取上升沿
5. 应用 `min_bars` 门槛（不足 N 根已完成 bar 不触发）
6. 对比 `_last_bar` 状态，只返回新 bar 的触发结果

**apply_intraday_edges()**（`custom_signals.py:486-502`）：先求值条件列（fill_null(false)），再取 `当前为 true 且前一根为 false` 的上升沿。首根 bar 前值视为 null → fill_null(true) → 不触发。

**盘中信号注入路径**：

- **监控路径**：`quote_service.py:1386-1446` 的 `_inject_intraday_signals()`，每分钟桶控频，通过 `IntradaySignalEvaluator.evaluate()` 评估并 `inject()` 到 enriched 快照。
- **引擎路径**：`engine.py:1630-1663` 的 `_inject_intraday_signal_columns()`，向分钟策略执行帧注入盘中信号列。
- **回放路径**：`signals.py:236-329` 的 `/api/custom-signals/intraday/replay`，用本地历史分钟 K 回放触发时点。
- **回测路径**：分钟回测 worker 调用 `engine.py` 的 `_inject_intraday_signal_columns()`。

### 数据流

**日线内置信号**：
1. `compute_all()` 或 `run_pipeline()` 调用 `compute_indicators()` 计算指标列
2. 调用 `compute_signals(df)` 计算 20 个内置信号 + 注入自定义信号（`pipeline.py:963`）
3. 结果写入 enriched parquet（含 `signal_*` 列），或直接返回给消费者

**日线自定义信号（全量路径）**：
1. `_get_custom_signal_exprs()` 懒加载 `data/user_data/custom_signals/*.json`，编译为表达式（`pipeline.py:53-64`）
2. `compute_signals()` 先 `attach_ext_columns()` 注入扩展表数值列，再 `materialize_factor_columns()` 补算因子列，最后 `inject()` 注入信号列（`pipeline.py:669-681`）

**日线自定义信号（盘中实时路径）**：
1. `compute_enriched_today()` 调用 `_get_custom_signal_exprs_today()`（`allow_shift=False`，跳过日期偏移条件）
2. `attach_ext_columns(include_snapshot=True)` 注入扩展列（含快照模式）
3. `custom_signals.inject()` 注入信号列（`pipeline.py:2143`）

**自定义信号 CRUD 数据流**：
1. 前端 `CustomSignalDialog` 提交 → `POST /api/custom-signals`
2. API 路由 `save_signal()` 校验 → 调用 `custom_signals.save_one()` 写 JSON 文件
3. `_invalidate()` 失效：`invalidate_intraday_cache()` → `invalidate_custom_signals()` → `strategy_cache.clear_cache()` → `repo.clear_cache()`
4. 下次计算时重新加载 JSON → 重编译表达式

**前端信号选择器数据流**：
1. `SignalPicker` 组件加载时发送 `QK.customSignalsOptions` 查询获取可选字段/运算符（`GET /api/custom-signals/options`）
2. 同时发送 `QK.customSignals` 查询获取已保存的自定义信号列表（`GET /api/custom-signals`）
3. 按 kind 过滤（entry/exit/both），合并内置信号选项展示
4. 用户选择后，信号 ID 列表保存在策略 overrides 中

### 调用链

**日线全量信号计算**：
```text
compute_all / run_pipeline / screener (pipeline.py:963 / :1414 / screener.py:182:270)
  → compute_signals(df, needed) (pipeline.py:617)
    → ext_factors.attach_ext_columns(df, include_snapshot=False) (pipeline.py:674)
    → custom_signals.build_expressions(sigs) 编译 (pipeline.py:60:79)
    → custom_signals.materialize_factor_columns(df, exprs) 补因子列 (pipeline.py:678)
    → custom_signals.inject(df, exprs) 注入信号列 (pipeline.py:679)
```

**盘中实时信号注入（监控路径）**：
```text
quote_service 行情轮 (quote_service.py:1192)
  → _inject_intraday_signals(enriched, engine, "stock") (quote_service.py:1386)
    → engine.intraday_signal_symbols("stock") (monitor.py:564)
    → repo.get_minute_batch() / fetch_intraday_monitor_batch() 获取分钟 K
    → IntradaySignalEvaluator.evaluate() (intraday_signals.py:82)
      → build_feature_frame(minute_df, prev_close) (intraday_features.py:54)
      → custom_signals.build_intraday_expressions(definitions) (custom_signals.py:439)
      → custom_signals.apply_intraday_edges(frame, exprs) (custom_signals.py:486)
    → IntradaySignalEvaluator.inject(enriched, signals) (intraday_signals.py:162)
```

**自定义信号 CRUD 调用链**：
```text
前端 Dialog (CustomSignalDialog.tsx:85) → POST /api/custom-signals (signals.py:172)
  → custom_signals.validate(sig) (custom_signals.py:226)
  → custom_signals.save_one() (custom_signals.py:153)
  → _invalidate(request) (signals.py:22)
    → custom_signals.invalidate_intraday_cache() (custom_signals.py:536)
    → invalidate_custom_signals() (pipeline.py:86)
    → strategy_cache.clear_cache() (strategy_cache.py:76)
    → repo.clear_cache()
```

**回测信号合并**：
```text
backtest strategy run (strategy.py:2301)
  → _build_signal_mask(panel, signals, name) (strategy.py:2320)
    → 遍历 signals，支持 signal_ / csg_ 前缀
    → 多个信号列 OR 合并
    → 返回布尔 Series
```

### 状态机

盘中信号 `IntradaySignalEvaluator` 维护 `_last_bar` 状态：

```text
[空状态] → 首次 evaluate: 建立基线，不触发
  → 新 bar 出现 && 条件上升沿: 触发 → 更新 last_bar
  → 同一 bar 重复调用: 不触发 (last_seen 限制)
  → 新交易日: 重新建立基线 (last_time.date() != 当前日期)
```

## 关键数据结构

### API 契约

**GET /api/custom-signals** — 返回信号列表：
```json
{ "signals": [{ "id": "str", "name": "str", "kind": "entry|exit|both",
    "conditions": [{ "left": "str", "op": "str", "right": "str",
      "leftDays": 0, "rightDays": 0 }],
    "enabled": true, "timeframe": "daily|intraday", "min_bars": 0 }] }
```

**GET /api/custom-signals/options** — 返回字段/运算符选项：
```json
{ "fields": [{ "key": "str", "label": "str" }],
  "groups": [{ "key": "str", "label": "str", "fields": [...] }],
  "maxDays": 60, "operators": [">", ">=", "<", "<=", "==", "!="],
  "stringFields": ["ext_..."], "stringOperators": ["contains", "==", "!="],
  "kinds": [{ "key": "entry|exit|both", "label": "入场|出场|出入通用" }],
  "intraday": { "fields": [...], "operators": ["...", "cross_up", "cross_down"] },
  "timeframes": [{ "key": "daily", "label": "日线" }, { "key": "intraday", "label": "盘中(分钟K)" }] }
```

**POST /api/custom-signals/ai/generate** — AI 生成请求/响应：
```json
// 请求: { "description": "回踩MA20且放量" }
// 响应: { "name": "str", "conditions": [{ "left": "str", "op": "str",
//   "right": "str", "leftDays": 0, "rightDays": 0 }] }
```

**POST /api/custom-signals/intraday/replay** — 盘中信号回放：
```json
// 请求: { "signal_id": "str", "start_date": "YYYY-MM-DD",
//   "end_date": "YYYY-MM-DD", "symbols": ["str"], "asset_type": "stock" }
// 响应: { "signal_id": "str", "triggers": [{ "date": "str", "time": "str",
//   "symbol": "str" }], "days_scanned": 0, "bars_scanned": 0 }
```

### 存储结构

**自定义信号 JSON 文件** (`data/user_data/custom_signals/{id}.json`)：
```json
{ "id": "low_touches_ma5", "name": "跌至MA5", "kind": "entry",
  "conditions": [
    { "left": "low", "op": "<=", "right": "field:ma5",
      "leftDays": 0, "rightDays": 0 }
  ],
  "enabled": true, "timeframe": "daily", "min_bars": 0 }
```

**enriched parquet 信号列**：
- 内置信号列：`signal_ma_golden_5_20`、`signal_macd_golden` 等 20 个布尔列
- 自定义信号列：`csg_{id}` 前缀的布尔列（如 `csg_low_touches_ma5`）
- 盘中信号列：`csgi_{id}` 前缀的布尔列（如 `csgi_my_intraday_signal`）
- 内置盘中信号列：`signal_intraday_avg_cross_up`、`signal_intraday_avg_cross_down`、`signal_intraday_zero_cross_up`、`signal_intraday_zero_cross_down`

**enriched 窄表存储列**：14 列（`pipeline.py:93-102`），不含任何信号列。信号列在读取时通过 `compute_signals()` 现算。

### 内存结构

**模块级缓存**（`pipeline.py:49-50`）：
```python
_custom_signal_exprs: dict[str, pl.Expr] | None = None     # allow_shift=True
_custom_signal_exprs_today: dict[str, pl.Expr] | None = None  # allow_shift=False
```

**盘中信号指纹缓存**（`custom_signals.py:506`）：
```python
_intraday_cache: dict[Path, tuple[object, list[dict]]] = {}
# 以 (文件名, mtime) 指纹为 key，避免每分钟读盘
```

**IntradaySignalEvaluator 状态**（`intraday_signals.py:80`）：
```python
self._last_bar: dict[tuple[str, str], datetime] = {}
# key: (asset_type, symbol), value: 最后处理 bar 的 datetime
```

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **创建自定义信号**：通过信号库页面 `/signals` 或策略设置中的「新建信号」按钮，使用「字段 + 运算符 + 值」组合条件。
- **从因子创建信号**：在策略设置中点击「从因子快速创建条件」，通过 `AddFactorSignalDialog` 将因子阈值条件生成为自定义信号。
- **AI 生成信号**：在自定义信号对话框中描述信号思路，LLM 生成条件组合（需先配置 AI API Key）。
- **扩展数据字段**：通过扩展数据（ext_data）配置数值/字符串字段表，信号条件自动可引用这些字段（`ext_factors.py`）。

### L2 扩展（插槽/路由/注册替换）

- **新因子注册**：在 `factors/registry.py` 注册新因子后，`allowed_fields()` 自动将其纳入白名单（`custom_signals.py:85-96`），信号条件可直接引用。
- **新扩展数据表**：在 `data/user_data/ext_data/` 下配置新表，`ext_factors.py` 自动处理列注入和注册因子。
- 本项目无信号相关的 L2 前端插槽。

### L3 修改（直接改源码）

- **新增内置信号**：在 `pipeline.py` 的 `SIGNAL_DEPENDENCIES` 添加依赖映射，在 `compute_signals()` 添加表达式，在 `signals.ts` 添加定义（含名称/分类/描述）。
- **修改字段白名单**：编辑 `custom_signals.py:38-60` 的 `ALLOWED_FIELDS` 集合。
- **修改运算符集**：编辑 `custom_signals.py:30-33` 的 `OPS`/`STRING_OPS`，在 `_OP_BUILDERS`（`:63-72`）中实现对应构造器。
- **修改盘中信号特征**：编辑 `intraday_features.py:23-35` 的 `INTRADAY_FEATURES` 字典，并在 `build_feature_frame()` 中添加计算逻辑。

### 缓存失效影响

`_invalidate()` 在信号保存/删除时依次清理 4 层缓存：

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 信号定义缓存（盘中） | `invalidate_intraday_cache()` 清 `_intraday_cache` 字典 | 盘中信号下次加载重新读盘 |
| 信号表达式缓存（模块级） | `invalidate_custom_signals()` 置 `None` | 下次 `compute_signals()` 重编译表达式 |
| 策略结果缓存（磁盘） | `strategy_cache.clear_cache()` 删文件 | 选股结果下次重算 |
| repo 内存 enriched 缓存 | `repo.clear_cache()` | 全量数据下次重新加载 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `test_custom_signals_factor_conditions.py` | `test_allowed_fields_union_registry` — 白名单动态化；`test_materialize_factor_columns_and_inject` — 因子列物化+注入；`test_materialize_skips_unknown_columns` — 缺失列跳过 |
| 单元测试 | `test_custom_signals_ai.py` | `test_build_messages_contains_whitelist_fields_and_rules` — 提示词含白名单；`test_parse_and_validate_*` — JSON 解析/容错/校验；`test_ai_generate_endpoint_*` — API 端点成功/失败 |
| 单元测试 | `test_intraday_signals.py` | `test_feature_frame_*` — 特征帧计算；`test_intraday_compile_*` — 表达式编译；`test_signal_step_*` — 信号评估；`test_intraday_signal_*` — 引擎注入/回放 |
| 集成测试 | `test_intraday_monitor_signals.py` | `test_intraday_crosses_are_edge_triggered_and_not_replayed` — 边沿触发不重放；`test_intraday_signals_flow_through_monitor_engine` — 流经监控引擎 |
| 回归测试 | `test_strategy_detail_signals.py` | `test_*_override_*` — 策略详情 entry/exit signals 合并回归 |

## 依赖关系

### 依赖的其他功能

- **指标流水线**（`indicators/pipeline.py`）：内置信号依赖指标列（ma5/ma20/macd_dif/boll_upper 等），自定义信号依赖 enriched 物化列和注册表因子。
- **扩展数据**（`factors/ext_factors.py`）：自定义信号条件可引用扩展数据字段（数值/字符串），需先配置扩展数据表。
- **因子注册表**（`factors/registry.py`）：自定义信号条件可引用注册表因子（虚拟/自定义/复合），因子列由 `materialize_scoring_columns()` 补算。
- **AI 服务**（`services/ai_provider.py`）：AI 生成信号功能依赖 LLM 服务配置。
- **分钟 K 数据**（`kline_repository`）：盘中信号依赖分钟 K 数据，实时路径依赖 `minute_refresh` 服务健康状态或数据源 API。

### 被依赖的功能

- **策略选股服务**（`services/screener.py`）：选股结果依赖于 `signal_*`/`csg_*` 列作为入场/出场触发器。
- **回测服务**（`backtest/`）：回测策略依赖信号列构建买卖掩码。
- **监控引擎**（`strategy/monitor.py`）：监控规则支持将信号（含盘中信号）作为触发条件。
- **策略引擎**（`strategy/engine.py`）：分钟策略执行依赖盘中信号列注入。
- **行情服务**（`services/quote_service.py`）：实时监控轮依赖 `_inject_intraday_signals()` 注入盘中信号到 enriched 快照。

## 常见问题与注意事项

- **日期偏移限制**：带 `leftDays`/`rightDays` 的盘中信号自动跳过，不会报错。日线路径中 `allow_shift=False` 的实时路径同样跳过偏移条件。
- **自定义信号 ID 不可修改**：保存后 id 不可编辑，如需更换需要新建。
- **字段白名单安全**：自定义信号使用白名单机制，杜绝任意表达式注入。字段白名单包括物化列、注册表因子列和扩展数据字符串字段，不包含 `symbol`/`date`/`name` 等非数值列。
- **盘中信号不跨日**：`apply_intraday_edges` 按 `(symbol, date)` 分组，首根 bar 不触发，同一标的同一根 bar 不会重复触发。
- **信号定义变更缓存滞后**：保存/删除信号后，API 端点自动清理 4 层缓存。但如果存在其他进程/线程直接读取文件，缓存可能滞后，需等下次失效触发。
- **扩展数据字符串字段**：仅支持 `contains`/`==`/`!=` 运算符，右值只能为字符串字面量，不支持字段引用。数值扩展字段注册为因子后自动纳入白名单，支持所有数值运算符。
- **AI 生成信号不自动落盘**：AI 生成的 `{name, conditions}` 仅回填表单，不直接保存到磁盘。用户需确认后通过常规 `save` 流程提交。