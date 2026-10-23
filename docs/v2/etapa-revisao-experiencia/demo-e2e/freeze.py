"""Read validation + local build metadata. Does not seed/reset or publish business records."""
import json,hashlib,subprocess,os
from pathlib import Path
from decimal import Decimal as D
from pypdf import PdfReader
import httpx
import runtime
from sqlalchemy import text

scenario=runtime.lab/'scenario';m=json.loads((scenario/'manifest.json').read_text(encoding='utf8'));a=m['stories'][0];b=m['stories'][1]
client=httpx.Client(base_url='http://127.0.0.1:8088',timeout=60);client.post('/api/auth/dev-login').raise_for_status()
def get(path):return client.get('/api'+path).raise_for_status().json()
stock=get(f"/reporting/stock-explorer?product_id={m['products'][0]['id']}")['rows'][0]
assert D(stock['quantity'])==42 and D(stock['cost_total'])==54900 and D(stock['sale_total'])==138138
assert D(get(f"/payables/{a['invoice']['payables'][0]['id']}")['balance'])==2000
assert D(get(f"/payables/{b['invoice']['payables'][0]['id']}")['balance'])==5100
checks=[]
def check(path,keys):
    data=get(path);checks.append({'path':'/api'+path,'fields':{k:data[k] for k in keys}})
check(f"/orders/{a['order']['id']}",['id','code','status','commercial_total'])
check(f"/invoices/{a['invoice']['id']}",['id','order_id','status','balance'])
check(f"/payments/{a['payment']['id']}",['id','amount','amount_allocated','amount_unallocated'])
check(f"/shipments/{a['shipment']['id']}",['id','status'])
check(f"/import-processes/{a['process']['id']}",['id','status'])
check(f"/inventory/sku/{m['products'][0]['id']}/position",['product_id','available_qty'])
check(f"/inventory/receipts/{a['receipts'][0]['id']}",['id','status'])
check(f"/inventory/receipts/{a['receipts'][1]['id']}",['id','status'])
check(f"/costing/cases/{a['case']['id']}",['id','current_published_id','included_total_brl'])
check(f"/costing/versions/{a['version']['id']}",['id','status','included_total_brl'])
economic=get(f"/reporting/stock-explorer?product_id={m['products'][0]['id']}")
checks.append({'path':f"/api/reporting/stock-explorer?product_id={m['products'][0]['id']}",'fields':{f'rows.0.{key}':economic['rows'][0][key] for key in ['product_id','quantity','cost_total','sale_total','margin','cost_quantity','price_quantity']}})
documents=[]
for doc in a['documents']:
    content=client.get(f"/api/documents/{doc['id']}/content").raise_for_status().content
    documents.append({'id':doc['id'],'url':f"/api/documents/{doc['id']}/content",'sha256':hashlib.sha256(content).hexdigest()})
pdfs=[]
for path in scenario.glob('*.pdf'):
    reader=PdfReader(path);assert len(reader.pages)>0 and 'DEMONSTRA' in reader.pages[0].extract_text();pdfs.append({'name':path.name,'pages':len(reader.pages),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
manifest={'schema_version':1,'logical_database':'epic_v2_test','scenario_id':'DEMO-HEROES-EXEC-20261023','label':'DEMONSTRAÇÃO Heroes · valores fictícios','base_date':m['base_date'],
 'ids':{'order':a['order']['id'],'invoice':a['invoice']['id'],'payment':a['payment']['id'],'shipment':a['shipment']['id'],'process':a['process']['id'],'product':m['products'][0]['id'],'case':a['case']['id'],'cost_version':a['version']['id'],'commercial_document':a['documents'][0]['id']},
 'expected':{'order_eur':'3000','paid_allocated_eur':'1000','open_eur':'2000','shipped_units':'20','nationalized_received_units':'20','nationalization_residual_units':'0','cost_brl':'24000','unit_cost_brl':'1200','stock_units':'42','stock_cost_brl':'54900','stock_sale_brl':'138138'},'checks':checks,'documents':documents}
assets=runtime.repo/'v2/frontend/dist/assets';assets.mkdir(exist_ok=True)
(assets/'demo-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime.repo,text=True).strip()
dirty=bool(subprocess.check_output(['git','status','--porcelain','--','v2/app','v2/frontend/src','v2/alembic'],cwd=runtime.repo,text=True).strip())
build={'build_id':os.environ.get('VITE_BUILD_ID','stock-executive-20261023.1'),'source_commit':revision,'uncommitted_candidate':dirty,'manifest_sha256':hashlib.sha256((assets/'demo-manifest.json').read_bytes()).hexdigest(),'assets':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.iterdir() if p.suffix in ('.js','.css','.mjs')}}
(assets/'build-info.json').write_text(json.dumps(build,indent=2),encoding='utf8')
with runtime.engine.connect() as conn:
    conn.execute(text('SET TRANSACTION READ ONLY'))
    tables=['products','orders','invoices','payables','payments','payment_allocations','shipments','import_processes','inventory_movements','costing_cases','costing_versions','documents','sales_price_entries']
    known=set(conn.execute(text("select tablename from pg_tables where schemaname='public'")).scalars())
    counts={t:conn.execute(text(f'select count(*) from {t}')).scalar() for t in tables if t in known}
(scenario/'validated.json').write_text(json.dumps({'stock_oracle':stock,'pdfs':pdfs,'counts':counts,'build':build},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'verified':'SHOW quantity/cost/sale + AP balances','pdfs':len(pdfs),'counts':counts,'build':build}))
