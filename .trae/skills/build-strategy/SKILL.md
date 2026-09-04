---
name: build-strategy
description: 引导在 TSP 中新建或修改自定义策略/自定义信号（二次开发 L1 级）。当用户要求"新建一个策略/信号/选股条件/改某个策略逻辑/想让引擎跑我的策略"时使用。
---
# 自定义策略/信号开发（build-strategy）

## 描述
TSP 策略体系由 `StrategyEngine` 从固定目录加载，支持自定义/AI/叠加策略与自定义信号。本技能保证新策略按项目真实契约落地、口径正确、可被引擎加载并被验证。

## 使用场景
- 创建自定义策略文件（L1：`data/strategies/custom/` 下的用户策略文件）。
- 新增/修改自定义信号表达式（设置页"信号库"或 `custom_signals` 体系）。
- 需要判断某选股思路用哪种扩展方式实现。

## 指令

1. **先读规范**（依据真实文档，不假设）：
   - `docs/strategy.md`（策略体系、三种扩展方式、文件结构）
   - `backend/app/strategy/prompts/strategy-guide.md` 与 `strategy-guide-compact.md`（策略开发完整规范，AI 生成与手写通用）
   - `CONTRIBUTING.md` §5.1（策略领域要求）与 `.trae/rules/project_rules.md`

2. **定位真实机制**（用代码确认，勿照设计示例虚构）：
   - 引擎加载目录与加载方式：`backend/app/main.py` 中 `StrategyEngine` 的 `strategy_dirs`（builtin 与 `data/strategies/{custom,ai,composite}`）；引擎入口 `backend/app/strategy/engine.py`。
   - 参数/过滤/评分/结果结构的统一契约：参考 `backend/app/strategy/builtin/` 中 1-2 个与思路最接近的**真实内置策略**模块结构。
   - 自定义信号的注册与白名单：`backend/app/strategy/custom_signals.py`。

3. **归类与设计**：
   - 明确策略类型：选股策略（内置参数化）/ 自定义信号 / 叠加（composite）/ 分钟策略 / AI 生成模板。按 `docs/strategy.md` 判断正确落盘位置与形态。
   - 先确认现有内置策略或参数能否覆盖需求；禁止平行实现第二套。
   - 若属于"扩展点不存在、必须改源码"，升级为 L2/L3 并说明，不在此技能范围内直接改核心。

4. **实现要点**：
   - 名称与 ID 唯一稳定；新建/编辑不覆盖既有策略 ID（复制/导入需分别处理 ID 冲突）。
   - 评分字段必须有确定来源或临时计算路径；缺输入返回明确"不可计算"，不把空值伪装成零分。
   - 口径核对：复权/换手/涨跌幅、交易日与北京时区、资产类型（股票/ETF/指数不串）、所需历史窗口（`required_history` 等声明与 engine 校验对齐）。
   - 指标依赖使用 enriched 现算指标列名与信号列（参考 `backend/app/indicators/pipeline.py` 列清单），不自己造列。

5. **接线与缓存**：改参数/文件后核对同步范围：策略结果缓存（`services/strategy_cache.py`）、监控实例（`strategy/monitor.py`）、AI 生成 META 解析（如涉及）与前端查询。按 `CONTRIBUTING.md` §6 失效链走，不遗漏。

6. **验证**（按 `run-verification` 技能/`CONTRIBUTING.md` §9 执行）：
   - 后端：对应策略/引擎测试（正常 + 边界 + 失败路径），至少覆盖参数变更、缓存失效与资产切换。
   - 前端（如涉及页面字段）：`pnpm build`。
   - 提交前 `git diff --check`。

7. **输出**：方案归类（L1/L2/L3）、落盘文件路径、策略契约（参数/过滤/评分/结果）、口径与缓存核对结果、实际验证结果、剩余风险。

## 注意
- 用户策略文件属用户数据，写入/覆盖前先展示方案并获得确认。
- 不修改 `backend/app/strategy/builtin/` 既有策略来演示；以新建为主。
