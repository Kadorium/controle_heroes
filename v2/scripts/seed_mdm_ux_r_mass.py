"""Seed massa MDM-UX-R em epic_v2_test — 55+ SKUs + fornecedor Heroes.

Uso (cwd=v2):
  .venv\\Scripts\\python.exe scripts/seed_mdm_ux_r_mass.py

Não faz DROP. Recusa epic_v2. Idempotente (SKU/code já existente = skip).
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from sqlalchemy.orm import Session

REQUIRED_DB = "epic_v2_test"
FORBIDDEN_DB = "epic_v2"


def _database_name(url: str) -> str:
    name = (urlparse(url).path or "").lstrip("/").split("?")[0]
    if not name:
        raise SystemExit(f"DATABASE_URL sem nome de banco: {url!r}")
    return name


def main() -> int:
    url = (
        os.environ.get("E2E_DATABASE_URL")
        or os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "postgresql://postgres@localhost:5433/epic_v2_test"
    )
    name = _database_name(url)
    if name == FORBIDDEN_DB:
        raise SystemExit(f"REFUSADO: URL aponta para {FORBIDDEN_DB}. Use apenas {REQUIRED_DB}.")
    if name != REQUIRED_DB:
        raise SystemExit(f"REFUSADO: database={name!r}. Exigido {REQUIRED_DB!r}.")
    os.environ["DATABASE_URL"] = url
    os.environ["APP_ENV"] = "test"

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    from app.catalog.commands import create_product, create_supplier, update_product
    from app.catalog.errors import SkuDuplicate, SupplierCodeDuplicate
    from app.catalog.models import Product, Supplier
    from app.foundation.database import SessionLocal
    from app.foundation.settings import get_settings

    get_settings.cache_clear()
    db: Session = SessionLocal()
    created = 0
    skipped = 0
    try:
        try:
            create_supplier(db, name="Heroes", code="HERO", country_code="IT")
            db.commit()
            created += 1
        except SupplierCodeDuplicate:
            db.rollback()
            skipped += 1
        if db.query(Supplier).filter(Supplier.name == "Heroes").count() == 0:
            existing = db.query(Supplier).filter(Supplier.code == "HERO").first()
            if existing is None:
                create_supplier(db, name="Heroes", country_code="IT")
                db.commit()
                created += 1

        for i in range(1, 56):
            sku = f"MDM-R-{i:03d}"
            description = "Fora da primeira página MDM" if i == 55 else f"Massa visual MDM {i}"
            try:
                row = create_product(db, sku=sku, description=description)
                db.commit()
                created += 1
            except SkuDuplicate:
                db.rollback()
                skipped += 1
                row = db.query(Product).filter(Product.sku == sku).one()

            if i == 1:
                update_product(
                    db,
                    row.id,
                    size="M",
                    size_set=True,
                    color="Red",
                    color_set=True,
                    country_of_origin="IT",
                    country_of_origin_set=True,
                    ncm="42029200",
                    ncm_set=True,
                    ean="7900000000001",
                    ean_set=True,
                )
                db.commit()
            elif i == 2:
                update_product(
                    db,
                    row.id,
                    size="L",
                    size_set=True,
                    color="Blue",
                    color_set=True,
                    is_active=False,
                )
                db.commit()

        total = db.query(Product).filter(Product.sku.like("MDM-R-%")).count()
        print(f"[seed_mdm_ux_r] created={created} skipped={skipped} mass_skus={total}")
        if total < 55:
            raise SystemExit(f"massa insuficiente: {total}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
