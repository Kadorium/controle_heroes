"""Moedas de importação — Epic/Heroes operam em EUR; USD legado é normalizado."""

from __future__ import annotations

from app.config import DEFAULT_IMPORT_CURRENCY

# Despesas aduaneiras / landed cost local permanecem em BRL.
LOCAL_CURRENCIES = frozenset({"BRL"})


def normalize_import_currency(code: str | None) -> str:
    """Importação, fatura e pagamento ao fornecedor: EUR. USD legado → EUR."""
    if not code or not str(code).strip():
        return DEFAULT_IMPORT_CURRENCY
    c = str(code).strip().upper()
    if c in LOCAL_CURRENCIES:
        return c
    if c == "USD":
        return DEFAULT_IMPORT_CURRENCY
    return c
