# 系统设置（设置 → 系统设置）— 功能文档

> 本文档描述「设置」页「系统设置」Tab 及与之配套的系统级能力（访问认证密码、缓存刷新、版本与更新），只记录已存在的实现，不含任何未实现的设计。
>
> **范围澄清（与直觉不同之处）**：
> - 「认证密码」**不在**系统设置 Tab 内，而是独立的 `/login` 认证页（[Auth.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Auth.tsx)）。系统设置 Tab 内**没有**密码设置 UI，文档在「业务逻辑」中单独说明认证全链路。
> - 「重启管理」在后端**不存在**对应 API 或 UI。用户可操作的只有前端「刷新前端缓存」（纯浏览器侧强制重载）；后端存在的是进程自愈看门狗 [watchdog.py](file:///c:/Code/tick-stock-panel/backend/app/watchdog.py)（进程僵死时自行退出、由 supervisor/Docker 拉起），**非用户可操作**。

## 功能概述

系统设置 Tab 是「设置」页的第四个 Tab（[Settings.tsx:39](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L39)），由 [System.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx) 的 `SettingsSystemPanel` 组件承载，共 6 个区块：

| 区块 | 能力 | 存储位置 | 是否走后端 |
| --- | --- | --- | --- |
| 策略页 | `screener_auto_run` 开关（选股页运行偏好） | `data/user_data/preferences.json` | ✅ |
| 通知弹窗 | 弹窗开关、最大条数、声音开关、声效选择 | `localStorage`（`alert_toast_*` / `alert_sound_*`） | ❌ |
| 语音播报 | 开关、音色选择、语速 | `localStorage`（`voice_broadcast_*`） | ❌ |
| 个股详情外链 | 外链模板（`{code}/{market}/{symbol}` 占位符） | `localStorage`（`stock_external_template`） | ❌ |
| 缓存 | 刷新前端缓存（清 React Query + 强制重载） | 浏览器运行时 | ❌ |
| 关于 | 版本号展示 + 跳转 GitHub Releases | 后端 `app.__version__` / VERSION 文件 | ✅（仅读取） |

配套的系统级能力（不在 Tab 内，但属于「系统设置」主题）：
- **访问认证密码**：`/login` 页设置/登录密码，全后端 `/api/` 受 [main.py](file:///c:/Code/tick-stock-panel/backend/app/main.py#L435-L465) 认证中间件保护。
- **后端自愈看门狗**：进程僵死时 [watchdog.py](file:///c:/Code/tick-stock-panel/backend/app/watchdog.py#L83-L89) 以退出码 70 退出，交由外部进程拉起。

## 文件清单

### 后端

| 文件 | 职责 |
| --- | --- |
| [backend/app/api/settings.py](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py) | `RealtimeMonitorConfigIn`（[1039-1049](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1039-L1049)）、`PUT /preferences/realtime-monitor`（[1052-1080](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1052-L1080)）、`GET /preferences`（`screener_auto_run` 于 [554](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L554)） |
| [backend/app/services/preferences.py](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py) | 偏好存取：`get_screener_auto_run`（[978-980](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L978-L980)，默认 True）、`set_realtime_monitor_config`（[988-998](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L988-L998)）；存储文件 [preferences.json:25](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L25) |
| [backend/app/api/auth.py](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py) | 认证端点：`/status`（[136-143](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L136-L143)）、`/setup`（[146-166](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L146-L166)）、`/login`（[169-194](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L169-L194)）、`/logout`（[197-204](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L197-L204)）、`/change-password`（[207-228](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L207-L228)） |
| [backend/app/services/auth.py](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py) | PBKDF2 哈希（[28-30](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L28-L30)）、会话存储（TTL 30 天，[33](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L33)）、`set_password` 清会话（[106-121](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L106-L121)）、`bootstrap_from_env`（[124-157](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L124-L157)） |
| [backend/app/main.py](file:///c:/Code/tick-stock-panel/backend/app/main.py) | 认证中间件 `auth_middleware`（[435-465](file:///c:/Code/tick-stock-panel/backend/app/main.py#L435-L465)）、白名单（[431-432](file:///c:/Code/tick-stock-panel/backend/app/main.py#L431-L432)）、`bootstrap_from_env` 于 lifespan（[95-101](file:///c:/Code/tick-stock-panel/backend/app/main.py#L95-L101)） |
| [backend/app/watchdog.py](file:///c:/Code/tick-stock-panel/backend/app/watchdog.py) | 自愈看门狗：连续失败达阈值后 `os._exit(70)`（[83-89](file:///c:/Code/tick-stock-panel/backend/app/watchdog.py#L83-L89)） |
| [backend/app/api/data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py) | `GET /api/data/version`（[833-845](file:///c:/Code/tick-stock-panel/backend/app/api/data.py#L833-L845)）：优先 `app.__version__`，回退 VERSION 文件，兜底 `v0.0.0` |

### 前端

| 文件 | 职责 |
| --- | --- |
| [frontend/src/pages/settings/System.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx) | `SettingsSystemPanel`（[20](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L20)）；save（[80-88](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L80-L88)）；`handleClearCache`（[92-99](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L92-L99)）；区块：策略页（[114-120](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L114-L120)）、通知弹窗（[129-203](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L129-L203)）、语音播报（[212-290](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L212-L290)）、个股详情外链（[299-314](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L299-L314)）、缓存（[317-345](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L317-L345)）、关于（[347-379](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L347-L379)） |
| [frontend/src/pages/Settings.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx) | Tab 外壳：TABS 数组（[32-40](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L32-L40)），`{ key: 'system', label: '系统设置', icon: Settings2, panel: SettingsSystemPanel }`（[39](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx#L39)） |
| [frontend/src/pages/Auth.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Auth.tsx) | `/login` 认证页：`isSetup = !status?.configured`（[38](file:///c:/Code/tick-stock-panel/frontend/src/pages/Auth.tsx#L38)），设密码页提示本机/内网限制（[168-185](file:///c:/Code/tick-stock-panel/frontend/src/pages/Auth.tsx#L168-L185)） |
| [frontend/src/lib/api.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts) | `request` 封装（[32-81](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L32-L81)，401 不弹 toast）；auth 方法（[1882-1901](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1882-L1901)）；`updateRealtimeMonitorConfig`（[2115-2135](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2115-L2135)）；`version`（[2270](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2270)） |
| [frontend/src/main.tsx](file:///c:/Code/tick-stock-panel/frontend/src/main.tsx) | 401 全局拦截跳 `/login?redirect=...`，排除 /login 防死循环（[8-26](file:///c:/Code/tick-stock-panel/frontend/src/main.tsx#L8-L26)） |
| [frontend/src/router.tsx](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx) | `/login` 路由挂载 `Auth`（[116](file:///c:/Code/tick-stock-panel/frontend/src/router.tsx#L116)） |
| [frontend/src/lib/queryKeys.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts) | `QK.preferences`、`QK.version`（[15](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L15)）；preferences 不在 SSE 失效列表 |
| [frontend/src/lib/useSharedQueries.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts) | `useVersion`（[76-82](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts#L76-L82)，staleTime: Infinity）、`usePreferences`（[43-48](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts#L43-L48)） |
| [frontend/src/lib/notificationSound.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/notificationSound.ts) | `SOUND_OPTIONS` 12 种声效（[131-144](file:///c:/Code/tick-stock-panel/frontend/src/lib/notificationSound.ts#L131-L144)）、`previewSound`（[147-153](file:///c:/Code/tick-stock-panel/frontend/src/lib/notificationSound.ts#L147-L153)） |
| [frontend/src/lib/voiceBroadcast.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/voiceBroadcast.ts) | `listZhVoices`、`previewVoice`（[205](file:///c:/Code/tick-stock-panel/frontend/src/lib/voiceBroadcast.ts#L205)）、`getCurrentVoiceURI`（[91-93](file:///c:/Code/tick-stock-panel/frontend/src/lib/voiceBroadcast.ts#L91-L93)） |
| [frontend/src/lib/stock-external-link.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/stock-external-link.ts) | 占位符 `{code}/{market}/{symbol}`（[4-8](file:///c:/Code/tick-stock-panel/frontend/src/lib/stock-external-link.ts#L4-L8)）；加载/保存（[16-22](file:///c:/Code/tick-stock-panel/frontend/src/lib/stock-external-link.ts#L16-L22)）；`buildStockExternalUrl` scheme 白名单仅 http/https（[26-27](file:///c:/Code/tick-stock-panel/frontend/src/lib/stock-external-link.ts#L26-L27)） |
| [frontend/src/lib/storage.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/storage.ts) | `stockExternalTemplate` → `localStorage` 键 `stock_external_template`（[48](file:///c:/Code/tick-stock-panel/frontend/src/lib/storage.ts#L48)） |
| [frontend/src/components/AlertToast.tsx](file:///c:/Code/tick-stock-panel/frontend/src/components/AlertToast.tsx) | `refreshAlertToastConfig`（[43](file:///c:/Code/tick-stock-panel/frontend/src/components/AlertToast.tsx#L43)） |

### 配置 / 数据

| 文件 / 键 | 用途 |
| --- | --- |
| `data/user_data/auth.json`（0600 权限） | 密码哈希与盐（[services/auth.py:44-48](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L44-L48)、[61-67](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L61-L67)） |
| `data/user_data/preferences.json`（[preferences.py:25](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L25)） | `screener_auto_run` 等后端偏好 |
| `localStorage`：`alert_toast_enabled` / `alert_toast_max` / `alert_sound_enabled` / `alert_sound` | 通知弹窗偏好 |
| `localStorage`：`voice_broadcast_enabled` / `voice_broadcast_voice` / `voice_broadcast_rate` | 语音播报偏好 |
| `localStorage`：`stock_external_template`（[storage.ts:48](file:///c:/Code/tick-stock-panel/frontend/src/lib/storage.ts#L48)） | 个股详情外链模板 |
| `AUTH_PASSWORD` 环境变量 | 一次性初始化密码（[services/auth.py:124-157](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L124-L157)） |

## 业务逻辑

### 核心流程

**① 系统设置 Tab 保存 `screener_auto_run`**

```text
SettingsSystemPanel.save()                     // System.tsx:80-88
        │  await api.updateRealtimeMonitorConfig(cfg)
        ▼
PUT /api/settings/preferences/realtime-monitor // settings.py:1052-1080
        │  preferences.set_realtime_monitor_config(cfg)
        ▼
data/user_data/preferences.json                 // 持久化
        ▲
qc.invalidateQueries({ queryKey: QK.preferences })  // 失效偏好缓存，触发重读
```

**② 刷新前端缓存（用户可操作的重启观感来源）**

```text
handleClearCache()                 // System.tsx:92-99
   ├─ qc.clear()                   // 清空 React Query 全部缓存
   └─ window.location.href = path + '?_t=' + Date.now()  // 强制整页重载（加时间戳防缓存）
```

> 注意：此操作**不清理** `localStorage`，用户本地偏好（通知/语音/外链模板）均保留；也不影响后端进程。

**③ 认证密码链路（不在 Tab 内，属系统级能力）**

```text
未设密码 → 访问 /api/* → auth_middleware（main.py:435-465）
    ├─ 本机/内网请求 → 放行（免密模式）
    ├─ 公网请求     → 403 NOT_INITIALIZED（提示先设密码）
    └─ 已设密码：校验 tf_session cookie
          ├─ 有效 → 放行
          └─ 无效 → 401 → 前端全局拦截跳 /login（main.tsx:8-26）
```

设密码 / 登录仅允许本机/内网（[auth.py:_is_local_network:42-63](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L42-L63)）；登录失败限流（5 次失败锁 5 分钟，[auth.py:38-39](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L38-L39)）；成功后写 HttpOnly + SameSite=Lax 会话 cookie（30 天）。

**④ 后端自愈看门狗（系统级，非用户可操作）**

```text
主线程僵死 → watchdog 连续失败达阈值（默认 2 次）→ os._exit(70)  // watchdog.py:83-89
         → 由 supervisor / Docker restart 策略拉起
```

### 数据流

1. **前端偏好（大部分区块）**：用户在 System.tsx 修改后直接写入 `localStorage`，不经后端；页面加载时从 `localStorage` 读取并初始化控件（如 `listZhVoices`、`loadStockExternalTemplate`）。
2. **后端偏好（策略页）**：`screener_auto_run` 变更 → `PUT /preferences/realtime-monitor` → `preferences.json` → 失效 `QK.preferences` → 重新拉取；该开关同时影响选股页默认行为（[preferences.get_screener_auto_run](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L978-L980)）。
3. **版本号（关于区块）**：`useVersion()`（staleTime: Infinity）→ `GET /api/data/version` → 后端取 `app.__version__`，缺失则回退 VERSION 文件，再兜底 `v0.0.0`（[data.py:833-845](file:///c:/Code/tick-stock-panel/backend/app/api/data.py#L833-L845)）；「检查更新」直接跳 `https://github.com/shy3130/tickflow-stock-panel/releases/latest`（System.tsx 关于区块）。

### 调用链

| 场景 | 调用链 |
| --- | --- |
| 保存策略页开关 | [System.tsx save:80-88](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx#L80-L88) → [api.updateRealtimeMonitorConfig:2115-2135](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2115-L2135) → [settings.py:1052-1080](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1052-L1080) → [preferences.set_realtime_monitor_config:988-998](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L988-L998) |
| 登录/设密码 | [Auth.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Auth.tsx) → [api.auth*:1882-1901](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L1882-L1901) → [auth.py:146-228](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L146-L228) → [services/auth.py](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py) |
| 请求鉴权 | 任意 `/api/*` → [auth_middleware:435-465](file:///c:/Code/tick-stock-panel/backend/app/main.py#L435-L465) → 401 → [main.tsx:8-26](file:///c:/Code/tick-stock-panel/frontend/src/main.tsx#L8-L26) 跳 `/login` |
| 版本号 | [useVersion:76-82](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts#L76-L82) → [api.version:2270](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts#L2270) → [data.py:833-845](file:///c:/Code/tick-stock-panel/backend/app/api/data.py#L833-L845) |

### 状态机（认证）

```text
未设密码 ──(本机/内网请求)──────────────► 放行（免密）
   │
   ├──(公网请求)───────────────────────► 403 NOT_INITIALIZED（提示先设密码）
   │
   └──(/api/auth/setup 设密码)────────► 已设密码 ──(tf_session 有效)──► 放行
                                            │
                                            └──(cookie 缺失/过期)─────► 401 → 跳 /login
```

改密码（`/change-password`）成功后使**所有**已存在的会话失效（[services/auth.py:106-121](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L106-L121)）。

## 关键数据结构

### API 契约

**认证（[auth.py](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py)）**

| 端点 | 方法 | 入参 | 说明 |
| --- | --- | --- | --- |
| `/api/auth/status` | GET | — | `{ configured: bool }`（[136-143](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L136-L143)） |
| `/api/auth/setup` | POST | `{ password }` | 仅本机/内网；已设密码返回 409（[146-166](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L146-L166)） |
| `/api/auth/login` | POST | `{ password }` | 限流 + 写 HttpOnly cookie（[169-194](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L169-L194)） |
| `/api/auth/logout` | POST | — | 清除会话（[197-204](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L197-L204)） |
| `/api/auth/change-password` | POST | `{ old_password, new_password }` | 成功后全部会话失效（[207-228](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L207-L228)） |

密码校验：最小 6 位（[auth.py:123-133](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L123-L133)）。Cookie：`tf_session`，`SameSite=Lax`，`HttpOnly`，30 天（[auth.py:32-33](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L32-L33)）。

**偏好（[settings.py](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）**

| 端点 | 方法 | 入参 | 说明 |
| --- | --- | --- | --- |
| `/api/settings/preferences` | GET | — | 返回 `screener_auto_run` 等（[554](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L554)） |
| `/api/settings/preferences/realtime-monitor` | PUT | `{ screener_auto_run?: bool, ... }`（[1039-1049](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1039-L1049)） | 保存实时监控/选股偏好（[1052-1080](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py#L1052-L1080)） |

**版本**

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/api/data/version` | GET | `{ version: string }`（[data.py:833-845](file:///c:/Code/tick-stock-panel/backend/app/api/data.py#L833-L845)） |

### 存储结构

- `data/user_data/auth.json`：`{ password_hash, salt, ... }`，PBKDF2-HMAC-SHA256、200,000 迭代、16 字节盐（[services/auth.py:28-30](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L28-L30)）；文件权限 0600（[61-67](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L61-L67)）。
- `data/user_data/preferences.json`：后端偏好 JSON，含 `screener_auto_run`（默认 True）。
- `localStorage`：通知弹窗、语音播报、外链模板均为浏览器本地键，无后端落盘。

### 内存结构

- 认证会话：内存 Map + 文件双存，启动时从文件恢复（[services/auth.py:204-222](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L204-L222)）；`is_configured` 带缓存（[93-103](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L93-L103)）。
- React Query：`QK.preferences`（偏好）、`QK.version`（版本，staleTime: Infinity）供全局共享（[queryKeys.ts:15](file:///c:/Code/tick-stock-panel/frontend/src/lib/queryKeys.ts#L15)、[useSharedQueries.ts:43-82](file:///c:/Code/tick-stock-panel/frontend/src/lib/useSharedQueries.ts#L43-L82)）。

## 扩展与修改指南

### 变更分级

| 级别 | 场景 | 落点 |
| --- | --- | --- |
| L1 | 调整某个本地偏好默认值 / 新增同类型本地偏好开关 | 只改前端 [System.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/System.tsx) 区块 + `localStorage` 读写工具，无需动后端 |
| L3 | 修改认证策略、新增后端偏好字段、改看门狗阈值 | 需改 [auth.py](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py) / [services/auth.py](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py) / [settings.py](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py) / [watchdog.py](file:///c:/Code/tick-stock-panel/backend/app/watchdog.py)，按 CONTRIBUTING §9 补回归 |

### 缓存失效影响表

| 变更 | 受影响缓存层 |
| --- | --- |
| `screener_auto_run` 变更（保存） | 后端 `preferences.json`（文件）→ 内存偏好 → 前端 `QK.preferences`（React Query）→ 依赖该偏好的页面（选股页） |
| `QK.version` | staleTime: Infinity，仅在应用发布后重启浏览器/前端进程时自然更新 |
| 刷新前端缓存 | 清空 React Query 全部键 + 整页重载；`localStorage` 不动，SSE 订阅重建 |
| 修改密码 / 登录 / 登出 | 后端会话存储（文件 + 内存）→ 前端 cookie → 401 跳转触发前端会话态重置 |
| 本地偏好（通知/语音/外链） | 仅 `localStorage`，不进入后端与 SSE 缓存链路（`QK.preferences` 不在 SSE 失效前缀列表） |

### 测试矩阵（最小充分验证）

| 变更 | 建议验证 |
| --- | --- |
| 偏好相关改动 | 后端定向 pytest（settings/preferences）+ `ruff`；前端 `pnpm build` |
| 认证相关改动 | 后端 auth 测试 + 认证中间件定向测试 + `ruff`；前端 `pnpm build` |
| 纯前端本地偏好改动 | 前端 `pnpm build` 即可 |

## 依赖关系

- **对外依赖**：语音播报依赖浏览器 Web Speech API（[voiceBroadcast.ts](file:///c:/Code/tick-stock-panel/frontend/src/lib/voiceBroadcast.ts)）；「检查更新」依赖 GitHub Releases 外链（仅跳转，无后端请求）。
- **对内依赖**：Tab 外壳依赖 [Settings.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx) 的 TABS 注册机制；偏好依赖 [preferences.py](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py) 存储服务；认证依赖 [auth_middleware](file:///c:/Code/tick-stock-panel/backend/app/main.py#L435-L465) 全局守卫与 [main.tsx](file:///c:/Code/tick-stock-panel/frontend/src/main.tsx#L8-L26) 401 跳转。
- **生产环境提示**：认证中间件默认拦截全部 `/api/`，`/docs`、`/health`、`/api/auth/*` 在白名单（[main.py:431-432](file:///c:/Code/tick-stock-panel/backend/app/main.py#L431-L432)），部署时需注意。

## 常见问题与注意事项

### 安全注意事项

- **设密码仅限本机/内网**：`/api/auth/setup` 与 `/api/auth/login` 通过 `_is_local_network`（[auth.py:42-63](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L42-L63)）拒绝公网直接调用；公网首次访问未设密码服务返回 403 而非 401，避免误导。
- **`X-Forwarded-For` 信任规则**：仅当直连 peer 为本机时才采信（[auth.py:66-78](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L66-L78)），防止伪造来源绕过本机限制。
- **登录限流**：5 次失败锁定 5 分钟（[auth.py:38-39](file:///c:/Code/tick-stock-panel/backend/app/api/auth.py#L38-L39)），减缓暴力破解。
- **密码哈希**：PBKDF2-HMAC-SHA256、200,000 迭代、16 字节随机盐 + 恒定时间比较（[services/auth.py:28-30](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L28-L30)、[78-86](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L78-L86)）。
- **会话 cookie**：HttpOnly + SameSite=Lax，前端脚本不可读取；改密码后全部旧会话立即失效（[services/auth.py:106-121](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L106-L121)）。
- **外链安全**：个股详情外链只放行 http/https scheme（[stock-external-link.ts:26-27](file:///c:/Code/tick-stock-panel/frontend/src/lib/stock-external-link.ts#L26-L27)），防止 `javascript:` 等危险协议。
- **认证白名单**：`/docs`、`/openapi.json` 等免鉴权暴露于公网，生产部署建议加反向代理层防护。

### 常见问题

- **「刷新前端缓存」会清掉我的设置吗？** 不会。它只清 React Query 缓存并强制重载页面；`localStorage` 中的通知/语音/外链偏好与后端 `preferences.json` 均保留。
- **为什么系统设置里没有「重启后端」按钮？** 项目未实现一键重启后端 API。后端提供的是自愈看门狗 [watchdog.py](file:///c:/Code/tick-stock-panel/backend/app/watchdog.py)：进程僵死时以退出码 70 退出，由 supervisor/Docker 拉起；如需手动重启请操作宿主进程管理（如 `docker restart`）。
- **密码设置入口在哪？** 不在系统设置 Tab。未设密码时公网访问会被引导，或直接访问 `/login`（[Auth.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Auth.tsx)）；亦可用 `AUTH_PASSWORD` 环境变量一次性初始化（[services/auth.py:124-157](file:///c:/Code/tick-stock-panel/backend/app/services/auth.py#L124-L157)）。
- **为什么 `screener_auto_run` 走后端而其他偏好走 localStorage？** 该开关影响选股页的**后端驱动行为**（策略筛选自动运行），需跨会话、跨前端实例一致，故持久化到 `preferences.json`；其余为纯展示层本地偏好。
