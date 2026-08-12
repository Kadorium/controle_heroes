"""FIN-23 cleanup — sample order 32 / invoice 244 / payables 18-19 / payments.

Never touches order 31 (589). Engine: epic_v2 :5433.
"""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")

ORDER_ID = 32
INVOICE_ID = 23


def ids(c, sql, **kw):
    return [r[0] for r in c.execute(text(sql), kw).fetchall()]


with e.begin() as c:
    o31 = c.execute(text("select id, code, status from orders where id=31")).fetchone()
    assert o31 is not None and o31[1] == "589", o31
    o32 = c.execute(text("select id, code, status from orders where id=32")).fetchone()
    print("before", {"order31": dict(o31._mapping), "order32": dict(o32._mapping) if o32 else None})

    inv_ids = ids(c, "select id from invoices where order_id = :oid", oid=ORDER_ID)
    assert INVOICE_ID in inv_ids or not inv_ids, inv_ids
    pay_ids = ids(
        c,
        "select id from payables where invoice_id = any(:ids)",
        ids=inv_ids or [0],
    )
    pmt_ids = ids(c, "select id from payments where order_id = :oid", oid=ORDER_ID)
    alloc_ids = ids(
        c,
        "select id from payment_allocations where payment_id = any(:ids) or payable_id = any(:pids)",
        ids=pmt_ids or [0],
        pids=pay_ids or [0],
    )
    batch_ids = ids(
        c,
        "select distinct batch_id from payment_allocations where id = any(:ids)",
        ids=alloc_ids or [0],
    )
    fx_ids = ids(
        c,
        "select id from fx_executions where payment_id = any(:ids)",
        ids=pmt_ids or [0],
    )
    print(
        {
            "invoices": inv_ids,
            "payables": pay_ids,
            "payments": pmt_ids,
            "allocs": alloc_ids,
            "alloc_batches": batch_ids,
            "fx": fx_ids,
        }
    )

    # ingestion IR for Fattura_244 sample
    doc_ids = ids(
        c,
        "select id from ingestion_documents where id = 29 or occurrence_id in "
        "(select id from ingestion_occurrences where original_filename = 'Fattura_244.pdf')",
    )
    occ_ids = ids(
        c,
        "select occurrence_id from ingestion_documents where id = any(:ids)",
        ids=doc_ids or [0],
    )
    ing_batch_ids = ids(
        c,
        "select distinct batch_id from ingestion_occurrences where id = any(:oids) "
        "or batch_id in (27, 28)",
        oids=occ_ids or [0],
    )
    print({"ing_docs": doc_ids, "occs": occ_ids, "ing_batches": ing_batch_ids})

    if alloc_ids:
        c.execute(
            text("delete from fx_allocation_valuations where payment_allocation_id = any(:ids)"),
            {"ids": alloc_ids},
        )
        c.execute(
            text("delete from fx_execution_allocations where payment_allocation_id = any(:ids)"),
            {"ids": alloc_ids},
        )
    if fx_ids:
        c.execute(
            text("delete from fx_execution_allocations where fx_execution_id = any(:ids)"),
            {"ids": fx_ids},
        )
        c.execute(
            text(
                "delete from document_links where entity_type = 'fx_execution' "
                "and entity_id = any(:ids)"
            ),
            {"ids": [str(i) for i in fx_ids]},
        )
        c.execute(text("delete from fx_executions where id = any(:ids)"), {"ids": fx_ids})
    if pay_ids:
        c.execute(text("delete from fx_plan_rates where payable_id = any(:ids)"), {"ids": pay_ids})
    if alloc_ids:
        c.execute(text("delete from payment_allocations where id = any(:ids)"), {"ids": alloc_ids})
    if batch_ids:
        c.execute(
            text("delete from payment_allocation_batches where id = any(:ids)"),
            {"ids": [b for b in batch_ids if b is not None]},
        )
    if pmt_ids:
        c.execute(
            text(
                "delete from document_links where entity_type = 'payment' "
                "and entity_id = any(:ids)"
            ),
            {"ids": [str(i) for i in pmt_ids]},
        )
        c.execute(text("delete from payments where id = any(:ids)"), {"ids": pmt_ids})
    if pay_ids:
        c.execute(text("delete from payables where id = any(:ids)"), {"ids": pay_ids})
    if inv_ids:
        c.execute(text("delete from payment_terms where invoice_id = any(:ids)"), {"ids": inv_ids})
        c.execute(text("delete from invoice_items where invoice_id = any(:ids)"), {"ids": inv_ids})
        c.execute(
            text(
                "delete from document_links where entity_type = 'invoice' "
                "and entity_id = any(:ids)"
            ),
            {"ids": [str(i) for i in inv_ids]},
        )
        c.execute(text("delete from invoices where id = any(:ids)"), {"ids": inv_ids})

    c.execute(
        text("delete from document_links where entity_type = 'order' and entity_id = :eid"),
        {"eid": str(ORDER_ID)},
    )
    c.execute(text("delete from order_items where order_id = :oid"), {"oid": ORDER_ID})
    c.execute(text("delete from orders where id = :oid"), {"oid": ORDER_ID})

    if doc_ids:
        c.execute(
            text("delete from ingestion_review_changes where document_id = any(:ids)"),
            {"ids": doc_ids},
        )
        c.execute(
            text("delete from ingestion_issues where document_id = any(:ids)"),
            {"ids": doc_ids},
        )
        c.execute(
            text("delete from ingestion_fields where document_id = any(:ids)"),
            {"ids": doc_ids},
        )
        c.execute(
            text("delete from ingestion_rows where document_id = any(:ids)"),
            {"ids": doc_ids},
        )
        c.execute(
            text("delete from ingestion_sections where document_id = any(:ids)"),
            {"ids": doc_ids},
        )
        att = ids(
            c,
            "select id from ingestion_commit_attempts where document_id = any(:ids)",
            ids=doc_ids,
        )
        if att:
            c.execute(
                text("delete from ingestion_commit_operations where attempt_id = any(:ids)"),
                {"ids": att},
            )
            c.execute(
                text("delete from ingestion_commit_attempts where id = any(:ids)"),
                {"ids": att},
            )
        c.execute(text("delete from ingestion_documents where id = any(:ids)"), {"ids": doc_ids})
    if occ_ids:
        c.execute(
            text("delete from ingestion_occurrences where id = any(:ids)"),
            {"ids": occ_ids},
        )
    if ing_batch_ids:
        leftover = c.execute(
            text(
                "select batch_id, count(1) from ingestion_occurrences "
                "where batch_id = any(:ids) group by batch_id"
            ),
            {"ids": ing_batch_ids},
        ).fetchall()
        print("ing_batch_leftover_occs", leftover)
        empty = [
            b
            for b in ing_batch_ids
            if b not in {r[0] for r in leftover}
        ]
        if empty:
            c.execute(
                text("delete from ingestion_batches where id = any(:ids)"),
                {"ids": empty},
            )

    left31_p = c.execute(text("select count(1) from payments where order_id = 31")).scalar()
    left31_i = c.execute(text("select count(1) from invoices where order_id = 31")).scalar()
    o31b = c.execute(text("select id, code, status from orders where id=31")).fetchone()
    o32b = c.execute(text("select id from orders where id=32")).fetchone()
    print(
        "after",
        {
            "order31": dict(o31b._mapping),
            "order32": o32b,
            "payments31": left31_p,
            "invoices31": left31_i,
        },
    )
    assert o32b is None
    assert o31b[1] == "589" and o31b[2] == "CONFIRMED"
    assert left31_p == 0 and left31_i == 0
