"""Inventory-only operational DTOs. No Customs/financial HTTP dependency."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission,get_current_user
from app.foundation.uow import UnitOfWork
from app.inventory import public as inventory
from app.inventory.routes import _map_error

router=APIRouter(prefix='/inventory/receiving',tags=['inventory'])

class ReceivingRow(BaseModel):
    item_id:int
    nationalization_id:int
    process_id:int
    process_code:str
    process_reference:str|None
    release_reference:str|None
    product_id:int|None
    sku:str|None
    product_name:str|None
    unit:str|None
    released_qty:str
    received_qty:str
    pending_qty:str
    state:Literal['pending','complete','blocked']
    block_reason:str|None

class ReceivingPage(BaseModel):
    rows:list[ReceivingRow]
    total:int
    limit:int
    offset:int

class ReceiveIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_key:str=Field(min_length=16,max_length=128,pattern=r'^[a-zA-Z0-9_-]+$')
    item_id:int=Field(gt=0)
    quantity:str=Field(pattern=r'^\d{1,14}(\.\d{1,4})?$')
    unit:str=Field(min_length=1,max_length=16)
    location_code:str=Field(min_length=1,max_length=64)

class ReceiveResult(BaseModel):
    receipt_id:int
    status:str
    product_id:int
    item_id:int
    quantity:str
    location_code:str
    received_at:datetime|None

@router.get('',response_model=ReceivingPage)
def queue(q:str=Query('',max_length=120),state:Literal['pending','complete','blocked','all']='pending',
          limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),item_id:int|None=None,
          db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'inventory:read')
    return inventory.receiving_rows(db,q=q,state=state,limit=limit,offset=offset,item_id=item_id)

@router.post('/confirm',response_model=ReceiveResult)
def confirm(body:ReceiveIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    enforce_permission(user,'inventory:write')
    try:
        with UnitOfWork(db) as uow:
            receipt=inventory.receive_domestic(db,actor_id=str(user.id),**body.model_dump())
            uow.commit()
            line=receipt.lines[0]
            return ReceiveResult(receipt_id=receipt.id,status=receipt.status,product_id=line.product_id,
                item_id=line.nationalization_item_id,quantity=str(line.quantity),
                location_code=receipt.location.code,received_at=receipt.received_at)
    except inventory.InventoryError as exc:
        raise _map_error(exc) from exc
