"""多布局菜单 (nav layouts) — 默认布局兼容 / 具名布局 CRUD / 激活解析。

默认布局(id='')不单独持久化, 数据沿用顶层旧字段 nav_order/nav_hidden,
因此删除新增键即回滚; 具名布局存顶层 nav_layouts, 当前生效布局存 nav_active_layout。
"""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from app.api import settings
from app.services import preferences


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    path = tmp_path / "preferences.json"
    monkeypatch.setattr(preferences, "_path", lambda: path)
    preferences._invalidate_cache()
    yield path
    preferences._invalidate_cache()


def _seed(data: dict, path) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")
    preferences._invalidate_cache()


# ── 默认布局 = 顶层旧字段 (向后兼容) ─────────────────────────────────────

def test_default_layout_reads_and_writes_legacy_fields(_isolated):
    _seed({"nav_order": ["/", "/watchlist"], "nav_hidden": ["/data"]}, _isolated)

    assert preferences.get_active_nav_layout() == ""
    assert preferences.get_nav_order() == ["/", "/watchlist"]
    assert preferences.get_nav_hidden() == ["/data"]

    # get_nav_layouts 首项为默认布局, 数据即顶层旧字段
    layouts = preferences.get_nav_layouts()
    assert [row["id"] for row in layouts] == [""]
    assert layouts[0]["name"] == "默认布局"
    assert layouts[0]["nav_order"] == ["/", "/watchlist"]

    # 无 layout_id 的写入 → 顶层旧字段
    assert preferences.set_nav_order(["/watchlist", "/"]) == ["/watchlist", "/"]
    assert preferences.load()["nav_order"] == ["/watchlist", "/"]


def test_default_layout_no_new_keys_when_no_named_layouts(_isolated):
    _seed({"nav_order": ["/"]}, _isolated)
    saved = preferences.load()
    assert "nav_layouts" not in saved
    assert "nav_active_layout" not in saved


# ── 具名布局创建/命名校验 ────────────────────────────────────────────────

def test_create_nav_layout_without_customization_starts_default(_isolated):
    # 未做过任何自定义时, 拷贝默认布局结果为空排序/无隐藏
    rec = preferences.create_nav_layout("短线")
    assert rec["id"]
    assert rec["name"] == "短线"
    assert rec["nav_order"] == []
    assert rec["nav_hidden"] == []

    layouts = preferences.get_nav_layouts()
    assert len(layouts) == 2
    assert layouts[1]["name"] == "短线"
    # 新建布局不得改默认布局
    assert layouts[0]["id"] == ""
    assert layouts[0]["nav_order"] == []


def test_create_nav_layout_copies_default_layout_customization(_isolated):
    _seed({"nav_order": ["/watchlist", "/"], "nav_hidden": ["/data"]}, _isolated)
    rec = preferences.create_nav_layout("短线")
    assert rec["nav_order"] == ["/watchlist", "/"]
    assert rec["nav_hidden"] == ["/data"]
    # 拷贝不产生引用共享, 后续修改副本不影响默认布局
    assert preferences.set_nav_order(["/"], rec["id"]) == ["/"]
    assert preferences.load()["nav_order"] == ["/watchlist", "/"]


def test_create_nav_layout_copies_named_source(_isolated):
    base = preferences.create_nav_layout("量化研究")
    preferences.set_nav_order(["/data", "/screener"], base["id"])
    preferences.set_nav_hidden(["/watchlist"], base["id"])

    copied = preferences.create_nav_layout("短线", source_layout_id=base["id"])
    assert copied["nav_order"] == ["/data", "/screener"]
    assert copied["nav_hidden"] == ["/watchlist"]
    # 来源布局保持不变
    assert preferences.get_nav_layouts()[1]["nav_order"] == ["/data", "/screener"]


def test_create_nav_layout_rejects_unknown_source(_isolated):
    with pytest.raises(ValueError, match="不存在"):
        preferences.create_nav_layout("短线", source_layout_id="deadbeef")


@pytest.mark.parametrize("bad", ["", "   ", "默认布局", "量化研究" * 7])
def test_create_nav_layout_rejects_invalid_names(_isolated, bad):
    with pytest.raises(ValueError):
        preferences.create_nav_layout(bad)


def test_create_nav_layout_duplicate_name_rejected(_isolated):
    preferences.create_nav_layout("短线")
    with pytest.raises(ValueError, match="已存在"):
        preferences.create_nav_layout(" 短线 ")
    # 与默认布局重名同样拒绝 (保留默认布局名的展示语义)
    with pytest.raises(ValueError, match="默认布局"):
        preferences.create_nav_layout("默认布局")


# ── 具名布局排序/显隐写入与激活解析 ─────────────────────────────────────

def test_set_nav_order_with_explicit_layout_id_edits_named_only(_isolated):
    _seed({"nav_order": ["/"], "nav_hidden": []}, _isolated)
    rec = preferences.create_nav_layout("量化研究")

    assert preferences.set_nav_order(["/data", "/screener"], rec["id"]) == ["/data", "/screener"]
    assert preferences.set_nav_hidden(["/watchlist"], rec["id"]) == ["/watchlist"]

    named = preferences.get_nav_layouts()[1]
    assert named["nav_order"] == ["/data", "/screener"]
    assert named["nav_hidden"] == ["/watchlist"]
    # 默认布局(顶层旧字段)不被触碰
    assert preferences.load()["nav_order"] == ["/"]

    # 显式未知 layout_id → 拒绝, 不静默写默认
    with pytest.raises(ValueError, match="布局不存在"):
        preferences.set_nav_order([], "deadbeef")


def test_set_nav_order_without_layout_id_targets_active(_isolated):
    _seed({"nav_order": ["/"]}, _isolated)
    rec = preferences.create_nav_layout("短线")
    preferences.set_active_nav_layout(rec["id"])

    # 无 layout_id → 写当前生效布局 (短线的记录)
    preferences.set_nav_order(["/watchlist"])
    named = preferences.get_nav_layouts()[1]
    assert named["nav_order"] == ["/watchlist"]
    assert preferences.load()["nav_order"] == ["/"]


def test_resolve_active_layout_for_read(_isolated):
    _seed({"nav_order": ["/"], "nav_hidden": ["/review"]}, _isolated)
    # 新建布局拷贝默认布局内容 (含隐藏项), 再单独改排序
    rec = preferences.create_nav_layout("价值投资")
    preferences.set_nav_order(["/backtest"], rec["id"])
    preferences.set_active_nav_layout(rec["id"])

    assert preferences.get_active_nav_layout() == rec["id"]
    assert preferences.get_nav_order() == ["/backtest"]
    assert preferences.get_nav_hidden() == ["/review"]
    # 默认布局自身的顶层数据仍在 nav_layouts 首项 (面板可独立编辑)
    assert preferences.get_nav_layouts()[0]["nav_order"] == ["/"]
    assert preferences.get_nav_layouts()[0]["nav_hidden"] == ["/review"]


def test_stale_active_layout_self_heals_to_default(_isolated):
    _seed({"nav_order": ["/"], "nav_active_layout": "deadbeef"}, _isolated)
    assert preferences.get_nav_order() == ["/"]
    # 无 layout_id 写入也回退默认, 不报错
    assert preferences.set_nav_order(["/watchlist"]) == ["/watchlist"]
    assert preferences.load()["nav_order"] == ["/watchlist"]


def test_rename_nav_layout(_isolated):
    rec = preferences.create_nav_layout("短线")
    renamed = preferences.rename_nav_layout(rec["id"], "打板")
    assert renamed["name"] == "打板"
    assert preferences.get_nav_layouts()[1]["name"] == "打板"

    with pytest.raises(ValueError, match="不可重命名"):
        preferences.rename_nav_layout("", "x")
    preferences.create_nav_layout("另存")
    with pytest.raises(ValueError, match="已存在"):
        preferences.rename_nav_layout(rec["id"], "另存")


def test_delete_nav_layout_resets_active_to_default(_isolated):
    rec = preferences.create_nav_layout("短线")
    preferences.set_active_nav_layout(rec["id"])

    assert preferences.delete_nav_layout(rec["id"]) == rec["id"]
    assert [row["id"] for row in preferences.get_nav_layouts()] == [""]
    assert preferences.get_active_nav_layout() == ""

    with pytest.raises(ValueError, match="不可删除"):
        preferences.delete_nav_layout("")
    with pytest.raises(ValueError, match="不存在"):
        preferences.delete_nav_layout(rec["id"])


# ── API 路由 (薄胶水, 直接调函数单测) ────────────────────────────────────

def test_update_nav_order_forwards_layout_id(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.preferences.set_nav_order",
        lambda order, layout_id: (calls.append((order, layout_id)) or order),
    )
    result = settings.update_nav_order(
        settings.NavOrderIn(nav_order=["/a"], layout_id="l1")
    )
    assert calls == [(["/a"], "l1")]
    assert result == {"nav_order": ["/a"]}


def test_update_nav_order_bad_layout_id_400(monkeypatch):
    def boom(order, layout_id):
        raise ValueError("布局不存在")

    monkeypatch.setattr("app.services.preferences.set_nav_order", boom)
    with pytest.raises(HTTPException) as exc:
        settings.update_nav_order(settings.NavOrderIn(nav_order=[], layout_id="x"))
    assert exc.value.status_code == 400


def test_update_nav_hidden_forwards_layout_id(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.preferences.set_nav_hidden",
        lambda hidden, layout_id: (calls.append((hidden, layout_id)) or hidden),
    )
    result = settings.update_nav_hidden(
        settings.NavHiddenIn(nav_hidden=["/x"], layout_id="")
    )
    assert calls == [(["/x"], "")]
    assert result == {"nav_hidden": ["/x"]}


def test_create_layout_route_forwards_name_and_source(monkeypatch):
    calls = []
    fake = {"id": "abc", "name": "短线", "nav_order": [], "nav_hidden": []}
    monkeypatch.setattr(
        "app.services.preferences.create_nav_layout",
        lambda name, source_layout_id: (
            calls.append((name, source_layout_id)) or fake
        ),
    )
    result = settings.create_nav_layout(
        settings.NavLayoutNameIn(name="短线", source_layout_id="")
    )
    assert calls == [("短线", "")]
    assert result == {"layout": fake}


def test_create_layout_route_rejects_duplicate_name_400(monkeypatch):
    def boom(name, source_layout_id=None):
        raise ValueError("布局名称已存在: 短线")

    monkeypatch.setattr("app.services.preferences.create_nav_layout", boom)
    with pytest.raises(HTTPException) as exc:
        settings.create_nav_layout(settings.NavLayoutNameIn(name="短线"))
    assert exc.value.status_code == 400


def test_rename_route_forwarding(monkeypatch):
    calls = []
    fake = {"id": "a", "name": "新名", "nav_order": [], "nav_hidden": []}
    monkeypatch.setattr(
        "app.services.preferences.rename_nav_layout",
        lambda layout_id, name: (calls.append((layout_id, name)) or fake),
    )
    result = settings.rename_nav_layout(settings.NavLayoutRenameIn(id="a", name="新名"))
    assert calls == [("a", "新名")]
    assert result == {"layout": fake}


def test_delete_route_forwarding_and_active_switch(monkeypatch):
    monkeypatch.setattr(
        "app.services.preferences.delete_nav_layout",
        lambda layout_id: layout_id,
    )
    assert settings.delete_nav_layout(settings.NavLayoutIdIn(id="a")) == {"layout_id": "a"}

    monkeypatch.setattr(
        "app.services.preferences.set_active_nav_layout",
        lambda layout_id: layout_id,
    )
    assert settings.set_active_nav_layout(settings.NavLayoutIdIn(id="a")) == {
        "nav_active_layout": "a"
    }


def test_active_route_rejects_unknown_layout_400(monkeypatch):
    def boom(layout_id):
        raise ValueError("布局不存在")

    monkeypatch.setattr("app.services.preferences.set_active_nav_layout", boom)
    with pytest.raises(HTTPException) as exc:
        settings.set_active_nav_layout(settings.NavLayoutIdIn(id="nope"))
    assert exc.value.status_code == 400
