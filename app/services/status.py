from sqlalchemy.orm import Session

from app.core.enums import IMPORTATION_TRANSITIONS, TRANSITION_REQUIRED_DOCUMENTS
from app.models import DocumentAttachment, ImportationOrder, StatusTransitionLog
from app.services.auth import write_audit_log


class InvalidStatusTransition(Exception):
    def __init__(self, current: str, target: str, detail: str | None = None):
        self.current = current
        self.target = target
        self.detail = detail
        msg = detail or f"Transição inválida: {current} -> {target}"
        super().__init__(msg)


def validate_transition(current_status: str, new_status: str) -> None:
    allowed = IMPORTATION_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise InvalidStatusTransition(current_status, new_status)


def check_required_documents(
    db: Session,
    importation_id: int,
    new_status: str,
) -> None:
    required = TRANSITION_REQUIRED_DOCUMENTS.get(new_status, [])
    if not required:
        return
    for doc_type in required:
        found = (
            db.query(DocumentAttachment)
            .filter(
                DocumentAttachment.entity_type == "importation_order",
                DocumentAttachment.entity_id == str(importation_id),
                DocumentAttachment.document_type == doc_type,
                DocumentAttachment.is_current_version.is_(True),
            )
            .first()
        )
        if not found:
            raise InvalidStatusTransition(
                "",
                new_status,
                detail=f"Documento obrigatório ausente para transição: {doc_type}",
            )


def transition_importation_status(
    db: Session,
    importation: ImportationOrder,
    new_status: str,
    *,
    user_id: int | None,
    reason: str | None = None,
) -> ImportationOrder:
    old_status = importation.current_status
    validate_transition(old_status, new_status)
    check_required_documents(db, importation.id, new_status)

    importation.current_status = new_status
    db.add(
        StatusTransitionLog(
            importation_id=str(importation.id),
            from_status=old_status,
            to_status=new_status,
            action="status_transition",
            user_id=user_id,
            comment=reason,
        )
    )
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="importation_order",
        entity_id=str(importation.id),
        action="status_transition",
        field_changed="current_status",
        old_value=old_status,
        new_value=new_status,
        justification=reason,
    )
    db.commit()
    db.refresh(importation)
    return importation
