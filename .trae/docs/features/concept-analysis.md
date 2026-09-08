---
title: 概念分析 ConceptAnalysis — 功能文档
description: 概念分析的完整功能参考，包含概念统计、涨幅RPS轮动矩阵、AI轮动分析等子功能。
---

# 概念分析 (ConceptAnalysis) — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

「概念分析」是 TSP 的一个核心看板页面，用于分析 A 股概念（题材）板块的资金轮动与强弱分布。它依托扩展数据系统（`ext_data`）的概念/题材分类数据，结合全市场快照行情，按概念分组统计涨跌幅、成交额、龙头评分等指标，并附加「涨幅 RPS 轮动矩阵」和「AI 轮动分析」两个高级子功能。行业分析（IndustryAnalysis）是同一套代码模式的平行复刻，维度改为行业。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 入口 | `backend/app/api/rps.py` | 涨幅轮动矩阵和 AI 轮动分析的 HTTP 端点注册 |
| API 入口 | `backend/app/api/overview.py` | 市场总览聚合（含概念/行业涨跌排名），5s 进程级缓存 |
| API 入口 | `backend/app/api/ext_data.py` | 扩展数据查询及内置预设拉取（`POST /api/ext-data/presets/{id}/fetch`） |
| 服务 | `backend/app/services/rps_rotation.py` | 涨幅轮动矩阵构建（`build_rps_rotation`），进程级 120s 结果缓存 + 600s 维度映射缓存 |
| 服务 | `backend/app/services/concept_rotation_analyzer.py` | AI 轮动分析：排名矩阵→轮动信号→LLM prompt→流式调用 |
| 服务 | `backend/app/services/market_overview_builder.py` | 市场总览装配（`build_market_overview`），含概念/行业维度聚合与排名 |
| 服务 | `backend/app/services/ext_data.py` | 扩展数据配置加载（`ExtConfigStore`） |
| 服务 | `backend/app/services/ext_presets.py` | 内置预设数据获取（`ext_gn_ths` 概念数据源，`ext_jq_industry` 行业数据源），结构转换与 Parquet 写入 |
| 数据 | `backend/app/services/market_mainline.py` | 复用了 `rps_rotation._load_concept_map_df` 做主线识别 |
| 数据 | `backend/app/services/ai_provider.py` | LLM 流式调用封装（`stream_ai_text`） |
| 装配 | `backend/app/main.py:495` | 注册 `rps.router`（`/api/rps`） |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/ConceptAnalysis.tsx` | 概念分析主页面（路由 `/concept-analysis`） |
| 页面 | `frontend/src/pages/IndustryAnalysis.tsx` | 行业分析页面（平行复刻，路由 `/industry-analysis`） |
| 组件 | `frontend/src/components/RpsRotationDialog.tsx` | 涨幅 RPS 轮动矩阵对话框（虚拟滚动 + AI 分析面板） |
| 组件 | `frontend/src/components/analysis-shared.tsx` | 共享 UI 组件：`AnalysisConfigDialog`、`PresetFetchState`、`DimensionHeatmap` |
| 组件 | `frontend/src/components/StockPreviewDialog.tsx` | 个股预览弹窗 |
| 组件 | `frontend/src/components/financials/MarkdownRenderer.tsx` | AI 分析结果的 Markdown 渲染 |
| 组件 | `frontend/src/components/Modal.tsx` | 模态框容器 |
| 适配层 | `frontend/src/lib/analysis-adapter.ts` | 扩展数据维度适配：支持两种结构（个股维度/板块维度），`resolveDimension` 自动探测 |
| API 客户端 | `frontend/src/lib/api.ts` | 封装所有 API 调用（`extDataList`、`extDataRows`、`extDataPresetFetch`、`marketSnapshot`、`rpsRotation`、`rotationAnalyzeStream`） |
| 查询键 | `frontend/src/lib/queryKeys.ts` | React Query 键：`QK.extData`、`QK.extDataRows`、`QK.marketSnapshot`、`QK.rpsRotation` |
| 存储 | `frontend/src/lib/storage.ts` | `conceptAnalysisConfig` / `industryAnalysisConfig` 本地存储 |
| 路由 | `frontend/src/router.tsx:129` | 注册 `/concept-analysis` 懒加载路由 |
| 导航 | `frontend/src/components/Layout.tsx:92` | 侧边栏菜单项「概念分析」 |

### 测试

| 文件 | 路径 | 用途 |
|------|------|------|
| 单元测试 | `backend/tests/test_rps_rotation_map_cache.py` | `_load_concept_map_df` 缓存契约回归（#186），验证 kind 隔离与缓存命中 |
| 单元测试 | `backend/tests/test_ai_analysis_focus.py` | AI 分析关注点 Prompt 契约（`build_focus_instruction` 在轮动分析中的正确传递） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 本地存储 | `frontend/src/lib/storage.ts` | 配置键 `concept-analysis-config` / `industry-analysis-config` |
| 数据目录 | `backend/data/ext_data/ext_gn_ths/` | 同花顺概念分类数据（Parquet，由 `ext_presets` 拉取写入） |
| 架构文档 | `.trae/docs/architecture.md:179` | 概念分析归属「行情总览」功能区 |

## 业务逻辑

### 核心流程

```
用户打开 /concept-analysis
  → 加载已有扩展数据配置（localStorage）
  → 从 preferredConfigId 推断活跃扩展数据源（自动选择或用户指定）
  → 并行请求：
     ① extDataList → 扩展数据源列表
     ② extDataRows(configId, limit=12000) → 扩展数据行
     ③ marketSnapshot → 全市场快照行情
  → resolveDimension 自动探测数据结构（个股维度/板块维度）
  → 按概念分组，每只股票与行情快照合并（symbol 匹配）
  → 计算每个概念组的统计指标（avgPct, upCount, heatScore, riskScore, leaderScore 等）
  → 渲染 HeroPanel + MarketPulse + ConceptRail + ConceptFocus
```

### 数据流

1. **输入来源**：
   - 扩展数据（概念/题材分类），来自 `ext_data` 系统，可手动在「设置」页配置或通过内置预设 `ext_gn_ths` 从同花顺接口获取
   - 全市场快照行情（`/api/screener/market-snapshot`），含 `change_pct`、`amount`、`turnover_rate`、`vol_ratio_5d` 等实时/日行情字段
   - 用户配置：`localStorage` 中的 `conceptAnalysisConfig`（选中的扩展数据源 ID 和维度字段）

2. **处理过程**：
   - `resolveDimension`（[analysis-adapter.ts:236](file:///c:/Code/tick-stock-panel/frontend/src/lib/analysis-adapter.ts#L236)）自动探测数据结构类型：
     - **结构 A（个股维度）**：每行一只股票，`concept` 字段存所属概念（支持多值分隔符）
     - **结构 B（板块维度）**：每行一个概念，带 `constituents` 成分股列表
   - 行情合并：`enrichStock`（[ConceptAnalysis.tsx:155](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L155)）用 `symbolKeys` 双向匹配（带后缀/不带后缀），将 `MarketSnapshotRow` 合并到每只股票
   - 概念统计：`calcConceptStat`（[ConceptAnalysis.tsx:168](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L168)）计算每个概念组的：
     - 基础统计：数量、涨幅均值/中位、涨跌平数、成交额、换手率
     - 龙头评分：`leaderScore`（[ConceptAnalysis.tsx:126](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L126)）六因子加权（动能 35% + 换手 22% + 成交 18% + 市值 15% + 量比 7% + 连板 3%）
     - 热度评分：`heatScore`（[ConceptAnalysis.tsx:199](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L199)）均值涨幅 38% + 上涨占比 20% + 强势股占比 16% + 成交额 12% + 龙头分 14%
     - 风险评分：`riskScore`（[ConceptAnalysis.tsx:200](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L200)）负涨幅 55% + 弱势股占比 45%
   - 前端排序：按 `heat` / `avgPct` / `leader` / `amount` / `down` 五种模式

3. **输出去向**：
   - 页面渲染：HeroPanel（5 个核心指标卡片）→ MarketPulse（领涨/领跌 Top 10 对比）→ ConceptRail（概念列表，带搜索与排序）→ ConceptFocus（选中概念详情，含成分股列表与龙头评分拆解）
   - 个股预览弹窗：`StockPreviewDialog`，点击成分股触发
   - RPS 轮动对话框：`RpsRotationDialog`，通过「涨幅RPS轮动分析」按钮打开

### 调用链

#### 主页面加载

```
路由器（router.tsx:129）→ ConceptAnalysis 组件（ConceptAnalysis.tsx:236）
  ├─ extDataList（api.ts，QK.extData）→ GET /api/ext-data
  ├─ extDataRows（api.ts，QK.extDataRows）→ GET /api/ext-data/{id}/rows?limit=12000
  └─ marketSnapshot（api.ts，QK.marketSnapshot）→ GET /api/screener/market-snapshot
```

#### 涨幅 RPS 轮动矩阵

```
RpsRotationDialog（RpsRotationDialog.tsx:50）
  ├─ rpsRotation（api.ts）→ GET /api/rps/rotation?days=12&kind=concept
  │   └─ rps_rotation.build_rps_rotation（rps_rotation.py:111）
  │       ├─ _load_concept_map_df（rps_rotation.py:54）→ ExtConfigStore.load_all → _dimension_field → _read_ext_rows
  │       ├─ repo.get_enriched_range（命中内存 _enriched_history_cache）
  │       └─ Polars group_by + sort 聚合
  └─ [AI分析] rotationAnalyzeStream（api.ts）→ POST /api/rps/rotation-analyze
      └─ analyze_rotation_stream（concept_rotation_analyzer.py:302）
          ├─ build_rps_rotation（复用轮动矩阵）
          ├─ _compute_rotation_signals（concept_rotation_analyzer.py:103）
          │   → 主线/新晋/退潮/机构特征/游资特征 五类信号
          ├─ build_market_overview（market_overview_builder.py:356）
          └─ stream_ai_text（ai_provider.py）→ LLM 流式响应 → NDJSON 协议
```

#### 内置预设数据获取

```
用户点击「获取数据」按钮
  → fetchMutation（ConceptAnalysis.tsx:270）
  → api.extDataPresetFetch('ext_gn_ths')
  → POST /api/ext-data/presets/ext_gn_ths/fetch
  → ext_presets.fetch_preset（ext_presets.py:261）
  → 从 https://shy313.com 拉取概念数据 → 结构转换 → 写入 Parquet
  → invalidateQueries（前端失效 QK.extData + QK.extDataRows）
```

### 状态机

页面存在 4 种渲染状态：

| 状态 | 条件 | 渲染内容 |
|------|------|----------|
| Loading | `configsQuery.isLoading` | 旋转加载动画 |
| 无配置 | `!activeConfig` | 提示框 + 配置按钮 + `PresetFetchState`（内置预设获取入口） |
| 无数据 | `needsConceptFetch` | `PresetFetchState`（数据源已就绪但未拉取） |
| 正常 | 数据加载完成且有概念分组 | 完整页面（HeroPanel + MarketPulse + ConceptRail + ConceptFocus） |

## 关键数据结构

### API 契约

#### GET /api/rps/rotation

```jsonc
{
  "dates": ["2026-09-05", "2026-09-04", ...],  // 最新在前
  "columns": {
    "2026-09-05": [["人工智能", 0.0522], ["芯片", 0.0381], ...],  // 每列按涨幅降序
    ...
  },
  "concept_count": 387  // 去重概念总数
}
```

#### POST /api/rps/rotation-analyze（流式 NDJSON）

```jsonc
{"type":"meta","days":12,"summary":"主线: 人工智能、芯片 | 新晋 3 | 退潮 2"}
{"type":"delta","content":"## 主线研判\n..."}
{"type":"error","message":"..."}
{"type":"done"}
```

#### GET /api/screener/market-snapshot → MarketSnapshotRow

详见 [api.ts:427](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L427)：
- `symbol, name, close, change_pct, amount, volume, turnover_rate, vol_ratio_5d, float_market_cap, market_cap, consecutive_limit_ups`

### 前端数据结构

#### ConceptStat（[ConceptAnalysis.tsx:47](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L47)）

```typescript
{
  key: string,          // 概念名称
  stocks: EnrichedStock[],  // 成分股（含行情+龙头评分）
  count: number,        // 成分股数量
  avgPct: number|null,  // 平均涨幅（小数制）
  medianPct: number|null,
  upCount/downCount/flatCount: number,
  upRate: number,       // 上涨占比
  strongCount/weakCount: number,  // 涨/跌≥5% 数量
  totalAmount: number,  // 总成交额（元）
  avgTurnover: number|null,  // 均换手率（百分数）
  avgVolRatio: number|null,
  leader: EnrichedStock|null,  // 龙头股
  heatScore: number,    // 热度评分 0-100
  riskScore: number,    // 风险评分 0-100
}
```

#### EnrichedStock（[ConceptAnalysis.tsx:35](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L35)）

`MarketSnapshotRow` 的扩展，增加 `leaderScore`（0-100）和 `leaderParts` 六因子明细。

### 存储结构

#### 扩展数据 Parquet

概念数据位于 `data/ext_data/ext_gn_ths/` 目录，由 `ext_presets.py` 从同花顺接口拉取并转换为标准结构。每行含：
- `symbol` / `code` / `股票代码`：股票代码
- `name` / `股票简称`：股票名称
- `所属概念`：概念名称（多值用分号分隔）

#### 本地存储

```jsonc
// localStorage key: tick-stock-panel:concept-analysis-config
{ "configId": "ext_gn_ths", "dimensionField": "所属概念" }
```

### 内存结构

#### rps_rotation 缓存

- `_cache: dict[str, dict]` + `_cache_ts: dict[str, float]`：轮动矩阵结果缓存，TTL 120s，键格式 `"{kind}|{level}|{latest_date}"`
- `_map_cache: dict[str, tuple[DataFrame, int]]` + `_map_ts: dict[str, float]`：维度映射缓存，TTL 600s，键为 `kind`（concept/industry）

#### overview 缓存

- `_cache: dict` + `_cache_ts: float` + `_cache_lock: Lock`：市场总览聚合结果缓存，TTL 5s，线程安全

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **添加自定义概念数据源**：在「设置→扩展数据」中添加新的扩展数据源，配置字段映射（`symbol`/`code` + 概念字段），概念分析页面会自动探测并出现在配置弹窗中
- **切换数据源**：通过页面右上角配置按钮，从已注册的扩展数据源中选择

### L2 扩展（插槽/路由/注册替换）

- 概念分析页面**未注册为前端插槽**（`docs/secondary-development.md` 中 `stock-preview.footer` 等三个插槽不包含概念分析）
- 当前无公开的插件扩展点；如需修改，走 L3 直接改源码

### L3 修改（直接改源码）

以下是高频修改场景及建议入口：

| 修改目标 | 入口文件 | 修改位置 |
|----------|----------|----------|
| 龙头评分权重 | `ConceptAnalysis.tsx` | `leaderScore` 函数（第 126-153 行），调整六因子权重 |
| 热度评分公式 | `ConceptAnalysis.tsx` | `calcConceptStat` 函数（第 199 行），调整 heatScore 子项权重 |
| 排序模式 | `ConceptAnalysis.tsx` | `statSort` 函数（第 223 行）及 `SortMode` 类型（第 33 行） |
| 渲染行数上限 | `ConceptAnalysis.tsx` | `MAX_RENDERED_CONCEPTS` / `MAX_RENDERED_STOCKS` 常量（第 30-31 行） |
| 轮动矩阵天数范围 | `RpsRotationDialog.tsx` | `MIN_DAYS` / `MAX_DAYS`（第 21-22 行） |
| RPS 轮动矩阵聚合口径 | `rps_rotation.py` | `build_rps_rotation`（第 175 行），`change_pct.mean()` 可改为加权平均等 |
| AI 分析系统 Prompt | `concept_rotation_analyzer.py` | `_build_system_prompt`（第 30 行），修改分析准则 |
| 轮动信号识别阈值 | `concept_rotation_analyzer.py` | `_compute_rotation_signals`（第 103 行），调整主线/新晋/退潮阈值 |

### 缓存失效影响

该功能涉及多个写路径，修改后需清理的缓存层：

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| rps_rotation 结果缓存 | 调用 `rps_rotation.invalidate_cache()`（rps_rotation.py:40） | 轮动矩阵 `/api/rps/rotation` 在 120s TTL 内返回旧数据 |
| overview 聚合缓存 | 调用 `overview.invalidate_overview_cache()`（overview.py:29） | 市场总览 `/api/overview/market` 在 5s TTL 内返回旧数据 |
| SSE 推送 | `SSE_INVALIDATE_PREFIXES` 含 `overview-market`、`index-quotes` | 盘中行情 tick 自动失效 overview 缓存 |
| 前端 query 缓存 | `queryClient.invalidateQueries` 携带 `QK.extData` / `QK.extDataRows` | 预设数据拉取后自动失效；SSE 不失效 ext_data 相关缓存 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_rps_rotation_map_cache.py` | 验证 `_load_concept_map_df` 缓存命中返回正确元组，kind 隔离（concept vs industry） |
| 单元测试 | `backend/tests/test_ai_analysis_focus.py` | 验证 `build_focus_instruction` 在轮动分析 prompt 中正确注入，空 focus 不添加多余章节 |

> 注意：当前无前端测试覆盖 ConceptAnalysis 页面逻辑，`test_rps_rotation_map_cache.py` 覆盖最核心的缓存契约回归。

## 依赖关系

### 依赖的其他功能

- **[扩展数据系统 (ExtData)](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py)**：概念分析的分类数据来源，依赖 `ExtConfigStore` 加载已注册的扩展数据源
- **[全市场快照 (Screener)](file:///c:/Code/tick-stock-panel/backend/app/api/screener.py)**：`/api/screener/market-snapshot` 提供个股行情数据（涨跌幅、成交额、换手率等）
- **[AI 提供商 (AI Provider)](file:///c:/Code/tick-stock-panel/backend/app/services/ai_provider.py)**：AI 轮动分析依赖 LLM 流式调用
- **[市场总览 (Market Overview)](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py)**：AI 分析需要大盘背景数据（指数、情绪、涨停等）
- **[KlineRepository 内存缓存](file:///c:/Code/tick-stock-panel/backend/app/repositories/kline_repository.py)**：`get_enriched_range` 命中 `_enriched_history_cache`，提供个股历史涨跌幅用于轮动矩阵

### 被依赖的功能

- **行业分析 (IndustryAnalysis)**：完全复用 ConceptAnalysis 的代码模式与 `rps_rotation` 服务，`RpsRotationDialog` 支持 `kind='industry'` 参数
- **市场主线识别 (MarketMainline)**：`market_mainline.py:24` 导入 `rps_rotation._load_concept_map_df` 复用概念维度映射
- **大盘复盘 (Market Recap)**：AI 复盘功能可能引用 `build_market_overview` 的总览数据

## 常见问题与注意事项

1. **概念数据源的获取**：首次使用需先获取数据。内置预设 `ext_gn_ths` 从 `https://shy313.com` 拉取数据，若该地址不可达，概念分析页面将显示「未获取概念数据」提示。用户可通过页面上的「获取数据」按钮手动触发拉取。

2. **扩展数据配置失效**：用户配置的 `configId` 指向的扩展数据源可能被删除（在设置页中移除）。页面通过 `pickBestConfig`（[ConceptAnalysis.tsx:75](file:///c:/Code/tick-stock-panel/frontend/src/pages/ConceptAnalysis.tsx#L75)）自动回退到最匹配的概念数据源。

3. **行情数据口径**：`change_pct` 为小数制（如 `0.0522` 表示 +5.22%），`turnover_rate` 在 `MarketSnapshotRow` 中为百分数（如 `5.5` 表示 5.5%）。前端 `fmtPct` 自动处理显示格式。

4. **性能注意事项**：
   - 概念分析页面最多请求 12000 行扩展数据（`PAGE_LIMIT`），前端渲染上限 120 个概念、160 只成分股
   - RPS 轮动矩阵使用虚拟滚动（`RpsRotationDialog.tsx` 第 113 行），只渲染可视区域 + overscan 8 行，确保 387 概念 × 30 天矩阵流畅滚动
   - 轮动矩阵的 `_enriched_history_cache` 在应用启动时全量加载到内存，后续 group_by + sort 为 Polars 内存操作，实测 <50ms

5. **AI 轮动分析 Token 控制**：`_compute_rotation_signals` 每类信号最多取 8 个概念（`_TOP_N = 8`），控制 prompt 长度。`stream_ai_text` 的 `max_tokens=None` 不限制输出，推理模型思考 token 计入预算。

6. **行业分析的差异**：`IndustryAnalysis.tsx` 是 `ConceptAnalysis.tsx` 的平行复刻，主要区别为：
   - 关键词使用 `['industry', '行业', 'sector', '申万', '中信']`
   - `RpsRotationDialog` 传入 `kind='industry'`，显示行业层级选择器（1/2/3 级）
   - 行业分析使用 `ext_jq_industry` 预设数据源