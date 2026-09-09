# 同花顺「智能诊股」页面 — 实施计划（MVP）

> 需求来源：`/new-extension` + `.trae/skills/10jqka-stock-diagnose/`（9 个私有接口已抓包文档化，实测日期 2026-09-09）。
> 分级结论：**L2 扩展（后端 `app/custom` 扩展路由 + 前端 `src/custom` 扩展路由页面 + 复用 ext-data 存储）**，仅在前端 `lib/api.ts`/`lib/queryKeys.ts` 做纯增量函数（L3 热点但只加不改）。零核心接线改动（扩展自动发现，不触碰 main.py / router.tsx / Layout.tsx）。

## 0. 摘要

在 TSP 内新增一个「智能诊股」页面（左侧导航 `/diagnose`），MVP 范围：

- **标的集合**：用户选中的集合（自选分组 / 手动录入 / 上次快照），由用户点「更新诊股快照」按钮**手动**批量拉取；数据以**扩展数据快照表**形式落盘（`data/ext_data/ths_diagnose/`，复用 ext-data 机制），页面表格/聚类/筛选只读本地快照。
- **刷新时机**：**仅手动**。诊股评分为**长线价值指标**：财务分按财报披露周期更新（非每日/盘中），fund/tech/valuation/message 虽每日更新但属日频、盘中刷无意义；手动拉取也避免频繁暴露私有接口。**MVP 不做任何自动定时**，盘后定时列为后续可选（§8）。
- **表格能力**：按**同花顺行业**（接口自带 `industry_name/industry_code/industry_rank`，无需额外数据）分类聚类；六维评分列可排序、可 min/max 区间筛选；提供趋势快筛（资金较昨日转强 / 财务同比改善 / 综合分区间）。
- **详情弹窗**：点击行弹出「智能诊股详情」全屏浮层（仿 StockPreviewDialog 的 framer-motion 浮层范式），实时拉取单只完整诊股数据（六维雷达 + 财务六能力+亮点风险+历史 + 资金要点+历史 + 估值分位 + 公告研报），并接入现有个股 K 线弹窗底部 `stock-preview.footer` 插槽显示评分摘要入口。
- **趋势筛选（需求 d）**：MVP 用「轻量趋势列」——每只拉取时附带 `资金较昨日变化(fund_score_minus)`、`财务同比(finance vs 上年同期 last_score)`、`综合变化(delta_score)`；真实序列（资金近 1 月、财务各报告期、估值分位）在详情弹窗展示，跨日自动趋势筛选列为扩展路线图。

数据红线全部遵守：不改 DuckDB 视图结构/Parquet schema/enriched 窄表/API 契约/data 目录布局；不新建第二套存储；外部请求带限流与失败隔离，fail-closed。

## 1. 现状分析（已核实的锚点）

| 领域 | 现状 | 锚点 |
| --- | --- | --- |
| 诊股接口 | 9 接口、双信封（总评/财务/估值 `status_code==0`，资金/消息 `==200`）、覆盖仅沪深 A 股、market=17/33 | `.trae/skills/10jqka-stock-diagnose/SKILL.md`、`references/api.md` |
| 扩展数据 | `data/ext_data/{id}/config.json` + `part.parquet`(snapshot) / `timeseries/date=…`；ExtConfig/ExtConfigStore/rows_to_parquet；行查询 API `/api/ext-data/{id}/rows`（读 parquet，不依赖视图） | [ext_data.py](../../../backend/app/services/ext_data.py) L150-318、L591-649、L734-749；[api/ext_data.py](../../../backend/app/api/ext_data.py) L416-458 |
| 出站 HTTP 范式 | 无鉴权外部接口注意限流；现有扩展出站默认 UA 标识头；fuyao 客户端为 httpx 参考 | [ext_pull.py](../../../backend/app/services/ext_pull.py) L26-43；[plugins/fuyao/client.py](../../../backend/app/plugins/fuyao/client.py) L33-65 |
| 后端扩展 | `app/custom/<module>`（子包可）自动发现；`EXTENSION_ID`/`setup(registrar)`；`include_router` 注册路由并做路径冲突校验 | [extensions/loader.py](../../../backend/app/extensions/loader.py) L24-64；[registry.py](../../../backend/app/extensions/registry.py) |
| 前端扩展 | `src/custom/<ns>/extension.tsx` 懒加载；注册路由+导航；3 个插槽 | [bootstrap.ts](../../../frontend/src/extensions/bootstrap.ts) L4-9；[types.ts](../../../frontend/src/extensions/types.ts) L6-58 |
| 弹窗/表格/图表 | StockPreviewDialog 浮层范式、`stock-preview.footer` 挂载点、StockDataTable/useTableSort、ScreenerFilter 区间过滤范式、ExtDimensionAnalysis 左分组+右明细双栏、EmotionRadar(SVG) 雷达范式、useECharts | [StockPreviewDialog.tsx](../../../frontend/src/components/StockPreviewDialog.tsx) L299-322/L640-646；[StockDataTable.tsx](../../../frontend/src/components/stock-table/StockDataTable.tsx) L17-43；[useTableSort.ts](../../../frontend/src/components/stock-table/useTableSort.ts) L15-50；[ExtDimensionAnalysis.tsx](../../../frontend/src/components/ExtDimensionAnalysis.tsx) L217-236/L329-429；[Dashboard.tsx](../../../frontend/src/pages/Dashboard.tsx) L305-369；[useECharts.ts](../../../frontend/src/pages/backtest/charts/useECharts.ts) L12-43 |

## 2. 总体架构与数据流

```text
前端 /diagnose（src/custom/diagnose，L2 扩展页）
  │ ①选标的集合 → ②POST /api/custom/ths-diagnose/snapshot/pull（发起后台拉取）
  │ ③轮询 /snapshot/progress → ④完成后 GET /snapshot 读快照
后端 app/custom/ths_diagnose/（L2 扩展，路由 /api/custom/ths-diagnose/*，受认证中间件保护）
  ├─ client.py    10jqka HTTP（eq/dq.10jqka.com.cn，无鉴权、UA 标识、信号量+最小间隔+单次重试）
  ├─ parsers.py   逐接口字段规范化（str 分数→float、双信封判据、缺值→null）
  ├─ service.py   快照存取（复用 ext_data）、拉取进度状态、prefs（记忆上次标的集合）
  └─ api.py       5 组详情端点 + 快照端点 + prefs 端点
刷新方式 = 页面「更新诊股快照」手动按钮（无自动定时任务）
存储 data/ext_data/ths_diagnose/（config.json + part.parquet，snapshot 模式）→ 复用 /api/ext-data 行查询与「扩展页面」装配
详情弹窗：每次打开实时拉 5 组端点（限流共享），不落盘
```

## 3. 需求映射

| 需求 | 实现 |
| --- | --- |
| 1. 数据经扩展/插件机制引入 | 快照以 ext-data snapshot 表落盘（`ths_diagnose`），在「数据管理/扩展数据」可见；前端页面同样走扩展注册（路由/导航），不复制核心页面 |
| 2a 分类聚类 | 表格提供「平铺 / 按行业分组」两种模式；分组模式复用 ExtDimensionAnalysis 的「左行业榜（count/平均综合分）+ 右该行业明细」双栏布局；行业来自快照 `industry_name` |
| 2b 排名筛选 | 列头排序（`useTableSort` 三态）；每数值列 min/max 区间输入（参照 ScreenerFilter 交互）；综合快筛 chips（如 综合≥X 且 估值<Y） |
| 2c 弹窗详情 | 行点击开 DiagnoseDetailDialog（framer-motion 全屏浮层 + ESC/点遮罩关闭），实时拉单只完整数据 |
| 2d 前值走势筛选 | 快照内置趋势列（资金较昨日、财务同比、综合变化）→ 本地方列过滤；真实序列（资金近 1 月/财务各期/估值分位）放详情弹窗图表；跨日自动趋势筛选列扩展路线（§8） |
| 3. 扩展思考 | 见 §8 |

## 4. 后端改动（全部新增，无核心文件修改）

### 4.1 文件清单（`backend/app/custom/ths_diagnose/` 子包）

| 文件 | 职责 |
| --- | --- |
| `__init__.py` | `EXTENSION_ID="ths.diagnose"`、`EXTENSION_API_VERSION=BACKEND_EXTENSION_API_VERSION`、`setup()` 调 `api.setup(registrar)`。**不实现 `startup` 钩子**（无自动定时任务，config 由首次拉取懒创建） |
| `client.py` | `ThsDiagnoseClient`：模块级单例（惰性创建、异步线程安全）；方法对应 9 接口（get_score/finance_ablility/finance_analysis/fund_summary/fund_comprehensive/fund_history/message_analyze/valuation_industry/finance_ablility_history）。统一 `_request_json(host_group, path, params)`，按接口组判定成功码；共享信号量（默认并发 3）+ 最小请求间隔（默认 0.25s）+ 失败单次退避重试（5xx/超时），**不做无脑放大重试** |
| `parsers.py` | `flatten_summary(get_score)`、`finance_section/…`、`to_snapshot_row(symbol, code, get_score, ablility, fund_comp)`：产出快照行字典（字段见 4.3）；str 分数统一 `float_or_none`；缺字段→None 不臆造 |
| `service.py` | ExtConfig 确保（`ExtConfigStore` upsert，幂等，首次拉取时懒创建）；`pull_snapshot(symbols, include_trend=True)` asyncio 后台任务+进度状态（module dict：running/total/done/ok/failed/failed_symbols/started_at/finished_at）；写盘走 `rows_to_parquet(df, config, data_dir)`（snapshot 模式内部按 symbol 去重 keep-last，天然支持分批/多 universe 累积）；`read_snapshot()`；`prefs_load/save`（记忆上次标的集合供一键重拉）。**无自动调度**——长线价值口径，财务分按财报披露周期更新、盘中不刷，刷新只由手动按钮触发 |
| `api.py` | `APIRouter(prefix="/api/custom/ths-diagnose")`，端点见 4.4 |

### 4.2 标的 → 资产过滤与 market 推导

- 输入允许 `000001.SZ`/`600519.SH` 等。先经 `data/instruments/instruments.parquet` 维表过滤（以仓库实际 schema 为准，读取其资产类型列确定"仅 A 股股票"），拒绝 ETF/指数/北交所并**报告跳过原因**；无法判定时 fail-closed（明确提示，不静默猜测）。
- market 推导：`symbol` 后缀 `.SH` → 17、`.SZ` → 33（沪深 A 股内 688 亦为 17，与 skill 实测一致）。

### 4.3 快照表 schema（ExtConfig fields，dtype 标注）

| 字段 | dtype | 说明 |
| --- | --- | --- |
| symbol / code / name | string | name 优先 get_score `stock_name`，缺失用维表 join 补 |
| snapshot_date | string | `YYYY-MM-DD`（get_score `date`） |
| industry_name / industry_code | string | 同花顺行业 |
| rank_industry / rank_market | int | 行业/市场排名 |
| total_industry / total_market | int | 行业/市场总数 |
| score_fund / score_tech / score_valuation / score_message / score_finance | float | 六维（满分 5） |
| score_average | float | 平均分 |
| score_delta | float | 较前值变化分 |
| fund_chg | float | `fund_score_minus` 资金较昨日 |
| finance_total | float | 财务总分（ablility `share_comprehensive_score`） |
| finance_prev | float | 上年同期总分（`last_score`）→ `finance_total > finance_prev` 即"财务同比改善" |
| abl_profit / abl_growth / abl_operate / abl_cash / abl_pay / abl_asset | float | 六能力当期分 |

> 说明：财务/资金两个"趋势字段"每标的各多 1 次请求 → 拉取默认 3 请求/标的。`message` 常年在 2.5（无消息刺激），筛选 UI 上给 tooltip 提示，避免误导。

### 4.4 端点表（router prefix 见 4.1）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/config` | 快照存在性/行数/更新时间 + 当前 universe + 趋势列开关 |
| GET | `/snapshot` | 返回快照 rows（含全部 schema 列）+ date + total |
| POST | `/snapshot/pull` | body `{symbols: string[], include_trend?: bool=true}` → 校验过滤后启动后台任务，返回任务已启动 |
| GET | `/snapshot/progress` | 拉取进度 |
| POST | `/snapshot/clear` | 清空快照数据（保留 config） |
| GET | `/stock/{symbol}/summary` | 总评（get_score 规范化） |
| GET | `/stock/{symbol}/finance` | finance/ablility+analysis（六能力+亮点/风险+总分同比），可选 `ability_id` 传 ablility_history |
| GET | `/stock/{symbol}/fund` | fund_summary+comprehensive，可选 `history=one-month\|one-year` 追加序列 |
| GET | `/stock/{symbol}/message` | significant_message_analyze |
| GET | `/stock/{symbol}/valuation` | 默认 `index=pb&period=1`（可传 pe/pof/ps、3/5/10） |
| GET/POST | `/prefs` | 记忆上次 universe 与 include_trend（`data/user_data/ths_diagnose.json`，沿用 user_data 运行时习惯），供重进页面/一键重拉 |

### 4.5 红线与失败隔离

- 外部接口私有无鉴权：不做后台超大批量；MVP 单次拉取默认上限 500 只（UI 有阈值提示），可分批累积；未来全 A 走路线图（§8）。
- 单只失败只记入 `failed_symbols`，可仅重拉失败项；解析失败/HTTP 失败不中断整批；数据缺失不填 0。
- 扩展加载失败只影响本功能（loader 隔离），不阻塞主程序启动。
- 拉取仅由手动请求触发，无常驻定时线程，进程退出/重启无残留任务问题。

## 5. 前端改动

### 5.1 `frontend/src/custom/diagnose/extension.tsx`（L2 注册）

- `FrontendExtension { id:'ths.diagnose', apiVersion:1 }`：
  - `routes:[{id:'ths-diagnose', path:'/diagnose', component:DiagnosePage}]`
  - `navigation:[{id:'ths-diagnose', routeId:'ths-diagnose', label:'智能诊股', icon:Radar, order:…}]`
  - `slots:[{name:'stock-preview.footer', id:'ths-diagnose-footer-summary', component:FooterSummary}]`——在个股 K 线弹窗底部展示迷你评分摘要（读快照中该 symbol 行或单只 summary）与「查看完整诊股」入口（跳 `/diagnose?symbol=xxx`）
- 子文件：`DiagnosePage.tsx`、`components/DiagnoseDetailDialog.tsx`、`components/charts.tsx`（ScoreRadar SVG 仿 [Dashboard.tsx](../../../frontend/src/pages/Dashboard.tsx#L305-L369) EmotionRadar；TrendChart 折线用 useECharts 范式 [useECharts.ts](../../../frontend/src/pages/backtest/charts/useECharts.ts#L12-L43)）、`components/FooterSummary.tsx`。
- 设计规范：先读 `.trae/docs/design.md`；尺寸/间距/色板遵守现有 Tailwind 语义 token（base/surface/elevated/accent + bull/bear）。

### 5.2 DiagnosePage 交互

- 头部：标的集合选择器（自选分组下拉（`api.watchlistGroups`/`api.watchlistList` 按组过滤）+ 手动粘贴代码 + 「加载上次快照标的」）；**「更新诊股快照」手动按钮（唯一刷新入口）** + 进度条/失败列表（可重试失败项）；快照元信息（N 只·更新于 X，含 `snapshot_date`，跨多日未更新时显示提醒）。按钮旁提示「长线价值口径：财务分按财报披露周期更新，无需盘中刷新，建议盘后手动更新」。
- 表格区：复用 `StockDataTable`（columns 自定义 + `renderCell` 注入，参照 ScreenerTable 模式）+ `useTableSort`。
  - 视图切换「平铺 / 按行业分组」：分组模式 = 左行业榜（行业名、数量、平均综合分，可点选）+ 右明细表（仅该行业），参考 ExtDimensionAnalysis 双栏实现；行业榜支持排序。
  - 每数值列 min/max 过滤输入（参照 ScreenerFilter 的 applyFilter 纯函数模式，本页为纯客户端过滤）；趋势快筛 chips：资金转强(fund_chg>0)、财务改善(finance_total>finance_prev)、综合分区间等。
  - 行点击 → `DiagnoseDetailDialog`（用与 Watchlist 相同的「state + 页面底部渲染弹窗」模式）。
- query 参数支持：`/diagnose?symbol=xxx`（详情直达，从 footer 摘要跳转进入时自动开弹窗）。

### 5.3 DiagnoseDetailDialog

- 浮层：framer-motion 全屏（仿 StockPreviewDialog，ESC/遮罩关闭）。
- 内容分区（并行拉 5 组端点，分区级 loading/error 隔离）：
  1. **概览**：名称/行业/市场排名 + 六维雷达（ScoreRadar）+ 平均分 + 消息面常 2.5 提示。
  2. **财务**：总分/上年同期对比、六能力当期条、亮点/风险列表；能力下拉 → 该能力 ablility_history 折线（45 期）。
  3. **资金**：综合分与 `fund_score_minus`、机构持股/股东增减持/大宗/龙虎榜要点；`history=one-month` 资金评分折线（附事件点标签——大/榜/减，仿 ECharts 折线 + markPoint）。
  4. **估值**：当前分位 + 个股/行业估值历史曲线（默认 pb，1 年），口径说明"分位越高越便宜"。
  5. **消息**：公告/研报列表（日期、评级/利好档、摘要），研报行可跳外链（content.url）。

### 5.4 `lib/api.ts` 与 `queryKeys.ts`（纯增量）

- `api.ts`：在类型区新增 `DiagnoseSnapshot`/`DiagnoseRow`/`DiagnoseSummary` 等 interface；在 `api` 对象加 `thsDiagnose*` 函数族（`request<T>` 封装，参照 [api.ts](../../../frontend/src/lib/api.ts) L2925-2944 的 extData 系列写法）。
- `queryKeys.ts`：新增 `QK.diagnose = { snapshot:['ths-diagnose','snapshot'] as const, progress:['ths-diagnose','progress'], … }`（参照 L73-78 extData 分组风格）。不加入 `SSE_INVALIDATE_PREFIXES`（无 SSE 实时需求，快照为手动刷新）。

## 6. 测试计划（backend/tests/custom/，先测后实现）

| 文件 | 覆盖 |
| --- | --- |
| `test_ths_diagnose_parsers.py` | 双信封判据、str 分数→float、float 保持、缺字段→None、快照行组装（sample payload 直接引用 `references/api.md` 实测样本） |
| `test_ths_diagnose_http.py` | httpx MockTransport：URL/query/market 推导、`status_code` 差异判定、5xx 单次退避、拒绝非股票 |
| `test_ths_diagnose_snapshot.py` | ExtConfig 幂等创建、rows_to_parquet 快照 merge keep-last、分批累积、clear、进度状态机（用假 client 注入） |
| `test_ths_diagnose_api.py` | 端点点参数校验、fail-closed（维表缺失/空数据）、prefs round-trip、路由与核心无冲突 |
| 前端 | 无前端单测基建 → `pnpm build` 通过 + 手测交互清单（见 §9） |

## 7. 分级结论与风险

- 分级：**L2**。理由：全部落在已开放的扩展机制内（后端 `app/custom` 路由 + 前端 `src/custom` 路由/导航/插槽 + ext-data 复用），无核心流程改动；`lib/api.ts`/`queryKeys.ts` 仅纯增量。
- 风险 / 待确认：
  1. **外部接口可用性**：eq/dq.10jqka.com.cn 无鉴权私有接口，可能随时风控；客户端限流+单次重试+分批，不静默放大。
  2. **instruments 维表资产类型列名**：实现第一步先读 schema 定过滤列，找不到则对非股票输入明确拒绝。
  3. **`ablility`/`fund` 额外请求量**：趋势列使单只拉取 3 请求；大集合（>500）MVP 不放开。
  4. **数据新鲜度**：只手动刷新时，跨交易日可能陈旧；页面展示快照 `snapshot_date` 并在过期时提示，由用户自行点更新。无自动定时即无重启/存活依赖问题。

## 8. 扩展思考 / 后续路线图

- **全 A 覆盖（用户已确认下一步）**：引入"目标集合 = 全 A 股"模式 → 低并发跑批 + 分片断点续拉 + 多日 timeseries 分区，仍以手动触发为主。
- **盘后自动刷新（可选）**：若后续希望到点自动更新（例如财务披露季手动不便），再评估扩展内定时或接入核心盘后管道（属 L3），MVP 明确不做。
- **诊股分数成为全站数据资产**：快照 ext 表已被 ext-data 生态支持 → 后续可让 `ext_ths_diagnose` 列并入 enriched 帧（现状由 ext API 写入时注册视图并清缓存），使 Screener/自定义信号/监控规则/回测因子能引用"资金转强/财务改善"类条件——需评估扩展列接入链路。
- **跨日趋势筛选**：timeseries 化后支持"近 5 日资金分上行/财务分连续改善"等区间条件过滤；详情弹窗内的序列也可下沉为筛选。
- **与现有弹窗联动**：`stock-preview.footer` 摘要已在 MVP；后续可加"诊股评分异动"通知（复用 Monitor 规则需要新能力，按需扩展）。
- **组合成策略输入**：评分列参与 `ScoringEditor` 权重/自定义 SQL 选股需接入相应层，均属后续真实需求驱动，不提前建设。

## 9. 实施顺序与验证

1. 读 `.trae/docs/design.md`、`docs/secondary-development.md` §6 模板、`references/api.md`，核实 instruments 维表 schema。
2. 后端：parsers → client（含测试）→ service → api → `__init__` 接线。
3. 前端：api.ts/queryKeys 增量 → extension.tsx → DiagnosePage → DiagnoseDetailDialog → FooterSummary。
4. 验证（CONTRIBUTING §9 二开矩阵 + secondary-development §7）：
   - `cd backend && uv run pytest tests/custom/test_ths_diagnose_*.py -q`
   - `uv run ruff check app/custom/ths_diagnose tests/custom`
   - `cd frontend && pnpm build`
   - `git diff --check`；`git status --short`
   - 手测：扩展路由/导航出现、手动快照拉取进度与失败重试、行业分组、区间筛选与排序、详情弹窗各分区、K 线弹窗底部摘要入口、扩展失败隔离（临时改坏 extension.tsx 观察错误边界）。
5. 完成后更新文档提示：`/understand-feature` 生成功能文档并在 architecture.md §0.5 登记（按 new-extension 第 6 步）。
