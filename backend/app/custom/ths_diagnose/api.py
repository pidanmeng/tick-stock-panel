# ruff: noqa: RUF001, RUF002, RUF003
"""智能诊股扩展 API（prefix=/api/custom/ths-diagnose）。

快照与偏好读写走 service（复用 ext-data 存储）；详情端点实时调用外部接口，
单分区请求各自独立失败隔离。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.custom.ths_diagnose import parsers, service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/custom/ths-diagnose", tags=["custom-ths-diagnose"])

_ROW_LIMIT = 20000


def _data_dir(request: Request):
    return request.app.state.repo.store.data_dir


def _symbol_or_400(symbol: str) -> tuple[str, int]:
    parts = service.split_symbol(symbol)
    if parts is None:
        raise HTTPException(400, f"非法标的: {symbol}（需 6 位代码 + .SH/.SZ）")
    return parts


class PullReq(BaseModel):
    """拉取请求。scope='all' 表示 A 股全量（忽略 symbols）；否则按给定列表。"""

    symbols: list[str] = Field(default_factory=list, max_length=2000)
    include_trend: bool = True
    scope: Literal["symbols", "all"] = "symbols"


class PrefsReq(BaseModel):
    universe: dict[str, Any] | None = None
    include_trend: bool | None = None


# ----------------------------------------------------------------------
# 快照
# ----------------------------------------------------------------------
@router.get("/config")
def config(request: Request) -> dict:
    data_dir = _data_dir(request)
    meta = service.snapshot_meta(data_dir)
    prefs = service.load_prefs(data_dir)
    return {
        **meta,
        "running": service.progress_snapshot()["running"],
        "universe": prefs.get("universe"),
        "include_trend": bool(prefs.get("include_trend", True)),
        "cap": service.DEFAULT_PULL_CAP,
        "fields": [
            {"name": n, "dtype": d, "label": lab} for n, d, lab in service.FIELDS
        ],
    }


@router.get("/snapshot")
def snapshot(request: Request) -> dict:
    data_dir = _data_dir(request)
    rows, date = service.read_snapshot(data_dir)
    return {"date": date, "total": len(rows), "rows": rows[: _ROW_LIMIT]}


@router.post("/snapshot/pull")
async def pull(request: Request, body: PullReq) -> dict:
    data_dir = _data_dir(request)
    if body.scope == "all":
        ok = service.all_stock_symbols(data_dir)
        if not ok:
            raise HTTPException(400, "instruments 股票维表缺失或为空，无法拉取 A 股全量")
        skipped: list[str] = []
        cap = service.DEFAULT_PULL_CAP_ALL
        service.save_prefs(data_dir, {"universe": {"type": "all"}})
    else:
        ok, skipped = service.filter_stock_symbols(body.symbols, data_dir)
        if not ok:
            raise HTTPException(400, "没有可拉取的标的：" + "；".join(skipped[:5]))
        cap = service.DEFAULT_PULL_CAP
        # 保存本次 universe 供“上次快照/一键重拉”
        service.save_prefs(data_dir, {"universe": {"type": "symbols", "symbols": ok}})
    try:
        task = asyncio.create_task(
            service.pull_snapshot(data_dir, ok, include_trend=body.include_trend, cap=cap)
        )
        # 持有引用防止任务被 GC
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return {
        "status": "started",
        "queued": len(ok),
        "cap": cap,
        "skipped": skipped,
    }


_tasks: set[asyncio.Task] = set()


@router.get("/snapshot/progress")
def pull_progress() -> dict:
    return service.progress_snapshot()


@router.post("/snapshot/clear")
def clear(request: Request) -> dict:
    service.clear_snapshot(_data_dir(request))
    return {"status": "ok"}


# ----------------------------------------------------------------------
# 偏好
# ----------------------------------------------------------------------
@router.get("/prefs")
def get_prefs(request: Request) -> dict:
    return service.load_prefs(_data_dir(request))


@router.post("/prefs")
def post_prefs(request: Request, body: PrefsReq) -> dict:
    patch = {}
    if body.universe is not None:
        patch["universe"] = body.universe
    if body.include_trend is not None:
        patch["include_trend"] = body.include_trend
    return service.save_prefs(_data_dir(request), patch)


# ----------------------------------------------------------------------
# 详情（单只实时）
# ----------------------------------------------------------------------
@router.get("/stock/{symbol}/summary")
async def stock_summary(symbol: str) -> dict:
    code, market = _symbol_or_400(symbol)
    client = await _client()
    data = await _safe_call(client.get_score(market, code), "总评")
    return parsers.summary_section(data)


@router.get("/stock/{symbol}/finance")
async def stock_finance(
    symbol: str,
    ability_id: str | None = Query(None),
) -> dict:
    code, market = _symbol_or_400(symbol)
    client = await _client()
    ablility = await _safe_call(client.finance_ablility(market, code), "财务评分")
    try:
        analysis = await client.finance_analysis(market, code)
    except Exception:
        analysis = None
    history = None
    if ability_id:
        allowed = set(parsers.ABILITY_IDS) | {"final_score"}
        if ability_id not in allowed:
            raise HTTPException(400, f"非法 ability_id: {ability_id}")
        history = await _safe_call(
            client.finance_ablility_history(market, code, ability_id), "财务历史"
        )
    return parsers.finance_section(ablility, analysis, history)


@router.get("/stock/{symbol}/fund")
async def stock_fund(
    symbol: str,
    history: str | None = Query(None, description="one-month | one-year"),
) -> dict:
    code, market = _symbol_or_400(symbol)
    client = await _client()
    comprehensive = await _safe_call(client.fund_comprehensive(market, code), "资金评分")
    try:
        summary = await client.fund_summary(market, code)
    except Exception:
        summary = None
    hist_rows: list | None = None
    if history:
        if history not in parsers.FUND_PERIODS:
            raise HTTPException(400, f"非法 history: {history}")
        hist_rows = await _safe_call(client.fund_history(market, code, history), "资金历史")
    return parsers.fund_section(comprehensive, summary, hist_rows)


@router.get("/stock/{symbol}/message")
async def stock_message(symbol: str) -> dict:
    _symbol_or_400(symbol)
    client = await _client()
    data = await _safe_call(client.message(symbol), "公告研报")
    return parsers.message_section(data)


@router.get("/stock/{symbol}/valuation")
async def stock_valuation(
    symbol: str,
    index: str = Query("pb"),
    period: str = Query("1", description="1/3/5/10 年"),
) -> dict:
    code, market = _symbol_or_400(symbol)
    if index not in parsers.VALID_VALUATION_INDEX:
        raise HTTPException(400, f"非法 index: {index}")
    if period not in parsers.VALID_VALUATION_PERIOD:
        raise HTTPException(400, f"非法 period: {period}")
    client = await _client()
    data = await _safe_call(client.valuation(market, code, index, period), "估值分位")
    return parsers.valuation_section(data)


# ----------------------------------------------------------------------
# 私有
# ----------------------------------------------------------------------
async def _client():
    from app.custom.ths_diagnose.client import get_client

    return await get_client()


async def _safe_call(coro, label: str):
    """统一失败语义：外部接口异常 → 502，带原因（不静默返回错误金融结果）。"""
    from app.custom.ths_diagnose.client import DiagnoseError

    try:
        return await coro
    except DiagnoseError as e:
        raise HTTPException(502, f"{label}接口请求失败: {e}") from e
    except Exception as e:
        logger.warning("诊股详情接口异常(%s): %s", label, e)
        raise HTTPException(502, f"{label}接口请求失败: {e}") from e
