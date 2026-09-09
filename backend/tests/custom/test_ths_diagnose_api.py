# ruff: noqa: RUF002
"""API/注册层约束测试：路由前缀、标的校验、扩展自动发现。"""
import asyncio

import pytest
from fastapi import HTTPException

from app.custom.ths_diagnose import api, service


def test_router_prefix_and_registered_paths():
    assert api.router.prefix == "/api/custom/ths-diagnose"
    paths = {r.path for r in api.router.routes}
    assert "/api/custom/ths-diagnose/snapshot" in paths
    assert "/api/custom/ths-diagnose/snapshot/pull" in paths
    assert "/api/custom/ths-diagnose/snapshot/progress" in paths
    assert "/api/custom/ths-diagnose/stock/{symbol}/finance" in paths
    assert "/api/custom/ths-diagnose/stock/{symbol}/valuation" in paths
    assert "/api/custom/ths-diagnose/prefs" in paths


def test_symbol_or_400():
    assert api._symbol_or_400("600519.SH") == ("600519", 17)
    assert api._symbol_or_400("300476.SZ") == ("300476", 33)
    with pytest.raises(HTTPException) as ei:
        api._symbol_or_400("300476.XX")  # 非 SH/SZ 后缀
    assert ei.value.status_code == 400


def test_pull_validates_empty_or_all_skipped(tmp_path):
    # 无维表 → fail-closed 400 语义来源
    ok, skipped = service.filter_stock_symbols(["600519.SH"], tmp_path)
    assert ok == []
    assert skipped


def test_extension_module_discoverable_and_wired():
    from app.extensions import loader

    names = loader._custom_module_names()
    assert "app.custom.ths_diagnose" in names

    import app.custom.ths_diagnose as mod

    assert mod.EXTENSION_ID == "ths.diagnose"
    from app.extensions.contracts import BACKEND_EXTENSION_API_VERSION

    assert mod.EXTENSION_API_VERSION == BACKEND_EXTENSION_API_VERSION
    assert callable(mod.setup)


# ----------------------------------------------------------------------
# 详情端点回归: 必须 await 客户端再调用方法(曾出现把协程当客户端用)
# ----------------------------------------------------------------------
class _StubClient:
    """与 ThsDiagnoseClient 同签名的最小桩，直接调用 api 端点函数验证装配。"""

    async def get_score(self, market, code):
        return {"date": "2026-09-09", "stock_name": "示例", "industry_name": "元件",
                "industry_code": "881270", "rank": {"score": {"fund": 2.0}}}

    async def finance_ablility(self, market, code):
        return {"share_comprehensive_score": "2.8", "diagnosis_abilities": []}

    async def finance_analysis(self, market, code):
        return {"overview": "o", "highlight": [], "risk": []}

    async def fund_comprehensive(self, market, code):
        return {"fund_score": 2.0, "fund_score_minus": 0.2}

    async def fund_summary(self, market, code):
        return {}

    async def message(self, ths_code):
        return {"data_list": [], "has_next_page": False}

    async def valuation(self, market, code, index, period):
        return {"performance_list": {}, "value_list": {}}


def _make_stub_client():
    async def stub():
        return _StubClient()

    api._client = stub
    return stub


def test_detail_endpoints_await_client_before_calling():
    _make_stub_client()

    async def go():
        s = await api.stock_summary("300502.SZ")
        assert "scores" in s
        f = await api.stock_finance("300502.SZ", ability_id=None)
        assert f["share"] == 2.8
        fund = await api.stock_fund("300502.SZ", history=None)
        assert fund["fund_score"] == 2.0
        msg = await api.stock_message("300502.SZ")
        assert msg["rows"] == []
        val = await api.stock_valuation("300502.SZ", index="pb", period="1")
        assert val["points"] == []

    asyncio.run(go())
