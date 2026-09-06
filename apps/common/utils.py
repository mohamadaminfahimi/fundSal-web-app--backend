from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MONEY_QUANTIZE = Decimal("0.01")
WEIGHT_QUANTIZE = Decimal("0.0001")
PERCENT_QUANTIZE = Decimal("0.0001")


def quantize_money(value: Decimal | str | int | float) -> Decimal:
    """اعداد مالی را به دقت استاندارد پروژه رند می‌کند."""
    return Decimal(str(value)).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)


def quantize_weight(value: Decimal | str | int | float) -> Decimal:
    """وزن فلزات را به دقت استاندارد رند می‌کند."""
    return Decimal(str(value)).quantize(WEIGHT_QUANTIZE, rounding=ROUND_HALF_UP)


def quantize_percentage(value: Decimal | str | int | float) -> Decimal:
    """درصدها را با دقت استاندارد رند می‌کند."""
    return Decimal(str(value)).quantize(PERCENT_QUANTIZE, rounding=ROUND_HALF_UP)


def safe_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """محاسبات مالی را از مقادیر نامعتبر و None محافظت می‌کند."""
    if value in (None, "", "None"):
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default
