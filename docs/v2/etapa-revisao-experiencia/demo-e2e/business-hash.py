"""Read-only business fingerprint; excludes sessions/read audit and FX cache."""
import json,hashlib,sys
import runtime
from sqlalchemy import text
tables=['products','product_categories','product_types','orders','order_items','invoices','invoice_items','payables','payments','payment_allocations','shipments','shipment_items','import_processes','goods_receipts','goods_receipt_lines','inventory_movements','stock_balances','costing_cases','costing_versions','costing_lines','cost_allocations','costing_expenses','cost_components','documents','sales_price_lists','sales_price_entries']
with runtime.engine.connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    known=set(c.execute(text("select tablename from pg_tables where schemaname='public'")).scalars())
    rows={}
    for t in tables:
        if t not in known:continue
        records=sorted(c.execute(text(f'select row_to_json(t)::text from "{t}" t')).scalars())
        rows[t]={'count':len(records),'sha256':hashlib.sha256('\n'.join(records).encode()).hexdigest()}
    result={'tables':rows,'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}
if len(sys.argv)>1:(runtime.lab/sys.argv[1]).write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
