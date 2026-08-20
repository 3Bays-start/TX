"""信用等级计算单元测试。"""

from __future__ import annotations

from app.models.credit import CreditLevel
from app.services.credit_service import compute_credit


def _levels() -> list[CreditLevel]:
    def mk(name: str, code: str, min_orders: int) -> CreditLevel:
        return CreditLevel(name=name, code=code, min_orders=min_orders, status="ACTIVE", sort_order=0)

    return [
        mk("普通信用", "BASIC", 0),
        mk("铜牌信用", "BRONZE", 3),
        mk("银牌信用", "SILVER", 10),
        mk("金牌信用", "GOLD", 30),
        mk("钻石信用", "DIAMOND", 80),
    ]


def test_basic_level_at_zero():
    data = compute_credit(0, _levels())
    assert data["current"]["code"] == "BASIC"
    assert data["next"]["code"] == "BRONZE"
    assert data["progress"] == 0
    assert data["need"] == 3


def test_level_up_on_completed_orders():
    assert compute_credit(3, _levels())["current"]["code"] == "BRONZE"
    assert compute_credit(10, _levels())["current"]["code"] == "SILVER"
    assert compute_credit(30, _levels())["current"]["code"] == "GOLD"
    assert compute_credit(80, _levels())["current"]["code"] == "DIAMOND"


def test_progress_and_top_level():
    # 3 -> 10 之间进度
    data = compute_credit(5, _levels())
    assert data["current"]["code"] == "BRONZE"
    assert data["next"]["code"] == "SILVER"
    assert data["progress"] == 29  # (5-3)/(10-3) ≈ 0.29
    assert data["need"] == 5

    # 达到最高等级后无下一级
    top = compute_credit(200, _levels())
    assert top["current"]["code"] == "DIAMOND"
    assert top["next"] is None
    assert top["progress"] == 100
