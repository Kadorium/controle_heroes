"""Preview standalone Heroes — sku_review_groups no response."""

from __future__ import annotations

import uuid

import pytest
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx

pytestmark = pytest.mark.usefixtures("admin_client")


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_standalone_preview_returns_sku_review_groups(admin_client):
    content = build_ordine_758_xlsx()
    upload = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={"file": ("o.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code in (200, 201)
    raw_id = upload.json()["raw_file_id"]
    sheets = upload.json()["sheets"]
    sheet_name = next((s["sheet_name"] for s in sheets if "758" in s.get("sheet_name", "")), sheets[0]["sheet_name"])

    prev = admin_client.post(
        "/api/imports/heroes/xlsx/preview",
        json={"raw_file_id": raw_id, "sheet_name": sheet_name},
    )
    assert prev.status_code == 200, prev.text
    body = prev.json()

    assert "sku_review_open_count" in body
    assert "sku_review_groups" in body
    assert isinstance(body["sku_review_groups"], list)
    assert "sku_review_pending" in body


def test_standalone_commit_blocks_unresolved_sku(admin_client, db):
    uid = uuid.uuid4().hex[:8]
    content = build_ordine_758_xlsx()
    upload = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={"file": ("o.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    raw_id = upload.json()["raw_file_id"]
    sheets = upload.json()["sheets"]
    sheet_name = next((s["sheet_name"] for s in sheets if "758" in s.get("sheet_name", "")), sheets[0]["sheet_name"])

    prev = admin_client.post(
        "/api/imports/heroes/xlsx/preview",
        json={"raw_file_id": raw_id, "sheet_name": sheet_name},
    )
    body = prev.json()
    if body.get("sku_review_open_count", 0) == 0:
        pytest.skip("Todos SKUs já resolvidos no cadastro de teste")

    run_id = body["run_id"]
    blocked = admin_client.post(
        "/api/imports/heroes/xlsx/commit",
        json={
            "run_id": run_id,
            "confirm_import": True,
            "confirm_sheet_match": True,
            "confirm_financial_review": True,
            "opening_exchange_rate": "6.10",
        },
    )
    assert blocked.status_code == 400
    assert "SKU" in blocked.json().get("detail", "")
