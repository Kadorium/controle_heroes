"""Customs I5-3B — Payable Customs + FundingPayableLink."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from alembic.config import Config
from alembic.script import ScriptDirectory


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _process(client):
    r = client.post("/api/import-processes", json={"external_reference": f"DUIMP-{_uid()}"})
    assert r.status_code == 201, r.text
    return r.json()


def _payee(client, *, name="Bechtrans", **extra):
    body = {"name": name, **extra}
    r = client.post("/api/customs/payees", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _funding(client, process_id: int, payee_id: int, **extra):
    body = {
        "payee_id": payee_id,
        "currency": "BRL",
        "declared_total": "1500.00",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        **extra,
    }
    r = client.post(f"/api/import-processes/{process_id}/funding-requests", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_migration_014_revises_013():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("014")
    assert rev is not None
    assert rev.down_revision == "013"
    assert script.get_revision("013").down_revision == "012"


def test_confirm_creates_payable_and_link(admin_client, db):
    from app.billing.models import Payable
    from app.customs.models import FundingPayableLink

    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Bechtrans-{_uid()}")
    fr = _funding(client, process["id"], payee["id"], declared_total="2500.50")

    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "CONFIRMED"
    assert len(out["payable_links"]) == 1
    link = out["payable_links"][0]
    assert link["sequence"] == 1
    assert Decimal(link["amount"]) == Decimal("2500.50")

    payable = db.query(Payable).filter(Payable.id == link["payable_id"]).one()
    assert payable.invoice_id is None
    assert payable.payment_term_id is None
    assert payable.source_type == "CUSTOMS_FUNDING"
    assert payable.source_id == fr["id"]
    assert payable.sequence == 1
    assert payable.status == "OPEN"
    assert payable.payee_display_name == payee["name"]
    assert Decimal(payable.amount) == Decimal("2500.50")
    assert payable.balance == payable.amount

    db_link = (
        db.query(FundingPayableLink)
        .filter(FundingPayableLink.funding_request_id == fr["id"])
        .one()
    )
    assert db_link.payable_id == payable.id


def test_confirm_idempotent(admin_client, db):
    from app.billing.models import Payable
    from app.customs.models import FundingPayableLink

    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")
    fr = _funding(client, process["id"], payee["id"], declared_total="100")

    r1 = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r1.status_code == 200, r1.text
    fr1 = r1.json()
    pid = fr1["payable_links"][0]["payable_id"]

    r2 = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr1["version"]},
    )
    assert r2.status_code == 200, r2.text
    fr2 = r2.json()
    assert len(fr2["payable_links"]) == 1
    assert fr2["payable_links"][0]["payable_id"] == pid

    assert db.query(Payable).filter(Payable.source_type == "CUSTOMS_FUNDING", Payable.source_id == fr["id"]).count() == 1
    assert db.query(FundingPayableLink).filter(FundingPayableLink.funding_request_id == fr["id"]).count() == 1


def test_cancel_confirmed_open_payable(admin_client, db):
    from app.billing.models import Payable

    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")
    fr = _funding(client, process["id"], payee["id"], declared_total="80")
    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    pid = fr["payable_links"][0]["payable_id"]

    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/cancel",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CANCELLED"

    payable = db.query(Payable).filter(Payable.id == pid).one()
    assert payable.status == "CANCELLED"


def test_cancel_confirmed_blocked_when_partially_paid(admin_client, db):
    from app.billing.models import Payable
    from app.foundation.uow import UnitOfWork

    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")
    fr = _funding(client, process["id"], payee["id"], declared_total="200")
    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    pid = fr["payable_links"][0]["payable_id"]

    # Simulate partial liquidation without Treasury allocation (balance proxy)
    with UnitOfWork(db) as uow:
        p = uow.session.query(Payable).filter(Payable.id == pid).one()
        p.balance = Decimal("100.00")
        p.status = "PARTIALLY_PAID"
        uow.commit()

    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/cancel",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 409, r.text


def test_customs_payable_not_in_eligible_list(admin_client, db):
    """Gap intencional I5-3B: INNER JOIN Invoice exclui CUSTOMS_FUNDING da alocação."""
    from app.billing import public as billing_public

    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")
    fr = _funding(client, process["id"], payee["id"], declared_total="99")
    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    pid = r.json()["payable_links"][0]["payable_id"]

    eligible = billing_public.list_eligible_payables(db, supplier_id=1, currency="BRL")
    assert all(p.id != pid for p in eligible)

    # AP queue still shows the customs payable
    queue = billing_public.payables_queue(db, limit=200)
    ids = {int(x["id"]) for x in queue["items"]}
    assert pid in ids
    row = next(x for x in queue["items"] if int(x["id"]) == pid)
    assert row["source_type"] == "CUSTOMS_FUNDING"
    assert row["payee_display_name"] == payee["name"]
    assert row["invoice_number"] is None


def test_commercial_payable_unique_invoice_sequence(admin_client, db):
    """Payables comerciais mantêm UNIQUE(invoice_id, sequence) parcial."""
    from app.billing.models import Payable
    from sqlalchemy.exc import IntegrityError

    # Two customs payables with same sequence but different source_id — OK
    p1 = Payable(
        invoice_id=None,
        payment_term_id=None,
        sequence=1,
        due_date=date.today(),
        amount=Decimal("10"),
        balance=Decimal("10"),
        currency="BRL",
        status="OPEN",
        source_type="CUSTOMS_FUNDING",
        source_id=900001,
        payee_display_name="A",
    )
    p2 = Payable(
        invoice_id=None,
        payment_term_id=None,
        sequence=1,
        due_date=date.today(),
        amount=Decimal("20"),
        balance=Decimal("20"),
        currency="BRL",
        status="OPEN",
        source_type="CUSTOMS_FUNDING",
        source_id=900002,
        payee_display_name="B",
    )
    db.add_all([p1, p2])
    db.flush()

    # Duplicate (source_type, source_id, sequence) must fail
    dup = Payable(
        invoice_id=None,
        payment_term_id=None,
        sequence=1,
        due_date=date.today(),
        amount=Decimal("30"),
        balance=Decimal("30"),
        currency="BRL",
        status="OPEN",
        source_type="CUSTOMS_FUNDING",
        source_id=900001,
        payee_display_name="A2",
    )
    db.add(dup)
    try:
        db.flush()
        raise AssertionError("expected unique violation on source sequence")
    except IntegrityError:
        db.rollback()
