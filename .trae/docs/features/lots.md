---
title: 持仓提醒（Lots / 批次登记）— 功能文档
description: 持仓提醒（批次登记）功能完整参考，含前后端调用链、数据流、存储结构、扩展指南与测试覆盖。
---

# 持仓提醒（Lots / 批次登记）— 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

"持仓提醒"页（菜单：持仓提醒，路由 `/lots`）是薄批次登记功能：用户记录每笔买入批次（标的、数量、成本价、止盈%/止损%、买入日期、到期日/提前提醒天数），系统自动派生两条监控规则（价格止盈止损规则、日期到期提醒规则），同步进监控中心统一规则引擎，盘中评估触发后推送告警。**明确只用于生成提醒，不做持仓记账**（无会计语义，交易口径拆分见 issue #230）。

该功能定位为"监控规则生成器"——绝不是持仓管理系统，而是将一次性的买入批次转化为两条持续评估的监控规则，并复用监控中心的通知/推送管道。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 入口 | [lots.py](../../../backend/app/api/lots.py) | `/api/lots` 路由：GET 列表、POST 新建/编辑、DELETE 删除；`sync_lot()` 写批次+派生规则+重载引擎的胶水 |
| 域服务 | [lots.py](../../../backend/app/strategy/lots.py) | 批次域：校验(`validate_lot`)、归一化(`normalize_lot`)、文件存储(`load_all`/`save_one`/`delete_one`)、批次→规则映射(`lot_to_rules`) |
| 规则存储 | [monitor_rules.py](../../../backend/app/strategy/monitor_rules.py) | 监控规则持久化(`load_one`/`save_one`/`delete_one`)、校验(`validate`)、归一化(`normalize`)、日期窗口判定(`date_rule_in_window`) |
| 规则引擎 | [monitor.py](../../../backend/app/strategy/monitor.py) | `MonitorRuleEngine`：实时评估 price 规则(`_evaluate_rule`)、date 规则(`evaluate_date_rules`)、条件文本拼装(`_format_conditions_text`) |
| 引擎重载 | [monitor_rules.py](../../../backend/app/api/monitor_rules.py) | `_sync_engine()`：批次保存/删除后 reload 引擎内存态规则 |
| 偏好设置 | [preferences.py](../../../backend/app/services/preferences.py) | `get_webhook_default_channels()`：派生规则继承用户的默认推送渠道 |
| 盘中评估 | [quote_service.py](../../../backend/app/services/quote_service.py) | `_evaluate_monitors()`：行情轮询线程中调用引擎评估所有规则（含 date 轮） |
| 告警存储 | [alert_store.py](../../../backend/app/services/alert_store.py) | `append_many()`：告警事件落盘到 `alerts.jsonl` |
| 测试 | [test_lots.py](../../../backend/tests/test_lots.py) | 8 个测试用例：映射/校验/一致性/级联删除/ETF 资产类型 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | [Lots.tsx](../../../frontend/src/pages/Lots.tsx) | 全量持仓提醒页面：列表展示、新增/编辑弹窗(`LotDialog`)、删除确认、日K预览 |
| 路由 | [router.tsx](../../../frontend/src/router.tsx) | 懒加载注册 `/lots` 路由 |
| API 客户端 | [api.ts](../../../frontend/src/lib/api.ts) | `Lot` 接口定义、`lotsList`/`lotSave`/`lotDelete` 三个方法 |
| 查询键 | [queryKeys.ts](../../../frontend/src/lib/queryKeys.ts) | `QK.lots` 与 `QK.lotsKline(symbols)` |
| 组件 | [StockPreviewDialog.tsx](../../../frontend/src/components/StockPreviewDialog.tsx) | 日K预览弹窗 + `toNavItems` 导航 |
| 组件 | [DatePicker.tsx](../../../frontend/src/components/DatePicker.tsx) | 日期选择器 |
| 组件 | [DateShortcuts.tsx](../../../frontend/src/components/DateShortcuts.tsx) | 快捷日期按钮（今天/5天/10天/15天） |
| 组件 | [Modal.tsx](../../../frontend/src/components/Modal.tsx) | 弹窗容器 |
| 组件 | [primitives.tsx](../../../frontend/src/components/stock-table/primitives.tsx) | `boardTag` 板块标签 |
| 工具库 | [format.ts](../../../frontend/src/lib/format.ts) | `fmtPct`/`fmtPrice`/`priceColorClass` 格式化 |
| 工具库 | [cn.ts](../../../frontend/src/lib/cn.ts) | CSS class 合并 |

### 数据文件

| 文件 | 路径 | 用途 |
|------|------|------|
| 批次文件 | `data/user_data/lots/{lot_id}.json` | 每笔批次一个 JSON 文件 |
| 派生规则 | `data/user_data/monitor_rules/{lot_id}_p.json` | 价格止盈止损规则 |
| 派生规则 | `data/user_data/monitor_rules/{lot_id}_d.json` | 日期到期提醒规则 |
| 告警文件 | `data/user_data/alerts.jsonl` | 触发后的告警事件（由 quote_service 落盘） |

## 业务逻辑

### 核心流程

```text
用户操作（前端 Lots.tsx） → POST /api/lots（api/lots.py）
  → validate_lot + normalize_lot（strategy/lots.py:41-83）
  → sync_lot（api/lots.py:61-96）
    → 解析资产类型（stock/etf）
    → lot_to_rules 派生两条规则（strategy/lots.py:113-177）
    → 校验规则（monitor_rules.validate）
    → 写批次文件 + 写/删派生规则文件
    → _reload_engine → engine.set_rules（monitor_rules.py:43-52）
  → 监控引擎盘中评估（monitor.py MonitorRuleEngine）
    → price 规则：行情条件匹配 → 冷却期去重 → AlertEvent
    → date 规则：窗口判定 → 每天一次 → AlertEvent
  → 告警落盘（alert_store.append_many）+ SSE 推送
  → 前端 invalidate QK.lots + QK.monitorRules
```

### 数据流

1. **输入来源**：用户在 `/lots` 页面通过 `LotDialog` 弹窗填写批次表单（标的、数量、成本价、止盈%/止损%、买入日期、到期日、提前天数），提交调用 `api.lotSave()` → `POST /api/lots`。

2. **处理过程**：
   - **服务端校验**：`lots.validate_lot`（[strategy/lots.py:41-68](../../../backend/app/strategy/lots.py#L41-L68)）检查 id 合法性、symbol 非空、cost_price 为正数、各数值非负、日期格式 YYYY-MM-DD、至少设置止盈%/止损%/到期日之一。
   - **归一化**：`lots.normalize_lot`（[strategy/lots.py:71-83](../../../backend/app/strategy/lots.py#L71-L83)）补全缺省字段，设置 `created_at`。
   - **资产类型解析**：`_resolve_asset_type`（[api/lots.py:29-39](../../../backend/app/api/lots.py#L29-L39)）通过 `repo.resolve_asset_type()` 识别 stock/etf，解析失败回退 stock 并记警告。
   - **派生规则**：`lot_to_rules`（[strategy/lots.py:113-177](../../../backend/app/strategy/lots.py#L113-L177））将批次映射为两条规则：
     - `{lot_id}_p`：type=price，conditions 为 `close >= 成本×(1+止盈%)` 或 `close <= 成本×(1-止损%)`，logic=or，cooldown=86400s（24h），severity=warn。
     - `{lot_id}_d`：type=date，记录 `remind_date` + `lead_days`，cooldown=86400s，severity=info。
     - 任一监控点为零/空时，对应规则为 None（不做派生）。
   - **同步写入**：`sync_lot`（[api/lots.py:61-96](../../../backend/app/api/lots.py#L61-L96））在写锁保护下：先校验派生规则（通过 `monitor_rules.validate`），再写批次文件，然后写/删两条派生规则文件。规则校验失败抛 HTTP 400，批次文件不落盘（避免半成品）。
   - **引擎重载**：`_reload_engine`（[api/lots.py:54-58](../../../backend/app/api/lots.py#L54-L58））调用 `monitor_rules.py` 的 `_sync_engine`，从文件重新加载所有规则到 `MonitorRuleEngine._rules`。

3. **输出去向**：
   - 批次 JSON 写入 `data/user_data/lots/{lot_id}.json`。
   - 派生规则 JSON 写入 `data/user_data/monitor_rules/{lot_id}_p.json` / `{lot_id}_d.json`。
   - 前端 `useMutation.onSuccess` 自动 `invalidateQueries` 刷新列表和监控规则页。

### 调用链

**写路径（用户操作 → 落盘）**：

```text
前端 Lots.tsx:279-287（lotSave mutation）
→ api.ts:3438-3442（POST /api/lots）
→ api/lots.py:104-116（upsert_lot）
  → api/lots.py:111（lots_domain.validate_lot）
  → api/lots.py:114（lots_domain.normalize_lot）
  → api/lots.py:115（sync_lot）
    → api/lots.py:72（_resolve_asset_type）
    → api/lots.py:73（lots_domain.lot_to_rules）
    → api/lots.py:87-88（monitor_rules.validate）
    → api/lots.py:91（lots_domain.save_one 批次文件）
    → api/lots.py:93（monitor_rules.delete_one 规则文件）
    → api/lots.py:94-95（monitor_rules.save_one 规则文件）
    → api/lots.py:96（_reload_engine → monitor_rules.py:43-52 _sync_engine）
      → api/monitor_rules.py:50（monitor_rules.load_all）
      → api/monitor_rules.py:52（engine.set_rules）
```

**读路径（页面加载 → 展示）**：

```text
前端 Lots.tsx:54（lotsQuery → api.lotsList）
→ api.ts:3435-3436（GET /api/lots）
→ api/lots.py:99-101（list_lots）
  → strategy/lots.py:87-95（lots_domain.load_all 读 data/user_data/lots/）
前端 Lots.tsx:58-63（namesQuery → api.instrumentNames）
前端 Lots.tsx:75-80（dailyQuery → api.klineDailyBatch 加载最近5日K线）
```

**监控评估路径（盘中触发 → 告警）**：

```text
quote_service.py:1151-1250（_evaluate_monitors 行情轮询）
→ monitor.py:587-708（engine.evaluate — 评估 price 规则）
  → monitor.py:689-701（遍历 rules，_evaluate_rule）
    → monitor.py:1152-1178（_apply_scope 过滤 symbols）
    → monitor.py:1446-1467（_match_conditions 匹配 close>=/<= 条件）
    → monitor.py:1096-1150（cooldown 去重 + 生成 AlertEvent）
  → 回调 alert_handler → quote_service.py:1254-1258（alert_store.append_many 落盘）
  → quote_service.py:1262-1289（转为 SSE 格式，广播给前端）
→ monitor.py:710-782（engine.evaluate_date_rules — 纯日历评估）
  → monitor_rules.py:119-132（date_rule_in_window 窗口判定）
  → monitor.py:730-774（遍历 date 规则，按天 cooldown，生成 AlertEvent）
  → 回调 alert_handler → 同 price 路径落盘+SSE
```

**删除路径**：

```text
前端 Lots.tsx:100-110（handleClickDelete 两次点击确认）
→ api.ts:3444-3445（DELETE /api/lots/{id}）
→ api/lots.py:119-131（delete_lot）
  → strategy/lots.py:104-109（lots_domain.delete_one 删批次文件）
  → monitor_rules.py:107-108（monitor_rules.delete_one 删 _p 规则）
  → monitor_rules.py:107-108（monitor_rules.delete_one 删 _d 规则）
  → api/lots.py:129-130（有文件真删才 _reload_engine）
```

### 状态机

**批次生命周期**：

```text
[新建/编辑] → validate_lot + normalize_lot
  → sync_lot 写批次文件 + 派生规则
  → 引擎重载
  → [盘中] MonitorRuleEngine 评估
    → price 规则命中: 止盈/止损告警
    → date 规则命中: 到期提醒告警
  → [删除] 删批次文件 + 级联删两条派生规则 + 引擎重载
```

**派生规则与批次的映射关系**：

- 批次 id 为 `lot_{timestamp}_{random}`（[api/lots.py:109](../../../backend/app/api/lots.py#L109)），派生规则 id 为 `{lot_id}_p`（price）和 `{lot_id}_d`（date）。
- 派生规则通过 `lot_id` 字段反向关联到批次（[strategy/lots.py:155](../../../backend/app/strategy/lots.py#L155) 和 [strategy/lots.py:175](../../../backend/app/strategy/lots.py#L175)）。
- 编辑批次时，原派生规则若不再需要（如去掉了止盈止损），则级联删除（[api/lots.py:76-78](../../../backend/app/api/lots.py#L76-L78)）。
- 删除批次时，两条派生规则被级联删除（[api/lots.py:127-128](../../../backend/app/api/lots.py#L127-L128)）。

## 关键数据结构

### API 契约

**`LotModel`**（[api/lots.py:42-51](../../../backend/app/api/lots.py#L42-L51)）：

```python
class LotModel(BaseModel):
    id: str | None = None           # 新建时缺省，服务端生成
    symbol: str                     # 标的代码
    qty: float = 0                  # 数量（参考，不做会计）
    cost_price: float = 0           # 成本价（必须正数）
    buy_date: str | None = None     # 买入日期 YYYY-MM-DD（可选）
    target_pct: float = 0           # 止盈%（>0 时启用）
    stop_pct: float = 0             # 止损%（>0 时启用）
    remind_date: str | None = None  # 到期日 YYYY-MM-DD（可选）
    lead_days: int = 1              # 提前提醒天数（到期日存在时有效）
```

**前端 `Lot` 接口**（[api.ts:986-998](../../../frontend/src/lib/api.ts#L986-L998)）：

```typescript
export interface Lot {
  id: string
  symbol: string
  qty: number
  cost_price: number
  buy_date?: string | null
  target_pct: number
  stop_pct: number
  remind_date?: string | null
  lead_days: number
  created_at?: string
}
```

**API 返回**：

- `GET /api/lots` → `{"lots": Lot[]}`（[api/lots.py:99-101](../../../backend/app/api/lots.py#L99-L101)）
- `POST /api/lots` → `{"ok": true, "lot": Lot}`（[api/lots.py:104-116](../../../backend/app/api/lots.py#L104-L116)）
- `DELETE /api/lots/{lot_id}` → `{"ok": true}`（[api/lots.py:119-131](../../../backend/app/api/lots.py#L119-L131)）

### 存储结构

**批次文件** `data/user_data/lots/{lot_id}.json`：

```json
{
  "id": "lot_17f3a2c_ab12",
  "symbol": "600519.SH",
  "qty": 100,
  "cost_price": 1500.0,
  "buy_date": "2026-08-01",
  "target_pct": 10,
  "stop_pct": 5,
  "remind_date": "2026-09-01",
  "lead_days": 2,
  "created_at": "2026-08-15T10:00:00+00:00"
}
```

存储路径由 `lots._dir` 决定：`data_dir / "user_data" / "lots"`（[strategy/lots.py:26-29](../../../backend/app/strategy/lots.py#L26-L29)）。

**派生规则文件** `data/user_data/monitor_rules/{lot_id}_p.json`（price 规则）：

```json
{
  "id": "lot_17f3a2c_ab12_p",
  "name": "批次止盈止损 · 600519.SH",
  "type": "price",
  "asset_type": "stock",
  "scope": "symbols",
  "symbols": ["600519.SH"],
  "conditions": [
    {"field": "close", "op": ">=", "value": 1650.0},
    {"field": "close", "op": "<=", "value": 1425.0}
  ],
  "logic": "or",
  "cooldown_seconds": 86400,
  "severity": "warn",
  "message": "批次止盈止损 · 成本1500 · 止盈10% · 止损5% · 100股 · 收盘价≥1650或≤1425",
  "enabled": true,
  "lot_id": "lot_17f3a2c_ab12",
  "webhook_channels": ["feishu"],
  "created_at": "2026-08-15T10:00:00+00:00"
}
```

**派生规则文件** `data/user_data/monitor_rules/{lot_id}_d.json`（date 规则）：

```json
{
  "id": "lot_17f3a2c_ab12_d",
  "name": "批次到期 · 600519.SH",
  "type": "date",
  "asset_type": "stock",
  "scope": "symbols",
  "symbols": ["600519.SH"],
  "remind_date": "2026-09-01",
  "lead_days": 2,
  "cooldown_seconds": 86400,
  "severity": "info",
  "message": "批次到期提醒 · 2026-09-01 · 100股",
  "enabled": true,
  "lot_id": "lot_17f3a2c_ab12",
  "webhook_channels": ["feishu"],
  "created_at": "2026-08-15T10:00:00+00:00"
}
```

### 内存结构

**`MonitorRuleEngine`**（[monitor.py:323-374](../../../backend/app/strategy/monitor.py#L323-L374)）：

- `_rules: dict[str, dict]` — rule_id → rule 的内存映射，由 `set_rules` 原子替换。
- `_last_fire: dict[tuple[str, str, str], float]` — `(rule_id, symbol, event_type)` → 上次触发时间戳，用于 cooldown 去重。
- `_date_eval_day: str | None` — 今日 ISO 日期，跨天重置。
- `_date_eval_rules_version: int` — 规则集版本号，变更时清空日期缓存。

**`_write_lock`**（[api/lots.py:22](../../../backend/app/api/lots.py#L22)）— `threading.Lock()`，跨请求互斥批次+派生规则写操作，避免并发请求产生半成品。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

无。批次功能不涉及 YAML 策略文件或配置项，所有行为由前端表单字段驱动。

### L2 扩展（插槽/路由/注册替换）

- 批次产出的告警消息通过 `NotificationFormatter` 扩展点推送（见 `docs/secondary-development.md` 前端插槽外的后端扩展）。
- 默认推送渠道由 `preferences.get_webhook_default_channels` 控制（[preferences.py:947-963](../../../backend/app/services/preferences.py#L947-L963)），用户可在设置页面修改默认值。

### L3 修改（直接改源码）

- **修改派生规则逻辑**：编辑 `strategy/lots.py` 的 `lot_to_rules` 函数（[strategy/lots.py:113-177](../../../backend/app/strategy/lots.py#L113-L177)），注意保持 `id` 后缀 `_p`/`_d` 的稳定性。
- **修改校验规则**：编辑 `strategy/lots.py` 的 `validate_lot` 函数（[strategy/lots.py:41-68](../../../backend/app/strategy/lots.py#L41-L68)）。
- **修改 id 生成方式**：编辑 `api/lots.py:109` 的 `lot_{timestamp:x}_{token_hex(2)}` 格式，注意 `strategy/lots.py` 的 `_MAX_ID_LEN`（[strategy/lots.py:23](../../../backend/app/strategy/lots.py#L23)）约束 — 派生规则 id 后缀后不得超过 40 字符。
- **修改冷却期/告警级别**：编辑 `lot_to_rules` 中的 `cooldown_seconds` 和 `severity` 常量（[strategy/lots.py:151-152](../../../backend/app/strategy/lots.py#L151-L152)）。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件缓存（批次 JSON） | `save_one`/`delete_one` 直接写/删文件 | `data/user_data/lots/` 目录 |
| 文件缓存（规则 JSON） | `monitor_rules.save_one`/`delete_one` 直接写/删文件 | `data/user_data/monitor_rules/` 目录 |
| 内存缓存（引擎规则） | `_reload_engine` → `engine.set_rules` 原子替换 `_rules` | `MonitorRuleEngine._rules` 全量替换 |
| 内存缓存（引擎冷却期） | `set_rules` 计算 `changed_ids`，只清 `_last_fire` 中规则签名未变的条目 | 冷却期状态保留，规则语义变更时重置 |
| 内存缓存（engine date 轮） | `_rules_version` 递增 → `_date_eval_rules_version` 与 `_date_eval_day` 不匹配 → 下一轮重评 | `evaluate_date_rules` 跨天或被规则变更触发 |
| SSE/前端 | `invalidateQueries({ queryKey: QK.lots })` 和 `QK.monitorRules` | 前端列表自动刷新 |
| 文件缓存（告警 JSONL） | 无（append-only，不在此功能范围内） | 告警历史由 `alert_store` 管理 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_lot_to_rules_price_and_date`（映射正确性 + 止盈/止损条件计算 + 消息文本）（L59-73） |
| 单元测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_lot_to_rules_optional_parts`（仅止盈→无 date 规则；仅到期→无 price 规则）（L76-83） |
| 单元测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_validate_lot_rules_and_errors`（8 种非法输入，覆盖空 symbol、零成本价、负数、非法日期、无监控点）（L86-100） |
| 单元测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_normalize_lot_defaults`（缺省字段补全）（L103-107） |
| 集成测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_sync_lot_validates_rules_before_write`（校验失败→批次文件不落盘+引擎不重载，避免半成品）（L111-129） |
| 集成测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_sync_lot_writes_lot_rules_and_reloads_once`（正常写入+重载次数=1）（L132-146） |
| 集成测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_sync_lot_removes_rules_when_monitor_point_removed`（编辑后去掉到期→date 规则级联删除）（L149-158） |
| 集成测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_delete_lot_removes_lot_and_both_rules`（删除批次→批次+两条规则都被删）（L161-170） |
| 集成测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_sync_lot_etf_resolves_asset_type`（ETF 标的的派生规则 asset_type=etf）（L173-188） |
| 集成测试 | [test_lots.py](../../../backend/tests/test_lots.py) | • `test_upsert_lot_invalid_returns_400`（API 层校验返回 400）（L191-198） |

## 依赖关系

### 依赖的其他功能

- **监控中心（Monitor Rules）**：批次功能强依赖 `monitor_rules` 模块的规则存储、校验、归一化、引擎重载能力。`monitor_rules.validate` 拦截非法规则，`monitor_rules.save_one`/`delete_one` 持久化派生规则，`_sync_engine` 将规则加载到引擎。
- **监控规则引擎（MonitorRuleEngine）**：`monitor.py` 的 `MonitorRuleEngine` 负责盘中评估 price 规则和 date 规则。price 规则走 `_evaluate_rule` → `_match_conditions` 匹配行情条件；date 规则走 `evaluate_date_rules` → `date_rule_in_window` 判定窗口。
- **行情轮询（QuoteService）**：`quote_service.py` 的 `_evaluate_monitors` 在每轮行情更新后调用引擎评估，并将告警落盘+推 SSE。
- **偏好设置（Preferences）**：`get_webhook_default_channels` 决定派生规则默认推送渠道。
- **资产类型解析（Repo）**：`repo.resolve_asset_type` 确定标的为 stock/etf，影响派生规则的 `asset_type` 字段，进而决定该规则走股票还是 ETF 评估轮。

### 被依赖的功能

- 无。批次功能是纯生产者，只产出监控规则，不被其他功能依赖。

## 常见问题与注意事项

1. **批次不是持仓记账**：数量只作参考，加减仓/调仓需要走交易口径（issue #230），本功能无会计语义。
2. **派生规则 id 长度限制**：`_MAX_ID_LEN = 38`（[strategy/lots.py:23](../../../backend/app/strategy/lots.py#L23)），派生规则 id 为 `{id}_p`/`{id}_d` 后不得超过 40 字符（`monitor_rules.ID_RE` 约束）。`api/lots.py:109` 的 id 生成使用紧凑 hex 格式，避免超长。
3. **冷却期 24h**：`cooldown_seconds = 86400`（[strategy/lots.py:151](../../../backend/app/strategy/lots.py#L151)），同一条 price 规则对同一标的每天最多触发一次。date 规则冷却期也是 86400s，加 `_date_{today_iso}` 键隔离按天评估。
4. **到期日遇节假日**：`date_rule_in_window` 只判自然日历窗口（[monitor_rules.py:119-132](../../../backend/app/strategy/monitor.py#L119-L132)），到期落在休市/节假日不会顺延，需要 `lead_days` 覆盖。前端提示语建议提前天数 ≥ 2（节假日更大）（[Lots.tsx:396](../../../frontend/src/pages/Lots.tsx#L396)）。
5. **资产类型派生**：`_resolve_asset_type` 解析失败默认回退 `stock`（[api/lots.py:35-39](../../../backend/app/api/lots.py#L35-L39)），这将导致 ETF 批次的止盈止损规则走股票监控轮而不是 ETF 轮，可能永远不触发。日志中记录 `warning` 供排查。
6. **写锁**：`_write_lock`（[api/lots.py:22](../../../backend/app/api/lots.py#L22)）保护 `sync_lot` 和 `delete_lot` 的写入操作，避免并发请求造成批次文件与规则文件不一致。
7. **删除二次确认**：前端首次点击删除按钮进入确认态（红色闪烁"确认"字样），3 秒自动复位，第二次点击真删（[Lots.tsx:100-110](../../../frontend/src/pages/Lots.tsx#L100-L110)）。
8. **前端成本价校验**：提交时 `cost_price` 必须为正数（[Lots.tsx:304](../../../frontend/src/pages/Lots.tsx#L304)），且至少设置止盈%/止损%/到期日之一（[Lots.tsx:308-309](../../../frontend/src/pages/Lots.tsx#L308-L309)），与服务端校验一致。
9. **数字字段输入**：前端使用本地字符串状态承载数字输入（[Lots.tsx:260-267](../../../frontend/src/pages/Lots.tsx#L260-L267)），避免受控 `number` 类型在清空时自动回填 0 的问题。
10. **created_at 保留**：编辑批次时，派生规则保留原有 `created_at`（[api/lots.py:83-85](../../../backend/app/api/lots.py#L83-L85)），避免监控中心列表排序跳动。