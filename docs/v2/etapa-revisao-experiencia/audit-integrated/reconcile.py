"""Independent SQL arithmetic and environment identity. READ ONLY, no app calculation imports."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,subprocess
import httpx
from sqlalchemy import create_engine,text,inspect
repo=Path(__file__).resolve().parents[4];epic=repo.parent;lab=epic/'audit-lab/integrated-20261023';out=lab/'package/evidencias'
c=json.loads((lab/'chain.json').read_text());data={}
for name,port,root in [('presentation',5451,epic/'audit-runtime/receiving-stock-20261023'),('audit',5452,lab)]:
 engine=create_engine(f'postgresql://postgres@127.0.0.1:{port}/epic_v2_test')
 with engine.connect() as db:
  db.execute(text('SET TRANSACTION READ ONLY'))
  identity=db.execute(text("select current_database(),inet_server_port(),current_setting('data_directory'),system_identifier from pg_control_system()")).one()
  assert identity[1]==port and Path(identity[2]).resolve()==(root/'postgres').resolve()
  rows=lambda sql,**p:[dict(r) for r in db.execute(text(sql),p).mappings()]
  tables=['products','orders','invoices','payables','payments','payment_allocations','shipments','import_processes','nationalizations','goods_receipts','inventory_movements','costing_cases','costing_versions','sales_price_entries','documents']
  counts={t:db.execute(text(f'select count(*) from {t}')).scalar_one() for t in tables}
  ap=rows("select p.currency,sum(p.amount) original,sum(p.balance) persisted_balance,sum(p.amount-coalesce(a.allocated,0)) independent_balance from payables p left join(select payable_id,sum(amount) allocated from payment_allocations group by payable_id)a on a.payable_id=p.id where p.status<>'CANCELLED' group by p.currency order by p.currency")
  assert all(Decimal(r['persisted_balance'])==Decimal(r['independent_balance']) for r in ap)
  show=rows('select location_id,qty from stock_balances where product_id=3 order by location_id')
  a=rows('select id,amount,currency,balance,status from payables where id=2')
  assert sum(Decimal(r['qty']) for r in show)==42 and Decimal(a[0]['balance'])==2000
  show_facts={'ledger':rows('select m.id,m.quantity_delta,r.process_id,m.movement_type from inventory_movements m left join goods_receipt_lines l on l.id=m.receipt_line_id left join goods_receipts r on r.id=l.receipt_id where m.product_id=3 order by m.created_at,m.id'), 'published':rows("select v.id,v.case_id,v.version_number,v.kind,v.snapshot->'products' products from costing_versions v join costing_cases c on c.current_published_id=v.id where v.id in(select version_id from costing_lines where product_id=3) order by v.id"), 'prices':rows('select list_id,amount,unit,valid_from,valid_to,cancelled from sales_price_entries where product_id=3 order by id')}
  data[name]={'identity':{'database':identity[0],'port':identity[1],'cluster':str(identity[3]),'separate_storage':str(root/'storage')},'counts':counts,'payablesByCurrency':ap,'SHOW26':{'balances':show,'payableA':a},'AUDOrders':rows("select id,code,status from orders where code like 'AUD26%' order by id")}
  data[name]['SHOW26']['independentSourceFacts']=show_facts
  if name=='audit':
   data['chain']={'ids':c,'payables':rows('select id,amount,balance,currency,status from payables where id=:p or(source_type=\'CUSTOMS_FUNDING\' and source_id in(select id from customs_funding_requests where process_id=:proc))',p=c['payable'],proc=c['process']), 'payments':rows('select id,amount,currency,status from payments where id=:p',p=c['payment']),'allocations':rows('select id,payment_id,payable_id,amount from payment_allocations where payment_id=:p',p=c['payment']),'movements':rows('select id,product_id,location_id,quantity_delta,movement_type from inventory_movements where product_id=:p order by id',p=c['product']),'balance':rows('select location_id,qty from stock_balances where product_id=:p',p=c['product']),'release':rows('select ni.quantity,n.status from nationalization_items ni join nationalizations n on n.id=ni.nationalization_id where n.process_id=:p',p=c['process']),'costLines':rows('select version_id,invoice_item_id,shipment_item_id,qty,merchandise_brl,fx_status from costing_lines where version_id in(select id from costing_versions where case_id=:p)',p=c['costing']),'price':rows('select id,list_id,amount,unit,valid_from,valid_to,cancelled from sales_price_entries where product_id=:p order by id',p=c['product'])}
   assert sum(Decimal(r['quantity_delta']) for r in data['chain']['movements'])==20
   assert sum(Decimal(r['amount']) for r in data['chain']['allocations'])==500
 assert name!='presentation' or data[name]['AUDOrders']==[]
# Check exact served assets, not merely build label.
http={};hashes={}
for port in [8082,8094]:
 build=httpx.get(f'http://127.0.0.1:{port}/assets/build-info.json').raise_for_status().json();manifest=httpx.get(f'http://127.0.0.1:{port}/assets/demo-manifest.json').raise_for_status().content
 html=httpx.get(f'http://127.0.0.1:{port}/').raise_for_status().text
 import re
 assets=re.findall(r'(?:src|href)="(/assets/[^" ]+\.(?:js|css))"',html)
 http[str(port)]={'build':build,'manifest_sha256':hashlib.sha256(manifest).hexdigest(),'assets':{a:hashlib.sha256(httpx.get(f'http://127.0.0.1:{port}'+a).raise_for_status().content).hexdigest() for a in assets}}
assert http['8082']==http['8094'];data['http']=http
data['independentExpected']={'AUD26':{'paymentBeforeAllocation':2000,'paymentAfterAllocation':1500,'released':20,'received':[8,12],'available':20,'priceToday':1100,'saleToday':22000,'costIfInvoiceLinesAllocated':12300,'unitCostIfComplete':615,'costActuallyEligible':None,'marginActuallyEligible':None},'SHOW26':{'quantity':42,'cost':54900,'sale':138138,'marginPercent':str((Decimal(138138)-54900)/138138*100)}}
data['method']='SQL sums over persisted facts; no application finance/stock function used. Conditional cost 12300 is NOT asserted for a process with zero invoice-line allocations; expected response there is incomplete/blocked, never complete zero.'
(out/'reconciliation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf8')
print(json.dumps({k:data[k]['counts'] for k in ['presentation','audit']}));print('SHOW26 42, payable A 2000, assets identical; independent balances checked')
