"""Vínculo raw_import_files ↔ ordem manual (Nova Ordem)."""

import uuid

import pytest

from app.core.enums import HeroesImportRunStatus
from app.models import HeroesImportRun
from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx


@pytest.fixture()
def admin_client(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@epic.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return client


def test_link_heroes_raw_to_manual_importation(admin_client, db):
    uid = uuid.uuid4().hex[:8]
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"Heroes Link {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    imp = admin_client.post(
        "/api/importations",
        json={
            "po_number": f"MANUAL-{uid}",
            "supplier_id": sup["id"],
            "currency": "EUR",
            "incoterm": "FOB",
        },
    ).json()

    content = build_ordine_758_xlsx()
    upload = admin_client.post(
        "/api/imports/heroes/xlsx/upload",
        files={
            "file": (
                "ordine758.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload.status_code == 201
    raw_id = upload.json()["raw_file_id"]

    link = admin_client.post(
        f"/api/importations/{imp['id']}/link-heroes-raw",
        json={"raw_file_id": raw_id},
    )
    assert link.status_code == 201
    body = link.json()
    assert body["importation_id"] == imp["id"]
    assert body["raw_file_id"] == raw_id
    assert body["status"] == HeroesImportRunStatus.ATTACHED.value

    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == body["run_id"]).first()
    assert run is not None
    assert run.importation_id == imp["id"]
    assert run.raw_file_id == raw_id

    link2 = admin_client.post(
        f"/api/importations/{imp['id']}/link-heroes-raw",
        json={"raw_file_id": raw_id},
    )
    assert link2.status_code == 201
    assert link2.json()["run_id"] == body["run_id"]
