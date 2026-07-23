from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ImportationItem, ModalChangeLog, ReasonCode, Shipment, ShipmentItem
from app.services.auth import write_audit_log


class QuantityExceededError(Exception):
    pass


class ModalChangeError(Exception):
    pass


class ShipmentUpdateError(Exception):
    pass


_VALID_SHIPMENT_STATUSES = frozenset(
    {"PLANNED", "BOOKED", "SHIPPED", "IN_TRANSIT", "ARRIVED", "DELIVERED", "CANCELLED"}
)

_STATUS_ORDER = {
    "PLANNED": 0,
    "BOOKED": 1,
    "SHIPPED": 2,
    "IN_TRANSIT": 3,
    "ARRIVED": 4,
    "DELIVERED": 5,
    "CANCELLED": 99,
}


def _shipped_total(db: Session, importation_item_id: int, exclude_shipment_item_id: int | None = None) -> int:
    q = db.query(func.coalesce(func.sum(ShipmentItem.quantity_shipped), 0)).filter(
        ShipmentItem.importation_item_id == importation_item_id,
        ShipmentItem.is_active.is_(True),
    )
    if exclude_shipment_item_id:
        q = q.filter(ShipmentItem.id != exclude_shipment_item_id)
    return int(q.scalar() or 0)


def _shipped_total_for_display(db: Session, importation_item_id: int) -> int | None:
    """None = etapa ainda não iniciada; 0 = embarque registrado com quantidade zero."""
    has_row = (
        db.query(ShipmentItem.id)
        .filter(
            ShipmentItem.importation_item_id == importation_item_id,
            ShipmentItem.is_active.is_(True),
        )
        .first()
    )
    if not has_row:
        return None
    return _shipped_total(db, importation_item_id)


def validate_shipment_quantity(
    db: Session,
    importation_item: ImportationItem,
    quantity_shipped: int | None,
    *,
    exclude_shipment_item_id: int | None = None,
    reason_code_id: int | None = None,
    justification: str | None = None,
) -> None:
    if quantity_shipped is None:
        return
    ordered = importation_item.quantity_ordered
    if ordered is None:
        return
    already = _shipped_total(db, importation_item.id, exclude_shipment_item_id)
    if already + quantity_shipped > ordered:
        if not reason_code_id or not (justification or "").strip():
            raise QuantityExceededError(
                f"Quantidade embarcada ({already + quantity_shipped}) excede pedida ({ordered}) "
                "sem reason_code e justificativa"
            )


def create_shipment(
    db: Session,
    *,
    importation_id: int,
    shipment_number: str,
    modal: str,
    user_id: int | None,
    **kwargs,
) -> Shipment:
    shipment = Shipment(
        importation_id=importation_id,
        shipment_number=shipment_number,
        modal=modal,
        created_by_id=user_id,
        **kwargs,
    )
    db.add(shipment)
    db.flush()
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="shipment",
        entity_id=str(shipment.id),
        action="create",
        new_value=modal,
    )
    db.commit()
    db.refresh(shipment)
    return shipment


def add_shipment_item(
    db: Session,
    shipment: Shipment,
    importation_item_id: int,
    quantity_shipped: int | None,
    *,
    user_id: int | None,
    reason_code_id: int | None = None,
    justification: str | None = None,
) -> ShipmentItem:
    imp_item = db.query(ImportationItem).filter(ImportationItem.id == importation_item_id).first()
    if not imp_item:
        raise ValueError("Item de importação não encontrado")
    validate_shipment_quantity(
        db,
        imp_item,
        quantity_shipped,
        reason_code_id=reason_code_id,
        justification=justification,
    )
    item = ShipmentItem(
        shipment_id=shipment.id,
        importation_item_id=importation_item_id,
        quantity_shipped=quantity_shipped,
        quantity_override_reason_code_id=reason_code_id,
        quantity_override_justification=justification,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def change_shipment_modal(
    db: Session,
    shipment: Shipment,
    new_modal: str,
    *,
    user_id: int | None,
    reason_code_id: int | None = None,
    comment: str | None = None,
    estimated_cost_impact: Decimal | None = None,
    estimated_time_impact_days: int | None = None,
) -> Shipment:
    if new_modal == shipment.modal:
        raise ModalChangeError("Modal já é o informado")
    if not reason_code_id and not (comment or "").strip():
        raise ModalChangeError("Alteração de modal exige reason_code ou comentário")

    old_modal = shipment.modal
    shipment.modal_previous = old_modal
    shipment.modal = new_modal

    db.add(
        ModalChangeLog(
            shipment_id=shipment.id,
            from_modal=old_modal,
            to_modal=new_modal,
            reason_code_id=reason_code_id,
            comment=comment,
            user_id=user_id,
            estimated_cost_impact=estimated_cost_impact,
            estimated_time_impact_days=estimated_time_impact_days,
        )
    )
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="shipment",
        entity_id=str(shipment.id),
        action="modal_change",
        field_changed="modal",
        old_value=old_modal,
        new_value=new_modal,
        reason_code_id=reason_code_id,
        justification=comment,
    )

    from app.core.enums import AllocationMethod, LandedCostVersionType
    from app.models import LandedCostVersion
    from app.services.landed_cost import create_landed_cost_version

    has_lc = (
        db.query(LandedCostVersion)
        .filter(LandedCostVersion.importation_id == shipment.importation_id)
        .first()
    )
    if has_lc:
        create_landed_cost_version(
            db,
            importation_id=shipment.importation_id,
            version_type=LandedCostVersionType.REVISED.value,
            allocation_method=AllocationMethod.VALUE.value,
            user_id=user_id,
            trigger_event="MODAL_CHANGE",
            trigger_notes=f"{old_modal} -> {new_modal}",
        )
    else:
        db.commit()
        db.refresh(shipment)
        return shipment

    db.refresh(shipment)
    return shipment


def list_shipment_items(db: Session, shipment_id: int) -> list[dict]:
    rows = (
        db.query(ShipmentItem, ImportationItem)
        .join(ImportationItem, ShipmentItem.importation_item_id == ImportationItem.id)
        .filter(ShipmentItem.shipment_id == shipment_id, ShipmentItem.is_active.is_(True))
        .all()
    )
    return [
        {
            "id": si.id,
            "shipment_id": si.shipment_id,
            "importation_item_id": si.importation_item_id,
            "quantity_shipped": si.quantity_shipped,
            "supplier_sku": ii.supplier_sku,
            "description": ii.description,
        }
        for si, ii in rows
    ]


def update_shipment(
    db: Session,
    shipment: Shipment,
    *,
    user_id: int | None,
    **fields,
) -> Shipment:
    changes: dict[str, tuple[str | None, str | None]] = {}
    if "status" in fields and fields["status"] is not None:
        new_status = fields["status"]
        if new_status not in _VALID_SHIPMENT_STATUSES:
            raise ShipmentUpdateError(f"Status inválido: {new_status}")
        old_status = shipment.status
        if old_status != new_status and old_status != "CANCELLED":
            old_ord = _STATUS_ORDER.get(old_status, 0)
            new_ord = _STATUS_ORDER.get(new_status, 0)
            if new_status != "CANCELLED" and new_ord < old_ord:
                raise ShipmentUpdateError(
                    f"Transição de status inválida: {old_status} → {new_status}"
                )
        if old_status != new_status:
            changes["status"] = (old_status, new_status)
            shipment.status = new_status

    scalar_fields = (
        "bl_number",
        "awb_number",
        "container_number",
        "etd_planned",
        "eta_planned",
        "etd_actual",
        "eta_actual",
        "freight_amount",
        "freight_currency",
    )
    for key in scalar_fields:
        if key not in fields:
            continue
        new_val = fields[key]
        old_val = getattr(shipment, key)
        if old_val != new_val:
            changes[key] = (
                str(old_val) if old_val is not None else None,
                str(new_val) if new_val is not None else None,
            )
            setattr(shipment, key, new_val)

    if not changes:
        return shipment

    for field, (old_v, new_v) in changes.items():
        write_audit_log(
            db,
            user_id=user_id,
            entity_type="shipment",
            entity_id=str(shipment.id),
            action="update",
            field_changed=field,
            old_value=old_v,
            new_value=new_v,
        )
    db.commit()
    db.refresh(shipment)
    return shipment


def quantity_summary(db: Session, importation_id: int) -> list[dict]:
    items = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    result = []
    for item in items:
        shipped = _shipped_total(db, item.id)
        result.append(
            {
                "importation_item_id": item.id,
                "quantity_ordered": item.quantity_ordered,
                "quantity_shipped": shipped,
                "quantity_remaining": (
                    (item.quantity_ordered - shipped) if item.quantity_ordered is not None else None
                ),
            }
        )
    return result
