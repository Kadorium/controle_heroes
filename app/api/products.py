from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_IMPORTATION_READ, PERM_IMPORTATION_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import Product, User
from app.schemas_import import CancelRequest, ProductCreate, ProductResponse, ProductUpdate
from app.services.auth import write_audit_log

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
    include_inactive: bool = False,
):
    q = db.query(Product)
    if not include_inactive:
        q = q.filter(Product.is_active.is_(True))
    return q.order_by(Product.sku_code).all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    if db.query(Product).filter(Product.sku_code == payload.sku_code).first():
        raise HTTPException(status_code=409, detail="SKU já existe")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="create",
    )
    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_IMPORTATION_READ)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="update",
    )
    return product


@router.post("/{product_id}/cancel", response_model=ProductResponse)
def cancel_product(
    product_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_IMPORTATION_WRITE)),
):
    product = db.query(Product).filter(Product.id == product_id, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    product.is_active = False
    product.cancelled_at = datetime.now(timezone.utc)
    product.cancelled_by_id = current_user.id
    product.cancellation_reason = payload.reason
    write_audit_log(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=str(product.id),
        action="cancel",
        justification=payload.reason,
    )
    db.commit()
    db.refresh(product)
    return product
