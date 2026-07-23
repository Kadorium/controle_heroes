from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import EntrepostoMovementType
from app.models import EntrepostoMovement, ImportationItem
from app.services.auth import write_audit_log
from app.services.logistics import _shipped_total
from app.services.nationalization import _nationalized_total


class EntrepostoError(Exception):
    pass


def _receipt_total(db: Session, importation_item_id: int) -> int:
    return int(
        db.query(func.coalesce(func.sum(EntrepostoMovement.quantity), 0))
        .filter(
            EntrepostoMovement.importation_item_id == importation_item_id,
            EntrepostoMovement.movement_type == EntrepostoMovementType.RECEIPT.value,
            EntrepostoMovement.is_active.is_(True),
        )
        .scalar()
        or 0
    )


def _consumption_total(db: Session, importation_item_id: int) -> int:
    return int(
        db.query(func.coalesce(func.sum(EntrepostoMovement.quantity), 0))
        .filter(
            EntrepostoMovement.importation_item_id == importation_item_id,
            EntrepostoMovement.movement_type == EntrepostoMovementType.CONSUMPTION.value,
            EntrepostoMovement.is_active.is_(True),
        )
        .scalar()
        or 0
    )


def entreposto_balance(db: Session, importation_item_id: int) -> int:
    return _receipt_total(db, importation_item_id) - _consumption_total(db, importation_item_id)


def _has_entreposto_movement(db: Session, importation_item_id: int) -> bool:
    return (
        db.query(EntrepostoMovement.id)
        .filter(
            EntrepostoMovement.importation_item_id == importation_item_id,
            EntrepostoMovement.is_active.is_(True),
        )
        .first()
        is not None
    )


def entreposto_balance_for_display(db: Session, importation_item_id: int) -> int | None:
    if not _has_entreposto_movement(db, importation_item_id):
        return None
    return entreposto_balance(db, importation_item_id)


def entreposto_consumed_for_display(db: Session, importation_item_id: int) -> int | None:
    if not _has_entreposto_movement(db, importation_item_id):
        return None
    consumed = _consumption_total(db, importation_item_id)
    if consumed == 0:
        has_consumption = (
            db.query(EntrepostoMovement.id)
            .filter(
                EntrepostoMovement.importation_item_id == importation_item_id,
                EntrepostoMovement.movement_type == EntrepostoMovementType.CONSUMPTION.value,
                EntrepostoMovement.is_active.is_(True),
            )
            .first()
        )
        if not has_consumption:
            return None
    return consumed


def create_entreposto_movement(
    db: Session,
    *,
    importation_id: int,
    importation_item_id: int,
    movement_type: str,
    quantity: int,
    user_id: int | None,
    event_date: date | None = None,
    shipment_id: int | None = None,
    notes: str | None = None,
    reason_code_id: int | None = None,
) -> EntrepostoMovement:
    if quantity is None or quantity <= 0:
        raise EntrepostoError("Quantidade deve ser positiva")

    imp_item = (
        db.query(ImportationItem)
        .filter(
            ImportationItem.id == importation_item_id,
            ImportationItem.importation_id == importation_id,
            ImportationItem.is_active.is_(True),
        )
        .first()
    )
    if not imp_item:
        raise EntrepostoError("Item de importação não encontrado")

    shipped = _shipped_total(db, importation_item_id)
    if shipped <= 0:
        raise EntrepostoError("Entreposto exige quantidade embarcada")

    nationalized = _nationalized_total(db, importation_item_id)
    balance = entreposto_balance(db, importation_item_id)
    available_for_receipt = shipped - nationalized - balance

    if movement_type == EntrepostoMovementType.RECEIPT.value:
        if quantity > available_for_receipt:
            raise EntrepostoError(
                f"Entrada no entreposto ({quantity}) excede disponível "
                f"(embarcado {shipped} − nacionalizado {nationalized} − saldo {balance})"
            )
    elif movement_type == EntrepostoMovementType.CONSUMPTION.value:
        if quantity > balance:
            if not reason_code_id or not (notes or "").strip():
                raise EntrepostoError(
                    f"Consumo ({quantity}) excede saldo entreposto ({balance}) "
                    "— exige reason_code e justificativa"
                )
    else:
        raise EntrepostoError(f"Tipo de movimento inválido: {movement_type}")

    movement = EntrepostoMovement(
        importation_id=importation_id,
        importation_item_id=importation_item_id,
        movement_type=movement_type,
        quantity=quantity,
        event_date=event_date,
        shipment_id=shipment_id,
        notes=notes,
        reason_code_id=reason_code_id,
        created_by_id=user_id,
    )
    db.add(movement)
    db.flush()
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="entreposto_movement",
        entity_id=str(movement.id),
        action="create",
        new_value=f"{movement_type}:{quantity}",
    )
    db.commit()
    db.refresh(movement)
    return movement


def list_entreposto_movements(db: Session, importation_id: int) -> list[EntrepostoMovement]:
    return (
        db.query(EntrepostoMovement)
        .filter(EntrepostoMovement.importation_id == importation_id, EntrepostoMovement.is_active.is_(True))
        .order_by(EntrepostoMovement.created_at.desc())
        .all()
    )
