# ruff: noqa: RUF002
"""同花顺「智能诊股」二开扩展（L2）。

自动发现：backend/app/custom/ 下子包会被 loader 扫描（EXTENSION_ID + setup）。
无自动定时：诊股评分为长线价值口径（财务分按财报披露周期更新），刷新只由
页面手动按钮触发；config 由首次拉取懒创建，因此不实现 startup 钩子。
"""
from __future__ import annotations

from app.custom.ths_diagnose import api
from app.extensions import BACKEND_EXTENSION_API_VERSION

EXTENSION_ID = "ths.diagnose"
EXTENSION_API_VERSION = BACKEND_EXTENSION_API_VERSION


def setup(registrar) -> None:
    registrar.include_router(api.router)
