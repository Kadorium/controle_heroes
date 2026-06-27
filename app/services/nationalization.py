from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import CustomsDocumentStatus
from app.models import (
    CustomsDocument,
    ImportationItem,
    Nationalization,
    NationalizationItem,
    QuantityDiscrepancy,
    StockEntry,
)
from app.services.auth import write_audit_log


class NationalizationError(Exception):
    pass


class StockEntryError(Exception):
    pass


def _nationalized_total(db: Session, importation_item_id: int, exclude_nat_item_id: int | None = None) -> int:
    q = (
        db.query(func.coalesce(func.sum(NationalizationItem.quantity_nationalized), 0))
        .join(Nationalization)
        .filter(NationalizationItem.importation_item_id == importation_item_id)
    )
    if exclude_nat_item_id:
        q = q.filter(NationalizationItem.id != exclude_nat_item_id)
    return int(q.scalar() or 0)


def _stock_total(db: Session, importation_item_id: int, exclude_entry_id: int | None = None) -> int:
    q = db.query(func.coalesce(func.sum(StockEntry.quantity_received), 0)).filter(
        StockEntry.importation_item_id == importation_item_id
    )
    if exclude_entry_id:
        q = q.filter(StockEntry.id != exclude_entry_id)
    return int(q.scalar() or 0)


def _nationalized_total_for_display(db: Session, importation_item_id: int) -> int | None:
    """None = nacionalização ainda não registrada; 0 = registro com quantidade zero."""
    has_row = (
        db.query(NationalizationItem.id)
        .join(Nationalization)
        .filter(NationalizationItem.importation_item_id == importation_item_id)
        .first()
    )
    if not has_row:
        return None
    return _nationalized_total(db, importation_item_id)


def _stock_total_for_display(db: Session, importation_item_id: int) -> int | None:
    """None = estoque ainda não recebido; 0 = entrada com quantidade zero."""
    has_row = (
        db.query(StockEntry.id)
        .filter(StockEntry.importation_item_id == importation_item_id)
        .first()
    )
    if not has_row:
        return None
    return _stock_total(db, importation_item_id)


def create_nationalization(
    db: Session,
    *,
    importation_id: int,
    customs_document_id: int,
    items: list[dict],
    user_id: int | None,
    event_date=None,
    notes: str | None = None,
) -> Nationalization:
    doc = db.query(CustomsDocument).filter(CustomsDocument.id == customs_document_id).first()
    if not doc or doc.importation_id != importation_id:
        raise NationalizationError("Documento aduaneiro não encontrado")
    if doc.status != CustomsDocumentStatus.OFFICIAL.value or not doc.is_valid:
        raise NationalizationError("Nacionalização exige DI/DUIMP oficial válida")

    nat = Nationalization(
        importation_id=importation_id,
        customs_document_id=customs_document_id,
        event_date=event_date,
        notes=notes,
        created_by_id=user_id,
    )
    db.add(nat)
    db.flush()

    for item_data in items:
        db.add(
            NationalizationItem(
                nationalization_id=nat.id,
                importation_item_id=item_data["importation_item_id"],
                quantity_nationalized=item_data["quantity_nationalized"],
            )
        )

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="nationalization",
        entity_id=str(nat.id),
        action="create",
    )
    db.commit()
    db.refresh(nat)
    return nat


def create_stock_entry(
    db: Session,
    *,
    nationalization_id: int,
    importation_item_id: int,
    quantity_received: int,
    user_id: int | None,
    unit_cost_approved: Decimal | None = None,
    landed_cost_version_id: int | None = None,
    reason_code_id: int | None = None,
    justification: str | None = None,
) -> StockEntry:
    nat = db.query(Nationalization).filter(Nationalization.id == nationalization_id).first()
    if not nat:
        raise StockEntryError("Nacionalização não encontrada")

    nat_item = (
        db.query(NationalizationItem)
        .filter(
            NationalizationItem.nationalization_id == nationalization_id,
            NationalizationItem.importation_item_id == importation_item_id,
        )
        .first()
    )
    if not nat_item:
        raise StockEntryError("Entrada em estoque depende de nacionalização do item")

    already_stock = _stock_total(db, importation_item_id)
    nat_total = _nationalized_total(db, importation_item_id)

    if already_stock + quantity_received > nat_total:
        if not reason_code_id or not (justification or "").strip():
            raise StockEntryError(
                "Quantidade em estoque excede nacionalizada — exige reason_code e justificativa"
            )

    entry = StockEntry(
        nationalization_id=nationalization_id,
        importation_item_id=importation_item_id,
        quantity_received=quantity_received,
        unit_cost_approved=unit_cost_approved,
        landed_cost_version_id=landed_cost_version_id,
        override_reason_code_id=reason_code_id,
        override_justification=justification,
        created_by_id=user_id,
    )
    db.add(entry)
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="stock_entry",
        entity_id="new",
        action="create",
        new_value=str(quantity_received),
    )
    db.commit()
    db.refresh(entry)
    return entry


def record_quantity_discrepancy(
    db: Session,
    *,
    importation_id: int,
    importation_item_id: int | None,
    stage_from: str,
    stage_to: str,
    expected_quantity: int | None,
    actual_quantity: int | None,
    reason: str | None,
    user_id: int | None,
) -> QuantityDiscrepancy:
    diff = None
    if expected_quantity is not None and actual_quantity is not None:
        diff = actual_quantity - expected_quantity
    disc = QuantityDiscrepancy(
        importation_id=importation_id,
        importation_item_id=importation_item_id,
        stage_from=stage_from,
        stage_to=stage_to,
        expected_quantity=expected_quantity,
        actual_quantity=actual_quantity,
        difference=diff,
        reason=reason,
        recorded_by_id=user_id,
    )
    db.add(disc)
    db.commit()
    db.refresh(disc)
    return disc


def quantity_chain(db: Session, importation_id: int) -> list[dict]:
    items = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    from app.services.logistics import _shipped_total_for_display
    from app.services.entreposto import entreposto_balance_for_display, entreposto_consumed_for_display

    result = []
    for item in items:
        ordered = item.quantity_ordered
        shipped = _shipped_total_for_display(db, item.id)
        nationalized = _nationalized_total_for_display(db, item.id)
        stocked = _stock_total_for_display(db, item.id)
        entreposto_bal = entreposto_balance_for_display(db, item.id)
        entreposto_cons = entreposto_consumed_for_display(db, item.id)
        result.append(
            {
                "importation_item_id": item.id,
                "quantity_ordered": ordered,
                "quantity_shipped": shipped,
                "quantity_nationalized": nationalized,
                "quantity_stocked": stocked,
                "quantity_entreposto_balance": entreposto_bal,
                "quantity_entreposto_consumed": entreposto_cons,
                "difference_ordered_stocked": (stocked - ordered)
                if ordered is not None and stocked is not None
                else None,
            }
        )
    return result
