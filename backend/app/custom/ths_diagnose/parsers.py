# ruff: noqa: RUF002, RUF003
"""同花顺诊股接口响应 → 规范化结构 / 快照行。

分数类型不统一（重要）：rank.score 等为 float，复合分/历史分多为 str
（如 "4.5059"、"2.833333330"），统一走 float_or_none；缺字段一律置 None，
不臆造、不填 0。
"""
from __future__ import annotations

from typing import Any

ABILITY_IDS = ("profit", "growth", "operate", "cash", "pay", "asset_quality")
VALID_VALUATION_INDEX = ("pb", "pe", "pof", "ps")
VALID_VALUATION_PERIOD = ("1", "3", "5", "10")
FUND_PERIODS = ("one-month", "one-year")

_ABILITY_ABBR = {
    "profit": "abl_profit",
    "growth": "abl_growth",
    "operate": "abl_operate",
    "cash": "abl_cash",
    "pay": "abl_pay",
    "asset_quality": "abl_asset",
}


def float_or_none(v: Any) -> float | None:
    """str/float/int → float，非法/None → None。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def int_or_none(v: Any) -> int | None:
    f = float_or_none(v)
    if f is None:
        return None
    return int(f)


def _score_map(rank: dict) -> dict[str, float | None]:
    """总评六维分（rank.score）。"""
    scores = rank.get("score") or {}
    return {
        "score_fund": float_or_none(scores.get("fund")),
        "score_tech": float_or_none(scores.get("tech")),
        "score_valuation": float_or_none(scores.get("valuation")),
        "score_message": float_or_none(scores.get("message")),
        "score_finance": float_or_none(scores.get("finance")),
        "score_average": float_or_none(scores.get("average")),
        "score_delta": float_or_none(scores.get("delta_score")),
    }


def flatten_summary(data: dict) -> dict:
    """get_score data → 快照行基础字段（不含 finance/fund 趋势列）。"""
    rank = data.get("rank") or {}
    row: dict[str, Any] = {
        "name": data.get("stock_name"),
        "industry_name": data.get("industry_name"),
        "industry_code": data.get("industry_code"),
        "snapshot_date": data.get("date"),
        "rank_industry": int_or_none(rank.get("industry_rank")),
        "rank_market": int_or_none(rank.get("market_rank")),
        "total_industry": int_or_none(rank.get("industry_stock_total")),
        "total_market": int_or_none(rank.get("market_stock_total")),
    }
    row.update(_score_map(rank))
    return row


def _ability_columns(data: dict) -> dict:
    """finance/ablility data → 六能力当期分列 + 总分/上年同期。"""
    out: dict[str, Any] = {
        "finance_total": float_or_none(data.get("share_comprehensive_score")),
        "finance_prev": float_or_none(data.get("last_score")),
    }
    for item in data.get("diagnosis_abilities") or []:
        abbr = _ABILITY_ABBR.get(item.get("diagnosis_ability_id") or "")
        if abbr:
            out[abbr] = float_or_none(item.get("current_score"))
    return out


def to_snapshot_row(
    symbol: str,
    summary: dict,
    finance: dict | None = None,
    fund: dict | None = None,
) -> dict:
    """组合 get_score + ablility + fund_comprehensive 成一行快照数据。"""
    code = symbol.split(".", 1)[0]
    row: dict[str, Any] = {"symbol": symbol, "code": code}
    row.update(flatten_summary(summary))
    # 趋势列缺省置 None（finance/fund 未拉取或失败时不臆造、不填 0）
    row["fund_chg"] = None
    row["finance_total"] = None
    row["finance_prev"] = None
    for abbr in _ABILITY_ABBR.values():
        row[abbr] = None
    if finance:
        row.update(_ability_columns(finance))
    if fund:
        row["fund_chg"] = float_or_none(fund.get("fund_score_minus"))
    return row


# ----------------------------------------------------------------------
# 详情弹窗分区解析
# ----------------------------------------------------------------------
def summary_section(data: dict) -> dict:
    rank = data.get("rank") or {}
    comp = data.get("composite_diagnosis_description") or {}
    return {
        "date": data.get("date"),
        "name": data.get("stock_name"),
        "ths_code": data.get("stock_ths_code"),
        "industry_name": data.get("industry_name"),
        "industry_code": data.get("industry_code"),
        "industry_rank": int_or_none(rank.get("industry_rank")),
        "market_rank": int_or_none(rank.get("market_rank")),
        "industry_stock_total": int_or_none(rank.get("industry_stock_total")),
        "market_stock_total": int_or_none(rank.get("market_stock_total")),
        "scores": _score_map(rank),
        "anomaly": [
            {"content": a.get("analysis_content"), "keywords": a.get("keyword_list") or []}
            for a in (data.get("anomaly_analysis") or [])
        ],
        "finance_overview": comp.get("finance_overview"),
        "valuation_tag": comp.get("valuation_tag"),
        "message_effect": comp.get("message_effect"),
    }


def finance_section(
    ablility: dict,
    analysis: dict | None = None,
    history: dict | None = None,
) -> dict:
    abilities = []
    for item in ablility.get("diagnosis_abilities") or []:
        abilities.append(
            {
                "id": item.get("diagnosis_ability_id"),
                "name": item.get("diagnosis_ability_name"),
                "current": float_or_none(item.get("current_score")),
                "last": float_or_none(item.get("last_score")),
                "industry_average": float_or_none(item.get("industry_average")),
                "rank": int_or_none(item.get("rank")),
                "keyword": item.get("keyword"),
            }
        )
    out: dict[str, Any] = {
        "share": float_or_none(ablility.get("share_comprehensive_score")),
        "last": float_or_none(ablility.get("last_score")),
        "rank": int_or_none(ablility.get("rank")),
        "total": int_or_none(ablility.get("total")),
        "keyword": ablility.get("keyword"),
        "industry_name": ablility.get("industry_name"),
        "abilities": abilities,
        "highlight": [],
        "risk": [],
    }
    if analysis:
        out["overview"] = analysis.get("overview")
        out["highlight"] = [
            {"name": h.get("name"), "comment": h.get("comment")}
            for h in (analysis.get("highlight") or [])
        ]
        out["risk"] = [
            {"name": r.get("name"), "comment": r.get("comment")}
            for r in (analysis.get("risk") or [])
        ]
    if history:
        out["history"] = [
            {
                "report": (it.get("report") or {}).get("report"),
                "report_date": (it.get("report") or {}).get("date"),
                "score": float_or_none(it.get("score")),
                "final_score": float_or_none(it.get("final_score")),
                "percent": float_or_none(it.get("percent")),
                "comment": it.get("comment"),
            }
            for it in (history.get("current_ability_details") or [])
        ]
    return out


def fund_section(
    comprehensive: dict,
    summary: dict | None = None,
    history: list | None = None,
) -> dict:
    out: dict[str, Any] = {
        "fund_score": float_or_none(comprehensive.get("fund_score")),
        "fund_score_minus": float_or_none(comprehensive.get("fund_score_minus")),
        "strength": comprehensive.get("strength"),
        "fund_score_update_time": comprehensive.get("fund_score_update_time"),
        "industry_rank": int_or_none(comprehensive.get("industry_rank")),
        "fund_summary": None,
        "history": [],
    }
    if summary:
        out["fund_summary"] = {
            "org_holding": summary.get("org_holding"),
            "rankings": summary.get("rankings"),
            "holding_change": summary.get("holding_change"),
            "block_trades": summary.get("block_trades"),
        }
    out["history"] = [
        {
            "date": it.get("date"),
            "fund_score": float_or_none(it.get("fund_score")),
            "events": [
                {
                    "type": ev.get("type"),
                    "label": ev.get("label"),
                    "label_type": ev.get("label_type"),
                }
                for ev in (it.get("transactions") or [])
            ],
        }
        for it in (history or [])
    ]
    return out


def message_section(data: dict) -> dict:
    rows = []
    for it in data.get("data_list") or []:
        content: dict = {}
        raw = it.get("content")
        if isinstance(raw, str):
            try:
                import json

                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    content = parsed
            except ValueError:
                content = {}
        elif isinstance(raw, dict):
            content = raw
        rows.append(
            {
                "pub_date": it.get("pubDate"),
                "event_type": it.get("eventType"),
                "carrier": it.get("msgCourierType"),
                "label_property": it.get("labelProperty"),
                "labels": it.get("label"),
                "overview": it.get("announcementOverview"),
                "abstract": content.get("noticeAbstract"),
                "title": content.get("title"),
                "url": content.get("url"),
            }
        )
    return {"rows": rows, "has_next_page": bool(data.get("has_next_page"))}


def valuation_section(data: dict) -> dict:
    perf = data.get("performance_list") or {}
    values = data.get("value_list") or {}
    dates = sorted(k for k in perf if isinstance(perf.get(k), (int, float)))
    points = []
    for d in dates:
        v = values.get(d) or {}
        points.append(
            {
                "date": d,
                "pct": float(perf[d]) if perf[d] is not None else None,
                "stock": float_or_none(v.get("stock") if isinstance(v, dict) else None),
                "industry": float_or_none(v.get("industry") if isinstance(v, dict) else None),
            }
        )
    return {"points": points}
