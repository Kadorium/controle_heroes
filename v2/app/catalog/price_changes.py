"""Catalog commands: preserve old prices and record before/after in the same UoW."""
import hashlib,json
from datetime import date,datetime,timedelta
from decimal import Decimal,InvalidOperation
from zoneinfo import ZoneInfo
from sqlalchemy import text
from app.catalog.models import Product,SalesPriceEntry,SalesPriceList,SalesPriceOperation
from app.catalog.pricing import add_price,price_dict
from app.catalog.errors import CatalogValidationError
from app.audit import public as audit

def today():return datetime.now(ZoneInfo('America/Sao_Paulo')).date()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()

def replay(db,key,actor,payload):
    # Serializes retries even for CSV spanning several products; then lock products in ID order.
    db.execute(text('select pg_advisory_xact_lock(:key)'),{'key':int(hashlib.sha256(key.encode()).hexdigest()[:15],16)})
    old=db.query(SalesPriceOperation).filter_by(request_key=key).first()
    if old:
        if old.actor_id!=str(actor) or old.payload_hash!=digest(payload):raise CatalogValidationError('Confirmação já usada com outros dados. Gere uma nova prévia.')
        return old.result

def remember(db,key,actor,payload,result):
    db.add(SalesPriceOperation(request_key=key,actor_id=str(actor),payload_hash=digest(payload),result=result));db.flush()
    return result

def validate_interval(product,pricelist,amount,unit,start,end):
    if not pricelist:raise CatalogValidationError('Tabela não encontrada. Selecione uma tabela válida.')
    if pricelist.currency!='BRL' or pricelist.nature not in ('GROSS','GROSS_LIST') or not pricelist.channel.strip():raise CatalogValidationError('A tabela deve ter canal definido e preço bruto em BRL.')
    if not product.unit or product.unit!=unit:raise CatalogValidationError(f'Unidade inválida: use {product.unit or "a unidade cadastrada"}.')
    try:value=Decimal(str(amount))
    except InvalidOperation:raise CatalogValidationError('Preço inválido. Use um número positivo.')
    if not value.is_finite() or value<=0 or value>=Decimal('1e14') or value.as_tuple().exponent < -4:raise CatalogValidationError('Preço deve ser positivo, com até quatro casas decimais.')
    if start<today():raise CatalogValidationError('A nova vigência deve começar hoje ou no futuro.')
    if end and end<start:raise CatalogValidationError('Fim da vigência deve ser igual ou posterior ao início.')
    return value

def active_rows(db,pid,lid):
    return db.query(SalesPriceEntry).filter_by(product_id=pid,list_id=lid,cancelled=False).order_by(SalesPriceEntry.valid_from,SalesPriceEntry.id).all()

def prepare_price(db,*,product,list_id,amount,unit,start,end,action,target_id=None):
    value=validate_interval(product,db.get(SalesPriceList,list_id),amount,unit,start,end)
    existing=active_rows(db,product.id,list_id)
    overlapping=[p for p in existing if p.valid_from<=(end or date.max) and (p.valid_to or date.max)>=start]
    target=None
    if action=='replace':
        candidates=[p for p in existing if p.valid_from<=start<=(p.valid_to or date.max)]
        target=next((p for p in candidates if target_id is None or p.id==target_id),None)
        if not target:raise CatalogValidationError('Nenhum preço nessa data para substituir. Escolha Criar ou confira a vigência.')
    if any(p.id!=(target.id if target else None) for p in overlapping):raise CatalogValidationError('Vigência sobrepõe outro preço. Ajuste as datas; o preço futuro será preservado.')
    if action not in ('create','replace'):raise CatalogValidationError('Ação inválida: use criar ou substituir.')
    return {'product_id':product.id,'sku':product.sku,'name':product.commercial_name or product.description,'list_id':list_id,
        'amount':str(value),'unit':unit,'valid_from':start.isoformat(),'valid_to':end.isoformat() if end else None,
        'action':action,'before':price_dict(target) if target else None}

def apply_price(db,plan,*,actor,key,reason):
    before=plan['before'];start=date.fromisoformat(plan['valid_from'])
    if before:
        previous=db.get(SalesPriceEntry,before['id'])
        if price_dict(previous)['revision_token']!=before['revision_token']:raise CatalogValidationError('O preço mudou. Gere uma nova prévia.')
        if previous.valid_from==start:previous.cancelled=True
        else:previous.valid_to=start-timedelta(days=1)
        db.flush()
        audit.record_event(db,actor_id=str(actor),entity_type='sales_price',entity_id=str(previous.id),action='replace',reason_code='SALES_PRICE_REPLACE',details=json.dumps({'before':before,'after':price_dict(previous),'reason':reason},ensure_ascii=False))
    created=add_price(db,actor_id=str(actor),product_id=plan['product_id'],list_id=plan['list_id'],amount=plan['amount'],unit=plan['unit'],valid_from=start,
        valid_to=date.fromisoformat(plan['valid_to']) if plan['valid_to'] else None,request_key=key,reason=reason)
    return {'action':plan['action'],'previous_id':before['id'] if before else None,'price':price_dict(created)}

def change_price(db,*,actor_id,price_id,action,expected_token,valid_from=None,valid_to=None,amount=None,unit=None,reason,request_key):
    payload=locals().copy();payload.pop('db');payload.pop('request_key')
    old=replay(db,request_key,actor_id,payload)
    if old is not None:return old
    row=db.get(SalesPriceEntry,price_id)
    if not row:raise CatalogValidationError('Preço não encontrado.')
    product=db.query(Product).filter_by(id=row.product_id).with_for_update().one();db.refresh(row)
    before=price_dict(row)
    if row.cancelled or before['revision_token']!=expected_token:raise CatalogValidationError('O preço mudou. Reabra o histórico antes de confirmar.')
    if not reason.strip():raise CatalogValidationError('Informe o motivo da alteração.')
    if action=='close':
        if not valid_to or valid_to<max(today(),row.valid_from) or row.valid_to and valid_to>row.valid_to:raise CatalogValidationError('Informe o último dia válido, hoje ou depois, sem ampliar a vigência atual.')
        row.valid_to=valid_to;db.flush()
        audit.record_event(db,actor_id=str(actor_id),entity_type='sales_price',entity_id=str(row.id),action='close',reason_code='SALES_PRICE_CLOSE',details=json.dumps({'before':before,'after':price_dict(row),'reason':reason},ensure_ascii=False))
        result={'action':'close','price':price_dict(row)}
    elif action=='replace':
        if not valid_from:raise CatalogValidationError('Informe quando o novo preço começa.')
        plan=prepare_price(db,product=product,list_id=row.list_id,amount=amount,unit=unit,start=valid_from,end=valid_to,action='replace',target_id=row.id)
        result=apply_price(db,plan,actor=actor_id,key=request_key,reason=reason)
    else:raise CatalogValidationError('Ação desconhecida.')
    return remember(db,request_key,actor_id,payload,result)

def price_history(db,price_id):
    return [{'action':x.action,'at':x.created_at.isoformat(),'details':json.loads(x.details) if x.details else None} for x in audit.history_by_entity(db,'sales_price',str(price_id))]
