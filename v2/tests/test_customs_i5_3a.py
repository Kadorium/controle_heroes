"""Customs I5-3A — Numerário: Payee + FundingRequest + linhas (Payable em I5-3B)."""

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


def test_migration_013_revises_012():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("013")
    assert rev is not None
    assert rev.down_revision == "012"
    # chain intact
    assert script.get_revision("012").down_revision == "011"


def test_payee_without_supplier(admin_client):
    client = admin_client
    p = _payee(
        client,
        name="Bechtrans Despachante",
        tax_id="12.345.678/0001-99",
        bank_name="Banco X",
        agency="0001",
        account="12345-6",
        pix_key="bechtrans@example.com",
    )
    assert p["name"] == "Bechtrans Despachante"
    assert "supplier_id" not in p
    assert p["tax_id"] == "12.345.678/0001-99"
    assert p["pix_key"] == "bechtrans@example.com"

    listed = client.get("/api/customs/payees").json()
    assert any(x["id"] == p["id"] for x in listed)

    r = client.patch(
        f"/api/customs/payees/{p['id']}",
        json={"bank_name": "Banco Y"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["bank_name"] == "Banco Y"


def test_empty_amount_not_zero_sum_and_divergence(admin_client):
    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")

    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests",
        json={
            "payee_id": payee["id"],
            "currency": "BRL",
            "declared_total": "1500.0000",
            "reference": "NUM-1",
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
            "idempotency_key": f"fund-{_uid()}",
        },
    )
    assert r.status_code == 201, r.text
    fr = r.json()
    assert fr["status"] == "DRAFT"
    assert fr["declared_total"] in ("1500.0000", "1500.0", "1500")
    assert fr["structured_total"] == "0"
    assert Decimal(fr["divergence"]) == Decimal("-1500") or Decimal(fr["divergence"]) == Decimal(
        "-1500.0000"
    )

    # bases: one with amount, one empty (None) — empty must NOT count as 0 in a way that
    # collapses distinction; sum ignores None
    r = client.put(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/value-bases",
        json={
            "expected_version": fr["version"],
            "lines": [
                {"position": 1, "label": "CIF", "code": "CIF", "amount": "1000", "currency": "BRL"},
                {
                    "position": 2,
                    "label": "EMPTY",
                    "code": "EMPTY",
                    "amount": None,
                    "currency": "BRL",
                },
                {"position": 3, "label": "ZERO", "code": "ZERO", "amount": "0", "currency": "BRL"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    empty = next(x for x in fr["value_bases"] if x["code"] == "EMPTY")
    zero = next(x for x in fr["value_bases"] if x["code"] == "ZERO")
    assert empty["amount"] is None
    assert zero["amount"] in ("0", "0.0000", "0.0")
    assert Decimal(fr["structured_total"]) == Decimal("1000")

    r = client.put(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/tax-lines",
        json={
            "expected_version": fr["version"],
            "lines": [{"position": 1, "label": "II", "code": "II", "amount": "300"}],
        },
    )
    assert r.status_code == 200, r.text
    fr = r.json()

    r = client.put(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/expense-lines",
        json={
            "expected_version": fr["version"],
            "lines": [{"position": 1, "label": "DSP", "code": "DSP", "amount": "200"}],
        },
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    assert Decimal(fr["structured_total"]) == Decimal("1500")
    assert Decimal(fr["divergence"]) == Decimal("0")


def test_idempotency_per_process(admin_client):
    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")
    key = f"idem-{_uid()}"

    r1 = client.post(
        f"/api/import-processes/{process['id']}/funding-requests",
        json={
            "payee_id": payee["id"],
            "currency": "BRL",
            "declared_total": "100",
            "idempotency_key": key,
        },
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        f"/api/import-processes/{process['id']}/funding-requests",
        json={
            "payee_id": payee["id"],
            "currency": "EUR",
            "declared_total": "999",
            "idempotency_key": key,
        },
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == r1.json()["id"]
    assert r2.json()["currency"] == "BRL"  # original preserved


def test_confirm_creates_payable_and_stays_immutable(admin_client, db):
    """I5-3B: confirm cria Payable; linhas permanecem imutáveis."""
    from app.billing.models import Payable

    client = admin_client
    process = _process(client)
    payee = _payee(client, name=f"Payee-{_uid()}")
    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests",
        json={
            "payee_id": payee["id"],
            "currency": "BRL",
            "declared_total": "50",
        },
    )
    assert r.status_code == 201, r.text
    fr = r.json()
    before = db.query(Payable).count()

    r = client.post(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/confirm",
        json={"expected_version": fr["version"]},
    )
    assert r.status_code == 200, r.text
    fr = r.json()
    assert fr["status"] == "CONFIRMED"
    assert fr["confirmed_at"] is not None
    assert len(fr["payable_links"]) == 1

    after = db.query(Payable).count()
    assert after == before + 1

    # immutable after confirm
    r = client.put(
        f"/api/import-processes/{process['id']}/funding-requests/{fr['id']}/value-bases",
        json={"expected_version": fr["version"], "lines": []},
    )
    assert r.status_code == 409


def test_funding_rbac_read_only(client, db, admin_client):
    import json

    from app.identity.models import Role, User
    from app.identity.security import hash_password

    role = Role(
        name=f"fund_ro_{_uid()}",
        description="ro",
        permissions_json=json.dumps(["customs:read"]),
    )
    db.add(role)
    db.flush()
    email = f"fundro-{_uid()}@example.com"
    user = User(
        email=email,
        name="ro",
        password_hash=hash_password("test123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    process = _process(admin_client)
    r = client.post("/api/auth/login", json={"email": email, "password": "test123"})
    assert r.status_code == 200
    assert (
        client.get(f"/api/import-processes/{process['id']}/funding-requests").status_code == 200
    )
    assert client.get("/api/customs/payees").status_code == 200
    assert client.post("/api/customs/payees", json={"name": "X"}).status_code == 403
    assert (
        client.post(
            f"/api/import-processes/{process['id']}/funding-requests",
            json={"payee_id": 1, "currency": "BRL", "declared_total": "1"},
        ).status_code
        == 403
    )


def test_public_helpers_structured_total(admin_client, db):
    from app.customs import public as customs_public
    from app.foundation.uow import UnitOfWork

    client = admin_client
    process = _process(client)
    with UnitOfWork(db) as uow:
        payee = customs_public.create_payee(uow.session, name=f"P-{_uid()}")
        fr = customs_public.create_funding_request(
            uow.session,
            process["id"],
            payee_id=payee.id,
            currency="BRL",
            declared_total="100",
        )
        fr = customs_public.replace_value_bases(
            uow.session,
            fr.id,
            expected_version=fr.version,
            lines=[
                {"label": "A", "amount": "40"},
                {"label": "B", "amount": None},
                {"label": "C", "amount": "60"},
            ],
        )
        assert customs_public.structured_total(fr) == Decimal("100")
        assert customs_public.funding_divergence(fr) == Decimal("0")
        uow.commit()
