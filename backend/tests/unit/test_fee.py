"""费用计算单元测试。"""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.services.fee_service import calc_fee


def test_calc_fee_basic():
    assert calc_fee(Decimal("10000"), Decimal("0.05"), Decimal("0"), Decimal("0")) == Decimal("500.00")


def test_calc_fee_min_fee():
    assert calc_fee(Decimal("100"), Decimal("0.05"), Decimal("10"), Decimal("0")) == Decimal("10.00")


def test_calc_fee_max_fee():
    assert calc_fee(Decimal("100000"), Decimal("0.05"), Decimal("0"), Decimal("1000")) == Decimal("1000.00")


def test_calc_fee_zero():
    assert calc_fee(Decimal("0"), Decimal("0.05"), Decimal("0"), Decimal("0")) == Decimal("0.00")


def test_calc_fee_rounding():
    assert calc_fee(Decimal("99.99"), Decimal("0.05"), Decimal("0"), Decimal("0")) == Decimal("5.00")


@pytest.mark.parametrize(
    "amount,rate,expected",
    [
        (Decimal("2000"), Decimal("0.05"), Decimal("100.00")),
        (Decimal("3000"), Decimal("0.05"), Decimal("150.00")),
        (Decimal("5000"), Decimal("0.05"), Decimal("250.00")),
    ],
)
def test_calc_fee_parametrized(amount, rate, expected):
    assert calc_fee(amount, rate, Decimal("0"), Decimal("0")) == expected
