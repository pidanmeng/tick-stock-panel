---
name: understand-feature
description: 理解代码的某个特定功能并落实到文档。按标准模板产出功能文档，供后续修改/扩展/复审使用。
---

# 理解代码功能并文档化

按以下流程理解目标功能并产出功能文档，最终保存到 `.trae/docs/features/{feature-name}.md`。

## 执行步骤

1. **确认目标功能**：收集用户想要理解的功能名称、关键词、页面路径或 API 端点。

2. **调用 `feature-documenter` 子 Agent**：将用户描述的功能需求作为任务输入，让 `feature-documenter` 完成代码阅读、调用链追踪和文档初稿。

3. **确认文档**：将子 Agent 产出的文档初稿展示给用户，获得确认后写入 `.trae/docs/features/{feature-name}.md`。

4. **更新索引**：在 `.trae/docs/architecture.md` 的对应章节中，添加链接指向新创建的功能文档。

5. **输出总结**：告知用户功能文档已创建的位置、覆盖的内容范围，以及通过 `architecture.md` 可找到该文档的路径。

## 文档规范

- 严格遵循 `.trae/docs/features/_template.md` 的模板结构。
- 所有文件引用必须附带 `路径:行号` 锚点。
- 只描述代码中已存在的实现，不虚构 API、流程或数据结构。
- 区分"已实现"与"规划中"的能力。
- 数据流和调用链必须以代码证据为准，未经代码证实的内容需标注"待确认"。

## 输出格式

```text
功能: [功能名称]
文档: .trae/docs/features/{feature-name}.md
索引: .trae/docs/architecture.md 第 X 节
覆盖内容:
- 文件清单: N 个后端文件, M 个前端文件
- 业务逻辑与数据流: [概述]
- 调用链: [入口 → ... → 输出]
- 扩展指南: L1/L2/L3 扩展方式
- 测试覆盖: [测试文件列表]
```