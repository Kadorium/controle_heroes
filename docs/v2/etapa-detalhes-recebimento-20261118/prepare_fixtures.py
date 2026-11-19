"""Minimal synthetic prerequisites, only in the verified dedicated test cluster."""
import json, os, sys
from pathlib import Path
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
repo=Path(__file__).resolve().parents[3]
lab=repo.parent/'audit-lab/details-20261118'
release=repo.parent/'audit-runtime/executive-20261117'
engine=create_engine('postgresql://postgres@127.0.0.1:5461/epic_v2_test')
with engine.connect() as conn:
 name,port,folder=conn.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
 assert name=='epic_v2_test' and port==5461 and Path(folder).resolve()==(lab/'postgres').resolve()
sys.path.insert(0,str(release/'v2'))
from app.identity.models import Role,User
from app.identity import public as identity
from app.identity.seed import ensure_e2e_operator_users
from app.identity.security import hash_password
roles={
 'det_stock_read':['inventory:read'],
 'det_customs_read':['customs:read','inventory:read'],
 'det_order_read':['orders:read','billing:read','treasury:read','reporting:read'],
 'det_order_only':['orders:read'],
}

with Session(engine) as db:
 ensure_e2e_operator_users(db)
 for name,permissions in roles.items():
  role=db.query(Role).filter_by(name=name).first()
  if not role:
   role=Role(name=name,description='DET18 teste isolado',permissions_json=json.dumps(permissions));db.add(role);db.flush()
  if not db.query(User).filter_by(email=name+'@epic.com.br').first():
   db.add(User(email=name+'@epic.com.br',name='DET18 '+name,password_hash=hash_password('ensaio123'),role_id=role.id,is_active=True))
 db.commit()
 role_evidence={r.name:json.loads(r.permissions_json) for r in db.query(Role).all()}
out=Path(__file__).parent/'fixtures.json'
j=json.loads(out.read_text(encoding='utf8')) if out.exists() else {}
client=httpx.Client(base_url='http://127.0.0.1:8103',timeout=60)
def api(method,path,body=None):
 r=client.request(method,'/api'+path,json=body);r.raise_for_status();return r.json()
assert api('GET','/health')['logical_database']=='epic_v2_test'
api('POST','/auth/dev-login')
def step(key,method,path,body=None):
 if key not in j:
  j[key]=api(method,path,body);out.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
 return j[key]

supplier=step('supplier','POST','/suppliers',{'name':'DET18 Fornecedor fictício','country_code':'BR'})
product=step('product','POST','/products',{'sku':'DET18-RECEBIMENTO','description':'DET18 Produto de ensaio isolado'})
product=step('unit','PATCH',f"/products/{product['id']}",{'unit':'UN'})
for suffix,qty in [('1','16'),('10','3')]:
 prefix='case'+suffix+'-'
 order=step(prefix+'order','POST','/orders',{'code':'DET18-'+suffix,'supplier_id':supplier['id'],'currency':'BRL','notes':'DET18 ensaio isolado de detalhes'})
 order=step(prefix+'item','POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'product_id':product['id'],'quantity':qty,'unit_price':'1','unit':'UN'})
 order=step(prefix+'confirmed','POST',f"/orders/{order['id']}/confirm",{'expected_version':order['version']})
 invoice=step(prefix+'invoice','POST',f"/orders/{order['id']}/invoices",{'invoice_number':'DET18-'+suffix,'invoice_type':'FINAL'})
 invoice=step(prefix+'invoice-items','PUT',f"/invoices/{invoice['id']}/items",{'expected_version':invoice['version'],'items':[{'order_item_id':order['items'][0]['id'],'quantity':qty,'unit_price_gross':'1','unit':'UN','discount_type':'NONE'}]})
 invoice=step(prefix+'terms','PUT',f"/invoices/{invoice['id']}/terms",{'expected_version':invoice['version'],'mode':'PERCENT','terms':[{'due_date':'2030-01-01','percent':'100'}]})
 invoice=step(prefix+'issued','POST',f"/invoices/{invoice['id']}/issue",{'expected_version':invoice['version'],'issue_without_document':True,'reason_code':'DET18_SYNTHETIC_TEST'})
 process=step(prefix+'process','POST','/import-processes',{'external_reference':'DET18-REF-'+suffix,'notes':'DET18 preparação API; entradas exclusivamente pela UI'})
 process=step(prefix+'link','POST',f"/import-processes/{process['id']}/invoices",{'expected_version':process['version'],'invoice_id':invoice['id']})
 item=invoice['items'][0]
 process=step(prefix+'allocate','POST',f"/import-processes/{process['id']}/invoice-items/allocate",{'expected_version':process['version'],'invoice_item_id':item['id'],'allocated_qty':qty})
 process=step(prefix+'submitted','POST',f"/import-processes/{process['id']}/submit",{'expected_version':process['version']})
 if suffix=='10':
  nat=step(prefix+'nat','POST',f"/import-processes/{process['id']}/nationalizations",{'reference':'DET18-LIB-10'})
  nat=step(prefix+'nat-items','POST',f"/import-processes/{process['id']}/nationalizations/{nat['id']}/items",{'expected_version':nat['version'],'items':[{'product_id':product['id'],'invoice_item_id':item['id'],'quantity':qty}]})
  step(prefix+'released','POST',f"/import-processes/{process['id']}/nationalizations/{nat['id']}/confirm",{'expected_version':nat['version']})
# Mixed order proves one unbound line must not block the other eligible line.
order=step('mixed-order','POST','/orders',{'code':'DET18-MISTO','supplier_id':supplier['id'],'currency':'BRL'})
order=step('mixed-product','POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'product_id':product['id'],'quantity':'2','unit_price':'3','unit':'UN'})
order=step('mixed-commitment','POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'line_kind':'COMMITMENT','external_code':'DET18-SEM-VINCULO','description':'DET18 Compromisso sem produto','quantity':'5','unit_price':'2','unit':'UN'})
step('mixed-confirmed','POST',f"/orders/{order['id']}/confirm",{'expected_version':order['version']})
step('draft-order','POST','/orders',{'code':'DET18-RASCUNHO','supplier_id':supplier['id'],'currency':'BRL'})
(Path(__file__).parent/'roles.json').write_text(json.dumps(role_evidence,indent=2),encoding='utf8')
print(json.dumps({'test_database':'epic_v2_test','test_port':port,'product':product['id'],'fixtures':str(out),'receipt_writes':0}))
