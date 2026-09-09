# ruff: noqa: RUF002, RUF003
"""client 单测：URL/参数/信封差异判定/失败重试语义（httpx MockTransport）。"""
import asyncio

import httpx
import pytest

from app.custom.ths_diagnose.client import (
    _SUCCESS_CODES,
    DiagnoseError,
    ThsDiagnoseClient,
)


def _run(coro):
    return asyncio.run(coro)


def _client(handler):
    transport = httpx.MockTransport(handler)
    return ThsDiagnoseClient(transport=transport, min_interval_s=0, concurrency=2)


def _make_handler(routes: dict[str, dict]):
    """routes: path_substring -> {status_code, json}。"""
    async def handler(request: httpx.Request) -> httpx.Response:
        for sub, payload in routes.items():
            if sub in request.url.path:
                return httpx.Response(
                    status_code=payload.get("status_code", 200),
                    json=payload.get("json", {}),
                )
        return httpx.Response(404)
    return handler


def test_envelope_differences_and_params():
    routes = {
        "get_score/33/300476": {"json": {"status_code": 0, "data": {"ok": True}}},
        "fund_comprehensive": {
            "json": {"status_code": 200, "data": {"fund_score": 2.0}},
        },
        "significant_message_analyze": {
            "json": {"status_code": 200, "data": {"data_list": [], "has_next_page": False}},
        },
        "ablility_history": {"json": {"status_code": 0, "data": {"ability_ids": []}}},
    }
    c = _client(_make_handler(routes))

    async def go():
        score = await c.get_score(33, "300476")
        assert score == {"ok": True}
        fund = await c.fund_comprehensive(33, "300476")
        assert fund["fund_score"] == 2.0
        msg = await c.message("300476.SZ")
        assert msg["has_next_page"] is False
        hist = await c.finance_ablility_history(33, "300476", "cash")
        assert hist["ability_ids"] == []
    _run(go())


def test_wrong_envelope_code_raises():
    c = _client(_make_handler({"get_score": {"json": {"status_code": 1, "data": {}}}}))

    with pytest.raises(DiagnoseError, match="code=1"):
        _run(c.get_score(33, "300476"))


def test_http_500_retried_once_then_raise():
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500)

    c = _client(handler)
    with pytest.raises(DiagnoseError, match="HTTP 500"):
        _run(c.get_score(33, "300476"))
    assert calls["n"] == 2  # 1 次重试


def test_http_429_raises_immediately():
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429)

    c = _client(handler)
    with pytest.raises(DiagnoseError, match="429"):
        _run(c.get_score(33, "300476"))
    assert calls["n"] == 1


def test_http_404_raises_without_retry():
    c = _client(_make_handler({}))
    with pytest.raises(DiagnoseError, match="HTTP 404"):
        _run(c.get_score(33, "300476"))


def test_success_code_table_consistent():
    # 信封差异是本接口族最容易踩的坑：逐接口成功码固定
    assert _SUCCESS_CODES["eq_score"] == 0
    assert _SUCCESS_CODES["finance"] == 0
    assert _SUCCESS_CODES["valuation"] == 0
    assert _SUCCESS_CODES["fund"] == 200
    assert _SUCCESS_CODES["message"] == 200
