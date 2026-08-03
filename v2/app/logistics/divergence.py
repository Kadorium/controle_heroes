"""Tolerância provisória de divergência física — L-001.

PROVISIONAL L-001: não é política definitiva de Reconciliation.
Ajustar somente aqui; banner UI consome `is_significant`.
"""

from __future__ import annotations

from decimal import Decimal

# PROVISIONAL L-001 — single source of truth for physical divergence significance
WEIGHT_ABS_KG = Decimal("0.05")
WEIGHT_REL = Decimal("0.001")
VOLUME_ABS_M3 = Decimal("0.00001")
VOLUME_REL = Decimal("0.001")


def _sig_continuous(declared: Decimal | None, derived: Decimal | None, *, abs_tol: Decimal, rel: Decimal) -> bool:
    if declared is None or derived is None:
        return False
    diff = abs(declared - derived)
    if diff == 0:
        return False
    base = max(abs(declared), abs(derived), Decimal("1"))
    return diff > max(abs_tol, rel * base)


def weight_significant(declared: Decimal | None, derived: Decimal | None) -> bool:
    return _sig_continuous(declared, derived, abs_tol=WEIGHT_ABS_KG, rel=WEIGHT_REL)


def volume_significant(declared: Decimal | None, derived: Decimal | None) -> bool:
    return _sig_continuous(declared, derived, abs_tol=VOLUME_ABS_M3, rel=VOLUME_REL)


def count_significant(declared: int | None, derived: int | None) -> bool:
    if declared is None or derived is None:
        return False
    return abs(declared - derived) >= 1
