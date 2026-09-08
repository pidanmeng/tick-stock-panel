---
title: AI 设置
description: AI 设置页功能文档 — 连接预设、模型配置、策略 AI 组件。
---

# AI 设置（设置 → AI） — 功能文档

> 本文档是该功能的完整参考，包含所有修改、编辑或扩展该功能需要了解的内容。

## 功能概述

AI 设置页是「设置」页签之一（Tab id `ai`，前端外壳见 [Settings.tsx:22-30](file:///c:/Code/tick-stock-panel/frontend/src/pages/Settings.tsx)），负责配置策略 AI 组件与定时复盘的大模型接入。支持 OpenAI 兼容协议与 Codex CLI 两种模式，提供预设模板（DeepSeek / 通义千问 / 智谱 GLM / Kimi 等），管理连接测试与凭证清空。

核心定位：**策略 AI 点评与复盘报告的 LLM 后端唯一配置入口**，不处理普通对话或聊天。

## 文件清单

### 后端

| 文件 | 路径 | 用途 |
|------|------|------|
| API 入口 | `backend/app/api/settings.py` | `POST /api/settings/ai` 保存、`DELETE /api/settings/ai` 清空 |
| AI Provider | `backend/app/services/ai_provider.py` | `ai_configured` / 模型与推理参数 getter、Codex 命令规范 |
| 密钥存储 | `backend/app/secrets_store.py` | AI 凭证的读写（secrets.json） |

### 前端

| 文件 | 路径 | 用途 |
|------|------|------|
| 页面 | `frontend/src/pages/settings/AI.tsx` | 预设选择、连接状态卡片、配置表单、保存/清空/测试 |
| API 客户端 | `frontend/src/lib/api.ts` | `saveAiSettings` / `clearAiSettings` / `strategyAiTest` |
| 查询键 | `frontend/src/lib/queryKeys.ts` | `QK.preferences` / `QK.capabilities` |

### 配置/数据

| 文件 | 路径 | 用途 |
|------|------|------|
| 密钥 | `data/secrets.json` | `ai_provider` / `ai_base_url` / `ai_api_key` / `ai_model` 等 |

## 业务逻辑

### 核心流程

```text
用户选择预设（PRESETS）→ 预填 provider/base_url/model
  └→ openai_compat 模式：额外 base_url + API key + 可选 UA + 高级参数（max_output_tokens / context_window）
  └→ openai 模式：额外 reasoning_effort（low/medium/high）
  └→ codex_cli 模式：固定命令 codex，选择模型/推理力度下拉
→ 点击「保存」→ POST /api/settings/ai → 持久化到 secrets.json + 同步运行时 settings
→ 点击「测试」→ 先保存再调 strategyAiTest() → 验证连通性
→ 点击「清空」→ DELETE /api/settings/ai → 清除凭证，重置运行时默认值
```

### 数据流

1. **输入来源**：用户选择预设或手动填写连接参数。
2. **处理过程**：
   - 前端 `payload()` 组装提交参数（[AI.tsx:98-110](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/AI.tsx)）：`provider`、`base_url`、`api_key`（undefined 时不覆盖）、`model`、`reasoning_effort`（仅 openai）、`codex_command` / `codex_reasoning_effort`（仅 codex_cli）、`user_agent`（有开关则非空，否则 ''）、`max_output_tokens`（默认 8192）、`context_window`（默认 64000）。
   - 后端 `POST /api/settings/ai`（[settings.py:262-346](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：按 provider 分支保存——`codex_cli` 调用 `normalize_codex_command`/`normalize_codex_model` 校验；`openai` 单独存 `reasoning_effort`；`user_agent` 无条件持久化（清空凭证不影响自定义 UA）；`max_output_tokens`/`context_window` 为正整数校验。
   - 清空 `DELETE /api/settings/ai`（[settings.py:349-378](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：清除 8 个字段，保留 `ai_user_agent`；重置运行时内存 `provider=openai_compat`、`codex_command=codex`、`max_output_tokens=8192`、`context_window=64000`。
   - 连接状态判定：`ai_configured` 由 provider + has_ai_key / codex 组合判断（[AI.tsx:76-78](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/AI.tsx)）。
3. **输出去向**：全部写入 `secrets.json`；运行时同步到 `settings` 对象；前端 `ai_configured` 状态用于复盘入口的守卫。

### 调用链

```text
AI.tsx 表单 → api.saveAiSettings(payload()) → POST /api/settings/ai
  → backend/app/api/settings.py:262-346 → secrets_store.save() → backend/app/secrets_store.py
  → 同步 settings.ai_provider / .ai_base_url / .ai_api_key / .ai_model 等
  → 返回 {ai_provider, ai_model, ai_configured, ...}
```

### 状态机

```text
未配置（provider=openai_compat，无 key）──保存配置──▶ 已配置（ai_configured=true）
       ▲                                                   │
       └──────────────── 清空 ──────────────────────────────┘
```

## 关键数据结构

### API 契约

**预设列表**（[AI.tsx:10-45](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/AI.tsx)）：

| 预设 | provider | base_url | model |
|------|----------|----------|-------|
| 自定义 | openai_compat | （空） | （空） |
| OpenAI | openai | https://api.openai.com/v1 | gpt-5.5 |
| DeepSeek | openai_compat | https://api.deepseek.com/v1 | deepseek-chat |
| 通义千问 | openai_compat | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-turbo |
| 智谱 GLM | openai_compat | https://open.bigmodel.cn/api/paas/v4 | glm-4-plus |
| Kimi | openai_compat | https://api.moonshot.cn/v1 | moonshot-v1-8k |
| Codex CLI | codex_cli | （无） | codex （固定命令） |
| 炸鸡中转站 | openai_compat | https://api.zhaji.dev/v1 | claude-sonnet-4-20250514 |

**`POST /api/settings/ai` 请求体**（`AiSettingsIn`，[settings.py:249-259](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：

```json
{
  "provider": "openai_compat | openai | codex_cli",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-... | null（不覆盖）",
  "model": "gpt-5.5",
  "reasoning_effort": "high",
  "codex_command": "codex",
  "codex_reasoning_effort": "xhigh",
  "user_agent": "custom UA",
  "max_output_tokens": 8192,
  "context_window": 64000
}
```

**`GET /api/settings` 返回的 AI 字段**（[settings.py:83-97](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）：`ai_provider`、`ai_base_url`、`ai_api_key_masked`、`has_ai_key`、`ai_configured`、`ai_model`、`ai_openai_model`、`ai_reasoning_effort`、`ai_codex_model`、`ai_codex_command`、`ai_codex_reasoning_effort`、`ai_user_agent`、`ai_max_output_tokens`、`ai_context_window`。

### 存储结构

- **secrets.json**：`ai_provider`、`ai_base_url`、`ai_api_key`、`ai_model`、`ai_reasoning_effort`、`ai_codex_model`、`ai_codex_command`、`ai_codex_reasoning_effort`、`ai_user_agent`、`ai_max_output_tokens`、`ai_context_window`。
- 运行时 `settings` 对象（`backend/app/config.py`）镜像以上字段，作为 getter 的备选默认值。

### 内存结构

- `ai_provider.py` 各 getter 优先读 secrets.json，缺省时回退 `settings` 的默认值。
- `current_ai_model()` 按 provider 分支返回 `ai_model` 或 `ai_codex_model`。

## 扩展与修改指南

### L1 扩展（配置/策略文件/扩展数据）

- 修改预设：在 [AI.tsx:10-45](file:///c:/Code/tick-stock-panel/frontend/src/pages/settings/AI.tsx) 的 `PRESETS` 数组新增条目，定义 `provider` / `base_url` / `model` 三元组。

### L2 扩展（插槽/路由/注册替换）

- **新增 provider 类型**：在 `ai_provider.py` 新增分支，`AiSettingsIn` 中增加对应字段，`settings.py:262-346` 的保存逻辑增加处理分支，前端 `AI.tsx` 的 `payload()` 增加对应字段。

### L3 修改（直接改源码）

- 修改默认值：`max_output_tokens`（8192）和 `context_window`（64000）的默认值在 `settings.py:375-376` 清空重置处，以及前端 `AI.tsx` 的 `payload()` 函数中。

### 缓存失效影响

| 缓存层 | 失效方式 | 影响范围 |
|--------|----------|----------|
| 文件 | 直接写 `secrets.json` | AI 凭证 |
| 运行时 | 同步 `settings` 对象 | 策略 AI + 复盘调度 |
| 前端 | 保存后刷新 `QK.preferences` | 连接状态卡片、复盘页面的 `ai_configured` 守卫 |

### 测试

| 测试类型 | 位置 | 关键测试用例 |
|----------|------|-------------|
| API 测试 | `backend/tests/` | 保存/清空/各 provider 分支/非法参数校验 |
| 前端测试 | `frontend/src/` | 预设预填、Codex 模式下拉、保存/清空/测试按钮状态 |

## 依赖关系

### 依赖的其他功能

- 无（AI 设置是独立配置，被策略 AI 与复盘消费）

### 被依赖的功能

- [选股策略 AI](review.md)：策略 AI 分析功能依赖 `ai_configured` 状态。
- [定时复盘](review.md)：复盘调度依赖 AI Key（`POST /preferences/review-schedule` 校验 `has_ai_key`，[settings.py:1882-1889](file:///c:/Code/tick-stock-panel/backend/app/api/settings.py)）。

## 常见问题与注意事项

- **Key 隐私**：保存后 `ai_api_key_masked` 返回脱敏值（`sk-****...****`），前端只显示掩码，不可回读明文。
- **Codex CLI 模式**：`codex_cli` 模式下命令固定为 `codex`，`base_url` 和 `api_key` 被忽略；上下文按 OpenAI 协议发送，需确保模型支持。
- **清空不丢 UA**：`DELETE /ai` 保留 `ai_user_agent`，与凭证解耦，避免清空后 CDN 拦截问题复发。
- **测试先保存**：测试按钮先调用 `api.saveAiSettings()` 再调 `api.strategyAiTest()`，确保测试时使用最新配置。
- **高级参数**：`max_output_tokens` 和 `context_window` 钳制所有 AI 任务的 token 上限，缺省值 8192/64000 适用于大多数场景。