"""Integridade FX — excesso sequencial, concorrência, orphan cleanup, rounding."""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from sqlalchemy.orm import sessionmaker

from app.audit import public as audit_public
from app.foundation.settings import get_settings
from app.treasury import fx_commands as fx
from app.treasury.fx_models import FxExecutionAllocation, FxPlanRate
from app.treasury.fx_money import money2


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _issued_payable_1000(client):
    sku = f"FXI-{_uid()}"
    s = client.post("/api/suppliers", json={"name": f"Sup-{_uid()}", "country_code": "IT"}).json()
    p = client.post("/api/products", json={"sku": sku, "description": "Item"}).json()
    o = client.post(
        "/api/orders",
        json={"code": f"ORD-{_uid()}", "supplier_id": s["id"], "currency": "EUR"},
    ).json()
    o = client.post(
        f"/api/orders/{o['id']}/items",
        json={
            "expected_version": o["version"],
            "product_id": p["id"],
            "quantity": "10",
            "unit_price": "100",
        },
    ).json()
    o = client.post(f"/api/orders/{o['id']}/confirm", json={"expected_version": o["version"]}).json()
    inv = client.post(
        f"/api/orders/{o['id']}/invoices",
        json={"invoice_number": f"F-{_uid()}"},
    ).json()
    item = inv["items"][0]
    inv = client.put(
        f"/api/invoices/{inv['id']}/items",
        json={
            "expected_version": inv["version"],
            "items": [
                {
                    "order_item_id": item["order_item_id"],
                    "quantity": "10",
                    "unit_price_gross": "100",
                    "discount_type": "NONE",
                }
            ],
        },
    ).json()
    today = date.today()
    inv = client.put(
        f"/api/invoices/{inv['id']}/terms",
        json={
            "expected_version": inv["version"],
            "mode": "AMOUNT",
            "terms": [{"due_date": today.isoformat(), "amount": "1000"}],
        },
    ).json()
    client.post(
        "/api/documents",
        files={"file": ("f.pdf", BytesIO(b"%PDF"), "application/pdf")},
        data={"entity_type": "invoice", "entity_id": str(inv["id"]), "role": "official"},
    )
    inv = client.post(
        f"/api/invoices/{inv['id']}/issue",
        json={"expected_version": inv["version"]},
    ).json()
    return s, inv, inv["payables"][0]


def _payment_alloc_exec(client, supplier_id, payable, amount="400"):
    pay = client.post(
        "/api/payments",
        json={
            "supplier_id": supplier_id,
            "amount": amount,
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    ).json()
    r = client.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"fx-{_uid()}",
            "allocations": [
                {
                    "payable_id": payable["id"],
                    "amount": amount,
                    "expected_version": payable["version"],
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    pay = r.json()
    ex = client.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": amount,
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    ).json()
    return pay, pay["allocations"][0], ex


def test_link_excess_sequential_blocked(admin_client):
    c = admin_client
    s, _, payable = _issued_payable_1000(c)
    c.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay = c.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "amount": "400",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    ).json()
    r = c.post(
        f"/api/payments/{pay['id']}/allocations",
        json={
            "expected_version": pay["version"],
            "idempotency_key": f"a1-{_uid()}",
            "allocations": [
                {"payable_id": payable["id"], "amount": "200", "expected_version": payable["version"]},
            ],
        },
    )
    assert r.status_code == 200, r.text
    pay = r.json()
    alloc1 = pay["allocations"][0]
    ex = c.post(
        f"/api/payments/{pay['id']}/fx-executions",
        json={
            "foreign_amount": "200",
            "rate": "6.20",
            "execution_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "FX_NO_DOC",
        },
    ).json()
    r = c.post(
        "/api/fx/execution-allocations",
        json={
            "fx_execution_id": ex["id"],
            "payment_allocation_id": alloc1["id"],
            "foreign_amount": "300",
        },
    )
    assert r.status_code == 400
    msg = r.json().get("message", "")
    assert ("inválido" in msg) or ("excede" in msg)


def test_brl_prorata_rounding(admin_client, db):
    c = admin_client
    s, _, payable = _issued_payable_1000(c)
    c.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay, alloc, ex = _payment_alloc_exec(c, s["id"], payable, amount="100")
    # force domain call: foreign partial 33.33 of exec 100 / brl = 620 → ba = money2(620*33.33/100)
    link = fx.link_execution_allocation(
        db,
        fx_execution_id=ex["id"],
        payment_allocation_id=alloc["id"],
        foreign_amount="33.33",
        created_by_actor_id="test",
    )
    db.commit()
    expected = money2(Decimal(ex["brl_amount"]) * (Decimal("33.33") / Decimal(ex["foreign_amount"])))
    assert link.brl_amount == expected


def test_fx_orphan_cleanup_on_audit_fail(admin_client, monkeypatch):
    c = admin_client
    s, _, payable = _issued_payable_1000(c)
    c.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay = c.post(
        "/api/payments",
        json={
            "supplier_id": s["id"],
            "amount": "100",
            "currency": "EUR",
            "payment_date": date.today().isoformat(),
            "register_without_document": True,
            "reason_code": "TEST_OVERRIDE",
        },
    ).json()

    settings = get_settings()
    before = set(settings.attachments_path.rglob("*")) if settings.attachments_path.exists() else set()

    def boom(*_a, **_k):
        raise RuntimeError("audit fail fx")

    monkeypatch.setattr(audit_public, "record_event", boom)
    with pytest.raises(RuntimeError, match="audit fail fx"):
        c.post(
            f"/api/payments/{pay['id']}/fx-executions/with-document",
            data={
                "foreign_amount": "100",
                "rate": "6.20",
                "execution_date": date.today().isoformat(),
            },
            files={"file": ("fx.pdf", BytesIO(b"%PDF-fx-orphan"), "application/pdf")},
        )
    monkeypatch.undo()
    after = set(settings.attachments_path.rglob("*")) if settings.attachments_path.exists() else set()
    new_files = [p for p in (after - before) if p.is_file()]
    assert new_files == [], f"Arquivos órfãos: {new_files}"
    assert c.get(f"/api/payments/{pay['id']}/fx-executions").json() == []


def test_concurrent_initial_plan_one_current(admin_client, engine):
    c = admin_client
    _, _, payable = _issued_payable_1000(c)
    pid = payable["id"]
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def worker(rate: str):
        db = SessionLocal()
        try:
            barrier.wait(timeout=10)
            try:
                fx.register_plan_rate(
                    db,
                    payable_id=pid,
                    kind="INITIAL",
                    rate=rate,
                    effective_from=date.today(),
                    created_by_actor_id="conc",
                )
                db.commit()
                with lock:
                    results.append("ok")
            except Exception as exc:
                db.rollback()
                with lock:
                    results.append(type(exc).__name__)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(worker, "6.00")
        f2 = pool.submit(worker, "6.01")
        f1.result(timeout=30)
        f2.result(timeout=30)

    assert results.count("ok") == 1, results
    db = SessionLocal()
    try:
        currents = (
            db.query(FxPlanRate)
            .filter(FxPlanRate.payable_id == pid, FxPlanRate.is_current.is_(True))
            .all()
        )
        assert len(currents) == 1
    finally:
        db.close()


def test_concurrent_link_one_wins(admin_client, engine):
    c = admin_client
    s, _, payable = _issued_payable_1000(c)
    c.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay, alloc, ex = _payment_alloc_exec(c, s["id"], payable, amount="400")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def worker():
        db = SessionLocal()
        try:
            barrier.wait(timeout=10)
            try:
                fx.link_execution_allocation(
                    db,
                    fx_execution_id=ex["id"],
                    payment_allocation_id=alloc["id"],
                    foreign_amount="400",
                    created_by_actor_id="conc",
                )
                db.commit()
                with lock:
                    results.append("ok")
            except Exception as exc:
                db.rollback()
                with lock:
                    results.append(type(exc).__name__)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(worker)
        f2 = pool.submit(worker)
        f1.result(timeout=30)
        f2.result(timeout=30)

    assert results.count("ok") == 1, results
    db = SessionLocal()
    try:
        n = (
            db.query(FxExecutionAllocation)
            .filter(FxExecutionAllocation.payment_allocation_id == alloc["id"])
            .count()
        )
        assert n == 1
    finally:
        db.close()


def test_link_rollback_no_partial(admin_client, db, monkeypatch):
    c = admin_client
    s, _, payable = _issued_payable_1000(c)
    c.post(
        f"/api/payables/{payable['id']}/fx-plan",
        json={"kind": "INITIAL", "rate": "6.00", "effective_from": date.today().isoformat()},
    )
    pay, alloc, ex = _payment_alloc_exec(c, s["id"], payable, amount="400")

    def boom(*_a, **_k):
        raise RuntimeError("audit fail link")

    monkeypatch.setattr(audit_public, "record_event", boom)
    with pytest.raises(RuntimeError, match="audit fail link"):
        c.post(
            "/api/fx/execution-allocations",
            json={"fx_execution_id": ex["id"], "payment_allocation_id": alloc["id"]},
        )
    monkeypatch.undo()
    n = (
        db.query(FxExecutionAllocation)
        .filter(FxExecutionAllocation.payment_allocation_id == alloc["id"])
        .count()
    )
    assert n == 0
