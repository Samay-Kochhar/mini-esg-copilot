from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas import UnitIn

ROUND_SCALE = Decimal("0.001")


def round_value(value: Decimal) -> Decimal:
    return value.quantize(ROUND_SCALE, rounding=ROUND_HALF_UP)


def to_tco2e(value: Decimal, unit: UnitIn) -> Decimal:
    converted = value / Decimal("1000") if unit == UnitIn.KG_CO2E else value
    return round_value(converted)

