# AI 开发入口

修改、调试或审查本仓库前，请按以下文档链阅读并遵循：

1. [`.trae/rules/project_rules.md`](.trae/rules/project_rules.md)（常驻精简规则，已自动注入）
2. [`CONTRIBUTING.md`](CONTRIBUTING.md)（项目架构、数据契约、数据源插件化、缓存与性能要求、测试矩阵、PR 复审与合并标准）
3. [`docs/secondary-development.md`](docs/secondary-development.md)（代码二次开发、前端插槽、后端可替换策略、扩展注册与上游升级兼容；区分已实现能力与目标契约，不得虚构尚不存在的 API）
4. [`.trae/docs/architecture.md`](.trae/docs/architecture.md)（完整架构地图，只描述已存在实现并标注代码锚点）

## 项目架构速览

自托管单容器 A 股量化工作台（选股 + 监控 + 回测 + AI 研究）：

- 后端：FastAPI + Polars + Parquet/DuckDB（内存视图），业务在 `backend/app/services/`、策略在 `strategy/`、回测在 `backtest/`（worker 隔离）。应用装配在 `backend/app/main.py`（lifespan main.py:376）。
- 前端：React 18 + TS + Vite + TanStack Query，路由在 `frontend/src/router.tsx`，唯一 API 客户端 `frontend/src/lib/api.ts`，SSE 经 `useQuoteStream` 按 `queryKeys.ts` 前缀精确失效。
- 数据：数据源（TickFlow/fuyao/stock-sdk/YAML 自定义源）→ 同步服务 → `KlineRepository`(Parquet) → `indicators.pipeline`（enriched 窄表 14 列存储、68 列指标现算）→ 选股/策略/监控/回测/挖掘 → API/SSE → 前端。
- 能力路由：`backend/app/data_providers/capabilities.py` 的 `CAPABILITY_REGISTRY` 是数据集维度单一权威，上层只能经 `get_provider()`/偏好能力路由访问数据。
- 定时：APScheduler 盘前 09:10 维表、盘后 15:30 管道、depth_finalize 15:02（偏好可调），节假日按交易日探针自动停轮询。
- 二次开发：L1 配置/策略文件 / L2 前端插槽（已开放 3 个：`layout.navigation.extra`、`stock-preview.footer`、`watchlist.toolbar`）与后端 `NotificationFormatter` / L3 直接改源码；详见 `docs/secondary-development.md`。

## 红线（所有改动必须遵守）

- 严格按现有架构实施：不改 DuckDB 内存视图结构、Parquet schema、enriched 窄表列、API 契约与 `data/` 目录布局；不新增项目不存在的数据结构、模块、流程或扩展点。
- 禁止虚构 API / 流程 / 测试结果 / 性能数据；"已可用"与"按需扩展"不可混用，示例不是实现。
- 金融口径红线：复权价 vs 原始价、小数制/百分制、交易日与北京时间、股票/ETF/指数资产路由、财务公告日 PIT；改数据契约与缓存读写时列出受影响缓存层（文件→内存→generation→SSE→前端）。
- provider 缺能力/字段缺失/空数据时明确提示或 fail-closed，禁止静默返回看似合理的错误结果。

## 验证命令速查

```bash
cd backend
uv run pytest tests/path/to/test_x.py -q     # 按 CONTRIBUTING §9 矩阵选择
uv run ruff check app/path.py tests/path.py

cd frontend
pnpm build                                    # 前端改动必须通过

cd ..
git diff --check                              # 提交前必须执行
```

## 工作规则

- 先理解调用链和现有测试，再进行修改。
- 保持实现简单、改动范围最小，不处理无关问题。
- 不覆盖工作区已有修改，不虚构测试或审查结果。
- 以实际验证结果作为完成标准。

## `.trae` 智能体 / 技能 / 命令

主 Agent 会根据任务匹配下列能力，也可直接点名调用：

| 类型 | 名称 | 用途 |
| --- | --- | --- |
| Subagent | [architecture-guide](.trae/agents/architecture-guide.md) | 架构导航（只读）：模块边界/数据流/调用链/入口定位，输出带 `路径:行号` |
| Subagent | [code-reviewer](.trae/agents/code-reviewer.md) | 代码复审（只读）：按 CONTRIBUTING 复审清单与 P0-P3 级别出结论 |
| Subagent | [finance-auditor](.trae/agents/finance-auditor.md) | 金融口径审计（只读）：复权/单位/交易日/时区/资产路由/缓存链路核查 |
| Subagent | [research-analyst](.trae/agents/research-analyst.md) | 投研分析（只读）：结合项目研究能力与公开资料做结构化分析，标注来源与置信度 |
| Subagent | [developer](.trae/agents/developer.md) | 程序开发（可读写）：按 L1/L2/L3 分类、最小改动实现并如实验证 |
| Skill | [run-verification](.trae/skills/run-verification/SKILL.md) | 按验证矩阵执行受影响测试/构建/静态检查并汇报实际结果 |
| Skill | [build-strategy](.trae/skills/build-strategy/SKILL.md) | 自定义策略/信号开发引导（L1），含口径检查与测试要求 |
| Skill | [investment-research](.trae/skills/investment-research/SKILL.md) | 投研复盘工作流 SOP（复盘/板块/个股/财报解读与输出规范） |
| Command | [/new-strategy](.trae/commands/new-strategy.md) | 引导创建自定义策略 |
