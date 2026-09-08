---
title: 菜单设置
description: 设置页「菜单设置」Tab 的完整参考，涵盖左侧导航菜单的排序、隐藏、监控中心徽标开关的实现、数据流、调用链与扩展方式。
---

# 菜单设置（设置 → 菜单设置） — 功能文档

> 本 Tab 位于 [Settings.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L32-L40) 的第 6 个 Tab，`key='menus'`、label「菜单设置」、图标 `SlidersHorizontal`，对应面板组件 `SettingsMenuSettingsPanel`（[MenuSettings.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx)）。核心定位：让用户通过拖拽调整左侧全局导航的展示顺序，通过眼睛图标控制单个菜单项在侧边栏的显示/隐藏，并为「监控中心」提供独立的未读数字徽标开关。所有顺序与隐藏配置持久化到后端 `preferences.json`，徽标开关仅存浏览器 `localStorage`。

## 功能概述

「菜单设置」是用户对全局左侧导航栏的个性化入口。它不创建新菜单，只消费两类菜单项源：
1. 18 个**内置页面**（由 [Layout.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L84-L103) 的 `nav` 常量定义，MenuSettings 内有一份同顺序的 `BUILTIN_PAGES` 镜像）。
2. **扩展分析菜单**（通过 `/api/analysis-menus` 获取，见 [analysis.py](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L12-L128)）。

面板提供三列操作：拖拽手柄（重排序）、眼睛图标（显示/隐藏）、铃铛图标（仅 `/monitor` 一行，控制未读数字徽标）。排序与隐藏写入后端偏好 `nav_order` / `nav_hidden`，由 [Layout](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L543-L586) 读取后渲染侧边栏；徽标开关仅写 `localStorage.monitor_badge_enabled`，由 [MonitorBadge](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L137-L150) 读取。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 设置 API 路由 | `backend/app/api/settings.py` | 暴露 `GET /api/settings/preferences`（返回 `nav_order`/`nav_hidden`，见 [settings.py:494-562](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L494-L562)）、`PUT /preferences/nav-order`（[settings.py:855-861](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L855-L861)）、`PUT /preferences/nav-hidden`（[settings.py:863-869](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L863-L869)） |
| 偏好服务 | `backend/app/services/preferences.py` | `get_nav_order`/`set_nav_order`（[preferences.py:1039-1047](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L1039-L1047)）、`get_nav_hidden`/`set_nav_hidden`（[preferences.py:1050-1058](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L1050-L1058)），统一以 `load()`/`save()` 读写 preferences.json |
| 分析菜单 API | `backend/app/api/analysis.py` | `GET /api/analysis-menus` 返回扩展分析菜单（含 `visible`、`order`，[analysis.py:12-128](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L12-L128)），作为菜单设置的扩展项来源 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 面板组件 | `frontend/src/pages/settings/MenuSettings.tsx` | 拖拽排序 / 显示隐藏 / 监控徽标开关的完整 UI 与写操作（[MenuSettings.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx)） |
| 设置外壳 | `frontend/src/pages/Settings.tsx` | Tab 注册 `key='menus'` → `SettingsMenuSettingsPanel`（[Settings.tsx:38](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L38)） |
| Layout 侧边栏 | `frontend/src/components/Layout.tsx` | 消费 `nav_order`/`nav_hidden` 渲染可见菜单（[Layout.tsx:543-586](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L543-L586)），`MonitorBadge` 读 `localStorage.monitor_badge_enabled`（[Layout.tsx:137-150](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L137-L150)） |
| API 客户端 | `frontend/src/lib/api.ts` | `api.preferences`、`api.saveNavOrder`、`api.saveNavHidden`、`api.analysisMenus`（[api.ts:1929](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1929)、[api.ts:2225-2234](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2225-L2234)、[api.ts:2914-2915](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2914-L2915)） |
| 共享查询 | `frontend/src/lib/useSharedQueries.ts` | `usePreferences()`（[useSharedQueries.ts:43-48](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts#L43-L48)） |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `QK.preferences`、`QK.analysisMenus`（[queryKeys.ts:16,77](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L16)） |
| 类型 | `frontend/src/lib/api.ts` | `Preferences.nav_order: string[]`、`Preferences.nav_hidden: string[]`（[api.ts:1838-1839](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1838-L1839)） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 偏好持久化 | `data/preferences.json`（路径由 `preferences.load/save` 决定） | 持久化 `nav_order`、`nav_hidden` 字段，跨设备/清缓存安全 |
| 本地存储键 | 浏览器 `localStorage.monitor_badge_enabled` | 监控中心未读徽标开关（仅前端，见 [MenuSettings.tsx:280-288](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L280-L288)） |

## 业务逻辑

### 核心流程

1. **加载**：面板通过 `usePreferences()` 取 `nav_order`/`nav_hidden`，通过 `useQuery(QK.analysisMenus, api.analysisMenus)` 取扩展分析菜单，合并内置 `BUILTIN_PAGES` 与扩展项得到 `allEntries`，再按保存顺序重排（未保存过的新内置页插回默认位置，扩展项追加末尾）。
2. **排序**：用户拖拽 `SortableItem` 的手柄 → `onDragEnd` 用 `arrayMove` 计算新顺序 → `setLocalOrder` 乐观更新 → `api.saveNavOrder` 落盘 → 成功后 `invalidateQueries(QK.preferences)`。
3. **隐藏**：点击眼睛图标 → 切换 `hiddenSet` 中的 id → `api.saveNavHidden([...next])` → 成功后失效 `QK.preferences`。
4. **徽标**：仅 `/monitor` 行的铃铛按钮 → 切换 `localStorage.monitor_badge_enabled`（`'1'`/`'0'`），不调后端；`Layout.MonitorBadge` 渲染时读同一键决定是否显示未读数。

```text
加载 preferences + analysis-menus
  → 合并内置/扩展项 → 按 nav_order 重排
  → [拖拽] arrayMove → saveNavOrder → invalidate preferences
  → [眼睛] toggle hidden → saveNavHidden → invalidate preferences
  → [铃铛] 写 localStorage.monitor_badge_enabled (仅前端)
```

### 数据流

1. **输入来源**：
   - `GET /api/settings/preferences` → `nav_order` / `nav_hidden`
   - `GET /api/analysis-menus` → 扩展分析菜单（`{items: AnalysisMenu[]}`）
   - `localStorage.monitor_badge_enabled`（初始值，`'0'` 表示关闭）
2. **处理过程**：
   - `allEntries`：把 `BUILTIN_PAGES`（18 项）与分析菜单合并，按 `prefs.nav_order` 重排；未在保存列表中的新内置页按默认顺序插回前驱之后，新扩展项追加到末尾（[MenuSettings.tsx:177-209](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L177-L209)）。
   - `orderedEntries`：再叠加本地乐观排序 `localOrder`（拖拽进行中临时覆盖 `nav_order`，保存成功后清空），重排逻辑同上（[MenuSettings.tsx:214-240](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L214-L240)）。
   - `hiddenSet`：`new Set(prefs.nav_hidden ?? [])`（[MenuSettings.tsx:211](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L211)）。
3. **输出去向**：
   - `PUT /api/settings/preferences/nav-order` → `preferences.json.nav_order`
   - `PUT /api/settings/preferences/nav-hidden` → `preferences.json.nav_hidden`
   - `localStorage.monitor_badge_enabled` 写入浏览器本地
   - 写成功后失效 `QK.preferences`，`Layout` 侧栏随之重排/显隐

### 调用链

**排序写操作**：
```text
SortableItem drag (MenuSettings.tsx:310-330)
  → handleDragEnd (MenuSettings.tsx:260-270)
  → arrayMove + setLocalOrder (乐观)
  → saveNavOrder.mutate (MenuSettings.tsx:242-248)
  → api.saveNavOrder PUT /api/settings/preferences/nav-order (api.ts:2225-2229)
  → update_nav_order (settings.py:855-861)
  → preferences.set_nav_order → save (preferences.py:1044-1047)
  → onSuccess: setLocalOrder(null) + qc.invalidateQueries(QK.preferences)
```

**隐藏写操作**：
```text
眼睛按钮 onClick (MenuSettings.tsx:112-123)
  → toggleHidden (MenuSettings.tsx:272-277)
  → saveNavHidden.mutate (MenuSettings.tsx:250-253)
  → api.saveNavHidden PUT /api/settings/preferences/nav-hidden (api.ts:2230-2234)
  → update_nav_hidden (settings.py:863-869)
  → preferences.set_nav_hidden (preferences.py:1055-1058)
  → onSuccess: invalidateQueries(QK.preferences)
```

**侧栏渲染消费**：
```text
Layout 读取 prefs.nav_order / nav_hidden (Layout.tsx:556-586)
  → navItems 重排 → visibleNavItems 过滤隐藏项
  → 侧边栏 map 渲染 (Layout.tsx:738-866)
```

## 关键数据结构

### API 契约

- `GET /api/settings/preferences` 响应包含：
  - `nav_order: string[]` — 有序的菜单 id 列表。内置页用其 path（如 `/`、`/watchlist`）；扩展分析菜单用菜单 id（在 Layout 中通过 `/analysis/${id}` 反查，见 [Layout.tsx:561-563](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L561-L563)）。
  - `nav_hidden: string[]` — 隐藏项 id 列表（同上语义）。
- `PUT /api/settings/preferences/nav-order` 请求体 `{ nav_order: string[] }`，响应 `{ nav_order: string[] }`。
- `PUT /api/settings/preferences/nav-hidden` 请求体 `{ nav_hidden: string[] }`，响应 `{ nav_hidden: string[] }`。
- `GET /api/analysis-menus` 响应 `{ items: AnalysisMenu[] }`，`AnalysisMenu` 含 `id`、`label`、`visible`、`icon`、`order`（[analysis.py:12-128](file:///c:/Code/tick-stock-panel/backend/app/api/analysis.py#L12-L128)）。

### 存储结构

- `preferences.json` 两个顶层字段：
  - `nav_order: ["/", "/watchlist", ...]`
  - `nav_hidden: ["/abnormal", "/signals", ...]`
- 浏览器 `localStorage.monitor_badge_enabled`：`'1'`（默认，开启）或 `'0'`（关闭）。

### 内存结构

- 前端 `allEntries: NavEntry[]`（含 `id`/`label`/`type`/`visible`，[MenuSettings.tsx:26-31](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L26-L31)）。
- `localOrder: string[] | null` — 拖拽过程的乐观顺序，保存成功置 null（[MenuSettings.tsx:214](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L214)）。
- `hiddenSet: Set<string>` — 当前隐藏项集合（[MenuSettings.tsx:211](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L211)）。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **新增内置菜单项**：需在 [Layout.tsx:84-103](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L84-L103) 的 `nav` 数组与 [MenuSettings.tsx:34-53](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L34-L53) 的 `BUILTIN_PAGES` 中**同步**添加，两者顺序需保持一致（否则「未保存排序的新内置页插回默认位置」逻辑会错位）。
- **扩展分析菜单**：通过扩展页（设置 → 扩展页面）新增或直接写分析菜单数据源；菜单设置面板会自动通过 `/api/analysis-menus` 拉取并显示为 `type:'analysis'`（扩展）。
- **隐藏菜单**：直接编辑 `preferences.json` 的 `nav_hidden` 字段（字符串数组，元素为 path 或分析菜单 id）。

### L2 扩展（插槽/路由/注册替换）

- 前端扩展导航项通过 `getFrontendExtensionNavigation()`（[Layout.tsx:548-553](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L548-L553)）注册，进入 `allNav` 参与排序；但 **MenuSettings 当前并未把扩展导航项纳入可排序列表**（仅内置 + 分析菜单），扩展项在保存顺序中缺失时会被追加到末尾。如需支持扩展项的排序/隐藏，需在 `MenuSettings` 中也读取 `getFrontendExtensionNavigation()`。
- 菜单设置面板本身没有提供插槽；若要增加操作列（例如针对某类菜单的额外开关），需改 `SortableItem` 列定义（[MenuSettings.tsx:80-160](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L80-L160)）。

### L3 修改（直接改源码）

- **调整列布局**：`grid-cols-[2.5rem_1fr_4.5rem_3rem_3rem_3rem]`（[MenuSettings.tsx:84,301](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L84)）表头与行使用相同列模板，改动需同步两处。
- **改变默认菜单顺序**：`BUILTIN_PAGES` 与 `Layout.nav` 必须同步改，且 `nav_order` 里已保存的旧顺序不会自动迁移，老用户需手动重排。
- **将徽标开关改为后端持久化**：需在 `preferences` 增加字段、`Settings.preferences` 响应、`Preferences` 类型、`update_*` 路由与 `api.*` 方法，并把 `MonitorBadge` 的 `localStorage` 读取改为 `usePreferences()`。
- **加入「恢复默认」按钮**：可调用 `saveNavOrder([])` 与 `saveNavHidden([])` 清空两个偏好，让 Layout 回退到 `nav` 默认顺序。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| React Query `QK.preferences` | `saveNavOrder`/`saveNavHidden` 的 `onSuccess` 中 `invalidateQueries({queryKey: QK.preferences})`（[MenuSettings.tsx:246,252](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L246)） | 全局 Layout 侧边栏、监控开关、数据同步等所有依赖 preferences 的组件立即重渲染 |
| React Query `QK.analysisMenus` | 不在本面板写入；若扩展页变更分析菜单，需失效此 key | 菜单设置与 Layout 的分析菜单列表 |
| `localStorage.monitor_badge_enabled` | 直接写，无缓存层；Layout 的 `MonitorBadge` 在每次渲染时读取 | 仅影响监控中心未读徽标显示，不触发 SSE |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 前端交互 | `frontend/src/pages/settings/MenuSettings.tsx`（待确认是否有对应 `*.test.tsx`） | 拖拽重排序后调用 `saveNavOrder`；眼睛点击切换 `nav_hidden`；监控行铃铛切换 `localStorage` |
| 后端偏好 | `backend/app/services/preferences.py` | `set_nav_order`/`set_nav_hidden` 读写 preferences.json 一致 |
| 后端路由 | `backend/app/api/settings.py` | `PUT /preferences/nav-order`、`PUT /preferences/nav-hidden` 正常与空列表路径 |

> 注：仓库内是否存在对应的单测/集成测文件需另行确认（本调研范围未覆盖测试目录）。

## 依赖关系

### 依赖的其他功能

- 「扩展页面」（设置 → ext-pages Tab）：管理扩展分析菜单，本面板通过 `/api/analysis-menus` 展示其产物。
- 「偏好设置」后端服务（`app.services.preferences`）：持久化 `nav_order`/`nav_hidden`。
- 「监控中心」未读徽标（`lib/monitorBadge` + `Layout.MonitorBadge`）：消费 `localStorage.monitor_badge_enabled`。

### 被依赖的功能

- 全局 Layout 侧边栏：消费 `nav_order`/`nav_hidden` 决定菜单顺序与显隐。
- 设置页 Tab 外壳：本面板是其中一个 Tab。

## 常见问题与注意事项

- **`BUILTIN_PAGES` 与 `Layout.nav` 必须保持同顺序**：二者是两份独立常量（[MenuSettings.tsx:34-53](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/MenuSettings.tsx#L34-L53) 与 [Layout.tsx:84-103](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L84-L103)），新增内置页时若只改一处，排序锚点算法（`findIndex` 前驱定位）会把新项插错位置。
- **扩展导航项（`getFrontendExtensionNavigation`）当前不可排序/隐藏**：Layout 会渲染它们并参与 `nav_order` 合并，但 MenuSettings 的 `allEntries` 不含它们，因此它们始终被追加到末尾且无法在面板里隐藏。如需支持需显式引入。
- **`nav_order`/`nav_hidden` 不区分内置 path 与分析菜单 id**：Layout 在反查时同时尝试 `byTo.get(id)` 与 `byTo.get('/analysis/' + id)`（[Layout.tsx:561-563](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L561-L563)），隐藏过滤同理（[Layout.tsx:585-586](file:///c:/Code/tick-stock-panel/frontend/src/components/Layout.tsx#L585-L586)）。
- **监控徽标开关不进后端**：`localStorage.monitor_badge_enabled` 仅当前浏览器生效，清缓存或换设备后回到默认开启。
- **拖拽是乐观更新**：`localOrder` 会临时覆盖服务端顺序，仅在 `saveNavOrder` 成功后清空并失效缓存；若保存失败，`localOrder` 不会被清空（代码中未处理失败回滚），刷新页面后会回退到服务端顺序。
- **无「恢复默认」入口**：清空排序/隐藏只能通过直接编辑 preferences.json 或调用对应 PUT 传空数组实现。
- **性能**：`allEntries` 与 `orderedEntries` 两个 `useMemo` 都包含一段「未保存项插回默认位置」的 O(n²) 锚点查找逻辑；菜单数量在几十级，可忽略。
