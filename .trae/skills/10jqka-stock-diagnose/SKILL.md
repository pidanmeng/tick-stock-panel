---
name: 10jqka-stock-diagnose
description: 同花顺智能诊股接口(eq/dq.10jqka.com.cn)的入参、返回字段、信封与 market ID 对照参考。当需要分析单只 A 股的总评/资金/财务/估值评分或公告研报要点，或将 10jqka 诊股数据接入扩展/数据源时使用。
---
# 同花顺智能诊股接口参考（10jqka-stock-diagnose）

## 描述

同花顺 App「智能诊股」页抓包得到的**未公开开放接口**文档（Reqable 抓包 + 2026-09-09 实抓对拍 + App 页面对照核验）。覆盖：总评（综合评分）、资金面评分与要点、财务评分与亮点风险、估值分位、公告/研报事件。字段语义口径已经用户逐项核验，仍有疑点的字段明确标注「未证实」。

接口与项目既有 `backend/app/plugins/fuyao/`（同花顺 fuyao 官方 REST、带 X-api-key）是**同族但不同 surface**：本技能接口挂在 `eq.10jqka.com.cn` / `dq.10jqka.com.cn` 私有域名下，抓包时无鉴权头、普通网络直连即可 200（实测日期见下），可能随时加风控，按需低频调用。

**资产覆盖**：经核验**仅沪深 A 股股票**，不含 ETF/指数/北交所。因此实际只会用到 market=17（沪）与 33（深，含创业板/科创板依赖同族口径，688 未在诊股接口单独实测）。

## 使用时机

- 需要查询单只沪深 A 股的总评分数、资金/财务/估值评分或评分历史。
- 需要结构化的"亮点/风险/公告/研报要点"文本数据（如为 AI 分析提供素材）。
- 需要把 10jqka 诊股能力接入扩展、Provider 或作为研究素材。

## 接口总表

| # | 功能 | Host / surface | 路径段 | 成功判定 | 关键入参 |
|---|------|----------------|--------|----------|----------|
| 1 | 总评 | eq.10jqka.com.cn（open/api 面） | `.../stock_diagnose_v2/composite_score/v1/get_score/{market}/{code}` | `status_code == 0` | path: market, code |
| 2 | 资金要点概述 | dq.10jqka.com.cn（fuyao 面） | `.../stock_diagnose_general/fund/v1/fund_summary/get` | `status_code == 200` | stock_code, stock_market |
| 3 | 资金评分历史 | 同上 | `.../fund/v1/fund_history/get` | `status_code == 200` | stock_code, stock_market, period |
| 4 | 资金评分（综合） | 同上 | `.../fund/v1/fund_comprehensive_evaluation/get` | `status_code == 200` | stock_code, stock_market |
| 5 | 公告/研报要点 | 同上 | `.../message/v1/significant_message_analyze/get` | `status_code == 200` | ths_code |
| 6 | 财务亮点与风险 | dq.10jqka.com.cn（stock_diagnosis 面） | `.../finance/v1/analysis` | `status_code == 0` | code, market |
| 7 | 财务评分（含上年同期） | 同上 | `.../finance/v1/ablility` | `status_code == 0` | code, market |
| 8 | 财务评分历史 | 同上 | `.../finance/v1/ablility_history` | `status_code == 0` | code, market, ability_id |
| 9 | 估值分位分析 | dq.10jqka.com.cn（stock_diagnosis_valuation 面） | `.../valuation/v1/valuation_industry` | `status_code == 0`（注意键名 `status_message`） | code, market, index, period |

**注意**：信封的成功码与字段名不统一——总评/财务/估值为 `status_code == 0`（且带 `status_msg` 或 `status_message`），资金/公告为 `status_code == 200`。逐接口明细见 `references/api.md`。

## Market ID 规则与对照

### 提取规则

同花顺诊股接口里 market ID 有两种承载方式，数值含义一致：

1. **路径式**（仅总评接口）：URL 中股票代码前紧邻的数字段，形如 `.../get_score/33/300476` —— 斜杠后是股票代码 `300476`，其前的 `33` 就是 market ID。
2. **查询式**（dq 面其余接口）：query 参数 `stock_market`（资金组）或 `market`（财务组/估值组），值与路径式相同。

### market ID → 市场对照

市场编码与 [quota_kline.py](../../backend/app/plugins/fuyao/quota_kline.py)（`classify_symbol`，L62-L93）属同一套同花顺内部市场码：

| market | 市场/板块 | 前缀（内部 code 口径） | 资产类型 |
|--------|-----------|------------------------|----------|
| 17 | 沪市（含科创板） | `6xxxxx` | 股票 |
| 20 | 沪市 | `5xxxxx`（51/56/58…） | ETF |
| 16 | 沪市指数 | 000001→1A0001、000300→1B0300、000680→1B0680 等 THS 码（见 quota_kline.py L45-46） | 指数 |
| 33 | 深市（含创业板） | 000/001/002/003/300/301 | 股票 |
| 36 | 深市 | `159xxx` | ETF |
| 32 | 深市指数 | `399xxx` | 指数 |
| 151 | 北交所 | — | 股票 |

**实测**：`33`（300476.SZ）、`17`（600519.SH）在总评/资金接口均正常返回。**资产覆盖核验结论**：诊股接口仅覆盖沪深 A 股股票（不含 ETF/指数/北交所），实际只会出现 17/33；表中 20/36/16/32/151 仅作为同族编码参考，不应对诊股接口使用。`33` 只区分"深市"，不区分深主板/创业板，接口返回里 `stock_ths_code`（如 `300476.SZ`）才带具体后缀。

## 通用约束与口径（含核验结论）

- **鉴权**：抓包与实抓均无鉴权头；不代表长期可用，调用失败时先排查网络/风控，不要盲目重试放大请求量。
- **评分刻度**：总评六个维度分满分均为 5、越高越好；`finance` 是唯一按财报披露周期更新的维度，其余（fund/tech/valuation/message）**每日更新**；资金面 `fund_score` 盘中会刷新。
- **时区/日期格式**：字段混用 `YYYY-MM-DD`（总评 date、估值 dict 键）、`YYYYMMDD`（资金/财务历史、公告 pubDate）、`YYYYMMDDHHMMSS`（资金评分更新时间）；均为北京口径。
- **分数类型**：`rank.score`/`fund_score`/估值数值为 float；复合分/历史分多为 `str`（如 `"4.5059"`、`"2.833333330"`），解析时按实际类型处理。
- **成功判据不一**：见总表；统一按 `data` 存在 + 对应 status 判定，禁止只认一种。
- **仍属未证实**：`strength` 档位含义、`tech_stock_*_comment` 用途、`holding_change` 四类主体（manager/actual_ctrl/strong/net）的精确归属、`message` 的 `eventType`/`labelProperty` 全量枚举——详细见 `references/api.md` 对应接口。

## 文件

- `references/api.md` — 逐接口入参表、返回字段表、实测样本与口径注释。
