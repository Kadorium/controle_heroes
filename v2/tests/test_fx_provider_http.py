"""HttpFxQuoteProvider — MockTransport determinístico (sem rede)."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.treasury.fx_provider import FxQuoteUnavailable
from app.treasury.fx_provider_http import (
    AWESOME_EUR_BRL_URL,
    FRANKFURTER_LATEST_URL,
    HttpFxQuoteProvider,
)


def _frankfurter_ok() -> httpx.Response:
    return httpx.Response(
        200,
        json={"amount": 1.0, "base": "EUR", "date": "2026-07-23", "rates": {"BRL": 6.11}},
    )


def _awesome_ok() -> httpx.Response:
    return httpx.Response(200, json={"EURBRL": {"bid": "6.40"}})


def _patch_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    class FakeClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            kwargs.setdefault("follow_redirects", False)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.treasury.fx_provider_http.httpx.Client", FakeClient)


def test_frankfurter_success_source(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "frankfurter.dev" in str(request.url):
            return _frankfurter_ok()
        return httpx.Response(500, text="should not call awesome")

    _patch_client(monkeypatch, handler)
    dto = HttpFxQuoteProvider(timeout=1.0).get_latest_quote("EUR", "BRL")
    assert dto.source.startswith("Frankfurter")
    assert dto.rate == Decimal("6.11")
    assert dto.foreign_currency == "EUR"
    assert dto.base_currency == "BRL"
    assert dto.observed_at is not None
    assert dto.retrieved_at is not None


def test_frankfurter_controlled_redirect_still_frankfurter(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        calls.append(url)
        if "frankfurter.dev" in url and request.url.params.get("from") == "EUR":
            # primeira resposta: redirect controlado
            if len([c for c in calls if "frankfurter" in c]) == 1:
                return httpx.Response(
                    301,
                    headers={"Location": "https://api.frankfurter.dev/v1/latest?from=EUR&to=BRL"},
                )
            return _frankfurter_ok()
        return httpx.Response(500)

    _patch_client(monkeypatch, handler)
    dto = HttpFxQuoteProvider(timeout=1.0).get_latest_quote("EUR", "BRL")
    assert dto.source.startswith("Frankfurter")
    assert any("frankfurter.dev" in c for c in calls)


def test_frankfurter_fail_falls_back_awesome(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "frankfurter" in str(request.url):
            return httpx.Response(503, text="down")
        if "awesomeapi" in str(request.url):
            return _awesome_ok()
        return httpx.Response(404)

    _patch_client(monkeypatch, handler)
    dto = HttpFxQuoteProvider(timeout=1.0).get_latest_quote("EUR", "BRL")
    assert dto.source.startswith("AwesomeAPI")
    assert dto.rate == Decimal("6.40")


def test_both_providers_fail_explicit_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    _patch_client(monkeypatch, handler)
    with pytest.raises(FxQuoteUnavailable, match="indisponível"):
        HttpFxQuoteProvider(timeout=1.0).get_latest_quote("EUR", "BRL")


def test_untrusted_redirect_falls_back(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "frankfurter.dev" in url:
            return httpx.Response(301, headers={"Location": "https://evil.example/quote"})
        if "awesomeapi" in url:
            return _awesome_ok()
        return httpx.Response(500)

    _patch_client(monkeypatch, handler)
    dto = HttpFxQuoteProvider(timeout=1.0).get_latest_quote("EUR", "BRL")
    assert dto.source.startswith("AwesomeAPI")


def test_canonical_urls_constants():
    assert FRANKFURTER_LATEST_URL == "https://api.frankfurter.dev/v1/latest"
    assert "awesomeapi.com.br" in AWESOME_EUR_BRL_URL
