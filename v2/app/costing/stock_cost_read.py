"""Bulk persisted line valuation; current published version, never recalculate."""
from decimal import Decimal
from sqlalchemy.orm import selectinload
from app.costing.models import CostingCase, CostingVersion, CostingLine, CostComponent
from app.billing import public as billing

def published_origin_costs(db, process_ids):
    if not process_ids:return []
    cases=db.query(CostingCase).filter(CostingCase.import_process_id.in_(process_ids)).all()
    by_version={c.current_published_id:c for c in cases if c.current_published_id}
    versions=db.query(CostingVersion).filter(CostingVersion.id.in_(by_version),CostingVersion.status=='PUBLISHED').options(
        selectinload(CostingVersion.lines).selectinload(CostingLine.allocations),selectinload(CostingVersion.components)).all()
    units=billing.stock_invoice_units(db,{l.invoice_item_id for v in versions for l in v.lines if l.invoice_item_id})
    result=[]
    for v in versions:
        components={c.id:c for c in v.components if c.included}
        for line in v.lines:
            total=sum((a.amount_brl for a in line.allocations if a.component_id in components),Decimal(0))
            # Unknown components remain partial even when a known subtotal exists.
            complete=not v.partial_coverage and all(c.amount_brl is not None for c in components.values()) and bool(components)
            result.append({'process_id':by_version[v.id].import_process_id,'case_id':v.case_id,'version_id':v.id,
                'number':v.version_number,'kind':v.kind,'invoice_item_id':line.invoice_item_id,'shipment_item_id':line.shipment_item_id,
                'product_id':line.product_id,'unit':units.get(line.invoice_item_id),'base_quantity':line.qty,'total_brl':total,'unit_brl':total/line.qty,
                'complete':complete,'fx':(v.snapshot or {}).get('fx',{})})
    return result
