"""Abstração de cotação online — domínio sem HTTP concreto."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol


class FxQuoteUnavailable(Exception):
    def __init__(self, message: str = "Cotação indisponível"):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class QuoteDTO:
    foreign_currency: str
    base_currency: str
    rate: Decimal
    source: str
    observed_at: datetime
    retrieved_at: datetime


class FxQuoteProvider(Protocol):
    def get_latest_quote(self, foreign: str, base: str = "BRL") -> QuoteDTO: ...


class FixtureFxQuoteProvider:
    """Provider determinístico para testes."""

    def __init__(self, rate: str = "6.25", source: str = "FIXTURE"):
        self._rate = Decimal(rate)
        self._source = source

    def get_latest_quote(self, foreign: str, base: str = "BRL") -> QuoteDTO:
        foreign = foreign.upper()
        base = base.upper()
        if base != "BRL" or foreign not in ("EUR", "USD"):
            raise FxQuoteUnavailable(f"Par {foreign}/{base} não suportado")
        now = datetime.now(timezone.utc)
        return QuoteDTO(
            foreign_currency=foreign,
            base_currency=base,
            rate=self._rate,
            source=self._source,
            observed_at=now,
            retrieved_at=now,
        )


class ManualFxQuoteProvider:
    """Usa última cotação MANUAL já persistida — não busca externo."""

    def __init__(self, rate: Decimal, source: str = "MANUAL", observed_at: datetime | None = None):
        self._rate = rate
        self._source = source
        self._observed = observed_at or datetime.now(timezone.utc)

    def get_latest_quote(self, foreign: str, base: str = "BRL") -> QuoteDTO:
        now = datetime.now(timezone.utc)
        return QuoteDTO(
            foreign_currency=foreign.upper(),
            base_currency=base.upper(),
            rate=self._rate,
            source=self._source,
            observed_at=self._observed,
            retrieved_at=now,
        )


_default_provider: FxQuoteProvider | None = None


def set_quote_provider(provider: FxQuoteProvider | None) -> None:
    global _default_provider
    _default_provider = provider


def get_quote_provider() -> FxQuoteProvider | None:
    return _default_provider
