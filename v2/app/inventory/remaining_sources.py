"""Gerencial PEPS projection, never mutates the ledger or its balance cache."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from app.inventory.models import InventoryMovement, GoodsReceiptLine, GoodsReceipt, StockLocation, StockBalance
from app.customs import public as customs

def replay(movements, origins):
    """Return remaining layers; generic withdrawals consume FIFO within SKU/location.

    Paired reclassification carries consumed origins. Reversed events are cancelled
    and replayed; any resulting deficit is flagged rather than inventing a purchase.
    """
    layers=defaultdict(list);transfers={};issues=set();estimated=set()
    reversed_ids={m['reversal_of_id'] for m in movements if m['reversal_of_id']}
    for m in movements:
        if m['id'] in reversed_ids or m['reversal_of_id']:continue
        key=(m['product_id'],m['location_id']);qty=Decimal(m['delta'])
        origin=m.get('origin') or origins.get(m['receipt_line_id'],{})
        if qty<0:
            needed=-qty;removed=[]
            candidates=layers[key]
            origin_key='invoice_item_id' if origin.get('invoice_item_id') else 'shipment_item_id'
            explicit=origin.get(origin_key)
            selected=[p for p in candidates if not explicit or p.get(origin_key)==explicit and (not origin.get('process_id') or p.get('process_id')==origin['process_id'])]
            if not explicit:estimated.add(key)
            for p in selected:
                take=min(needed,p['quantity']);needed-=take;p['quantity']-=take
                if take:removed.append({**p,'quantity':take})
                if not needed:break
            if needed:issues.add(key)
            if m['type']=='RECLASS_OUT':transfers[m['receipt_line_id']]=removed
        elif qty>0:
            if m['type']=='RECLASS_IN':
                carried=deepcopy(transfers.get(m['receipt_line_id'],[]))
                if sum((p['quantity'] for p in carried),Decimal(0))!=qty:
                    issues.add(key);carried=[{'quantity':qty,'process_id':None,'invoice_item_id':None,'shipment_item_id':None}]
                layers[key].extend(carried)
            else:layers[key].append({**origin,'quantity':qty,'receipt_line_id':m['receipt_line_id'],'movement_id':m['id']})
    return layers,issues,estimated

def remaining_sources(db):
    ledger=db.query(InventoryMovement).order_by(InventoryMovement.created_at,InventoryMovement.id).all()
    receipts=db.query(GoodsReceiptLine,GoodsReceipt).join(GoodsReceipt,GoodsReceipt.id==GoodsReceiptLine.receipt_id).all()
    links=customs.stock_origin_links(db,{l.nationalization_item_id for l,r in receipts if l.nationalization_item_id}|{m.nationalization_item_id for m in ledger if m.nationalization_item_id})
    origins={l.id:{'process_id':r.process_id,'shipment_item_id':l.shipment_item_id,**links.get(l.nationalization_item_id,{})} for l,r in receipts}
    events=[{'id':m.id,'product_id':m.product_id,'location_id':m.location_id,'delta':m.quantity_delta,'receipt_line_id':m.receipt_line_id,'reversal_of_id':m.reversal_of_id,'type':m.movement_type,'origin':links.get(m.nationalization_item_id,{})} for m in ledger]
    layers,issues,estimated=replay(events,origins)
    locations={l.id:{'id':l.id,'name':l.name,'regime':l.location_type,'active':l.active} for l in db.query(StockLocation).all()}
    result=[]
    for b in db.query(StockBalance).all():
        key=(b.product_id,b.location_id);positive=[p for p in layers[key] if p['quantity']>0]
        valid=key not in issues and sum((p['quantity'] for p in positive),Decimal(0))==b.qty
        result.append({'product_id':b.product_id,'location':locations[b.location_id],'quantity':b.qty,
            'layers':positive if valid else [],'reconciled':valid,'estimated':key in estimated})
    return result,list(locations.values())
