"""Read-only snapshot of the Elo 7 walk in epic_v2_test. Does not mutate."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text

OUT = Path(__file__).with_name("e7-walk-db.json")


def q(engine, sql: str):
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql))]


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url or "epic_v2_test" not in url:
        raise SystemExit("DATABASE_URL must point at epic_v2_test")
    engine = create_engine(url)
    out = {
        "db": "epic_v2_test",
        "orders": q(engine, "select id, code, status from orders order by id"),
        "invoices": q(engine, "select id, invoice_number, status from invoices order by id"),
        "payables": q(
            engine,
            "select id, source_type, status, currency, amount, balance from payables order by id",
        ),
        "shipments": q(engine, "select id, code, status from shipments order by id"),
        "processes": q(
            engine,
            "select id, code, status, external_reference, version from import_processes order by id",
        ),
        "funding": q(
            engine,
            "select id, process_id, status, declared_total "
            "from customs_funding_requests order by id",
        ),
        "tax_codes": q(engine, "select code, amount from customs_tax_lines order by id"),
        "nats": q(engine, "select id, process_id, status from nationalizations order by id"),
        "nat_items": q(
            engine,
            "select nationalization_id, product_id, quantity from nationalization_items order by id",
        ),
        "doganale_versions": q(
            engine,
            "select id, doganale_id, version_number, status, is_current "
            "from customs_doganale_versions order by id",
        ),
        "doganale_line_count": q(engine, "select count(*) as n from customs_doganale_lines"),
        "receipts": q(engine, "select id, process_id, status from goods_receipts order by id"),
        "audit_process": q(
            engine,
            "select action, entity_id from audit_log "
            "where entity_type = 'import_process' order by id",
        ),
        "commit_attempts": q(
            engine,
            "select id, document_id, operation_key, status from ingestion_commit_attempts order by id",
        ),
        "inv_alloc": q(
            engine,
            "select process_id, invoice_item_id, allocated_qty "
            "from import_process_invoice_items order by id",
        ),
        "shp_alloc": q(
            engine,
            "select process_id, shipment_item_id, allocated_qty "
            "from import_process_shipment_items order by id",
        ),
    }
    OUT.write_text(json.dumps(out, default=str, indent=2, ensure_ascii=False), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
