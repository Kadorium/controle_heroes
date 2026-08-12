"""Prepare epic_v2_test for J3-UIV manual advisor validation.

Run from v2/:
  set DATABASE_URL=postgresql://postgres@localhost:5433/epic_v2_test
  set APP_ENV=test
  .venv\\Scripts\\python docs/../scripts — actually path:
  .venv\\Scripts\\python scripts/prepare_j3_uiv_advisor.py

Only touches epic_v2_test. Does not change product code permissions silently.
Creates explicit test users with documented permission bundles.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5433/epic_v2_test")
if "epic_v2_test" not in DB_URL:
    raise SystemExit(f"REFUSED: DATABASE_URL must be epic_v2_test, got {DB_URL}")

os.environ["DATABASE_URL"] = DB_URL
os.environ["APP_ENV"] = "test"

from sqlalchemy.orm import Session

from app.foundation.database import SessionLocal
from app.foundation.settings import get_settings
from app.identity import public as identity_public
from app.identity.models import Role, User
from app.identity.security import hash_password
from app.identity.seed import ensure_seed


PASSWORD = "advisor123"

# Explicit test bundles — documented for advisor; not silent production role expansion.
TEST_USERS: list[dict] = [
    {
        "email": "comprador@epic.com.br",
        "name": "Comprador UIV",
        "role": "uiv_comprador",
        "description": "Upload/review ingestão; sem commit",
        "permissions": [
            "ingestion:read",
            "ingestion:write",
            "catalog:read",
            "orders:read",
            "documents:read",
        ],
    },
    {
        "email": "orders-commit@epic.com.br",
        "name": "Orders Commit UIV",
        "role": "uiv_orders_commit",
        "description": "Commit Ordine/XLSX (ingestion:commit + orders:write)",
        "permissions": [
            "ingestion:read",
            "ingestion:write",
            "ingestion:commit",
            "orders:read",
            "orders:write",
            "catalog:read",
            "catalog:write",
            "documents:read",
            "documents:write",
        ],
    },
    {
        "email": "billing-commit@epic.com.br",
        "name": "Billing Commit UIV",
        "role": "uiv_billing_commit",
        "description": "Commit Fattura (ingestion:commit + orders:write + billing:write)",
        "permissions": [
            "ingestion:read",
            "ingestion:write",
            "ingestion:commit",
            "orders:read",
            "orders:write",
            "billing:read",
            "billing:write",
            "catalog:read",
            "documents:read",
            "documents:write",
        ],
    },
    {
        "email": "logistics-commit@epic.com.br",
        "name": "Logistics Commit UIV",
        "role": "uiv_logistics_commit",
        "description": "Commit PL detail (ingestion:commit + logistics:write)",
        "permissions": [
            "ingestion:read",
            "ingestion:write",
            "ingestion:commit",
            "logistics:read",
            "logistics:write",
            "documents:read",
            "documents:write",
            "catalog:read",
        ],
    },
    {
        "email": "customs-commit@epic.com.br",
        "name": "Customs Commit UIV",
        "role": "uiv_customs_commit",
        "description": "Commit Doganale/Numerário (ingestion:commit + customs:write)",
        "permissions": [
            "ingestion:read",
            "ingestion:write",
            "ingestion:commit",
            "customs:read",
            "customs:write",
            "documents:read",
            "documents:write",
            "catalog:read",
        ],
    },
    {
        "email": "noaccess@epic.com.br",
        "name": "Sem Acesso UIV",
        "role": "uiv_no_access",
        "description": "Sem ingestion:* — deve ocultar rota ou 403",
        "permissions": ["documents:read"],
    },
]


def _ensure_role(db: Session, *, name: str, description: str, permissions: list[str]) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    desired = json.dumps(permissions)
    if role is None:
        role = Role(name=name, description=description, permissions_json=desired)
        db.add(role)
        db.flush()
        return role
    role.description = description
    role.permissions_json = desired
    db.flush()
    return role


def _ensure_user(db: Session, *, email: str, name: str, role: Role) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            name=name,
            password_hash=hash_password(PASSWORD),
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user
    user.name = name
    user.role_id = role.id
    user.password_hash = hash_password(PASSWORD)
    user.is_active = True
    db.flush()
    return user


def seed_catalog_and_order(db: Session) -> dict:
    from app.catalog import public as catalog_public
    from app.orders import public as orders_public
    from app.orders.models import Order

    suppliers = catalog_public.list_suppliers(db, q="Heroe", limit=5)
    if suppliers:
        supplier_id = suppliers[0].id
    else:
        supplier_id = catalog_public.create_supplier(
            db, name="Heroe's Srl", country_code="IT"
        ).id

    product_ids: dict[str, int] = {}
    for sku, desc in (
        ("I.V. 2", "racchette 2027 GRAFICATE"),
        ("I.V. 1", "racchette 2027"),
    ):
        try:
            product_ids[sku] = catalog_public.get_product_by_sku(db, sku).id
        except Exception:
            product_ids[sku] = catalog_public.create_product(
                db, sku=sku, description=desc
            ).id

    code = "ORD-UIV-ADVISOR-202"
    existing = db.query(Order).filter(Order.code == code).first()
    if existing is not None:
        order_id = existing.id
    else:
        order = orders_public.create_order(
            db,
            code=code,
            supplier_id=supplier_id,
            created_by_actor_id="advisor-prep",
            currency="EUR",
        )
        order = orders_public.add_item(
            db,
            order.id,
            expected_version=order.version,
            product_id=product_ids["I.V. 2"],
            quantity="10",
            unit_price="100",
        )
        order = orders_public.confirm_order(
            db,
            order.id,
            expected_version=order.version,
        )
        order_id = order.id

    return {
        "supplier_id": supplier_id,
        "products": product_ids,
        "order_confirmed_id": order_id,
        "order_code": code,
    }


def main() -> None:
    settings = get_settings()
    print(f"DATABASE_URL={DB_URL}")
    print(f"APP_ENV={settings.app_env}")
    print(f"quarantine={settings.quarantine_path}")

    db = SessionLocal()
    try:
        ensure_seed(
            db,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            name=settings.seed_admin_name,
        )
        identity_public.ensure_comprador_role(db)
        identity_public.ensure_aduana_role(db)
        identity_public.ensure_estoque_role(db)

        created = []
        for spec in TEST_USERS:
            role = _ensure_role(
                db,
                name=spec["role"],
                description=spec["description"],
                permissions=spec["permissions"],
            )
            user = _ensure_user(
                db, email=spec["email"], name=spec["name"], role=role
            )
            created.append(
                {
                    "email": user.email,
                    "role": role.name,
                    "permissions": spec["permissions"],
                }
            )

        owners = seed_catalog_and_order(db)
        db.commit()

        print("ADMIN", settings.seed_admin_email, "/ (settings password)")
        print("TEST_PASSWORD", PASSWORD)
        for row in created:
            print("USER", row["email"], "role=", row["role"])
        print("OWNERS", json.dumps(owners, ensure_ascii=False))
        print("DONE")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
