from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_STOCK_READ, PERM_STOCK_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import Nationalization, ReasonCode, User
from app.schemas_phase789 import (
    NationalizationCreate,
    NationalizationResponse,
    QuantityChainResponse,
    QuantityDiscrepancyCreate,
    StockEntryCreate,
    StockEntryResponse,
)
from app.services.nationalization import (
    NationalizationError,
    StockEntryError,
    create_nationalization,
    create_stock_entry,
    quantity_chain,
    record_quantity_discrepancy,
)

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/nationalizations", response_model=NationalizationResponse, status_code=status.HTTP_201_CREATED)
def nationalize(
    payload: NationalizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_STOCK_WRITE)),
):
    try:
        return create_nationalization(
            db,
            importation_id=payload.importation_id,
            customs_document_id=payload.customs_document_id,
            items=[i.model_dump() for i in payload.items],
            user_id=current_user.id,
            event_date=payload.event_date,
            notes=payload.notes,
        )
    except NationalizationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/nationalizations", response_model=list[NationalizationResponse])
def list_nationalizations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_STOCK_READ)),
    importation_id: int | None = None,
):
    q = db.query(Nationalization)
    if importation_id is not None:
        q = q.filter(Nationalization.importation_id == importation_id)
    return q.order_by(Nationalization.created_at.desc()).all()


@router.post("/entries", response_model=StockEntryResponse, status_code=status.HTTP_201_CREATED)
def stock_entry(
    payload: StockEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_STOCK_WRITE)),
):
    reason_code_id = None
    if payload.reason_code:
        rc = db.query(ReasonCode).filter(ReasonCode.code == payload.reason_code).first()
        reason_code_id = rc.id if rc else None
    try:
        return create_stock_entry(
            db,
            nationalization_id=payload.nationalization_id,
            importation_item_id=payload.importation_item_id,
            quantity_received=payload.quantity_received,
            user_id=current_user.id,
            unit_cost_approved=payload.unit_cost_approved,
            landed_cost_version_id=payload.landed_cost_version_id,
            reason_code_id=reason_code_id,
            justification=payload.justification,
        )
    except StockEntryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/importations/{importation_id}/quantity-chain", response_model=list[QuantityChainResponse])
def get_quantity_chain(
    importation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_STOCK_READ)),
):
    return quantity_chain(db, importation_id)


@router.post("/discrepancies", status_code=status.HTTP_201_CREATED)
def record_discrepancy(
    payload: QuantityDiscrepancyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_STOCK_WRITE)),
):
    disc = record_quantity_discrepancy(
        db,
        importation_id=payload.importation_id,
        importation_item_id=payload.importation_item_id,
        stage_from=payload.stage_from,
        stage_to=payload.stage_to,
        expected_quantity=payload.expected_quantity,
        actual_quantity=payload.actual_quantity,
        reason=payload.reason,
        user_id=current_user.id,
    )
    return {"id": disc.id, "difference": disc.difference}
