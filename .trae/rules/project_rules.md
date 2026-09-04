# 项目规则（常驻精简版）

> 本文件随每次对话自动注入，只放最高价值的约束；详细架构与证据见 `.trae/docs/architecture.md`，规范以 `CONTRIBUTING.md` / `docs/secondary-development.md` 为准。

## 必读文档链（按顺序）

1. `AGENTS.md`（AI 开发入口）
2. `CONTRIBUTING.md`（模块边界/数据契约/验证矩阵/复审流程）
3. `docs/secondary-development.md`（二开与扩展契约；区分"已可用/按需扩展"）
4. `.trae/docs/architecture.md`（架构地图，只描述已存在实现，标注锚点）

## 唯一事实来源

- 改动前先用代码与测试证实调用链、缓存层与现有测试，不凭文件名或界面现象猜测。
- 禁止虚构 API、流程、测试结果与性能数据。`secondary-development.md` 列出的"按需扩展"接口（如 CandidateFilter/ScoringPolicy/BacktestCostModel 等）**未实现不得导入**；设计示例不是实现。
- 带 `文件:行号` 给出证据；不确定必须明说，不得猜测成事实。

## 架构护栏（硬约束）

- 严格按现有架构实施：**不修改 DuckDB 内存视图结构、Parquet schema、enriched 窄表列、API 契约、`data/` 目录布局**。
- **不新增项目不存在的数据结构、模块、流程或扩展点**；禁止平行实现第二套数据/策略/缓存/请求逻辑。
- 新能力先确认能否由现有 Provider 能力、数据集、前端插槽或后端注册机制承载；只有确需修改核心时才按 L3 处理并补回归。
- 保持最小改动，不顺手重构、格式化或删除无关代码；不覆盖工作区已有修改。

## 数据契约红线速记

- 比例/百分比：实时源入口 `change_pct`/`turnover_rate` 为小数制；enriched `turnover_rate` 为百分数值；指数缓存存在百分数口径。跨边界显式转换，禁止"数值<1 乘 100"启发式。
- enriched OHLC 为前复权、`raw_*` 为不复权；涨跌停判断用原始价。
- 窗口/前 N 日按实际交易日；A 股统一北京时间；分钟 K `datetime` 为北京 naive 墙钟，禁止 UTC 入库/下发。
- 股票/ETF/指数分开存储与路由，不凭代码格式猜资产类型。
- 财务按 `(symbol, period_end)` 并集 + 公告日 PIT；公告前空值不填 0。
- provider 缺能力/字段缺失/空数据：明确提示或 fail-closed，禁止静默返回错误金融结果。

## 验证与提交

- 按 `CONTRIBUTING.md` §9 验证矩阵执行最小充分验证：后端定向 pytest + ruff、前端 `pnpm build`、提交前 `git diff --check`。
- 只汇报实际执行的命令与结果；无法执行时说明原因与剩余风险。
- 不自动 commit / push / merge / 删文件 / 数据库迁移 / 批量覆盖；需要时先取得明确确认。
