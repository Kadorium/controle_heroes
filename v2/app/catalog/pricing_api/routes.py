from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.catalog import public as catalog
from app.foundation.deps import enforce_permission, get_current_user, get_db
from app.foundation.uow import UnitOfWork
from app.foundation.errors import AppError

router=APIRouter(tags=["catalog-prices"])
class PriceIn(BaseModel):
    product_id:int
    list_id:int
    amount:Decimal=Field(gt=0,max_digits=18,decimal_places=4)
    unit:str=Field(min_length=1,max_length=16)
    valid_from:date
    valid_to:date|None=None
    request_key:str=Field(min_length=8,max_length=128)
    reason:str=Field(min_length=1,max_length=512)

@router.get('/catalog/price-lists')
def lists(db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_read')
    return catalog.price_lists(db)

@router.get('/catalog/sales-prices')
def prices(product_id:int|None=None,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_read')
    return catalog.list_prices(db,product_id)

@router.post('/catalog/sales-prices')
def create(payload:PriceIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_write')
    try:
        with UnitOfWork(db) as uow:
            row=catalog.add_price(db,actor_id=str(user.id),**payload.model_dump())
            result=catalog.price_dict(row);uow.commit();return result
    except catalog.CatalogError as e:raise AppError(e.message,code=e.code,status_code=422) from e
