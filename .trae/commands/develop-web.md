---
name: develop-web
description: 引导迭代与开发本项目前端网站（页面/组件/样式/交互/路由/前端扩展）。收集需求后调用 web-developer 子 Agent 落地，逐轮 build/lint 验证并支持多轮迭代。
---

# 前端网站迭代与开发引导

面向/迭代 Tick Stock Panel 的"网站"即前端 `frontend/`（React 18 + TS + Vite）。规范以 `docs/secondary-development.md` 为准，架构约束以 `.trae/docs/architecture.md` 与 `CONTRIBUTING.md` 为准；所有提及的组件/插槽/接口必须经查证真实存在，不虚构 API 或扩展点。

## 执行步骤

1. **收集需求**：明确要新增/修改的前端内容——目标页面（如 Dashboard/Screener/个股分析/设置等）、交互形态（页面/弹窗/表格列/图表/导航项/表单校验）、目标资产（股票/ETF/指数）、期望的接入位置与视觉/交互要求。

2. **确认实现级别与方案**（参考此前 `new-extension` 分级）：
   - **L1**：配置文件、自定义 YAML 数据、主题/菜单配置。
   - **L2**：前端扩展注册 `frontend/src/custom/<ns>/extension.tsx`（静态页/导航/3 个已开放插槽）、路由/导航注册；后端注册替换。
   - **L3**：直接修改核心前端源码（先说明冲突风险与最小改动方案）。
   - 若需求现有组件/插槽/接口无法承载，明确说明并按 L3 或"尚未实现"处理，不硬造第二套机制。
   - **动代码前必须通读 `.trae/docs/architecture.md`**（连同 `docs/secondary-development.md`/`CONTRIBUTING.md`）后再定方案；禁止跳读架构直接上手，或仅凭文件名/界面现象猜测扩展点。

3. **调用 `web-developer` 子 Agent**：将收集到的需求与实现级别交给 `web-developer`，要求它严格走：**先读架构文档链**（`.trae/docs/architecture.md` + `docs/secondary-development.md` + `CONTRIBUTING.md`）→ 保留现场 → 找真相（`lib/api.ts`/`queryKeys.ts`/既有组件/真实插槽）→ 计划 → 先测试后实现 → `cd frontend && pnpm build` 验证 → 汇报清单与风险。涉及纯视觉/动效打磨可参考 `frontend-design` 技能，但需遵守项目既有设计系统与可访问性。

4. **逐轮迭代**：先让子 Agent 狭窄落地首版（最小可用），经查看后确认方向，再增量扩展；每轮都要重新 `pnpm build` 且不被破坏既有布局/窄屏/响应式。

5. **验证**：前端必须通过 `frontend` 下 `pnpm build`（`tsc -b && vite build`），相关再用 `pnpm lint`（eslint）与仓库根目录 `git diff --check`；如实汇报实际命令与输出，无法执行的验证写明原因。需要肉眼确认时启动 `pnpm dev` 供浏览。

6. **需求验收后归档文档**：在整个需求验收完成之后，若新功能是一个比较大的模块（涉及新页面/组件/插槽/扩展点，或跨多个文件的完整功能域），应将其功能文档纳入 `architecture.md` 归档。具体流程与模板参考 `/understand-feature`：调用 `understand-feature` 的流程，将需求原先的目标功能交给 `feature-documenter` 产出文档初稿并确认后，写入 `.trae/docs/features/{feature-name}.md`，再在 `.trae/docs/architecture.md` 对应章节添加索引链接，并同步 `docs/secondary-development.md` 的插槽清单（如新增插槽/扩展点）。小改动（单点修复、纯样式的微调）不强制归档，做雏形即可不安排。

7. **输出总结**：实现级别与理由、修改文件清单（`路径:行号`）、关键契约/插槽变化、对缓存与布局的影响、验证结果、下一轮可迭代项与剩余风险；不自动 commit/push/merge/删文件。

## 输出格式

```text
需求: [一句话]
分级: L1/L2/L3（依据）
落盘位置: [文件或目录]
修改清单:
- [路径]: [改动说明]
关键契约/插槽变化: [如有，含 apiVersion]
验证: [实际执行的命令与结果]
下轮可迭代项: [如有]
风险/待确认: [如有]
```