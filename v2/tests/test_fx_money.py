"""Fórmulas FX — cenário canônico Inc-4 §6."""

from decimal import Decimal

from app.treasury.fx_money import (
    canonical_scenario_numbers,
    money2,
    online_result_vs_current,
    realized_result_vs_reference,
)


def test_canonical_scenario_minus_40_90_130():
    c = canonical_scenario_numbers()
    assert c.realized_brl == Decimal("2480.00")
    assert c.realized_vs_reference == Decimal("-40.00")
    assert c.realized_vs_initial == Decimal("-80.00")
    assert c.projected_open_brl == Decimal("3660.00")
    assert c.market_open_brl == Decimal("3750.00")
    assert c.online_vs_current == Decimal("-90.00")
    assert c.online_vs_initial == Decimal("-150.00")
    assert c.total_vs_current == Decimal("-130.00")
    assert c.total_vs_initial == Decimal("-230.00")


def test_post_reforecast_online_changes_realized_frozen():
    settled = Decimal("400")
    open_f = Decimal("600")
    realized = Decimal("6.20")
    frozen_ref = Decimal("6.10")  # freeze at current before reforecast
    market = Decimal("6.25")
    new_current = Decimal("6.15")

    vs_ref = realized_result_vs_reference(settled, frozen_ref, realized)
    online = online_result_vs_current(open_f, new_current, market)
    assert vs_ref == Decimal("-40.00")
    assert online == Decimal("-60.00")
    assert money2(vs_ref + online) == Decimal("-100.00")
