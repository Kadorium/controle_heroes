"""Journaled API prerequisites only; no receiving. New QA SKUs, never Heroes."""
import json
import httpx
import runtime
out=runtime.lab/'fixtures.json'
j=json.loads(out.read_text(encoding='utf8')) if out.exists() else {}
client=httpx.Client(base_url='http://127.0.0.1:8092',timeout=60)
def api(method,path,body=None):
    r=client.request(method,'/api'+path,json=body);r.raise_for_status();return r.json()
assert api('GET','/health')['alembic_head']=='034'
api('POST','/auth/dev-login')
def step(key,method,path,body=None):
    if key not in j:
        j[key]=api(method,path,body);out.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
    return j[key]
supplier=step('supplier','POST','/suppliers',{'name':'QA recebimento · fornecedor fictício','country_code':'BR'})
products=[]
for name,qty in [('STOCK',10),('RACE',8),('ADMIN',4),('BLOCKED',6),('READY',5)]:
    p=step('product-'+name,'POST','/products',{'sku':'QA-RCV-'+name,'description':'QA recebimento · '+name})
    p=step('unit-'+name,'PATCH',f"/products/{p['id']}",{'unit':'UN'})
    products.append((name,p,qty))
order=step('order','POST','/orders',{'code':'QA-RECEIVING-20261023','supplier_id':supplier['id'],'currency':'BRL','notes':'QA isolado do recorte Heroes; teste de recebimento'})
for name,p,qty in products:
    order=step('item-'+name,'POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'product_id':p['id'],'quantity':str(qty),'unit_price':'1','unit':'UN'})
order=step('confirmed','POST',f"/orders/{order['id']}/confirm",{'expected_version':order['version']})
invoice=step('invoice','POST',f"/orders/{order['id']}/invoices",{'invoice_number':'QA-RECEIVING-20261023','invoice_type':'FINAL'})
invoice=step('invoice-items','PUT',f"/invoices/{invoice['id']}/items",{'expected_version':invoice['version'],'items':[{'order_item_id':it['id'],'quantity':it['quantity'],'unit_price_gross':'1','unit':'UN','discount_type':'NONE'} for it in order['items']]})
invoice=step('terms','PUT',f"/invoices/{invoice['id']}/terms",{'expected_version':invoice['version'],'mode':'PERCENT','terms':[{'due_date':'2030-01-01','percent':'100'}]})
invoice=step('issued','POST',f"/invoices/{invoice['id']}/issue",{'expected_version':invoice['version'],'issue_without_document':True,'reason_code':'QA_RECEIVING_SYNTHETIC'})
process=step('process','POST','/import-processes',{'external_reference':'QA-RECEIVING-20261023','notes':'QA isolado; preparação por API, não operação do estoquista'})
process=step('link','POST',f"/import-processes/{process['id']}/invoices",{'expected_version':process['version'],'invoice_id':invoice['id']})
for item in invoice['items']:
    process=step('allocate-'+str(item['id']),'POST',f"/import-processes/{process['id']}/invoice-items/allocate",{'expected_version':process['version'],'invoice_item_id':item['id'],'allocated_qty':item['quantity']})
process=step('submitted','POST',f"/import-processes/{process['id']}/submit",{'expected_version':process['version']})
for name,p,qty in products:
    item=next(i for i in invoice['items'] if i['product_id']==p['id'])
    nat=step('nat-'+name,'POST',f"/import-processes/{process['id']}/nationalizations",{'reference':'QA-RCV-'+name})
    nat=step('nat-items-'+name,'POST',f"/import-processes/{process['id']}/nationalizations/{nat['id']}/items",{'expected_version':nat['version'],'items':[{'product_id':p['id'],'invoice_item_id':item['id'],'quantity':str(qty)}]})
    if name!='BLOCKED':step('released-'+name,'POST',f"/import-processes/{process['id']}/nationalizations/{nat['id']}/confirm",{'expected_version':nat['version']})
print(json.dumps({'process_id':process['id'],'qa_payable_brl':'33','stock_writes':0,'products':[{'name':n,'id':p['id'],'quantity':q} for n,p,q in products]}))
