# ruff: noqa: RUF002, RUF003
"""parsers 单测：双信封外的规范化、str/float 分数、缺字段 → None。"""
import json

from app.custom.ths_diagnose.parsers import (
    finance_section,
    flatten_summary,
    float_or_none,
    fund_section,
    int_or_none,
    message_section,
    summary_section,
    to_snapshot_row,
    valuation_section,
)

# 参考 references/api.md 实测样本（300476.SZ 胜宏科技，2026-09-09）
SUMMARY = {
    "stock_code": "300476",
    "stock_ths_code": "300476.SZ",
    "market": "33",
    "date": "2026-09-09",
    "stock_name": "胜宏科技",
    "industry_name": "元件",
    "industry_code": "881270",
    "rank": {
        "score": {
            "fund": 2.0717,
            "tech": 0.9,
            "valuation": 1.5978375,
            "message": 2.5,
            "finance": "2.833333330",
            "delta_score": 0.09327,
            "average": 1.98057416,
        },
        "industry_stock_total": 63,
        "market_stock_total": 5570,
        "industry_rank": 54,
        "market_rank": 4179,
    },
    "anomaly_analysis": [
        {"analysis_id": "a1", "analysis_content": "长文要点", "keyword_list": ["x"]}
    ],
    "composite_diagnosis_description": {
        "finance_overview": "财务总评文字",
        "valuation_tag": "投资价值较低",
        "message_effect": "消息面评分中性",
    },
}

ABLILITY = {
    "share_comprehensive_score": "2.833333330",
    "last_score": "3.278688535",
    "rank": "28",
    "total": "63",
    "keyword": "尚可",
    "industry_name": "元件",
    "diagnosis_abilities": [
        {"diagnosis_ability_id": "profit", "current_score": "2.5", "last_score": "3.0",
         "industry_average": "2.8", "rank": "40", "keyword": "一般"},
        {"diagnosis_ability_id": "cash", "current_score": "3.4", "last_score": "3.0",
         "industry_average": "3.0", "rank": "10", "keyword": "出众"},
    ],
}

FUND = {"fund_score": 2.0717, "fund_score_minus": 0.4283, "strength": "3"}


def test_float_or_none_normalizes_string_and_scalar():
    assert float_or_none("4.5059") == 4.5059
    assert float_or_none("2.833333330") == 2.83333333
    assert float_or_none(2.0717) == 2.0717
    assert float_or_none(3) == 3.0
    assert float_or_none(None) is None
    assert float_or_none("") is None
    assert float_or_none("   ") is None
    assert float_or_none("abc") is None
    assert float_or_none(False) is None
    assert float_or_none(True) is None


def test_int_or_none():
    assert int_or_none("28") == 28
    assert int_or_none(54) == 54
    assert int_or_none(None) is None
    assert int_or_none("2.7") == 2


def test_flatten_summary_and_snapshot_row():
    flat = flatten_summary(SUMMARY)
    assert flat["name"] == "胜宏科技"
    assert flat["industry_name"] == "元件"
    assert flat["score_fund"] == 2.0717
    # str 分数统一转 float
    assert flat["score_finance"] == 2.83333333
    assert flat["score_average"] == 1.98057416
    assert flat["rank_industry"] == 54
    assert flat["total_market"] == 5570

    row = to_snapshot_row("300476.SZ", SUMMARY)
    assert row["symbol"] == "300476.SZ"
    assert row["code"] == "300476"
    # 未传 finance/fund 时不臆造
    assert row["finance_total"] is None
    assert row["fund_chg"] is None
    assert row["abl_profit"] is None

    row2 = to_snapshot_row("300476.SZ", SUMMARY, ABLILITY, FUND)
    assert row2["finance_total"] == 2.83333333
    assert row2["finance_prev"] == 3.278688535
    assert row2["abl_profit"] == 2.5
    assert row2["abl_cash"] == 3.4
    assert row2["fund_chg"] == 0.4283
    assert row2["snapshot_date"] == "2026-09-09"


def test_summary_section_shape():
    s = summary_section(SUMMARY)
    assert s["scores"]["score_finance"] == 2.83333333
    assert s["scores"]["score_fund"] == 2.0717
    assert s["industry_rank"] == 54
    assert s["anomaly"][0]["content"] == "长文要点"
    assert s["finance_overview"] == "财务总评文字"


def test_finance_section_with_history():
    analysis = {"overview": "总评2.8分", "highlight": [{"name": "成长", "comment": "x"}],
                "risk": [{"name": "应收", "comment": "y"}]}
    history = {"current_ability_details": [
        {"score": "3.1", "final_score": "2.8", "report": {"report": "2026-2", "date": "2026-06-30"},
         "rank": "10", "total": "63", "percent": "0.8", "comment": "c"},
    ]}
    s = finance_section(ABLILITY, analysis, history)
    assert s["share"] == 2.83333333
    assert s["last"] == 3.278688535
    assert len(s["abilities"]) == 2
    assert s["abilities"][0]["current"] == 2.5
    assert s["highlight"][0]["name"] == "成长"
    assert s["history"][0]["score"] == 3.1
    assert s["history"][0]["report"] == "2026-2"


def test_fund_section_with_history_events():
    fund_hist = [
        {"date": "20260105", "fund_score": "3.5989",
         "transactions": [{"type": "减持", "label": "减", "label_type": "negative"}]},
        {"date": "20260106", "fund_score": "3.6", "transactions": []},
    ]
    s = fund_section(FUND, summary={"rankings": None}, history=fund_hist)
    assert s["fund_score"] == 2.0717
    assert s["fund_score_minus"] == 0.4283
    assert s["fund_summary"] == {
        "org_holding": None, "rankings": None,
        "holding_change": None, "block_trades": None,
    }
    assert s["history"][0]["fund_score"] == 3.5989
    assert s["history"][0]["events"][0]["label"] == "减"
    assert s["history"][1]["events"] == []


def test_message_section_parses_inner_json():
    data = {
        "has_next_page": False,
        "data_list": [
            {"pubDate": "20260409", "eventType": "yb", "msgCourierType": "research",
             "labelProperty": "买入", "label": json.dumps(["买入", "分析师", "券商"], ensure_ascii=False),
             "announcementOverview": "要点", "content": json.dumps(
                 {"noticeAbstract": "券商观点长文", "title": "研报标题", "url": "https://x"})},
            {"pubDate": "20260408", "eventType": "fhsz", "content": json.dumps(
                 {"noticeAbstract": "公告摘要", "title": None, "url": None})},
        ],
    }
    s = message_section(data)
    assert len(s["rows"]) == 2
    assert s["rows"][0]["url"] == "https://x"
    assert s["rows"][0]["label_property"] == "买入"
    assert s["rows"][1]["title"] is None
    assert s["has_next_page"] is False


def test_valuation_section_points():
    data = {
        "performance_list": {"2026-09-08": 0.98, "2026-09-09": 0.95},
        "value_list": {
            "2026-09-08": {"industry": 3.2, "stock": 2.9},
            "2026-09-09": {"industry": 3.1, "stock": 2.8},
        },
    }
    s = valuation_section(data)
    assert len(s["points"]) == 2
    assert s["points"][0]["date"] == "2026-09-08"
    assert s["points"][0]["pct"] == 0.98
    assert s["points"][1]["stock"] == 2.8
