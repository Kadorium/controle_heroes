from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import CustomsDocumentStatus, CustomsDocumentType
from app.models import CustomsDocument, DocumentAttachment, Expense, Tax
from app.services.auth import write_audit_log


class CustomsValidationError(Exception):
    pass


def create_customs_document(
    db: Session,
    *,
    importation_id: int,
    document_type: str,
    document_number: str,
    document_data_json: dict | None,
    user_id: int | None,
    attachment_id: int | None = None,
) -> CustomsDocument:
    doc = CustomsDocument(
        importation_id=importation_id,
        document_type=document_type,
        document_number=document_number,
        document_data_json=document_data_json,
        status=CustomsDocumentStatus.STAGING.value,
        attachment_id=attachment_id,
        created_by_id=user_id,
    )
    db.add(doc)
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="customs_document",
        entity_id="new",
        action="create_staging",
        new_value=document_number,
    )
    db.commit()
    db.refresh(doc)
    return doc


def approve_customs_document(
    db: Session,
    doc: CustomsDocument,
    official_data_json: dict,
    *,
    user_id: int | None,
) -> CustomsDocument:
    doc.official_data_json = official_data_json
    doc.status = CustomsDocumentStatus.OFFICIAL.value
    doc.is_valid = True
    doc.approved_at = datetime.now(timezone.utc)
    doc.approved_by_id = user_id
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="customs_document",
        entity_id=str(doc.id),
        action="approve_official",
    )
    db.commit()
    db.refresh(doc)
    return doc


def create_tax(
    db: Session,
    *,
    importation_id: int,
    customs_document_id: int,
    tax_type: str,
    amount: Decimal,
    source_document_attachment_id: int,
    user_id: int | None,
    currency: str = "BRL",
    notes: str | None = None,
) -> Tax:
    if not source_document_attachment_id:
        raise CustomsValidationError("Imposto exige documento comprobatório")

    doc = db.query(CustomsDocument).filter(CustomsDocument.id == customs_document_id).first()
    if not doc or doc.importation_id != importation_id:
        raise CustomsValidationError("Documento aduaneiro inválido")

    attachment = db.query(DocumentAttachment).filter(
        DocumentAttachment.id == source_document_attachment_id
    ).first()
    if not attachment:
        raise CustomsValidationError("Anexo comprobatório não encontrado")

    tax = Tax(
        importation_id=importation_id,
        customs_document_id=customs_document_id,
        tax_type=tax_type,
        amount=amount,
        currency=currency,
        source_document_attachment_id=source_document_attachment_id,
        notes=notes,
        created_by_id=user_id,
    )
    db.add(tax)
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="tax",
        entity_id="new",
        action="create",
        new_value=str(amount),
    )
    db.commit()
    db.refresh(tax)
    return tax


def validate_customs_agent_expense(expense: Expense) -> None:
    if expense.expense_type != "CUSTOMS_AGENT":
        return
    if not (expense.source_document_ref or "").strip():
        raise CustomsValidationError("Despesa de despachante exige evidência documental")
