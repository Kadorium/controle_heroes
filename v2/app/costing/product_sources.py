"""Product cost provenance. Projection of persisted versions/allocations only."""
from decimal import Decimal
from sqlalchemy.orm import Session, selectinload
from app.costing.models import CostingCase, CostingVersion, CostingLine, CostComponent, CostingExpense
from app.costing.errors import CostingNotFound
from app.customs import public as customs
from app.documents import public as documents
from app.orders import public as orders


def product_sources(db: Session, product_id: int, *, limit=25, offset=0, can_orders=False, case_id=None) -> dict:
    matching = db.query(CostingLine.version_id).filter(CostingLine.product_id == product_id)
    versions = db.query(CostingVersion).filter(CostingVersion.id.in_(matching))
    cases = db.query(CostingCase).filter(CostingCase.id.in_(versions.with_entities(CostingVersion.case_id)))
    if case_id is not None:
        cases = cases.filter(CostingCase.id == case_id)
    total = cases.count()
    page = cases.order_by(CostingCase.id.desc()).offset(offset).limit(limit).all()
    ids = [c.id for c in page]
    found = versions.filter(CostingVersion.case_id.in_(ids)).options(selectinload(CostingVersion.lines)).order_by(CostingVersion.version_number.desc()).all() if ids else []
    items = orders.get_order_items_bulk(db, {ln.order_item_id for v in found for ln in v.lines if ln.order_item_id}) if found and can_orders else {}
    purchases = orders.get_orders_bulk(db, {ln.order_id for ln in items.values()}) if items else {}
    labels = customs.cost_process_labels(db, [c.import_process_id for c in page]) if ids else {}
    return {"product_id": product_id, "total": total, "limit": limit, "offset": offset, "rows": [
        {"case_id": c.id, "process_id": c.import_process_id, **labels.get(c.import_process_id, {}),
         "current_published_id": c.current_published_id,
         "purchases": [{"id": o.id, "code": o.code} for o in purchases.values() if o.id in {
             items[ln.order_item_id].order_id for v in found if v.case_id == c.id for ln in v.lines if ln.order_item_id in items}],
         "versions": [{"id": v.id, "number": v.version_number, "kind": v.kind, "status": v.status,
                       "partial_coverage": v.partial_coverage,
                       "invoices": [{"id": i.get("invoice_id"), "number": i.get("invoice_number")} for i in (v.snapshot or {}).get("invoices", [])],
                       "product": next((p for p in (v.snapshot or {}).get("products", []) if p.get("product_id") == product_id), None)}
                      for v in found if v.case_id == c.id]}
        for c in page]}


def product_version(db: Session, product_id: int, version_id: int, *, permissions: set[str], admin=False) -> dict:
    version = db.query(CostingVersion).options(selectinload(CostingVersion.lines),
        selectinload(CostingVersion.components).selectinload(CostComponent.allocations)).filter(CostingVersion.id == version_id).first()
    if not version or not any(ln.product_id == product_id for ln in version.lines):
        raise CostingNotFound("Custo do produto", version_id)
    product = next((p for p in (version.snapshot or {}).get("products", []) if p.get("product_id") == product_id), None)
    line_ids = {ln.id for ln in version.lines if ln.product_id == product_id}
    source_ids = customs.cost_source_documents(db,
        [c.source_id for c in version.components if c.source_kind == "TAX_LINE"],
        [c.source_id for c in version.components if c.source_kind == "EXPENSE_LINE"])
    expenses = {e.id: e.document_id for e in db.query(CostingExpense).filter(CostingExpense.case_id == version.case_id).all()}
    components = []
    for c in version.components:
        refs = []
        can_documents = admin or "documents:read" in permissions
        if can_documents:
            if c.source_kind == "INVOICE":
                refs = documents.list_by_entity(db, "invoice", str(c.source_id))
            else:
                doc_id = expenses.get(c.source_id) if c.source_kind == "COSTING_EXPENSE" else source_ids.get((c.source_kind, c.source_id))
                doc = documents.get_document(db, doc_id) if doc_id else None
                refs = [doc] if doc else []
        accessible = [d for d in refs if admin or any(
            documents.entity_read_permission(link.entity_type) in permissions
            for link in documents.list_links_for_document(db, d.id))]
        allocations = [a for a in c.allocations if a.line_id in line_ids]
        components.append({"id": c.id, "type": c.component_type, "included": c.included,
            "product_brl": str(sum((a.amount_brl for a in allocations), Decimal(0))) if allocations else None,
            "process_brl": str(c.amount_brl) if c.amount_brl is not None else None,
            "source_kind": c.source_kind, "source_id": c.source_id,
            "documents": [{"id": d.id, "name": d.original_filename, "mime_type": d.mime_type} for d in accessible],
            "document_state": "available" if accessible else "absent_or_restricted"})
    case = db.get(CostingCase, version.case_id)
    return {"product_id": product_id, "case_id": version.case_id, "version_id": version.id,
        "number": version.version_number, "kind": version.kind, "status": version.status,
        "current_published_id": case.current_published_id, "partial_coverage": version.partial_coverage,
        "product": product, "fx": (version.snapshot or {}).get("fx", {}),
        "coverage": (version.snapshot or {}).get("coverage", {}), "components": components,
        "basis": "invoiced_or_shipped_lines_in_version", "tax_basis": "gross"}
