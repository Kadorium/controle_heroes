"""Catalog-owned price history. Product lock serializes overlapping interval commands."""
from datetime import date
from decimal import Decimal
from sqlalchemy import or_
from app.catalog.models import Product, SalesPriceEntry, SalesPriceList
from app.catalog.errors import CatalogValidationError
from app.audit import public as audit

def price_dict(p):
    return {"id":p.id,"list_id":p.list_id,"product_id":p.product_id,"amount":str(p.amount),"unit":p.unit,
        "valid_from":p.valid_from.isoformat(),"valid_to":p.valid_to.isoformat() if p.valid_to else None,"reason":p.reason}

def list_prices(db, product_id=None):
    q=db.query(SalesPriceEntry)
    if product_id is not None:q=q.filter(SalesPriceEntry.product_id==product_id)
    return [price_dict(p) for p in q.order_by(SalesPriceEntry.valid_from.desc(),SalesPriceEntry.id.desc()).all()]

def price_lists(db):
    return [{"id":p.id,"code":p.code,"name":p.name,"channel":p.channel,"currency":p.currency,"nature":p.nature} for p in db.query(SalesPriceList).order_by(SalesPriceList.id).all()]

def current_prices(db, list_id, on_date):
    rows=db.query(SalesPriceEntry).filter(SalesPriceEntry.list_id==list_id,SalesPriceEntry.valid_from<=on_date,
        or_(SalesPriceEntry.valid_to.is_(None),SalesPriceEntry.valid_to>=on_date)).all()
    return {p.product_id:price_dict(p) for p in rows}

def ensure_price_list(db, *, code, name, channel, currency='BRL', nature='GROSS', actor_id):
    row=db.query(SalesPriceList).filter_by(code=code).first()
    if row:return row
    if currency!='BRL' or nature!='GROSS':raise CatalogValidationError('Esta versão aceita preço bruto em BRL')
    row=SalesPriceList(code=code,name=name,channel=channel,currency=currency,nature=nature);db.add(row);db.flush()
    audit.record_event(db,actor_id=actor_id,entity_type='sales_price_list',entity_id=str(row.id),action='create',reason_code='SALES_PRICE_LIST_CREATE')
    return row

def add_price(db, *, actor_id, product_id, list_id, amount, unit, valid_from, valid_to=None, request_key, reason):
    p=db.query(Product).filter(Product.id==product_id).with_for_update().first()
    if not p:raise CatalogValidationError("Produto não encontrado")
    if not db.get(SalesPriceList,list_id):raise CatalogValidationError("Tabela não encontrada")
    value=Decimal(str(amount))
    if not value.is_finite() or value<=0 or (valid_to and valid_to<valid_from):raise CatalogValidationError("Confira preço e vigência")
    if not p.unit or unit != p.unit:raise CatalogValidationError("Unidade de venda deve corresponder à unidade cadastrada")
    if not reason.strip():raise CatalogValidationError("Informe o motivo")
    previous=db.query(SalesPriceEntry).filter(SalesPriceEntry.request_key==request_key).first()
    if previous:
        if (previous.product_id,previous.list_id,previous.amount,previous.unit,previous.valid_from,previous.valid_to)!=(product_id,list_id,value,unit,valid_from,valid_to):raise CatalogValidationError("Identificador já utilizado com outros valores")
        return previous
    overlap=db.query(SalesPriceEntry).filter(SalesPriceEntry.product_id==product_id,SalesPriceEntry.list_id==list_id,
        SalesPriceEntry.valid_from<=(valid_to or date.max),or_(SalesPriceEntry.valid_to.is_(None),SalesPriceEntry.valid_to>=valid_from)).first()
    if overlap:raise CatalogValidationError("Já existe preço nessa vigência. Escolha um intervalo sem sobreposição.")
    row=SalesPriceEntry(product_id=product_id,list_id=list_id,amount=value,unit=unit,valid_from=valid_from,valid_to=valid_to,
        request_key=request_key,actor_id=actor_id,reason=reason)
    db.add(row);db.flush()
    audit.record_event(db,actor_id=actor_id,entity_type="sales_price",entity_id=str(row.id),action="create",reason_code="SALES_PRICE_CREATE")
    return row
