---
title: AI 大盘复盘 — 功能文档
description: AI 复盘 Review 功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。
---

# AI 大盘复盘 — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

AI 大盘复盘（Review）是 TSP 的盘后复盘工作台，用户一键触发 AI 流式生成结构化大盘复盘报告（含指数/涨跌/板块/资金/情绪/消息/风险），支持报告归档、历史查看、删除、定时自动生成与多渠道推送（飞书/企微/自定义 Webhook/邮件）。路由 `/review`，入口在左侧菜单「复盘」。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `backend/app/api/market_recap.py:27` | 复盘相关端点注册，`/api/market-recap` 前缀 |
| API 设置 | `backend/app/api/settings.py:1871-1931` | 定时复盘调度与推送渠道偏好的写端点 |
| SSE 流 | `backend/app/api/intraday.py:156-162` | 定时复盘进度事件通过 SSE `review_progress` 事件推给前端 |
| 核心服务 | `backend/app/services/market_recap.py:1-384` | 流式复盘生成主逻辑：装配市场数据 → 构建 prompt → 流式调用 LLM |
| 报告持久化 | `backend/app/services/market_recap_reports.py:1-44` | 复盘报告的 CRUD，委托 `JsonReportStore` |
| 共享存储底座 | `backend/app/services/json_report_store.py:1-124` | JSON 原子写 + 实例锁的共享存储底座 |
| 市场总览 | `backend/app/services/market_overview_builder.py:356-594` | 装配市场总览数据（与 Dashboard 同源，被 `recap_market_stream` 调用） |
| AI Provider | `backend/app/services/ai_provider.py` | `stream_ai_text` 流式调用 LLM |
| 龙虎榜上下文 | `backend/app/services/dragon_tiger.py` | `build_recap_context` 供复盘 prompt 嵌入龙虎榜摘要 |
| 盘前风向标 | `backend/app/services/auction_benchmark.py` | `build_recap_context` 供复盘 prompt 嵌入竞价筛选摘要 |
| 偏好设置 | `backend/app/services/preferences.py:594-711` | `review_schedule` / `review_push_channels` / `review_push_mode` 的读写 |
| 推送适配器 | `backend/app/services/webhook_adapter.py` | 飞书/企微/自定义 Webhook 推送 |
| 邮件推送 | `backend/app/services/email_adapter.py` | SMTP 邮件推送 |
| 定时任务 | `backend/app/jobs/daily_pipeline.py:895-1120` | 定时复盘 job：注册/更新/执行/重试/推送门控 |
| 行情服务 | `backend/app/services/quote_service.py:449-456` | `push_review_event` 广播复盘事件到所有 SSE 订阅者 |
| SSE 订阅者 | `backend/app/services/quote_service.py:89-135` | `SnapshotSubscriber` 管理 `_reviews` 队列，支持背压丢弃 |
| 测试 | `backend/tests/test_review_push_mode.py` | 推送触发模式（auto/manual）门控测试 |
| 测试 | `backend/tests/test_ai_analysis_focus.py` | 关注点指令（`build_focus_instruction`）相关的测试 |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/Review.tsx:1-1391` | 复盘页主组件：市场摘要条 + 龙虎榜 + 关注点输入 + 报告面板 + 历史面板 + 定时弹窗 |
| 路由 | `frontend/src/router.tsx:32,51,132` | 懒加载 `Review` 组件，挂载到 `/review` 路径 |
| 全局 Store | `frontend/src/lib/reviewStore.ts:1-220` | 模块级单例状态管理：phase/content/meta，脱离组件生命周期，支持手动流与 SSE 流 |
| React Hook | `frontend/src/lib/useReviewStore.ts:1-14` | 用 `useSyncExternalStore` 订阅 reviewStore 的 React hook |
| API 客户端 | `frontend/src/lib/api.ts:670-679,3217-3289` | `AiReviewReport` 类型、`reviewReportsList`、`reviewReportSave`、`reviewReportDelete`、`reviewStream`（AsyncGenerator/NDJSON 解析） |
| Query Keys | `frontend/src/lib/queryKeys.ts:110` | `QK.reviewReports` 查询键，用于 React Query 缓存 |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 存储 | `data/user_data/ai_market_recaps.json` | 复盘报告持久化文件（JSON 数组，按 created_at 降序，最多 20 条） |
| 偏好 | `data/user_data/preferences.json` | 存储 `review_schedule` / `review_push_channels` / `review_push_mode` |

## 业务逻辑

### 核心流程

```text
用户点击「生成复盘」→ [手动流] POST /api/market-recap/analyze
                         → recap_market_stream() 装配市场总览
                         → _build_user_prompt() 构建 prompt（含龙虎榜/风向标/新闻/关注点）
                         → stream_ai_text() 流式调用 LLM
                         → NDJSON 事件（meta/delta/error/done）逐 chunk 返回
                         → reviewStore 累积 content + 更新 phase
                         → 生成完毕 → onGenerationDone → POST /api/market-recap/reports 归档
                         → 前端 invalidate QK.reviewReports

定时自动复盘 → _run_scheduled_review() → recap_market_stream()
             → 每事件经 quote_service.push_review_event() → SSE review_progress → feedReviewEvent()
             → 生成完毕 → market_recap_reports.save_report() 落盘
             → 推送门控: get_review_push_mode() == "auto" → _maybe_push_review() 多渠道推送
```

### 数据流

1. **输入来源**：
   - 手动触发：用户点击「生成复盘」按钮（[Review.tsx:276-291](file:///c:/Code/tick-stock-panel/frontend/src/pages/Review.tsx#L276-L291)）
   - 定时触发：APScheduler 工作日 cron 触发（[daily_pipeline.py:1111-1120](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L1111-L1120)）
   - 数据源：`build_market_overview` 聚合指数/涨跌/板块/情绪数据（[market_overview_builder.py:356-594](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L356-L594)）

2. **处理过程**：
   - `recap_market_stream` 装配市场总览 → 构建 system prompt（固定八节模板） + user prompt（数据切片 + 龙虎榜 + 风向标 + 新闻 + 关注点）→ 流式调用 LLM（[market_recap.py:277-353](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L277-L353)）
   - 指数简称映射保证摘要与前端一致（[market_recap.py:27-34](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L27-L34)）
   - 情绪分计算：六维雷达均分 → 标签映射（强势/偏暖/震荡/偏冷/冰点）（[market_overview_builder.py:531-549](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L531-L549)）

3. **输出去向**：
   - 手动流：NDJSON → 前端 reviewStore → 页面渲染 + 归档到 `ai_market_recaps.json`
   - 定时流：NDJSON → SSE `review_progress` → `feedReviewEvent()` → reviewStore → 归档 + 推送（飞书/企微/自定义 Webhook/邮件）

### 调用链

**手动流**：
```text
Review.tsx:197 generate() → reviewStore.ts:75 startReviewGeneration()
  → api.ts:3248 reviewStream() → POST /api/market-recap/analyze
  → market_recap.py:77 analyze_market() → market_recap.py:102 recap_market_stream()
    → market_overview_builder.py:356 build_market_overview() (数据源)
    → market_recap.py:182 _build_user_prompt() (含 dragon_tiger.py / auction_benchmark.py 上下文)
    → ai_provider.py stream_ai_text() (LLM 流式调用)
  → NDJSON 逐事件 → reviewStore.ts:93-131 处理 phase/content/meta
  → 生成完毕 → Review.tsx:184 onGenerationDone() → api.ts:3232 reviewReportSave()
  → API market_recap.py:134 save_report() → market_recap_reports.py:39 save_report()
  → json_report_store.py:85 save_report() (原子写 JSON)
```

**定时流**：
```text
daily_pipeline.py:1111 APScheduler CronTrigger → _run_scheduled_review()
  → _stream_review_with_retry() (最多 3 次尝试)
    → recap_market_stream() (同上)
    → 每事件: quote_service.py:450 push_review_event() → SSE intraday.py:158 review_progress
    → 前端 reviewStore.ts:185 feedReviewEvent() 更新 store
  → 生成完毕 → market_recap_reports.save_report() 落盘
  → 推送门控: daily_pipeline.py:1028 _maybe_push_review()
    → webhook_adapter.py / email_adapter.py 多渠道推送
```

### 状态机

reviewStore 的 `phase` 状态转换：

```text
idle → loading → streaming → done (正常完成)
idle → loading → streaming → error (失败)
idle → loading → error (直接失败)
done → idle (resetReview / 重新生成)
```

定时流 SSE 场景：`feedReviewEvent` 首次收到 `meta` 事件时 phase 从 idle 直接切到 `streaming`，不经过 `loading`。

### 前端组件结构

```
Review (页面)
├── MarketSummaryBar (市场摘要条：情绪分 + 四大指数 + 涨跌结构 + 涨停结构 + 成交额)
├── DragonTigerCard (龙虎榜卡片：折叠/展开，三榜 tab，可排序表格，游资席位列表)
├── 关注点输入框 (focus input)
├── ReportPanel (报告面板：空态/加载态/流式/错误/完成态，含复制/下载)
├── HistoryPanel (历史面板：列表显示，含生成中占位项，删除)
└── 定时复盘弹窗 (开关 + 时间设置 + 推送渠道多选 + 推送触发方式)
```

## 关键数据结构

### API 契约

**POST /api/market-recap/analyze** — 流式复盘请求

```json
// 请求
{ "as_of": "2026-06-27", "focus": "关注半导体板块" }

// 响应 NDJSON 逐行:
{"type":"meta","as_of":"2026-06-27","emotion_score":68,"emotion_label":"偏暖","summary":"上-0.23%..."}
{"type":"delta","content":"## 盘面总览\n三大指数..."}
{"type":"error","message":"AI 复盘失败: ..."}
{"type":"done"}
```

**GET /api/market-recap/reports** — 历史报告列表

```json
{ "reports": [
  { "id": "mkr_1719478500000", "as_of": "2026-06-27", "focus": "",
    "content": "# 复盘报告...", "summary": "上-0.23%...", "emotion_score": 68,
    "emotion_label": "偏暖", "created_at": "2026-06-27T15:35:00" }
] }
```

**POST /api/market-recap/reports** — 保存报告

```json
// 请求
{ "as_of": "2026-06-27", "focus": "", "content": "# 报告...",
  "summary": "上-0.23%...", "emotion_score": 68, "emotion_label": "偏暖", "push": false }
// 响应
{ "ok": true, "report": { "id": "mkr_...", "created_at": "..." } }
```

### 存储结构

**`data/user_data/ai_market_recaps.json`** — JSON 数组，按 `created_at` 降序，最多 20 条（[market_recap_reports.py:27-31](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap_reports.py#L27-L31)）

每条报告结构：
```json
{
  "id": "mkr_1719478500000",       // 唯一 id (market-recap-report)
  "as_of": "2026-06-27",            // 复盘日期
  "focus": "",                      // 用户追加的关心点
  "content": "# ...markdown",       // 报告正文
  "summary": "上-0.23%...",         // 一句话摘要
  "emotion_score": 68,              // 情绪分 0-100
  "emotion_label": "偏暖",          // 情绪标签
  "created_at": "2026-06-27T15:35:00"  // 创建时间 ISO
}
```

**`data/user_data/preferences.json`** — 复盘相关偏好：
- `review_schedule`: `{"enabled": false, "hour": 15, "minute": 40}` — 默认关闭，15:40（盘后管道 15:35 后 5 分钟缓冲）
- `review_push_channels`: `[]` — 空数组=不推送，可选 `["feishu", "wecom", "custom", "email"]`
- `review_push_mode`: `"manual"` — 默认手动确认，可选 `"auto"`（归档即推）

### 内存结构

**reviewStore**（[reviewStore.ts:24-30](file:///c:/Code/tick-stock-panel/frontend/src/lib/reviewStore.ts#L24-L30)）：
```typescript
interface ReviewState {
  phase: 'idle' | 'loading' | 'streaming' | 'done' | 'error'
  content: string        // 累积的 Markdown 文本
  error: string
  meta: ReviewMeta | null  // { as_of, emotion_score, emotion_label, summary }
  focus: string
}
```

**SSE 订阅者队列**（[quote_service.py:89-98](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py#L89-L98)）：
修订版本 `SnapshotSubscriber._reviews: list[str]` — 最多 200 条，背压丢弃最旧。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- **定时复盘调度**：用户可在复盘页定时弹窗直接设置开关与时间，保存到 `preferences.json`，重启后生效（[daily_pipeline.py:1239-1243](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L1239-L1243)）
- **推送渠道**：用户可在设置页配置飞书/企微/自定义 Webhook/邮件 → 复盘页定时弹窗勾选渠道（多选）+ 触发方式（auto/manual）
- **复盘 System Prompt**：修改 [market_recap.py:40-93](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L40-L93) 的 `_SYSTEM_PROMPT` 常量可调整报告模板与风格

### L2 扩展（插槽/路由/注册替换）

- **推送适配器**：`_maybe_push_review` 函数（[daily_pipeline.py:1028-1098](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L1028-L1098)）按渠道名分支，新增渠道时只需在 `PUSH_CHANNELS` 集合（[preferences.py:591](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L591)）添加渠道名 + 在 `_maybe_push_review` 添加分支
- **AI Provider 替换**：`stream_ai_text` 是唯一 LLM 调用入口，替换 AI 模型只需修改 `ai_provider.py` 的实现
- **数据上下文注入**：当前龙虎榜（`dragon_tiger.build_recap_context`）和盘前风向标（`auction_benchmark.build_recap_context`）是可选上下文，可在 `_build_user_prompt` 中追加更多数据源

### L3 修改（直接改源码）

- 修改报告模板结构：调整 `_SYSTEM_PROMPT`（[market_recap.py:40-93](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L40-L93)）的八节 Markdown 模板
- 调整情绪分计算逻辑：修改 [market_overview_builder.py:531-549](file:///c:/Code/tick-stock-panel/backend/app/services/market_overview_builder.py#L531-L549) 的雷达聚合与标签映射
- 修改报告上限：改 [market_recap_reports.py:27](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap_reports.py#L27) 的 `MAX_REPORTS`
- 修改定时重试逻辑：改 [daily_pipeline.py:978](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L978) 的 `max_attempts`

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| React Query | `QK.reviewReports` 在归档后手动 `invalidateQueries` | 历史列表刷新 |
| SSE 流 | `quote_service.push_review_event` 实时推送 | 定时复盘期间前端页面实时更新 |
| 文件存储 | `json_report_store.py` 原子写（替换写） | 归档/删除后立即生效 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| 推送门控测试 | `backend/tests/test_review_push_mode.py` | `test_review_push_mode_defaults_to_manual`（默认 manual）、`test_set_and_get_review_push_mode`（读写）、`test_set_review_push_mode_rejects_invalid_value`（非法值降级 manual）、`test_save_report_manual_requires_explicit_push`（manual 需显式 push=True）、`test_save_report_auto_pushes_without_flag`（auto 自动推）、`test_scheduled_review_manual_archives_without_push`（定时 manual 只归档不推）、`test_scheduled_review_auto_pushes`（定时 auto 归档并推） |
| 关注点指令测试 | `backend/tests/test_ai_analysis_focus.py` | 关注点指令构建与注入 |

## 依赖关系

### 依赖的其他功能

- [市场总览 Overview](file:///c:/Code/tick-stock-panel/.trae/docs/architecture.md)（待确认是否已有独立文档）：`build_market_overview` 提供指数/涨跌/板块/情绪等聚合数据，是复盘数据源（[market_recap.py:295](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L295)）
- 日 K 同步与 Enriched 管道：复盘依赖最新日 K 与 enriched 数据，盘后管道默认 15:35 确保数据就绪，复盘默认 15:40 留缓冲
- AI Provider：`stream_ai_text` 用于流式 LLM 调用（[market_recap.py:331](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L331)）
- 龙虎榜（fuyao 专有）：复盘 prompt 可选嵌入龙虎榜资金动向上下文（[market_recap.py:323](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L323)）
- 盘前风向标（fuyao 专有）：复盘 prompt 可选嵌入竞价筛选名单上下文（[market_recap.py:328](file:///c:/Code/tick-stock-panel/backend/app/services/market_recap.py#L328)）
- 偏好设置（Preferences）：`review_schedule` / `review_push_channels` / `review_push_mode` 的读写（[preferences.py:594-711](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L594-L711)）
- QuotaService SSE：`push_review_event` 广播复盘事件（[quote_service.py:449-456](file:///c:/Code/tick-stock-panel/backend/app/services/quote_service.py#L449-L456)）

### 被依赖的功能

- 无其他功能显式依赖大盘复盘

## 常见问题与注意事项

1. **AI Key 未配置时定时复盘跳过**：`_run_scheduled_review` 入口检查 `secrets_store.get_ai_key()`，无 Key 时直接 return 不报错（[daily_pipeline.py:914](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L914)）
2. **定时复盘默认关闭**：仅当 `review_schedule.enabled == true` 时 `start_scheduler` 才注册 job（[daily_pipeline.py:1239-1243](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L1239-L1243)）
3. **推送门控**：`review_push_mode` 默认 `manual`（只归档不推），需用户在定时弹窗中切换为 `auto` 或手动归档时传 `push: true` 才推送（[market_recap.py:147](file:///c:/Code/tick-stock-panel/backend/app/api/market_recap.py#L147)）
4. **手动流与定时流并发**：reviewStore 通过 `generatingSource` 区分两条流，手动流进行中时 SSE 事件一律忽略，避免冲突（[reviewStore.ts:191](file:///c:/Code/tick-stock-panel/frontend/src/lib/reviewStore.ts#L191)）
5. **LLM 断流重试**：定时复盘最多重试 2 次（共 3 次），重试时推 `retry` 事件清空前端已累积内容（[daily_pipeline.py:968-1025](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py#L968-L1025)）
6. **时间下限**：定时复盘时间强制不低于 15:00（A 股收盘）（[preferences.py:617](file:///c:/Code/tick-stock-panel/backend/app/services/preferences.py#L617)）
7. **龙虎榜/风向标降级**：fuyao 数据源未配置时，龙虎榜显示 `source_unavailable` 降级提示并引导配置；复盘 prompt 中龙虎榜/风向标上下文为空时不影响主流程
8. **情绪分口径**：`emotion_score` 为 0-100 整数，来源为六维雷达均分；前端 `scoreColor` 按阈值染色（70+ 红/55+ 橙/45+ 黄/30+ 绿/<30 绿）（[Review.tsx:50-57](file:///c:/Code/tick-stock-panel/frontend/src/pages/Review.tsx#L50-L57)）