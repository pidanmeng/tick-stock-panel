---
title: 数据源设置
description: 数据源设置页功能文档 — 能力路由、数据源管理、插件 Key、TickFlow 档位与端点。
---

# 数据源设置（设置 → 数据源） — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

数据源设置页是「设置」页签之一（Tab id `data-sources`，前端外壳见 [Settings.tsx:22-30](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx)），负责管理 TSP 全部行情/财务数据的**来源路由**：按数据能力维度（实时、日K、分钟、复权因子、5 档盘口、财务）选择 provider（TickFlow 内置源 / 插件 / YAML 自定义源），配置 TickFlow API Key 与档位，管理插件依赖安装与自定义源增删改查，并支持端点测速切换。

核心定位：**数据集维度单一权威路由的唯一 UI 入口**，上层业务只能经 `get_provider()` / 偏好能力路由访问数据（`backend/app/data_providers/capabilities.py`）。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 入口 | `backend/app/api/settings.py` | 全部设置端点：key 保存/清除、数据源 CRUD、插件安装、能力矩阵 |
| 能力注册表 | `backend/app/data_providers/capabilities.py` | `CAPABILITY_REGISTRY` + `build_capability_matrix`（矩阵组装） |
| 能力检测 | `backend/app/tickflow/policy.py` | `detect_capabilities` / `base_tier_name` / `tier_label` / 探测日志 |
| 自定义源加载 | `backend/app/data_providers/custom/` | YAML 源解析、插件清单、`probe_plugin_key`、`install_plugin` |
| 密钥存储 | `backend/app/secrets_store.py` | `get_tickflow_key` / `mask` / `save` / `clear`（secrets.json） |
| 偏好存储 | `backend/app/services/preferences.py` | 7 个 provider 路由 getter/setter + 各类偏好 |
| TickFlow 客户端 | `backend/app/tickflow/client.py` | `current_mode` / `current_endpoint` / `reset_clients` |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/settings/DataSources.tsx` | 能力路由卡片、数据源列表、TickFlow 详情、插件 Key |
| 编辑器 | `frontend/src/pages/settings/DataSourceEditor.tsx` | 自定义 YAML 源的编辑表单 |
| API 客户端 | `frontend/src/lib/api.ts` | `dataSources` / `capabilityMatrix` / `updateDataProviders` / `savePluginKey` 等 |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `QK.dataSources` / `QK.capabilityMatrix` 等 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 密钥 | `data/secrets.json` | TickFlow key、插件 key、自定义端点 |
| 偏好 | `data/preferences.json` | provider 路由、超时、压缩等全部偏好 |
| 自定义源 | `data/data_sources/*.yaml` | 用户自定义数据源定义 |

## 业务逻辑

### 核心流程

数据源设置页由四个区块组成，互不阻塞：

```text
能力路由区: 7 个能力 × 候选 provider chips → 点击 chip → 乐观更新 → PUT /preferences/data-providers → 刷新 capabilities 快照
数据源列表: GET /data-sources → 内置 tickflow + plugins + custom + errors → 卡片展示能力/安装/编辑/删除
TickFlow 详情: 探测档位 → TierTag + 能力表 → 存 key(先探后存) / 清除 / 重探测 / 端点测速切换
插件区:      probe key(先探后存) → 存 secrets.json → load_all 重扫 → 可切换
```

### 数据流

1. **输入来源**：用户操作（路由切换、key 输入、自定义源表单）、TickFlow 官方端点清单（`endpoints.json` 代理拉取）、插件 manifest（YAML）。
2. **处理过程**：
   - **先探后存**：`POST /tickflow-key` 先用新 key 强制探测档位（[settings.py:131-211](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)），`is_invalid_key()` 或档位 `none` → 清除 key 回滚并返回 `{ok:false, reason:"invalid"}`；档位 `free` → 清除自定义端点；`starter+` → 确保 `DEFAULT_PAID_ENDPOINT`（`https://api.tickflow.org`，[settings.py:31](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。探测结果同步 `app.state.capabilities` 与财务调度器能力（`_sync_financial_scheduler_caps`，[settings.py:34-46](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
   - **能力矩阵组装**：`GET /capability-matrix` 将偏好路由（getters 自带合法源校验）+ TickFlow 档位注入 `build_capability_matrix`（[settings.py:578-600](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)），候选 provider 按档位过滤。
   - **插件 key 探测**：`POST /plugin-key` 调 `probe_plugin_key` 实探，有效才写 `secrets.json`（`{name}_api_key`，优先级高于 .env），再 `load_all` 重扫（[settings.py:603-627](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
   - **自定义源 CRUD**：保存/删除 YAML 后自动 `load_all`；删除被路由选中的源时回退偏好到 `tickflow` 并刷新能力快照（[settings.py:728-755](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
   - **插件卸载回退**：卸载正在被使用的插件时，4 个路由（daily/minute/realtime/financial）自动回退 tickflow（[settings.py:677-701](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
   - **端点切换**：仅 `api_key` 模式（付费档）允许，持久化 `tickflow_base_url` 并 `reset_clients`（[settings.py:105-128](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
3. **输出去向**：偏好写入 `preferences.json`、密钥写入 `secrets.json`、自定义源写入 `data/data_sources/*.yaml`；能力快照写入 `app.state.capabilities`；前端通过 `invalidateSources()` 一次性失效 dataSources / capabilityMatrix / preferences / capabilities / quoteStatus。

### 调用链

```text
前端 DataSources.tsx（乐观更新）
  → api.updateDataProviders / api.saveTickflowKey / api.savePluginKey（frontend/src/lib/api.ts）
  → PUT /api/settings/preferences/data-providers 或 POST /api/settings/tickflow-key 等（backend/app/api/settings.py）
  → preferences.save()（backend/app/services/preferences.py）或 secrets_store.save()（backend/app/secrets_store.py）
  → detect_capabilities(force=True)（backend/app/tickflow/policy.py）→ app.state.capabilities 快照
  → 上层业务经 capabilities.get_provider() 按偏好路由取数（backend/app/data_providers/capabilities.py）
```

### 状态机（TickFlow 档位）

```text
none（无档）──存有效免费 key──▶ free（free-api 服务器）
   │                                │
   └──存付费 key──▶ api_key（starter+，付费端点 DEFAULT_PAID_ENDPOINT）
   ▲                │
   └──清除 key──────┘
```

档位联动规则：
- `none`/`free` 禁止切换端点（`switch_endpoint` 返回错误，[settings.py:113-114](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
- `free` 档清除自定义端点（[settings.py:182-194](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）；`starter+` 无自定义端点时自动写入默认付费端点。
- `none`/`free` 档 `realtime_allowed=False`，实时行情开关强制回弹（见 monitoring-settings.md）。

## 关键数据结构

### API 契约

**能力 ID 与标签**（`DATASET_LABEL`，[DataSources.tsx:48-56](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/DataSources.tsx)）：

| 能力 ID | 标签 | 说明 |
|---------|------|------|
| realtime | 实时行情 | 全市场实时快照 |
| daily | 日K | 日线历史 |
| minute | 分钟K | 分钟历史（盘中增量另有 full_minute） |
| full_minute | 全量分钟 | 盘中分钟增量落盘 |
| adj_factor | 复权因子 | 前复权计算 |
| depth5 | 5档盘口 | 连板梯队限价监控 |
| financial | 财务数据 | 三大报表等 |

**`GET /api/settings/data-sources` 响应**（[settings.py:565-575](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：

```json
{
  "builtin": [{"name": "tickflow", "display_name": "TickFlow", "datasets": ["daily", "adj_factor", "realtime", "minute"]}],
  "plugins": [...],        // custom_sources.list_plugins()
  "custom": [...],         // custom_sources.list_sources()
  "errors": [...],         // YAML 解析错误收集
  "config_dir": "data/data_sources"
}
```

**`PUT /api/settings/preferences/data-providers` 请求体**（`DataProvidersIn`，[settings.py:411-418](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：7 个可选字段 `daily_data_provider` / `adj_factor_provider` / `minute_data_provider` / `full_minute_data_provider` / `depth5_data_provider` / `realtime_data_provider` / `financial_data_provider`，均为 provider 名字符串。

**`POST /api/settings/tickflow-key` 响应**：`{ok, mode, tier_label, current_endpoint, probe_log, capabilities_count, tickflow_api_key_masked}`；无效 key 时 `{ok:false, reason:"invalid"}`。

**自定义源模型**：`CustomSourceIn`（`name/display_name/auth/datasets`，[settings.py:472-476](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）；`DatasetConfigIn`（url/method/batch/rpm/response_path/field_map/transforms/符号与时间参数名/timeout，[settings.py:444-462](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）；`AuthConfigIn`（type/token_env/header/param，[settings.py:465-469](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。

### 存储结构

- **secrets.json**：`tickflow_api_key`、`tickflow_base_url`、`{plugin}_api_key`（优先级高于同名 .env 变量）。
- **preferences.json**：7 个 `*_data_provider` 路由键；`data_source_job_timeout_s`（默认 1200）、`data_source_long_job_timeout_s`（默认 1800）；`minute_batch_compress` / `daily_batch_compress`（默认 true）。
- **data/data_sources/*.yaml**：自定义数据源定义（`data_sources_dir()` 提供路径）。

### 内存结构

- `app.state.capabilities`：探测结果 CapabilitySet，作为上层能力门禁唯一依据；`data-sources` 相关写操作后均刷新。
- `app.state.financial_scheduler`：启动时捕获旧能力引用，需 `update_capabilities(capset)` 显式刷新（[settings.py:34-46](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。
- `_endpoints_cache`：端点清单进程内缓存 `{ts, data}`，TTL 300s（[settings.py:1576-1631](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- 在 `data/data_sources/` 下新增 YAML 自定义数据源，通过 UI「编辑」表单或直接写 YAML 均可；保存后自动 reload。
- 通过「设置 → 数据源 → 能力路由」把任一能力切到自定义源/插件，无需改代码。
- 插件 key 可通过 `.env` 或 UI（secrets.json，优先级更高）配置。

### L2 扩展（插槽/路由/注册替换）

- **Provider 插件机制**：`backend/app/data_providers/custom/` 按 plugin.yaml 的 `runtime` 字段支持 npm/pip 依赖自动安装（`POST /api/settings/plugins/{name}/install`）；插件 manifest 声明 `api_key_env` 即可获得 UI key 配置入口。
- **能力注册表**：`CAPABILITY_REGISTRY` 是数据集维度唯一权威，新增能力需在此登记，上层才能经偏好路由访问。

### L3 修改（直接改源码）

- 新增内置数据集能力：改 `capabilities.py` 注册表 + `settings.py` 的 `DataProvidersIn` 与 `get_preferences` + 前端 `DataSources.tsx` 的 `DATASET_LABEL`/`DEFAULT_ROUTING`，并同步 `invalidateSources()`。
- 改动 provider 路由偏好读写的缓存层：偏好值 → 能力快照 → 各业务服务缓存 → SSE → 前端，需逐层列影响（见下）。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件缓存 | `preferences.save()` 直接写盘 | preferences.json / secrets.json / YAML 源 |
| 内存缓存 | 写操作后 `detect_capabilities()` 刷新 `app.state.capabilities`；`financial_scheduler.update_capabilities` | 全部上层能力门禁 |
| API/前端 | `invalidateSources()` 失效 dataSources/capabilityMatrix/preferences/capabilities/quoteStatus | 数据源页 + 依赖能力的页面 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| API 测试 | `backend/tests/` | tickflow-key 无效 key 回滚、free/starter+ 端点联动、插件 key 探测、数据源 CRUD、卸载回退 |
| 能力矩阵 | `backend/tests/` | 偏好非法值回退、档位候选过滤 |
| 前端 | `frontend/src/` | 乐观更新回滚、先探后存提示（invalid 文案） |

## 依赖关系

### 依赖的其他功能

- [定时任务与管道](architecture-and-infrastructure.md)：数据源决定盘后管道与盘中增量拉取内容。
- [实时行情监控设置](monitoring-settings.md)：`realtime_allowed` 档位门禁、`realtime_quotes_enabled` 联动。

### 被依赖的功能

- 所有数据消费方（看板/自选/选股/回测/个股分析）经能力路由获取 provider 数据。
- 端点代理（`GET /endpoints`）被 TickFlow 详情测速区使用。

## 常见问题与注意事项

- **Key 校验严格性**：乱填 key 会被探测后清除并回滚档位（先探后存），不会静默持久化；无效 key 的探测日志清空后前端提示「Key 无效」。
- **档位与端点绑定**：`free` 档运行时走 free-api 服务器，即使残留付费端点也会被清除；`none/free` 档切换端点会被拒绝。
- **自定义源写盘前请先「测试」**：`POST /data-sources/test` 试拉不写盘，避免保存后才发现的 YAML 配置错误进入生产。
- **删除/卸载回退**：删除被路由选中的自定义源、卸载被使用的插件都会把对应路由回退到 tickflow，属预期行为，不会静默断源。
- **能力快照一致性**：任何 provider 路由变化后都必须刷新 `app.state.capabilities`，否则上层能力门禁读到旧快照（如升级 Expert 后「全部同步」仍被拒）。
