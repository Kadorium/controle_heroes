"""Minimal synthetic prerequisites, only in the verified dedicated test cluster."""
import json, os, sys
from pathlib import Path
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
repo=Path(__file__).resolve().parents[3]
lab=repo.parent/'audit-lab/navigation-20261118'
release=repo.parent/'audit-runtime/executive-20261117'
engine=create_engine('postgresql://postgres@127.0.0.1:5460/epic_v2_test')
with engine.connect() as conn:
 name,port,folder=conn.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
 assert name=='epic_v2_test' and port==5460 and Path(folder).resolve()==(lab/'postgres').resolve()
sys.path.insert(0,str(release/'v2'))
from app.identity.models import Role,User
from app.identity import public as identity
from app.identity.seed import ensure_e2e_operator_users
from app.identity.security import hash_password
roles={
 'nav_catalog':['catalog:read','catalog:write'],
 'nav_cost':['costing:read'],
 'nav_stock':['inventory:read'],
 'nav_logistics':['logistics:read','logistics:write'],
 'nav_fx':['treasury:fx_read'],
 'nav_payments':['treasury:read','treasury:write'],
}
with Session(engine) as db:
 ensure_e2e_operator_users(db)
 for name,permissions in roles.items():
  role=db.query(Role).filter_by(name=name).first()
  if not role:
   role=Role(name=name,description='NAV18 teste isolado',permissions_json=json.dumps(permissions));db.add(role);db.flush()
  if not db.query(User).filter_by(email=name+'@epic.com.br').first():
   db.add(User(email=name+'@epic.com.br',name='NAV18 '+name,password_hash=hash_password('ensaio123'),role_id=role.id,is_active=True))
 db.commit()
 role_evidence={r.name:json.loads(r.permissions_json) for r in db.query(Role).all()}
out=Path(__file__).parent/'fixtures.json'
j=json.loads(out.read_text(encoding='utf8')) if out.exists() else {}
client=httpx.Client(base_url='http://127.0.0.1:8102',timeout=60)
def api(method,path,body=None):
 r=client.request(method,'/api'+path,json=body);r.raise_for_status();return r.json()
assert api('GET','/health')['logical_database']=='epic_v2_test'
api('POST','/auth/dev-login')
def step(key,method,path,body=None):
 if key not in j:
  j[key]=api(method,path,body);out.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
 return j[key]
supplier=step('supplier','POST','/suppliers',{'name':'NAV18 Fornecedor fictício','country_code':'BR'})
product=step('product','POST','/products',{'sku':'NAV18-RECEBIMENTO','description':'NAV18 Produto fictício para recebimento parcial'})
product=step('unit','PATCH',f"/products/{product['id']}",{'unit':'UN'})
step('no-stock','POST','/products',{'sku':'NAV18-SEM-ESTOQUE','description':'NAV18 Produto fictício sem estoque'})
order=step('order','POST','/orders',{'code':'NAV18-PARCIAL','supplier_id':supplier['id'],'currency':'BRL','notes':'NAV18 ensaio isolado de navegação'})
order=step('item','POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'product_id':product['id'],'quantity':'10','unit_price':'1','unit':'UN'})
order=step('confirmed','POST',f"/orders/{order['id']}/confirm",{'expected_version':order['version']})
invoice=step('invoice','POST',f"/orders/{order['id']}/invoices",{'invoice_number':'NAV18-PARCIAL','invoice_type':'FINAL'})
invoice=step('invoice-items','PUT',f"/invoices/{invoice['id']}/items",{'expected_version':invoice['version'],'items':[{'order_item_id':order['items'][0]['id'],'quantity':'10','unit_price_gross':'1','unit':'UN','discount_type':'NONE'}]})
invoice=step('terms','PUT',f"/invoices/{invoice['id']}/terms",{'expected_version':invoice['version'],'mode':'PERCENT','terms':[{'due_date':'2030-01-01','percent':'100'}]})
invoice=step('issued','POST',f"/invoices/{invoice['id']}/issue",{'expected_version':invoice['version'],'issue_without_document':True,'reason_code':'NAV18_SYNTHETIC_TEST'})
process=step('process','POST','/import-processes',{'external_reference':'NAV18-PARCIAL','notes':'NAV18 preparação via API; entrada física exclusivamente pela UI'})
process=step('link','POST',f"/import-processes/{process['id']}/invoices",{'expected_version':process['version'],'invoice_id':invoice['id']})
item=invoice['items'][0]
process=step('allocate','POST',f"/import-processes/{process['id']}/invoice-items/allocate",{'expected_version':process['version'],'invoice_item_id':item['id'],'allocated_qty':'10'})
process=step('submitted','POST',f"/import-processes/{process['id']}/submit",{'expected_version':process['version']})
nat=step('nat','POST',f"/import-processes/{process['id']}/nationalizations",{'reference':'NAV18-LIBERACAO'})
nat=step('nat-items','POST',f"/import-processes/{process['id']}/nationalizations/{nat['id']}/items",{'expected_version':nat['version'],'items':[{'product_id':product['id'],'invoice_item_id':item['id'],'quantity':'10'}]})
step('released','POST',f"/import-processes/{process['id']}/nationalizations/{nat['id']}/confirm",{'expected_version':nat['version']})
(Path(__file__).parent/'roles.json').write_text(json.dumps(role_evidence,indent=2),encoding='utf8')
print(json.dumps({'test_database':'epic_v2_test','test_port':port,'product':product['id'],'process':process['id'],'receiving_item':nat['items'][0]['id'],'receipt_writes':0}))
