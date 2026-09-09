# ruff: noqa: RUF001, RUF002, RUF003
"""诊股快照服务：标的过滤、批量拉取、扩展数据快照落盘、偏好记忆。

落盘复用现有扩展数据机制（data/ext_data/ths_diagnose/，snapshot 模式）：
- config.json 由首次拉取懒创建（ExtConfigStore.upsert，幂等）
- 数据行由 rows_to_parquet 写入 part.parquet（内部按 symbol 去重 keep-last，
  天然支持多批次/多标的集合累积）

刷新只由手动请求触发，无常驻定时线程。外部接口无鉴权：限流见 client。
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from app.services.ext_data import ExtConfig, ExtConfigStore, ExtField, rows_to_parquet

logger = logging.getLogger(__name__)

CONFIG_ID = "ths_diagnose"
CONFIG_LABEL = "同花顺智能诊股"
CONFIG_DESCRIPTION = "同花顺 App「智能诊股」评分快照（长线价值口径，手动更新）"

# 单次拉取默认上限（UI 阈值提示）。分批拉取可在多日内累积（按 symbol 去重）。
DEFAULT_PULL_CAP = 500
# A 股全量模式的单次上限（沪深全部 A 股约 5k 只；超长任务，仍低并发分批执行）
DEFAULT_PULL_CAP_ALL = 6000
PREFS_FILE = "ths_diagnose.json"

# 快照字段（ExtConfig fields）：与 parsers.to_snapshot_row 输出一致
FIELDS: list[tuple[str, str, str]] = [
    ("symbol", "string", "代码"),
    ("code", "string", "裸代码"),
    ("name", "string", "名称"),
    ("snapshot_date", "string", "快照日期"),
    ("industry_name", "string", "行业"),
    ("industry_code", "string", "行业编码"),
    ("rank_industry", "int", "行业排名"),
    ("rank_market", "int", "市场排名"),
    ("total_industry", "int", "行业总数"),
    ("total_market", "int", "市场总数"),
    ("score_fund", "float", "资金分"),
    ("score_tech", "float", "技术分"),
    ("score_valuation", "float", "估值分"),
    ("score_message", "float", "消息分"),
    ("score_finance", "float", "财务分"),
    ("score_average", "float", "平均分"),
    ("score_delta", "float", "变化分"),
    ("fund_chg", "float", "资金较昨"),
    ("finance_total", "float", "财务总分"),
    ("finance_prev", "float", "财务上年同期"),
    ("abl_profit", "float", "盈利"),
    ("abl_growth", "float", "成长"),
    ("abl_operate", "float", "营运"),
    ("abl_cash", "float", "现金流"),
    ("abl_pay", "float", "偿债"),
    ("abl_asset", "float", "资产质量"),
]


def _config_store(data_dir: Path) -> ExtConfigStore:
    return ExtConfigStore(data_dir)


def _config_path(data_dir: Path) -> Path:
    return data_dir / "ext_data" / CONFIG_ID / "config.json"


def _snapshot_path(data_dir: Path) -> Path:
    return data_dir / "ext_data" / CONFIG_ID / "part.parquet"


def ensure_config(data_dir: Path) -> ExtConfig:
    """幂等创建（或读取）扩展数据配置。"""
    store = _config_store(data_dir)
    cfg = store.get(CONFIG_ID)
    if cfg is not None:
        return cfg
    cfg = ExtConfig(
        id=CONFIG_ID,
        label=CONFIG_LABEL,
        mode="snapshot",
        fields=[ExtField(name, dtype, label) for name, dtype, label in FIELDS],
        description=CONFIG_DESCRIPTION,
    )
    store.upsert(cfg)
    return cfg


# ----------------------------------------------------------------------
# 标的校验与过滤（fail-closed）
# ----------------------------------------------------------------------
def split_symbol(symbol: str) -> tuple[str, int] | None:
    """'300476.SZ' → ('300476', 33)；'600519.SH' → ('600519', 17)。非法返回 None。"""
    if not isinstance(symbol, str):
        return None
    s = symbol.strip()
    if "." not in s:
        return None
    code, ex = s.split(".", 1)
    if not (len(code) == 6 and code.isdigit()):
        return None
    if ex == "SH":
        return code, 17
    if ex == "SZ":
        return code, 33
    return None


def load_stock_symbols(data_dir: Path) -> set[str]:
    """A 股股票维表 symbol 集合（type=stock 且沪深），供过滤。

    以 instruments 维表为准（含 type/exchange 列），不凭代码前缀猜资产类型。
    """
    path = data_dir / "instruments" / "instruments.parquet"
    if not path.exists():
        return set()
    try:
        df = pl.read_parquet(path, columns=["symbol", "type", "exchange"])
    except Exception as exc:
        logger.warning("读取 instruments 维表失败: %s", exc)
        return set()
    if "type" not in df.columns or "exchange" not in df.columns:
        return set()
    return set(
        df.filter(
            (pl.col("type") == "stock") & (pl.col("exchange").is_in(["SH", "SZ"]))
        )["symbol"].to_list()
    )


def filter_stock_symbols(symbols: list[str], data_dir: Path) -> tuple[list[str], list[str]]:
    """返回 (可拉取股票, 跳过原因列表)。

    规则：格式合法（6 位 + SH/SZ）且存在于 A 股股票维表；否则记录跳过。
    instruments 维表缺失时 fail-closed（返回空可拉取列表并说明）。
    """
    stock_set = load_stock_symbols(data_dir)
    if not stock_set:
        return [], ["instruments 股票维表缺失或为空，无法确认 A 股标的，已拒绝拉取"]
    ok: list[str] = []
    skipped: list[str] = []
    for s in symbols:
        parts = split_symbol(s)
        if parts is None:
            skipped.append(f"{s}: 非法格式（需 6 位代码 + .SH/.SZ）")
            continue
        if s not in stock_set:
            skipped.append(f"{s}: 不在 A 股股票维表（可能是 ETF/指数/北交所）")
            continue
        ok.append(s)
    return ok, skipped


def all_stock_symbols(data_dir: Path) -> list[str]:
    """A 股全量标的（维表内 type=stock 且沪深），按 symbol 排序。"""
    return sorted(load_stock_symbols(data_dir))


# ----------------------------------------------------------------------
# 批量拉取（后台任务 + 进度状态）
# ----------------------------------------------------------------------
_progress: dict[str, Any] = {
    "running": False,
    "total": 0,
    "done": 0,
    "ok": 0,
    "failed": 0,
    "failed_symbols": [],
    "warnings": {},
    "started_at": None,
    "finished_at": None,
}


def progress_snapshot() -> dict[str, Any]:
    return dict(_progress)


async def pull_snapshot(
    data_dir: Path,
    symbols: list[str],
    include_trend: bool = True,
    *,
    client: Any = None,
    cap: int = DEFAULT_PULL_CAP,
) -> None:
    """后台批量拉取并落盘。client 供测试注入；默认模块级单例。"""
    if _progress["running"]:
        raise RuntimeError("已有拉取任务进行中")
    if cap <= 0:
        cap = DEFAULT_PULL_CAP
    todo = symbols[:cap]

    _progress.update(
        running=True,
        total=len(todo),
        done=0,
        ok=0,
        failed=0,
        failed_symbols=[],
        warnings={},
        started_at=datetime.now().isoformat(timespec="seconds"),
        finished_at=None,
    )

    if client is None:
        from app.custom.ths_diagnose.client import get_client

        client = await get_client()

    ensure_config(data_dir)
    rows: list[dict] = []
    try:
        # 逐只拉取：总评必拉；趋势列开启时补 ablility + fund_comprehensive。
        # 并行度由 client 内部信号量限制（默认 3），外层按批调度避免一次挂太多任务。
        batch = 6
        for start in range(0, len(todo), batch):
            chunk = todo[start : start + batch]
            results = await asyncio.gather(
                *(fetch_one(client, s, include_trend) for s in chunk),
                return_exceptions=True,
            )
            for s, res in zip(chunk, results, strict=False):
                _progress["done"] += 1
                if isinstance(res, Exception):
                    _progress["failed"] += 1
                    _progress["failed_symbols"].append(s)
                    _progress["warnings"][s] = str(res)[:160]
                    logger.warning("诊股拉取失败 %s: %s", s, res)
                    continue
                row, warns = res
                if warns:
                    _progress["warnings"][s] = "；".join(warns)
                if row:
                    rows.append(row)
                    _progress["ok"] += 1
        if rows:
            df = pl.DataFrame(rows)
            rows_to_parquet(df, ensure_config(data_dir), data_dir)
    finally:
        _progress["running"] = False
        _progress["finished_at"] = datetime.now().isoformat(timespec="seconds")


async def fetch_one(client: Any, symbol: str, include_trend: bool) -> tuple[dict, list[str]]:
    """单只拉取：get_score（+可选 trend），返回 (快照行, 警告列表)。"""
    from app.custom.ths_diagnose import parsers

    parts = split_symbol(symbol)
    assert parts is not None
    code, market = parts

    summary = await client.get_score(market, code)
    if not summary:
        return {}, ["get_score 返回空数据"]
    finance = fund = None
    warns: list[str] = []
    if include_trend:
        try:
            finance = await client.finance_ablility(market, code)
        except Exception as exc:
            warns.append(f"财务趋势拉取失败: {exc}")
        try:
            fund = await client.fund_comprehensive(market, code)
        except Exception as exc:
            warns.append(f"资金趋势拉取失败: {exc}")
    row = parsers.to_snapshot_row(symbol, summary, finance, fund)
    return row, warns


def read_snapshot(data_dir: Path) -> tuple[list[dict], str | None]:
    """读取快照行与快照日期（part.parquet mtime → YYYY-MM-DD）。"""
    path = _snapshot_path(data_dir)
    if not path.exists():
        return [], None
    try:
        df = pl.read_parquet(path)
    except Exception as exc:
        logger.warning("读取诊股快照失败: %s", exc)
        return [], None
    rows = [_safe(v) for v in df.to_dicts()]
    date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    return rows, date


def snapshot_meta(data_dir: Path) -> dict[str, Any]:
    """快照元信息（供 /config）。"""
    path = _snapshot_path(data_dir)
    rows = 0
    date: str | None = None
    if path.exists():
        try:
            df = pl.read_parquet(path, columns=["symbol"])
            rows = len(df)
        except Exception:
            rows = 0
        date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return {"configured": _config_path(data_dir).exists(), "rows": rows, "date": date}


def clear_snapshot(data_dir: Path) -> None:
    """清空快照数据（保留 config）。"""
    _snapshot_path(data_dir).unlink(missing_ok=True)


def _safe(v: Any) -> Any:
    import math

    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


# ----------------------------------------------------------------------
# 偏好（data/user_data/ths_diagnose.json）
# ----------------------------------------------------------------------
def _prefs_path(data_dir: Path) -> Path:
    return data_dir / "user_data" / PREFS_FILE


def load_prefs(data_dir: Path) -> dict[str, Any]:
    path = _prefs_path(data_dir)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def save_prefs(data_dir: Path, patch: dict[str, Any]) -> dict[str, Any]:
    prefs = load_prefs(data_dir)
    for key in ("universe", "include_trend"):
        if key in patch:
            if patch[key] is None:
                prefs.pop(key, None)
            else:
                prefs[key] = patch[key]
    path = _prefs_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    return prefs
