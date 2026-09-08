---
title: 看板 Dashboard — 功能文档
description: 看板 Dashboard 是 TSP 的首页（路由 /），提供 A 股全市场行情总览的一站式可视化页面。本文档是修改、编辑或扩展该功能所需的完整参考。
---

# 看板 Dashboard — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

看板 Dashboard 是 TSP 的默认首页（路由 `/`），定位为"市场温度计"和项目主入口，提供 A 股全市场行情总览的一站式可视化聚合页面，包括指数行情、涨跌家数、涨跌停统计、涨跌幅分布、情绪雷达、涨停梯队、概念/行业热度排行、个股榜单以及监控中心实时信号。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `backend/app/api/overview.py` | `/api/overview/market` 单路由 + 5s TTL 缓存管理 |
| API 路由 | `backend/app/api/regime.py` | `/api/regime/*` 路由(市场环境时序，独立但同属看板域) |
| API 路由 | `backend/app/api/abnormal.py` | `/api/abnormal/*` 路由(异常波动，独立页面 `/abnormal`) |
| 服务 | `backend/app/services/market_overview_builder.py` | 市场总览聚合核心逻辑(与 HTTP Request 解耦) |
| 服务 | `backend/app/services/regime_builder.py` | 市场环境时序计算(纯函数，按日聚合+规则引擎分类) |
| 服务 | `backend/app/services/abnormal_moves.py` | 异常波动边缘计算(交易所口径偏离值接近度) |
| 装配 | `backend/app/main.py` | `include_router` 注册 overview/regime/abnormal 路由 |
| 定时 | `backend/app/jobs/daily_pipeline.py` | 盘后 regime 增量计算 |
| 缓失效 | `backend/app/services/quote_service.py` | 每次行情更新后调用 `invalidate_overview_cache()` |
| 缓失效 | `backend/app/api/data.py` | 数据同步/刷新后调用 `invalidate_overview_cache()` |
| 缓失效 | `backend/app/api/settings.py` | 设置变更后调用 `invalidate_overview_cache()` |
| 指数 | `backend/app/services/index_const.py` | 核心指数清单(`CORE_INDEX_SYMBOLS`) |
| 扩展 | `backend/app/services/ext_data.py` | 概念/行业维度扩展数据加载 |
| 测试 | `backend/tests/test_regime_builder.py` | 22 条：regime 聚合与分类 |
| 测试 | `backend/tests/test_abnormal_moves.py` | 25 条：异动边缘计算 |
| 测试 | `backend/tests/test_abnormal_intraday.py` | 5 条：盘中异动 |
| 测试 | `backend/tests/test_ext_preset_dimension_values.py` | 维度值解析 |
| 测试 | `backend/tests/test_review_push_mode.py` | 复盘推送模式(依赖 overview) |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Dashboard.tsx` | 看板主页面(952 行)，含全部子组件 |
| 组件 | `frontend/src/components/DimensionMembersDialog.tsx` | 概念/行业成分股弹窗 |
| 组件 | `frontend/src/components/StockPreviewDialog.tsx` | 个股预览弹窗(含导航) |
| 组件 | `frontend/src/components/stock-table/primitives.tsx` | `boardTag` 板块标签函数 |
| 组件 | `frontend/src/components/SealedBadge.tsx` | 五档封单修正状态徽标 |
| 组件 | `frontend/src/components/DatePicker.tsx` | 日期选择器 |
| API | `frontend/src/lib/api.ts` | `OverviewMarket` 接口定义 + `overviewMarket` 调用 |
| Query | `frontend/src/lib/queryKeys.ts` | `QK.overviewMarket` 工厂 + `SSE_INVALIDATE_PREFIXES` |
| SSE | `frontend/src/lib/useQuoteStream.ts` | SSE 事件驱动前端缓存失效 |
| 路由 | `frontend/src/router.tsx` | lazy load `Dashboard` + 路由 `/` |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 数据 | `data/regime_history/part.parquet` | 市场环境时序持久化 |
| 数据 | `data/ext_data/` | 概念/行业维度扩展数据目录 |
| 文档 | `.trae/docs/features/screener.md` | Screener 功能(overview 依赖 enriched 数据) |

## 业务逻辑

### 核心流程

#### 市场总览(Overview)

```text
前端请求 → /api/overview/market → 检查 5s TTL 缓存
  → _build_overview() → build_market_overview(repo, quote_service, depth_service, as_of)
  → ScreenerService._load_enriched_for_date(as_of) [加载 enriched Parquet]
  → 过滤真停牌(volume=0 且 change_pct=0)
  → 计算 breadth(涨跌家数/均值/中位/强弱)
  → 涨跌停计数 + 五档 DepthService sealed 修正(假涨停/假跌停剔除)
  → 封板率 = limit_up / (limit_up + broken)
  → 均线/新高新低(ma5/ma20/ma60/60日高/低)
  → 换手率/高换手/量比
  → 板块分布(沪/深/创/科/北)
  → 涨停梯队(连板分布)
  → 概念/行业维度排名(ext_data 扩展数据)
  → 情绪雷达 6 维度评分 + 综合情绪分 + 标签
  → 返回 JSON → 前端渲染
```

#### 市场环境(Regime)

```text
定时任务/手动触发 → compute_regime_incremental() / run_regime_batch()
  → repo.get_enriched_range(start, end) [多日 enriched 数据]
  → 过滤风险警示股(ST)
  → _aggregate_daily(): polars group_by("date") 一次向量化聚合
  → classify_state(): 规则引擎分 5 类离散状态(强势/偏强/震荡/偏弱/弱势)
  → 4 子维度: profit(赚钱)/speculation(投机)/resilience(抗跌)/trend(趋势)
  → 持久化: data/regime_history/part.parquet (upsert)
  → invalidate_regime_cache()
  → 阶段重标: refresh_phase_labels() → market_phase.classify_phase_series
```

### 数据流

1. **输入来源**：
   - 用户打开看板页面 → `api.overviewMarket(selectedDate)` 触发 GET 请求
   - SSE `quotes_updated` 事件 → 自动失效并重拉 overview-market 缓存
   - SSE `depth_updated` 事件 → 单独失效 overview-market（封单修正）
   - 定时任务 `daily_pipeline.py` 盘后触发 regime 增量计算
   - 用户手动点"重载"按钮 → `api.refreshCache()` + `invalidateQueries`

2. **处理过程**：
   - `market_overview_builder.py`: 从 enriched 数据（Polars 内存缓存/Parquet 文件）读取当日全市场数据，进行过滤、聚合、排名、评分
   - `regime_builder.py`: 从 enriched 多日范围数据按日 group_by 聚合指标，用规则引擎分类
   - `abnormal_moves.py`: 从历史偏离数据 + 实时行情计算偏离值接近度

3. **输出去向**：
   - Overview: JSON 响应 → TanStack Query 缓存(5s staleTime) → 前端渲染
   - Regime: `data/regime_history/part.parquet` 持久化 → 通过 `/api/regime/*` 查询
   - 缓存失效链: invalidate_overview_cache() → 后端 5s TTL 清空 → SSE 通知前端 → TanStack Query 自动 refetch

### 调用链

#### 市场总览(Overview)

```text
前端 Dashboard.tsx:603-608 (useQuery) → api.ts:2540 (GET /api/overview/market)
  → overview.py:358-374 (market_overview handler)
    → overview.py:343-355 (_build_overview, 检查 5s TTL 缓存)
      → market_overview_builder.py:354-359 (build_market_overview, 与 Request 解耦)
        → market_overview_builder.py:368 (ScreenerService 实例化)
        → market_overview_builder.py:372 (as_of 解析: 指定日期或最新有数据日)
        → market_overview_builder.py:373 (_quote_status: 实时行情状态)
        → market_overview_builder.py:374 (_index_quotes: 实时/数据库指数行情)
        → market_overview_builder.py:398 (svc._load_enriched_for_date(as_of))
        → market_overview_builder.py:410-415 (过滤真停牌)
        → market_overview_builder.py:416-432 (breadth: 涨跌家数/均值/中位/强弱)
        → market_overview_builder.py:434-455 (limit: 涨跌停 + sealed 修正)
        → market_overview_builder.py:457-464 (trend: 均线/新高新低)
        → market_overview_builder.py:466-469 (activity: 换手率)
        → market_overview_builder.py:471-485 (boards: 板块分布)
        → market_overview_builder.py:487-507 (tiers: 涨停梯队)
        → market_overview_builder.py:509-515 (vol_ratio: 量比)
        → market_overview_builder.py:517-518 (dimension_rank: 概念/行业排名)
        → market_overview_builder.py:520-549 (radar: 情绪雷达 6 维 + 情绪分)
        → market_overview_builder.py:551-595 (返回 JSON)
  → 响应 → Dashboard.tsx:603-608 (data 更新 → 子组件渲染)
```

#### SSE 失效链

```text
行情服务推送 SSE events
  → quotes_updated: useQuoteStream.ts:130-163
    → SSE_INVALIDATE_PREFIXES (queryKeys.ts:132-142) 含 'overview-market'
    → qc.invalidateQueries({ predicate: 前缀匹配 })
    → Dashboard useQuery 自动 refetch (staleTime 5s 后)
  → depth_updated: useQuoteStream.ts:191-196
    → qc.invalidateQueries({ queryKey: ['overview-market'] })
    → 同时失效 limit-ladder
```

#### 缓存失效写入点

```text
quote_service.py:420-422 (每次行情数据更新后)
data.py:695-696 (数据同步完成后)
data.py:872-873 (数据清除/刷新后)
settings.py:1814-1815 (数据源/偏好设置变更后)
  → overview.py:29-38 invalidate_overview_cache()
    → 清空模块级 _cache / _cache_key / _cache_ts
    → 下一个请求命中 TTL 检查失败 → 重新装配
```

#### 市场环境(Regime)

```text
daily_pipeline.py:669-700 (盘后定时任务)
  → regime_builder.compute_regime_incremental(repo, data_dir) [regime_builder.py:644]
    → 检测缺口 + stale 日 → run_regime_batch [regime_builder.py:452]
      → repo.get_enriched_range(start, end) [regime_builder.py:481]
      → _filter_excluded_symbols(ST 过滤) [regime_builder.py:496]
      → _aggregate_daily(df, index_pct_map) [regime_builder.py:148-316]
        → polars group_by("date") 向量化聚合
        → 逐日 classify_state(metrics) + _compute_subscores
      → 持久化 regime_path(data_dir) [regime_builder.py:508]
      → refresh_phase_labels(data_dir) [regime_builder.py:525]
  → invalidate_regime_cache() [regime.py:25]
```

### 状态机（如适用）

#### 市场情绪标签（Overview）

| 情绪分范围 | 标签 | 含义 |
|-----------|------|------|
| >= 70 | 强势 | 市场情绪高涨 |
| >= 55 | 偏暖 | 市场情绪较好 |
| >= 45 | 震荡 | 市场情绪中性 |
| >= 30 | 偏冷 | 市场情绪偏弱 |
| < 30 | 冰点 | 市场情绪低迷 |

阈值定义于 [market_overview_builder.py:540-549](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L540-L549)。

#### 市场环境离散状态（Regime）

| 状态 | 英文 key | 综合分范围 | 含义 |
|------|----------|-----------|------|
| 强势 | strong | >= 70 | 市场强势 |
| 偏强 | lean_strong | >= 55 | 市场偏强 |
| 震荡 | range | >= 45 | 市场震荡 |
| 偏弱 | lean_weak | >= 30 | 市场偏弱 |
| 弱势 | weak | < 30 | 市场弱势 |

阈值定义于 [regime_builder.py:37-42](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L37-L42)。

#### 情绪/环境评分差异说明

两个评分系统独立但阈值对齐：
- **Overview 情绪分**：6 维度(指数/赚钱/量能/投机/抗跌/主线)，面向单日实时总览，在 `market_overview_builder.py:531-549` 计算
- **Regime 综合分**：4 维度(赚钱/投机/抗跌/趋势)，面向多日时序分析，在 `regime_builder.py:63-112` 计算

设计取舍参见 [regime_builder.py:24-28](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L24-L28)。

## 关键数据结构

### API 契约

#### `GET /api/overview/market?as_of=YYYY-MM-DD`

响应: `OverviewMarket` 接口 [api.ts:460-496](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L460-L496)

```typescript
interface OverviewMarket {
  as_of: string | null                          // 数据日期
  quote_status: { enabled, running, quote_age_ms, is_trading_hours }
  indices: IndexQuote[]                         // 核心指数行情(上证/深证/创业板/科创50)
  breadth: { total, up, down, flat, up_pct, down_pct, avg_pct, median_pct, strong_up, strong_down }
  amount: { total, avg }                        // 成交额(亿)
  boards: { board, count, up, down, up_pct, amount }[]  // 板块分布
  limit: { limit_up, broken, failed, limit_down, max_boards, seal_rate, tiers, sealed_ready, fake_up, fake_down }
  distribution: { label, count, pct }[]         // 涨跌幅分桶(8 区间)
  trend: { above_ma5, above_ma20, above_ma60, above_ma5_pct, above_ma20_pct, above_ma60_pct, new_high, new_low }
  activity: { avg_turnover, high_turnover, high_vol_ratio, vol_ratio }
  radar: { key, label, value }[]               // 情绪雷达 6 维
  emotion: { score, label }                     // 综合情绪分 + 标签
  top_gainers: MarketSnapshotRow[]              // 涨幅榜 top 8
  top_losers: MarketSnapshotRow[]               // 跌幅榜 top 8
  turnover_leaders: MarketSnapshotRow[]          // 成交额榜 top 8
  active_leaders: MarketSnapshotRow[]            // 活跃换手榜 top 8
  concept_rank: { leading, lagging }            // 概念领涨/领跌 top 5
  industry_rank: { leading, lagging }           // 行业领涨/领跌 top 5
}
```

#### `GET /api/regime/*`

| 路由 | 参数 | 用途 |
|------|------|------|
| `/history` | start, end, limit | 历史环境时序(含状态/指标) |
| `/latest` | — | 最新一日环境(轻量) |
| `/states` | days | 状态分布统计(各状态天数/占比) |
| `/coverage` | — | 数据覆盖元信息 |
| `/recompute` | start, end | 手动触发重算 |
| `/phases` | start, end | 情绪周期阶段 |
| `/mainline` | kind, start, end, top | 市场主线排行 |
| `/mainline/recompute` | — | 手动重算主线 |

#### `GET /api/abnormal/overview`

| 参数 | 默认值 | 用途 |
|------|--------|------|
| min_closeness | 0.5 | 最小接近度过滤 |
| limit | 200 | 返回行数上限 |

### 存储结构

#### Regime 持久化

路径: `data/regime_history/part.parquet` [regime_builder.py:508-509](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L508-L509)

关键列: `date, state, score, limit_up, limit_down, broken_limit, max_consecutive, seal_rate, up_count, down_count, up_ratio, index_pct, above_ma20_pct, total_amount, avg_turnover, avg_pct, median_pct, strong_up_pct, strong_down_pct, profit_score, speculation_score, resilience_score, trend_score, phase, first_board_count, multi_board_count, max_ladder, promo_rate`

### 内存结构

#### Overview 缓存

```python
# overview.py:20-26
_CACHE_TTL = 5.0          # 秒
_cache: dict | None = None
_cache_key: str | None = None
_cache_ts: float = 0.0
_cache_lock = threading.Lock()  # 跨线程读写安全
```

#### Regime 缓存

```python
# regime.py:19-22
_CACHE_TTL = 5.0
_cache: dict | None = None
_cache_ts: float = 0.0
_cache_lock = threading.Lock()
```

#### TanStack Query 前端缓存

```typescript
// Dashboard.tsx:603-608
const overview = useQuery({
  queryKey: QK.overviewMarket(selectedDate),  // ['overview-market', asOf ?? 'latest']
  queryFn: () => api.overviewMarket(selectedDate),
  staleTime: 5_000,  // 5s 内不重复请求
  placeholderData: (prev) => prev,  // 保持上一帧数据
})
```

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

看板本身不提供 L1 配置扩展点。概念/行业维度排名依赖扩展数据(ext_data) Parquet — 用户可通过数据源的维度配置自定义概念/行业分类，详见 `docs/secondary-development.md` 扩展数据章节。

### L2 扩展（插槽/路由/注册替换）

看板页面是核心页面，不提供直接插槽。但以下 L2 插槽可间接作用于看板：

- `stock-preview.footer` — 个股预览弹窗底部扩展（`Dashboard.tsx:928-941` 使用 StockPreviewDialog）
- `watchlist.toolbar` — 不影响看板，但看板监控中心(MontiorWidget)与之共享数据源

### L3 修改（直接改源码）

如果必须修改核心源码，建议的最小改动方式：

1. **情绪雷达维度/权重调整**：修改 `market_overview_builder.py:531-549` 的 `radar` 列表，各维度 value 的 _score 调用参数可调
2. **情绪标签阈值调整**：修改 `market_overview_builder.py:540-549` 的阈值常量
3. **Regime 权重调整**：修改 `regime_builder.py:30-35` 的 `WEIGHTS` 字典
4. **Regime 状态阈值调整**：修改 `regime_builder.py:37-42` 的 `STATE_*` 常量
5. **Regime 子维度评分参数**：修改 `regime_builder.py:63-112` 的 `_compute_subscores` 中 _score 调用的 low/high 分位数
6. **涨跌幅分桶区间**：修改 `market_overview_builder.py:317-327` 的 `_pct_band_rows` 中 bands 列表
7. **前端视觉布局**：修改 `Dashboard.tsx` 中 `:818-926` 的 JSX 网格布局

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件(Parquet) | enriched 数据重建/同步 | 下一次 `_load_enriched_for_date` 读到新数据 |
| DuckDB 内存视图 | 数据同步后重建 | 影响所有依赖 DuckDB 的查询 |
| 后端 API TTL | `invalidate_overview_cache()` 清空 `_cache` | 下一个请求重新装配，5s 窗口内不再返回旧数据 |
| SSE/前端 | `quotes_updated` → `invalidateQueries(overview-market)` | 看板页面自动 refetch，保持实时 |
| 前端 TanStack | `depth_updated` → `invalidateQueries(overview-market)` | 封单修正后刷新，独立于行情更新 |

**写操作影响分析**：
- 每次行情数据更新(quote_service): 调用 `invalidate_overview_cache()` → 后端 5s 缓存清空 + SSE 推 `quotes_updated` → 前端 refetch
- 五档封单修正完成(depth_service): SSE 推 `depth_updated` → 前端单独失效 overview-market
- 数据同步/清除(data.py): `invalidate_overview_cache()` + 数据文件变更 → 重新装配时读到新数据
- 设置变更(settings.py): `invalidate_overview_cache()` → 可能影响数据源路由
- Regime 重算: `invalidate_regime_cache()` + 文件持久化 → 下次查询读到新数据

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_regime_builder.py` | 22 条：聚合、分类、子维度、状态标签、边界条件 |
| 单元测试 | `backend/tests/test_abnormal_moves.py` | 25 条：偏离值计算、接近度、阈值校验 |
| 单元测试 | `backend/tests/test_abnormal_intraday.py` | 5 条：盘中量价信号聚合 |
| 单元测试 | `backend/tests/test_ext_preset_dimension_values.py` | 维度值分割/解析 |
| 集成测试 | `backend/tests/test_review_push_mode.py` | 复盘推送依赖 overview emotion_label |
| 前端测试 | 无 | 待确认：当前无 Dashboard 专用前端测试 |

## 依赖关系

### 依赖的其他功能

- [Screener](file:///c:/Code/tick-stock-panel/.trae/docs/features/screener.md) — `ScreenerService._load_enriched_for_date()` 是 overview 的数据来源
- 扩展数据(ExtData) — 概念/行业维度排名需要 `ext_data/` 目录下的 Parquet 文件
- 五档行情(DepthService) — 涨跌停 sealed 修正依赖 `depth5.batch` 能力
- 实时行情(QuoteService) — 指数实时行情 + SSE 事件驱动缓存失效
- 市场阶段(MarketPhase) — regime 后处理：`refresh_phase_labels()` 调用 `classify_phase_series`
- 市场主线(MarketMainline) — 概念/行业涨停梯队聚合，与 regime 同开关
- 市场偏好(Preferences) — regime 自动计算开关 `pipeline_regime_enabled`，ST 过滤开关 `sentiment_exclude_st`

### 被依赖的功能

- 大盘复盘(Review) — 复用 `build_market_overview()` 获取 `emotion_label`，见 `test_review_push_mode.py`

## 常见问题与注意事项

### 金融口径

1. **`change_pct` 小数制**：enriched 数据中 `change_pct` 为小数制(如 0.03 表示 3%)，涨跌幅分桶 `_pct_band_rows` [market_overview_builder.py:317-327](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L317-L327) 以小数阈值判断
2. **`turnover_rate` 百分数**：enriched 数据中 `turnover_rate` 为百分数值(如 5.0 表示 5%)，与 `change_pct` 口径不同。高换手阈值 `>= 5` [market_overview_builder.py:469](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L469) 对应 5%
3. **指数行情双来源**：`_index_quotes` [market_overview_builder.py:87-120](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L87-L120) 优先实时 `quote_service.get_index_quotes()`，回退 `kline_index_daily` SQL 查询。指定日期(as_of)时强制回退数据库
4. **涨跌停 sealed 修正**：`DepthService` 过滤假涨停/假跌停 [market_overview_builder.py:439-453](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L439-L453)，需 Pro+ `depth5.batch` 能力。未开启时看板显示"降级/未修正"提示 [Dashboard.tsx:613-614](file:///c:/Code/tick-stock-panel/frontend/src/pages/Dashboard.tsx#L613-L614)
5. **真停牌过滤**：volume=0 且 change_pct=0 视为真停牌剔除 [market_overview_builder.py:410-415](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L410-L415)
6. **Regime ST 过滤**：默认剔除风险警示股，由 `sentiment_exclude_st` 偏好控制 [regime_builder.py:466-477](file:///c:/Code/tick-stock-panel/backend/app/services/regime_builder.py#L466-L477)

### 性能注意事项

1. **enriched 数据加载**：`_load_enriched_for_date` 使用 Polars 内存缓存，首次加载慢路径 scan_parquet 约 0.5-2s
2. **Regime 批算内存**：全量回填多日 enriched 内存峰值高，默认关闭(`pipeline_regime_enabled=False`)。需在数据页开启或手动触发
3. **API 缓存 TTL 5s**：避免高频请求重复装配，但行情更新后最长 5s 延迟
4. **前端 staleTime 5s**：与后端 TTL 对齐，避免无意义重复请求
5. **概念/行业维度排名**：依赖 `ExtConfigStore` 加载扩展数据 Parquet 文件，目录结构复杂时 I/O 开销大

### 安全注意事项

- 无直接安全风险。所有数据来自本地 Parquet 和行情服务，不涉及用户输入执行
- `overview-market` 缓存是只读计算，不涉及写操作权限

### 已知限制

- 无前端测试覆盖(Dashboard 专用)
- 概念/行业维度排名数据质量依赖 ext_data 配置，用户自定义维度可能不完整
- 实时行情模式(watchlist)下，看板大盘数据为盘后快照，仅自选股实时，需在页面顶部提示用户 [Dashboard.tsx:807-816](file:///c:/Code/tick-stock-panel/frontend/src/pages/Dashboard.tsx#L807-L816)
- Regime 的 4 维评分模型不包含 Overview 的"量能/主线"维度，两个评分系统不可直接比较