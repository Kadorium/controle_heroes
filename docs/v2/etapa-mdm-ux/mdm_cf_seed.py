"""Massa MDM-CF — ≥60 produtos só em epic_v2_test. Nunca toca epic_v2."""
from __future__ import annotations

import os
import sys
from pathlib import Path

URL = "postgresql://postgres@localhost:5433/epic_v2_test"
V2 = Path(__file__).resolve().parents[3] / "v2"
if str(V2) not in sys.path:
    sys.path.insert(0, str(V2))

os.environ["DATABASE_URL"] = URL
os.environ["APP_ENV"] = "test"


def main() -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.catalog.models import Product, Supplier
    from app.foundation.settings import get_settings
    from app.identity.seed import ensure_seed
    from app.inventory.repository import ensure_default_locations

    engine = create_engine(URL)
    with engine.connect() as conn:
        dbname = conn.execute(text("select current_database()")).scalar()
        if dbname != "epic_v2_test":
            raise SystemExit(f"REFUSED: current_database={dbname!r}")

    get_settings.cache_clear()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        settings = get_settings()
        ensure_seed(
            db,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            name=settings.seed_admin_name,
        )
        ensure_default_locations(db)

        suppliers = [
            Supplier(name="MDM Fornecedor Completo", country_code="IT", tax_id="02610500999", is_active=True),
            Supplier(name="MDM Fornecedor Sem Taxa", country_code="IT", is_active=True),
            Supplier(name="MDM Fornecedor BR", country_code="BR", tax_id="12345678000199", is_active=True),
            Supplier(name="MDM Fornecedor Inativo", country_code="IT", is_active=False),
        ]
        for s in suppliers:
            existing = db.query(Supplier).filter(Supplier.name == s.name).first()
            if not existing:
                db.add(s)
        db.flush()

        created = 0
        for i in range(1, 62):
            sku = f"MDM-SKU-{i:03d}"
            if db.query(Product).filter(Product.sku == sku).first():
                continue
            complete = i % 3 == 0
            inactive = i % 17 == 0
            db.add(
                Product(
                    sku=sku,
                    description=f"Produto massa {i:03d}",
                    is_active=not inactive,
                    ncm="61091000" if complete else None,
                    ean=f"7891000{i:06d}" if complete else None,
                    size="M" if i % 5 == 0 else None,
                    color="Preto" if i % 7 == 0 else None,
                    country_of_origin="IT" if complete else None,
                    unit="PZ",
                )
            )
            created += 1
        db.commit()
        total = db.query(Product).count()
        print(f"created={created} products_total={total}")
        if total < 60:
            raise SystemExit(f"expected >=60 products, got {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
