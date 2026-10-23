from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.catalog import public as catalog
from app.foundation.deps import enforce_permission, get_current_user, get_db
from app.foundation.uow import UnitOfWork
from app.foundation.errors import AppError
from app.catalog.price_changes import change_price,price_history
from app.catalog.price_import import preview_prices,confirm_prices
from typing import Literal

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

class ChangeIn(BaseModel):
    action:Literal['replace','close']
    expected_token:str=Field(min_length=64,max_length=64)
    amount:Decimal|None=Field(default=None,gt=0,max_digits=18,decimal_places=4)
    unit:str|None=Field(default=None,max_length=16)
    valid_from:date|None=None
    valid_to:date|None=None
    reason:str=Field(min_length=1,max_length=512)
    request_key:str=Field(min_length=8,max_length=128)

@router.post('/catalog/sales-prices/{price_id}/change')
def change(price_id:int,payload:ChangeIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_write')
    try:
        with UnitOfWork(db) as uow:
            result=change_price(db,actor_id=str(user.id),price_id=price_id,**payload.model_dump());uow.commit();return result
    except catalog.CatalogError as e:raise AppError(e.message,code=e.code,status_code=422) from e

@router.get('/catalog/sales-prices/{price_id}/history')
def history(price_id:int,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_read');return price_history(db,price_id)

class PreviewIn(BaseModel):
    list_id:int
    csv_text:str=Field(min_length=1,max_length=1_000_000)
class ConfirmIn(PreviewIn):
    preview_token:str=Field(min_length=64,max_length=64)
    request_key:str=Field(min_length=8,max_length=128)
    reason:str=Field(min_length=1,max_length=512)

@router.post('/catalog/price-import/preview')
def preview(payload:PreviewIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_write')
    try:return preview_prices(db,**payload.model_dump())
    except catalog.CatalogError as e:raise AppError(e.message,code=e.code,status_code=422) from e

@router.post('/catalog/price-import/confirm')
def confirm(payload:ConfirmIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'catalog:prices_write')
    try:
        with UnitOfWork(db) as uow:
            result=confirm_prices(db,actor_id=str(user.id),**payload.model_dump());uow.commit();return result
    except catalog.CatalogError as e:raise AppError(e.message,code=e.code,status_code=422) from e
