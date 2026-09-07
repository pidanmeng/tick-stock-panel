"""fuyao 插件 minute (quota-h single_kline) 契约测试 — 不依赖真实网络 / API Key。

覆盖 (CONTRIBUTING §9):
1. quota 响应解析: 信封/位置数组 → 行; 行宽不一致/非 0 status_code → 抛 QuotaError; 空返回 []
2. 时区/单位: time_ms +8h → 北京墙钟 naive; volume 股→手 floor(/100), 指数透传
3. symbol → (code, market) 码表分类 (沪/深股票、科创、ETF、指数、北交; 未覆盖沪指 → None)
4. provider.get_minute: canonical 列、窗口过滤、未映射标的 fail-closed 跳过、多标的并发拉取
5. 能力声明: config.datasets 含 minute (全量分钟未接), minute_history_days=40 浅源
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from app.plugins.fuyao import quota_kline as qk
from app.plugins.fuyao.provider import FuyaoProvider
from app.plugins.fuyao.quota_kline import QuotaError

# 时间换算锚点 (实测抓包): 15:00:00 收盘墙钟与 2026-09-04 00:00:00
_TS_1500 = 1_788_418_800_000
_TS_DAILY = 1_788_451_200_000


def _payload(values: list[list]) -> dict:
    return {
        "status_code": 0,
        "status_msg": "ok",
        "data": {
            "quote_data": [{
                "market": "17", "code": "688825", "delay": False,
                "data_fields": ["1", "7", "8", "9", "11", "13", "19"], "value": values,
            }]
        },
    }


class _FakeQuota:
    """可注入 _quota_client 的假客户端 (记录调用, 返回固定 bar)。"""

    def __init__(self, bars: list[dict] | None = None) -> None:
        self.calls: list[tuple[str, str, int]] = []
        self.bars = bars or [{"time_ms": _TS_1500, "open": 54.49, "high": 54.5,
                              "low": 54.44, "close": 54.45,
                              "volume": 330309.0, "amount": 17991300.0}]

    def minute_kline(self, code: str, market: str, begin_bars: int = 400):
        self.calls.append((code, market, begin_bars))
        return self.bars

    def close(self) -> None:
        pass


def _provider_with(fake: _FakeQuota) -> FuyaoProvider:
    p = FuyaoProvider()
    p._quota_client = fake
    return p


# ---- 1. quota 响应解析 ----
class TestQuotaParse:
    def test_real_row_parses(self) -> None:
        rows = qk._parse_payload(_payload([[1788403920000, 54.49, 54.5, 54.44, 54.45, 330309, 17991300]]))
        assert rows == [{"time_ms": 1788403920000, "open": 54.49, "high": 54.5,
                         "low": 54.44, "close": 54.45, "volume": 330309.0, "amount": 17991300.0}]

    def test_error_status_raises(self) -> None:
        with pytest.raises(QuotaError, match="unknown market id"):
            qk._parse_payload({"status_code": -3, "status_msg": "unknown market id！", "data": None})

    def test_width_mismatch_raises(self) -> None:
        with pytest.raises(QuotaError, match="行宽"):
            qk._parse_payload(_payload([[1788403920000, 54.49]]))

    def test_empty_payload(self) -> None:
        assert qk._parse_payload({"status_code": 0, "data": None}) == []


# ---- 2. 时区 / 单位 / 根数估算 ----
class TestQuotaHelpers:
    def test_bj_wallclock(self) -> None:
        assert qk.bj_datetime(_TS_1500) == datetime(2026, 9, 3, 15, 0, 0)
        assert qk.bj_datetime(_TS_DAILY) == datetime(2026, 9, 4, 0, 0, 0)

    def test_scale_volume_by_kind(self) -> None:
        assert qk.scale_volume(330309.0, "stock") == 3303
        assert qk.scale_volume(498182960.0, "etf") == 4981829
        assert qk.scale_volume(49699019000.0, "index") == 49699019000.0
        assert qk.scale_volume(None, "stock") is None

    def test_needed_bars(self) -> None:
        assert qk.needed_minute_bars(None, None) == 400
        # 同日全天窗口 (2026-09-03 周四): 1 个工作日 *240 + 240 缓冲 = 480 根。
        # 交易日口径 (非自然日分钟) — 常见增量请求须压在网关 ~950 根阈值内,
        # 避免整段留存倒出 (见 quota_kline 模块 docstring 实测语义)。
        win = qk.needed_minute_bars(
            datetime(2026, 9, 3), datetime(2026, 9, 3, 23, 59, 59)
        )
        assert win == 480

    def test_needed_bars_weekend_crossing(self) -> None:
        # 周五收盘 → 周一收盘 (隔夜+周末增量): 周五/周一 2 个工作日 → 720 根
        v = qk.needed_minute_bars(datetime(2026, 9, 4, 15), datetime(2026, 9, 7, 15))
        assert v == 720

    def test_needed_bars_weekend_only_clamps_to_min(self) -> None:
        # 纯周末窗口无交易日 → 估值 240 < 下限 → 收敛到 400
        assert qk.needed_minute_bars(datetime(2026, 9, 5), datetime(2026, 9, 6)) == 400

    def test_needed_bars_large_gap_keeps_retention_dump(self) -> None:
        # 真实缺口超过 ~4 个交易日: 估值 ≥1000, 允许整段留存返回 (数据不丢)。
        # 2026-09-01(周二) → 2026-09-11(周五) = 9 个工作日 → 2400 根
        assert qk.needed_minute_bars(datetime(2026, 9, 1), datetime(2026, 9, 11)) == 2400
        # 超长窗口封顶 30000 (服务端留存只有 ~2 个月, 请求再多返回量不变)
        assert qk.needed_minute_bars(
            datetime(2026, 1, 1), datetime(2026, 12, 31)
        ) == 30_000


# ---- 3. symbol → (code, market, kind) ----
class TestClassify:
    def test_mapping(self) -> None:
        cases = {
            "600000.SH": ("600000", "17", "stock"),
            "688825.SH": ("688825", "17", "stock"),
            "000001.SZ": ("000001", "33", "stock"),
            "300750.SZ": ("300750", "33", "stock"),
            "510300.SH": ("510300", "20", "etf"),
            "159915.SZ": ("159915", "36", "etf"),
            "000001.SH": ("1A0001", "16", "index"),
            "000300.SH": ("1B0300", "16", "index"),
            "000680.SH": ("1B0680", "16", "index"),  # 科创综指 (用户确认 1B0680/16)
            "399001.SZ": ("399001", "32", "index"),
            "920999.BJ": ("920999", "151", "stock"),
        }
        for sym, expected in cases.items():
            assert qk.classify_symbol(sym) == expected, sym

    def test_unmapped_fail_closed(self) -> None:
        assert qk.classify_symbol("000016.SH") is None
        assert qk.classify_symbol("600000") is None
        assert qk.classify_symbol("") is None


# ---- 4/5. provider.get_minute 集成 ----
class TestFuyaoMinuteProvider:
    def test_capability_declaration(self) -> None:
        p = FuyaoProvider()
        assert "minute" in p.config.datasets
        assert "full_minute" not in p.config.datasets
        assert getattr(p, "minute_history_days", None) == 40

    def test_minute_normalized_row(self) -> None:
        fake = _FakeQuota()
        p = _provider_with(fake)
        df = p.get_minute(
            ["688825.SH"], datetime(2026, 9, 3), datetime(2026, 9, 3, 23, 59, 59)
        )
        row = df.to_dicts()[0]
        assert fake.calls[0][0] == "688825" and fake.calls[0][1] == "17"
        assert row["symbol"] == "688825.SH"
        assert str(row["datetime"]) == "2026-09-03 15:00:00"  # naive 北京墙钟
        assert df.schema["datetime"] == pl.Datetime("us")
        assert row["volume"] == 3303  # 股 → 手
        assert row["amount"] == 17991300.0

    def test_minute_window_filter(self) -> None:
        p = _provider_with(_FakeQuota())
        # 窗口不含 15:00 所在日 → 空
        df = p.get_minute(["688825.SH"], datetime(2026, 9, 1), datetime(2026, 9, 2))
        assert df.is_empty()

    def test_minute_aware_window_normalized(self) -> None:
        """fetch_minute_single 传带 CN_TZ 的 aware 窗口 → 需剥 tz 后再比较, 不得抛错/回退。"""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Shanghai")
        fake = _FakeQuota()
        p = _provider_with(fake)
        df = p.get_minute(
            ["688825.SH"],
            datetime(2026, 9, 3, 0, 0, tzinfo=tz),
            datetime(2026, 9, 3, 23, 59, 59, tzinfo=tz),
        )
        assert df.height == 1  # 不再 TypeError → 空/回退
        assert str(df.to_dicts()[0]["datetime"]) == "2026-09-03 15:00:00"

    def test_minute_multi_symbol_concurrent(self) -> None:
        fake = _FakeQuota()
        p = _provider_with(fake)
        df = p.get_minute(
            ["600000.SH", "000001.SZ", "510300.SH"],
            datetime(2026, 9, 3), datetime(2026, 9, 3, 23, 59, 59),
        )
        assert df.height == 3
        assert {r["symbol"] for r in df.to_dicts()} == {"600000.SH", "000001.SZ", "510300.SH"}
        assert len(fake.calls) == 3
        markets = {m for _, m, _ in fake.calls}
        assert markets == {"17", "33", "20"}

    def test_minute_unmapped_symbol_skipped(self) -> None:
        fake = _FakeQuota()
        p = _provider_with(fake)
        df = p.get_minute(
            ["000016.SH"], datetime(2026, 9, 3), datetime(2026, 9, 3, 23, 59, 59)
        )
        assert df.is_empty()
        assert fake.calls == []  # fail-closed: 未发起请求

    def test_minute_index_volume_passthrough(self) -> None:
        fake = _FakeQuota()
        p = _provider_with(fake)
        df = p.get_minute(
            ["000001.SH"], datetime(2026, 9, 3), datetime(2026, 9, 3, 23, 59, 59)
        )
        assert fake.calls[0][0] == "1A0001" and fake.calls[0][1] == "16"
        # 指数分钟: volume 不 /100 (fake 返回 330309 → 原样)
        assert df.to_dicts()[0]["volume"] == 330309.0
