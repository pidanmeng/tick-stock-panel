# TSP 架构梳理 + `.trae` 文档/Agent/Skill/Command 建设计划

## 摘要

本项目（TSP · A股智能量化工作台）目前没有任何 `.trae` 目录。本计划：

1. 基于**真实代码勘察**（两个并行 search 子代理逐文件核对，含 `文件:行号` 证据）产出一份完整、只描述已存在实现的架构文档 `.trae/docs/architecture.md`；
2. 创建常驻注入的精简项目规则 `.trae/rules/project_rules.md`；
3. 重写根 `AGENTS.md`（架构速览 + 文档索引 + 工具目录 + 红线约束）；
4. 在 `.trae/agents/`、`.trae/skills/`、`.trae/commands/` 按用户选定创建 5 个子 Agent、3 个 Skills、1 个 Command。

**硬约束（用户明确要求，贯穿所有产物）**：所有文档/智能体/技能/命令描述与指令必须以本项目**真实存在的架构、文件、流程**为依据；禁止描述或引导新增项目不存在的数据结构、流程与 API；禁止改变 DuckDB 内存视图/Parquet schema/数据契约（与 `CONTRIBUTING.md` §2/§3/§4、`docs/secondary-development.md` 第 1 节"已可用/按需扩展"不可混用、不得虚构 API 的原则一致）。

## 现状分析（勘察结论）

- **仓库**：根目录有 `AGENTS.md`（自动注入入口）、`CONTRIBUTING.md`（贡献/AI/复审规范，模块边界+数据契约+验证矩阵+复审流程）、`docs/`（12 篇领域文档）、`README.md`；**`.trae/` 不存在**。
- **后端** `backend/app/`：FastAPI 应用装配在 `main.py`（lifespan main.py:87 起：DataStore/KlineRepository → 恢复挖掘 → enriched → 缓存预热 → 能力检测 → 插件加载 → QuoteService/MinuteRefresh → 策略引擎 → 扩展接线 → 关闭）。约 26 个 API 路由文件（前缀如 `/api/kline`、`/api/screener`、`/api/backtest`、`/api/monitor-rules` 等）为薄胶水；业务在 `services/`（~50 个）、`strategy/`（26 内置 + engine/monitor）、`backtest/`（worker spawn 隔离 + numba 运行时）、`indicators/`（enriched 窄表 14 列 + 现算 68 列指标）、`tickflow/`（SDK 客户端/能力探测/令牌桶调度/DataStore/KlineRepository）、`data_providers/`（Provider 契约 + `CAPABILITY_REGISTRY` 数据集维度单一权威 + YAML 自定义源 loader）、`plugins/`（fuyao / stocksdk 插件）、`extensions/`+`custom/`（前后端二开注册）。APScheduler 在 `jobs/daily_pipeline.py`（盘前 09:10 / 盘后 15:30 / depth_finalize / reprobe / 定时复盘）。
- **前端** `frontend/src/`：`router.tsx` 全页面 lazy 路由（约 24 主路由 + 扩展路由注入）；`lib/api.ts` 唯一 API 客户端 + NDJSON 流式 generator；`lib/queryKeys.ts` 集中查询键 + SSE invalidate 前缀；`useQuoteStream` 全局 SSE；`components/Layout.tsx` 外壳挂 SSE/扩展导航插槽；真实插槽仅 3 个：`layout.navigation.extra`、`stock-preview.footer`、`watchlist.toolbar`（`extensions/types.ts:6-26` 上下文契约）；扩展注册约定 `src/custom/<ns>/extension.tsx`。
- **验证命令**：后端 `uv run pytest`/`ruff`，前端 `pnpm build`/`lint`，提交前 `git diff --check`（`CONTRIBUTING.md` §9 矩阵；`secondary-development.md` §7 二开矩阵）。
- **`.trae` 官方约定**（docs.trae.cn）：项目级 Subagent = `.trae/agents/{name}.md`（frontmatter：`name/description/model?/tools?/disallowedTools?/mcpServers?` + 系统提示）；项目级 Skill = `.trae/skills/{name}/SKILL.md`（frontmatter `name/description` + 正文）；项目命令 = `.trae/commands/{name}.md`（frontmatter `name/description` + `---` 下为指令，目录最多 3 层）；项目规则 = `.trae/rules/`（全量注入，应精简）。

## 拟变更总览（目标文件树）

```
AGENTS.md                                # 重写：入口/架构速览/文档链/工具目录/红线
.trae/
├── docs/
│   └── architecture.md                  # 完整架构文档（详版，只描述已存在实现）
├── rules/
│   └── project_rules.md                 # 精简常驻规则（每次对话注入）
├── agents/                              # 5 个子 Agent
│   ├── architecture-guide.md
│   ├── code-reviewer.md
│   ├── finance-auditor.md
│   ├── research-analyst.md
│   └── developer.md
├── skills/                              # 3 个技能
│   ├── run-verification/SKILL.md
│   ├── build-strategy/SKILL.md
│   └── investment-research/SKILL.md
└── commands/
    └── new-strategy.md                  # /new-strategy 命令
```

不改任何业务代码、测试、配置、DuckDB/Parquet 结构；仅新增上述文档文件并重写 `AGENTS.md`。

## 变更明细（按文件）

### 1. `.trae/docs/architecture.md`（新建，完整架构文档）

内容大纲（全部基于勘察证据，标注关键 `文件:行号` 索引；只写"已存在"能力）：
- 定位与技术栈表（后端 FastAPI/Pydantic v2/Polars/DuckDB/Parquet/uv；前端 React18/TS/Vite/TanStack/pnpm）。
- 分层与数据流：主写路径（provider → services 同步 → KlineRepository/Parquet → indicators pipeline(enriched 窄表 14 列+现算指标) → 策略/监控/回测/挖掘 → API/SSE → 前端 TanStack Query）；盘中实时路径（quote_service 轮询线程 ~15s、`_enriched_cache` 盘中唯一数据源）；回测 worker spawn 隔离；`MiningProcessLock` 单进程。
- 目录模块地图：后端 `api/ services/ tickflow/ data_providers/ plugins/ indicators/ strategy/ backtest/ jobs/ extensions/ custom/` 与前端 `pages/ components/ lib/ extensions/ custom/` 各职责表（含关键文件 1 行说明）。
- API 域分组 × 前端路由对照表（后端 prefix → services → 前端页面路由/页面文件；SSE 事件与 `queryKeys.ts` 失效前缀）。
- 数据源插件化：Provider Protocol（base.py）、`CAPABILITY_REGISTRY` 数据集（daily/adj_factor/realtime/minute/depth5/financial/full_minute 与档位）、能力矩阵契约（candidates/pending/usable）、YAML 自定义源 loader、非路由直连（龙虎榜/风向标/交易日历）与"不得绕过抽象"红线。
- 存储与缓存分层：Parquet 分区 + DuckDB 内存视图、enriched generation marker 原子发布、repository Polars 热缓存、strategy_cache、screener TTL 缓存、backtest matrix 磁盘缓存、`data/` 运行时目录布局、缓存失效链（写→内存→generation→SSE→前端 invalidate）。
- 数据契约红线：比例/百分比口径、复权价 vs raw 价、交易日/北京时区/分钟 K 归一、历史股本 PIT、资产类型路由（禁止凭代码格式猜类型）。
- 调度与生命周期：lifespan 顺序、APScheduler job 表、定时常量、深度/分时等旁路。
- 扩展系统：前端 3 个真实插槽与路由/导航注册、后端 extensions 注册器 + `NotificationFormatter`、L1/L2/L3 分级与高冲突热点文件清单。
- 验证命令速查（CONTRIBUTING §9）与关键文件索引（main.py 锚点、registry、capabilities、pipeline 等）。

### 2. `.trae/rules/project_rules.md`（新建，精简常驻规则）

保持 <60 行、全量注入仍轻量。内容：
- 文档读取顺序：`AGENTS.md → CONTRIBUTING.md → docs/secondary-development.md → .trae/docs/architecture.md`。
- 唯一事实来源：改动前用代码/测试证实调用链；禁止虚构 API/流程/测试结果；`secondary-development.md` 区分"已可用/按需扩展"，不得把示例当实现。
- **架构护栏（用户硬约束）**：按现有架构实施；不改 DuckDB 内存视图/Parquet schema/API 契约/数据目录布局；不新增项目不存在的流程、模块或扩展点；新能力先确认是否已有 Provider 能力或插槽承载，禁止平行第二套。
- 数据契约红线速记（单位、复权、交易日/时区、资产类型、PIT、fail-closed）。
- 最小改动 + 验证矩阵 + 不提交/不推送（除非确认）。

### 3. `AGENTS.md`（重写，保持"AI 开发入口"定位与简洁）

- 保留开头的必读指引，新增文档链并链接 `.trae/docs/architecture.md` 与 `.trae/rules/project_rules.md`。
- 新增"项目架构速览"（约 10 行：单容器 FastAPI+Polars+Parquet/DuckDB 后端、React 前端；一句话数据流；模块地图链接）。
- 新增红线与规则（沿用现有 4 条 + 上述架构护栏）与验证命令速查。
- 新增"`.trae` 智能体 / 技能 / 命令目录"表（每项 1 行 + 指向文件）。
- 注意：`AGENTS.md` 会被自动注入，保持精简，避免重复 CONTRIBUTING 长文。

### 4~8. `.trae/agents/*.md`（5 个子 Agent，frontmatter + 中文系统提示）

frontmatter 统一规范：`name` 仅 ASCII 字母开头/字母数字连字符、≤50；`description` 具体到触发场景（利于主 Agent 调度）；不设 `model`（跟随当前选择）；不引用 MCP Server（避免依赖环境插件名）。正文明确角色、工作流、输出格式、行为边界（只读/读写），全部以仓库真实文档与文件为据。

| 文件 | name | tools | 定位与要点 |
|---|---|---|---|
| `architecture-guide.md` | architecture-guide | Read, Glob, Grep | 架构导航员（只读）。回答模块边界/数据流/调用链/入口问题；先查 `.trae/docs/architecture.md` 再核实源码；输出带 `路径:行号` 引用；不确定明说，禁止虚构。 |
| `code-reviewer.md` | code-reviewer | Read, Glob, Grep | 代码复审员（只读）。严格按 `CONTRIBUTING.md` §10/§11 复审流程（边界/契约/插件化/状态链路/兼容/并发/失败路径/测试质量/最终 diff）与 §11.2 输出格式（结论+阻断[P0-P3]+非阻断+已验证+剩余风险）；结论必须给"可合并/修改后合并/不建议合并"。 |
| `finance-auditor.md` | finance-auditor | Read, Glob, Grep | 金融口径审计员（只读）。按 `CONTRIBUTING.md` §3/§5/§6 清单核查：比例与百分比口径、复权 vs 原始价、交易日 vs 自然日、北京时区、资产类型路由、历史股本 PIT、缓存/失效/SSE 链路、未来函数与 fail-closed；输出问题表（文件:行号/触发条件/实际影响/建议）。 |
| `research-analyst.md` | research-analyst | Read, Glob, Grep, WebSearch, WebFetch, Skill | 投研分析员（只读）。结合项目研究域（复盘/财务/AI 分析等真实能力与 docs）与公开资料做结构化分析；结论先行；区分"本项目数据结论（需人工用平台复核）"与"外部资料结论"；标注来源与置信度；研究报告按用户偏好的星级（★）输出；附"不构成投资建议"免责；不写文件不改仓库。 |
| `developer.md` | developer | Read, Glob, Grep, Edit, Write, LSP, Bash, Skill, TodoWrite, WebSearch, WebFetch | 程序开发工程师（可读写）。先读文档链与 `git status` 保留现有修改；将需求归类 L1/L2/L3 并说明依据；复用现有接口/服务/类型/组件/缓存；改动最小、先补能证明行为的测试再实现；按验证矩阵实际执行并如实汇报；**禁止虚构 API、改变数据契约/数据结构或新增不存在流程**；不提交不推送（除非明确要求）。 |

每个文件含"被调用后第一步：读取/确认…"与"输出格式"两节，确保调度确定性。

### 9~11. `.trae/skills/*/SKILL.md`（3 个技能）

frontmatter `name` + `description`（描述触发场景，供自动调度）。正文含：描述 / 使用场景 / 指令 / 示例(如需)。

- `run-verification/SKILL.md`：按 `CONTRIBUTING.md` §9 矩阵识别改动范围（后端纯函数/API/数据源/指标/策略/回测/缓存/前端/前后端联调），只跑受影响测试；给出真实命令形态（`cd backend; uv run pytest tests/路径/test_x.py -q`、`uv run ruff check ...`、`cd frontend; pnpm build`、`git diff --check`）；要求记录实际输出，禁止虚构结果；对依赖实时数据源/外部网络/付费档位的测试明确标注可跳过原因。
- `build-strategy/SKILL.md`：新建/修改自定义策略与信号（L1）。指令：先读 `docs/strategy.md`、`backend/app/strategy/prompts/strategy-guide*.md` 与 `CONTRIBUTING.md` §5.1；确认策略落盘目录与 engine 加载机制（以实际代码/文档为准，不假设）；以真实内置策略/模板为参考实现参数/评分/过滤契约；列出需要同步的缓存/监控/前端查询；按矩阵补测试并验证；完成后输出清单。禁止发明 docs 中不存在的能力。
- `investment-research/SKILL.md`：投研工作流（复盘/板块/个股/财报解读 SOP）。映射本项目真实能力（市场环境 regime/mainline、异动、财务、AI 复盘等页面与 docs）与输出规范（结论先行、口径与来源、星级评价、置信度、免责）；优先一手来源（官方公告/财报/交易所/项目数据结果），二级来源需标注；不虚构数据，不给出买卖建议。

### 12. `.trae/commands/new-strategy.md`

frontmatter `name: new-strategy`、`description`；正文为触发后指令：确认策略类型与级别（L1）→ 按 build-strategy 技能规范（若技能可用则调用，否则按其流程）引导用户输入策略逻辑/参数 → 依据真实策略体系落盘与接线 → 按验证矩阵执行并汇报；明确"创建属于用户数据文件，先展示方案并确认后再写入"。

## 假设与决策

- `.trae` 目录将纳入 Git 版本管理（与仓库共存，供所有协作者使用）。
- 子 Agent 均不绑定 `model`、不绑定 MCP Server 名（避免跨设备/环境失效）；如执行期需要投研数据，由主 Agent 或用户在会话内提供已启用的数据技能/MCP。
- `AGENTS.md` 保持精简（架构详版放 `.trae/docs/architecture.md`），避免自动注入内容膨胀。
- 不新增任何业务代码、测试或 `.env` 改动；产物全部为文档 + 配置类 Markdown。
- "程序员"子 Agent 命名为 `developer`（唯一、无内建同名冲突），可在后续改名。
- 所有产物正文用中文（frontmatter `name` 用 ASCII）。

## 验证步骤

1. 文件齐全性：按上述树形逐个确认文件存在且非空。
2. frontmatter 合法性：逐个检查 YAML 以 `---` 起止、无 BOM；`name` 满足"字母开头/字母数字连字符/≤50"；`description` 存在且具体。
3. 引用真实性抽查：抽取 architecture.md 中 5~8 个关键锚点（如 main.py lifespan 行、`CAPABILITY_REGISTRY`、3 个前端插槽名、后端 router 前缀、验证命令），用 Grep/Read 复核文档所述与代码一致；文档只描述已存在实现。
4. 交叉链接有效性：文档中链接的仓库文件与 `.trae` 内部文件路径均存在。
5. `AGENTS.md` 重读：确认仍为"入口级"文档、无与 CONTRIBUTING 重复的长文、4 条规则与新增护栏齐全。
6. 无代码回归：本变更不含业务代码，运行 `git status` 确认未误改其他文件；执行 `git diff --check` 无空白错误。
