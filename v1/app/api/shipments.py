from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_LOGISTICS_READ, PERM_LOGISTICS_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import ImportationOrder, ModalChangeLog, ReasonCode, Shipment, ShipmentItem, User
from app.schemas_docs import (
    ModalChangeLogResponse,
    ModalChangeRequest,
    QuantitySummaryResponse,
    ShipmentCreate,
    ShipmentItemCreate,
    ShipmentItemDetailResponse,
    ShipmentItemResponse,
    ShipmentResponse,
    ShipmentUpdate,
)
from app.services.logistics import (
    ModalChangeError,
    QuantityExceededError,
    ShipmentUpdateError,
    add_shipment_item,
    change_shipment_modal,
    create_shipment,
    list_shipment_items,
    quantity_summary,
    update_shipment,
)

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("", response_model=list[ShipmentResponse])
def list_shipments(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_LOGISTICS_READ)),
):
    """Lista embarques de uma ordem — importation_id obrigatório (evita vazamento global)."""
    return (
        db.query(Shipment)
        .filter(Shipment.is_active.is_(True), Shipment.importation_id == importation_id)
        .order_by(Shipment.created_at)
        .all()
    )


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment_endpoint(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_LOGISTICS_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == payload.importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    return create_shipment(
        db,
        importation_id=payload.importation_id,
        shipment_number=payload.shipment_number,
        modal=payload.modal,
        user_id=current_user.id,
        bl_number=payload.bl_number,
        awb_number=payload.awb_number,
        container_number=payload.container_number,
        etd_planned=payload.etd_planned,
        eta_planned=payload.eta_planned,
        freight_amount=payload.freight_amount,
        freight_currency=payload.freight_currency,
    )


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_LOGISTICS_READ)),
):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Embarque não encontrado")
    return s


@router.get("/{shipment_id}/items", response_model=list[ShipmentItemDetailResponse])
def get_shipment_items(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_LOGISTICS_READ)),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id, Shipment.is_active.is_(True)).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Embarque não encontrado")
    return list_shipment_items(db, shipment_id)


@router.patch("/{shipment_id}", response_model=ShipmentResponse)
def patch_shipment(
    shipment_id: int,
    payload: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_LOGISTICS_WRITE)),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id, Shipment.is_active.is_(True)).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Embarque não encontrado")
    try:
        return update_shipment(
            db,
            shipment,
            user_id=current_user.id,
            **payload.model_dump(exclude_unset=True),
        )
    except ShipmentUpdateError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{shipment_id}/items", response_model=ShipmentItemResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    shipment_id: int,
    payload: ShipmentItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_LOGISTICS_WRITE)),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id, Shipment.is_active.is_(True)).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Embarque não encontrado")
    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
        reason_code_id = rc.id if rc else None
    try:
        return add_shipment_item(
            db,
            shipment,
            payload.importation_item_id,
            payload.quantity_shipped,
            user_id=current_user.id,
            reason_code_id=reason_code_id,
            justification=payload.justification,
        )
    except QuantityExceededError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{shipment_id}/change-modal", response_model=ShipmentResponse)
def change_modal(
    shipment_id: int,
    payload: ModalChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_LOGISTICS_WRITE)),
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id, Shipment.is_active.is_(True)).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Embarque não encontrado")
    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
        reason_code_id = rc.id if rc else None
    try:
        return change_shipment_modal(
            db,
            shipment,
            payload.new_modal,
            user_id=current_user.id,
            reason_code_id=reason_code_id,
            comment=payload.comment,
            estimated_cost_impact=payload.estimated_cost_impact,
            estimated_time_impact_days=payload.estimated_time_impact_days,
        )
    except ModalChangeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{shipment_id}/modal-history", response_model=list[ModalChangeLogResponse])
def modal_history(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_LOGISTICS_READ)),
):
    return (
        db.query(ModalChangeLog)
        .filter(ModalChangeLog.shipment_id == shipment_id)
        .order_by(ModalChangeLog.timestamp.desc())
        .all()
    )


@router.get("/importations/{importation_id}/quantity-summary", response_model=list[QuantitySummaryResponse])
def qty_summary(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_LOGISTICS_READ)),
):
    return quantity_summary(db, importation_id)
