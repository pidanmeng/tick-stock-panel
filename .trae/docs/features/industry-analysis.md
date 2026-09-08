---
title: 行业分析 — 功能文档
description: TSP 行业分析功能的完整参考。涵盖前端页面 IndustryAnalysis、后端 Ext Data 维度 API、SectorMonitor 监控服务、MarketOverview 行业排名与 RPS 轮动矩阵。
---

# 行业分析 IndustryAnalysis — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

行业分析功能为用户提供 A 股行业/板块维度的聚合分析视图：基于扩展数据（Ext Data）的行业分类配置，将全市场个股归入行业分组，通过 6 因子 LeaderScore 筛选龙头、5 因子 HeatScore 评估行业热度、2 因子 RiskScore 识别风险，以热力图/排行/轮动矩阵等形式呈现。该功能同时为大盘看板的 `industry_rank`/`concept_rank` 与监控规则引擎的 SectorMonitor 提供行业/概念维度后端支持。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| Ext Data API | `backend/app/api/ext_data.py` | 扩展数据 CRUD、预设数据获取、维度成员查询、维度盘中估算 |
| Overview API | `backend/app/api/overview.py` | 市场总览（含 `industry_rank`/`concept_rank`），5s TTL 缓存 |
| RPS API | `backend/app/api/rps.py` | 涨幅轮动矩阵与 AI 流式分析（kind=industry/concept） |
| Data API | `backend/app/api/data.py` | 数据管理（清除/刷新时触发 overview 缓存失效） |
| 行业预设 | `backend/app/services/ext_presets.py` | 内置同花顺行业/概念预设，启动创建 config.json，手动触发数据获取 |
| 市场总览器 | `backend/app/services/market_overview_builder.py` | 装配大盘总览（指数/情绪/涨跌分布/行业/概念排名） |
| 板块监控器 | `backend/app/services/sector_monitor.py` | 行业/概念实时监控，为监控规则引擎提供板块快照 |
| RPS 轮动 | `backend/app/services/rps_rotation.py` | 构建涨幅轮动矩阵，120s 后端缓存 |
| 行情服务 | `backend/app/services/quote_service.py` | 行情广播时触发 overview 缓存失效 |
| 监控规则引擎 | `backend/app/strategy/monitor.py` | 消费 SectorMonitorService.build_snapshots 的规则引擎 |
| 应用入口 | `backend/app/main.py` | 实例化 SectorMonitorService（行 321） |
| 设置 API | `backend/app/api/settings.py` | 设置变更时触发 overview 缓存失效（行 1814-1815） |
| 测试 | `backend/tests/test_sector_monitor.py` | 板块监控服务 6 个测试用例 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 行业分析页面 | `frontend/src/pages/IndustryAnalysis.tsx` | 主页面（894 行），路线 `/industry-analysis`，含 HeroPanel/MarketPulse/IndustryRail/IndustryFocus/LeaderStage 子组件 |
| RPS 轮动对话框 | `frontend/src/components/RpsRotationDialog.tsx` | 涨幅轮动矩阵对话框，支持 concept/industry 切换与行业层级选择 |
| 分析共享组件 | `frontend/src/components/analysis-shared.tsx` | AnalysisConfigDialog 配置对话框、AnalysisFieldConfig 接口 |
| 分析适配器 | `frontend/src/lib/analysis-adapter.ts` | 维度解析（per_stock/per_dimension 双结构自动检测）、行业分组聚合 |
| API 客户端 | `frontend/src/lib/api.ts` | 所有后端 API 调用（extDataList/extDataRows/marketSnapshot/overviewMarket/rpsRotation 等） |
| Query Keys | `frontend/src/lib/queryKeys.ts` | React Query 键（QK.extData/QK.extDataRows/QK.marketSnapshot）与 SSE 失效前缀 |
| 本地存储 | `frontend/src/lib/storage.ts` | `industryAnalysisConfig` 键持久化字段配置（行 151） |
| 路由 | `frontend/src/router.tsx` | `/industry-analysis` 懒加载路由（行 29,130） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 扩展数据配置 | `backend/app/services/ext_presets.py` | 内置预设 `ext_hy_ths`（行业）和 `ext_gn_ths`（概念）的定义 |
| 数据存储 | `data/ext/{config_id}/` | 扩展数据 JSON 文件目录（含 config.json 与 rows.json） |

## 业务逻辑

### 核心流程 — 行业分析页面

```text
[页面加载] → ExtData 配置列表 → ExtData 行数据 → MarketSnapshot 行情快照
→ resolveDimension(检测 per_stock/per_dimension 结构) + pickDimensionField(自动选择维度字段)
→ groupByIndustryLevel("-"分隔的 "一级-二级-三级" → 按 level 参数聚合)
→ calcIndustryStat(6 因子 Leader + 5 因子 Heat + 2 因子 Risk)
→ sort(heat/avgPct/leader/amount/down) + filter(search)
→ 子组件渲染 (HeroPanel/MarketPulse/热力图/IndustryRail/IndustryFocus)
    ↕ [RpsRotationDialog] → /api/rps/rotation?kind=industry&level=N → 轮动矩阵
    ↕ [StockPreviewDialog] → /api/screener/market-snapshot → 弹出标的预览
```

#### LeaderScore 六因子评分（IndustryAnalysis.tsx:130-157）

每一只被勾选的行业中，计算每只成分股的加权总分：

| 因子 | 权重 | 计算方式 |
|------|------|----------|
| momentum | 35% | `(涨幅排名 / 总数)` 归一化，反映相对强度 |
| turnover | 22% | 换手率归一化，反映交易活跃度 |
| amount | 18% | 成交额归一化，反映资金关注度 |
| cap | 15% | 流通市值归一化，反映权重贡献 |
| volume | 7% | 成交量归一化（辅助因子） |
| boards | 3% | 涨停板额外加分（涨停 +1、连板 +2），反映情绪溢价 |

未在 MarketMap 中出现的股票（停牌等）跳过评分，`LeaderStage` 组件展示全市场前 6 名领涨个股。

#### HeatScore 五因子热度评分（IndustryAnalysis.tsx:174-227）

| 因子 | 权重 | 含义 |
|------|------|------|
| avgPart | 38% | 个股平均涨幅归一化，反映行业整体强弱 |
| upPart | 20% | 上涨家数占比，反映行业广度 |
| strongScore | 16% | 强于大盘（跑赢指数）的个股占比 |
| amountScore | 12% | 行业总成交额占比归一化，反映资金集中度 |
| leaderPart | 14% | 龙头股（LeaderScore 前 10%）的涨幅贡献 |

#### RiskScore 风险评分（IndustryAnalysis.tsx:213-227）

| 因子 | 权重 | 含义 |
|------|------|------|
| negativeAvgPct | 55% | 下跌个股的平均跌幅（越大越危险） |
| weakCount | 45% | 跌幅 >3% 的个股数量归一化 |

#### 内置行业预设（IndustryAnalysis.tsx:303-315）

当 `activeConfig.id === 'ext_hy_ths'` 且 `total === 0` 时，页面展示 `PresetFetchState` 按钮；用户点击后调用 `api.extDataPresetFetch('ext_hy_ths')`，成功后 `invalidateQueries([QK.extData, QK.extDataRows])` 自动重载。

### 核心流程 — 后端服务

#### 市场总览行业排名（market_overview_builder.py:240-302,520）

`build_market_overview` 调用 `_dimension_rank(rows, repo, "industry", level=2)`，按二级行业聚合个股涨跌幅排名；同时计算 `concept_rank`（无 level 参数）。结果经 5s TTL 缓存从 `/api/overview/market` 输出。该排名被 Dashboard / 大盘看板消费，非 IndustryAnalysis 页面直接使用。

#### 实时板块监控（sector_monitor.py:79-121）

`MonitorRuleEngine`（strategy/monitor.py:811）调用 `SectorMonitorService.build_snapshots()`，为每个行业/概念维度构建快照（`_dimension_snapshot` 行 295-325），条件为 `total_count >= 5 AND coverage_ratio >= 0.8`。快照包含 `window_changes`（滑动窗口涨跌幅，90s 容忍阈值 `_window_change` 行 327-342）。每日首次调用自动 `_reset_history_for_day`（行 344-349）。

#### RPS 轮动矩阵（rps_rotation.py:111-208）

`build_rps_rotation(repo, days, kind, level)` 按维度聚合个股涨幅排名：每列（交易日）各自降序排列。缓存 key 为 `f"{kind}|{level}|{latest.isoformat()}"`，TTL 120s。行业时按 `level` 参数聚合 `"一级-二级-三级"` 的指定层级（行 169-174）。支持 `kind="industry"` 和 `kind="concept"`。

### 数据流

#### 主路径：行业分析页面加载

1. **输入来源**：
   - `GET /api/ext-data`（ext_data.py:325-336）→ 扩展数据配置列表
   - `GET /api/ext-data/{id}/rows?limit=12000`（ext_data.py:416-458）→ 行业分类行数据
   - `GET /api/screener/market-snapshot`（api.ts:2538）→ 全市场个股行情快照
   - 本地存储 `industryAnalysisConfig`（storage.ts:151）→ 持久化的字段配置

2. **处理过程**：
   - `resolveDimension()`（analysis-adapter.ts:236-289）：自动检测数据结构类型（per_stock: 每行一个股票，"一级-二级-三级"格式；per_dimension: 每行一个维度含 constituents 列表），选出维度字段
   - `pickDimensionField()`（analysis-adapter.ts:88-104）：按优先级匹配候选字段名，回退到首列非数值列
   - `groupByIndustryLevel()`（IndustryAnalysis.tsx:249-267）：以 `"-"` 分隔三级名称，按 fieldConfig.hierarchyLevel 聚合（默认 2 级）；`industryLevelName()` 取第 N 段
   - `calcIndustryStat()`（IndustryAnalysis.tsx:174-227）：逐行业计算热度/风险/龙头评分
   - `statSort()`（IndustryAnalysis.tsx:229-240）：按 heat/avgPct/leader/amount/down 排序

3. **输出去向**：
   - HeroPanel 展示领涨/领跌/活跃行业与广度（IndustryAnalysis.tsx:448）
   - MarketPulse 展示 top 10 领涨/领跌排行（IndustryAnalysis.tsx:450-457）
   - DimensionHeatmap 展示行业热力图（IndustryAnalysis.tsx:460-468）
   - IndustryRail + IndustryFocus 行业列表与聚焦面板（IndustryAnalysis.tsx:471-481）
   - LeaderStage 展示全市场龙头股排行

#### 旁路：内置预设数据获取

- 用户点击"获取行业数据" → `fetchMutation` 调用 `POST /api/ext-data/presets/ext_hy_ths/fetch`（ext_data.py:339-357）
- 后端 `fetch_preset`（ext_presets.py:261-281）请求同花顺 API → `_flatten_industry_rows`（ext_presets.py:145-164）将 JSON `industries` 数组拼接为 `"-"` 分隔字符串 → 写入 rows.json
- 前端 `invalidateQueries` 触发重载

#### 旁路：RPS 轮动分析

- 用户点击"涨幅RPS轮动分析"按钮 → `RpsRotationDialog`（kind="industry"）
- 对话框请求 `GET /api/rps/rotation?days=N&kind=industry&level=LV`（rps.py:18-32）
- 后端 `build_rps_rotation`（rps_rotation.py:111-208）按指定层级聚合行业涨幅矩阵
- 可选："AI 分析"按钮 → `POST /api/rps/rotation-analyze`（rps.py:43-73）→ NDJSON 流式返回

### 调用链

#### 行业分析主页面

```text
前端路由 router.tsx:29,130
→ IndustryAnalysis.tsx:271 page component
  → api.extDataList() [api.ts:2889] → GET /api/ext-data [ext_data.py:325]
  → api.extDataRows(id, {limit: 12000}) [api.ts:2892] → GET /api/ext-data/{id}/rows [ext_data.py:416]
  → api.marketSnapshot() [api.ts:2538] → GET /api/screener/market-snapshot
  → analysis-adapter.ts:236 resolveDimension()
  → analysis-adapter.ts:88 pickDimensionField()
  → IndustryAnalysis.tsx:249 groupByIndustryLevel()
  → IndustryAnalysis.tsx:174 calcIndustryStat()
  → sub-components (hero/marketPulse/heatmap/rail/focus)
```

#### 市场总览行业排名

```text
GET /api/overview/market [overview.py:356] (5s TTL 缓存行 364)
→ overview.py:341 _build_overview → market_overview_builder.py:356 build_market_overview
  → market_overview_builder.py:240 _dimension_rank(level=2) [行 520]
  → ext_data.py 读取 ext rows + KlineRepository 获取个股涨跌幅
  → outputs: industry_rank / concept_rank / radar / emotion
→ 缓存失效:
  data.py:696 (数据清除)
  data.py:873 (强制刷新)
  quote_service.py:422 (行情广播时)
  settings.py:1815 (设置变更时)
```

#### 实时板块监控

```text
main.py:321 SectorMonitorService(repo) 启动
→ strategy/monitor.py:811 MonitorRuleEngine.evaluate()
  → sector_monitor.py:79 build_snapshots(targets, windows)
    → sector_monitor.py:252 _industry_paths() 解析三级路径
    → sector_monitor.py:295 _dimension_snapshot() (coverage≥0.8, count≥5)
    → sector_monitor.py:327 _window_change() (90s tolerance)
→ outputs: sector snapshots with window_changes
```

#### RPS 轮动矩阵

```text
RpsRotationDialog.tsx:50 (kind="industry", level 默认 2)
→ api.rpsRotation(days, kind, level) [api.ts:2543]
  → GET /api/rps/rotation [rps.py:18]
    → rps_rotation.py:111 build_rps_rotation()
      → rps_rotation.py:54 _load_concept_map_df() (共用于 industry, 600s 缓存)
      → polars split/aggregate by level (行 169-174)
      → 120s cache [key: f"{kind}|{level}|{date}"](行 138)
→ RpsRotationDialog 虚拟滚动渲染矩阵
→ 可选: POST /api/rps/rotation-analyze → concept_rotation_analyzer → NDJSON streaming
```

### 状态机

行业分析页面的状态取决于数据加载阶段：

```text
configsQuery loading → 全页居中 spinner（行 382-384）
  ↓
activeConfig 为空 → PresetFetchState（行 388-411）
  ↓
rowsQuery loading + 无 stats → "正在计算行业强度..."（行 483-484）
  ↓
rows 为空 + needsIndustryFetch → "未获取行业数据" PresetFetchState（行 485-492）
  ↓
rows 为空 + 非内置预设 → "未匹配到行业数据" EmptyState（行 493-494）
  ↓
stats 有数据 → 全页渲染（HeroPanel/MarketPulse/热力图/IndustryRail/IndustryFocus）
```

## 关键数据结构

### API 契约

#### `GET /api/ext-data` — 扩展数据配置列表

```json
{
  "items": [
    {
      "id": "ext_hy_ths",
      "name": "同花顺行业",
      // display name
      "type": "snapshot",       // "snapshot" | "timeseries"
      "fields": [{"name": "所属同花顺行业", "type": "string"}, ...],
      "created_at": "...",
      "updated_at": "...",
      "row_count": 5000+,
      "pull": {"enabled": false}
    }
  ]
}
```

#### `GET /api/ext-data/{id}/rows` — 扩展数据行

请求参数：`?limit=12000`（前端 PAGE_LIMIT 常数）。响应：

```json
{
  "items": [
    {
      "symbol": "000001",
      "name": "平安银行",
      "所属同花顺行业": "银行-银行-股份制银行",   // 三级 "-" 拼接
      ...其他自定义字段
    }
  ],
  "total": 5000,
  "date": "2026-09-08"
}
```

#### `GET /api/screener/market-snapshot` — 行情快照

返回全市场个股实时行情（含 change_pct/turnover_rate/amount/cap/volume 等字段），前端 `buildMarketMap()` 转为 `Map<symbol, quote>` 供 stat 计算。

#### `GET /api/overview/market` — 市场总览（5s TTL）

返回包含 `industry_rank`/`concept_rank`/`radar`/`emotion`/`limit_up_down` 等。`industry_rank` 为二级行业（level=2）聚合排名，每项含 `name`/`avg_pct`/`member_count`（market_overview_builder.py:520）。

#### `GET /api/rps/rotation?days=N&kind=industry&level=LV` — RPS 轮动矩阵

```json
{
  "dates": ["2026-09-08", "2026-09-07", ...],
  "columns": {
    "2026-09-08": [["银行-银行", 0.0123], ["半导体", -0.0056], ...],
    ...
  },
  "concept_count": 86
}
```

#### `POST /api/rps/rotation-analyze` — AI 轮动分析

请求：`{ "days": 12, "focus": "...", "kind": "industry", "level": 2 }`。响应为 NDJSON 流：`{"type":"meta"}` / `{"type":"delta","content":"..."}` / `{"type":"done"}` / `{"type":"error"}`。

#### `POST /api/ext-data/presets/{config_id}/fetch` — 内置预设数据获取

手动触发预设数据拉取（仅 `pull.enabled=false` 的预设可调用）。前端调用后需 `invalidateQueries` 触发重载（IndustryAnalysis.tsx:307-310）。

#### `GET /api/ext-data/{id}/dimension-members?field=X&value=Y` — 维度成员

返回某行业/概念下的成分股列表，含 `symbol`/`name` 等。

#### `GET /api/ext-data/{id}/dimension-intraday` — 维度盘中估算

返回各维度等权估算涨跌幅（ext_data.py:685-706, 60s 缓存），成分股超 2000 只时 forward-fill 截断（_dimension_intraday_compute 行 576-682）。

### 存储结构

#### ext 数据 JSON（`data/ext/{config_id}/`）

- `config.json`：ExtConfig 定义（字段/类型/拉取配置）
- `rows.json`：行数据数组。timeseries 模式含多日数据 `[{date, symbols, ...}]`

#### 缓存键

| 缓存 | 键 | TTL | 位置 |
|------|-----|-----|------|
| Overview 市场总览 | `as_of.isoformat()` / `"latest"` | 5s | overview.py:361-364 |
| RPS 轮动矩阵 | `f"{kind}\|{level}\|{latest.isoformat()}"` | 120s | rps_rotation.py:138 |
| 概念/行业 map | per-kind（600s 独立） | 600s | rps_rotation.py:54-103 |
| 维度盘中估算 | `dimension_intraday:{config_id}` | 60s | ext_data.py:685-706 |

### 内存结构

```typescript
// IndustryStat — 前端行业统计结果 (IndustryAnalysis.tsx 内部)
interface IndustryStat {
  key: string             // 行业名（如 "银行-银行"）
  label: string           // 展示名
  level: number           // 1/2/3
  path: string[]          // ["一级","二级","三级"]
  count: number           // 成分股数量
  stocks: StockBrief[]    // 成分股列表
  avgPct?: number         // 平均涨幅（小数制）
  upPart: number          // 上涨占比
  turnoverRate?: number   // 平均换手率
  amount?: number         // 成交额
  cap?: number            // 流通市值
  leaderScore: number     // 龙头评分 0-100
  heatScore: number       // 热度评分 0-100
  riskScore: number       // 风险评分 0-100
  leaderSymbol?: string   // 龙头股代码
  leaderName?: string
  leaderPct?: number
}
```

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **新增行业分类数据源**：在管理端创建新的 Ext Data 配置（snapshot 或 timeseries 模式），定义包含行业/板块字段即可。页面自动在 configsQuery 中列出，用户点击配置按钮选择。
- **内置预设**：`ext_presets.py` 中 `_industry_preset()`（行 72-99）定义了 `ext_hy_ths`；如需增加其他内置预设，遵循 `_industry_preset` 模式注册并在 `ensure_builtin_presets`（行 237-258）中调用。
- **SectorMonitor 规则**：通过监控规则配置界面（monitor_rules.py）创建 sector 类型规则，规则引擎自动调用 sector_monitor.py 评估。

### L2 扩展（插槽/路由/注册替换）

- **前端插槽**：行业分析页面未注册 `docs/secondary-development.md` 中定义的 `layout.navigation.extra` / `stock-preview.footer` / `watchlist.toolbar` 插槽。如需添加，在对应子组件位置注册插槽。
- **后端可替换策略**：`docs/secondary-development.md` 中定义的 `CandidateFilter`/`ScoringPolicy` 等为"按需扩展"接口，当前未实现，不得导入。

### L3 修改（直接改源码）

- **修改评分算法**：
  - LeaderScore 权重调整：`IndustryAnalysis.tsx:130-157` 中 `leaderScore()` 函数的 `WEIGHTS` 对象
  - HeatScore 权重调整：`IndustryAnalysis.tsx:174-227` 中 `calcIndustryStat()` 的因子计算
  - RiskScore 权重调整：同上函数中的 riskScore 部分
- **修改行业分组逻辑**：`analysis-adapter.ts:236-289` `resolveDimension()` 检测维度字段；`IndustryAnalysis.tsx:249-267` `groupByIndustryLevel()` 按 `-` 分隔聚合
- **修改后端排名口径**：`market_overview_builder.py:240-302` `_dimension_rank()` 中的排名逻辑；`rps_rotation.py:169-174` 中的行业层级聚合
- **修改缓存 TTL**：`overview.py` 行 364 `_CACHE_TTL`（5s）、`rps_rotation.py` 行 35 `RPS_CACHE_TTL`（120s）、ext_data.py 行 686 `_DIMENSION_INTRADAY_TTL`（60s）
- **SectorMonitor 阈值**：`sector_monitor.py:295-325` `_dimension_snapshot()` 中的 `coverage_ratio >= 0.8` 和 `total_count >= 5`

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| Overview 内存缓存 | `invalidate_overview_cache()` 全局清空（overview.py:29-38），触发于 data clear/refresh、行情广播、设置变更 | Dashboard 大盘看板 5s 内展示最新行业排名 |
| RPS 矩阵内存缓存 | `invalidate_cache()` 清空 `_cache` 字典（rps_rotation.py:40-43）| RPS 轮动矩阵下次请求重新计算 |
| 维度盘中估算缓存 | TTL 60s 自动过期（ext_data.py:686） | 维度估算数据 60s 刷新 |
| 前端 React Query | `queryClient.invalidateQueries({ queryKey: QK.extData })` 触发重载 | 行业分析页面自动刷新数据源列表与行数据 |
| SSE 失效前缀 | SSE `overview-market` 前缀（queryKeys.ts:140） | 实时行情触发后自动失效 market 相关缓存 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_sector_monitor.py` | `test_validate_accepts_sector_rule_and_rejects_mixed_target_kinds`（行 53-73）：验证 sector 规则与混合 target 的校验 |
| 单元测试 | `backend/tests/test_sector_monitor.py` | `test_dimension_values_preserve_names_with_spaces_and_filter_nulls`（行 76-84）：确保带空格的维度值不被截断 |
| 单元测试 | `backend/tests/test_sector_monitor.py` | `test_concept_snapshot_uses_member_average_and_full_window`（行 132-184）：验证概念快照采用成员等权平均与完整窗口 |
| 单元测试 | `backend/tests/test_sector_monitor.py` | `test_momentum_rule_triggers_after_complete_window`（行 186-211）：验证动量规则在完整窗口后才触发 |
| 单元测试 | `backend/tests/test_sector_monitor.py` | `test_index_targets_are_evaluated_independently`（行 87-110）：索引 target 独立评估 |

**测试覆盖缺口**（待确认）：
- IndustryAnalysis.tsx 前端无专用测试文件
- market_overview_builder.py 无独立测试文件（大盘看板功能联合测试）
- rps_rotation.py 无独立测试文件

## 依赖关系

### 依赖的其他功能

- [扩展数据（Ext Data）](../architecture.md#ext-data)：提供行业分类数据源（配置/行数据/预设）
- [行情快照（Screener Market Snapshot）]：提供个股实时行情供 stat 计算
- [同花顺数据源]：内置预设 `ext_hy_ths` 的数据来源
- [KlineRepository]：市场总览构建个股涨跌幅时依赖 K 线数据
- [大盘看板（Dashboard）]：消费 overview API 的 industry_rank
- [监控规则引擎（Monitor）]：消费 SectorMonitorService 的板块快照

### 被依赖的功能

- 行业分析页面为独立功能页面，不被其他功能依赖
- `market_overview_builder.py` 被大盘看板（overview API）和大盘复盘（market_recap.py:295）共同依赖
- `sector_monitor.py` 被监控规则引擎（strategy/monitor.py:811）依赖

## 常见问题与注意事项

1. **内置预设数据需手动获取**：`ext_presets.py` 的 `ensure_builtin_presets()`（行 237-258）仅在启动时创建 config.json，**不自动拉取数据**。用户需在页面点击"获取行业数据"按钮触发 fetch，或通过 API `POST /api/ext-data/presets/ext_hy_ths/fetch` 触发。

2. **行业层级默认值**：前端 `fieldConfig.hierarchyLevel` 默认 2 级（二级行业），`RpsRotationDialog` 中 `level` 默认 2。`market_overview_builder.py` 中 `industry_rank` 固定 level=2。

3. **LeaderScore 的 LeaderStage 差异**：LeaderStage 组件（IndustryAnalysis.tsx 底部）展示的是**全市场**前 6 名领涨个股（按 leaderScore 排序），不是当前选中行业的个股。行业内的龙头股在 IndustryFocus 中高亮展示。

4. **数据口径一致性**：
   - 百分比字段：MarketSnapshot 中 `change_pct` 为小数制（如 0.0123 表示 +1.23%）
   - 行业总览排名 `avg_pct`：market_overview_builder.py 输出为小数制
   - 维度盘中估算：个股涨幅等权平均，2000 只上限 forward-fill

5. **SectorMonitor 服务启动时序**：`SectorMonitorService` 在 `main.py:321` 实例化，依赖 repo 就绪。被 `MonitorRuleEngine` 按需调用，无独立定时任务。

6. **配置失效回退**：当用户持久化的 `industryAnalysisConfig.configId` 指向已被删除的扩展数据时，页面自动调用 `pickBestConfig()`（行 291）回退到第一个可用配置，不报错（行 289-293）。

7. **PAGE_LIMIT=12000**：硬编码的 ext data 行数上限（行 290），用于覆盖全市场股票（~5000+ 只）及多级维度的行数据量。如需支持更大数据集需调整此值。

8. **per_stock vs per_dimension 结构**：`resolveDimension()`（analysis-adapter.ts:236-289）自动检测数据结构。当 `rows[0]` 含 `symbol`/`name` 时判定为 per_stock（每行一只股票），否则判定为 per_dimension（每行一个行业含 constituents）。

9. **RPS 轮动可选列缺失**：行业分析页面的 RPS 对话框通过 `kind="industry"` 调用，但 RPS 对话框顶部未显示行业层级切换 UI（待确认：对话框内 `level` state 默认为 2，但 UI 中是否展示层级选择器？代码中 `setLevel` 被 `useState` 初始化但未发现显式 UI 绑定——实际在 RpsRotationDialog.tsx:57 初始化 `level`，UI 部分需进一步确认）。