"""Referência de câmbio EUR/BRL — fontes públicas (não é cotação contratada)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx


def fetch_fx_reference(currency_from: str = "EUR", currency_to: str = "BRL") -> dict:
    """Busca cotação de referência. Falha com HTTPException detail se indisponível."""
    cur_from = currency_from.strip().upper()
    cur_to = currency_to.strip().upper()
    if cur_from != "EUR" or cur_to != "BRL":
        return {
            "currency_from": cur_from,
            "currency_to": cur_to,
            "rate": None,
            "rate_date": None,
            "source": None,
            "disclaimer": "Par de moedas não suportado para referência automática.",
        }

    errors: list[str] = []

    try:
        with httpx.Client(timeout=6.0) as client:
            r = client.get("https://api.frankfurter.app/latest", params={"from": "EUR", "to": "BRL"})
            r.raise_for_status()
            data = r.json()
            rate = data.get("rates", {}).get("BRL")
            if rate is not None:
                return {
                    "currency_from": "EUR",
                    "currency_to": "BRL",
                    "rate": str(Decimal(str(rate))),
                    "rate_date": data.get("date"),
                    "source": "Frankfurter (ECB)",
                    "disclaimer": "Referência de mercado; não equivale a cotação contratada ou PTAX.",
                }
    except Exception as exc:
        errors.append(f"Frankfurter: {exc}")

    try:
        with httpx.Client(timeout=6.0) as client:
            r = client.get("https://economia.awesomeapi.com.br/json/last/EUR-BRL")
            r.raise_for_status()
            data = r.json()
            row = data.get("EURBRL") or data.get("EUR-BRL")
            if row and row.get("bid"):
                bid = Decimal(str(row["bid"]))
                return {
                    "currency_from": "EUR",
                    "currency_to": "BRL",
                    "rate": str(bid),
                    "rate_date": str(date.today()),
                    "source": "AwesomeAPI (mercado)",
                    "disclaimer": "Referência de mercado; não equivale a cotação contratada ou PTAX.",
                }
    except Exception as exc:
        errors.append(f"AwesomeAPI: {exc}")

    return {
        "currency_from": cur_from,
        "currency_to": cur_to,
        "rate": None,
        "rate_date": None,
        "source": None,
        "disclaimer": "Referência indisponível no momento. Informe o câmbio manualmente.",
        "errors": errors,
    }
