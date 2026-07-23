"""HttpFxQuoteProvider — Inc-4B (Frankfurter → AwesomeAPI), compatível com V1."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import httpx

from app.treasury.fx_provider import FxQuoteUnavailable, QuoteDTO


class HttpFxQuoteProvider:
    """Não deve ser importado pelo domínio de comandos — só via FxQuoteProvider."""

    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout

    def get_latest_quote(self, foreign: str, base: str = "BRL") -> QuoteDTO:
        foreign = foreign.strip().upper()
        base = base.strip().upper()
        if foreign != "EUR" or base != "BRL":
            raise FxQuoteUnavailable("Par automático suportado apenas EUR/BRL")
        errors: list[str] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.get(
                    "https://api.frankfurter.app/latest",
                    params={"from": "EUR", "to": "BRL"},
                )
                r.raise_for_status()
                data = r.json()
                rate = data.get("rates", {}).get("BRL")
                if rate is not None:
                    obs = datetime.fromisoformat(str(data.get("date")) + "T12:00:00+00:00")
                    now = datetime.now(timezone.utc)
                    return QuoteDTO(
                        foreign_currency="EUR",
                        base_currency="BRL",
                        rate=Decimal(str(rate)),
                        source="Frankfurter (ECB)",
                        observed_at=obs,
                        retrieved_at=now,
                    )
        except Exception as exc:
            errors.append(f"Frankfurter: {exc}")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.get("https://economia.awesomeapi.com.br/json/last/EUR-BRL")
                r.raise_for_status()
                data = r.json()
                row = data.get("EURBRL") or data.get("EUR-BRL")
                if row and row.get("bid"):
                    now = datetime.now(timezone.utc)
                    return QuoteDTO(
                        foreign_currency="EUR",
                        base_currency="BRL",
                        rate=Decimal(str(row["bid"])),
                        source="AwesomeAPI (mercado)",
                        observed_at=datetime.combine(date.today(), datetime.min.time()).replace(
                            tzinfo=timezone.utc
                        ),
                        retrieved_at=now,
                    )
        except Exception as exc:
            errors.append(f"AwesomeAPI: {exc}")
        raise FxQuoteUnavailable(
            "Cotação EUR/BRL indisponível. " + "; ".join(errors) if errors else "Cotação indisponível"
        )
