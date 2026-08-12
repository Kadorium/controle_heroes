"""FIN-3B cleanup — sample order 33 / invoice 24 / IR doc 30.

Never touches order 31 (589). Engine: epic_v2 :5433.
"""
from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")

ORDER_ID = 33
INVOICE_ID = 24
DOC_ID = 30
OCC_ID = 33
BATCH_ID = 29


def ids(c, sql, **kw):
    return [r[0] for r in c.execute(text(sql), kw).fetchall()]


with e.begin() as c:
    o31 = c.execute(text("select id, code, status from orders where id=31")).fetchone()
    assert o31 is not None and o31[1] == "589", o31
    o33 = c.execute(text("select id, code, status from orders where id=:oid"), {"oid": ORDER_ID}).fetchone()
    print("before", {"order31": dict(o31._mapping), "order33": dict(o33._mapping) if o33 else None})

    inv_ids = ids(c, "select id from invoices where order_id = :oid", oid=ORDER_ID)
    assert INVOICE_ID in inv_ids or not inv_ids, inv_ids
    pay_ids = ids(
        c,
        "select id from payables where invoice_id = any(:ids)",
        ids=inv_ids or [0],
    )
    pmt_ids = ids(c, "select id from payments where order_id = :oid", oid=ORDER_ID)
    print({"invoices": inv_ids, "payables": pay_ids, "payments": pmt_ids})

    doc_link_docs = ids(
        c,
        "select distinct document_id from document_links where "
        "(entity_type = 'invoice' and entity_id = any(:iids)) "
        "or (entity_type = 'order' and entity_id = :oid)",
        iids=[str(i) for i in (inv_ids or [0])],
        oid=str(ORDER_ID),
    )
    print({"linked_documents": doc_link_docs})

    if pay_ids:
        c.execute(text("delete from fx_plan_rates where payable_id = any(:ids)"), {"ids": pay_ids})
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

    for did in doc_link_docs:
        left = c.execute(
            text("select count(1) from document_links where document_id = :d"),
            {"d": did},
        ).scalar()
        if left == 0:
            c.execute(text("delete from documents where id = :d"), {"d": did})
            print("deleted document", did)

    doc_ids = [DOC_ID]
    occ_ids = [OCC_ID]
    ing_batch_ids = [BATCH_ID]

    c.execute(
        text("delete from ingestion_review_changes where document_id = any(:ids)"),
        {"ids": doc_ids},
    )
    c.execute(text("delete from ingestion_issues where document_id = any(:ids)"), {"ids": doc_ids})
    c.execute(text("delete from ingestion_fields where document_id = any(:ids)"), {"ids": doc_ids})
    c.execute(text("delete from ingestion_rows where document_id = any(:ids)"), {"ids": doc_ids})
    c.execute(text("delete from ingestion_sections where document_id = any(:ids)"), {"ids": doc_ids})
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
        c.execute(text("delete from ingestion_commit_attempts where id = any(:ids)"), {"ids": att})
    c.execute(text("delete from ingestion_documents where id = any(:ids)"), {"ids": doc_ids})
    c.execute(text("delete from ingestion_occurrences where id = any(:ids)"), {"ids": occ_ids})
    leftover = c.execute(
        text(
            "select count(1) from ingestion_occurrences where batch_id = any(:ids)"
        ),
        {"ids": ing_batch_ids},
    ).scalar()
    print("ing_batch_leftover_occs", leftover)
    if leftover == 0:
        c.execute(text("delete from ingestion_batches where id = any(:ids)"), {"ids": ing_batch_ids})

    left31_p = c.execute(text("select count(1) from payments where order_id = 31")).scalar()
    left31_i = c.execute(text("select count(1) from invoices where order_id = 31")).scalar()
    o31b = c.execute(text("select id, code, status from orders where id=31")).fetchone()
    o33b = c.execute(text("select id from orders where id=:oid"), {"oid": ORDER_ID}).fetchone()
    print(
        "after",
        {
            "order31": dict(o31b._mapping),
            "order33": o33b,
            "payments31": left31_p,
            "invoices31": left31_i,
        },
    )
    assert o33b is None
    assert o31b[1] == "589" and o31b[2] == "CONFIRMED"
    assert left31_p == 0 and left31_i == 0
