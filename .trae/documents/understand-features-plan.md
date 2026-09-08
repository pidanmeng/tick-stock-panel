# 功能文档化计划

## 目标

对整个 TSP（Tick Stock Panel）项目进行全面的功能理解与文档化，覆盖：
1. 整体架构、启动流程、定时任务、基础设施
2. Layout.tsx 侧边导航栏每个菜单项对应的功能
3. Settings.tsx 每个 Tab 对应的功能

## 产出规范

- 每篇文档严格遵循 `.trae/docs/features/_template.md` 模板结构
- 所有文件引用附带 `路径:行号` 锚点
- 只描述代码中已存在的实现，不虚构 API、流程或数据结构
- 区分"已实现"与"规划中"的能力
- 最终在 `.trae/docs/architecture.md` §0.5 登记所有功能文档

## 调研方法

每篇功能文档通过以下步骤产出：
1. 调用 `feature-documenter` 子 Agent（`Task tool` + `subagent_type: "general_purpose_task"` 或直接使用搜索工具）
2. 子 Agent 读取相关代码文件、追踪调用链
3. 产出文档初稿
4. 确认后写入 `.trae/docs/features/{feature-name}.md`

## 功能列表（共 26 篇文档）

### A 组：整体架构与基础设施（1 篇）

| # | 功能名 | 说明 | 覆盖范围 |
|---|--------|------|----------|
| A1 | 整体架构与基础设施 | 启动流程、数据流、定时任务、缓存分层、能力路由 | main.py, jobs/daily_pipeline.py, repository.py, capabilities.py, backend 全貌 |

### B 组：Layout 导航菜单功能（18 篇 + 3 个附属功能）

| # | 功能名 | 菜单选项 | 前端页面 | 后端核心服务 |
|---|--------|---------|---------|-------------|
| B1 | 看板 Dashboard | 看板 | Dashboard.tsx | overview, market_overview_builder, regime |
| B2 | 自选 Watchlist | 自选 | Watchlist.tsx | watchlist, quote_service |
| B3 | 选股 Screener | 策略 | Screener.tsx | screener, strategy |
| B4 | 因子 Factors | 因子 | Factors.tsx (+ FactorXxx) | factor-system, strategy/engine |
| B5 | 回测 Backtest | 回测 | Backtest.tsx (+ sub-views) | backtest/engine, worker, mining |
| B6 | 个股分析 StockAnalysis | 个股分析 | StockAnalysis.tsx | stock_analysis, stock_analyzer |
| B7 | 连板梯队 LimitUpLadder | 连板梯队 | LimitUpLadder.tsx | limit_signals, price_limits |
| B8 | 概念分析 ConceptAnalysis | 概念分析 | ConceptAnalysis.tsx | concept_rotation_analyzer |
| B9 | 行业分析 IndustryAnalysis | 行业分析 | IndustryAnalysis.tsx | sector_monitor, industry_overview |
| B10 | 财务分析 Financials | 财务分析 | Financials.tsx | financial_sync, financial_analyzer |
| B11 | 监控中心 Monitor | 监控中心 | Monitor.tsx | monitor_rules, alert_store, monitor_service |
| B12 | 市场环境 Regime | 市场环境 | Regime.tsx | regime_builder, market_phase, market_mainline |
| B13 | 异动监控 AbnormalMoves | 异动监控 | AbnormalMoves.tsx | abnormal_moves |
| B14 | 持仓提醒 Lots | 持仓提醒 | Lots.tsx | lots service |
| B15 | 信号库 Signals | 信号库 | Signals.tsx | custom_signals |
| B16 | 复盘 Review | 复盘 | Review.tsx | market_recap, ai_reports |
| B17 | 指数 Indices | 指数 | Indices.tsx | index_const, index_sync |
| B18 | 数据管理 Data | 数据 | Data.tsx | data, pipeline, ext_data |

附属功能（Layout 侧栏组件，不单独成文档，在 B 组文档中分别覆盖）：
- 数据源能力健康卡（DataSourceHealthBadge）
- AI 配置状态条（AIConfigBadge）
- 实时行情开关（Realtime toggle）
- 核心指数行情条（SidebarIndexQuotes）
- 主题切换（ThemeToggle）

### C 组：Settings 设置 Tab 功能（7 篇）

| # | 功能名 | Tab 选项 | 前端面板 | 后端服务 |
|---|--------|---------|---------|---------|
| C1 | 数据源设置 | 数据源 | DataSources.tsx | capabilities, data_providers, custom_sources |
| C2 | AI 设置 | AI 设置 | AI.tsx | ai_provider |
| C3 | 实时监控设置 | 实时监控 | Monitoring.tsx | QuoteService, monitor |
| C4 | 扩展页面设置 | 扩展页面 | ExtPages.tsx | ext_data, ext_presets |
| C5 | 网络设置 | 网络设置 | Timeout.tsx | timeout config |
| C6 | 菜单设置 | 菜单设置 | MenuSettings.tsx | preferences, nav_order |
| C7 | 系统设置 | 系统设置 | System.tsx | system config |

## 执行步骤

### 第 1 阶段：逐篇产出文档

对每篇功能文档，循环执行以下步骤：

1. **调用子 Agent**：使用 `Task tool` 调用 `feature-documenter` 子代理，输入功能名、关键词、相关文件路径
2. **获取初稿**：子 Agent 返回按模板格式的文档 Markdown 全文
3. **确认**：将初稿展示给用户确认
4. **写入文件**：写入 `.trae/docs/features/{feature-name}.md`
5. **更新索引**：在 `architecture.md` §0.5 表格中登记新文档

### 第 2 阶段：更新架构索引

所有文档产出后，更新 `architecture.md` §0.5 表格，添加所有新功能文档的链接。

## 执行顺序

建议按依赖关系分组执行，每组内可并行调研：

1. **A1（架构基础）** → 先产出，所有后续文档依赖
2. **B 组（导航功能）** → 按 B1→B18 顺序，同组可并行调研
3. **C 组（设置功能）** → 按 C1→C7 顺序，同组可并行调研
4. **更新索引** → 最终统一更新

## 验证方式

- 每篇文档写完后，抽查关键文件引用路径是否准确
- 确认 `architecture.md` §0.5 表格登记完整
- 确认所有文档均按 `_template.md` 格式产出