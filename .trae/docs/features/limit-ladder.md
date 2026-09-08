# 连板梯队 LimitUpLadder — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。
> 本文档只描述已实现代码；所有引用带 `路径:行号` 证据。不确定内容已标注「待确认」。

- **功能名**：连板梯队 LimitUpLadder（含连跌梯队，涨停/跌停双向对称）
- **建议文件名**：`features/limit-ladder.md`
- **本次检索范围**：
  - 前端：`frontend/src/pages/LimitUpLadder.tsx`、`router.tsx`、`components/Layout.tsx`、`components/SealedBadge.tsx`、`lib/api.ts`、`lib/queryKeys.ts`、`lib/useQuoteStream.ts`、`lib/storage.ts`、`pages/settings/Monitoring.tsx`
  - 后端：`backend/app/api/screener.py`、`services/screener.py`、`indicators/pipeline.py`、`price_limits.py`、`services/depth_service.py`、`services/preferences.py`、`api/settings.py`、`strategy/monitor_rules.py`、`strategy/monitor.py`、`api/monitor_rules.py`
  - 测试：`backend/tests/test_limit_ladder_one_word.py`、`test_price_limits.py`、`backtest/test_dependencies.py`
  - 关键词：`limit_ladder`、`limit-ladder`、`compute_limit_signals`、`DepthService`、`sealed`、`连板梯队`

## 功能概述

连板梯队（路由 `/limit-ladder`，菜单「连板梯队」）以**连板数/连跌数分组**展示 A 股当日涨停/跌停梯队，是情绪周期的核心视图。它以 enriched 窄表即时计算的涨跌停信号（[`compute_limit_signals`](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L683-L950)）为价格口径基础，叠加独立的「五档盘口 sealed」旁路（[`DepthService`](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L60)）修正真假封板，并通过 SSE `depth_updated` 事件实时刷新前端。涨停/跌停两个方向结构完全对称，由 `direction` 参数切换（[`screener.py:730`](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L726-L976)）。

一句话总结：**把「价格层面的涨/跌停 + 连板计数」与「盘口层面的真假封板」分层叠加，按板数聚合成梯队卡片，供短线情绪观测与封单监控**。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API | `backend/app/api/screener.py` | `GET /screener/limit-ladder` 端点（[L726-976](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L726-L976)）；一字板表达式 `_one_word_limit_expr`（[L58-71](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L58-L71)） |
| API | `backend/app/api/settings.py` | 五档监控开关/手动修正/轮询间隔偏好端点（[L1786-1830](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1786-L1830)） |
| 服务 | `backend/app/services/screener.py` | `ScreenerService`：enriched 数据加载（内存缓存→历史缓存→parquet 慢路径）与前一交易日连板数窄读（[L51-141](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L51-L141)） |
| 指标 | `backend/app/indicators/pipeline.py` | `compute_limit_signals`（[L683-949](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L683-L949)）与盘中版 `_compute_limit_signals_today`（[L2159](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L2159)）；盘后管道在 [L1422](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L1422) 调用 |
| 规则 | `backend/app/price_limits.py` | 板块/ST 涨跌停百分比规则与整数分算价函数（[L23-84](file:///c:/Code/tick-stock-panel/backend/app/price_limits.py#L23-L84)） |
| 旁路 | `backend/app/services/depth_service.py` | `DepthService`：五档盘口 sealed 修正（轮询线程/盘后定版/独立 parquet），[L207-482](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L207-L482) |
| 偏好 | `backend/app/services/preferences.py` | `get_limit_ladder_monitor_enabled`（[L553-555](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L553-L555)）、`get/set_depth_polling_interval`（[L558-567](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L558-L567)） |
| 监控 | `backend/app/strategy/monitor_rules.py` | 规则校验：`type=ladder`、`LADDER_METRICS`（[L32-40](file:///c:/Code/tick-stock-panel/backend/app/strategy/monitor_rules.py#L32-L40)、[L180-182](file:///c:/Code/tick-stock-panel/backend/app/strategy/monitor_rules.py#L180-L182)） |
| 监控 | `backend/app/strategy/monitor.py` | ladder 规则评估：`_sealed_vol` 封单量比较（[L1606-1666](file:///c:/Code/tick-stock-panel/backend/app/strategy/monitor.py#L1606-L1666)） |
| 监控 | `backend/app/api/monitor_rules.py` | ladder 规则状态/历史查询与 `_sealed_vol` 注入（[L462-626](file:///c:/Code/tick-stock-panel/backend/app/api/monitor_rules.py#L462-L626)） |
| 测试 | `backend/tests/test_limit_ladder_one_word.py` | `_one_word_limit_expr` 一字板判定（涨停/跌停两个用例） |
| 测试 | `backend/tests/test_price_limits.py` | 执行 `compute_limit_signals`（L182）与 `_compute_limit_signals_today`（L215） |
| 测试 | `backend/tests/backtest/test_dependencies.py` | `compute_limit_signals` 依赖 `raw_low` 的回归测试（[L51-74](file:///c:/Code/tick-stock-panel/backend/tests/backtest/test_dependencies.py#L51-L74)） |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/LimitUpLadder.tsx` | 主页面：方向/状态/板块过滤、梯队卡片、封单监控菜单、ext 字段配置、降级标识（主组件 [L1458](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L1458)） |
| 路由 | `frontend/src/router.tsx` | `/limit-ladder` → `LimitUpLadder`（[L143](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx#L143)），lazy 加载（[L33](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx#L33)），核心路由白名单（[L60](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx#L60)） |
| 组件 | `frontend/src/components/Layout.tsx` | 导航菜单项「连板梯队」（[L91](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L91)） |
| 组件 | `frontend/src/components/SealedBadge.tsx` | 修正/降级徽章 + 弹窗（[L45-166](file:///c:/Code/tick-stock-panel/frontend/src/components/SealedBadge.tsx#L45-L166)） |
| API | `frontend/src/lib/api.ts` | `LimitLadderStock/Tier/Result` 类型（[L1075-1114](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1075-L1114)）、`limitLadder()`（[L2586-2595](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2586-L2595)）、`updateLimitLadderMonitor`/`runLimitLadderFix`（[L2211-2219](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2211-L2219)） |
| 缓存 | `frontend/src/lib/queryKeys.ts` | `QK.limitLadder`（[L51](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L51)）；`SSE_INVALIDATE_PREFIXES` 含 `'limit-ladder'`（[L141](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L141)） |
| SSE | `frontend/src/lib/useQuoteStream.ts` | `depth_updated` 事件失效 `['limit-ladder']` + `['overview-market']`（[L192-197](file:///c:/Code/tick-stock-panel/frontend/src/lib/useQuoteStream.ts#L192-L197)） |
| 存储 | `frontend/src/lib/storage.ts` | localStorage 键：板块过滤/方向/封单模式/ext 字段/显示开关（[L90-102](file:///c:/Code/tick-stock-panel/frontend/src/lib/storage.ts#L90-L102)） |
| 设置 | `frontend/src/pages/settings/Monitoring.tsx` | 「连板梯队降级修正」设置卡（[L516-557](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L516-L557)），修正后失效 `['limit-ladder']`（[L307-315](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L307-L315)） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 数据 | `data/depth5/date={date}/part.parquet` | 五档 sealed 独立落盘（schema 见「存储结构」，写入见 [depth_service.py:358-396](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L358-L396)） |
| 数据 | `data/enriched/date={date}/part.parquet` | enriched 窄表（14 列存储，涨跌停信号即时计算，见 [screener.py:84-103](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L84-L103)） |
| 文档 | `.trae/docs/architecture.md` | 行情总览索引含 `/limit-ladder`（[L179](file:///c:/Code/tick-stock-panel/.trae/docs/architecture.md#L179)）；常驻服务含 `DepthService 盘中轮询`（[L239](file:///c:/Code/tick-stock-panel/.trae/docs/architecture.md#L239)） |

## 业务逻辑

### 核心流程

```text
[前端 useQuery(limitLadder)] → [GET /screener/limit-ladder?as_of&direction&ext_columns]
  → 加载当日 enriched（内存缓存/历史缓存/parquet+即时计算）
  → 双方向原始涨跌停计数
  → 前一交易日连板数窄读（load_prior_consecutive）
  → 计算 status + boards（is_limit / is_broken / is_failed 三分支）
  → sealed 旁路叠加（假涨停→降级 broken；附 sealed_status/sealed_vol）
  → 一字板判定（is_one_word）
  → ext_columns 动态 JOIN 扩展数据
  → 排序 + 按 boards 分组为 tiers
  → 返回 { tiers, counts, counts_raw, sealed_ready, sealed_age, sealed_counts* }
  → 前端过滤/排序/渲染；SSE depth_updated 增量刷新
```

**关键决策点：**

1. **状态三分支**（[screener.py:818-828](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L818-L828)），涨跌停结构对称：
   - `is_limit`（当日有涨停/跌停信号）→ `status=main`，`boards=consec`（当日连续数）
   - `is_broken`（炸板/翘板信号）→ `status=broken/recovery`，`boards=prev_consec+1`
   - `is_failed`（`~is_limit & ~is_broken & prev_consec>0`，昨板今日未连）→ `status=failed`，`boards=prev_consec+1`
   - 过滤条件：`status.is_not_null() & boards>0`（[L830](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L830)）

2. **sealed 降级规则**（[screener.py:835-896](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L835-L896)）：仅对 `status=main` 的票生效；`_sealed==False`（假封板，收盘价=涨跌停价但盘口对面有量）→ 降级为 `broken/recovery`；`_sealed==True` → `sealed_status='real'` 并带 `sealed_vol`；`_sealed is null` → `sealed_status='pending'` 保持原状。**不改写 `signal_limit_up/down`**（价格口径永久保留）。

3. **一字板判定**（[screener.py:58-71](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L58-L71)）：`status==main & close>0 & open==high==low==close`。

4. **前一交易日连板数**（[screener.py:105-141](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L105-L141)）：`as_of-1..9` 天向前找第一个存在的日分区，谓词下推只读 `[symbol, consec_col]` 两列，替代旧的全量指标重算循环。

### 数据流

1. **输入来源**：
   - 用户在前端切换日期/方向/过滤/外字段（[LimitUpLadder.tsx:1459-1544](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L1459-L1544)）触发 `GET /api/screener/limit-ladder`。
   - 底层数据来自 enriched 窄表（盘后管道写入）与 instruments 维表（`limit_up/limit_down/as_of` 权威涨跌停价）。
   - sealed 数据来自 `DepthService` 盘中轮询线程（读 enriched 内存缓存筛选涨跌停名单 → `tf.depth.batch` → 判 sealed → 更新内存缓存）。

2. **处理过程**：
   - `compute_limit_signals`：按 `needed` 裁剪 → JOIN instruments（ST 标记/流通股本/权威涨跌停价）→ 计算 `_prev_raw_close`（除权日用前复权昨收，否则 `raw_close.shift(1)`）→ `polars_price_limit_pct` + `polars_limit_price` 整数算术算理论涨跌停价 → 与权威 `limit_up/limit_down` 按 `as_of` 匹配择优 → 生成 5 信号 + 连板计数（[pipeline.py:763-947](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L763-L947)）。
   - `limit_ladder` 端点：方向列映射 → 加载 enriched → 双方向计数 → sealed 修正 → status/boards → sealed 叠加 → 一字板 → ext JOIN → 分组（[screener.py:745-960](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L745-L960)）。

3. **输出去向**：
   - API 返回 `tiers`（按 boards 降序分组的股票列表）与各类计数/就绪状态（[screener.py:962-976](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L962-L976)）。
   - 前端渲染 `TierGroup`/`StockCard`，封单监控菜单创建 `type=ladder` 监控规则（[LimitUpLadder.tsx:462-490](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L462-L490)），由监控引擎评估封单量阈值告警。

### 调用链

```text
Layout 菜单(components/Layout.tsx:91)
  → 路由 /limit-ladder(router.tsx:143)
  → LimitUpLadder 页面(useQuery, LimitUpLadder.tsx:1539-1546)
  → api.limitLadder()(lib/api.ts:2586) → GET /api/screener/limit-ladder
  → limit_ladder 端点(api/screener.py:726)
  → ScreenerService._load_enriched_for_date(services/screener.py:51)
  → compute_limit_signals(indicators/pipeline.py:683) + price_limits.py 规则
  → load_prior_consecutive(services/screener.py:105)
  → DepthService.get_sealed_map/is_sealed_ready(services/depth_service.py:409/470)   ← 旁路 sealed 修正
  → SSE depth_updated(useQuoteStream.ts:192) → invalidate ['limit-ladder'] → 前端刷新
```

### 状态机

- **梯队状态**（涨/跌停对称）：

| 状态 | up 含义 | down 含义 | 判定 |
|------|---------|-----------|------|
| `limit_up`/`limit_down` | 涨停 | 跌停 | 当日 signal 命中，`boards=consec` |
| `broken`/`recovery` | 炸板（摸板未封） | 翘板（触跌停回升收阳） | 当日 broken 信号，`boards=prev+1` |
| `failed` | 断板（晋级失败） | 止跌 | 昨有连板今日未连未炸，`boards=prev+1` |
| sealed 附加：`real`（真封板）/`fake`（假封板→降级）/`pending`（待确认）/`null`（降级/无能力） | | | |

- 方向切换（[LimitUpLadder.tsx:1486-1497](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L1486-L1497)）：切到 down 时重置状态筛选为该方向默认集，避免涨跌状态键错配。

## 关键数据结构

### API 契约

请求 `GET /api/screener/limit-ladder`（[screener.py:726-732](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L726-L732)）：

| 参数 | 类型 | 说明 |
|------|------|------|
| `as_of` | date | 目标交易日，缺省用 `ScreenerService.latest_date()`（[screener.py:761](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L761)） |
| `direction` | `"up"\|"down"` | 默认 `up`（[L730](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L730)） |
| `ext_columns` | string | 逗号分隔 `config_id.field_name`，动态 JOIN 扩展数据（[L731](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L731)） |

响应 `LimitLadderResult`（[api.ts:1097-1114](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1097-L1114)）：

```jsonc
{
  "as_of": "2026-09-08",
  "tiers": [{ "boards": 3, "count": 2, "stocks": [{ "symbol": "...", "name": "...",
    "close": 12.5, "change_pct": 0.10,            // 小数制（实时源口径）
    "boards": 3, "status": "limit_up",             // limit_up|broken|failed|limit_down|recovery
    "consecutive_limit_ups": 3,                    // 或 consecutive_limit_downs
    "sealed_status": "real",                        // real|fake|pending|null
    "sealed_vol": 123456,                           // 封单量（手），仅真封板有值
    "is_one_word": true                             // 一字板
  }] }],
  "counts": { "up": 42, "down": 3 },               // sealed 修正后
  "counts_raw": { "up": 45, "down": 3 },            // 修正前
  "sealed_ready": true, "sealed_age": 32.0,
  "sealed_counts": { "real": 38, "fake": 3, "pending": 1 },
  "sealed_counts_up": {...}, "sealed_counts_down": {...}
}
```

说明：`change_pct`/`turnover_rate` 实时源为小数制；enriched 存储列 `turnover_rate` 为百分数值。`counts.up/down` 恒为双方向（前端同时展示两方向计数），不受 `direction` 影响（[screener.py:770-789](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L770-L789)）。

### 存储结构

- **enriched 窄表**（`data/enriched/date={date}/part.parquet`，14 列）：`symbol, date, open, high, low, close, volume, amount, raw_close, raw_high, raw_low, turnover_rate, consecutive_limit_ups, consecutive_limit_downs`（存储列；涨跌停信号为即时计算，不落盘）。读取列清单见 [screener.py:159-160](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L159-L160)。
- **depth5 parquet**（`data/depth5/date={date}/part.parquet`，显式 schema）：`symbol, sealed_up(bool), sealed_down(bool), ask1_vol(int64), bid1_vol(int64), status(utf8), fetched_at(float64)`（[depth_service.py:379-387](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L379-L387)）。原子写：临时文件 + `os.replace`（[L391-394](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L391-L394)）。
- **localStorage**（[storage.ts:90-102](file:///c:/Code/tick-stock-panel/frontend/src/lib/storage.ts#L90-L102)）：`limit-ladder-board-filter`（板块/状态过滤）、`limit-ladder-ext-fields`、`limit-ladder-show-ext`、`limit-ladder-direction`、`limit-ladder-seal-mode`。
- **查询键**：`['limit-ladder', asOf]`（[queryKeys.ts:51](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L51)）；页面实际用拍平 key `['limit-ladder', asOf, extColumnsParam, direction]`（[LimitUpLadder.tsx:1543](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L1543)），保证 `key[0]==='limit-ladder'` 才能被 SSE 前缀命中。
- **偏好键**：`limit_ladder_monitor_enabled`（[preferences.py:553-555](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L553-L555)）、`depth_polling_interval`（[L558-567](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L558-L567)）、`depth_finalize_time`（默认 15:02，[L570-573](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L570-L573)）。

### 内存结构

- `DepthService._sealed_cache: dict[str, dict]`：`{symbol: {sealed_up, sealed_down, ask1_vol, bid1_vol, status, fetched_ts}}`；`_sealed_ready/_sealed_date/_sealed_fetched_ts` 记录就绪状态与数据对应交易日（[depth_service.py:74-81](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L74-L81)）。锁：`_lock` 护内存缓存，`_fetch_lock` 串行化 fetch+seal（[L64-68](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L64-L68)）。
- `ScreenerService._history_cache`：进程级历史窗口缓存，TTL 120s（[screener.py:23-24](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L23-L24)）。
- 前端内存：`filterKeys`/`extFields`/`direction`/`sealMode` 等 React state，持久化到 localStorage。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **外字段注入**：通过请求参数 `ext_columns=config_id.field_name` 动态 JOIN 扩展数据（概念/行业等），前端在「齿轮弹窗」配置字段、显示开关与统计（[LimitUpLadder.tsx:1380-1454](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L1380-L1454)、[screener.py:900-934](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L900-L934)）。JOIN 优先走 DuckDB view，失败回退 parquet glob（[L911-934](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py#L911-L934)）。
- **监控规则**：卡片齿轮可创建 `type=ladder` 封单监控规则（`sealed_vol`/`sealed_amount` 阈值，单位手/万手/元/万元/亿元），走现有监控规则体系（[LimitUpLadder.tsx:397-500](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L397-L500)、[monitor_rules.py:180-182](file:///c:/Code/tick-stock-panel/backend/app/strategy/monitor_rules.py#L180-L182)）。

### L2 扩展（插槽/路由/注册替换）

- 该功能本身不暴露额外前端插槽；前端已有插槽 `layout.navigation.extra` 可用于在其菜单附近追加导航（见 `docs/secondary-development.md`）。
- 数据源能力通过 `CAPABILITY_REGISTRY` 的 `depth5.batch` 能力路由接入 `DepthService`（`_has_capability` 检查，[depth_service.py:155](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L155)）；无能力时前端降级显示（`SealedBadge` 降级原因，[SealedBadge.tsx:72-75](file:///c:/Code/tick-stock-panel/frontend/src/components/SealedBadge.tsx#L72-L75)）。

### L3 修改（直接改源码）

- **调整涨跌停规则**：改 `backend/app/price_limits.py`（板块/ST 百分比、整数算价），需同步 `polars_*` 与 `numpy_*` 两套实现，并跑 `test_price_limits.py`。
- **调整信号口径**：改 `compute_limit_signals` 时注意：涨跌停判定用**原始价** `raw_close/raw_high/raw_low`，前收盘用 `_prev_raw_close`（除权日切前复权昨收）；临时列（`_` 前缀）与 instruments 列计算完必须清理，不能落入 enriched（[pipeline.py:930-947](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L930-L947)）。
- **调整 sealed 判定**：改 `DepthService._fetch_and_seal_locked` 的 `sealed_up=(ask1==0)` / `sealed_down=(bid1==0)`（[depth_service.py:266-269](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L266-L269)），注意「只读 enriched、不写回」的旁路架构约束。

### 缓存失效影响

该功能**无写路径**（只读聚合），但依赖多级缓存，任何上游数据变动都需按链路失效：

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件缓存 | depth5 parquet 原子写（临时文件+`os.replace`）；enriched parquet 由盘后管道重写 | 影响所有读该分区日期的请求；`ScreenerService.clear_history_cache()` 需在清数后调用（[screener.py:43-49](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L43-L49)） |
| 内存缓存 | `DepthService._sealed_cache`（盘中轮询每轮覆盖，[L278-280](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L278-L280)）；`_history_cache` TTL 120s 自动过期；repo enriched 最新日缓存随盘后管道刷新 | 影响 `/limit-ladder` 与看板总览 |
| SSE/前端 | `depth_updated` 事件 → `invalidateQueries({ queryKey: ['limit-ladder'] })`（[useQuoteStream.ts:192-197](file:///c:/Code/tick-stock-panel/frontend/src/lib/useQuoteStream.ts#L192-L197)）；`quotes_updated` 按 `sseRefreshPages['limit-ladder']` 开关过滤（[L138-155](file:///c:/Code/tick-stock-panel/frontend/src/lib/useQuoteStream.ts#L138-L155)）；手动修正后前端也失效 `['limit-ladder']`（[Monitoring.tsx:312](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L312)） | 连板梯队页面与看板封单数据 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_limit_ladder_one_word.py` | 一字板：涨停 main 四价相等→True；OHLC 不等/非 main/broken→False；跌停方向 support |
| 单元测试 | `backend/tests/test_price_limits.py` | 执行 `compute_limit_signals`（L182）与 `_compute_limit_signals_today`（L215）的涨跌停信号正确性 |
| 回归测试 | `backend/tests/backtest/test_dependencies.py` | `compute_limit_signals` 依赖 `raw_low` 的输入列约束（L51-74） |

## 依赖关系

### 依赖的其他功能

- **[enriched 窄表 + 指标管道](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L683)**：连板梯队的数据基座，`consecutive_limit_ups/downs` 为存储列，其余信号即时计算。管道在盘后 [L1422](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L1422) 与盘中 [L2108](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L2108) 两处调用。
- **instruments 维表**：提供 `limit_up/limit_down/as_of` 权威涨跌停价、ST 标记、流通股本（换手率用）。
- **数据源能力路由**：`depth5.batch` 能力（`CAPABILITY_REGISTRY`）驱动 `DepthService`，无能力→前端降级。
- **监控规则引擎**：`type=ladder` 封单监控依赖 `monitor.py` 的 `_sealed_vol` 注入评估。
- **SSE 行情流**：`depth_updated` 事件驱动前端实时刷新。

### 被依赖的功能

- **看板/行情总览**：`/limit-ladder` 与看板共用 `SealedBadge` 与 sealed 数据；`run_limit_ladder_fix` 修正后同时清理看板总览缓存（[settings.py:1811-1814](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1811-L1814)）。
- **`_one_word_limit_expr`**：测试直接 import 该函数（`test_limit_ladder_one_word.py:3`）。

## 常见问题与注意事项

- **口径红线**：涨跌停判定用原始价（`raw_close/raw_high/raw_low`），前收盘基准在除权日用前复权昨收、否则用 `raw_close.shift(1)`（[pipeline.py:760-775](file:///c:/Code/tick-stock-panel/backend/app/indicators/pipeline.py#L760-L775)）；「数值<1 乘 100」启发式禁止使用。
- **sealed 是旁路不是替代**：`signal_limit_up` 永远是「价格涨停」，sealed 只是叠加判定层（[depth_service.py:1-8](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L1-L8)）；假涨停降级只发生在此功能视图内，不污染 enriched。
- **盘中/盘后差异**：盘中 sealed 为轮询快照（`sealed_age` 为秒数，`sealed_ready=false` 时前端降级显示）；盘后 `depth_finalize` 定版写 parquet（`age=None`）。历史日期一律降级（快照不可获取，[SealedBadge.tsx:74](file:///c:/Code/tick-stock-panel/frontend/src/components/SealedBadge.tsx#L74)）。
- **`pending` 计数口径**：前端 `SealedDirBlock` 的 pending 从原始总数反推（`rawTotal-real-fake`），因后端 `sealed_counts.pending` 含另一方向票不可直接用（[SealedBadge.tsx:19-20](file:///c:/Code/tick-stock-panel/frontend/src/components/SealedBadge.tsx#L19-L20)）。
- **查询 key 必须拍平**：嵌套数组 key 会导致 SSE 前缀失效永远失配（[LimitUpLadder.tsx:1540-1543](file:///c:/Code/tick-stock-panel/frontend/src/pages/LimitUpLadder.tsx#L1540-L1543)）。
- **窄读优化**：`load_prior_consecutive` 只读前一交易日 `[symbol, consec_col]` 两列，避免旧实现最坏 9 次全市场指标重算（[screener.py:105-110](file:///c:/Code/tick-stock-panel/backend/app/services/screener.py#L105-L110)）。
- **五档轮询节流三层防护**：套餐范围 clamp → 限速安全 clamp（`rpm*0.8`）→ 系统接管通知 toast（[depth_service.py:535-569](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L535-L569)）；非连续竞价时段跳过轮询，避免集合竞价盘口覆盖 11:30 定格值（[L492-495](file:///c:/Code/tick-stock-panel/backend/app/services/depth_service.py#L492-L495)）。
- **能力缺失行为**：无 `DEPTH5_BATCH` 能力时轮询线程不启动、手动修正返回 `403 CapabilityDenied`（[settings.py:1803-1805](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1803-L1805)），前端 fail-closed 显示降级标识，不静默返回错误金融结果。
- **待确认**：`docs/secondary-development.md` 中未检索到本功能的专项索引节（关键词 `limit-ladder/ladder/连板梯队/五档/深度修正` 均无匹配）；如后续在该文档补充 L2 扩展描述，需与本文件保持一致。
