# 智能诊股接口明细（入参与返回字段）

> 实测日期：2026-09-09；标的：300476.SZ（胜宏科技，深市 market=33）为主，600519.SH（贵州茅台，沪市 market=17）用于市场对照。请求无鉴权头。字段类型/示例来自实测响应；**语义口径已按同花顺 App「智能诊股」页面逐项核验**，标注「未证实」的字段语义仍未确定。
> 资产范围：仅沪深 A 股股票（不含 ETF/指数/北交所）。

## 信封差异（重要）

| 组 | 示例端点 | 成功判据 | 顶层字段 |
|----|----------|----------|----------|
| 总评（eq open/api 面） | `get_score` | `status_code == 0` | `{status_code, data, status_msg:"success"}` |
| 财务（dq `stock_diagnosis/finance`） | `analysis` / `ablility` / `ablility_history` | `status_code == 0` | `{status_code, data, status_msg}` |
| 估值（dq `stock_diagnosis_valuation`） | `valuation_industry` | `status_code == 0` | `{status_code, status_message(键名!), data}` |
| 资金（dq `stock_diagnose_general/fund`） | `fund_summary` 等 | `status_code == 200` | `{status_code, data, status_msg}` |
| 公告研报（dq `stock_diagnose_general/message`） | `significant_message_analyze` | `status_code == 200` | `{status_code, data, status_msg}` |

---

## 1. 总评（composite_score）

- `GET https://eq.10jqka.com.cn/open/api/stock_diagnose_v2/composite_score/v1/get_score/{market}/{code}`
- 入参：仅路径。`market`（如 33）、`code`（如 300476）。实测 33/300476、17/600519 均 200。
- data 字段：

| 字段 | 类型 | 实测示例 | 说明 |
|------|------|----------|------|
| stock_code / stock_ths_code / market | str | `300476` / `300476.SZ` / `33` | ths_code 带交易所后缀 |
| date | str | `2026-09-09` | 北京日期 |
| stock_name / industry_name | str | 胜宏科技 / 元件 | |
| industry_code / industry_uid / industry_market | str | `881270` / `CNIS48881270` / `48` | 行业板块编码；industry_market 是行业指数的市场码（不同标的相同行业相同） |
| rank.score | dict | fund 2.0717 / tech 0.9 / valuation 1.5978375 / message 2.5 / finance 2.83333333 / delta_score 0.09327 / average 1.98057416 | 六个维度分 + 变化分 + 平均分（float），语义见下 |
| rank.industry_stock_total / market_stock_total | int | 63 / 5570 | 行业/全市场股票数 |
| rank.industry_rank / market_rank | int | 54 / 4179 | 排名 |
| anomaly_analysis[] | list[dict] | 见下 | 异动分析要点列表 |
| composite_diagnosis_description | dict | 见下 | 汇总文字与标签 |

- **`rank.score` 维度语义（满分均为 5、越高越好）**：
  - `fund`：资金强度评分，越高资金强度越高；与接口 4 `fund_score` 一致；每日更新。
  - `tech`：技术面评分，越高技术评价越高；每日更新。
  - `valuation`：估值评分，越高投资价值越高；每日更新。
  - `message`：消息面评分；**无消息刺激时常年为 2.5**；每日更新。
  - `finance`：财务（纸面基本面）评分；**唯一按财报披露周期更新**的维度。
  - `delta_score`：与较前值的变化分。
  - `average` = (fund+tech+valuation+message+finance)/5（两标的样本计算精确吻合；delta_score 不参与平均）。
- `composite_diagnosis_description`：`{tech_stock_property_comment / tech_stock_qr_comment / tech_stock_trend_comment: float(用途未证实), fund_org_shareholders_rate: float, fund_report_date: str YYYYMMDD, finance_overview: str(与接口 6 overview 措辞一致), valuation_tag: str, message_effect: str}`。`valuation_tag`/`message_effect` 为**文案拼接用字符串标签**（如"投资价值较低""消息面评分中性"），取值集未穷举。
- `anomaly_analysis[]`：`{analysis_id: str, analysis_content: str(长文,含行业/公司原因、免责声明), keyword_list: [str], anomaly_analysis_data_create_time: int(ms 时间戳)}`。属"异动分析"要点；与页面列表的窗口/条数对应关系未找到同源（本次会话内 3 条）。

---

## 2. 资金要点概述（fund_summary）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnose_general/fund/v1/fund_summary/get?stock_code=300476&stock_market=33`
- 入参：`stock_code`、`stock_market`。
- data 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| org_holding | dict | `{org_shareholders_rate, qfii_shareholders_rate, social_security_shareholders_rate: float(百分数), report_date: str YYYYMMDD}`，来自财报披露；是否可为 null 未证实 |
| rankings | dict\|null | **异动上榜（龙虎榜等）汇总**：`{lately_rankings_date: YYYYMMDD(上榜日期), lately_rankings_reason: [str](上榜原因), rankings_num: int(上榜次数), rankings_num_in_five_years: int(近 5 年上榜次数)}`。无上榜为 null（600519 实测 null） |
| holding_change | dict | 股东增减持（均来自财报披露口径）；`{manager/actual_ctrl/strong_increase_shareholdings_num: int(股), *_rate: float(百分数, 负=减持), net_increase_shareholdings_num/_rate, actual_ctrl_shareholdings_rate, stock_market: str}`。四类主体（manager/actual_ctrl/strong/net）的精确归属**未证实**；如 -2371000 = 减持 237.1 万股 |
| block_trades | dict | **大宗交易笔数**：`{trade_num: int(总笔数), premium_trade_num: int(溢价), flat_trade_num: int(平价), discount_trade_num: int(折价)}` |
| stock_code | str | 300476 |

- 口径提示：`*_rate` 为百分数（如 -0.2773 表示 -0.2773%）；`*_num` 单位股。

---

## 3. 资金评分历史（fund_history）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnose_general/fund/v1/fund_history/get?stock_code=300476&stock_market=33&period=one-month`
- 入参：`stock_code`、`stock_market`、`period`。实测 `one-month`（23 行，2026-08-10→09-09）、`one-year`（243 行，2025-09-09→2026-09-09）。其它取值未验证。
- data 为数组，每行：

| 字段 | 类型 | 示例 | 说明 |
|------|------|------|------|
| date | str | `20260909` | YYYYMMDD，仅交易日 |
| fund_score | str | `"4.5059"` | **字符串**小数，资金强度分（0–5），与接口 4 一致，盘中更新 |
| transactions | list | 见下 | 该日事件要点，无事件为空数组 |

- `transactions[]`：`{type: str(事件类型), label: str(标签文字), label_type: str, extra: dict}`。语义（经核验）：
  - `label_type`：**控制折线图标签颜色**（positive/negative，如红/绿），不是"利好/利空"判断。
  - `label`：**控制标签文字**，随事件类型变化（实测 `大`=大宗交易、`榜`=龙虎榜；用户核验样本还有 `减`=减持）。
  - `extra`：恒含 `rankings` / `holding_change` / `block_trades` 三键，按事件类型挂对应明细、其余为 null：大宗交易→`block_trades`；龙虎榜→`rankings`；减持/增持→`holding_change`。事件内联的 `rankings` 为简版 `{"rankings_reason": [str]}`，**字段集与接口 2 `fund_summary.rankings`（lately_rankings_date 等）不同**。
  - 实测事件枚举：一年样本 15 个事件点 = 大宗交易(14, label=大, positive 为主)/龙虎榜(1, label=榜, negative)；用户补充样本含 `type=减持`、`label=减`、`label_type=negative`。除这三种外是否还有其它类型未证实。

示例（减持事件，用户核验样本）：

```json
{"date":"20260105","fund_score":"3.5989","transactions":[{"extra":{"rankings":null,
  "holding_change":{"manager_increase_shareholdings_num":-370000,"strong_increase_shareholdings_rate":0,
    "manager_increase_shareholdings_rate":-0.1003,"net_increase_shareholdings_num":-370000,
    "actual_ctrl_increase_shareholdings_num":0,"net_increase_shareholdings_rate":-0.1003,
    "strong_increase_shareholdings_num":0,"actual_ctrl_shareholdings_rate":0},
  "block_trades":null},"label_type":"negative","label":"减","type":"减持"}]}
```

---

## 4. 资金评分综合（fund_comprehensive_evaluation）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnose_general/fund/v1/fund_comprehensive_evaluation/get?stock_code=300476&stock_market=33`
- 入参：`stock_code`、`stock_market`。
- data 字段（实测 300476）：

| 字段 | 类型 | 示例 | 说明 |
|------|------|------|------|
| fund_score | float | 2.0717 | 资金强度分（满分 5，盘中更新），与接口 1 `rank.score.fund` 一致 |
| fund_score_minus | float | 0.4283 | **资金评分与前值的对比**（比昨天上升/下降的变化量） |
| strength | str | `"3"` | 星级/强度（字符串）；**档位语义未证实** |
| fund_score_update_time | str | `20260909113335` | YYYYMMDDHHMMSS（盘中 11:33 样本 → 确认盘中可刷新） |
| stock_code / ths_code / stock_market | str | 300476 / 300476.SZ / 33 | |
| industry_name / industry_code / industry_uid / industry_count / industry_market | str/int | 元件 / 881270 / CNIS48881270 / 63 / 48 | 行业与股票数 |
| industry_rank | int | 50 | 行业内排名 |

- `status_msg` 回显请求参数：`查询资金综合评价数据成功! stock_code：【300476】，stock_market：【33】。`

---

## 5. 个股公告、研报要点（significant_message_analyze）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnose_general/message/v1/significant_message_analyze/get?ths_code=300476.SZ`
- 入参：`ths_code`（**带交易所后缀**，与其它接口用 `code`+`market` 不同）。`page_num` 参数存在但核验认为**等同无分页**——不同取值返回无差异，本次默认 15 条、`has_next_page=false`。
- data：`{data_list: [...], has_next_page: bool}`。
- `data_list[]` 字段：

| 字段 | 类型 | 实测枚举/示例 | 说明 |
|------|------|----------------|------|
| thsCode | str | 300476.SZ | |
| pubDate | str | `20260409` | YYYYMMDD |
| eventType | str | `yb` / `fhsz` | 事件类型缩写：yb=研报、fhsz=分红送转（与 msgCourierType 对应）；目前未见其它类型 |
| msgCourierType | str | `research` / `pub` | 消息载体：研报 / 公告 |
| labelProperty | str | 买入 / 增持 / 小利好 / 中性 | 情绪/评级标签：研报行=研报评级，公告行=利好档；枚举未穷举 |
| label | str(JSON数组) | `["买入","郑震湘","国盛证券"]`、`["普通分红率","无送转","实施方案"]` | 标签 JSON 字符串：研报=评级+分析师+机构；公告=事件标签 |
| announcementOverview | str | `普通分红率无送转方案实施` | 一句话摘要 |
| announcementOrResearchPoint | str | `0.1` | 数值化字符串；核验结论：**不重要**（无需解析） |
| isLimitExceeded | bool | True(研报)/False(公告) | 核验结论：**不重要**（疑似内容超长标记） |
| pubId | str | uuid | 事件 ID |
| content | str(JSON) | 见说明 | 内嵌 JSON 字符串：`research` 行 `noticeAbstract`(券商观点长文)/`title`/`url` 均有值；`pub` 行仅 `noticeAbstract`(公告摘要)有值，`title`/`url` 为 null |

---

## 6. 财务亮点与风险（finance/analysis）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnosis/finance/v1/analysis?code=300476&market=33`
- 入参：`code`、`market`。
- data 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| overview | str | 一句话总评（含总分、行业内排名/总数，如"…总评分为2.8分，元件行业内排名28/63…"）；与接口 1 `finance_overview` 措辞一致 |
| reports | [str] | 报告期枚举 `YYYY-Q`（如 2015-1 … 2026-2，共 45 期），文本顺序与接口 8 对齐 |
| highlight / risk | [dict] | `{name: str(维度), comment: str}`，如 highlight 营收/成长，risk 应收/存货周转/营运；comment 为含均值与结论的生成文本 |
| code / name / industry | str | 300476 / 胜宏科技 / `T0806` |

---

## 7. 财务评分（finance/ablility，接口拼写如此）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnosis/finance/v1/ablility?code=300476&market=33`
- 入参：`code`、`market`。
- data 字段（实测 300476）：

| 字段 | 类型 | 示例 | 说明 |
|------|------|------|------|
| diagnosis_abilities[] | list[dict] | 见下 | 六维能力评分 |
| share_comprehensive_score | str | `2.833333330` | 财务总分（字符串），与接口 1 `rank.score.finance` 一致 |
| last_score | str | `3.278688535` | **上年同期总分**（字符串） |
| rank | str | `28` | 行业内总排名（字符串） |
| total | str | `63` | 行业内公司数（字符串，随行业口径变化） |
| keyword | str | 尚可 | 定性总评标签；**阈值无需关注** |
| industry / industry_name / industry_quote_code / industry_quote_market / industry_uid | str | T0806 / 元件 / 881270 / 48 / CNIS48881270 | corr_code=`48:881270` 同义 |
| industry_category | str | normal | 分类（样本） |
| products | [str] | ["PCB制造"] | 主营产品 |
| prosperity_tag | null/str | null | 景气标签（样本为 null） |
| code / name / market | str | 300476 / 胜宏科技 / 33 | |

- `diagnosis_abilities[]`：`{diagnosis_ability_id: profit/growth/operate/cash/pay/asset_quality, diagnosis_ability_name: 盈利能力/成长能力/营运能力/现金流/偿债能力/资产质量, current_score: str, last_score: str(上年同期), industry_average: str, rank: str, keyword: str(优秀/出众/尚可/一般/较弱/不佳)}`。**分数与排名均为字符串**。

---

## 8. 财务评分历史（finance/ablility_history）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnosis/finance/v1/ablility_history?code=300476&market=33&ability_id=asset_quality`
- 入参：`code`、`market`、`ability_id`。枚举（抓包备注 + 实测）：`asset_quality`(资产质量) / `cash`(现金流) / `growth`(成长能力) / `operate`(营运能力) / `pay`(偿债能力) / `profit`(盈利能力) / `final_score`(总分)。
- data 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| ability_ids | [str] | 服务端返回的能力全集（实测 7 项，含 final_score） |
| current_ability_details | [dict] | 按报告期展开，45 行（2015-2 … 2026-2，与接口 6 reports 对齐）；`ability_id` 决定其中 `score` 代表的维度 |
| industry_name / name | str | 元件 / 胜宏科技 |

- `current_ability_details[]`：`{score: str(所选 ability 当季分), final_score: str(当季财务总分), report: {date: str YYYY-MM-DD(报告期末), report: str YYYY-Q, report_name: str(如"2015中报")}, rank: str, total: str(当季口径行业总数, 示例 69), comment: str(含排名与均值评述), percent: str(0..1 分位)}`。`percent` 语义经核验为**分位**（与 ablility 页展示的"领先"比例对应）。
- 口径提示：`rank`/`total`/comment 里的行业随报告期不同（历史期可能归属旧行业口径，如早期为"半导体"、当前为"元件"），与当前 industry_name 不一致属正常；分数/排名均为字符串。

---

## 9. 估值分位分析（valuation_industry）

- `GET https://dq.10jqka.com.cn/fuyao/stock_diagnosis_valuation/valuation/v1/valuation_industry?code=300476&market=33&index=pb&period=1`
- 入参：`code`、`market`、`index`（枚举 `pb`/`pe`/`pof`/`ps`；**`pof` = 市现率**。口径：除市净率外，智能诊股上显示的均为 **TTM** 口径，即 pe/pof/ps 为 TTM、pb 非 TTM）、`period`（枚举 `1`/`3`/`5`/`10`，单位为年；period=1 实测约 245 个交易日）。
- 信封顶层键为 `status_message`（空串），成功判据 `status_code == 0`。
- data 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| market / code | str | 33 / 300476 |
| performance_list | dict[str, float] | `{ "YYYY-MM-DD": float(0..1) }`，**低于自身历史估值的分位**：如 0.98347 = 当前估值低于自身 98.35% 的历史估值（值越大代表当前相对自身历史越"便宜"）。键为回溯窗口内交易日 |
| value_list | dict[str, {industry, stock}] | `{ "YYYY-MM-DD": {industry: float(行业估值), stock: float(个股估值)} }`，值类型随 `index` 变化（index=pb 时为 PB 数值）。日期集合与 performance_list 基本一致 |

- 其它：窗口内每天一个点，period 越大体积线性放大（period=1 已约 245 点 × 两个 map）；个别日期 `stock == industry` 属**巧合**（该区间两者数值确实接近），非回填标记。

---

## 常见问题

- **不同接口 code 传参不一致**：资金/财务/估值用 `code`(+`market`)，公告研报用 `ths_code`（带 .SZ/.SH 后缀）。
- **分数类型不一致**：复合分/历史分多为 `str`（如 `"4.5059"`、`"2.833333330"`），总评/估值 `rank.score`、`fund_score` 为 float，解析时按实际类型处理，勿统一 float()。
- **评分刻度与更新节奏**：总评六维满分均为 5、越高越好；finance 按财报披露周期更新，fund/tech/valuation/message 每日更新（fund_score 盘中刷新）。行业排名/总数随报告期与行业重分类变化，跨期比较按 `report.report`/`reports` 对齐。
