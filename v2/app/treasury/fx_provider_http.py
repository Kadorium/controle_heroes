"""HttpFxQuoteProvider — Inc-4B (Frankfurter → AwesomeAPI), compatível com V1.

Endpoint canônico Frankfurter (2026-07): api.frankfurter.dev
(api.frankfurter.app responde 301 Location → .../v1/latest).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import httpx

from app.treasury.fx_provider import FxQuoteUnavailable, QuoteDTO

# URL canônica confirmada via Location do 301 de api.frankfurter.app
FRANKFURTER_LATEST_URL = "https://api.frankfurter.dev/v1/latest"
AWESOME_EUR_BRL_URL = "https://economia.awesomeapi.com.br/json/last/EUR-BRL"


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
            # follow_redirects=False: usamos URL canônica; redirect inesperado = falha → fallback
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                r = client.get(
                    FRANKFURTER_LATEST_URL,
                    params={"from": "EUR", "to": "BRL"},
                )
                if r.status_code in (301, 302, 307, 308):
                    loc = r.headers.get("Location", "")
                    if "frankfurter.dev" not in loc and "frankfurter.app" not in loc:
                        raise RuntimeError(f"Redirect Frankfurter não confiável: {loc}")
                    r = client.get(loc) if loc.startswith("http") else client.get(
                        f"https://api.frankfurter.dev{loc}" if loc.startswith("/") else loc
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
                errors.append("Frankfurter: resposta sem rates.BRL")
        except Exception as exc:
            errors.append(f"Frankfurter: {exc}")
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                r = client.get(AWESOME_EUR_BRL_URL)
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
                errors.append("AwesomeAPI: resposta sem bid")
        except Exception as exc:
            errors.append(f"AwesomeAPI: {exc}")
        raise FxQuoteUnavailable(
            "Cotação EUR/BRL indisponível. " + "; ".join(errors) if errors else "Cotação indisponível"
        )
