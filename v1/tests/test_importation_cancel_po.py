"""Testes anulação de ordem e reuso de PO."""

import uuid


def test_cancel_releases_po_number_for_reuse(admin_client, db):
    uid = uuid.uuid4().hex[:8]
    po = f"PO-CANCEL-{uid}"
    sup = admin_client.post(
        "/api/suppliers",
        json={"name": f"Sup Cancel {uid}", "country": "IT", "currency_default": "EUR"},
    ).json()
    created = admin_client.post(
        "/api/importations",
        json={"po_number": po, "supplier_id": sup["id"], "currency": "EUR"},
    )
    assert created.status_code == 201
    imp_id = created.json()["id"]

    cancel = admin_client.post(f"/api/importations/{imp_id}/cancel", json={"reason": "Teste anulação PO"})
    assert cancel.status_code == 200
    assert cancel.json()["is_active"] is False
    assert cancel.json()["po_number"].endswith(f"~anulado-{imp_id}")

    queue = admin_client.get("/api/importations/order-queue").json()
    assert not any(i["id"] == imp_id for i in queue["items"])

    again = admin_client.post(
        "/api/importations",
        json={"po_number": po, "supplier_id": sup["id"], "currency": "EUR"},
    )
    assert again.status_code == 201
    assert again.json()["po_number"] == po
    assert again.json()["is_active"] is True

    queue2 = admin_client.get("/api/importations/order-queue").json()
    assert any(i["po_number"] == po for i in queue2["items"])
