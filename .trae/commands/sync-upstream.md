---
name: sync-upstream
description: 将上游 GitHub 开源项目（fork 来源）的更新同步到本地仓库并处理冲突。先做安全检查与分歧分析，默认 merge 同步，冲突时调用 upstream-sync 子 Agent 出预案，用户逐项确认后执行，最后按验证矩阵回归。
---
# 同步上游更新（sync-upstream）

本命令用于将 fork 来源的上游项目代码定期同步进本地仓库并解决冲突。上游以 `git remote -v` 中的 `upstream` 为准；同步结果以真实 git 状态为准，不虚构 commit、冲突或解决结果。

## 执行步骤

1. **安全检查（先于一切）**
   - `git status`：工作区必须干净；有未提交/未 stash 的本地改动时，先列出改动并请用户选择 commit 或 stash，禁止静默丢弃。
   - 确认当前分支（默认 `main`）与 `git remote -v` 中 upstream 地址存在且可达；upstream 未配置时提示先 `git remote add upstream <url>`（需用户确认执行）。

2. **分歧分析（只读）**
   - `git fetch upstream`（fetch 只更新远端跟踪引用，不改工作区）。
   - `git rev-list --left-right --count upstream/main...main` 统计双向领先 commit，明确分叉规模。
   - 列出 `git log main..upstream/main --oneline`（上游新增）与 `git log upstream/main..main --oneline` 的数量（本地独有），向用户说明将把上游哪些内容合入。
   - **归纳本次上游新增功能与修改**：结合 `git log main..upstream/main` 与 `git show`/`git diff` 的真实内容，按功能/模块分组说明上游这次"新增了什么功能、改了什么行为"（如新增页面/API/策略能力、改动数据契约、依赖变更等），展示给用户，禁止臆测。
   - 若存在上次同步记录（如 sync 分支或文档），以此估算冲突风险面。

3. **合并方式确认**
   - 默认 `git merge upstream/main`（保留双方历史，不重写本地 commit）。
   - 仅当用户显式要求时才用 rebase，并先说明会重写本地独有 commit、冲突需逐个解决、可能需 force push。

4. **执行同步（需用户确认后操作）**
   - 展示将要执行的 git 命令后请用户确认再执行 merge；**不自动 commit/push/merge**，每步以确认门为准。

5. **冲突解决（存在冲突时）**
   - `git status` 列出冲突文件清单（`UU`/`AA`/`AU`/`UA` 等）。
   - 调用 `upstream-sync` 子 Agent：输入冲突文件清单与本地独有 commit 摘要，让其按 `.trae/docs/architecture.md` 与 `CONTRIBUTING.md` 模块边界输出"本次上游新增功能/修改摘要 + 冲突归属 + P0-P3 风险分级 + 逐文件解决预案"。
   - **先向用户完整汇报本次上游新增功能与修改**（Agent 摘要），用户了解上游改动意图后，再进入逐文件取舍确认。
   - **逐项与用户确认取舍**后才执行 `git add <file>`；P0/P1（架构红线/核心逻辑）文件必须用户拍板，Agent 只给建议不擅自二选一。
   - 处理完 `git diff --check` 确认无空白错误。

6. **回归验证**
   - 若冲突/合并涉及 P0/P1 文件（后端服务、数据契约、前端核心），按 `CONTRIBUTING.md` §9 验证矩阵执行适用验证（后端定向 pytest + ruff、前端 `pnpm build`），如实汇报实际命令与结果；无法执行的验证写明原因。
   - 只读文档/配置类冲突（P3）可不跑全量验证，但需说明依据。

7. **输出总结**
   - 同步的 upstream commit 范围、合并或冲突解决后的文件清单、每个冲突的取舍决策、验证结果与剩余风险；**不自动 commit/push**，由用户决定提交方式。

## 输出格式

```text
同步对象: upstream/<branch> → <本地分支>
分歧规模: 上游新增 X 个 / 本地独有 Y 个 commit
上游本次新增/修改摘要: [按功能/模块分组：新增了什么、改了什么行为，依据真实 commit/diff]
合并方式: merge / rebase（依据）
冲突文件:
- [路径]: 冲突内容摘要 → 建议取舍（P0-P3 分级）
已解决取舍: [用户确认的决策]
验证: [实际执行的命令与结果]
剩余风险: [如有]
提交状态: [未 commit / 已 commit，由用户决定]
```
