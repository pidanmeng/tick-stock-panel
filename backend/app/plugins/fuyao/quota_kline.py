"""quota-h single_kline 子客户端 — fuyao 插件的 minute 数据集后端。

与 fuyao.aicubes.cn 官方 REST (X-api-key, 信封 {code,message,data}) 是**两套不同
surface**: 本模块直连同花顺 quota-h 私有行情网关 (IP/网络白名单, 无鉴权头), 信封
{status_code, data:{quote_data:[...]}}, 仅用于 1 分钟 K 线。

实测行为 (2026-09 对拍, 数据抓包存档见 fuyao provider docstring 与测试):
  - 请求体 code_list 只能一条 entry 且 codes 单码 (多 entry/多码整批空返回);
  - trade_date 无效; end_time=0=最新; begin_time=-N = 当前周期下 N 根 K 线前。
    实测响应分两段 (2026-09-05 梯度探针): N≤~950 根按请求量返回 (延迟 ~100ms);
    N≥1000 根时网关无视深度、整段返回留存内全部 (~12050 根 ≈ 2 个月, 延迟
    ~600-900ms) — 常见窗口估算一旦越过 1000 根, 单标的请求体量放大一个量级;
  - adjust_type="actual" = 不复权 (项目分钟/日K口径要求; forward 亦可但除权日
    历史分钟会漂移); "none/0/1/2/3/back/raw/qfq/hfq" 实测空返回;
  - data_fields 位置编码单 K 行 = [时间(ms), 开, 高, 低, 收, 量(股), 额(元)];
    time_ms 为「北京墙钟数值按 UTC 存储」, 统一 +8h 转北京墙钟 naive。
  - TLS: 该私有网关证书链本机不可验证 (UnknownIssuer) → verify=False (私有网关约定,
    部署环境若信任其证书可改 True)。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://quota-h.10jqka.com.cn/fuyao/common_hq_aggr/quote/v1/single_kline"

# data_fields 位置编码 → 字段名 (实测固定序列, 仍按编码定位以兼容字段增减)
_FIELD_MAP = {
    "1": "time_ms",
    "7": "open",
    "8": "high",
    "9": "low",
    "11": "close",
    "13": "volume",
    "19": "amount",
}

# 沪/中证指数 THS 代码 (内部 000xxx.SH → 接口 code), 仅收录已实测/用户确认项
# 上证综指=1A0001; 其余非 000001 沪指实测为 '1B' + code[2:] (000300→1B0300, 000680→1B0680)
_SH_INDEX_THS = {"000001": "1A0001", "000300": "1B0300", "000680": "1B0680"}

_DEFAULT_VERIFY_SSL = False  # 见模块 docstring TLS 说明


class QuotaError(Exception):
    """quota-h 分钟接口错误 (网络/HTTP/信封/结构异常)。"""


def bj_datetime(time_ms: int) -> datetime:
    """响应 ms (北京墙钟按 UTC 存储) → 北京墙钟 naive。"""
    return (datetime.fromtimestamp(time_ms / 1000.0, tz=UTC) + timedelta(hours=8)).replace(
        tzinfo=None
    )


def classify_symbol(symbol: str) -> tuple[str, str, str] | None:
    """内部 symbol → (code, market, kind)。kind: stock | etf | index。

    无法映射 (如未确认 THS 码的沪指) 返回 None → 上层 fail-closed 跳过。
    码表来源: 用户 API 文档确认 (2026-09)。
    """
    if not symbol:
        return None
    base, _, exch = symbol.partition(".")
    exch = exch.upper()
    if not exch or not base:
        return None
    if exch == "SH":
        if base.startswith("6"):
            return base, "17", "stock"  # 沪主板/科创板/存托凭证
        if base.startswith("5"):
            return base, "20", "etf"  # 沪 ETF (51/56/58…)
        if base.startswith("000"):
            ths = _SH_INDEX_THS.get(base)
            return (ths, "16", "index") if ths else None
        return None
    if exch == "SZ":
        if base.startswith(("000", "001", "002", "003", "300", "301")):
            return base, "33", "stock"
        if base.startswith("159"):
            return base, "36", "etf"
        if base.startswith("399"):
            return base, "32", "index"
        return None
    if exch == "BJ":
        return base, "151", "stock"  # 市场已识别, 实际分钟数据覆盖待验证
    return None


def scale_volume(value, kind: str):
    """volume 股 → 内部口径: 股票/ETF 为手 (floor /100), 指数透传。"""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if kind == "index":
        return value
    return float(int(value // 100))


def needed_minute_bars(start_time: datetime | None, end_time: datetime | None) -> int:
    """按窗口估算 begin_time 根数(交易日口径); 无窗口默认最近 400 根, 上限 30000。

    交易日口径而非自然日分钟: 分钟数据只在连续竞价时段产生 (240 根/交易日),
    自然日跨度会把隔夜/周末/节假日按全天分钟计入, 估值虚高跨过网关 1000 根
    阈值 → 整段留存倒出 (见模块 docstring), 请求与解析成本放大一个量级。
    估算 = 窗口内工作日 *240 + 240 缓冲; 真实缺口超过 ~4 个交易日时估值自然
    ≥1000 → 退化为整段留存返回 (留存即 ~2 个月上限, 数据不丢)。工作日口径
    无法感知调休休市, 该场景只会多算 (安全方向), 不产生缺口。
    """
    if start_time is None or end_time is None:
        return 400
    d0 = start_time.date()
    d1 = end_time.date()
    days = (d1 - d0).days
    weekdays = sum(1 for i in range(days + 1) if (d0 + timedelta(days=i)).weekday() < 5)
    est = weekdays * 240 + 240  # 240 根/交易日 + 1 交易日缓冲
    return min(30_000, max(400, est))


def _parse_payload(payload: dict) -> list[dict]:
    """信封/位置数组 → 逐行 dict; 行宽与 data_fields 不一致 → 抛 QuotaError。"""
    if not isinstance(payload, dict):
        raise QuotaError("响应不是 JSON 对象")
    code = payload.get("status_code")
    if code not in (0, "0", None):
        raise QuotaError(f"接口错误 code={code}: {payload.get('status_msg', '')}")
    data = payload.get("data") or {}
    quote_data = data.get("quote_data")
    if not isinstance(quote_data, list) or not quote_data:
        return []
    out: list[dict] = []
    for item in quote_data:
        if not isinstance(item, dict):
            continue
        fields = item.get("data_fields") or []
        values = item.get("value")
        if not isinstance(values, list):
            continue
        for row in values:
            if not isinstance(row, list):
                continue
            if len(row) != len(fields):
                raise QuotaError(
                    f"K线行宽 {len(row)} != data_fields {len(fields)}, 疑似结构变化"
                )
            bar: dict[str, Any] = {}
            for raw_code, raw_value in zip(fields, row, strict=True):
                name = _FIELD_MAP.get(str(raw_code))
                if name is None:
                    continue
                if name == "time_ms":
                    try:
                        bar[name] = int(raw_value)
                    except (TypeError, ValueError):
                        bar[name] = None
                else:
                    try:
                        bar[name] = float(raw_value)
                    except (TypeError, ValueError):
                        bar[name] = None
            if bar.get("time_ms") is None:
                continue
            out.append(bar)
    return out


class QuotaClient:
    """quota-h single_kline 1 分钟客户端 (httpx.Client 线程安全, 可并发复用)。"""

    def __init__(
        self, url: str = BASE_URL, timeout: float = 30.0, verify: bool = _DEFAULT_VERIFY_SSL
    ) -> None:
        self._http = httpx.Client(timeout=timeout, verify=verify)
        self.url = url

    def close(self) -> None:
        self._http.close()

    def minute_kline(self, code: str, market: str, begin_bars: int = 400) -> list[dict]:
        """拉取单个 (code, market) 的 1 分钟 K (adjust=actual), 返回原始行 dict。

        code_list 限单条单码 (实测多码/多 entry 整批空返回)。
        """
        body = {
            "code_list": [{"codes": [code], "market": market}],
            "trade_class": "intraday",
            "time_period": "min_1",
            "trade_date": -1,  # 实测无效字段, 仅保持请求形状
            "begin_time": -int(begin_bars),
            "end_time": 0,
            "adjust_type": "actual",
            "gpid": 1,
        }
        try:
            resp = self._http.post(self.url, json=body)
        except httpx.HTTPError as e:
            raise QuotaError(f"网络请求失败({type(e).__name__}): {e}") from e
        if resp.status_code != 200:
            raise QuotaError(f"HTTP {resp.status_code}: {self.url}")
        try:
            payload = resp.json()
        except ValueError as e:
            raise QuotaError(f"响应不是 JSON: {self.url}") from e
        return _parse_payload(payload)
