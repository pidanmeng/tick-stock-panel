---
name: new-extension
description: 引导进行项目二次开发（L1 配置/策略文件、L2 插槽/注册、L3 源码修改）。先调用 extension-guide 说明架构与约束，再分级引导实现并验证。
---

# 二次开发引导

按以下流程引导用户在 TSP 项目中完成二次开发。二次开发规范以 `docs/secondary-development.md` 为准，架构约束以 `.trae/docs/architecture.md` 与 `CONTRIBUTING.md` 为准，不虚构不存在的 API 或扩展点。

## 执行步骤

1. **收集需求**：明确要新增/修改的功能、目标资产（股票/ETF/指数）、交互形态（页面/弹窗/表格列/API/通知）、期望接入的位置。

2. **调用 `extension-guide` 子 Agent**：让子 Agent 基于仓库真实架构说明：该需求属于哪个功能域、涉及哪些模块边界、存在哪些扩展点（前端插槽/后端注册/Provider 能力/策略目录）、应归为 L1/L2/L3 哪一级及理由。

3. **确认实现方案**：与用户确认最终的实现级别与落盘位置：
   - **L1**：配置 / 策略文件 / 扩展数据 / YAML 数据源，参考 `docs/secondary-development.md` 与 `docs/configuration.md`。
   - **L2**：前端扩展注册（`frontend/src/custom/<ns>/extension.tsx`，3 个已开放插槽）、后端注册替换（`backend/app/custom/`，`NotificationFormatter`）。
   - **L3**：直接修改核心源码（必须先说明冲突风险与最小改动方案）。
   - 若需求现有能力无法承载，明确说明"该能力按 docs 标注尚未实现"并停止，不虚构 API。

4. **实现**：按 `developer` 子 Agent 的开发流程最小改动实现；先补能证明行为的测试，再实现逻辑；不顺手重构无关代码。

5. **验证**：按 `CONTRIBUTING.md` §9 验证矩阵执行适用命令（后端定向 pytest + ruff、前端 `pnpm build`、`git diff --check`），如实汇报实际命令与输出；无法执行的验证写明原因。

6. **更新文档**：若改动新增了功能或扩展点，提示用户可用 `/understand-feature` 更新功能文档、用 `architecture.md` 索引。

7. **输出总结**：方案分级与理由、修改文件清单（`路径:行号`）、关键契约变化、验证结果、剩余风险；不自动 commit/push/merge/删文件。

## 输出格式

```text
需求: [一句话]
分级: L1/L2/L3（依据）
落盘位置: [文件或目录]
修改清单:
- [路径]: [改动说明]
关键契约变化: [如有]
验证: [实际执行的命令与结果]
风险/待确认: [如有]
```