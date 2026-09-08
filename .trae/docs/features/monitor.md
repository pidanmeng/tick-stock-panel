---
title: 监控中心 Monitor — 功能文档
description: 监控中心（路由 /monitor）的完整功能参考，覆盖规则引擎、告警存储、通知推送、前端交互与扩展指南。
---

# 监控中心 Monitor — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

**本次检索范围**：`backend/app/strategy/monitor.py`、`backend/app/strategy/monitor_rules.py`、`backend/app/api/monitor_rules.py`、`backend/app/api/alerts.py`、`backend/app/services/alert_store.py`、`backend/app/services/quote_service.py`、`backend/app/services/notify_adapter.py`、`backend/app/services/webhook_adapter.py`、`backend/app/services/wecom_bot_service.py`、`frontend/src/pages/Monitor.tsx`、`frontend/src/components/monitor/RuleEditor.tsx`、`frontend/src/lib/monitorBadge.ts`、`frontend/src/lib/strategyMonitorEvents.ts`、`frontend/src/lib/queryKeys.ts`、`frontend/src/router.tsx`、`backend/tests/test_monitor_index.py`、`backend/tests/test_monitor_group_scope.py`、`backend/tests/test_monitor_etf.py`、`.trae/docs/architecture.md`、`docs/secondary-development.md`。

## 功能概述

监控中心是 TSP 的实时规则引擎与告警中枢。用户在页面上创建"监控规则"（9 种类型覆盖信号/价格/策略/板块/异动/放量/封单/市场/日期），每轮行情轮询由 `MonitorRuleEngine` 统一评估，命中规则时生成告警事件，经 JSONL 落盘、SSE 广播、系统通知、Webhook 推送四条输出通道下发，前端通过 TanStack Query 轮询 + SSE 双通道消费。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| 核心引擎 | `backend/app/strategy/monitor.py` | `MonitorRuleEngine` 统一评估所有规则类型；`StrategyMonitorService` 旧策略监控（迁移中） |
| 规则模型/CRUD | `backend/app/strategy/monitor_rules.py` | `MonitorRule` 模型定义、JSON 文件持久化、校验、normalize、`migrate_strategy_monitors` 迁移 |
| API 规则路由 | `backend/app/api/monitor_rules.py` | `/api/monitor-rules` 规则增删改查、选项、种子、ladder 调试 |
| API 告警路由 | `backend/app/api/alerts.py` | `/api/alerts` 告警查询、清空、单条删除、种子 |
| 告警存储 | `backend/app/services/alert_store.py` | JSONL 文件 `data/user_data/alerts.jsonl` 滚动写入/清理 |
| 行情轮询 | `backend/app/services/quote_service.py` | `_evaluate_monitors` 每轮行情评估入口，含 SSE 广播、Webhook、系统通知 |
| 系统通知 | `backend/app/services/notify_adapter.py` | winotify/osascript/notify-send 操作系统原生通知 |
| Webhook 推送 | `backend/app/services/webhook_adapter.py` | 飞书（文本+卡片+签名）、企业微信（text+markdown+字节截断）、第三方 JSON（HMAC-SHA256） |
| 企微 Bot | `backend/app/services/wecom_bot_service.py` | 企业微信智能机器人 WebSocket 长连接（心跳 30s，暂只保活） |
| 邮件通知 | `backend/app/services/email_adapter.py` | SMTP 邮件推送（由 webhook 流程调用） |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Monitor.tsx` | 监控中心主页面：左栏触发记录 + 右栏规则列表 + 编辑器弹窗 + ext 配置弹窗 |
| 组件 | `frontend/src/components/monitor/RuleEditor.tsx` | 规则编辑器（完整模式/极简模式），支持所有 9 种规则类型 |
| API 类型 | `frontend/src/lib/api.ts` | `MonitorRule`、`AlertEvent`、`MonitorCondition`、`MonitorRuleOptions`、`SectorMonitorTarget` 等接口定义 + 端点方法 |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `QK.monitorRules`、`QK.alerts`、`QK.monitorRuleOptions` |
| 未读徽标 | `frontend/src/lib/monitorBadge.ts` | `useUnreadAlerts` 全局 store + localStorage 持久化 |
| 策略事件配置 | `frontend/src/lib/strategyMonitorEvents.ts` | `StrategyNotifyEvent` 选项、默认值、元信息 |
| 路由 | `frontend/src/router.tsx` | `/monitor` 路由注册（lazy 加载） |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 规则存储 | `data/user_data/monitor_rules/*.json` | 每条规则一个 JSON 文件，按 `{rule_id}.json` 命名 |
| 告警存储 | `data/user_data/alerts.jsonl` | 触发记录 JSONL 滚动文件，最多 7 天/5000 条 |
| 种子数据 | `backend/app/seed/` | 初始规则种子（由 `POST /api/monitor-rules/seed` 和 `POST /api/alerts/seed` 加载） |

### 测试

| 文件 | 路径 | 用途 |
|------|------|------|
| 指数规则测试 | `backend/tests/test_monitor_index.py` | 指数规则校验拒绝（strategy/market/scope=all/分时信号）+ 指数评估轮隔离 + 资产类型纠正 |
| 分组作用域测试 | `backend/tests/test_monitor_group_scope.py` | 分组作用域校验、动态成员解析、分组删除 fail-closed、API 存在性校验 |
| ETF 规则测试 | `backend/tests/test_monitor_etf.py` | ETF 资产类型规则过滤、`has_asset_rules`、历史加载器按资产类型选择 |

## 业务逻辑

### 核心流程

```
[行情轮询收数] → _on_quote_updated → _evaluate_monitors
  → 连续竞价时段检查
  → 获取 enriched 快照（股票/ETF/指数三表独立）
  → 注入临时列（封单/sealed_vol、放量/volume_delta、分时信号）
  → MonitorRuleEngine.evaluate 按资产类型分轮评估
    → 按 asset_type 过滤规则 → 解析 scope（符号/分组/全市场）
    → 条件匹配: 信号布尔/阈值比较 / 策略选股 / 板块快照 / 异动边缘 / 放量 / 封单 / 市场
    → cooldown 去重 → 生成 AlertEvent dict
  → 旁路: evaluate_sectors / evaluate_abnormal / evaluate_date_rules
  → 扩展通知格式化
  → alert_store.append_many 落盘 JSONL
  → SSE 广播 strategy_alert 事件
  → 系统通知（可选） + Webhook 推送（规则独立选择）
```

### 数据流

1. **输入来源**：每轮行情轮询（`quote_service._on_quote_updated`，约 1-6s 间隔）触发 `_evaluate_monitors`。连续竞价时段（9:30-11:30/13:00-15:00，节假日前交易日探针兜底）之外跳过，避免集合竞价指示价误报。

2. **处理过程**：
   - 从 `app_state` 获取 `monitor_engine`（`MonitorRuleEngine` 单例），按 `asset_type` 分轮评估：股票轮（依赖 enriched 快照日期=当日）、ETF 轮（独立快照 `refresh=False`）、指数轮（独立快照 + 日期守卫）。
   - 股票轮中，若存在 `ladder` 规则则注入 `_sealed_vol` 临时列，若存在 `volume_delta` 规则则注入 `_volume_delta`/`_volume_delta_amount`/`_volume_delta_span` 临时列，若存在分时信号规则则注入日内布尔信号列。
   - 引擎内 `evaluate()` 按 `asset_type` 过滤规则，对每条规则调用 `_evaluate_rule()`：先 `_apply_scope()` 解析作用域（符号列表/自选分组动态成员/全市场），再按类型分支匹配条件，cooldown 检查通过后生成 `AlertEvent` dict。
   - 板块（sector）和异动（abnormal）规则由独立旁路 `evaluate_sectors()`/`evaluate_abnormal()` 评估，不经过主 evaluate 路径。
   - 策略类型（strategy）规则由 `_match_strategy()` 复用 `StrategyEngine.run` 实时选股，>5 只合并为批量事件（`symbol="_batch"`）。

3. **输出去向**：
   - **JSONL 落盘**：`alert_store.append_many()` 追加到 `data/user_data/alerts.jsonl`，按 `PRUNE_EVERY=20` 触发滚动清理（保留 MAX_DAYS=7 天、MAX_RECORDS=5000 条）。
   - **SSE 广播**：`_broadcast_alerts()` 推送到所有 SSE 订阅者，前端 `useQuoteStream` 收到 `strategy_alert` 事件后按 `QK.alerts` 前缀失效 TanStack Query 缓存。
   - **系统通知**（可选开关）：`_maybe_send_system_notifications()` 调用 `notify_adapter.notify()` 逐条弹出操作系统原生通知，失败静默。
   - **Webhook 推送**（规则独立选择）：`_maybe_send_webhook()` 按规则 `webhook_channels` 字段投递到飞书/企业微信/第三方/邮件，失败静默不阻断主流程。

### 调用链

```text
行情轮询（quote_service.py:909）
  → _evaluate_monitors（quote_service.py:1151-1312）
    → _is_continuous_trading 检查（quote_service.py:1129-1147）
    → get_enriched_today() 获取股票快照（quote_service.py:1160）
    → 股票轮: _inject_sealed_vol（quote_service.py:1189）
                _inject_volume_delta（quote_service.py:1191）
                _inject_intraday_signals（quote_service.py:1192）
                → engine.evaluate(df, asset_type="stock")（monitor.py:587-708）
                  → _evaluate_rule（monitor.py:1067-1150）
                    → _apply_scope（monitor.py:1153-1178）
                    → 条件匹配 / _match_strategy（monitor.py:1180-1413）
                    → cooldown 检查（monitor.py:1090-1101）
                  → 返回 AlertEvent dict
    → 板块旁路: engine.evaluate_sectors()（monitor.py:826-898）
    → 异动旁路: engine.evaluate_abnormal() 30s 限频（monitor.py:968-1053）
    → 日期旁路: engine.evaluate_date_rules()（monitor.py:710-782）
    → ETF 轮: engine.evaluate(asset_type="etf")（quote_service.py:1233-1235）
    → 指数轮: engine.evaluate(asset_type="index")（quote_service.py:1246-1248）
    → _format_extension_notifications（quote_service.py:1314-1348）
    → alert_store.append_many（alert_store.py:38-65）
    → _enrich_alerts_ext（quote_service.py:1350）
    → _broadcast_alerts → SSE strategy_alert 事件（quote_service.py:1299）
    → _maybe_send_system_notifications（notify_adapter.py:60-92）
    → _maybe_send_webhook（webhook_adapter.py:1576-1653）
      → 飞书 send_feishu / send_feishu_card（webhook_adapter.py:151-220）
      → 企业微信 send_wecom / send_wecom_markdown（webhook_adapter.py:297-347）
      → 第三方 send_custom（webhook_adapter.py:366-421）
      → 邮件 email_adapter.send_email（email_adapter.py）
```

### 状态机

MonitorRuleEngine 内部维护以下内存状态：

| 状态 | 键类型 | 说明 |
|------|--------|------|
| `_last_fire` | `(rule_id, symbol, event_type) → float(timestamp)` | cooldown 去重，键含事件类型（strategy 规则区分 buy_signal/sell_signal/pool_entry/pool_exit） |
| `_date_eval_day` | `str(YYYY-MM-DD)` | 日期提醒规则每日一次守卫 |
| `_strategy_pools` | `strategy_id → list[symbol]` | 策略选股池结果缓存 |
| `_strategy_signal_state` | `(rule_id, symbol) → bool` | 策略信号边缘触发（False→True 跳变） |
| `_strategy_signal_seen` | `(rule_id, symbol, event_type) → bool` | 策略事件已推送守卫 |
| `_sector_condition_state` | `(rule_id, key) → bool` | 板块条件边缘触发 |
| `_abnormal_condition_state` | `(rule_id, symbol) → float` | 异动接近度边缘触发（首轮观测不触发） |
| `_latest_strategy_results` | `strategy_id → dict` | 策略结果缓存，供 `/api/screener/cached` 叠加读取 |
| `_active_matrix_snapshots` | `strategy_id → list[symbol]` | matrix_native 策略快照 |
| `_volume_delta` | `symbol → (vol, amount)` | 全市场快照成交量差值（首轮开盘保护） |

## 关键数据结构

### API 契约

#### MonitorRule（核心模型）

```typescript
// frontend/src/lib/api.ts:940-984
interface MonitorRule {
  id: string
  name: string
  enabled: boolean
  type: 'strategy' | 'signal' | 'price' | 'market' | 'ladder'
      | 'sector' | 'abnormal' | 'volume_delta' | 'date'
  asset_type?: 'stock' | 'etf' | 'index'          // 默认 stock
  scope: 'symbols' | 'all' | 'sector' | 'watchlist_group'
  symbols: string[]
  group_id?: string | null                           // scope=watchlist_group
  sector_targets?: SectorMonitorTarget[]             // type=sector
  sector_trigger?: 'change_pct' | 'momentum'
  threshold_pct?: number                             // sector:涨幅%; abnormal:接近度%
  window_minutes?: 1 | 3 | 5 | 10 | 15
  abnormal_window?: 'any' | '3d' | '10d' | '30d'
  strategy_id?: string | null
  direction: 'entry' | 'exit' | 'both' | 'up' | 'down'
  notify_events?: StrategyNotifyEvent[]              // type=strategy 的事件过滤
  score_min?: number | null
  score_max?: number | null
  conditions: MonitorCondition[]
  logic: 'and' | 'or'
  cooldown_seconds: number
  severity: 'info' | 'warn' | 'critical'
  message: string
  webhook_channels?: string[]                        // feishu | wecom | custom | email
  // volume_delta 专属
  metric?: 'volume' | 'amount'
  threshold_volume?: number                          // 手
  threshold_amount?: number                          // 元
  basic_filter?: VDBasicFilter
  // date 专属
  remind_date?: string | null
  lead_days?: number
  lot_id?: string                                    // 托管于批次页，监控中心只读
}
```

**单位口径说明**：
- `change_pct`（实时源）：小数制，message 中 ×100 显示百分号
- `threshold_pct`（sector）：%，评估时 `/100` 转为小数制
- `threshold_pct`（abnormal）：接近度%（1-150），评估时 `/100` 转为小数
- `threshold_volume`：手
- `threshold_amount`：元
- `_sealed_vol`：手

#### AlertEvent

```typescript
// frontend/src/lib/api.ts:1029-1054
interface AlertEvent {
  ts: number                                          // 毫秒时间戳
  rule_id?: string
  rule_name?: string
  source: string                                      // strategy|signal|price|market|sector|abnormal|volume_delta|date
  type: string
  symbol?: string
  name?: string | null
  message: string
  price?: number | null
  change_pct?: number | null
  signals?: string[]
  severity?: string
  // 板块/异动/放量衍生字段
  sector_kind?: SectorKind
  sector_key?: string
  sector_name?: string
  window_change_pct?: number | null
  coverage_ratio?: number
  leader?: string
  abnormal_window?: string
  abnormal_closeness?: number
  volume_delta?: number
  volume_delta_span?: number
}
```

#### REST API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/monitor-rules` | GET | 规则列表 + `runtime_warning` |
| `/api/monitor-rules` | POST | 保存规则（校验+同步引擎） |
| `/api/monitor-rules/{rule_id}` | DELETE | 删除规则（lot_id 托管规则禁止删除） |
| `/api/monitor-rules/options` | GET | 字段选项（类型/作用域/信号/阈值字段等） |
| `/api/monitor-rules/seed` | POST | 加载种子规则 |
| `/api/monitor-rules/test-ladder` | POST | 封单调试端点 |
| `/api/monitor-rules/trigger-ladder` | POST | 触发封单调式端点 |
| `/api/alerts` | GET | 查询告警（days/limit/source/type/ext_columns 富化） |
| `/api/alerts` | DELETE | 清空全部告警 |
| `/api/alerts/{ts}` | DELETE | 按 ts 单条删除 |
| `/api/alerts/seed` | POST | 种子演示数据 + SSE 推送 |

### 存储结构

**规则文件**：`data/user_data/monitor_rules/{rule_id}.json`

每个文件是一个完整的 `MonitorRule` JSON 对象。`load_all()` 遍历目录反序列化，`save_one()` 写文件，`delete_one()` 删文件。`set_rules()` 批量加载时保留引擎内存状态（`_last_fire` 等），只新增/更新/删除差异规则。

**告警文件**：`data/user_data/alerts.jsonl`

每行一个 JSON 对象，包含 `ts`（毫秒时间戳，唯一标识）、`source`、`type`、`rule_id`、`symbol`、`name`、`message`、`price`、`change_pct`、`signals`、`severity` 等字段。`append_many()` 追加，`delete_one(ts)` 重写文件排除该行，`clear()` 清空文件，`list_recent()` 按时间倒序返回。

**缓存失效**：`monitor_rules` 的 SSE 失效前缀**不在** `SSE_INVALIDATE_PREFIXES` 列表中（`queryKeys.ts:132-142`），因为规则变更频率极低且由手动操作触发，SSE 自动失效反而浪费。规则保存后由 `onSuccess` 回调手动 `invalidateQueries({ queryKey: QK.monitorRules })`。

### 内存结构

见上表"状态机"。核心是 `MonitorRuleEngine` 单例，生命周期与 `app_state` 绑定，在每个行情轮询中由 `quote_service._evaluate_monitors` 引用。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **新建规则**：通过页面 `/monitor` 新建，或通过 `POST /api/monitor-rules` 直接写入 JSON 文件。种子数据由 `POST /api/monitor-rules/seed` 加载。
- **策略监控**：策略类型规则复用 `StrategyEngine` 的选股结果，无需额外配置。`notify_events` 控制策略事件类型（buy_signal/sell_signal/pool_entry/pool_exit），`score_min`/`score_max` 过滤评分范围。
- **扩展数据标签**：告警按 `symbol` 富化行业/概念标签，由 `preferences.monitor_ext_fields` 配置字段来源（`frontend/src/pages/Monitor.tsx:147-155`）。

### L2 扩展（插槽/路由/注册替换）

- **`NotificationFormatter`**（已实现）：后端扩展注册 `NotificationFormatter` 实现，在评估完成后调整通知文案。注册示例见 `docs/secondary-development.md:214-223`。引擎侧 `_format_extension_notifications` 在 `quote_service.py:1314-1348` 调用。
- **通知渠道**：通过 `webhook_adapter.py` 的飞书/企业微信/第三方/邮件通道，无需修改核心代码。新增渠道只需在 `webhook_adapter.py` 添加发送函数，并在 `_maybe_send_webhook` 中注册。

### L3 修改（直接改源码）

- **新增规则类型**：在 `monitor.py` 添加 `_evaluate_xxx` 方法，在 `_evaluate_rule` 主分支中注册，同时在 `monitor_rules.py` 的 `validate`/`normalize` 中添加校验逻辑，在前端 `RuleEditor.tsx` 添加 UI 编辑区。
- **修改评估逻辑**：`MonitorRuleEngine` 所有评估方法集中在 `monitor.py`（`_evaluate_sector_rule` :826、`_evaluate_abnormal_rule` :968、`_evaluate_volume_delta` :1500、`_evaluate_ladder` :1603、`_match_strategy` :1180 等），修改时注意 `_last_fire` cooldown 一致性和 `_latest_strategy_results` 缓存同步。
- **修改通知输出**：`quote_service.py` 的 `_evaluate_monitors` 方法（:1151-1312）是告警输出的总调度点，新增输出通道在此添加。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件缓存（规则 JSON） | `save_one`/`delete_one` 直接写文件；`set_rules` 批量加载 | 下次 `load_all` 读取新文件 |
| 内存缓存（引擎状态） | `set_rules` 保留活跃规则 `_last_fire` 等状态，只增删改差异规则 | 引擎评估立即生效 |
| 内存缓存（策略结果） | `consume_strategy_result_updates()` 消费后 notify | 前端 `/api/screener/cached` 下次读取新结果 |
| SSE/前端 | 规则保存后手动 `invalidateQueries({ queryKey: QK.monitorRules })`；告警由 SSE `strategy_alert` 事件触发 `QK.alerts` 前缀失效 | 前端规则列表/告警列表即时刷新 |
| localStorage（未读徽标） | `markSeen`/`resetBadge`/`setCurrentTotal` 实时写入 | `monitorBadge.ts` 的 `useUnreadAlerts` 即时更新 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试（指数） | `backend/tests/test_monitor_index.py` | 指数规则校验拒绝（类型/作用域/分时信号）、指数评估轮只评估指数规则、`asset_type` 自动纠正 |
| 单元测试（分组） | `backend/tests/test_monitor_group_scope.py` | 分组校验、动态成员解析（增删自选自动生效）、分组删除 fail-closed、API 分组存在性校验 |
| 单元测试（ETF） | `backend/tests/test_monitor_etf.py` | ETF 规则过滤、`has_asset_rules`、历史加载器按资产类型选择 |

## 依赖关系

### 依赖的其他功能

- **行情轮询**（`quote_service.py`）：监控评估的入口触发点，依赖 enriched 快照就绪。
- **策略引擎**（`strategy/engine.py`）：策略类型规则依赖 `StrategyEngine.run` 实时选股。
- **自选分组**（`services/watchlist.py`）：`watchlist_group` 作用域依赖 `get_group_members` 动态解析分组成员，`watchlist.revision()` 版本号缓存。
- **深度行情**（`depth_service`）：封单监控依赖 `get_sealed_map` 获取涨跌停封单量。
- **行情路由**（`data_providers`）：分时信号依赖 Provider 提供分钟 K 线，通过 `intraday_signal_support` 能力检测决定可用性。
- **扩展数据**（`ext_data`）：告警行业/概念标签依赖 `preferences.monitor_ext_fields` 配置的扩展数据字段。
- **SSE 推送**（`services/quote_service.py` 的 `_broadcast_alerts`）：告警事件通过 SSE 推送到前端，触发 `useQuoteStream` 按 `QK.alerts` 前缀失效。

### 被依赖的功能

- **策略页**（`screener`）：监控策略引擎的 `_latest_strategy_results` 由 `/api/screener/cached` 端点叠加读取，供策略页实时回显选股结果。
- **Layout 层**（`components/Layout.tsx`）：`monitorBadge.ts` 的 `useUnreadAlerts` Hook 在 Layout 导航栏显示未读徽标。
- **批次页**（`lots`）：`lot_id` 托管规则由批次页生成，监控中心只读显示。

## 常见问题与注意事项

1. **连续竞价时段守卫**：`_is_continuous_trading()`（`quote_service.py:1129-1147`）严格限制仅 9:30-11:30/13:00-15:00 评估监控，排除集合竞价和收盘缓存。节假日由 enriched 快照日期 `cn_today()` 兜底，无需交易日历。

2. **cooldown 键含事件类型**：`_last_fire` 的键是 `(rule_id, symbol, event_type)` 三元组。策略规则的事件类型为 `buy_signal`/`sell_signal`/`pool_entry`/`pool_exit`，同一规则同一标的的不同事件类型独立冷却。

3. **scope=sector 为 fail-closed**：`_apply_scope`（`monitor.py:1153-1178`）对 scope=sector 返回空列表，引擎侧不触发告警。前端显示"开发中，当前等同全市场"。

4. **自选分组作用域动态绑定**：`_watchlist_groups_snapshot()` 带 `watchlist.revision()` 版本号缓存，分组内增删标的自动纳管。分组删除时 fail-closed（不崩、不触发、不退化为全市场）。

5. **abnormal 边缘触发**：`_abnormal_condition_state` 只在接近度从 False→True 跳变时告警，首轮观测不触发。`_evaluate_abnormal_rule` 同时清理不在当前快照中的旧状态。

6. **volume_delta 开盘保护**：`_volume_delta` 首轮为空（`_prev_stock_volume` 尚未初始化），暂停后恢复也跳过第一轮，防止集合竞价撮合误报。

7. **Webhook 异步投递**：`_WEBHOOK_EXECUTOR.submit` 将推送提交到独立线程池，不阻塞行情轮询线程。失败由 `webhook_adapter` 记 WARNING 日志。

8. **告警 ext 富化静默降级**：`_enrich_alerts_ext` 读取扩展数据 parquet，带 mtime 缓存。富化失败不影响告警推送，仅缺失行业/概念标签。

9. **前端 10s 轮询兜底**：`alertsQuery` 设 `refetchInterval: 10000` 作为 SSE 的兜底，确保后台标签页也能收到告警。SSE 事件到达时通过 `useQuoteStream` 的 `SSE_INVALIDATE_PREFIXES` 机制失效缓存。

10. **策略类型 >5 只批量合并**：`_match_strategy` 中超过 5 只标的的策略事件合并为单条，`symbol="_batch"`，避免短时间内大量告警刷屏。