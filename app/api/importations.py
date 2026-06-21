from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import ImportationItem, ImportationOrder, Supplier, User
from app.schemas_import import (
    CancelRequest,
    ImportationCreate,
    ImportationItemCreate,
    ImportationItemResponse,
    ImportationResponse,
    StatusTransitionRequest,
)
from app.schemas_order_central import OrderCentralResponse, OrderQueueResponse
from app.services.auth import write_audit_log
from app.services.importation_guard import ImportationLockedError, assert_importation_editable
from app.services.order_central import build_order_central, build_order_queue
from app.services.status import InvalidStatusTransition, transition_importation_status

router = APIRouter(prefix="/importations", tags=["importations"])


@router.get("", response_model=list[ImportationResponse])
def list_importations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    include_inactive: bool = False,
):
    q = db.query(ImportationOrder)
    if not include_inactive:
        q = q.filter(ImportationOrder.is_active.is_(True))
    return q.order_by(ImportationOrder.created_at.desc()).all()


@router.get("/order-queue", response_model=OrderQueueResponse)
def get_order_queue(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    limit: int = 100,
):
    return build_order_queue(db, limit=limit)


@router.post("", response_model=ImportationResponse, status_code=status.HTTP_201_CREATED)
def create_importation(
    payload: ImportationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.is_active.is_(True)).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    if db.query(ImportationOrder).filter(ImportationOrder.po_number == payload.po_number).first():
        raise HTTPException(status_code=409, detail="PO já existe")

    imp = ImportationOrder(
        po_number=payload.po_number,
        supplier_id=payload.supplier_id,
        currency=payload.currency,
        incoterm=payload.incoterm,
        estimated_total=payload.estimated_total,
        current_status="PO_CREATED",
        created_by_id=current_user.id,
    )
    db.add(imp)
    db.flush()

    for item_data in payload.items:
        db.add(ImportationItem(importation_id=imp.id, **item_data.model_dump()))

    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="importation_order",
        entity_id=str(imp.id),
        action="create",
    )
    db.commit()
    db.refresh(imp)
    return imp


@router.get("/{importation_id}", response_model=ImportationResponse)
def get_importation(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    return imp


@router.get("/{importation_id}/order-central", response_model=OrderCentralResponse)
def get_order_central(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    try:
        return build_order_central(db, importation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{importation_id}/items", response_model=list[ImportationItemResponse])
def list_items(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    return (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )


@router.post("/{importation_id}/items", response_model=ImportationItemResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    importation_id: int,
    payload: ImportationItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    item = ImportationItem(importation_id=importation_id, **payload.model_dump())
    db.add(item)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="importation_item",
        entity_id=str(importation_id),
        action="add_item",
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/{importation_id}/transition", response_model=ImportationResponse)
def transition_status(
    importation_id: int,
    payload: StatusTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    try:
        assert_importation_editable(imp)
    except ImportationLockedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    try:
        return transition_importation_status(
            db, imp, payload.new_status, user_id=current_user.id, reason=payload.reason
        )
    except InvalidStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{importation_id}/cancel", response_model=ImportationResponse)
def cancel_importation(
    importation_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    imp = db.query(ImportationOrder).filter(
        ImportationOrder.id == importation_id, ImportationOrder.is_active.is_(True)
    ).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    imp.is_active = False
    imp.cancelled_at = datetime.now(timezone.utc)
    imp.cancelled_by_id = current_user.id
    imp.cancellation_reason = payload.reason
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="importation_order",
        entity_id=str(imp.id),
        action="cancel",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(imp)
    return imp
