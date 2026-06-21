from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import Supplier, User
from app.schemas_import import CancelRequest, SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.auth import write_audit_log

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    include_inactive: bool = False,
):
    q = db.query(Supplier)
    if not include_inactive:
        q = q.filter(Supplier.is_active.is_(True))
    return q.order_by(Supplier.name).all()


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=str(supplier.id),
        action="create",
    )
    return supplier


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return supplier


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.is_active.is_(True)).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=str(supplier.id),
        action="update",
    )
    return supplier


@router.post("/{supplier_id}/cancel", response_model=SupplierResponse)
def cancel_supplier(
    supplier_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.is_active.is_(True)).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    supplier.is_active = False
    supplier.cancelled_at = datetime.now(timezone.utc)
    supplier.cancelled_by_id = current_user.id
    supplier.cancellation_reason = payload.reason
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=str(supplier.id),
        action="cancel",
        field_changed="is_active",
        old_value="True",
        new_value="False",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(supplier)
    return supplier
