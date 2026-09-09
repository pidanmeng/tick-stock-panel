# ruff: noqa: RUF002, RUF003
"""service 单测：标的过滤、配置幂等、快照落盘 merge/clear、进度、prefs。"""
import asyncio
from pathlib import Path

import polars as pl

from app.custom.ths_diagnose import service

SAMPLE_SCORE = {
    "date": "2026-09-09",
    "stock_name": "示例",
    "industry_name": "元件",
    "industry_code": "881270",
    "rank": {
        "score": {"fund": 2.0, "tech": 1.0, "valuation": 1.5, "message": 2.5,
                  "finance": "2.8", "delta_score": 0.1, "average": 2.0},
        "industry_rank": 10, "market_rank": 100,
        "industry_stock_total": 63, "market_stock_total": 5570,
    },
}


def _write_instruments(data_dir: Path) -> None:
    df = pl.DataFrame(
        {
            "symbol": ["600519.SH", "300476.SZ", "000858.SZ", "510300.SH", "000300.SH"],
            "type": ["stock", "stock", "stock", "etf", "index"],
            "exchange": ["SH", "SZ", "SZ", "SH", "SH"],
        }
    )
    (data_dir / "instruments").mkdir(parents=True, exist_ok=True)
    df.write_parquet(data_dir / "instruments" / "instruments.parquet")


class FakeClient:
    """可控假客户端：get_score 返回示例，可注入失败（按裸 code）。"""

    def __init__(self, fail_codes=(), fail_finance_codes=()) -> None:
        self.fail = set(fail_codes)
        self.fail_finance = set(fail_finance_codes)
        self.calls: list[tuple[str, str, str]] = []

    async def get_score(self, market, code):
        self.calls.append(("score", str(market), code))
        if code in self.fail:
            raise RuntimeError("boom")
        return dict(SAMPLE_SCORE)

    async def finance_ablility(self, market, code):
        self.calls.append(("finance", str(market), code))
        if code in self.fail_finance:
            raise RuntimeError("finance boom")
        return {"share_comprehensive_score": "2.8", "last_score": "3.0",
                "diagnosis_abilities": []}

    async def fund_comprehensive(self, market, code):
        self.calls.append(("fund", str(market), code))
        return {"fund_score": 2.0, "fund_score_minus": 0.2}


def test_split_symbol_and_fail_closed_without_instruments(tmp_path):
    assert service.split_symbol("300476.SZ") == ("300476", 33)
    assert service.split_symbol("600519.SH") == ("600519", 17)
    assert service.split_symbol("510300.SH") == ("510300", 17)
    assert service.split_symbol("300476") is None
    assert service.split_symbol("abc.SH") is None
    assert service.split_symbol("688012.SH") == ("688012", 17)

    # instruments 维表缺失 → fail-closed
    ok, skipped = service.filter_stock_symbols(["600519.SH"], tmp_path)
    assert ok == []
    assert skipped and "维表" in skipped[0]


def test_filter_stock_symbols_uses_instrument_type(tmp_path):
    _write_instruments(tmp_path)
    ok, skipped = service.filter_stock_symbols(
        ["600519.SH", "300476.SZ", "510300.SH", "000300.SH", "000001.SZ"], tmp_path
    )
    assert ok == ["600519.SH", "300476.SZ"]
    assert len(skipped) == 3  # ETF / 指数 / 非维表


def test_ensure_config_idempotent(tmp_path):
    cfg1 = service.ensure_config(tmp_path)
    cfg2 = service.ensure_config(tmp_path)
    assert cfg1.id == service.CONFIG_ID == cfg2.id
    assert cfg1.label == cfg2.label == service.CONFIG_LABEL
    assert cfg1.mode == "snapshot"
    assert (tmp_path / "ext_data" / service.CONFIG_ID / "config.json").exists()
    assert {f.name for f in cfg1.fields} >= {
        "symbol", "score_fund", "finance_prev", "fund_chg", "abl_asset",
    }


def test_pull_snapshot_writes_merge_and_clear(tmp_path):
    _write_instruments(tmp_path)
    client = FakeClient()
    symbols = ["600519.SH", "300476.SZ"]

    asyncio.run(
        service.pull_snapshot(tmp_path, symbols, include_trend=True, client=client, cap=10)
    )

    rows, date = service.read_snapshot(tmp_path)
    assert date == "2026-09-09"
    assert {r["symbol"] for r in rows} == set(symbols)
    assert rows[0]["finance_prev"] == 3.0
    assert rows[0]["fund_chg"] == 0.2
    # 请求形态：每只 3 次（score + finance + fund）
    assert len(client.calls) == 6

    # 分批累积：新增标的（keep-last 合并）
    asyncio.run(
        service.pull_snapshot(tmp_path, ["600519.SH", "000858.SZ"], client=client, cap=10)
    )
    rows, _ = service.read_snapshot(tmp_path)
    assert len(rows) == 3

    # 清空保留 config
    service.clear_snapshot(tmp_path)
    meta = service.snapshot_meta(tmp_path)
    assert meta["rows"] == 0 and meta["configured"] is True


def test_pull_failures_recorded_and_skip_ok(tmp_path):
    _write_instruments(tmp_path)
    client = FakeClient(fail_codes=["300476"], fail_finance_codes=["600519"])
    symbols = ["600519.SH", "300476.SZ"]

    asyncio.run(
        service.pull_snapshot(tmp_path, symbols, include_trend=True, client=client, cap=10)
    )

    rows, _ = service.read_snapshot(tmp_path)
    # 300476 全挂不进表；600519 总评成功但财务趋势失败仍保留行
    assert [r["symbol"] for r in rows] == ["600519.SH"]
    prog = service.progress_snapshot()
    assert prog["running"] is False
    assert prog["failed"] == 1
    assert prog["failed_symbols"] == ["300476.SZ"]
    assert "600519.SH" in prog["warnings"]
    assert rows[0]["finance_total"] is None  # 趋势缺失不填 0


def test_all_stock_symbols_returns_stocks_only(tmp_path):
    _write_instruments(tmp_path)
    all_ = service.all_stock_symbols(tmp_path)
    assert all_ == sorted(["000858.SZ", "300476.SZ", "600519.SH"])


def test_prefs_roundtrip_and_patch(tmp_path):
    service.save_prefs(tmp_path, {"universe": {"type": "symbols", "symbols": ["600519.SH"]}})
    prefs = service.load_prefs(tmp_path)
    assert prefs["universe"]["symbols"] == ["600519.SH"]

    service.save_prefs(tmp_path, {"include_trend": False})
    prefs = service.load_prefs(tmp_path)
    assert prefs["include_trend"] is False
    assert "600519.SH" in prefs["universe"]["symbols"]

    service.save_prefs(tmp_path, {"universe": None})
    prefs = service.load_prefs(tmp_path)
    assert "universe" not in prefs
