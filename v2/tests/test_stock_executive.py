from datetime import date,timedelta
from decimal import Decimal as D
import pytest
from app.catalog.attributes import normalize_attributes,merge_attributes
from app.catalog.models import Product,ProductType
from app.catalog.pricing import ensure_price_list,add_price,current_prices
from app.catalog.errors import CatalogValidationError
from app.inventory.remaining_sources import replay
from app.inventory import public as inventory
from app.reporting.stock_contract import StockQuery
from app.reporting.stock_explorer import explorer
from app.reporting.stock_economics import value_product,aggregate
from app.reporting.stock_views import save_stock_view,list_stock_views
from app.reporting.errors import ReportingError

def test_attribute_clear_preserves_unsent():
    assert merge_attributes({'sport':'Beach Tennis','model':'SHOW'},normalize_attributes({'model':None}))=={'sport':'Beach Tennis'}
    assert normalize_attributes({'model':'SHOW'})=={'model':'SHOW'}
    with pytest.raises(CatalogValidationError):normalize_attributes({'consumable_kind':'invented'})

def test_explicit_empty_filters_do_not_restrict():
    q=StockQuery(modality_ids=[''],item_kind_ids=[''],position_ids=[''],group_by=[''])
    assert q.modality_ids==q.item_kind_ids==q.position_ids==q.group_by==[]

def test_financial_period_metadata_matches_queries(admin_client):
    r=admin_client.get('/api/reporting/dashboard',params={'view':'executiva','period':'custom','date_from':'2026-01-01','date_to':'2026-12-31','as_of':'2025-01-01'})
    assert r.status_code==200
    ws={w['widget_id']:w for w in r.json()['widgets']}
    for key in ['ap.cash_due','ap.cash_committed']:
        assert 'date_from' not in ws[key]['filters_applied'] and 'date_from' in ws[key]['filters_ignored']
    assert 'as_of' not in ws['treasury.fx_exposure']['filters_applied']
    assert 'as_of' in ws['treasury.fx_exposure']['filters_ignored']

def event(id,qty,origin=None,kind='ADJUSTMENT',loc=1,reversal=None):
    return dict(id=id,product_id=1,location_id=loc,delta=D(qty),receipt_line_id=origin,type=kind,reversal_of_id=reversal)

def test_fifo_layers_and_reverse():
    origins={1:{'process_id':1,'invoice_item_id':1},2:{'process_id':2,'invoice_item_id':2}}
    layers,issues,estimated=replay([event(1,'12',1),event(2,'8',1),event(3,'30',2),event(4,'-8')],origins)
    assert sum(x['quantity'] for x in layers[(1,1)] if x['process_id']==1)==12
    assert sum(x['quantity'] for x in layers[(1,1)] if x['process_id']==2)==30
    assert not issues and (1,1) in estimated
    layers,_,_=replay([event(1,'20',1),event(2,'-8'),event(3,'8',reversal=2)],origins)
    assert sum(x['quantity'] for x in layers[(1,1)])==20

def test_exact_origin_not_last_purchase():
    origins={1:{'process_id':1,'invoice_item_id':11},2:{'process_id':2,'invoice_item_id':22}}
    layers,issues,_=replay([event(1,'20',1),event(2,'30',2),event(3,'-8',2)],origins)
    assert not issues
    assert [x['quantity'] for x in layers[(1,1)]]==[20,22]

def fixture_value():
    p={'product_id':1,'unit':'UN','active':True}
    positions=[{'quantity':D(42),'location':{'regime':'DOMESTIC','active':True,'name':'Principal'},'estimated':True,'reconciled':True,'layers':[{'quantity':D(12),'process_id':1,'invoice_item_id':1},{'quantity':D(30),'process_id':2,'invoice_item_id':2}]}]
    costs=[{'process_id':i,'product_id':1,'invoice_item_id':i,'unit':'UN','unit_brl':D(c),'complete':True,'kind':'REVISED'} for i,c in [(1,1200),(2,1350)]]
    price={'amount':'3289','unit':'UN'}
    return p,positions,costs,price

def test_show_oracle_independent():
    p,pos,costs,price=fixture_value();r=value_product(p,pos,costs,price,can_cost=True,can_price=True,price_currency='BRL')
    assert r['cost_total']==D('54900') and r['sale_total']==D('138138')
    assert r['comparable_sale']-r['comparable_cost']==D('83238')
    assert round(r['margin'],2)==D('60.26')
    assert r['unit_cost']==D('54900')/42

def test_two_receipts_one_economic_origin():
    p,pos,costs,price=fixture_value();pos[0]['layers']=[{'quantity':D(4),'process_id':1,'invoice_item_id':1},{'quantity':D(8),'process_id':1,'invoice_item_id':1},pos[0]['layers'][1]]
    r=value_product(p,pos,costs,price,can_cost=True,can_price=True,price_currency='BRL')
    assert len(r['contributions'])==2
    assert r['contributions'][0]['remaining_quantity']==12 and r['contributions'][0]['subtotal']==14400
    assert r['cost_total']==54900

@pytest.mark.parametrize('change',['no-price','wrong-unit','wrong-currency','partial','no-cost','no-permission'])
def test_missing_partial_not_zero(change):
    p,pos,costs,price=fixture_value();currency='BRL';can_cost=True
    if change=='no-price':price=None
    if change=='wrong-unit':price['unit']='CX'
    if change=='wrong-currency':currency='EUR'
    if change=='partial':costs[1]['complete']=False
    if change=='no-cost':costs=[]
    if change=='no-permission':can_cost=False
    r=value_product(p,pos,costs,price,can_cost=can_cost,can_price=True,price_currency=currency)
    if change in ['no-price','wrong-unit','wrong-currency']:assert r['sale_total'] is None and r['margin'] is None
    if change=='partial':assert r['cost_quantity']==12 and r['unit_cost'] is None and r['comparable_quantity']==12
    if change in ['no-cost','no-permission']:assert r['cost_total'] is None and r['margin'] is None

def test_margin_weighted_and_units():
    p,pos,costs,price=fixture_value();a=value_product(p,pos,costs,price,can_cost=True,can_price=True,price_currency='BRL');a['unit']='UN'
    b={**a,'unit':'PCT','quantity':D(1),'comparable_cost':D(90),'comparable_sale':D(100)}
    t=aggregate([a,b]);assert t['quantities']=={'UN':42,'PCT':1};assert t['margin']==(D(138238)-D(54990))/D(138238)*100

def test_prices_validity_idempotency_and_overlap(db):
    p=Product(sku='stock-test-price',description='Price test',commercial_name='Price test',unit='UN');db.add(p);db.flush()
    l=ensure_price_list(db,code='stock-test-list',name='Teste',channel='Direta',actor_id='1')
    args=dict(actor_id='1',product_id=p.id,list_id=l.id,amount=D(100),unit='UN',valid_from=date(2026,1,1),valid_to=date(2026,2,1),request_key='price-test-unique',reason='teste')
    first=add_price(db,**args);assert add_price(db,**args).id==first.id
    assert current_prices(db,l.id,date(2026,1,20))[p.id]['amount']=='100'
    assert p.id not in current_prices(db,l.id,date(2026,2,2))
    with pytest.raises(CatalogValidationError):add_price(db,**{**args,'request_key':'second-key'})
    with pytest.raises(CatalogValidationError):add_price(db,**{**args,'request_key':'second-key','unit':'CX'})

def test_views_actors_default_version(db):
    a=save_stock_view(db,actor_id='stock-a',name='Principal',config=StockQuery(modality_ids=['bt']).model_dump(),is_default=True)
    b=save_stock_view(db,actor_id='stock-b',name='Principal',config=StockQuery().model_dump(),is_default=True)
    assert [v['id'] for v in list_stock_views(db,'stock-a')]==[a['id']]
    with pytest.raises(ReportingError):save_stock_view(db,actor_id='stock-a',name='Principal',config=StockQuery().model_dump(),view_id=b['id'],expected_version=1)
    with pytest.raises(ReportingError):save_stock_view(db,actor_id='stock-a',name='Principal',config=StockQuery().model_dump(),view_id=a['id'],expected_version=99)
    updated=save_stock_view(db,actor_id='stock-a',name='Principal',config=StockQuery().model_dump(),view_id=a['id'],expected_version=1,is_default=True);assert updated['version']==2

def test_scale_population_group_sort_pagination_acl(db):
    typ=db.query(ProductType).filter_by(slug='consumivel').one()
    for n in range(507):
        p=Product(sku=f'SCALE-STOCK-{n}',description=f'Bola de teste {n:04}',commercial_name=f'Bola de teste {n:04}',unit='PCT',product_type_id=typ.id,attributes={'sport':'Beach Tennis / Padel','consumable_kind':'BALL','model':'Fixture escala'})
        db.add(p);db.flush();inventory.record_adjustment(db,location_code='DOMESTIC-MAIN',product_id=p.id,quantity_delta='1',reason='fixture isolated scale')
    q=StockQuery(q='Bola de teste',modality_ids=['bt','padel'],group_by=['item_kind'],limit=25)
    a=explorer(db,q,permissions=[],admin=True);assert a['total']==507 and a['totals']['quantities']['PCT']=='507.0000'
    b=explorer(db,StockQuery(**{**q.model_dump(),'sort':'-quantity','offset':500,'group_by':['modality']}),permissions=[],admin=True)
    assert a['totals']==b['totals'] and a['population_key']==b['population_key'] and len(b['rows'])==7
    assert len(b['groups'])==1 and b['groups'][0]['totals']['sku_count']==507
    denied=explorer(db,StockQuery(q='Bola de teste'),permissions=['inventory:read']);assert denied['total']==507 and denied['totals']['cost_total'] is None
    with pytest.raises(ReportingError):explorer(db,q,permissions=['inventory:read'])
    with pytest.raises(ReportingError):explorer(db,StockQuery(modality_ids=['not-valid']),permissions=[],admin=True)
