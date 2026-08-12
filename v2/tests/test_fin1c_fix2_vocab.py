"""FIN-1C-FIX-2 — paymentAllocationStateLabel."""

from __future__ import annotations


def test_payment_allocation_state_label_via_frontend_contract():
    """Espelho do canônico FE (crédito em aberto / parcial / total)."""

    def label(status: str, allocated: str, unallocated: str) -> str:
        if status.upper() == "CANCELLED":
            return "Cancelado"
        a = float(allocated)
        u = float(unallocated)
        if a <= 0:
            return "crédito em aberto"
        if u > 0:
            return "parcialmente alocado"
        return "totalmente alocado"

    assert label("REGISTERED", "0", "1000") == "crédito em aberto"
    assert label("REGISTERED", "400", "600") == "parcialmente alocado"
    assert label("REGISTERED", "1000", "0") == "totalmente alocado"
    assert label("CANCELLED", "0", "1000") == "Cancelado"
