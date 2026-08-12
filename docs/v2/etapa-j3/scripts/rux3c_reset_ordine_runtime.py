#!/usr/bin/env python3
"""RUX-3C/3E — limpa fila de ingestão + remove Heroe's em epic_v2.

Uso (na pasta v2/):

  .\\.venv\\Scripts\\python.exe ..\\docs\\v2\\etapa-j3\\scripts\\rux3c_reset_ordine_runtime.py

Só age em epic_v2. Recusa epic_v2_test.

Remove Orders de ingestão em DRAFT (com ou sem linhas) desde que sem Invoice
e sem Shipment vinculados. Mantém travas se CONFIRMADO ou com vínculos.
Também repara (via DELETE da fila) docs REJECTED — a limpeza zera a fila.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "v2"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from sqlalchemy import create_engine, text  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5433/epic_v2")

INGESTION_TABLES = (
    "ingestion_commit_operations",
    "ingestion_commit_attempts",
    "ingestion_review_changes",
    "ingestion_issues",
    "ingestion_rows",
    "ingestion_fields",
    "ingestion_sections",
    "ingestion_document_set_members",
    "ingestion_document_sets",
    "ingestion_documents",
    "ingestion_occurrences",
    "ingestion_blobs",
    "ingestion_batches",
    "ingestion_metric_events",
)


def main() -> int:
    if "epic_v2_test" in DATABASE_URL:
        print("ABORT: recusa epic_v2_test — script só para runtime operacional epic_v2")
        return 2

    eng = create_engine(DATABASE_URL)
    with eng.begin() as conn:
        dbname = conn.execute(text("SELECT current_database()")).scalar()
        if dbname != "epic_v2":
            print(f"ABORT: current_database={dbname!r} (esperado epic_v2)")
            return 2

        orders = conn.execute(
            text(
                """
                SELECT id, code, status, source_system, external_ref FROM orders
                WHERE code IN ('589', 'ING-589')
                   OR code LIKE 'ING-%'
                   OR code LIKE '589%'
                   OR (source_system = 'INGESTION' AND status = 'DRAFT')
                ORDER BY id
                """
            )
        ).fetchall()

        for oid, code, status, source_system, external_ref in orders:
            st = (status or "").upper()
            items = conn.execute(
                text("SELECT COUNT(*) FROM order_items WHERE order_id = :oid"),
                {"oid": oid},
            ).scalar()
            invoices = conn.execute(
                text("SELECT COUNT(*) FROM invoices WHERE order_id = :oid"),
                {"oid": oid},
            ).scalar()
            shipments = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM shipment_items si
                    JOIN order_items oi ON oi.id = si.order_item_id
                    WHERE oi.order_id = :oid
                    """
                ),
                {"oid": oid},
            ).scalar()

            if invoices or shipments:
                print(
                    f"ABORT: pedido id={oid} code={code} tem "
                    f"invoices={invoices} shipment_items={shipments} — remova manualmente"
                )
                return 3

            if st not in ("DRAFT", "CANCELLED"):
                print(
                    f"ABORT: pedido id={oid} code={code} status={status} items={items} "
                    "— não é DRAFT/CANCELLED"
                )
                return 3

            # RUX-3E: permite DRAFT com linhas se sem Invoice/Shipment
            conn.execute(
                text("DELETE FROM document_links WHERE entity_type = 'order' AND entity_id = :eid"),
                {"eid": str(oid)},
            )
            conn.execute(text("DELETE FROM order_items WHERE order_id = :oid"), {"oid": oid})
            conn.execute(text("DELETE FROM orders WHERE id = :oid"), {"oid": oid})
            print(
                f"DELETED order id={oid} code={code} status={status} "
                f"items={items} source={source_system} external_ref={external_ref}"
            )

        counts: dict[str, int] = {}
        for table in INGESTION_TABLES:
            exists = conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar()
            if not exists:
                continue
            n = conn.execute(text(f"DELETE FROM {table}")).rowcount  # noqa: S608
            counts[table] = int(n or 0)

        # Documentos promovidos órfãos de ingestão (links já removidos com orders)
        # Não apaga documents genéricos — só limpa links restantes de ingestion_document
        conn.execute(
            text("DELETE FROM document_links WHERE entity_type = 'ingestion_document'")
        )

        heroes = conn.execute(
            text(
                """
                SELECT id, name, code FROM suppliers
                WHERE name ILIKE '%hero%' OR code ILIKE '%hero%' OR code LIKE '%02610500395%'
                ORDER BY id
                """
            )
        ).fetchall()
        deleted_suppliers = 0
        for sid, name, code in heroes:
            linked = conn.execute(
                text("SELECT COUNT(*) FROM orders WHERE supplier_id = :sid"),
                {"sid": sid},
            ).scalar()
            if linked:
                print(f"SKIP supplier id={sid} name={name!r} — referenciado por {linked} pedido(s)")
                continue
            conn.execute(text("DELETE FROM suppliers WHERE id = :sid"), {"sid": sid})
            deleted_suppliers += 1
            print(f"DELETED supplier id={sid} name={name!r} code={code!r}")

        print("OK epic_v2 reset for Ordine RUX-3E")
        for k, v in counts.items():
            if v:
                print(f"  {k}: deleted {v}")
        print(f"  suppliers_heroes: deleted {deleted_suppliers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
