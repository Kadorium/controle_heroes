"""Guarded candidate fixture. Journaled domain/API steps; no reset and no startup hook.

Source identities use public Heroes names. All transactions, prices and identifiers
are synthetic. PDFs are generated from the exact persisted transaction inputs.
"""
import hashlib,json,sys
from datetime import datetime,timedelta
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
import runtime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.catalog import public as catalog
from app.catalog.models import Product

ROOT=runtime.repo;LAB=runtime.lab;OUT=LAB/'scenario';OUT.mkdir(exist_ok=True)
JOURNAL=OUT/'journal.json';MANIFEST=OUT/'manifest.json';CODE='HEROES-EXEC-20261023-v1'
journal=json.loads(JOURNAL.read_text(encoding='utf-8')) if JOURNAL.exists() else {'base_date':datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat(),'steps':{}}
base=datetime.fromisoformat(journal['base_date']).date()
date=lambda n:(base+timedelta(days=n)).isoformat()
def persist():JOURNAL.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8')
client=httpx.Client(base_url='http://127.0.0.1:8088',timeout=90)
def api(method,path,body=None,**kw):
    r=client.request(method,'/api'+path,json=body,**kw)
    if r.is_error:raise RuntimeError(f'{method} {path}: {r.status_code} {r.text[:1500]}')
    return r.json() if r.content else None
health=api('GET','/health');assert health['logical_database']=='epic_v2_test' and health['alembic_head']=='032'
actor=api('POST','/auth/dev-login');assert actor['role']=='admin'
with Session(runtime.engine) as db:
    assert db.execute(text('select inet_server_port()')).scalar()==5445
    assert Path(db.execute(text('show data_directory')).scalar()).resolve()==(LAB/'postgres').resolve()
    catalog.ensure_taxonomy(db)
    pricelist=catalog.ensure_price_list(db,code=CODE,name='Varejo demonstração',channel='Venda direta',actor_id=str(actor['id']))
    list_id=pricelist.id;db.commit()
def step(key,method,path,body=None,**kw):
    if key in journal['steps']:return journal['steps'][key]
    result=api(method,path,body,**kw);journal['steps'][key]=result;persist();return result
def pdf(name,title,rows,notes):
    path=OUT/(name+'.pdf')
    if not path.exists():
        styles=getSampleStyleSheet();story=[Paragraph('EPIC • DEMONSTRAÇÃO',styles['Title']),Paragraph(title,styles['Heading2']),Paragraph('Documento sintético · sem validade fiscal · '+date(0),styles['Normal']),Spacer(1,18)]
        table=Table([[Paragraph(str(c),styles['Normal']) for c in row] for row in rows],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf0f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,0),.6,colors.grey)]))
        story.extend([table,Spacer(1,20),Paragraph(notes,styles['Normal'])]);SimpleDocTemplate(str(path),pagesize=(595,842),leftMargin=38,rightMargin=38).build(story)
    return path
def upload(key,path,entity,eid,role='attachment'):
    if key in journal['steps']:return journal['steps'][key]
    with path.open('rb') as f:return step(key,'POST','/documents',files={'file':(path.name,f,'application/pdf')},data={'entity_type':entity,'entity_id':str(eid),'role':role})
taxonomy=api('GET','/catalog/taxonomy');cats={x['slug']:x['id'] for x in taxonomy['categories']};types={x['slug']:x['id'] for x in taxonomy['product_types']}
products=[]
def product(key,name,kind,price,*,model=None,sport='Beach Tennis',unit='UN',size=None,color=None,pack=None,consume=None):
    sku='DEMO-HR-'+key
    if 'prod-'+key not in journal['steps']:
        with Session(runtime.engine) as db:existing=db.query(Product).filter((Product.sku==sku)|(Product.commercial_name==name)).first();eid=existing.id if existing else None
        row=api('GET',f'/products/{eid}') if eid else api('POST','/products',{'sku':sku,'description':name})
        journal['steps']['prod-'+key]=row;persist()
    row=journal['steps']['prod-'+key]
    attrs={'sport':sport,'model':model or key,'collection_year':'2026'}
    if kind=='vestuario':attrs.update(garment_kind='Camiseta' if 'Camiseta' in name else 'Moletom' if 'Moletom' in name else 'Saia')
    if pack:attrs['pack_qty']=str(pack)
    if consume:attrs['consumable_kind']=consume
    row=step('class-'+key,'PATCH',f"/products/{row['id']}",{'commercial_name':name,'unit':unit,'category_id':cats['raquetes' if kind=='raquete' else 'vestuario' if kind=='vestuario' else 'acessorios'],'product_type_id':types[kind],'size':size,'color':color,'attributes':attrs,'taxonomy_status':'CONFIDENT','taxonomy_reason':'Demonstração Heroes; transações e preços sintéticos','lifecycle_status':'ACTIVE'})
    if price is not None:step('price-'+key,'POST','/catalog/sales-prices',{'product_id':row['id'],'list_id':list_id,'amount':str(price),'unit':unit,'valid_from':date(-30),'valid_to':date(90) if key!='FOREST' else date(-1),'reason':'Preço fictício de demonstração, inspirado em referência pública; não é política comercial aprovada','request_key':CODE+'-price-'+key})
    row={**row,'demo_price':price,'key':key};products.append(row);return row
for key,price in [('SHOW26',3289),('FIERCE26',3000),('ARION26',3649),('AURA26',2800),('THEBULL26',3300),('STARLIGHT26',3000),('FOREST',1900),('HARLEY24',1599)]:
    product(key,'Raquete Heroes '+key,'raquete',price,model=key)
for size in ['S','M','L','XL','XXL']:product('BULL-'+size,'Camiseta Heroes The Bull · '+size,'vestuario',449,model='THE BULL',size=size,sport='Beach Tennis / Padel')
for color in ['Purple','Brown']:
    for size in ['S','M','L']:product('WAVE-'+color+'-'+size,'Moletom Heroes Wave feminino · '+color+' · '+size,'vestuario',590,model='WAVE',size=size,color=color,sport='Beach Tennis / Padel')
for size in ['S','M','L','XL']:product('SAIA-'+size,'Saia Heroes Starlight · '+size,'vestuario',600,model='STARLIGHT',size=size)
product('GRAVITY','Mochila Heroes Gravity Fierce','mochila',1149,model='GRAVITY FIERCE')
product('GRIP3','Overgrip Heroes High Level · pacote 3','consumivel','89.90',model='HIGH LEVEL 3',sport='Beach Tennis / Padel',unit='PCT',pack=3,consume='OVERGRIP')
for color in ['Branco','Misto']:product('GRIP60-'+color,'Overgrip Heroes High Level · pacote 60 · '+color,'consumivel','1799.90',model='HIGH LEVEL 60',sport='Beach Tennis / Padel',color=color,unit='PCT',pack=60,consume='OVERGRIP')
product('BALL3','Bolas Heroes Beach Tennis · embalagem 3','consumivel','74.90',model='STAGE 2 · 3',unit='PCT',pack=3,consume='BALL')
product('BALL50','Bolas Heroes Stage 2 · caixa 50','consumivel',None,model='STAGE 2 · 50',unit='CX',pack=50,consume='BALL')
product('TOURO26','Raquete Heroes Touro 26 · Padel','raquete',3059,model='TOURO 26',sport='Padel')
product('NOVA27','Raquete Heroes Nova 27 · Pickleball','raquete',1945,model='NOVA 27',sport='Pickleball')
supplier=step('supplier','POST','/suppliers',{'name':'DEMONSTRAÇÃO Heroes Export','country_code':'IT'})
carrier=step('carrier','POST','/logistics-providers',{'legal_name':'DEMONSTRAÇÃO Rota Heroes','provider_type':'TRANSPORTADOR','active':True})
payee=step('payee','POST','/customs/payees',{'name':'DEMONSTRAÇÃO Despachante Heroes'})
def purchase(key,lines,due,*,freight=0,tax=0,other=0,receive=None,stages=3,installments=1):
    def s(k,m,p,b=None,**kw):return step(key+'-'+k,m,p,b,**kw)
    total=sum(D(str(q))*D(str(price)) for _,q,price in lines)
    rows=[['Produto / SKU','Quantidade','Preço EUR','Total EUR']]+[[p['commercial_name']+' / '+p['sku'],str(q)+' '+p['unit'],str(price),str(D(str(q))*D(str(price)))] for p,q,price in lines]+[['TOTAL','','',str(total)]]
    commercial=pdf(key+'-commercial','Compra '+key,rows,'Origem: preparação pelas APIs; documento vinculado, não ingestão. Fornecedor fictício Heroes Export.')
    order=s('order','POST','/orders',{'code':CODE+'-'+key,'supplier_id':supplier['id'],'currency':'EUR','order_date':date(-40),'notes':'DEMONSTRAÇÃO Heroes; preparação por APIs.'})
    for i,(p,q,price) in enumerate(lines):order=s('item-'+str(i),'POST',f"/orders/{order['id']}/items",{'expected_version':order['version'],'product_id':p['id'],'quantity':str(q),'unit_price':str(price),'unit':p['unit']})
    orderdoc=upload(key+'-orderdoc',commercial,'order',order['id'])
    order=s('confirm','POST',f"/orders/{order['id']}/confirm",{'expected_version':order['version']})
    inv=s('invoice','POST',f"/orders/{order['id']}/invoices",{'invoice_number':CODE+'-FAT-'+key,'invoice_type':'FINAL','invoice_date':date(-30)})
    inv=s('invoice-items','PUT',f"/invoices/{inv['id']}/items",{'expected_version':inv['version'],'items':[{'order_item_id':it['id'],'quantity':str(lines[i][1]),'unit_price_gross':str(lines[i][2]),'discount_type':'NONE','unit':lines[i][0]['unit']} for i,it in enumerate(order['items'])]})
    percents=['100'] if installments==1 else ['30','30','40']
    inv=s('terms','PUT',f"/invoices/{inv['id']}/terms",{'expected_version':inv['version'],'mode':'PERCENT','terms':[{'due_date':date(due+i*30),'percent':v} for i,v in enumerate(percents)]})
    invdoc=upload(key+'-invdoc',commercial,'invoice',inv['id'],'official')
    inv=s('issue','POST',f"/invoices/{inv['id']}/issue",{'expected_version':api('GET',f"/invoices/{inv['id']}")['version']})
    for i,payable in enumerate(inv['payables']):s('fx-'+str(i),'POST',f"/payables/{payable['id']}/fx-plan",{'kind':'INITIAL','rate':'6','effective_from':date(-30)})
    result={'key':key,'order':order,'invoice':inv,'documents':[orderdoc,invdoc]}
    if receive is None:return result
    ship=s('ship','POST','/shipments',{'modal':'SEA','logistics_provider_id':carrier['id'],'origin':'Gênova','destination':'Santos','planned_departure':date(-25),'planned_arrival':date(-15),'notes':'DEMONSTRAÇÃO Heroes '+key})
    for i,it in enumerate(order['items']):ship=s('shipitem-'+str(i),'POST',f"/shipments/{ship['id']}/items",{'expected_version':ship['version'],'order_item_id':it['id'],'quantity':it['quantity']})
    pack=pdf(key+'-packing','Packing '+key,[['Produto','Quantidade']]+[[p['commercial_name'],str(q)+' '+p['unit']] for p,q,_ in lines],'Quantidades correspondem à fatura '+inv['invoice_number'])
    packdoc=upload(key+'-packdoc',pack,'shipment',ship['id']);result['documents'].append(packdoc)
    for i,event in enumerate([-26,-25,-15][:stages]):ship=s('advance-'+str(i),'POST',f"/shipments/{ship['id']}/advance",{'expected_version':ship['version'],'event_date':date(event)})
    result['shipment']=ship
    if stages<3:return result
    proc=s('process','POST','/import-processes',{'external_reference':CODE+'-DI-'+key,'notes':'DEMONSTRAÇÃO; sem transmissão externa'})
    proc=s('linkinv','POST',f"/import-processes/{proc['id']}/invoices",{'expected_version':proc['version'],'invoice_id':inv['id']})
    for i,it in enumerate(inv['items']):proc=s('allocinv-'+str(i),'POST',f"/import-processes/{proc['id']}/invoice-items/allocate",{'expected_version':proc['version'],'invoice_item_id':it['id'],'allocated_qty':it['quantity']})
    proc=s('linkship','POST',f"/import-processes/{proc['id']}/shipments",{'expected_version':proc['version'],'shipment_id':ship['id']})
    for i,it in enumerate(ship['items']):proc=s('allocship-'+str(i),'POST',f"/import-processes/{proc['id']}/shipment-items/allocate",{'expected_version':proc['version'],'shipment_item_id':it['id'],'allocated_qty':it['quantity']})
    proc=s('submit','POST',f"/import-processes/{proc['id']}/submit",{'expected_version':proc['version']})
    costpdf=pdf(key+'-cost','Composição documental '+key,[['Componente','Valor BRL'],['Mercadoria · EUR '+str(total)+' × 6',str(total*6)],['Frete internacional',str(freight)],['Tributos brutos',str(tax)],['Outras despesas',str(other)],['TOTAL',str(total*6+freight+tax+other)]],'Câmbio planejado/documental 6,00; não realizado bancário. Base: toda a quantidade faturada, não apenas recebida.')
    costdoc=upload(key+'-costdoc',costpdf,'import_process',proc['id']);result['documents'].append(costdoc)
    funding=s('funding','POST',f"/import-processes/{proc['id']}/funding-requests",{'payee_id':payee['id'],'currency':'BRL','declared_total':str(tax+freight),'document_id':costdoc['id'],'reference':CODE+'-NUM-'+key,'due_date':date(5),'idempotency_key':CODE+'-funding-'+key})
    for kind,content in [('value-bases',[{'position':1,'label':'FOB','code':'FOB','amount':str(total),'currency':'EUR'}]),('tax-lines',[{'position':1,'label':'Imposto de importação fictício','code':'II','amount':str(tax)}]),('expense-lines',[{'position':1,'label':'Frete internacional','code':'FRETE_INT','amount':str(freight)}])]:
        funding=s(kind,'PUT',f"/import-processes/{proc['id']}/funding-requests/{funding['id']}/{kind}",{'expected_version':funding['version'],'lines':content})
    result['process']=proc;result['funding']=funding;result['receipts']=[]
    for ri,quantities in enumerate(receive):
        nat=s('nat-'+str(ri),'POST',f"/import-processes/{proc['id']}/nationalizations",{'reference':CODE+'-LIB-'+key+'-'+str(ri),'notes':'DEMONSTRAÇÃO'})
        nat=s('natitems-'+str(ri),'POST',f"/import-processes/{proc['id']}/nationalizations/{nat['id']}/items",{'expected_version':nat['version'],'items':[{'shipment_item_id':ship['items'][i]['id'],'product_id':p['id'],'quantity':str(quantities[i])} for i,(p,_,_) in enumerate(lines) if quantities[i]>0]})
        nat=s('natconfirm-'+str(ri),'POST',f"/import-processes/{proc['id']}/nationalizations/{nat['id']}/confirm",{'expected_version':nat['version']})
        receipt=s('receipt-'+str(ri),'POST','/inventory/receipts',{'receipt_type':'DOMESTIC_IN','location_code':'DOMESTIC-MAIN','process_id':proc['id'],'nationalization_id':nat['id'],'notes':CODE+' '+key})
        receipt=s('receiptitems-'+str(ri),'POST',f"/inventory/receipts/{receipt['id']}/lines",{'expected_version':receipt['version'],'lines':[{'product_id':it['product_id'],'quantity':it['quantity'],'nationalization_item_id':it['id'],'shipment_item_id':it['shipment_item_id']} for it in nat['items']]})
        receipt=s('receiptconfirm-'+str(ri),'POST',f"/inventory/receipts/{receipt['id']}/confirm",{'expected_version':receipt['version']});result['receipts'].append(receipt)
    case=s('case','POST','/costing/cases',{'process_id':proc['id']});casedoc=upload(key+'-casedoc',costpdf,'costing_case',case['id']);result['documents'].append(casedoc)
    s('expense','POST',f"/costing/cases/{case['id']}/expenses",{'category':'OUTRAS','description':'DEMONSTRAÇÃO despesa local','amount':str(other),'currency':'BRL','document_id':casedoc['id'],'allocation_method':'VALUE','expense_date':date(-15)})
    version=s('calc','POST',f"/costing/cases/{case['id']}/recalculate",{'kind':'REVISED'})
    version=s('publish','POST',f"/costing/versions/{version['id']}/publish",{'reason':'DEMONSTRAÇÃO Heroes; conferência das fontes','allow_partial':False})
    assert D(version['included_total_brl'])==total*6+freight+tax+other,(key,version['included_total_brl'])
    result.update(case=case,version=version);return result
show=products[0]
stories=[purchase('A',[(show,20,150)],-7,freight=2000,tax=3000,other=1000,receive=[[12],[8]]),purchase('B',[(show,30,170)],45,freight=3000,tax=5400,other=1500,receive=[[30]])]
for group,items in enumerate([products[1:8],products[8:19],products[19:]]):
    lines=[(p,10+3*(i%5),max(3,round(float(p['demo_price'] or 750)/15,2))) for i,p in enumerate(items)]
    stories.append(purchase('C'+str(group),lines,-15+group*20,freight=500,tax=900,other=200,receive=[[q for _,q,_ in lines]],installments=3))
for i in range(3):stories.append(purchase('F'+str(i),[(products[i+1],10+i,160)],5+i*20,installments=3,receive=[] if i==0 else None,stages=2))
# No explicit origin on this withdrawal: managerial FIFO is intentionally estimated.
step('show-withdrawal','POST','/inventory/adjustments',{'location_code':'DOMESTIC-MAIN','product_id':show['id'],'quantity_delta':'-8','reason':CODE+' saída fictícia sem origem explícita'})
for i,story in enumerate(stories[:7]):
    inv=story['invoice'];p=inv['payables'][0];amount='1000' if i==0 else str(D(p['amount'])/2 if i%2 else D(p['amount']))
    doc=pdf('payment-'+str(i),'Pagamento de demonstração',[['Referência','Valor EUR'],[inv['invoice_number'],amount]],'Registro interno fictício. A alocação, não o registro isolado, liquida a obrigação.')
    with doc.open('rb') as f:payment=step('payment-'+str(i),'POST','/payments/with-document',files={'file':(doc.name,f,'application/pdf')},data={'supplier_id':str(supplier['id']),'order_id':str(story['order']['id']),'amount':amount,'currency':'EUR','payment_date':date(0),'external_reference':CODE+'-PAY-'+str(i),'idempotency_key':CODE+'-pay-'+str(i)})
    if i!=1:
        current=api('GET',f"/payables/{p['id']}")
        if 'allocation-'+str(i) not in journal['steps']:assert D(current['balance'])==D(p['amount'])
        payment=step('allocation-'+str(i),'POST',f"/payments/{payment['id']}/allocations",{'expected_version':payment['version'],'idempotency_key':CODE+'-allocation-'+str(i),'allocations':[{'payable_id':p['id'],'expected_version':current['version'],'amount':amount}]})
    story['payment']=payment
manifest={'scenario_id':CODE,'base_date':date(0),'database_port':5445,'origin':'Prepared through public APIs/domain services; generated supporting PDFs, not ingestion','products':[{'id':p['id'],'sku':p['sku'],'name':p['commercial_name'],'unit':p['unit'],'price':p['demo_price']} for p in products],
    'stories':stories,'expected_show':{'quantity':'42','cost':'54900','sale':'138138','margin_numerator':'83238','a_remaining':'12','b_remaining':'30','a_open_eur':'2000','b_open_eur':'5100'},'limitations':['Tabela e transações fictícias. Política gerencial, não contábil.','Numérarios preparados com composição documental; confirmar obrigação local depende do cenário.']}
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'manifest':str(MANIFEST),'products':len(products),'stories':len(stories),'steps':len(journal['steps'])}))
