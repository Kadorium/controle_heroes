"""Public bulk nationalization provenance for Inventory; no writes."""
from app.customs.models import NationalizationItem, Nationalization
def stock_origin_links(db, ids):
    if not ids:return {}
    return {i.id:{"invoice_item_id":i.invoice_item_id,"shipment_item_id":i.shipment_item_id,"process_id":n.process_id}
        for i,n in db.query(NationalizationItem,Nationalization).join(Nationalization,Nationalization.id==NationalizationItem.nationalization_id).filter(NationalizationItem.id.in_(ids)).all()}
