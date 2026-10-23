"""Real PostgreSQL tests; fixture database is explicitly isolated by the runner."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from app.catalog import public as catalog
from app.customs.models import ImportProcess,Nationalization,NationalizationItem
from app.inventory import public as inventory
from app.inventory.models import GoodsReceipt,InventoryMovement,ReceiptOperation,StockLocation
from app.audit.models import AuditLog
from app.identity.seed import ensure_e2e_operator_users

@pytest.fixture
def source(db):
    product=catalog.create_product(db,sku='REC-'+uuid4().hex[:10],description='Teste recebimento')
    catalog.update_product(db,product.id,unit='UN',unit_set=True)
    process=ImportProcess(code='REC-'+uuid4().hex[:10],external_reference='QA RECEBIMENTO',status='SUBMITTED',version=1)
    db.add(process);db.flush()
    nat=Nationalization(process_id=process.id,reference='QA LIBERADA',status='CONFIRMED',version=1)
    db.add(nat);db.flush()
    item=NationalizationItem(nationalization_id=nat.id,product_id=product.id,quantity=10)
    db.add(item);db.commit()
    return dict(item=item.id,product=product.id,process=process.id,nat=nat.id)

def args(s,**overrides):
    return dict(actor_id='stock-test',request_key=uuid4().hex,item_id=s['item'],quantity='4',unit='UN',location_code='DOMESTIC-MAIN',**overrides)

def test_partial_retry_finish_audit(db,source):
    payload=args(source);r=inventory.receive_domestic(db,**payload);rid=r.id;db.commit()
    assert inventory.receive_domestic(db,**payload).id==rid;db.commit()
    row=inventory.receiving_rows(db,item_id=source['item'],state='all')['rows'][0]
    assert (Decimal(row['released_qty']),Decimal(row['received_qty']),Decimal(row['pending_qty']))==(10,4,6)
    payload2=args(source);payload2['quantity']='6';inventory.receive_domestic(db,**payload2);db.commit()
    assert Decimal(inventory.get_stock_balance(db,product_id=source['product'],location_code='DOMESTIC-MAIN')['qty'])==10
    assert db.query(InventoryMovement).filter_by(product_id=source['product']).count()==2
    assert db.query(AuditLog).filter_by(entity_type='goods_receipt',entity_id=str(rid),action='goods_receipt.receive',actor_id='stock-test').count()==1
    assert inventory.receiving_rows(db,item_id=source['item'],state='all')['rows'][0]['state']=='complete'

@pytest.mark.parametrize('field,value',[('quantity','11'),('quantity','0'),('quantity','-1'),('quantity','NaN'),('quantity','Infinity'),('quantity','0.00001'),('quantity','1e99'),('unit','CX'),('location_code','BONDED-MAIN'),('location_code','UNKNOWN')])
def test_invalid_has_no_side_effect(db,source,field,value):
    payload=args(source);payload[field]=value
    with pytest.raises(inventory.InventoryError):inventory.receive_domestic(db,**payload)
    db.rollback()
    assert db.query(GoodsReceipt).filter_by(process_id=source['process']).count()==0
    assert db.query(InventoryMovement).filter_by(product_id=source['product']).count()==0

@pytest.mark.parametrize('kind',['draft','reversed','cancelled','inactive_location','missing_unit','inactive_product'])
def test_ineligible(db,source,kind):
    if kind in ('draft','reversed'):db.get(Nationalization,source['nat']).status=kind.upper()
    elif kind=='cancelled':db.get(ImportProcess,source['process']).status='CANCELLED'
    elif kind=='inactive_location':db.query(StockLocation).filter_by(code='DOMESTIC-MAIN').one().active=False
    elif kind=='missing_unit':catalog.update_product(db,source['product'],unit=None,unit_set=True)
    else:catalog.update_product(db,source['product'],is_active=False)
    db.flush()
    with pytest.raises(inventory.InventoryError):inventory.receive_domestic(db,**args(source))
    db.rollback()

def test_key_bound_to_actor_and_payload(db,source):
    payload=args(source);inventory.receive_domestic(db,**payload);db.commit()
    for delta in ({'actor_id':'another'},{'quantity':'3'}):
        with pytest.raises(inventory.InventoryError):inventory.receive_domestic(db,**{**payload,**delta})
        db.rollback()

def test_two_receipts_compete_and_retry_concurrently(engine,db,source):
    barrier=Barrier(2)
    def run(key):
        with Session(engine) as s:
            barrier.wait()
            try:
                payload=args(source);payload.update(quantity='6',request_key=key)
                r=inventory.receive_domestic(s,**payload);rid=r.id;s.commit();return rid
            except inventory.InventoryError:s.rollback();return 'blocked'
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,[uuid4().hex,uuid4().hex]))
    assert results.count('blocked')==1
    assert Decimal(inventory.get_stock_balance(db,product_id=source['product'],location_code='DOMESTIC-MAIN')['qty'])==6
    barrier=Barrier(2);same=uuid4().hex
    def retry(_):
        with Session(engine) as s:
            barrier.wait();payload=args(source);payload.update(quantity='4',request_key=same)
            r=inventory.receive_domestic(s,**payload);rid=r.id;s.commit();return rid
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(retry,[1,2]))
    assert results[0]==results[1]
    db.expire_all();assert Decimal(inventory.get_stock_balance(db,product_id=source['product'],location_code='DOMESTIC-MAIN')['qty'])==10

def test_legacy_duplicate_lines_cannot_exceed_release(db,source):
    r=inventory.create_receipt(db,location_code='DOMESTIC-MAIN',process_id=source['process'],receipt_type='DOMESTIC_IN')
    r=inventory.add_receipt_lines(db,r.id,expected_version=r.version,lines=[dict(product_id=source['product'],quantity='6',nationalization_item_id=source['item'])]*2)
    with pytest.raises(inventory.OverReceiptError):inventory.confirm_receipt(db,r.id,expected_version=r.version)
    db.rollback()

def test_legacy_two_drafts_cannot_overreceive(engine,db,source):
    drafts=[]
    for _ in range(2):
        r=inventory.create_receipt(db,location_code='DOMESTIC-MAIN',process_id=source['process'],receipt_type='DOMESTIC_IN')
        r=inventory.add_receipt_lines(db,r.id,expected_version=r.version,lines=[dict(product_id=source['product'],quantity='6',nationalization_item_id=source['item'])])
        drafts.append((r.id,r.version));db.commit()
    barrier=Barrier(2)
    def run(draft):
        with Session(engine) as s:
            barrier.wait()
            try:
                inventory.confirm_receipt(s,draft[0],expected_version=draft[1]);s.commit();return 'ok'
            except inventory.OverReceiptError:s.rollback();return 'blocked'
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,drafts))
    assert sorted(results)==['blocked','ok']
    assert Decimal(inventory.get_stock_balance(db,product_id=source['product'],location_code='DOMESTIC-MAIN')['qty'])==6

def test_atomic_balance_across_independent_origins(engine,db,source):
    process=ImportProcess(code='PAR-'+uuid4().hex[:10],status='SUBMITTED',version=1);db.add(process);db.flush()
    nat=Nationalization(process_id=process.id,status='CONFIRMED',version=1);db.add(nat);db.flush()
    item=NationalizationItem(nationalization_id=nat.id,product_id=source['product'],quantity=10);db.add(item);db.commit()
    other={**source,'process':process.id,'nat':nat.id,'item':item.id};barrier=Barrier(2)
    def run(origin):
        with Session(engine) as s:
            barrier.wait();inventory.receive_domestic(s,**args(origin));s.commit()
    with ThreadPoolExecutor(2) as pool:list(pool.map(run,[source,other]))
    assert Decimal(inventory.get_stock_balance(db,product_id=source['product'],location_code='DOMESTIC-MAIN')['qty'])==8

def test_server_acl_and_minimum_fields(client,db,source):
    ensure_e2e_operator_users(db);db.commit()
    assert client.post('/api/auth/login',json={'email':'estoque@epic.com.br','password':'ensaio123'}).status_code==200
    r=client.get('/api/inventory/receiving',params={'item_id':source['item'],'state':'all'});assert r.status_code==200
    row=r.json()['rows'][0]
    assert set(row)=={'item_id','nationalization_id','process_id','process_code','process_reference','release_reference','product_id','sku','product_name','unit','released_qty','received_qty','pending_qty','state','block_reason'}
    for path in ['/api/import-processes','/api/catalog/sales-prices','/api/payables','/api/payments','/api/costing/queue']:
        assert client.get(path).status_code==403,path
    payload=args(source);payload.pop('actor_id')
    assert client.post('/api/inventory/receiving/confirm',json=payload).status_code==200
    assert client.post('/api/inventory/receiving/confirm',json={**payload,'financial_amount':'10'}).status_code==422
    client.post('/api/auth/logout')
    client.post('/api/auth/login',json={'email':'comprador@epic.com.br','password':'ensaio123'})
    assert client.get('/api/inventory/receiving').status_code==200
    assert client.post('/api/inventory/receiving/confirm',json=payload).status_code==403
