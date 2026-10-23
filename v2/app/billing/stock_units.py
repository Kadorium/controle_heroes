from app.billing.models import InvoiceItem

def stock_invoice_units(db, item_ids):
    """Persisted invoice units for origin valuation; no SKU-based inference."""
    return {row.id:row.unit for row in db.query(InvoiceItem).filter(InvoiceItem.id.in_(item_ids)).all()} if item_ids else {}
