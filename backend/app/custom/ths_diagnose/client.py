# ruff: noqa: RUF002, RUF003
"""同花顺「智能诊股」私有接口 HTTP 客户端。

对应 .trae/skills/10jqka-stock-diagnose/ 的 9 个接口（抓包文档化，2026-09-09 实测）。
挂在 eq.10jqka.com.cn / dq.10jqka.com.cn 私有域名下，抓包与实抓均无鉴权头，
可能随时加风控。本客户端并发按需求放开（min_interval=0、并发走高），
仅保留单次退避重试，禁止无脑放大重试。

信封成功码不统一（关键）：
  - eq open/api 面（get_score）：status_code == 0
  - dq fund / message 面：status_code == 200
  - dq finance / valuation 面：status_code == 0（valuation 顶层键为 status_message）
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Literal

import httpx

from app import __version__

logger = logging.getLogger(__name__)

EQ_BASE = "https://eq.10jqka.com.cn"
DQ_BASE = "https://dq.10jqka.com.cn"

# 每只股票下拉取(3 请求)与详情弹窗(单只多接口)共用同一份限流配置：
# 已按需求放开并发（不限制外部 API 负载）：并发走高，最小请求间隔设为 0。
_DEFAULT_CONCURRENCY = 32
_DEFAULT_INTERVAL_S = 0.0
_TIMEOUT_S = 15.0
_RETRIES = 1  # 失败后再重试 1 次

Group = Literal["eq_score", "fund", "message", "finance", "valuation"]

# group -> 成功判据
_SUCCESS_CODES: dict[Group, int] = {
    "eq_score": 0,
    "finance": 0,
    "valuation": 0,
    "fund": 200,
    "message": 200,
}


class DiagnoseError(Exception):
    """诊股接口错误（网络失败 / 信封码不符 / 响应异常）。"""


class ThsDiagnoseClient:
    """10jqka 智能诊股客户端（asyncio，限流共享）。

    线程安全：AsyncClient 可复用；同一时刻全局一个实例即可（模块级单例
    get_client()），请求经由共享信号量与最小间隔节流。
    """

    def __init__(
        self,
        *,
        timeout: float = _TIMEOUT_S,
        concurrency: int = _DEFAULT_CONCURRENCY,
        min_interval_s: float = _DEFAULT_INTERVAL_S,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
            headers={"User-Agent": f"tsp/{__version__}", "Accept": "application/json"},
        )
        self._sem = asyncio.Semaphore(concurrency)
        self._min_interval = min_interval_s
        self._next_ok_at = 0.0
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------
    # 限流与单次重试
    # ------------------------------------------------------------------
    async def _throttle(self) -> None:
        now = time.monotonic()
        async with self._lock:
            wait = self._next_ok_at - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_ok_at = max(now, self._next_ok_at) + self._min_interval

    async def _request(self, group: Group, url: str, params: dict | None = None) -> Any:
        """GET + 信封判定，返回 data。5xx/网络错误重试 1 次（指数退避）。"""
        last_err: Exception | None = None
        for attempt in range(_RETRIES + 1):
            if attempt:
                await asyncio.sleep(0.5 * (2**attempt))
            async with self._sem:
                await self._throttle()
                try:
                    resp = await self._http.get(url, params=params)
                except httpx.HTTPError as e:
                    last_err = e
                    continue
            if resp.status_code == 429:
                # 风控/限频：不自动放大，直接报错由上层提示
                raise DiagnoseError(f"HTTP 429 限频: {url}")
            if resp.status_code >= 500:
                last_err = DiagnoseError(f"HTTP {resp.status_code}: {url}")
                continue
            if resp.status_code != 200:
                raise DiagnoseError(f"HTTP {resp.status_code}: {url}")
            try:
                payload = resp.json()
            except ValueError as e:
                raise DiagnoseError(f"响应不是 JSON: {url}") from e
            if not isinstance(payload, dict):
                raise DiagnoseError(f"响应不是对象: {url}")
            code = payload.get("status_code")
            if code != _SUCCESS_CODES[group]:
                msg = payload.get("status_msg") or payload.get("status_message") or ""
                raise DiagnoseError(f"诊股接口错误 code={code}: {msg} ({url})")
            return payload.get("data")
        raise DiagnoseError(f"诊股接口请求失败: {last_err}")

    # ------------------------------------------------------------------
    # 各接口方法
    # ------------------------------------------------------------------
    async def get_score(self, market: int, code: str) -> dict:
        """总评（含六维评分/排名/异动要点）。"""
        url = f"{EQ_BASE}/open/api/stock_diagnose_v2/composite_score/v1/get_score/{market}/{code}"
        data = await self._request("eq_score", url)
        return data if isinstance(data, dict) else {}

    async def finance_ablility(self, market: int, code: str) -> dict:
        """财务评分（含六能力、上年同期 last_score）。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnosis/finance/v1/ablility"
        data = await self._request("finance", url, {"code": code, "market": market})
        return data if isinstance(data, dict) else {}

    async def finance_analysis(self, market: int, code: str) -> dict:
        """财务亮点与风险。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnosis/finance/v1/analysis"
        data = await self._request("finance", url, {"code": code, "market": market})
        return data if isinstance(data, dict) else {}

    async def finance_ablility_history(self, market: int, code: str, ability_id: str) -> dict:
        """财务分历史（ability_id 见 parsers.ABILITY_IDS）。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnosis/finance/v1/ablility_history"
        data = await self._request(
            "finance", url, {"code": code, "market": market, "ability_id": ability_id}
        )
        return data if isinstance(data, dict) else {}

    async def fund_summary(self, market: int, code: str) -> dict:
        """资金要点概述（机构持股/上榜/增减持/大宗）。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnose_general/fund/v1/fund_summary/get"
        data = await self._request("fund", url, {"stock_code": code, "stock_market": market})
        return data if isinstance(data, dict) else {}

    async def fund_comprehensive(self, market: int, code: str) -> dict:
        """资金评分综合（含 fund_score_minus 较昨日变化）。"""
        url = (
            f"{DQ_BASE}/fuyao/stock_diagnose_general/fund/v1/"
            "fund_comprehensive_evaluation/get"
        )
        data = await self._request(
            "fund", url, {"stock_code": code, "stock_market": market}
        )
        return data if isinstance(data, dict) else {}

    async def fund_history(self, market: int, code: str, period: str = "one-month") -> list:
        """资金评分历史（period: one-month / one-year）。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnose_general/fund/v1/fund_history/get"
        data = await self._request(
            "fund", url, {"stock_code": code, "stock_market": market, "period": period}
        )
        return data if isinstance(data, list) else []

    async def message(self, ths_code: str) -> dict:
        """个股公告/研报要点（ths_code 带交易所后缀）。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnose_general/message/v1/significant_message_analyze/get"
        data = await self._request("message", url, {"ths_code": ths_code})
        return data if isinstance(data, dict) else {}

    async def valuation(self, market: int, code: str, index: str, period: str) -> dict:
        """估值分位分析（index: pb/pe/pof/ps；period: 1/3/5/10 年）。"""
        url = f"{DQ_BASE}/fuyao/stock_diagnosis_valuation/valuation/v1/valuation_industry"
        data = await self._request(
            "valuation",
            url,
            {"code": code, "market": market, "index": index, "period": period},
        )
        return data if isinstance(data, dict) else {}


# ----------------------------------------------------------------------
# 模块级单例（惰性创建）
# ----------------------------------------------------------------------
_client: ThsDiagnoseClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> ThsDiagnoseClient:
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = ThsDiagnoseClient()
    return _client
