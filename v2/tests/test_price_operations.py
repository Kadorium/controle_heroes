from datetime import timedelta
from decimal import Decimal
import pytest
from app.catalog.models import Product,SalesPriceEntry,SalesPriceOperation,SalesPriceList
from app.catalog.pricing import add_price,price_dict,current_prices,ensure_price_list
from app.catalog.price_changes import change_price,today,price_history
from app.catalog.price_import import preview_prices,confirm_prices,parse_csv
from app.catalog.errors import CatalogValidationError

@pytest.fixture
def prices(db):
    p=Product(sku='LAPTOP-PRICE',description='Teste preço',commercial_name='Teste preço',unit='UN');db.add(p);db.flush()
    table=ensure_price_list(db,code='LAPTOP',name='Teste',channel='Direta',actor_id='1')
    old=add_price(db,actor_id='1',product_id=p.id,list_id=table.id,amount=100,unit='UN',valid_from=today()-timedelta(days=5),request_key='price-initial',reason='fixture')
    return p,table,old

def args(old,**kw):
    return dict(actor_id='1',price_id=old.id,action='replace',expected_token=price_dict(old)['revision_token'],valid_from=today(),amount=120,unit='UN',reason='revisão',request_key='replacement-1',**kw)

def test_replace_retry_history_and_current(db,prices):
    p,t,old=prices;command=args(old);a=change_price(db,**command);b=change_price(db,**command)
    assert a==b and db.query(SalesPriceEntry).count()==2
    assert old.valid_to==today()-timedelta(days=1)
    assert Decimal(current_prices(db,t.id,today())[p.id]['amount'])==120
    assert price_history(db,old.id)[0]['details']['before']['amount'] in ('100','100.0000')
    with pytest.raises(CatalogValidationError):change_price(db,**{**command,'amount':130})

def test_same_day_replace_keeps_old_and_close(db,prices):
    p,t,old=prices;first=change_price(db,**args(old));new=db.get(SalesPriceEntry,first['price']['id'])
    second=change_price(db,**{**args(new),'request_key':'second-replacement','amount':140})
    assert new.cancelled and db.query(SalesPriceEntry).count()==3
    current=db.get(SalesPriceEntry,second['price']['id'])
    change_price(db,actor_id='1',price_id=current.id,action='close',expected_token=price_dict(current)['revision_token'],valid_to=today(),reason='encerrar',request_key='close-price')
    assert p.id in current_prices(db,t.id,today()) and p.id not in current_prices(db,t.id,today()+timedelta(days=1))

@pytest.mark.parametrize('patch',[{'unit':'CX'},{'amount':'NaN'},{'valid_to':today()-timedelta(days=1)},{'valid_from':today()-timedelta(days=1)},{'reason':' '},{'expected_token':'x'*64}])
def test_reject_invalid_change(db,prices,patch):
    with pytest.raises(CatalogValidationError):change_price(db,**{**args(prices[2]),**patch})
    assert db.query(SalesPriceEntry).count()==1

def csvrow(sku='LAPTOP-PRICE',price='150',action='substituir',unit='UN',start=None,end=''):
    return f'sku;preco;unidade;inicio;fim;acao\n{sku};{price};{unit};{start or today()};{end};{action}'

def test_preview_confirm_retry_and_stale(db,prices):
    p,t,old=prices;content=csvrow();preview=preview_prices(db,list_id=t.id,csv_text=content)
    assert preview['valid'] and preview['rows'][0]['action']=='replace'
    command=dict(actor_id='1',list_id=t.id,csv_text=content,preview_token=preview['token'],request_key='import-first',reason='CSV')
    a=confirm_prices(db,**command);assert a==confirm_prices(db,**command)
    assert db.query(SalesPriceEntry).count()==2 and db.query(SalesPriceOperation).count()==1
    with pytest.raises(CatalogValidationError):confirm_prices(db,**{**command,'request_key':'import-stale'})

@pytest.mark.parametrize('csv_text',[csvrow(sku='missing'),csvrow(unit='CX'),csvrow(start='2026-02-30'),csvrow(price='-1'),csvrow(action='criar'),csvrow()+'\nLAPTOP-PRICE;1;UN;2026-10-23;;criar'])
def test_per_line_errors_no_writes(db,prices,csv_text):
    _,t,_=prices;preview=preview_prices(db,list_id=t.id,csv_text=csv_text);assert not preview['valid']
    assert any(x['error'] for x in preview['rows'])
    with pytest.raises(CatalogValidationError):confirm_prices(db,actor_id='1',list_id=t.id,csv_text=csv_text,preview_token=preview['token'],request_key='invalid-import',reason='invalid')
    assert db.query(SalesPriceEntry).count()==1

def test_future_overlap_and_table_validation(db,prices):
    p,t,old=prices
    change_price(db,actor_id='1',price_id=old.id,action='close',expected_token=price_dict(old)['revision_token'],valid_to=today()+timedelta(days=2),reason='future',request_key='close-future')
    future=add_price(db,actor_id='1',product_id=p.id,list_id=t.id,amount=200,unit='UN',valid_from=today()+timedelta(days=3),request_key='future-price',reason='future')
    assert current_prices(db,t.id,today())[p.id]['id']==old.id
    assert current_prices(db,t.id,today()+timedelta(days=3))[p.id]['id']==future.id
    with pytest.raises(CatalogValidationError):change_price(db,**args(old))
    t.channel='';db.flush()
    assert not preview_prices(db,list_id=t.id,csv_text=csvrow())['valid']

def test_malformed_csv():
    with pytest.raises(CatalogValidationError):parse_csv('sku;preco;unidade;inicio;fim;acao\n"unterminated')

def test_http_validation_and_permissions(admin_client):
    assert admin_client.post('/api/catalog/price-import/preview',json={'list_id':999999,'csv_text':csvrow()}).status_code==422
    assert admin_client.post('/api/catalog/sales-prices/1/change',json={'action':'close','expected_token':'x'*64,'valid_to':'2026-02-30','reason':'x','request_key':'invalid-date'}).status_code==422
