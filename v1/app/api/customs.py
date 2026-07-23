from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import PERM_CUSTOMS_READ, PERM_CUSTOMS_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import CustomsDocument, Tax, User
from app.schemas_phase789 import (
    CustomsDocumentApprove,
    CustomsDocumentCreate,
    CustomsDocumentResponse,
    TaxCreate,
    TaxResponse,
)
from app.services.customs import CustomsValidationError, approve_customs_document, create_customs_document, create_tax

router = APIRouter(prefix="/customs", tags=["customs"])


@router.get("/documents", response_model=list[CustomsDocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_CUSTOMS_READ)),
    importation_id: int | None = None,
):
    q = db.query(CustomsDocument).filter(CustomsDocument.is_active.is_(True))
    if importation_id is not None:
        q = q.filter(CustomsDocument.importation_id == importation_id)
    return q.order_by(CustomsDocument.created_at.desc()).all()


@router.post("/documents", response_model=CustomsDocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: CustomsDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CUSTOMS_WRITE)),
):
    return create_customs_document(
        db,
        importation_id=payload.importation_id,
        document_type=payload.document_type,
        document_number=payload.document_number,
        document_data_json=payload.document_data_json,
        user_id=current_user.id,
        attachment_id=payload.attachment_id,
    )


@router.post("/documents/{document_id}/approve", response_model=CustomsDocumentResponse)
def approve_document(
    document_id: int,
    payload: CustomsDocumentApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CUSTOMS_WRITE)),
):
    doc = db.query(CustomsDocument).filter(CustomsDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return approve_customs_document(db, doc, payload.official_data_json, user_id=current_user.id)


@router.get("/taxes", response_model=list[TaxResponse])
def list_taxes(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_CUSTOMS_READ)),
    importation_id: int | None = None,
):
    q = db.query(Tax).filter(Tax.is_active.is_(True))
    if importation_id is not None:
        q = q.filter(Tax.importation_id == importation_id)
    return q.all()


@router.post("/taxes", response_model=TaxResponse, status_code=status.HTTP_201_CREATED)
def create_tax_endpoint(
    payload: TaxCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CUSTOMS_WRITE)),
):
    try:
        return create_tax(
            db,
            importation_id=payload.importation_id,
            customs_document_id=payload.customs_document_id,
            tax_type=payload.tax_type,
            amount=payload.amount,
            source_document_attachment_id=payload.source_document_attachment_id,
            user_id=current_user.id,
            currency=payload.currency,
            notes=payload.notes,
        )
    except CustomsValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
