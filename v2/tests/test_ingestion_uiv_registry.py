"""J3-UIV — adapter registry + row add/remove + classify API."""

from __future__ import annotations

import io

import pytest

from app.ingestion.adapter_registry import (
    classify_occurrence_bytes,
    list_adapters,
    resolve_adapter_id,
)


def test_registry_lists_eight_adapters():
    ids = {e.adapter_id for e in list_adapters()}
    assert "ordine_heroes_v1" in ids
    assert "packing_list_detail_v1" in ids
    assert "fattura_doganale_v1" in ids
    assert len(ids) == 8


def test_resolve_adapter_by_doc_type():
    assert resolve_adapter_id(adapter_id=None, doc_type="FATTURA_VENDITA") == "fattura_heroes_v1"
    assert resolve_adapter_id(adapter_id=None, doc_type="PACKING_LIST_GROUPED") == (
        "packing_list_grouped_v1"
    )


def test_classify_hints_ordine_filename():
    hits = classify_occurrence_bytes(
        b"%PDF-1.4",
        filename="Ordine_589.pdf",
        detected_mime="application/pdf",
    )
    assert any(h["adapter_id"] == "ordine_heroes_v1" for h in hits)


def test_list_adapters_api(admin_client):
    r = admin_client.get("/api/ingestion/adapters")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 8
    assert all("adapter_id" in a and "doc_type" in a for a in body)


def test_run_adapter_empty_body_still_ordine(admin_client, monkeypatch):
    """Compat: POST sem body continua default Ordine (pode falhar se fixture ausente)."""
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "ingestion"
        / "corpus_589"
        / "Ordine_589.pdf"
    )
    if not fixture.is_file():
        pytest.skip("Ordine_589.pdf fixture missing")

    br = admin_client.post("/api/ingestion/batches", json={"notes": "uiv-reg"})
    assert br.status_code == 200
    batch_id = br.json()["id"]
    with fixture.open("rb") as f:
        ur = admin_client.post(
            f"/api/ingestion/batches/{batch_id}/files",
            files={"files": ("Ordine_589.pdf", f, "application/pdf")},
        )
    assert ur.status_code == 200
    occ_id = ur.json()["results"][0]["id"]

    cr = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/classify")
    assert cr.status_code == 200
    assert "suggestions" in cr.json()

    rr = admin_client.post(f"/api/ingestion/occurrences/{occ_id}/run-adapter")
    assert rr.status_code == 200
    assert rr.json()["doc_type"] == "ORDINE_COMPRA"
    doc_id = rr.json()["id"]

    # add + remove row
    ar = admin_client.post(
        f"/api/ingestion/documents/{doc_id}/rows",
        json={"cells": {"sku": {"raw": "X"}}, "expected_version": rr.json()["version"]},
    )
    assert ar.status_code == 201
    row_id = ar.json()["id"]
    dr = admin_client.delete(
        f"/api/ingestion/rows/{row_id}?expected_version={ar.json()['version']}"
    )
    assert dr.status_code == 204
