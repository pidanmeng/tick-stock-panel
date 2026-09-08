---
title: 实时监控设置
description: 设置 → 实时监控 Tab 的完整功能文档，涵盖行情轮询、页面 SSE 刷新、分时图刷新、全量分钟落盘、连板梯队真假板修正、以及飞书/企业微信/第三方/邮件/智能机器人等推送渠道的配置与校验逻辑。
---

# 实时监控设置（设置 → 实时监控） — 功能文档

> 该 Tab 位于设置页左侧竖向 Tab 栏第 3 项，Tab key = `monitoring`、label = `实时监控`、icon = `Radio`，由 [Settings.tsx:35](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L35) 注册并通过 `SettingsMonitoringPanel` 渲染（[Settings.tsx:124-126](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L124-L126)）。核心定位：集中管理实时行情开关与轮询节奏、SSE 页面刷新范围、分时/全量分钟落盘策略、连板梯队五档盘口修正、以及监控告警的全部外部推送渠道（飞书 / 企业微信 / 第三方 JSON Webhook / SMTP 邮件 / 企业微信智能机器人长连接）。

## 功能概述

「实时监控」Tab 是 TSP 盘中实时数据与告警推送的统一配置中心。它承担三类职责：

1. **行情节奏控制**：实时行情总开关、全市场轮询间隔（按档位 clamp）、分时图刷新间隔、全量分钟增量落盘间隔；
2. **页面实时刷新范围**：通过 `sse_refresh_pages` 控制哪些页面跟随 SSE 推送刷新；
3. **告警推送渠道**：配置并测试飞书 / 企业微信群 Webhook / 第三方 JSON Webhook / SMTP 邮件 / 企业微信智能机器人（长连接），并设置新建监控规则的默认推送渠道。

所有配置均持久化到后端 `preferences.json`（非敏感字段）或 `secrets_store`（Webhook 密钥、SMTP 密码），前端通过 React Query 的 `QK.preferences` 统一读写，写操作后失效该 query 实现 UI 同步。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 设置 API | [backend/app/api/settings.py](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py) | 实时监控相关全部 REST 端点（preferences 聚合 / realtime-quotes / quote-interval / realtime-monitor / minute-refresh/status / webhook 系列 / limit-ladder-monitor） |
| 偏好服务 | [backend/app/services/preferences.py](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py) | 所有监控相关配置的 getter/setter、clamp 区间、默认值 |
| 行情服务 | [backend/app/services/quote_service.py](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py) | `QuoteService` 单例：实时开关启停、轮询间隔 clamp（按档位）、暂停态 |
| Webhook 适配 | `backend/app/services/webhook_adapter.py` | URL 校验、各渠道发送（本 Tab 仅调用其 `is_valid_*_url` / `send_*`） |
| 邮件适配 | `backend/app/services/email_adapter.py` | SMTP 配置校验与发送 |
| 密钥存储 | `backend/app/services/secrets_store.py` | 第三方 Webhook secret、SMTP password 的持久化（非 preferences.json） |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 监控面板页面 | [frontend/src/pages/settings/Monitoring.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx) | Tab 主体：6 张卡片的渲染、草稿态、防抖保存、渠道校验 |
| 设置外壳 | [frontend/src/pages/Settings.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx) | Tab 注册与 `?tab=monitoring&highlight=` 路由 |
| API 客户端 | [frontend/src/lib/api.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts) | 所有监控相关 API 方法与类型定义 |
| 查询键 | [frontend/src/lib/queryKeys.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts) | `preferences` / `quoteStatus` / `quoteInterval` 等 key |
| 共享 Query | [frontend/src/lib/useSharedQueries.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts) | `usePreferences` / `useQuoteStatus` / `useQuoteInterval` / `useCapabilities` |
| 共享 Mutation | [frontend/src/lib/useSharedMutations.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedMutations.ts) | `useToggleRealtimeQuotes` / `useUpdateQuoteInterval` |
| 五档盘口配置 | [frontend/src/components/data/DepthConfigCard.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/data/DepthConfigCard.tsx) | `DepthConfigContent` 子组件（连板修正卡片内嵌入） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 偏好 JSON | `backend/data/preferences.json`（运行时） | 所有非敏感监控配置的持久化存储 |
| 密钥存储 | `backend/data/secrets.json`（运行时，secrets_store） | 第三方 Webhook HMAC 密钥、SMTP 密码 |

## 业务逻辑

### 核心流程

本 Tab 的写操作可归为三条独立链路：

**链路 A — 行情开关与轮询间隔**
```text
用户拨动「实时行情」开关 / 拖动「轮询间隔」滑块
  → 2s 防抖（仅间隔）
  → PUT /api/settings/preferences/realtime-quotes 或 PUT /api/settings/preferences/quote-interval
  → 后端 QuoteService.enable()/disable() 或 set_interval()（按档位 clamp）
  → 同步启停 depth 轮询（_sync_depth_polling）
  → 失效 QK.preferences + QK.quoteStatus
  → UI 刷新
```

**链路 B — 实时监控配置（SSE 页面 / 分时图 / 全量分钟 / 策略监控 / ext 字段）**
```text
用户切换任意 ToggleRow / 拖动分时或全量分钟间隔滑块
  → 2s 防抖（仅间隔类）
  → PUT /api/settings/preferences/realtime-monitor（body 为部分字段）
  → preferences.set_realtime_monitor_config() 逐项保存并 clamp
  → 若改动 strategy_monitor_ids/enabled：迁移为 MonitorRule 并 reload monitor_engine
  → 失效 QK.preferences → UI 刷新
```

**链路 C — 推送渠道配置与测试**
```text
用户编辑渠道地址 / 密钥
  → 前端格式预校验（飞书前缀、企业微信 key 长度、HTTP(S) URL）
  → 点「保存」→ PUT 对应端点 → 后端 webhook_adapter/email_adapter 再校验 → 写入 preferences / secrets_store
  → 失效 QK.preferences
  → 点「测试」→ POST /api/settings/preferences/webhook-test { channel }
  → 后端读取已保存配置（非草稿）单发一次 → 返回 { ok, detail }
  → 前端 TestResult 渲染绿/红（成功 2s 自动消失）
```

**连板梯队修正**（独立于上述链路）：
```text
切换「启用真假板修正」→ PUT /api/settings/preferences/limit-ladder-monitor → depth_service.apply_monitor_toggle()
点「立即修正」→ POST /api/settings/preferences/limit-ladder-monitor/run → depth_service.run_once() → invalidate_overview_cache()
```

### 数据流

1. **输入来源**：
   - 用户在 6 张卡片上的 Toggle / Slider / Input 操作；
   - `usePreferences()`（`GET /api/settings/preferences`）聚合返回所有初始值；
   - `useQuoteStatus()`（`GET /api/intraday/status`）提供 `running` / `paused` / `is_trading_hours` / `mode`；
   - `useQuoteInterval()`（`GET /api/settings/preferences/quote-interval`）提供当前间隔与档位限制 `min_interval` / `max_interval`；
   - `useCapabilities()` 提供 `depth5.batch` 与 `intraday.universe` 能力门控；
   - `minuteRefreshStatus` query（15s 轮询 `GET /api/settings/minute-refresh/status`）提供全量分钟服务运行状态。

2. **处理过程**：
   - 前端为每个可保存字段维护 `xxxDraft` 本地草稿态，`useEffect` 同步服务端值→草稿；
   - 滑块类（行情间隔、分时间隔、全量分钟间隔）采用 **2s 防抖** 落库（[Monitoring.tsx:321-355](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L321-L355)）；
   - Toggle 类即时保存，无防抖；
   - 后端 `set_realtime_monitor_config` 对间隔字段再次 clamp（[preferences.py:988-1021](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L988-L1021)）；
   - Webhook / SMTP 保存时后端二次校验 URL / 邮箱格式，失败抛 400；
   - 实时行情开启时后端执行三重门禁（档位权限 / 本地无数据 / 数据完整性扫描），任一不满足返回 409。

3. **输出去向**：
   - 非敏感字段 → `preferences.json`（`preferences.save()`）；
   - 敏感字段（custom secret、email password）→ `secrets_store`；
   - 实时行情开关 → `QuoteService._enabled` + 轮询线程启停；
   - 轮询间隔 → `QuoteService._interval`（立即生效）；
   - 策略监控 → `monitor_engine.set_rules()` 重载规则。

### 调用链

**实时行情开关**：
```text
Monitoring.tsx:158 handleToggleQuote
  → useToggleRealtimeQuotes (useSharedMutations.ts:9)
  → api.updateRealtimeQuotes (api.ts:2066)
  → PUT /api/settings/preferences/realtime-quotes
  → settings.py:938 update_realtime_quotes
  → QuoteService.enable()/disable() (quote_service.py:296/316)
  → _sync_depth_polling → depth_svc.start_polling()/stop_polling()
  → preferences.save({"realtime_quotes_enabled": ...})
  → 失效 QK.preferences + QK.quoteStatus
```

**行情轮询间隔**：
```text
Monitoring.tsx:321 intervalDraft useEffect(2s防抖)
  → useUpdateQuoteInterval (useSharedMutations.ts:21)
  → api.updateQuoteInterval (api.ts:2105)
  → PUT /api/settings/preferences/quote-interval
  → settings.py:1484 update_quote_interval
  → QuoteService.set_interval() (quote_service.py:382)
  → _clamp_interval → [tier_min, 60]
  → preferences.set_realtime_quote_interval()
  → setQueryData(QK.quoteInterval) + 失效 QK.quoteStatus
```

**SSE 页面 / 分时 / 全量分钟 / 策略监控**：
```text
Monitoring.tsx:149 save(cfg) / 各 ToggleRow.onChange / 防抖 useEffect
  → api.updateRealtimeMonitorConfig (api.ts:2115)
  → PUT /api/settings/preferences/realtime-monitor
  → settings.py:1052 update_realtime_monitor_config
  → preferences.set_realtime_monitor_config (preferences.py:988)
  → [若 strategy_monitor 变动] monitor_engine.set_rules(mr_store.load_all())
  → 失效 QK.preferences
```

**推送渠道（以飞书为例）**：
```text
Monitoring.tsx:187 submitFeishu
  → saveFeishuWebhook mutation → api.updateFeishuWebhook (api.ts:2141)
  → PUT /api/settings/preferences/feishu-webhook
  → settings.py:1193 update_feishu_webhook
  → webhook_adapter.is_valid_feishu_url()
  → preferences.set_feishu_webhook_url() / set_feishu_webhook_secret()
  → 失效 QK.preferences
测试：Monitoring.tsx:217 testFeishu → api.sendTestWebhook('feishu') → POST /api/settings/preferences/webhook-test → settings.py:1324
```

## 关键数据结构

### API 契约

**`GET /api/settings/preferences` 响应中与本 Tab 相关字段**（[settings.py:498-561](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L498-L561)）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `realtime_quotes_enabled` | bool | 实时行情总开关 |
| `realtime_allowed` | bool | 当前档位是否允许实时（none 档为 false） |
| `minute_intraday_refresh` | bool | 分时图实时刷新开关 |
| `minute_intraday_refresh_interval` | int | 分时图刷新间隔秒数，[3, 60]，默认 6 |
| `minute_refresh_enabled` | bool | 全量分钟落盘开关 |
| `minute_refresh_interval` | int | 全量分钟刷新间隔秒数，[3, 120]，默认 6 |
| `sse_refresh_pages` | `Record<string, bool>` | 各页面是否跟随 SSE 刷新 |
| `strategy_monitor_enabled` | bool | 策略监控开关 |
| `strategy_monitor_ids` | `string[]` | 监控的策略 ID 列表 |
| `monitor_ext_fields` | `{ concept, industry }` | 监控 ext 字段配置 |
| `limit_ladder_monitor_enabled` | bool | 连板梯队真假板修正开关 |
| `depth_polling_interval` | float | 五档盘口轮询间隔秒 |
| `feishu_webhook_url` / `feishu_webhook_secret` | string | 飞书 Webhook（secret 明文存储于 preferences） |
| `wecom_webhook_url` | string | 企业微信群 Webhook |
| `custom_webhook_url` | string | 第三方 JSON Webhook URL |
| `custom_webhook_secret_set` | bool | 是否已保存第三方 HMAC 密钥 |
| `email_smtp_config` | `EmailSmtpConfig` | SMTP 配置（不含密码） |
| `email_smtp_password_set` | bool | 是否已保存 SMTP 密码 |
| `wecom_bot_id` / `wecom_bot_secret` | string | 企业微信智能机器人凭证 |
| `wecom_bot_enabled` | bool | 智能机器人长连接开关 |
| `webhook_default_channels` | `string[]` | 新建监控规则的默认推送渠道 |

**`GET /api/settings/preferences/quote-interval`**（[settings.py:1498-1508](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1498-L1508)）：
```ts
{ interval: number; min_interval: number; max_interval: number }
```
- `min_interval` 由档位决定（expert=1, pro=3, starter/free=6，自定义源=1）；
- `max_interval` 恒为 60。

**`GET /api/intraday/status`**（`quoteStatus`，[api.ts:2081-2100](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2081-L2100)）关键字段：
- `enabled` / `running` / `paused` / `mode`（`'none' \| 'watchlist' \| 'full_market'`）/ `is_trading_hours` / `interval_s`。

**`PUT /api/settings/preferences/realtime-monitor` 请求体**（[settings.py:1039-1049](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1039-L1049)）：所有字段可选，仅传需要更新的项。

**`EmailSmtpConfig`**（[api.ts:1846-1853](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1846-L1853)）：
```ts
{ host: string; port: number; security: 'ssl' | 'starttls' | 'none';
  username: string; from_address: string; to_addresses: string[] }
```

**`WecomBotStatus`**（[api.ts:1772-1779](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1772-L1779)）：
```ts
{ enabled: boolean; running: boolean; connected: boolean;
  bot_id_configured: boolean; secret_configured: boolean; last_error: string }
```

**`GET /api/settings/minute-refresh/status`**（[api.ts:2019-2041](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2019-L2041)）：
```ts
{ available, enabled, running, healthy, provider, provider_effective,
  repair_only, interval_seconds, capability_ok, in_trading_hours, gate_reason,
  rounds, last_round_at, last_round_ms, last_rows, last_symbols, last_requests,
  next_round_at, last_error }
```

### 存储结构

- **preferences.json** 键（非敏感）：`realtime_quotes_enabled`、`realtime_quote_interval`、`sse_refresh_pages`、`minute_intraday_refresh`、`minute_intraday_refresh_interval`、`minute_refresh_enabled`、`minute_refresh_interval`、`strategy_monitor_enabled`、`strategy_monitor_ids`、`monitor_ext_fields`、`limit_ladder_monitor_enabled`、`depth_polling_interval`、`feishu_webhook_url`、`feishu_webhook_secret`、`wecom_webhook_url`、`custom_webhook_url`、`email_smtp_config`、`wecom_bot_id`、`wecom_bot_secret`、`wecom_bot_enabled`、`webhook_default_channels`。
- **secrets_store** 键（敏感）：`custom_webhook_secret`、`email_smtp_password`。
- 间隔 clamp 常量（[preferences.py:123-124](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L123-L124)、[preferences.py:202-203](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L202-L203)）：分时 `[3, 60]`、全量分钟 `[3, 120]`。

### 内存结构

- **QuoteService**（[quote_service.py:197-266](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py#L197-L266)）：`_enabled`、`_running`、`_paused`、`_interval`、`_subscribers`（SSE 订阅者集合）。
- **前端 React Query 缓存**：`QK.preferences`（本 Tab 几乎所有卡片的数据源）、`QK.quoteStatus`、`QK.quoteInterval`、`['minute-refresh-status']`（15s 轮询）。
- **前端本地草稿态**：各 `xxxDraft` useState（`intervalDraft`、`intradayIntervalDraft`、`minuteRefreshIntervalDraft`、`feishuDraft` 等），与服务端值解耦，防抖或点保存时提交。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- 调整默认推送渠道：直接修改 `webhook_default_channels`（飞书前端勾选默认渠道，[Monitoring.tsx:170-175](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L170-L175)）。
- 调整 SSE 刷新页面列表：修改前端 `PAGE_LABELS` 常量（[Monitoring.tsx:29-33](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L29-L33)），后端 `sse_refresh_pages` 为自由 dict，无需改后端。
- 调整分时/全量分钟间隔范围：改 `preferences.py` 中 `_INTRADAY_REFRESH_INTERVAL_MIN/MAX`、`_MINUTE_REFRESH_INTERVAL_MIN/MAX` 常量，并同步前端滑块 `min/max` 属性。

### L2 扩展（插槽/路由/注册替换）

- 新增推送渠道：需在 `preferences.py` 加 getter/setter、`settings.py` 加 `update_xxx` 与 `webhook-test` 分支、`api.ts` 加方法、`Monitoring.tsx` 加渠道行；无统一注册表，属分散改动。
- 新增页面到 SSE 刷新列表：仅前端 `PAGE_LABELS` 加键值对即可（后端透传）。
- 能力门控：通过 `useCapabilities()` 读取 `caps.capabilities['depth5.batch']` / `['intraday.universe']` 控制卡片禁用态。

### L3 修改（直接改源码）

- 实时行情门禁逻辑集中在 [settings.py:938-1016](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L938-L1016)，新增门禁条件在此函数内追加判断。
- 档位最小间隔映射在 [quote_service.py:201-206](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py#L201-L206) `TIER_MIN_INTERVAL`。
- 防抖时长统一为 2000ms，分散在 Monitoring.tsx 的 3 处 `useEffect`（[L321](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L321)、[L335](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L335)、[L349](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L349)）。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| React Query `QK.preferences` | 每个写操作 `onSuccess` 都 `invalidateQueries(QK.preferences)` | 全 Tab 所有卡片、Layout 顶栏、其他共享 preferences 的页面 |
| React Query `QK.quoteStatus` | 实时开关、间隔更新后失效 | 行情状态指示、顶栏行情角标 |
| React Query `QK.quoteInterval` | `useUpdateQuoteInterval` 用 `setQueryData` 直接更新（非失效） | 行情间隔滑块立即反映 clamp 后值 |
| `['minute-refresh-status']` | 15s 自动轮询，无主动失效 | 全量分钟状态行 |
| `['limit-ladder']` | `runLimitLadderFix` 成功后失效 | 连板梯队页面 |
| 后端 overview 缓存 | `run_limit_ladder_fix` 成功调 `invalidate_overview_cache()` | 看板总览真假板数据 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 后端单测 | `backend/tests/`（待确认具体文件） | realtime-quotes 开启门禁（无数据/完整性扫描/暂停态）；quote-interval 按档位 clamp；realtime-monitor 间隔 clamp；webhook URL 校验 400 |
| 后端集成 | `backend/tests/`（待确认） | 实时开关联动 depth 轮询启停；策略监控变更触发 monitor_engine reload |
| 前端测试 | `frontend/src/`（待确认） | 滑块 2s 防抖落库；渠道保存后 QK.preferences 失效；测试按钮成功 2s 消失 |

## 依赖关系

### 依赖的其他功能

- **数据源 / 档位能力**（`useCapabilities`）：实时行情权限、`depth5.batch`、`intraday.universe` 门控。
- **QuoteService**：实时行情启停、轮询间隔、暂停态。
- **DepthService**：连板梯队真假板修正轮询。
- **MinuteRefreshService**：全量分钟落盘服务（`GET /api/settings/minute-refresh/status`）。
- **MonitorEngine / StrategyEngine**：策略监控规则迁移与重载。
- **WebhookAdapter / EmailAdapter**：推送渠道校验与发送。
- **SecretsStore**：敏感密钥持久化。

### 被依赖的功能

- **监控中心（Monitor Rules）**：新建规则默认推送渠道取 `webhook_default_channels`；告警推送复用本页配置的各渠道地址。
- **连板梯队页面**：依赖 `limit_ladder_monitor_enabled` 与 depth 修正结果。
- **看板总览**：实时行情开关决定 enriched 是否被快照覆盖。
- **Layout 顶栏**：`quoteStatus` 显示行情运行状态。

## 常见问题与注意事项

1. **实时行情开关无法开启**：依次检查（1）档位是否 none；（2）本地是否有日K/enriched 数据；（3）`is_paused` 是否为 true（管道/数据修正运行中）；（4）数据完整性扫描是否有缺口（会自动创建修复任务）。后端均返回 409 并附原因。

2. **轮询间隔无法拖到 1s**：仅 expert 档（或自定义实时源）允许最小 1s；pro 档最小 3s；starter/free 档最小 6s。前端滑块 `min` 由 `min_interval` 动态决定，且后端 `set_interval` 会再次 clamp。

3. **推送测试失败**：测试接口只读取**已保存**的配置（不读草稿），必须先点「保存」再点「测试」。返回 `ok:false` 时 detail 会说明是未配置、地址非法还是发送失败。

4. **SMTP 密码留空行为**：`password` 传 `None`（前端不填）时保留已存密码；传空串则清空。前端 `emailPasswordDraft` 留空时不提交 `password` 字段（即保留）。

5. **飞书 secret 明文存储**：飞书签名密钥存储于 `preferences.json`（非 secrets_store），与第三方 HMAC secret 不同，注意备份时的敏感信息处理。

6. **防抖竞态**：三个滑块各有独立的 2s 防抖 `useEffect`，快速连续拖动会重置定时器，但因为 `setTimeout` 返回值在 cleanup 中 `clearTimeout`，不会重复发请求。

7. **`highlight` 锚点**：卡片支持 `?tab=monitoring&highlight=<anchor>` 滚动并闪烁，锚点值为 `quotes` / `intraday-refresh` / `minute-refresh` / `depth-fix` / `webhooks`（[Monitoring.tsx:363,425,466,519,562](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/Monitoring.tsx#L363)）。

8. **企业微信智能机器人凭证齐全才允许勾选**：前端 checkbox 在 `!wecomBotId` 时 disabled；后端 `toggle_wecom_bot` 也强制 `enabled = req.enabled && bot_id && secret`。
