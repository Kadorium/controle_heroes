from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ValidationError
from app.reporting.errors import ReportingError
from sqlalchemy.orm import Session
from app.foundation.deps import enforce_permission, get_current_user, get_db, permission_set
from app.foundation.uow import UnitOfWork
from app.foundation.settings import get_settings
from app.reporting.stock_contract import StockQuery
from app.reporting.stock_explorer import explorer
from app.reporting.stock_views import list_stock_views, save_stock_view

router=APIRouter(tags=['stock-explorer'])
@router.get('/reporting/stock-explorer')
def read_stock(q:str='',modality_ids:list[str]=Query(default=[]),item_kind_ids:list[str]=Query(default=[]),
    model_ids:list[str]=Query(default=[]),position_ids:list[str]=Query(default=['DOMESTIC']),location_ids:list[int]=Query(default=[]),
    product_id:int|None=None,group_by:list[str]=Query(default=[]),sort:str='name',status:str='positive',
    price_list_id:int|None=None,limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0),
    db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'inventory:read')
    try:
        query=StockQuery(q=q,modality_ids=modality_ids,item_kind_ids=item_kind_ids,model_ids=model_ids,position_ids=position_ids,
            location_ids=location_ids,product_id=product_id,group_by=group_by,sort=sort,status=status,price_list_id=price_list_id,limit=limit,offset=offset)
    except ValidationError as e:
        raise ReportingError('Confira os filtros da consulta',code='invalid_stock_filter',status_code=422) from e
    settings=get_settings()
    return explorer(db,query,permissions=permission_set(user),admin=user.role.name=='admin',economic_policy=settings.app_env=='test' and settings.stock_economics_policy=='DEMO_ORIGIN_FIFO_V1')

class ViewIn(BaseModel):
    name:str=Field(min_length=1,max_length=128)
    config:StockQuery
    is_default:bool=False
    view_id:int|None=None
    expected_version:int|None=None

@router.get('/reporting/stock-views')
def views(db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'inventory:read');return list_stock_views(db,str(user.id))

@router.post('/reporting/stock-views')
def save(payload:ViewIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'inventory:read')
    with UnitOfWork(db) as uow:
        result=save_stock_view(db,actor_id=str(user.id),**payload.model_dump());uow.commit();return result
