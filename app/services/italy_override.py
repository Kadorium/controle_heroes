"""Override controlado de campos Itália — exige motivo + anexo + AuditLog."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import DocumentAttachment, ImportationOrder, Invoice, InvoiceItem
from app.services.auth import write_audit_log
from app.core.parse import optional_decimal, optional_int

ALLOWED_FIELDS: dict[str, set[str]] = {
    "invoice": {"amount", "invoice_number"},
    "invoice_item": {"quantity", "unit_price", "amount"},
}


class ItalyOverrideError(ValueError):
    pass


def apply_italy_field_override(
    db: Session,
    *,
    importation_id: int,
    entity_type: str,
    entity_id: int,
    field_name: str,
    new_value: str,
    reason: str,
    attachment_id: int,
    user_id: int | None,
) -> dict:
    if not reason or not reason.strip():
        raise ItalyOverrideError("Motivo obrigatório para override de campo Itália")
    allowed = ALLOWED_FIELDS.get(entity_type)
    if not allowed or field_name not in allowed:
        raise ItalyOverrideError(f"Campo não permitido para override: {entity_type}.{field_name}")

    att = (
        db.query(DocumentAttachment)
        .filter(
            DocumentAttachment.id == attachment_id,
            DocumentAttachment.is_current_version.is_(True),
        )
        .first()
    )
    if not att:
        raise ItalyOverrideError("Anexo obrigatório — faça upload antes do override")
    if att.entity_type == "importation_order" and att.entity_id != str(importation_id):
        raise ItalyOverrideError("Anexo não pertence a esta ordem")

    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ItalyOverrideError("Ordem não encontrada")

    old_value: str | None = None
    if entity_type == "invoice":
        inv = (
            db.query(Invoice)
            .filter(Invoice.id == entity_id, Invoice.importation_id == importation_id, Invoice.is_active.is_(True))
            .first()
        )
        if not inv:
            raise ItalyOverrideError("Fatura não encontrada")
        old_value = str(getattr(inv, field_name))
        if field_name == "amount":
            setattr(inv, field_name, optional_decimal(new_value))
        else:
            setattr(inv, field_name, new_value)
    elif entity_type == "invoice_item":
        ii = (
            db.query(InvoiceItem)
            .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
            .filter(
                InvoiceItem.id == entity_id,
                Invoice.importation_id == importation_id,
                InvoiceItem.is_active.is_(True),
            )
            .first()
        )
        if not ii:
            raise ItalyOverrideError("Item de fatura não encontrado")
        old_value = str(getattr(ii, field_name))
        if field_name == "quantity":
            setattr(ii, field_name, optional_int(new_value))
        elif field_name in ("unit_price", "amount"):
            setattr(ii, field_name, optional_decimal(new_value))
        else:
            setattr(ii, field_name, new_value)
    else:
        raise ItalyOverrideError("Tipo de entidade inválido")

    write_audit_log(
        db,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action="italy_field_override",
        field_changed=field_name,
        old_value=old_value,
        new_value=new_value,
        justification=reason,
        attachment_id=str(attachment_id),
    )
    db.commit()
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field_name": field_name,
        "old_value": old_value,
        "new_value": new_value,
        "attachment_id": attachment_id,
    }
