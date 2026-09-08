---
title: 网络设置
description: 网络设置页功能文档 — 数据任务停滞超时配置 + 分时/日K批量传输压缩开关。
---

# 网络设置（设置 → 网络设置） — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

「网络设置」页是「设置」页签之一（Tab key `timeout`，菜单名为「网络设置」，前端外壳见 [Settings.tsx:32-40](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx)，图标 `Clock3`），负责两类与数据传输/任务运行相关的配置：

1. **超时设置**（卡片内区块标题保持「超时设置」）：普通数据后台任务与长任务的**停滞卡死判定**阈值。
2. **数据传输压缩**：分时（分钟K）批量与日K批量大 JSON 响应的 gzip 传输压缩开关。

核心定位：**后台数据任务「进度停滞」判定的唯一配置入口**，以及**大数据批量接口传输压缩的唯一配置入口**。注意该 Tab 并不包含「前端请求超时」的 UI 配置——前端请求超时是 `api.ts` 请求层的默认机制（详见「常见问题与注意事项」），与后端 job 停滞超时是两套独立语义。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 入口 | `backend/app/api/settings.py` | `GET /preferences` 返回偏好、3 个 `PUT` 端点保存超时与压缩开关 |
| 偏好服务 | `backend/app/services/preferences.py` | 超时/压缩 getter 与 `save()` 落盘（锁内 read-modify-write） |
| Job 存储 | `backend/app/services/pipeline_jobs.py` | `DEFAULT_JOB_TIMEOUT_S`/`LONG_JOB_TIMEOUT_S` 默认值、`create()` 读配置、`reap_stale()` 停滞判定 |
| 管道 API | `backend/app/api/pipeline.py` | `POST /run`、`GET /jobs/{id}` 轮询时触发 `reap_stale()` |
| K 线 API | `backend/app/api/kline.py` | `_gzip_payload()` 按偏好键对分时/日K批量响应做 gzip 压缩 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/settings/Timeout.tsx` | `SettingsTimeoutPanel` 外壳，转发渲染 `JobTimeoutCard` |
| 组件 | `frontend/src/pages/settings/JobTimeoutCard.tsx` | 超时输入（秒/分/时）、保存按钮、压缩总开关与子开关 |
| API 客户端 | `frontend/src/lib/api.ts` | `updateDataSourceJobTimeouts` / `updateMinuteBatchCompress` / `updateDailyBatchCompress` / `preferences` |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `QK.preferences`（['preferences']） |
| 共享查询 | `frontend/src/lib/useSharedQueries.ts` | `usePreferences()` 拉取偏好 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 偏好存储 | `data/user_data/preferences.json` | `data_source_job_timeout_s` / `data_source_long_job_timeout_s` / `minute_batch_compress` / `daily_batch_compress` |

## 业务逻辑

### 核心流程

```text
网络设置 Tab（JobTimeoutCard）
├─ 超时设置：
│   ├─ 普通任务停滞超时（默认 1200s / 20 分钟，最小 60s）
│   ├─ 长任务停滞超时（默认 1800s / 30 分钟，最小 60s，分钟K全市场同步）
│   └─ 保存 → PUT /api/settings/preferences/data-source-job-timeouts
│       → preferences.save() 落盘 → 新建任务 create() 时读取写入 job.timeout_s
│       → reap_stale() 按「进度停滞」判定卡死 → terminate()（协作式取消）
└─ 数据传输压缩：
    ├─ 总开关：任一子项开即亮，点击全开/全关（并行写两个子项）
    ├─ 分时数据压缩 → PUT /preferences/minute-batch-compress
    ├─ 日K数据压缩   → PUT /preferences/daily-batch-compress
    └─ 逐请求即时读取：kline.py _gzip_payload() 按偏好 + accept-encoding 决定压缩
```

### 数据流

1. **输入来源**：
   - 超时值：用户在 [JobTimeoutCard.tsx:133-196](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx) 的 number 输入框 + 单位下拉（秒/分/时）填写，前端换算为秒。
   - 压缩开关：总开关与两个子开关的切换（[JobTimeoutCard.tsx:198-235](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）。
2. **处理过程**：
   - 超时换算：`TIMEOUT_UNIT_SECONDS`（[JobTimeoutCard.tsx:15-19](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）按秒/分/时折算；单位智能推荐 `preferredTimeoutUnit()`（[JobTimeoutCard.tsx:21-25](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）——≥3600 且被 1800 整除建议小时、被 60 整除建议分钟，否则秒。校验规则（[JobTimeoutCard.tsx:52-54](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）：两个输入必须为有限正数，且换算成秒后均 ≥60。
   - 保存：`saveJobTimeouts` 调 `api.updateDataSourceJobTimeouts(regularTimeout, longTimeout)`（[JobTimeoutCard.tsx:99-109](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）。
   - 压缩保存：`toggleCompress` / `toggleDailyCompress` 分别保存两个子项；`toggleAllCompress` 用 `Promise.all` 并行写两个子项（[JobTimeoutCard.tsx:82-97](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）。
   - 后端落盘：三个 `PUT` 端点都调用 `preferences.save()`（锁内 read-modify-write，见 [preferences.py:61-74](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)）。
3. **输出去向**：
   - 超时值 → `preferences.json` → 下一次 `JobStore.create()` 读取，写入 `job["timeout_s"]`（[pipeline_jobs.py:200-254](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)），**对新建任务生效，正在运行的任务不受影响**。
   - 压缩开关 → `preferences.json` → kline 批量接口**逐请求即时读取**（保存后立即生效，无缓存）。

### 调用链

```text
超时保存：
JobTimeoutCard.tsx:99-109 → api.updateDataSourceJobTimeouts → PUT /api/settings/preferences/data-source-job-timeouts
  → settings.py:803-808 → preferences.save() → preferences.py:61-74（preferences.json）
  → 新建任务 JobStore.create()（pipeline_jobs.py:219-224 读 getter）→ job.timeout_s
  → 轮询/触发时 reap_stale()（pipeline.py:37 / pipeline.py:91）→ pipeline_jobs.py:367-423
  → 停滞超阈值 → terminate()（pipeline_jobs.py:425-437）

压缩保存：
JobTimeoutCard.tsx:62-97 → api.updateMinuteBatchCompress / updateDailyBatchCompress
  → PUT /api/settings/preferences/minute-batch-compress（settings.py:811-816）
  → PUT /api/settings/preferences/daily-batch-compress（settings.py:819-824）
  → preferences.save() → preferences.json
  → kline.py:853（分时）/ kline.py:634（日K）→ _gzip_payload()（kline.py:27-59）
```

### 状态机（如适用）

超时保存按钮的可用性由校验状态驱动（[JobTimeoutCard.tsx:52-56](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）：

```text
输入非法（非数 / ≤0 / <60s）或未变更 → 保存按钮 disabled
        │  输入合法且已变更
        ▼
保存中（saveJobTimeouts.isPending → 文案「保存中...」）
        │  onSuccess
        ▼
清空草稿（setTimeoutDraft(null)）+ 刷新 QK.preferences + toast「任务超时配置已保存」
```

压缩总开关状态（[JobTimeoutCard.tsx:58-61](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）：任一子项开启则总开关为开；点击总开关 = 全开/全关（并行写两个子项）。

## 关键数据结构

### API 契约

**`GET /api/settings/preferences`** 返回的相关字段（[settings.py:494-519](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)，网络相关在第 515-518 行）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data_source_job_timeout_s` | int | 普通数据任务停滞判定阈值（秒），默认 1200 |
| `data_source_long_job_timeout_s` | int | 长任务（分钟K全市场同步）停滞判定阈值（秒），默认 1800 |
| `minute_batch_compress` | bool | 分时批量响应 gzip 压缩，默认 true |
| `daily_batch_compress` | bool | 日K批量响应 gzip 压缩，默认 true |

前端 `Preferences` 接口同名字段见 [api.ts:1799-1802](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)，读取端点 `api.preferences` 为 `GET /api/settings/preferences`（[api.ts:1929](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)）。

**`PUT /api/settings/preferences/data-source-job-timeouts`**（[settings.py:803-808](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：

请求体 `DataSourceJobTimeoutPrefs`（[settings.py:426-428](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：

```json
{
  "data_source_job_timeout_s": 1200,
  "data_source_long_job_timeout_s": 1800
}
```

两个字段均 `Field(ge=60)`——后端最小 60 秒。响应原样回显 `req.model_dump()`。

**`PUT /api/settings/preferences/minute-batch-compress`**（[settings.py:811-816](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：请求体 `MinuteBatchCompressPrefs`（`{"minute_batch_compress": bool}`，[settings.py:431-432](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）；响应 `{"minute_batch_compress": <getter 结果>}`。

**`PUT /api/settings/preferences/daily-batch-compress`**（[settings.py:819-824](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：请求体 `DailyBatchCompressPrefs`（`{"daily_batch_compress": bool}`，[settings.py:435-436](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。

前端对应方法见 [api.ts:1982-2007](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)（`updateDataSourceJobTimeouts` / `updateMinuteBatchCompress` / `updateDailyBatchCompress`），均为 `PUT` + JSON body。

### 存储结构

- **`data/user_data/preferences.json`**（路径由 [preferences.py:23-27](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py) 决定）：
  - `data_source_job_timeout_s`（默认 1200）
  - `data_source_long_job_timeout_s`（默认 1800）
  - `minute_batch_compress`（默认 true）
  - `daily_batch_compress`（默认 true）
- 采用 `save()` 锁内 read-modify-write 落盘（[preferences.py:61-74](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)），`_SAVE_LOCK` 防止并行 PUT 互相覆盖（压缩总开关并行写两个子项的场景）。

### 内存结构

- `preferences.py` 进程内缓存带 `(mtime_ns, size)` 签名，文件变化才重读（[preferences.py:36-55](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)）。
- `JobStore` 中每个 job 记录带 `timeout_s` 字段，`create()` 时快照用户配置（[pipeline_jobs.py:246](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)）。
- 超时默认常量集中在 `pipeline_jobs.py`：`DEFAULT_JOB_TIMEOUT_S = 1200`、`LONG_JOB_TIMEOUT_S = 1800`、`HARD_JOB_TIMEOUT_S = 12 * 3600`、兼容别名 `STALE_JOB_TIMEOUT_S`（[pipeline_jobs.py:38-44](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)）。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- 直接编辑 `data/user_data/preferences.json` 中的四个键可生效；超时值小于 60 会被 `getter` 钳制到 60（[preferences.py:232](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py) 与 [preferences.py:246](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)）。

### L2 扩展（插槽/路由/注册替换）

- 该功能没有独立插槽；若要新增第三类「批量压缩开关」（如周K批量），需在 `kline.py` 的 `_getters` 字典与前端 `JobTimeoutCard` 同步新增。

### L3 修改（直接改源码）

- 修改默认阈值：`pipeline_jobs.py` 的 `DEFAULT_JOB_TIMEOUT_S`/`LONG_JOB_TIMEOUT_S`（[pipeline_jobs.py:38-39](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)），同时同步 `preferences.py` 的 `getter` 默认值与前端 [JobTimeoutCard.tsx:40-41](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx) 的回退默认值。
- 修改最小限制：后端 `DataSourceJobTimeoutPrefs.Field(ge=60)`（[settings.py:427-428](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）与 `preferences.py` 的 `DATA_SOURCE_JOB_TIMEOUT_MIN_S`（[preferences.py:221](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)）、前端校验（[JobTimeoutCard.tsx:52-54](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）需三处联动。
- 修改压缩阈值/级别：`_gzip_payload()` 的 1024 字节阈值与 gzip `level 6`（[kline.py:53-55](file:///c:/Code/tick-stock-panel/backend/app/api/kline.py)）。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件 | 直接写 `preferences.json`（`save()`） | 四个偏好键 |
| 内存 | `save()` 调 `_invalidate_cache()` 清进程缓存；kline 压缩逐请求读取不缓存 | 超时 getter、压缩 getter |
| 前端 | 保存成功后 `qc.setQueryData(QK.preferences)` 乐观合并（[JobTimeoutCard.tsx:64-68](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx) 等） | 卡片当前值显示、`usePreferences()` 消费者 |
| Job 记录 | 超时修改只对**新建**任务生效，运行中的 job 保持 `create()` 时快照的 `timeout_s` | 不影响运行中任务 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 单元测试 | `backend/tests/test_job_stall_and_cancel.py` | 停滞判定 reap（`test_stalled_job_is_reaped`，[L43-60](file:///c:/Code/tick-stock-panel/backend/tests/test_job_stall_and_cancel.py)）；协作式取消 flag |
| 回归测试 | `backend/tests/test_pipeline_and_monitor_fixes.py` | 用户配置超时被 `create()` 读取：普通 3600s（[L19-37](file:///c:/Code/tick-stock-panel/backend/tests/test_pipeline_and_monitor_fixes.py)）、长任务 5400s（[L40-50](file:///c:/Code/tick-stock-panel/backend/tests/test_pipeline_and_monitor_fixes.py)） |
| API/偏好测试 | `backend/tests/test_minute_routing.py` | 压缩默认开与切换（[L1018-1025](file:///c:/Code/tick-stock-panel/backend/tests/test_minute_routing.py)）；开启返回 gzip（[L1053-1068](file:///c:/Code/tick-stock-panel/backend/tests/test_minute_routing.py)）；关闭/未声明 gzip 原样返回（[L1071-1083](file:///c:/Code/tick-stock-panel/backend/tests/test_minute_routing.py)）；并行写两个压缩键互不覆盖（[L1169-1183](file:///c:/Code/tick-stock-panel/backend/tests/test_minute_routing.py)） |

## 依赖关系

### 依赖的其他功能

- [设置页外壳](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx)：网络设置作为 `timeout` Tab 挂载在设置页。
- [偏好服务](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)：所有 getter/save 由它提供。

### 被依赖的功能

- [数据任务管道](../architecture.md)：`JobStore.create()` 读取超时阈值，`reap_stale()` 执行停滞判定。
- K 线批量接口：`/api/kline/minute-batch` 与日K批量接口通过 `_gzip_payload()` 消费压缩开关。
- [数据源设置](data-sources.md)：数据源页面与网络设置共享 `JobStore` 任务生命周期与偏好存储。

## 常见问题与注意事项

- **「进度停滞」≠「总时长」**：停滞判定只在 running 期间**没有新进度上报**超过阈值时才判卡死（[pipeline_jobs.py:414-418](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)）；慢带宽冷启动全市场拉取只要分块在推进就不会被误杀。另有总时长 12h 硬上限兜底病态循环（[pipeline_jobs.py:42](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)、[pipeline_jobs.py:419-423](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py)）。
- **修改只对新建任务生效**：超时阈值在 `create()` 时快照到 `job.timeout_s`，已运行任务不受修改影响；前端文案明确「保存时自动换算为秒，修改后对新建任务生效」（[JobTimeoutCard.tsx:117-120](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）。
- **前端请求超时与后端 job 超时是两套独立机制**：网络设置 Tab **没有**「前端请求超时」配置 UI。前端请求超时是 `api.ts` 请求层的默认行为——`request()` 默认 30s（`DEFAULT_REQUEST_TIMEOUT_MS = 30_000`，[api.ts:28](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)），计算型接口（回测/筛选）放宽到 300s（`COMPUTE_REQUEST_TIMEOUT_MS`，[api.ts:30](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)），`timeoutMs` 传 `null` 或自带 `signal` 时不启用默认超时（[api.ts:40-43](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)）；超时后抛 `ApiError("请求超时（Xs）· path", 0)`（[api.ts:52-56](file:///c:/Code/tick-stock-panel/frontend/src/lib/api.ts)）。
- **单位智能推荐**：`preferredTimeoutUnit()` 仅在输入能被 1800/60 整除时推荐小时/分钟，否则用秒；切换单位会把当前值按原单位换算后重填，不丢值（[JobTimeoutCard.tsx:21-31](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/JobTimeoutCard.tsx)）。
- **压缩的协商前提**：gzip 仅在「偏好开 + 客户端 `Accept-Encoding` 含 gzip + 响应体 > 1024 字节」三者同时满足时启用（[kline.py:48-58](file:///c:/Code/tick-stock-panel/backend/app/api/kline.py)）；level 6 是实测权衡（13MB ≈ 290ms CPU 压掉 87%，level 9 需 2.5s 不可用）。
- **压缩开关立即生效**：与超时不同，压缩开关逐请求即时读取，保存后无需重启；本机/内网可关闭以节省服务端 CPU（默认开启，公网部署传输是大头）。
- **并发安全**：`preferences.save()` 用 `_SAVE_LOCK` 做锁内 read-modify-write，压缩总开关并行写两个子项不会互相覆盖（[preferences.py:58-74](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py)）。
