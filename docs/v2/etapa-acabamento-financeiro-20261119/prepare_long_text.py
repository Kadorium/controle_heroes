"""Only new FIN19 fixtures in the previously verified, isolated 5461 clone.
Necessary to exercise references differing in the middle/end and large money.
No existing demonstration values are edited.
"""
from pathlib import Path
import json,httpx
from sqlalchemy import create_engine,text
out=Path(__file__).parent
root=out.parents[3]
engine=create_engine('postgresql://postgres@127.0.0.1:5461/epic_v2_test')
with engine.connect() as db:
 name,port,folder=db.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
 assert name=='epic_v2_test' and port==5461
 assert Path(folder).resolve()==(root/'audit-lab/details-20261118/postgres').resolve(),(root,folder)
client=httpx.Client(base_url='http://127.0.0.1:8104',timeout=30)
def api(method,path,body=None):
 r=client.request(method,'/api'+path,json=body);r.raise_for_status();return r.json()
api('POST','/auth/dev-login')
j=json.loads((out/'long-text-fixtures.json').read_text(encoding='utf8')) if (out/'long-text-fixtures.json').exists() else {}
def step(key,method,path,body=None):
 if key not in j:
  j[key]=api(method,path,body);(out/'long-text-fixtures.json').write_text(json.dumps(j,indent=2,ensure_ascii=False),encoding='utf8')
 return j[key]
supplier=step('supplier','POST','/suppliers',{'name':'FIN19 Fornecedor fictício de equipamentos esportivos e acessórios para demonstração de referências completas e leitura financeira internacional','country_code':'BR'})
product=step('product','POST','/products',{'sku':'FIN19-LEITURA','description':'FIN19 Ensaio visual isolado'})
for i,(middle,end,currency) in enumerate([('AAA','FINAL-A','EUR'),('AAA','FINAL-B','USD'),('BBB','FINAL-A','BRL')]):
 ref=f'FIN19-PREFIXO-COMPARTILHADO-{middle}-REFERENCIA-OPERACIONAL-{end}'
 order=step(f'o{i}','POST','/orders',{'code':ref,'supplier_id':supplier['id'],'currency':currency,'notes':'FIN19 massa exclusivamente visual, sem promoção'})
 order=step(f'oi{i}','POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'product_id':product['id'],'quantity':'1','unit_price':'123456789.90','unit':'UN'})
 order=step(f'oc{i}','POST',f"/orders/{order['id']}/confirm",{'expected_version':order['version']})
 inv=step(f'i{i}','POST',f"/orders/{order['id']}/invoices",{'invoice_number':ref,'invoice_type':'FINAL'})
 inv=step(f'ii{i}','PUT',f"/invoices/{inv['id']}/items",{'expected_version':inv['version'],'items':[{'order_item_id':order['items'][0]['id'],'quantity':'1','unit_price_gross':'123456789.90','unit':'UN','discount_type':'NONE'}]})
 inv=step(f'it{i}','PUT',f"/invoices/{inv['id']}/terms",{'expected_version':inv['version'],'mode':'PERCENT','terms':[{'due_date':'2030-02-01','percent':'50'},{'due_date':'2030-03-01','percent':'50'}]})
 step(f'issued{i}','POST',f"/invoices/{inv['id']}/issue",{'expected_version':inv['version'],'issue_without_document':True,'reason_code':'FIN19_VISUAL_TEST_ONLY'})
print(json.dumps({'supplier':supplier['id'],'invoices':[j[f'issued{i}']['id'] for i in range(3)],'database_port':port}))
