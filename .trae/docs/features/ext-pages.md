---
title: 扩展页面设置
description: 扩展页面设置页功能文档 — 把扩展数据源配置成左侧动态分析菜单（维度热度榜 / 指标排名榜 / 明细表），含菜单 CRUD、模板字段映射与缓存失效。
---

# 扩展页面设置（设置 → 扩展页面） — 功能文档

> 该 Tab 在 [Settings.tsx:36](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L36) 注册，Tab key 为 `ext-pages`、label 为「扩展页面」、图标 `BarChart3`。核心定位：**把已有的扩展数据源（`/api/ext-data`）可视化装配成可访问的动态分析菜单**——用户选择数据源、模板、分组/排名字段与列表列后，系统生成一条左侧导航项（`/analysis/{menuId}`），由 [ExtDimensionAnalysis.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/ExtDimensionAnalysis.tsx) 按模板渲染数据。该 Tab 只负责「菜单配置的 CRUD」，不负责扩展数据源本身的增删改查与数据拉取（后者由「数据」页 / `ext_data` API 承担）。

## 功能概述

「扩展页面」页是「设置」页签之一，负责把扩展数据源配置成左侧分析菜单。它做三件事：

1. **列出已有分析菜单**：读取 `/api/analysis-menus`，以卡片形式展示，支持「打开分析页」跳转。
2. **新建/编辑菜单**：选择扩展数据源、模板（`dimension_rank` / `ranking` / `table`）、分组字段或排名字段、列表列，保存为一条 `AnalysisMenu`。
3. **删除自定义菜单**：内置（`builtin`）菜单不可删。

前端把 `ExtDataField[]` 实时转换成 `AnalysisColumn[]`（`dtype int/float → number`，其余 `string`），并按模板自动生成 `group_columns`（维度榜的「分组 / 股票数 / 平均指标」行）或 `default_sort`（排名榜默认按排名字段降序）。保存后仅失效 `QK.analysisMenus` 查询，左侧导航 [Layout.tsx:362-365](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L362-L365) 会自动刷新。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 分析菜单 API | `backend/app/api/analysis.py` | `/api/analysis-menus` 的列表/详情/重排/新增编辑/删除；`AnalysisMenu`、`AnalysisColumn`、`UpsertAnalysisMenu` 模型；菜单 JSON 落盘 `data/analysis_menus/{id}.json` |
| 扩展数据 API | `backend/app/api/ext_data.py` | `/api/ext-data` 列表配置（本 Tab 的数据源下拉）、行查询、预设拉取、上传/写入、定时拉取配置等 |
| 扩展数据服务 | `backend/app/services/ext_data.py` | `ExtConfig`/`ExtField`/`PullConfig` 模型、`ExtConfigStore` 配置读写、Parquet 写入、CSV 编码转换、symbol 标准化 |
| 内置预设 | `backend/app/services/ext_presets.py` | 概念(`ext_gn_ths`)/行业(`ext_hy_ths`) 预设定义、接口结构→本地 schema 转换、启动时仅建配置不拉取、手动 `fetch_preset` |
| 定时拉取 | `backend/app/services/ext_pull.py` | `PullScheduler`、`fetch_and_ingest`、`backfill_history`、鉴权与时间窗口 |
| 路由挂载 | `backend/app/main.py` | `app.include_router(analysis.router)`、`app.include_router(ext_data.router)` |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面面板 | `frontend/src/pages/settings/ExtPages.tsx` | `SettingsExtPagesPanel`：菜单卡片列表 + 新建/编辑表单 + 删除 |
| 设置外壳 | `frontend/src/pages/Settings.tsx` | Tab 定义（`ext-pages` → `SettingsExtPagesPanel`） |
| 分析页消费者 | `frontend/src/pages/AnalysisDetail.tsx` | `/analysis/:menuId` 路由，渲染 `ExtDimensionAnalysis` |
| 分析页渲染 | `frontend/src/components/ExtDimensionAnalysis.tsx` | 按 `AnalysisMenu.template` 渲染维度榜/排名榜/明细表，读取 ext 数据行 |
| 导航挂载 | `frontend/src/components/Layout.tsx` | 拉取 `analysisMenus`，过滤 `visible` 后拼入左侧导航 |
| API 客户端 | `frontend/src/lib/api.ts` | `analysisMenus` / `analysisMenu` / `analysisMenuSave` / `analysisMenuReorder` / `analysisMenuDelete` / `extDataList`；类型 `AnalysisMenu` / `AnalysisColumn` / `ExtDataConfig` / `ExtDataField` |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `QK.analysisMenus`、`QK.extData`、`QK.analysisMenu(id)` |
| 路由 | `frontend/src/router.tsx` | `/analysis` 重定向到设置页、`/analysis/:menuId` 渲染 `AnalysisDetail` |
| 菜单设置 | `frontend/src/pages/settings/MenuSettings.tsx` | 复用 `analysisMenus` 参与左侧导航排序/隐藏（同一菜单集合） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 分析菜单存储 | `data/analysis_menus/{menu_id}.json` | 每个菜单一个 JSON 文件，含模板、字段、列配置 |
| 扩展数据配置 | `data/ext_data/{config_id}/config.json` | 扩展数据源 schema + pull 配置 |
| 扩展数据快照 | `data/ext_data/{config_id}/part.parquet`（snapshot）或 `timeseries/date=YYYY-MM-DD/part.parquet`（timeseries） | 实际数据 |
| 导航偏好 | `data/user_data/preferences.json` | `nav_order` / `nav_hidden`（菜单设置页维护，影响扩展菜单位置） |

## 业务逻辑

### 核心流程

```text
打开「设置 → 扩展页面」
├─ 拉取 analysisMenus（GET /api/analysis-menus）→ 卡片列表
├─ 拉取 extData（GET /api/ext-data）→ 数据源下拉
├─ 新建/编辑表单：
│   ├─ 选数据源 → 取该配置的 fields
│   ├─ 选模板：
│   │   ├─ dimension_rank → 选「分组字段」(dimension_field)
│   │   │   └─ group_columns = [分组(__dimension), 股票数(__count), 前2个数值列(avg)]
│   │   ├─ ranking → 选「排名字段」(rank_field)
│   │   │   └─ default_sort = { field: rank_field, order: 'desc' }
│   │   └─ table → 无额外字段
│   ├─ 勾选列表列 → detail_columns（排除 symbol/code，dtype→type 映射）
│   └─ 保存（POST /api/analysis-menus/{id}）
│       └─ onSuccess → invalidate QK.analysisMenus → 关闭表单 + 重置
├─ 删除（DELETE /api/analysis-menus/{id}，仅非 builtin）
│   └─ onSuccess → invalidate QK.analysisMenus
└─ 卡片「打开分析页」→ 跳转 /analysis/{menu.id}
```

新建表单的默认值由 `resetForm()` 给出：数据源取 `configs[0]`，分组字段用 `firstMatchingField` 按关键词 `['概念','industry','行业','sector']` 匹配，列表列默认取前 6 个非 `symbol/code` 字段。

### 数据流

1. **输入来源**：
   - `GET /api/analysis-menus` 返回 `{ items: AnalysisMenu[] }`（已保存菜单 + 默认菜单；当前 `_default_menus()` 返回空）。
   - `GET /api/ext-data` 返回 `{ items: ExtDataConfig[] }`，每项含 `fields`、`latest_sync_date`、`date_range`。
   - 用户表单输入（id、label、数据源、模板、分组/排名字段、勾选列）。

2. **处理过程**：
   - 前端 `buildColumn(field)` 把 `ExtDataField` 转为 `AnalysisColumn`：`int/float → type:'number', sortable:true, precision:2`，其余 `type:'string'`。
   - `dimension_rank` 模板：`group_columns` 追加 `__dimension`（分组）、`__count`（股票数）、前 2 个数值列改名为「平均XX」并设 `aggregate:'avg'`；`dimension_field` 写入菜单。
   - `ranking` 模板：`default_sort = { field: rankField, order: 'desc' }`；`rank_field` 写入菜单。
   - `table` 模板：`dimension_field / rank_field` 传 `null`。
   - icon：`dimension_rank → 'tags'`，其余 `'chart'`（仅前端保存时决定，后端不强制）。
   - `order`：编辑时保留原值，新建时取 `menuItems.length + 100`。
   - 后端 `_save()` 强制 `builtin=False`，写入 `created_at`/`updated_at`。

3. **输出去向**：
   - 菜单 JSON 写入 `data/analysis_menus/{id}.json`（`AnalysisMenu.model_dump()`）。
   - 前端 `QK.analysisMenus` 失效 → [Layout.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx) 重新拉取并把可见菜单拼入左侧导航。
   - 跳转 `/analysis/{id}` 时由 `ExtDimensionAnalysis` 读 `analysisMenu(id)` + `extDataRows(dataSource)` 渲染。

### 调用链

```text
ExtPages.tsx:36-39 (useQuery analysisMenus / extData)
  → api.analysisMenus → GET /api/analysis-menus
    → analysis.py:124 list_menus → _load_saved (glob *.json) + _default_menus → _ordered
  → api.extDataList → GET /api/ext-data
    → ext_data.py:326 list_configs → ExtConfigStore.load_all (带目录签名缓存)

ExtPages.tsx:83-124 (save mutation)
  → 前端 buildColumn / group_columns 组装
  → api.analysisMenuSave → POST /api/analysis-menus/{id}
    → analysis.py:153 upsert_menu → AnalysisMenu(...) → _save → write {id}.json
  → onSuccess: qc.invalidateQueries(QK.analysisMenus)

ExtPages.tsx:126-129 (del mutation)
  → api.analysisMenuDelete → DELETE /api/analysis-menus/{id}
    → analysis.py:166 delete_menu → unlink {id}.json
  → onSuccess: invalidate QK.analysisMenus

Layout.tsx:362-365 (导航消费)
  → useQuery QK.analysisMenus → 过滤 visible → /analysis/{id} 导航项

AnalysisDetail.tsx:5-6 (页面消费)
  → ExtDimensionAnalysis(menuId) → 按 template 渲染（读 menu + extDataRows）
```

## 关键数据结构

### API 契约

**`AnalysisMenu`（[analysis.py:32-47](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L32-L47) / [api.ts:3828-3844](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L3828-L3844)）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str | 菜单标识，`^[a-zA-Z0-9_]+$`，1-64 字符；保存后不可改（前端编辑时 input 禁用） |
| `label` | str | 菜单名称，1-64 字符 |
| `icon` | str | `'tags'`(维度榜) / `'chart'`(其余)；前端导航据此选 `Tags` 或 `BarChart3` 图标 |
| `data_source` | str | 扩展数据源 id（对应 `ext_data` 的 `config.id`） |
| `template` | `'dimension_rank' \| 'ranking' \| 'table'` | 渲染模板 |
| `dimension_field` | str \| null | 维度榜的分组字段名 |
| `rank_field` | str \| null | 排名榜的排名字段名 |
| `group_columns` | `AnalysisColumn[]` | 维度榜的分组行列（`__dimension` / `__count` / 平均指标） |
| `detail_columns` | `AnalysisColumn[]` | 明细表列 |
| `default_sort` | `{field, order:'asc'\|'desc'} \| null` | 排名榜默认排序 |
| `visible` | bool | 是否显示在左侧导航 |
| `order` | int | 排序权重 |
| `builtin` | bool | 是否内置（`_save` 强制 False） |

**`AnalysisColumn`（[analysis.py:15-24](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L15-L24) / [api.ts:3816-3826](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L3816-L3826)）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `field` | str | 列字段名 |
| `label` | str | 列标题 |
| `type` | `'string'\|'number'\|'percent'\|'amount'\|'date'` | 前端类型；`int/float → number`，其余 `string` |
| `sortable` | bool | 数值列可排序 |
| `precision` | int \| null | `float` 列默认 2 |
| `aggregate` | `'count'\|'avg'\|'sum'\|'min'\|'max' \| null` | 维度榜分组聚合 |
| `visible` | bool | 默认 True |

**端点**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/analysis-menus` | `{ items: AnalysisMenu[] }`（[analysis.py:123-128](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L123-L128)） |
| GET | `/api/analysis-menus/{menu_id}` | 单个菜单（[analysis.py:131-136](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L131-L136)） |
| POST | `/api/analysis-menus/{menu_id}` | 新增/编辑（[analysis.py:152-162](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L152-L162)） |
| POST | `/api/analysis-menus/reorder` | 按 ids 重排（[analysis.py:139-149](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L139-L149)） |
| DELETE | `/api/analysis-menus/{menu_id}` | 删除（仅已保存的，默认菜单不可删）（[analysis.py:165-171](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L165-L171)） |
| GET | `/api/ext-data` | 扩展数据源列表（本 Tab 数据源下拉）（[ext_data.py:325-336](file:///c:/Code/tick-stock-panel/backend/app/api/ext_data.py#L325-L336)） |

### 存储结构

**`data/analysis_menus/{menu_id}.json`**：`AnalysisMenu.model_dump()` 的完整序列化，与上表字段一一对应。

**`data/ext_data/{config_id}/config.json`**：扩展数据源配置，关键字段 `id`、`label`、`mode`、`fields[]`（`{name,dtype,label}`）、`symbol_map`、`code_map`、`pull{}`。本 Tab 只读取 `id`/`label`/`fields` 供下拉与列选择使用。

### 内存结构

- `_load_all_cache`（[ext_data.py:222](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L222)）：`ExtConfigStore.load_all` 的进程内缓存，key 为配置目录路径，value 为 `(目录签名, [ExtConfig])`；配置目录 mtime/size 变化时失效。
- `PullScheduler._tasks`（[ext_pull.py:393-396](file:///c:/Code/tick-stock-panel/backend/app/services/ext_pull.py#L393-L396)）：`{config_id: asyncio.Task}`，管理启用了 pull 的扩展数据源定时任务。
- 前端 `QK.analysisMenus` / `QK.extData` 的 React Query 缓存。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **新增一个扩展页面**：无需改代码，在「设置 → 扩展页面」点「新建页面」即可。前提是目标扩展数据源已存在（`data/ext_data/{id}/config.json`）。
- **调整内置预设**：概念/行业预设定义在 [ext_presets.py:41-103](file:///c:/Code/tick-stock-panel/backend/app/services/ext_presets.py#L41-L103)，字段结构与拉取 URL 在此改。预设 `enabled=False`，启动只建 `config.json`，数据需手动拉取。
- **修改菜单 JSON**：可直接编辑 `data/analysis_menus/{id}.json`（字段需符合 `AnalysisMenu` schema），重启或重拉 `analysisMenus` 即生效；注意 `builtin` 字段会被 `_save` 覆盖为 False，只有默认菜单（当前无）才为 True。

### L2 扩展（插槽/路由/注册替换）

- **新增分析模板**：需同时改三处——前端 [ExtPages.tsx:46](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L46) 的 `template` state 与 select 选项、[analysis.py:37](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L37) 的 `Literal` 联合类型、以及 [ExtDimensionAnalysis.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/ExtDimensionAnalysis.tsx) 的渲染分支。模板字面量是贯穿前后端的契约，改动需同步。
- **新增列类型**：`AnalysisColumn.type` 联合类型在 [analysis.py:18](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L18) 与 [api.ts:3819](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L3819) 各定义一次，需保持一致。
- **自动生成默认菜单**：当前 `_default_menus()`（[analysis.py:113-120](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L113-L120)）返回空。如需恢复「扫描含概念字段的扩展表自动生成菜单」，在此函数实现；但注释已说明会与内置概念分析页导航重复，需谨慎。

### L3 修改（直接改源码）

- **改保存校验**：前端校验在 [ExtPages.tsx:85-90](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L85-L90)（数据源/标识/名称/分组/排名字段必填）；后端校验在 `UpsertAnalysisMenu` 的 Pydantic 约束（[analysis.py:50-61](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L50-L61)）。两处需同步收紧。
- **改默认列选择逻辑**：`firstMatchingField`（[ExtPages.tsx:24-32](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L24-L32)）按关键词匹配分组字段；默认列取前 6 个非 symbol/code 字段（[ExtPages.tsx:65](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L65)）。
- **改维度榜聚合列数**：当前取前 2 个数值列做「平均」聚合（[ExtPages.tsx:100](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L100)），改 `.slice(0, 2)` 即可。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 前端 React Query `QK.analysisMenus` | 保存/删除 mutation 的 `onSuccess` 调用 `qc.invalidateQueries`（[ExtPages.tsx:119](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L119)、[ExtPages.tsx:128](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L128)） | 本页卡片列表 + 左侧导航 + 菜单设置页 |
| 前端 React Query `QK.extData` | 本 Tab 不写 ext 数据，不主动失效；若数据源被外部修改需手动重拉 | 数据源下拉 |
| 后端 `_load_all_cache`（ext 配置缓存） | 扩展配置 upsert/delete 时 `_invalidate_ext_derived` 失效（[ext_data.py:305](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L305)）；本 Tab 不触发 | 扩展帧缓存、因子、策略结果 |
| 后端分析菜单 JSON | 无进程内缓存，每次 `list_menus` 读盘（glob `*.json`） | 仅磁盘 IO |

注意：本 Tab 的写操作（菜单 CRUD）**不**触发 `_invalidate_ext_derived`，因为菜单配置不改变扩展数据本身；只有 ext 数据/配置变化才需要清扩展派生缓存。

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 扩展数据单元 | `backend/tests/test_ext_config_store_safety.py` | config_id 白名单防穿越、非法 id 拒绝 |
| 扩展数据单元 | `backend/tests/test_ext_config_load_all_cache.py` | load_all 目录签名缓存命中/失效 |
| 扩展数据单元 | `backend/tests/test_ext_csv_transcode_*.py` | GBK/GB18030 CSV 转 UTF-8 |
| 扩展数据单元 | `backend/tests/test_ext_pull_auth.py` | 拉取接口鉴权（bearer/header/query） |
| 扩展数据单元 | `backend/tests/test_ext_backfill.py` | timeseries 历史回补、429 退避 |
| 扩展数据单元 | `backend/tests/test_ext_presets_startup.py` | 启动只建配置不拉取、已存在跳过 |
| 扩展数据单元 | `backend/tests/test_ext_data_dimension_members.py` | 维度成员查询 |
| 分析菜单 | 待确认 | 未发现 `analysis-menus` 专用测试；菜单 CRUD 当前无后端单测覆盖 |
| 前端 | 待确认 | 未发现 `ExtPages.tsx` 专用前端测试 |

## 依赖关系

### 依赖的其他功能

- [扩展数据](file:///c:/Code/tick-stock-panel/.trae/docs/features/data-management.md)：本 Tab 的数据源下拉与列选择完全依赖 `ext_data` 配置；没有扩展数据源就无法创建扩展页面。
- [菜单设置](file:///c:/Code/tick-stock-panel/.trae/docs/features/menu-settings.md)（`MenuSettings.tsx`）：复用同一 `analysisMenus` 集合做导航排序/隐藏，两者共享 `QK.analysisMenus` 缓存。
- 左侧导航（[Layout.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx)）：消费 `analysisMenus` 生成 `/analysis/{id}` 导航项。

### 被依赖的功能

- 分析详情页（[AnalysisDetail.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/AnalysisDetail.tsx) / [ExtDimensionAnalysis.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/ExtDimensionAnalysis.tsx)）：依赖本 Tab 创建的 `AnalysisMenu` 配置来决定数据源、模板、分组/排名字段与列。
- 前端扩展注册表（`getFrontendExtensionNavigation`，[Layout.tsx:548](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L548)）：与扩展菜单并列拼入导航（不同机制，不互相依赖）。

## 常见问题与注意事项

- **菜单标识保存后不可改**：前端编辑时 `id` 输入框禁用（[ExtPages.tsx:169](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L169)），后端 `upsert_menu` 用 path 中的 `menu_id` 作为 id，body 不传 id。如需改名只能新建+删旧。
- **数据源变化不自动更新菜单**：若扩展数据源的 `fields` 被修改，已保存菜单的 `detail_columns`/`group_columns` 不会自动同步，可能引用已不存在的字段。需重新编辑菜单并保存。
- **`builtin` 菜单不可删**：删除按钮仅在 `!menu.builtin` 时渲染（[ExtPages.tsx:267](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L267)），后端 `delete_menu` 也只删已存在的 JSON 文件（默认菜单无文件，返回 404）。
- **`/analysis` 路由重定向**：[router.tsx:127](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx#L127) 把 `/analysis` 重定向到 `/settings?tab=ext-pages`，因为分析菜单是动态的，没有固定的「分析首页」。
- **维度榜的 `__dimension` / `__count` 是虚拟列**：在 `group_columns` 中以 `field:'__dimension'/'__count'` 存在，由渲染层（`ExtDimensionAnalysis`）按分组聚合生成，不对应 ext 数据里的真实字段。
- **`firstMatchingField` 兜底**：若关键词都不匹配，取第一个非 symbol/code 的 string 字段（[ExtPages.tsx:31](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/ExtPages.tsx#L31)），可能不是用户想要的分组字段，需手动确认。
- **并发写菜单**：后端 `_save` 无文件锁，多个请求同时写同一菜单 id 会出现后写覆盖前写；当前为单用户桌面场景，未加锁。
- **导航顺序**：本 Tab 新建菜单 `order = menuItems.length + 100`，会排在已有菜单之后；如需调整顺序需去「菜单设置」Tab 拖动（调用 `analysisMenuReorder`）。
