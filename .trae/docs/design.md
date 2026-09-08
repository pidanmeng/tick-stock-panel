# TSP 前端设计风格指南（design.md）

> 本文档只描述仓库中已存在的前端设计与实现（关键结论均可复核），**不描述"规划中/设计示例"内容**。新增或修改前端界面时必须遵循本文档，以保持整体视觉一致。代码证据见各节标注。

## 1. 设计语言概览

TSP 前端采用**暗色优先**的专业交易终端风格，以等宽数字、红涨绿跌语义色、克制的层级区分为核心特征：

- 暗色为默认主题，亮色可切换（[index.css](../../frontend/src/index.css) §6.0）。
- 强调色为**电光蓝**（`#3B82F6`），仅用于交互与数据高亮；**不用于价格**。
- A 股语义色**红涨绿跌**（`bull`/`bear`），**仅用于价格/K线相关元素，不用于 UI 状态**（如成功/失败）。
- 价格与数字一律**等宽字体 + tabular-nums**，保证列对齐。
- 暗色模式用**边框区分层次**，不使用阴影；亮色模式同理。
- 品牌色（紫色 `#8B5CF6`）仅用于 Logo/brand 区域，不影响功能语义色（[Layout.tsx](../../frontend/src/components/Layout.tsx) 中的 `BRAND` 常量）。

## 2. 设计令牌（Design Tokens）

设计令牌定义在 [index.css](../../frontend/src/index.css)（CSS variables，HSL 形式兼容 Tailwind alpha 语法）与 [tailwind.config.ts](../../frontend/tailwind.config.ts)（映射为 Tailwind 色板）。

### 2.1 色板

| Token | 暗色值 | 亮色值 | 用途 |
| --- | --- | --- | --- |
| `--base` | `#0A0A0B` | `#FAFAFA` | 页面背景 |
| `--surface` | `#18181B` | `#FFFFFF` | 卡片/面板背景 |
| `--elevated` | `#212126` | `#F4F4F5` | hover 背景/次级面板 |
| `--border` | `#353539` | `#E4E4E7` | 边框/分隔线 |
| `--fg-primary` | `#FAFAFA` | `#18181B` | 主文字 |
| `--fg-secondary` | `#C4C4CB` | `#52525B` | 次级文字（子标题/导航非激活） |
| `--fg-muted` | `#8E8E96` | `#A1A1AA` | 辅助提示文字 |
| `--accent` | `#3B82F6` | `#3B82F6` | 强调色（交互/高亮） |
| `--bull` | `#F04438` | `#F04438` | 红涨（价格/涨跌） |
| `--bear` | `#12B76A` | `#12B76A` | 绿跌（价格/涨跌） |
| `--warning` | `#F79009` | `#F79009` | 琥珀警告 |
| `--danger` | `#F04438` | `#F04438` | 危险/错误 |

对应的 Tailwind 类：`bg-base` `bg-surface` `bg-elevated` `border-border` `text-foreground` `text-secondary` `text-muted` `text-accent` `text-bull` `text-bear` `text-warning` `text-danger`。支持 alpha：`bg-surface/80`、`border-border/60` 等。

### 2.2 字体

| 用途 | 字体栈 |
| --- | --- |
| 正文 | `Inter` → `HarmonyOS Sans SC` → `PingFang SC` → `system-ui` → `sans-serif` |
| 数字/代码 | `JetBrains Mono` → `IBM Plex Mono` → `ui-monospace` → `monospace` |

**规则**：价格、涨跌幅、成交量、指标数值等一律用 `font-mono` 类；数字对齐用 `tabular-nums` 类（或全局 `.tabular`/`.num` 工具类，见 [index.css](../../frontend/src/index.css)）。

### 2.3 圆角

| Token | 值 | 适用 |
| --- | --- | --- |
| `rounded-card` | `8px` | 卡片 |
| `rounded-btn` | `6px` | 按钮 |
| `rounded-input` | `4px` | 输入框 |
| `rounded-dialog` | `12px` | 弹窗面板 |

### 2.4 动效

- 过渡：`transition-colors duration-150 ease-smooth` 是按钮/链接 hover 的标配。
- 缓动：`ease-smooth` = `cubic-bezier(0.16, 1, 0.3, 1)`（Linear/Vercel 同款）。
- 动画库：`framer-motion`（复杂动画）与 `tailwindcss-animate`（简单进出场，如 toast 的 `animate-in slide-in-from-bottom-2 fade-in`）。

### 2.5 全局滚动条

细滚动条（8px），暗色 thumb 用 border 色，hover 时变 accent 色（[index.css](../../frontend/src/index.css) 全局样式）。

## 3. 主题系统

- 状态存 `localStorage('tf-theme')`，默认 `dark`；生效方式为 `html.dark` class + CSS variables（[theme.ts](../../frontend/src/lib/theme.ts)）。
- `index.html` 预渲染内联脚本在首屏前设好 class，避免闪烁（FOUC）。
- **UI token 自动跟随主题；图表画布不吃 CSS 变量**，统一走 `useChartTheme()` 取调色板（见 §6）。

## 4. 数据格式化约定

统一使用 [format.ts](../../frontend/src/lib/format.ts) 中的格式化函数，**不自行拼字符串**：

| 函数 | 输出示例 | 说明 |
| --- | --- | --- |
| `fmtPrice(v)` | `12.34` | 价格，缺值 `—` |
| `fmtPct(v)` | `+3.25%` | 涨跌幅（输入为小数制，内部 `*100`） |
| `fmtVolume(v)` | `1.23亿` | 成交量（亿/万自动） |
| `fmtBigNum(v)` | `1.23万亿` | 大数（万亿/亿/万自动） |
| `fmtDate(s)` | `2026-09-08` | 日期 |

价格颜色语义：`priceColorClass(v)` 返回 `text-bull`（涨）/`text-bear`（跌）/`text-muted`（0 或缺失）。**禁止**直接用 `v > 0 ? 'red' : 'green'` 之类的硬编码。

## 5. 组件库约定

### 5.1 布局组件

- [PageHeader](../../frontend/src/components/PageHeader.tsx)：页面顶部标题栏。结构：`px-5 pt-3 pb-2 border-b border-border` + 左侧 `title`（`text-lg font-semibold tracking-tight`）+ `titleExtra`（状态徽标）+ `subtitle`（`text-xs text-muted`）+ 右侧 `right` 操作区。
- [EmptyState](../../frontend/src/components/EmptyState.tsx)：空状态。**图示 + 引导**（lucide 图标 + 标题 + 提示），而非一句"暂无数据"。
- [Modal](../../frontend/src/components/Modal.tsx)：共享模态框原语，已内置完整可访问性：焦点陷阱、ESC 关闭、焦点还原、遮罩点击关闭（防拖选误关）。新弹窗优先复用 `Modal` + `useDialogBackdrop`，**不要自建弹窗**。

### 5.2 反馈组件

- [Toast](../../frontend/src/components/Toast.tsx)：全局轻提示，`toast(msg, kind)` 调用，kind 为 `error`（红）或 `success`（绿），4 秒自动消失。容器已挂在 Layout 顶层。
- [AlertToast](../../frontend/src/components/AlertToast.tsx)：监控告警弹出。
- 按钮 hover 标准：`transition-colors duration-150 ease-smooth hover:bg-elevated hover:text-foreground`。

### 5.3 个股面板

- [StockPanel](../../frontend/src/components/StockPanel.tsx)：个股图表面板（信息条 + 日K + 分时），被 StockPreviewDialog 与 TradeKlineModal 复用。新增个股相关交互时优先复用 StockPanel/StockInfoBar。
- [StockInfoBar](../../frontend/src/components/StockInfoBar.tsx)：信息条。注意其中 `BULL = '#C74040'` / `BEAR = '#2D9B65'` 是**局部定义的价格色**（画布内部使用），普通文本价格仍用 `text-bull`/`text-bear` token。

### 5.4 图标

统一使用 `lucide-react`。尺寸惯例：导航/侧栏图标 `h-3.5 w-3.5` 或 `h-4 w-4`，空状态大图标 `h-10 w-10`。品牌 Logo 见 [Logo.tsx](../../frontend/src/components/Logo.tsx)（方括号包裹 K 线的原创 SVG，用 `currentColor` 继承父级颜色）。

## 6. 图表系统

- 图表库：ECharts（复杂图表）+ lightweight-charts（蜡烛图）。
- **主题联动**：图表画布不吃 CSS 变量，所有图表组件通过 `useChartTheme()` 获取当前主题调色板（[theme.ts](../../frontend/src/lib/theme.ts) 的 `ChartTheme`），主题切换时依赖 `useTheme` 重建或 `applyOptions` 刷新。**新增图表必须走 `useChartTheme`，禁止硬编码画布颜色**（序列色如 bull/bear/accent 除外，双主题一致）。
- 语义色序列（双主题通用）：`bull: #F04438`、`bear: #12B76A`，成交量半透明版本 `rgba(240,68,56,0.4)` / `rgba(18,183,106,0.4)`（[CandlestickChart.tsx](../../frontend/src/components/CandlestickChart.tsx)）。

## 7. 页面与布局结构

- 路由：所有页面定义在 [router.tsx](../../frontend/src/router.tsx)（lazy 加载）。
- 外壳：`Layout.tsx` 左侧导航 + 内容区；导航项 = lucide 图标 + 中文短标签；激活态高亮。底部有核心指数迷你报价、数据源能力健康卡。
- 页面结构惯例：`PageHeader`（标题栏）→ 内容区（卡片/表格/图表）。
- 表格：`StockDataTable` 虚拟滚动表格（`components/stock-table/`）；列自定义通过 `ColumnCustomizer`/`ListColumnCustomizer`。

## 8. 状态与数据层约定

- 唯一 API 客户端：[lib/api.ts](../../frontend/src/lib/api.ts)（`request()` 封装 + NDJSON 流式 generator）。
- 查询键：集中管理在 [lib/queryKeys.ts](../../frontend/src/lib/queryKeys.ts)（`QK` 工厂 + SSE 失效前缀）。
- 数据获取：TanStack Query（`useQuery`/`useMutation`），共享 hook 在 `useSharedQueries.ts`/`useSharedMutations.ts`。
- 全局 SSE：`useQuoteStream` 驱动前端按 `SSE_INVALIDATE_PREFIXES` 前缀精确失效。
- 样式类合并：统一用 `cn()`（[lib/cn.ts](../../frontend/src/lib/cn.ts)，clsx + tailwind-merge）。
- 新建页面/组件必须复用上述基建，**禁止自建第二套请求/查询/样式工具**。

## 9. 新增/修改界面时的检查清单

1. **色值**：只用 Tailwind 语义色类（`text-secondary`/`bg-surface` 等），不写死 hex（品牌色与局部价格色除外）。
2. **数字**：价格/涨跌/成交量用 `font-mono` + `tabular-nums`，格式化用 `fmt*` 函数。
3. **语义色**：bull/bear 只用于价格涨跌；UI 状态用 accent/warning/danger。
4. **主题**：画布类颜色走 `useChartTheme()`；纯 DOM 用 CSS variable token 自动跟随。
5. **弹窗**：复用 `Modal` 原语，不手写遮罩/焦点逻辑。
6. **空/加载态**：用 `EmptyState`（图示 + 引导）；加载态预留高度避免布局抖动。
7. **数据层**：走 `api.ts` + `QK` + TanStack Query + `cn()`，不新建平行工具。
8. **扩展接入**：新功能若属于二次开发，遵循 [secondary-development.md](../../docs/secondary-development.md) 的插槽/注册规范（已开放 3 个前端插槽），UI 风格保持一致。

## 10. 相关文件索引

| 主题 | 位置 |
| --- | --- |
| CSS variables / 全局样式 | [index.css](../../frontend/src/index.css) |
| Tailwind 配置（色板/字体/圆角/缓动） | [tailwind.config.ts](../../frontend/tailwind.config.ts) |
| 主题管理与图表调色板 | [lib/theme.ts](../../frontend/src/lib/theme.ts) |
| 数字/价格格式化 | [lib/format.ts](../../frontend/src/lib/format.ts) |
| 样式合并工具 | [lib/cn.ts](../../frontend/src/lib/cn.ts) |
| 共享组件 | [components/](../../frontend/src/components/)（Modal / Toast / PageHeader / EmptyState / StockPanel / StockInfoBar） |
| 应用外壳与导航 | [components/Layout.tsx](../../frontend/src/components/Layout.tsx) |
| 图表组件 | [components/EChartsCandlestick.tsx](../../frontend/src/components/EChartsCandlestick.tsx)、[CandlestickChart.tsx](../../frontend/src/components/CandlestickChart.tsx)、[StockIntradayChart.tsx](../../frontend/src/components/StockIntradayChart.tsx) |
| API 客户端 / 查询键 | [lib/api.ts](../../frontend/src/lib/api.ts) / [lib/queryKeys.ts](../../frontend/src/lib/queryKeys.ts) |
| 前端扩展契约 | [extensions/types.ts](../../frontend/src/extensions/types.ts) |

> 维护约定：本文档随前端设计演变同步更新；引用行号仅作锚点，以代码现状为准。
