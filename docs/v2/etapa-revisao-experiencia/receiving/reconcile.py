"""Read-only proof after UI mutations. Does not repeat a transaction."""
import json,sys
from decimal import Decimal as D
from pathlib import Path
import httpx
from sqlalchemy import create_engine,text
repo=Path(__file__).resolve().parents[4];lab=repo.parent/'audit-lab/receiving-20261023'
port=int(sys.argv[1]) if len(sys.argv)>1 else 8092
dbport=5450 if port==8092 else 5451
folder=lab if dbport==5450 else repo.parent/'audit-runtime/receiving-stock-20261023'
f=json.loads((lab/'fixtures.json').read_text(encoding='utf8'))
c=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=60)
c.post('/api/auth/login',json={'email':'estoque@epic.com.br','password':'ensaio123'}).raise_for_status()
user=c.get('/api/auth/me').raise_for_status().json();assert user['role']=='estoque'
expected={'STOCK':(10,10,0,[4,6]),'RACE':(8,6,2,[6]),'ADMIN':(4,1,3,[1]),'BLOCKED':(0,0,0,[]),'READY':(5,0,5,[])}
result={'url':str(c.base_url),'actor':user['id'],'rows':{}}
for name,(released,received,pending,moves) in expected.items():
    item=f['nat-items-'+name]['items'][0]['id'];product=f['product-'+name]['id']
    row=c.get('/api/inventory/receiving',params={'item_id':item,'state':'all'}).raise_for_status().json()['rows'][0]
    assert tuple(D(row[k]) for k in ['released_qty','received_qty','pending_qty'])==(released,received,pending)
    movement=c.get('/api/inventory/movements',params={'product_id':product}).raise_for_status().json()
    assert sorted(D(m['quantity_delta']) for m in movement)==moves
    balance=c.get(f'/api/inventory/sku/{product}/position').raise_for_status().json()
    assert D(balance['available_qty'])==received
    result['rows'][name]={'row':row,'balance':balance['available_qty'],'movements':movement}
with create_engine(f'postgresql://postgres@127.0.0.1:{dbport}/epic_v2_test').connect() as conn:
    conn.execute(text('SET TRANSACTION READ ONLY'))
    assert Path(conn.execute(text('show data_directory')).scalar()).resolve()==(folder/'postgres').resolve()
    audit=conn.execute(text("select actor_id,entity_id,action,details from audit_log where action='goods_receipt.receive' order by id")).mappings().all()
    assert len(audit)==3 and all(a['actor_id']==str(user['id']) for a in audit)
    operations=conn.execute(text('select request_key,actor_id,receipt_id from inventory_receipt_operations order by id')).mappings().all()
    assert len(operations)==3 and len({o['receipt_id'] for o in operations})==3
    result.update(audit=[dict(a) for a in audit],operations=[dict(o) for o in operations])
c.post('/api/auth/logout');c.post('/api/auth/dev-login').raise_for_status()
m=json.loads((lab/'demo-manifest.json').read_text(encoding='utf8'))
stock=c.get('/api/reporting/stock-explorer',params={'product_id':m['ids']['product']}).raise_for_status().json()['rows'][0]
assert (D(stock['quantity']),D(stock['cost_total']),D(stock['sale_total']))==(42,54900,138138)
payable=c.get('/api/payables/2').raise_for_status().json();assert D(payable['balance'])==2000
result['show']={k:stock[k] for k in ('product_id','quantity','cost_total','sale_total')};result['obligation_A']={'id':2,'balance':payable['balance'],'currency':payable['currency']}
(lab/f'evidence/reconciliation-{port}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
