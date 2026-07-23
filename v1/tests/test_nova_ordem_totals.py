"""Totais Nova Ordem — desconto por unidade (regra de negócio)."""


def _line_totals(qty, price, disc_per_unit):
    gross = qty * price if qty is not None and price is not None else None
    discount = qty * disc_per_unit if qty is not None and disc_per_unit is not None else None
    net = gross - (discount if discount is not None else 0) if gross is not None else None
    return gross, discount, net


def test_per_unit_discount_not_flat_on_line():
    gross, discount, net = _line_totals(10, 12.5, 1.0)
    assert gross == 125.0
    assert discount == 10.0
    assert net == 115.0


def test_no_discount_keeps_gross():
    gross, discount, net = _line_totals(10, 12.5, None)
    assert gross == 125.0
    assert discount is None
    assert net == 125.0
