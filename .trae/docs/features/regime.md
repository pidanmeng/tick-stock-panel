---
title: 市场环境(Regime) — 功能文档
description: 市场环境(Regime)功能的完整参考，涵盖环境状态分类、情绪周期阶段判定、主线识别及其前端展示。
---

# 市场环境(Regime) — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

市场环境(Regime)功能从已算好的 enriched 日K数据中按日聚合环境指标，用规则引擎将市场分类为 5 档离散状态（强势/偏强/震荡/偏弱/弱势），在此基础上通过连板梯队指标判定 6 阶段情绪周期（冰点/启动/主升/高潮/退潮/修复），并识别每日概念/行业主线。数据供前端市场环境页（路由 `/regime`）展示历史趋势、状态分布、阶段演化与主线排行。

**定位**：纯本地聚合计算，不依赖外部数据源，不生成交易信号，只供研究分析使用。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `backend/app/api/regime.py` | 7 个 REST 端点：history/latest/states/coverage/recompute/phases/mainline + 5s TTL 查询缓存 |
| 核心服务 | `backend/app/services/regime_builder.py` | 日级聚合、4 维评分、状态分类、upsert 持久化、增量检测(stale+缺口) |
| 情绪周期 | `backend/app/services/market_phase.py` | 梯队聚合表达式、晋级率计算、EMA 平滑、6 阶段规则引擎、持续性确认 |
| 主线识别 | `backend/app/services/market_mainline.py` | 概念/行业涨停梯队聚合、截面 rank 归一加权、宽基过滤、upsert 持久化 |
| 偏好配置 | `backend/app/services/preferences.py` | 管道开关、分批参数、主线过滤配置、ST 剔除开关 |
| 盘后管道 | `backend/app/jobs/daily_pipeline.py` | 增量计算 regime + 主线 + 阶段切换推送通知 |
| 路由注册 | `backend/app/main.py:481` | `app.include_router(regime.router)` |
| 测试 | `backend/tests/test_regime_builder.py` | 环境聚合与状态分类测试 |
| 测试 | `backend/tests/test_market_phase.py` | 梯队/晋级率/阶段序列/弱档否决/持续性测试 |
| 测试 | `backend/tests/test_market_mainline.py` | 概念/行业聚合/过滤/upsert/增量测试 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Regime.tsx` | 完整市场环境页面，含市场环境 + 情绪周期双 tab、5 个 ECharts 图、日历热力图、主线过滤面板 |
| API 类型与客户端 | `frontend/src/lib/api.ts:507-667` | RegimeRow/RegimeState/MarketPhase/PhaseSegment/MainlineResult 等类型定义 + 7 个 API 调用方法 |
| 查询键 | `frontend/src/lib/queryKeys.ts:116-121` | 6 个 TanStack Query 键（regimeHistory/regimeLatest/regimeStates/regimeCoverage/regimePhases/regimeMainline） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 持久化数据 | `data/regime_history/part.parquet` | 日频环境时序表（state/score/4 子维度/梯队指标/phase） |
| 持久化数据 | `data/mainline_history/part.parquet` | 日频主线时序表（概念/行业每日 top30） |
| 用户偏好 | `data/preferences.json` | 存储 pipeline_regime_enabled、batch_days、warmup_days、mainline_filter 等 |
| 功能文档 | `docs/market-phase.md` | 情绪周期阶段与主线识别的设计文档（口径、阈值、验收） |

## 业务逻辑

### 核心流程

```text
[enriched 日K(含 signal_limit_up/consecutive_limit_ups等)]
    → [按 date group_by 聚合: 涨跌家数/均值/中位/涨停/封板/梯队]
    → [_compute_subscores 4 维评分: 赚钱/投机/抗跌/趋势]
    → [classify_state 离散化: 5 档 state]
    → [upsert 到 regime_history/part.parquet]
    → [refresh_phase_labels: 读全量序列 → EMA 平滑 → 规则引擎 → 2 日确认 → 写回 phase 列]
    → [compute_mainline_range: 窄扫 enriched 4 列 → join 概念映射 → 截面 rank 加权 → 持久化]
    → [API 查询 + 前端 ECharts 渲染]
```

### 三个并存的分类体系

| 体系 | 输出 | 驱动量 | 档位 | 消费方 |
|------|------|--------|------|--------|
| `state` (5 档) | 状态标签 + 综合分 | 赚钱/投机/抗跌/趋势 4 维加权 | 强势/偏强/震荡/偏弱/弱势 | 回测环境过滤、挖掘、策略页 |
| `phase` (6 阶段) | 情绪周期阶段标签 | 连板梯队(高度/宽度/晋级率/完整度) | 冰点/启动/主升/高潮/退潮/修复 | 市场环境页分析、主线识别 |
| 主线排行 | 每日概念/行业排名 | 涨停数/最高板/梯队档位/二板宽度 | top30 排名 + 截面分 | 市场环境页阶段×主线、主线排行 |

### 数据流

1. **输入来源**：
   - enriched 日K Parquet（`kline_daily_enriched/date=*/part.parquet`），含 `change_pct`、`consecutive_limit_ups`、`signal_limit_up`、`ma20` 等列
   - 指数日K（`000001.SH`）计算每日涨幅供趋势维度
   - 概念映射快照（`ext_gn_ths`）供主线识别
   - 维表 instruments 供涨跌停价计算与 ST 剔除

2. **处理过程**：
   - **regime_builder._aggregate_daily**（[regime_builder.py:148](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L148)）：纯 polars `group_by("date")` 一次性向量化聚合，不逐日循环
   - **classify_state**（[regime_builder.py:116](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L116)）：4 维 → 规则引擎 → 5 档离散状态
   - **market_phase.classify_phase_series**（[market_phase.py:172](file:///c:/Code/tick-stock-panel/backend/app/services/market_phase.py#L172)）：EMA 平滑 + 6 级优先级规则 + 2 日确认 + 弱档否决
   - **market_mainline.compute_mainline_range**（[market_mainline.py:123](file:///c:/Code/tick-stock-panel/backend/app/services/market_mainline.py#L123)）：窄扫 4 列 → join 概念映射 → 截面 rank 归一 → 加权得分

3. **输出去向**：
   - `data/regime_history/part.parquet`：日频环境时序（含 phase 列，由 refresh_phase_labels 统一重标）
   - `data/mainline_history/part.parquet`：日频主线时序（concept + industry 两维度）
   - API 响应 → 前端 ECharts 图表 + 指标卡 + 表格

### 调用链

**主路径（手动重算）**：
```
Regime.tsx 点击"重算" → api.regimeRecompute()
  → POST /api/regime/recompute (regime.py:138)
    → regime_builder.run_regime_batch (regime_builder.py:453)
      → repo.get_enriched_range (缓存优先)
      → 或 _scan_enriched_fallback (分批慢路径, regime_builder.py:365)
      → _aggregate_daily (regime_builder.py:148)
        → market_phase.ladder_daily_aggs/promo_aggs (market_phase.py:105/121)
      → classify_state (regime_builder.py:116)
        → _compute_subscores (regime_builder.py:63)
    → regime_builder.upsert_regime_history (regime_builder.py:547)
    → regime_builder.refresh_phase_labels (regime_builder.py:525)
      → market_phase.classify_phase_series (market_phase.py:172)
    → market_mainline.compute_mainline_range (market_mainline.py:123)
    → market_mainline.upsert_mainline_history (market_mainline.py:252)
    → invalidate_regime_cache (regime.py:25)
```

**旁路（盘后管道增量）**：
```
daily_pipeline.py:670-723 → regime_builder.compute_regime_incremental (regime_builder.py:644)
  → detect_stale_dates (regime_builder.py:593) + enriched_date_set 缺口检测
  → run_regime_batch → upsert_regime_history → refresh_phase_labels
→ market_mainline.compute_mainline_incremental (market_mainline.py:279)
→ _push_phase_change_alert (daily_pipeline.py:810-834, 阶段切换通知)
```

**前端查询热路径**：
```
Regime.tsx 渲染 → 5 个 useQuery 并行:
  coverage (QK.regimeCoverage) → GET /api/regime/coverage
  history (['regime-history', range]) → GET /api/regime/history
  states (QK.regimeStates) → GET /api/regime/states
  phases (QK.regimePhases) → GET /api/regime/phases
  mainline (QK.regimeMainline) → GET /api/regime/mainline
```

### 状态机

**情绪周期阶段转换**（6 阶段，修复为兜底）：

```
冰点(ice) → 启动(ignite) → 主升(rally) → 高潮(climax) → 退潮(ebb) → 修复(repair) → 冰点(ice) ...
```

阶段切换需要连续 `_CONFIRM_DAYS=2` 日出现新标签才生效（[market_phase.py:81](file:///c:/Code/tick-stock-panel/backend/app/services/market_phase.py#L81)）。弱档否决：`state ∈ {weak, lean_weak}` 时正向阶段（主升/高潮/启动）降为修复（[market_phase.py:85-86](file:///c:/Code/tick-stock-panel/backend/app/services/market_phase.py#L85-L86)）。

## 关键数据结构

### API 契约

**GET /api/regime/history?start&end&limit**
```json
{ "rows": [{ "date": "2024-09-24", "state": "strong", "score": 82, "limit_up": 150,
  "max_consecutive": 7, "seal_rate": 0.85, "profit_score": 78, "speculation_score": 80,
  "resilience_score": 65, "trend_score": 72, "phase": "rally", "first_board": 80,
  "ge2_count": 28, "ladder_completeness": 0.85, "promo_rate": 0.35, "promo_pool": 30 }],
  "total": 120 }
```

**GET /api/regime/states?days=250**
```json
{ "distribution": [{ "state": "strong", "label": "强势", "count": 45, "pct": 18.0 }],
  "days": 250 }
```

**GET /api/regime/phases?start&end**
```json
{ "segments": [{ "phase": "rally", "label": "主升", "start": "2024-09-24", "end": "2024-10-08",
  "days": 7, "avg_height": 8.3, "avg_ge2": 35.2, "avg_promo": 0.38, "avg_seal_rate": 0.82,
  "top_mainlines": [{ "member": "华为概念", "top5_days": 6, "score_sum": 480, "max_boards": 7,
    "leader_symbol": "600519.SH" }] }], "total": 1 }
```

**GET /api/regime/mainline?start&end&top=10&kind=concept**
```json
{ "rows": [{ "date": "2024-09-24", "kind": "concept", "member": "华为概念",
  "limit_up_count": 25, "ge2_count": 8, "max_boards": 7, "rungs_filled": 5,
  "leader_symbol": "600519.SH", "score": 92.5, "rank": 1 }],
  "leaders": [{ "member": "华为概念", "top1_days": 12, "avg_score": 85.3, "max_boards": 7 }],
  "membership_note": "概念成分为当前快照回看历史...",
  "filter": { "min_members": 4, "max_members": 600, "blacklist": [], "exclude_st": true } }
```

### 存储结构

**regime_history/part.parquet**（日频，单行=1 交易日）：
`date, state, score, limit_up, limit_down, broken_limit, max_consecutive, seal_rate, up_count, down_count, up_ratio, index_pct, above_ma20_pct, total_amount, avg_turnover, avg_pct, median_pct, strong_up_pct, strong_down_pct, profit_score, speculation_score, resilience_score, trend_score, phase, first_board, ge2_count, ge3_count, ge5_count, ladder_completeness, promo_rate, promo_pool`

**mainline_history/part.parquet**（日频，单行=1 概念×1 日）：
`date, kind, member, limit_up_count, ge2_count, max_boards, boards_sum, rungs_filled, leader_symbol, score, rank`

### 内存结构

**API 查询缓存**（[regime.py:19-22](file:///c:/Code/tick-stock-panel/backend/app/api/regime.py#L19-L22)）：
- `_cache: dict | None` — 单字典缓存最近一次查询结果
- `_cache_ts: float` — 缓存时间戳
- `_cache_lock: threading.Lock` — 线程安全
- TTL = 5 秒（`_CACHE_TTL = 5.0`）

**ST 符号缓存**（[market_mainline.py:72](file:///c:/Code/tick-stock-panel/backend/app/services/market_mainline.py#L72)）：
- `_ST_SYMBOLS_CACHE: tuple[float, frozenset[str]] | None` — 600s 进程内缓存

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **阈值调整**：修改 [market_phase.py:49-76](file:///c:/Code/tick-stock-panel/backend/app/services/market_phase.py#L49-L76) 的常量（CLIMAX_GE2/RALLY_HEIGHT/EBB_PROMO 等），改后重新运行 `regime_recompute` 即可生效
- **权重调整**：修改 [regime_builder.py:30-35](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L30-L35) 的 `WEIGHTS` 字典
- **状态阈值**：修改 [regime_builder.py:38-42](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L38-L42) 的 `STATE_STRONG/STATE_LEAN_STRONG/STATE_RANGE/STATE_LEAN_WEAK`
- **分批参数**：通过偏好配置 `regime_batch_days` / `regime_warmup_days`（[preferences.py:346-367](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L346-L367)）
- **主线过滤**：通过偏好配置 `mainline_max_members` / `mainline_min_members` / `mainline_blacklist` / `sentiment_exclude_st`（[preferences.py:370-434](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L370-L434)）

### L2 扩展（插槽/路由/注册替换）

该功能当前未提供 L2 扩展点。硬编码的策略包括：
- 阶段判定的 6 级优先级顺序（[market_phase.py:46](file:///c:/Code/tick-stock-panel/backend/app/services/market_phase.py#L46)）
- 主线分权重（[market_mainline.py:39-44](file:///c:/Code/tick-stock-panel/backend/app/services/market_mainline.py#L39-L44)）
- 每日主线持久化 top30（[market_mainline.py:34](file:///c:/Code/tick-stock-panel/backend/app/services/market_mainline.py#L34)）

如需扩展，建议参照 `docs/secondary-development.md` 的模式新增注册机制。

### L3 修改（直接改源码）

- **新增评分维度**：在 `_aggregate_daily` 的 group_by 中添加新聚合列，在 `_compute_subscores` 中添加新维度加权，在 `WEIGHTS` 中调整权重
- **新增阶段规则**：在 `classify_phase_series` 的 `raw_label` 函数中按优先级插入新规则
- **新增主线维度**：在 `compute_mainline_range` 的 `_SCORE_WEIGHTS` 中添加新指标
- **修改持久化 schema**：`upsert_regime_history`（[regime_builder.py:547](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L547)）和 `upsert_mainline_history`（[market_mainline.py:252](file:///c:/Code/tick-stock-panel/backend/app/services/market_mainline.py#L252)）已支持 schema 自动迁移（旧数据补 null）

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| API 查询缓存 | `invalidate_regime_cache()` 清空 `_cache`（[regime.py:25-30](file:///c:/Code/tick-stock-panel/backend/app/api/regime.py#L25-L30)） | 重算后下次查询重新从 Parquet 读取 |
| 前端 TanStack Query | `qc.invalidateQueries` 按前缀批量失效（[Regime.tsx:637-644](file:///c:/Code/tick-stock-panel/frontend/src/pages/Regime.tsx#L637-L644)） | regime-history / regime-states / regime-latest / regime-phases / regime-mainline / regime-coverage |
| Parquet 文件 | 直接写 `write_parquet` 覆盖 | 下次读取即最新 |
| ST 符号缓存 | 600s 超时自动刷新（[market_mainline.py:84](file:///c:/Code/tick-stock-panel/backend/app/services/market_mainline.py#L84)） | 维表 snapshot 进程内不变，不需手动失效 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_regime_builder.py` | 环境聚合、状态分类、4 维评分、upsert 覆盖逻辑 |
| 单元测试 | `backend/tests/test_market_phase.py` | 梯队聚合（首板/ge2/ge3/ge5）、晋级率（池不足记 null）、梯队完整度、阶段序列规则、弱档否决、持续性（噪声下不出现 1 日翻转）、refresh 往返 |
| 单元测试 | `backend/tests/test_market_mainline.py` | 概念/行业聚合、宽基过滤（成员数上限/下限）、黑名单、最少涨停家数（`_MIN_LIMIT_UP`）、同日 upsert 替换、增量补齐 |

## 依赖关系

### 依赖的其他功能

- **enriched 日K**：regime 的数据基础，依赖 `indicators.pipeline.compute_indicators` 和 `compute_limit_signals` 生成信号列
- **概念映射**：主线识别依赖 `rps_rotation._load_concept_map_df` 加载 `ext_gn_ths` 快照
- **维表 instruments**：涨跌停价计算、ST 名称判定
- **偏好配置**：`preferences.py` 提供管道开关、分批参数、过滤配置

### 被依赖的功能

- **日终盘后管道**：`daily_pipeline.py` 在 pipeline 中调用 `compute_regime_incremental` 和 `compute_mainline_incremental`
- **阶段切换通知**：`daily_pipeline._push_phase_change_alert` 调用 `latest_phase_transition` 向 SSE 推送阶段切换消息

## 常见问题与注意事项

1. **概念成分快照回看偏差**：主线识别使用当前概念快照回看历史，早年存在归属漂移。`membership_note` 字段随 API 返回并在前端展示。详见 [docs/market-phase.md#快照回填偏差](file:///c:/Code/tick-stock-panel/docs/market-phase.md#快照回填偏差)。

2. **ST 剔除口径**：默认剔除风险警示股（`sentiment_exclude_st=True`）。主板 ST 在 2026-07 前享 5% 涨跌幅，是跨行业状态桶而非题材。切换口径需全量重算 regime 与主线。

3. **修复段占比高**：A 股大部分时间没有处于可辨认的周期位置，修复段约占 ~74% 天数。退潮/冰点天然是短段（平均 2.8/2.5 天）。

4. **全量重算内存**：首次全量回填或大范围重算时，若缓存未预热会走 `_scan_enriched_fallback` 分批路径。可通过偏好调整 `batch_days`（默认 60）和 `warmup_days`（默认 40）控制峰值。

5. **管道默认关闭**：`pipeline_regime_enabled` 默认 False。首次使用需在页面点击"重算"手动触发，或通过数据页设置开启自动计算。

6. **API 缓存 TTL 仅 5 秒**：`_CACHE_TTL = 5.0`，高频刷新时每次读 Parquet（但 Parquet 行数仅千级，开销可忽略）。