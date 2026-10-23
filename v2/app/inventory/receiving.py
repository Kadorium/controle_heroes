"""Operational receiving: minimum read model and atomic, retry-safe command."""
import hashlib
import json
from decimal import Decimal
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from app.audit import public as audit
from app.catalog import public as catalog
from app.customs import public as customs
from app.inventory import commands, repository
from app.inventory.errors import InventoryValidationError, NationalizationRequired
from app.inventory.models import GoodsReceipt, GoodsReceiptLine, ReceiptOperation


def receiving_rows(db: Session, *, q='', state='pending', limit=25, offset=0, item_id=None):
    sources = customs.receiving_sources(db, [item_id] if item_id else None)
    products = catalog.get_products_bulk(db, {s['product_id'] for s in sources if s['product_id']})
    received = dict(db.query(GoodsReceiptLine.nationalization_item_id,func.sum(GoodsReceiptLine.quantity))
        .join(GoodsReceipt).filter(GoodsReceipt.status=='CONFIRMED',
            GoodsReceipt.receipt_type.in_(('DOMESTIC_IN','RECLASS')))
        .group_by(GoodsReceiptLine.nationalization_item_id).all())
    rows=[]
    for s in sources:
        p=products.get(s['product_id']); unit=p.unit if p else None
        released=Decimal(s['quantity']) if s['release_status']=='CONFIRMED' else Decimal(0)
        used=Decimal(received.get(s['item_id'],0)); pending=max(Decimal(0),released-used)
        blocked=('Origem cancelada' if s['process_cancelled'] else
                 'Aguardando liberação' if s['release_status']!='CONFIRMED' else
                 'Vincular produto' if not p else 'Revisar unidade do produto' if not unit else
                 'Produto inativo' if not p.is_active else None)
        row=dict(item_id=s['item_id'],nationalization_id=s['nationalization_id'],process_id=s['process_id'],
            process_code=s['process_code'],process_reference=s['process_reference'],release_reference=s['release_reference'],
            product_id=s['product_id'],sku=p.sku if p else None,product_name=p.description if p else None,unit=unit,
            released_qty=str(released),received_qty=str(used),pending_qty=str(pending),
            state='blocked' if blocked else 'pending' if pending>0 else 'complete',block_reason=blocked)
        if state!='all' and row['state']!=state:continue
        if q and q.casefold() not in ' '.join(str(row[k] or '') for k in ('process_code','process_reference','release_reference','sku','product_name')).casefold():continue
        rows.append(row)
    return dict(rows=rows[offset:offset+limit],total=len(rows),limit=limit,offset=offset)


def receive_domestic(db: Session, *, actor_id: str, request_key: str, item_id: int, quantity: str, unit: str, location_code: str):
    qty=commands._req_dec(quantity,field='Quantidade')
    payload=dict(item_id=item_id,quantity=format(qty.normalize(),'f'),unit=unit,location_code=location_code)
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    lock=int.from_bytes(hashlib.sha256(('inventory-receipt:'+request_key).encode()).digest()[:8],'big',signed=True)
    db.execute(text('select pg_advisory_xact_lock(:key)'),{'key':lock})
    prior=db.query(ReceiptOperation).filter_by(request_key=request_key).one_or_none()
    if prior:
        if prior.actor_id!=actor_id or prior.payload_hash!=digest:
            raise InventoryValidationError('Esta confirmação já foi usada para outra operação.',code='conflict')
        return repository.get_receipt(db,prior.receipt_id)
    customs.lock_receiving_sources(db,[item_id])
    rows=receiving_rows(db,item_id=item_id,state='all')['rows']
    if not rows or rows[0]['state']=='blocked':
        raise NationalizationRequired(rows[0]['block_reason'] if rows else 'Liberação não encontrada.')
    row=rows[0]
    if unit!=row['unit']:
        raise InventoryValidationError('Unidade diferente do cadastro. Atualize a consulta.',code='unit_mismatch')
    receipt=commands.create_receipt(db,process_id=row['process_id'],nationalization_id=row['nationalization_id'],
        receipt_type='DOMESTIC_IN',location_code=location_code)
    receipt=commands.add_receipt_lines(db,receipt.id,expected_version=receipt.version,
        lines=[dict(product_id=row['product_id'],quantity=str(qty),nationalization_item_id=item_id)])
    receipt=commands.confirm_receipt(db,receipt.id,expected_version=receipt.version)
    db.add(ReceiptOperation(request_key=request_key,actor_id=actor_id,payload_hash=digest,receipt_id=receipt.id))
    audit.record_event(db,actor_id=actor_id,entity_type='goods_receipt',entity_id=str(receipt.id),
        action='goods_receipt.receive',details=json.dumps({**payload,'process_id':row['process_id'],
            'nationalization_id':row['nationalization_id'],'product_id':row['product_id'],'status':receipt.status}))
    db.flush()
    return receipt
