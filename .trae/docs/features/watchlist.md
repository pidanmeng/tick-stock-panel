---
title: 自选 Watchlist — 功能文档
description: 自选股管理的完整功能参考，包含分组管理、实时行情集成、批量导入、数据展示等全部子功能。
---

# 自选 Watchlist — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

自选 Watchlist 是用户跟踪关注股票的核心功能。用户可添加/删除/分组管理自选标的，通过表格/卡片/分组卡片/分组统计四种视图查看实时行情、技术指标、K 线/分时图，通过截图 OCR/CSV 文件/粘贴代码批量导入，并集成实时行情 SSE 推送实现盘中数据随 tick 跳动。路由注册于 `/watchlist`，菜单名"自选"。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 服务 | `backend/app/services/watchlist.py` | 自选数据与分组管理核心：Parquet 读写、JSON 分组定义、版本号机制、实时行情拉取 |
| API | `backend/app/api/watchlist.py` | 自选 REST API 路由：增删改查/分组管理/批量导入/OCR/enriched 数据 |
| 导入—CSV | `backend/app/services/watchlist_csv.py` | CSV/TXT 与粘贴代码导入：解码→抽代码→instruments 校验（不落盘） |
| 导入—OCR | `backend/app/services/watchlist_ocr/__init__.py` | 截图 OCR 导入入口 |
| 导入—OCR 流水线 | `backend/app/services/watchlist_ocr/pipeline.py` | 截图→OCR 文本→抽代码→instruments 校验 |
| 导入—OCR 引擎 | `backend/app/services/watchlist_ocr/provider.py` | OCR 引擎抽象层 + Tesseract 实现 |
| 主应用 | `backend/app/main.py` | 路由注册（行 472） |
| 数据仓库 | `backend/app/tickflow/repository.py` | KlineRepository：get_enriched_latest（行 1141）、get_enriched_latest_asset（行 1155）、get_name_map（行 1366）等 |
| 实时行情 | `backend/app/services/quote_service.py` | 行情轮询/SSE 广播（watchlist 实时模式交互） |
| 测试 | `backend/tests/test_watchlist_groups.py` | 分组管理单元测试 |
| 测试 | `backend/tests/test_watchlist_enriched_join.py` | enriched LEFT JOIN 集成测试 |
| 测试 | `backend/tests/test_watchlist_csv.py` | CSV 导入测试 |
| 测试 | `backend/tests/test_watchlist_ocr.py` | OCR 流水线测试 |
| 测试 | `backend/tests/test_watchlist_upload_size_limit.py` | 上传大小限制测试 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Watchlist.tsx` | 自选页主入口（2007 行），集成所有视图/交互/数据管理 |
| 组件 | `frontend/src/components/WatchlistGroups.tsx` | 分组栏（WatchlistGroupBar）与分组选择器（WatchlistGroupPicker） |
| 组件 | `frontend/src/components/WatchlistGroupCards.tsx` | 分组卡片总览视图 |
| 组件 | `frontend/src/components/WatchlistGroupStatsBar.tsx` | 分组统计条（顶部图形化涨跌概览） |
| 组件 | `frontend/src/components/WatchlistImportDialog.tsx` | 批量导入弹窗（OCR/CSV/粘贴代码） |
| 组件 | `frontend/src/components/WatchlistAddMenu.tsx` | 添加至分组菜单 |
| 组件 | `frontend/src/components/stock-table/StockDataTable.tsx` | 表格骨架组件 |
| 组件 | `frontend/src/components/stock-table/primitives.tsx` | 表格渲染原语（boardTag、renderBuiltinDataCell 等） |
| 组件 | `frontend/src/components/stock-table/MiniCandlestick.tsx` | 迷你蜡烛图组件 |
| 组件 | `frontend/src/components/stock-table/MiniIntraday.tsx` | 迷你分时图组件 |
| 组件 | `frontend/src/components/StockPreviewDialog.tsx` | 日K/分时预览弹窗 |
| 组件 | `frontend/src/components/DimensionMembersDialog.tsx` | 维度成员弹窗（扩展数据标签点击钻取） |
| 组件 | `frontend/src/components/ColumnCustomizer.tsx` | 自定义列侧栏 |
| API 客户端 | `frontend/src/lib/api.ts` | watchlist 系列 API 方法（行 2395-2498） |
| Query 键 | `frontend/src/lib/queryKeys.ts` | watchlist 查询键定义（行 25-40） |
| SSE 流 | `frontend/src/lib/useQuoteStream.ts` | SSE 实时行情连接 + invalidation 控制 |
| 路由 | `frontend/src/router.tsx` | 路由注册（行 133） |
| 工具库 | `frontend/src/lib/watchlist-columns.ts` | 列配置加载/保存/列构建 |
| 工具库 | `frontend/src/lib/watchlistGroupStats.ts` | 分组统计计算（computeGroupPcts） |
| 工具库 | `frontend/src/lib/stock-table.ts` | 信号识别/排序值获取 |
| 工具库 | `frontend/src/lib/minuteBatchIncremental.ts` | 分时批量增量轮询 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 数据 | `data/user_data/watchlist.parquet` | 自选条目持久化（Polars DataFrame） |
| 数据 | `data/user_data/watchlist_groups.json` | 分组定义持久化 |
| 配置 | `frontend/src/lib/list-columns.ts` | 日K/分时列渲染配置解析（resolveCandleConfig、resolveIntradayConfig） |

## 业务逻辑

### 核心流程

自选功能的核心是"用户管理关注标的 → 实时查看行情数据"，分解为以下子流程：

**管理流程（用户操作 → 持久化）：**
```text
用户操作（添加/移除/分组/导入）→ API 路由（api/watchlist.py）→ 服务层（services/watchlist.py）→
文件系统（Parquet + JSON）→ 响应返回 → 前端 TanStack Query 缓存更新 → UI 即时反映
```

**数据查询流程（页面加载 → 数据展示）：**
```text
页面加载 → TanStack Query 并发请求：
  ├─ GET /api/watchlist（symbol 列表）→ watchlist.list_symbols() → 读取 Parquet
  ├─ GET /api/watchlist/groups（分组列表）→ watchlist.list_groups() → 读取 JSON
  └─ GET /api/watchlist/enriched（行情数据）→ KlineRepository.get_enriched_latest() →
     内存缓存/懒加载 → 按资产类型分三路（stock/etf/index）LEFT JOIN 保证全部返回 →
     37 列内置指标 + 扩展数据列 → 前端渲染
```

**实时数据流（盘中推送）：**
```text
后端 QuoteService 轮询 → 写 kline_daily → 增量 enriched 计算 → SSE 广播 `quotes_updated` →
前端 useQuoteStream 收到事件 → 按 SSE_INVALIDATE_PREFIXES 精确失效
['watchlist-quotes', 'watchlist-enriched'] → TanStack Query 自动 refetch →
UI 实时更新（rt_price/rt_pct 覆盖）
```

### 数据流

1. **输入来源**：
   - 用户操作：添加/移除/分组/导入（前端 API 请求）
   - 实时行情：QuoteService 后台轮询（TickFlow 数据源）
   - 历史数据：KlineRepository 预计算 enriched 缓存（盘后管道刷新）

2. **处理过程**：
   - **写入路径**：所有写操作在 `watchlist.py` 的 `_LOCK`（RLock）内执行，`_REVISION` 每次写 +1，适用于线程安全。旧 schema 单值 `group_id` 自动迁移为 `group_ids: list[str]`（行 87-98）
   - **查询路径**：`/enriched` 端点以自选列表为主表 LEFT JOIN enriched 缓存，保证自选每一只都返回一行（行 409-415）。按资产类型（stock/etf/index）分三路合并，各自调用 `get_enriched_latest_asset`（repository.py:1155）
   - **实时行情**：`fetch_quotes`（watchlist.py:396）优先用 `QUOTE_BATCH` 能力，否则降级为 `QUOTE_BY_SYMBOL`，8s 超时保护
   - **导入流程**：OCR/CSV/粘贴代码 → 统一返回 `ImportCandidate[]`（候选列表，不落盘）→ 前端确认 → 通过 `POST /batch` 写入

3. **输出去向**：
   - 文件存储：`watchlist.parquet`（条目）+ `watchlist_groups.json`（分组定义）
   - API 响应：`/enriched` 返回 `{ rows, as_of, elapsed_ms }`，前端 TanStack Query 缓存
   - SSE 推送：`quotes_updated` 事件 → 前端 `useQuoteStream` → 按前缀精确失效

### 调用链

```text
前端页面（Watchlist.tsx:659）
  → TanStack Query（useQuery/useMutation）
    → API 客户端（api.ts:2395-2498）
      → HTTP REST API
        → API 路由（api/watchlist.py:23, prefix=/api/watchlist）
          → 服务层（services/watchlist.py）
            → 读操作：read_entries（watchlist.py:82）/ read_groups（watchlist.py:118）
            → 写操作：write_entries（watchlist.py:102）/ write_groups（watchlist.py:141）
            → 实时行情：fetch_quotes（watchlist.py:396）→ TickFlow Client（tf.quotes.get）
          → 数据查询（/enriched 端点）：
            → KlineRepository.get_enriched_latest（repository.py:1141）
            → KlineRepository.get_enriched_latest_asset（repository.py:1155）
            → KlineRepository.get_name_map（repository.py:1366）
            → 动态 EXT 列 JOIN：ExtConfigStore + _read_ext_dataframe
          → 导入路径：
            → OCR：import_watchlist_image（watchlist_ocr/pipeline.py:122）
            → CSV：import_watchlist_csv（watchlist_csv.py:103）
            → 粘贴代码：import_watchlist_codes（watchlist_csv.py:114）
  → SSE 实时行情：
    QuoteService 轮询 → SSE 广播（quotes_updated）
    → useQuoteStream（useQuoteStream.ts:131）
      → qc.invalidateQueries（按 SSE_INVALIDATE_PREFIXES 过滤）
        → watchlist-enriched / watchlist-quotes 自动 refetch
```

### 状态机

**数据版本号（_REVISION）：**
```text
初始值 0 → 每次写操作（_write_entries / _write_groups）+1
```

**写操作锁（_LOCK）：**
```text
线程安全：RLock 确保读写互斥，_REVISION 在锁内递增（read 免锁，以版本号做缓存失效判断）
```

## 关键数据结构

### API 契约

**`GET /api/watchlist`（行 111-113）：**
```json
{ "symbols": [{ "symbol": "000001", "added_at": "2024-01-01T00:00:00", "note": "", "group_ids": ["gid1", "gid2"], "name": "平安银行" }] }
```

**`GET /api/watchlist/enriched`（行 378-532）：**
```json
{ "rows": [{ "symbol": "...", "close": 10.5, "change_pct": 2.3, "name": "...", "asset_type": "stock", ...37列+ext列 }], "as_of": "2024-01-01", "elapsed_ms": 42 }
```

入参：`ext_columns`（可选，格式 `config_id.field_name,config_id2.field2`）
出参：LEFT JOIN 保证所有自选标的都返回，指标为 null 时前端渲染为"—"

**`POST /api/watchlist/batch`（行 125-136）：**
```json
{ "symbols": ["000001", "000002"], "note": "", "group_id": null, "group_ids": ["gid1", "gid2"] }
```

**`POST /api/watchlist/import-image`（行 200-233）：**
```json
// Request: multipart/form-data file
// Response:
{ "provider": "tesseract", "codes": ["000001"], "candidates": [{ "code": "000001", "symbol": "000001.SZ", "name": "平安银行", "matched": true, "already_in_watchlist": false }], "matched_count": 1, "unmatched_count": 0 }
```

### 存储结构

**`watchlist.parquet`（Schama 定义行 58-63）：**
```python
{
    "symbol": pl.Utf8,       # 证券代码
    "added_at": pl.Utf8,     # 添加时间（ISO 8601）
    "note": pl.Utf8,         # 备注
    "group_ids": pl.List(pl.Utf8),  # 所属分组 ID 列表（M:N 多对多）
}
```

**`watchlist_groups.json`（行 133-137）：**
```json
[
    { "id": "a1b2c3d4e5f6", "name": "核心持仓", "color": "sky" },
    { "id": "b2c3d4e5f6a7", "name": "观察池", "color": "amber" }
]
```

支持的颜色：`sky`, `blue`, `indigo`, `violet`, `fuchsia`, `rose`, `orange`, `amber`, `lime`, `emerald`, `teal`, `cyan`（行 44-57）

**`_WATCHLIST_COLS`（行 354-375）：** 37 个内置列，包含：
- OHLC：`close`, `open`, `high`, `low`, `change_pct`, `change_amount`, `amount`, `turnover_rate`
- 技术指标：`amplitude`, `annual_vol_20d`, `vol_ratio_5d`
- 均线：`ma5`, `ma10`, `ma20`, `ma60`, `vol_ma5`, `vol_ma10`
- 高低点：`high_60d`, `low_60d`
- 震荡指标：`rsi_6`, `rsi_14`, `rsi_24`, `macd_dif/dea/hist`, `kdj_k/d/j`, `boll_upper/lower`, `atr_14`
- 动量：`momentum_5d/10d/20d/30d/60d`, `deviate_3d/10d/30d`
- 信号：`signal_limit_up/down`, `signal_volume_surge`, `signal_ma_golden_5_20`, `signal_macd_golden/dead`, `signal_n_day_high/low`, `signal_boll_breakout_upper/lower`, `signal_ma20_breakout/breakdown`, `consecutive_limit_ups/downs`

### 内存结构

**服务层状态（watchlist.py 行 33-36）：**
```python
_LOCK = threading.RLock()       # 写操作互斥锁
_REVISION = 0                    # 数据版本号，每次写 +1
```

**前端 Query 键（queryKeys.ts 行 25-40）：**
```typescript
QK.watchlist               // ['watchlist'] — 自选列表
QK.watchlistGroups         // ['watchlist-groups'] — 分组列表
QK.watchlistQuotes         // ['watchlist-quotes'] — 实时行情
QK.watchlistEnriched(ext?) // ['watchlist-enriched', ext] — enriched 数据（带 ext 列参）
QK.watchlistKlineBatch     // ['kline-batch', symbols] — 日K 批量（不含 watchlist- 前缀，避免 SSE 高频失效）
QK.minuteBatch             // ['minute-batch', symbols] — 分时批量（同理）
```

**SSE 失效前缀（queryKeys.ts 行 132-142）：**
```typescript
SSE_INVALIDATE_PREFIXES = [
  'watchlist-quotes',      // 只失效实时行情缓存
  'watchlist-enriched',    // 只失效 enriched 缓存
  'quote-status',          // 全局状态
  'index-quotes', 'overview-market', 'limit-ladder',
]
```
注意：不用宽泛的 `'watchlist'`，避免误伤 `['watchlist']`（自选列表）和 `['watchlist-groups']`（分组配置），这两个只随手动操作变化。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **扩展数据列**：通过 `ext_columns` 参数（`config_id.field_name` 格式）在 `/enriched` 端点动态 LEFT JOIN 扩展数据表（api/watchlist.py 行 466-512）。用户在前端列定制器中勾选扩展列即可生效。
- **列配置持久化**：前端列配置通过 `api.watchlistColumns` 保存在后端，前端通过 `loadColumnConfig`/`saveColumnConfig` 加载（watchlist-columns.ts）
- **自选页工具栏插槽**：`ExtensionSlot` name="watchlist.toolbar"（Watchlist.tsx 行 1490-1498），注册的自定义组件可获取 `symbols`、`viewMode`、`selectedGroup`、`refresh` 上下文

### L2 扩展（插槽/路由/注册替换）

- **前端扩展插槽**：
  - `watchlist.toolbar`（Watchlist.tsx:1490）：工具栏最右侧，可注册自定义按钮/操作
  - `stock-preview.footer`（StockPreviewDialog）：预览弹窗底部
  - `layout.navigation.extra`：侧边栏导航额外菜单项（可注册 `/watchlist?group=xxx` 快速跳转）
- **后端扩展**：`NotificationFormatter` 可注册自定义通知格式

### L3 修改（直接改源码）

- **新增内置列**：在 `_WATCHLIST_COLS`（api/watchlist.py:354-375）中添加列名，确保 enriched 缓存已包含该列
- **修改分组模型**：`watchlist.py` 中的 `_ENTRY_SCHEMA`（行 58-63）是数据契约硬约束，修改需同步迁移逻辑（行 87-98）和备份机制（行 106-111）
- **修改实时行情模式**：`watchlist.py:396` 的 `fetch_quotes` 中 batch_size 由 `resolve_limit` 根据 CapabilitySet 决定，新增降级路径需同步更新

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件缓存（Parquet/JSON） | 直接写文件，`_REVISION` 递增 | 进程内通过 `revision()` 可检测变化 |
| 内存缓存（enriched） | 盘后管道刷新 + 盘中 SSE 增量 | 所有 watchlist 实时数据用户 |
| TanStack Query | `qc.setQueryData` 即时更新 + `qc.invalidateQueries` 后台 refetch | 当前用户所有已打开页面 |
| SSE/前端 | `useQuoteStream` 收到 `quotes_updated` → 按前缀精确失效 | 所有已连接浏览器 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_watchlist_groups.py` | 创建/重命名/删除/重排序分组；增减组成员；清空分组 |
| 集成测试 | `backend/tests/test_watchlist_enriched_join.py` | enriched LEFT JOIN 保证所有自选返回；资产类型路由 |
| 单元测试 | `backend/tests/test_watchlist_csv.py` | CSV 解码（UTF-8/GBK）；分隔符识别；代码抽取；去重保序 |
| 单元测试 | `backend/tests/test_watchlist_ocr.py` | 代码抽取（含拆分拼接）；候选解析；已有自选标记 |
| 集成测试 | `backend/tests/test_watchlist_upload_size_limit.py` | 上传文件大小限制（12MB 图片 / 5MB CSV） |

## 依赖关系

### 依赖的其他功能

- **KlineRepository / Enriched 缓存**（`repository.py`）：自选 `/enriched` 端点依赖 enriched 预计算数据，盘后管道刷新。新股/冷门股未覆盖时指标为 null
- **QuoteService / SSE 实时行情**（`quote_service.py`）：盘中实时数据依赖 QuoteService 后台轮询 + SSE 广播。`fetch_quotes` 直接调用 TickFlow 客户端
- **Instruments 主数据**（`repository.py` 的 `get_instruments`/`get_name_map`/`get_etf_symbol_set`/`get_index_symbol_set`）：资产类型识别、名称注入、ETF 路由
- **ExtData 扩展数据**（`ext_data.py`）：动态 JOIN 扩展列，需 ExtConfigStore 加载配置
- **TickFlow Capabilities**（`tickflow/capabilities.py`）：决定实时行情 batch 大小和降级路径

### 被依赖的功能

- **监控（Monitor）**：`watchlist.revision()` 被监控引擎用于检测自选成员变化，版本增加时重读成员列表
- **实时行情设置**：`watchlist_symbol_count` 决定自选前 N 个被实时监控，`realtimeMode` 控制模式
- **侧边栏导航**：`watchlist_groups_in_nav` 设置决定是否在侧边栏显示分组二级菜单（`api.ts:1783`）

## 常见问题与注意事项

- **M:N 多组模型语义**：`group_ids: list[str]` 为多值列，同一标的可同时属于多个分组。移出分组只摘标签（标的仍在自选），移出自选才删除实体。旧 schema 单值 `group_id` 首次写时自动备份并迁移
- **enriched LEFT JOIN 保证**：`/enriched` 以自选列表为主表 LEFT JOIN，保证每一只自选都返回一行。旧实现方向反了（以 enriched 为主表）会把缓存未覆盖的冷门股静默丢弃
- **实时行情列前缀**：前端使用 `rt_price`/`rt_pct`/`rt_name`/`rt_amount` 回退显示实时值，盘中覆盖 `close`/`change_pct`/`name`/`amount`，收盘后实时值回退到盘后值
- **日K/分时 SSE 续画机制**：历史 K 线按 staleTime 周期拉取，最后一根用每 tick 刷新的 enriched 当日 OHLC 前端覆盖/追加，零额外请求。分时图同理：SSE 续画到期前，轮询间隔内分时图随实时价跳动
- **视口感知**：卡片视图超过 `VIRTUAL_LIST_THRESHOLD` 时启用虚拟列表，分时批量请求只拉取可见 + overscan 缓冲区的 symbol，滚动后 300ms 防抖补拉
- **导入不落盘**：OCR/CSV/粘贴代码导入均只返回候选列表（`ImportCandidate[]`），前端确认后再通过 `POST /batch` 写入。`raw_text` 在响应中已剥离（可能很长）
- **OCR 并发限制**：`api/watchlist.py:35` 使用 `anyio.CapacityLimiter(2)` 限制 OCR 并发，避免多张大图同时解码 + 多 Tesseract 子进程
- **编码回退**：CSV/TXT 导入编码回退链 `utf-8-sig` → `gb18030`（`watchlist_csv.py:27`），分隔符自动识别 Tab vs 逗号
- **板块筛选**：`boardFilter` 使用 Set 持久化到 localStorage。ETF 无板块语义，按 `asset_type === 'etf'` 单独匹配 `ETF_BOARD` 筛选键
- **清空/删除确认**：清空自选和单只移除都有二次确认机制（`confirmClear` / `confirmRemove` 状态），防止误操作