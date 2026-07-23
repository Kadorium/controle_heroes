"""Fórmulas FX Inc-4 — benchmarks nomeados; positivo = favorável."""

from decimal import Decimal, ROUND_HALF_UP
from typing import NamedTuple


def money2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rate6(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def parse_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if s == "":
        return None
    return Decimal(s)


def to_brl(foreign_amount: Decimal, rate: Decimal) -> Decimal:
    return money2(foreign_amount * rate)


def realized_result_vs_reference(
    settled_foreign: Decimal, frozen_reference_rate: Decimal, realized_rate: Decimal
) -> Decimal:
    return money2(settled_foreign * (frozen_reference_rate - realized_rate))


def realized_result_vs_initial(
    settled_foreign: Decimal, initial_rate: Decimal, realized_rate: Decimal
) -> Decimal:
    return money2(settled_foreign * (initial_rate - realized_rate))


def online_result_vs_current(
    open_foreign: Decimal, current_forecast_rate: Decimal, market_rate: Decimal
) -> Decimal:
    return money2(open_foreign * (current_forecast_rate - market_rate))


def online_result_vs_initial(
    open_foreign: Decimal, initial_rate: Decimal, market_rate: Decimal
) -> Decimal:
    return money2(open_foreign * (initial_rate - market_rate))


def weighted_rate(foreign_total: Decimal, brl_total: Decimal) -> Decimal | None:
    if foreign_total <= 0:
        return None
    return rate6(brl_total / foreign_total)


class CanonicalScenario(NamedTuple):
    realized_brl: Decimal
    realized_vs_reference: Decimal
    realized_vs_initial: Decimal
    projected_open_brl: Decimal
    market_open_brl: Decimal
    online_vs_current: Decimal
    online_vs_initial: Decimal
    total_vs_current: Decimal
    total_vs_initial: Decimal


def canonical_scenario_numbers() -> CanonicalScenario:
    """INITIAL=6.00, REFORECAST=6.10, MARKET=6.25, ALLOC=400@6.20, OPEN=600."""
    settled = Decimal("400")
    open_f = Decimal("600")
    initial = Decimal("6.00")
    current = Decimal("6.10")
    market = Decimal("6.25")
    realized = Decimal("6.20")
    r_brl = to_brl(settled, realized)
    r_ref = realized_result_vs_reference(settled, current, realized)
    r_ini = realized_result_vs_initial(settled, initial, realized)
    proj = to_brl(open_f, current)
    mkt = to_brl(open_f, market)
    o_cur = online_result_vs_current(open_f, current, market)
    o_ini = online_result_vs_initial(open_f, initial, market)
    return CanonicalScenario(
        realized_brl=r_brl,
        realized_vs_reference=r_ref,
        realized_vs_initial=r_ini,
        projected_open_brl=proj,
        market_open_brl=mkt,
        online_vs_current=o_cur,
        online_vs_initial=o_ini,
        total_vs_current=money2(r_ref + o_cur),
        total_vs_initial=money2(r_ini + o_ini),
    )
