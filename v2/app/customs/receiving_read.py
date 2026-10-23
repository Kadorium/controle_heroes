"""Minimal operational contract for Inventory; never exposes fiscal/financial facts."""
from sqlalchemy.orm import Session
from app.customs.models import ImportProcess, Nationalization, NationalizationItem


def receiving_sources(db: Session, item_ids: list[int] | None = None) -> list[dict]:
    query = db.query(NationalizationItem, Nationalization, ImportProcess).join(
        Nationalization, Nationalization.id == NationalizationItem.nationalization_id
    ).join(ImportProcess, ImportProcess.id == Nationalization.process_id)
    if item_ids is not None:
        query = query.filter(NationalizationItem.id.in_(item_ids))
    return [dict(item_id=i.id, nationalization_id=n.id, process_id=p.id,
                 process_code=p.code, process_reference=p.external_reference,
                 release_reference=n.reference, release_status=n.status,
                 process_cancelled=p.status == 'CANCELLED', product_id=i.product_id,
                 quantity=str(i.quantity))
            for i,n,p in query.order_by(NationalizationItem.id.desc()).all()]


def lock_receiving_sources(db: Session, item_ids: list[int]) -> None:
    """Same rows used by Customs state transitions; sorted locks avoid balance races.

    Lock Nationalization before ImportProcess, matching existing Customs commands.
    This contract locks only; it does not release or change Customs state.
    """
    ids = sorted({
        row[0] for row in db.query(NationalizationItem.nationalization_id).filter(
            NationalizationItem.id.in_(item_ids)).all()})
    nats = db.query(Nationalization).filter(Nationalization.id.in_(ids)).order_by(
        Nationalization.id).populate_existing().with_for_update().all()
    db.query(ImportProcess).filter(ImportProcess.id.in_({n.process_id for n in nats})).order_by(
        ImportProcess.id).populate_existing().with_for_update().all()
