"""Minimal owner read contracts for Costing; never prepare a process."""
from sqlalchemy.orm import Session
from app.customs.models import ImportProcess, CustomsTaxLine, CustomsExpenseLine, CustomsFundingRequest


def cost_process_labels(db: Session, ids: list[int]) -> dict:
    return {p.id: {"code": p.code, "reference": p.external_reference} for p in
            db.query(ImportProcess).filter(ImportProcess.id.in_(ids)).all()}


def cost_source_documents(db: Session, tax_ids: list[int], expense_ids: list[int]) -> dict:
    result = {}
    for model, ids, kind in ((CustomsTaxLine, tax_ids, "TAX_LINE"), (CustomsExpenseLine, expense_ids, "EXPENSE_LINE")):
        if ids:
            for line_id, document_id in db.query(model.id, CustomsFundingRequest.document_id).join(
                CustomsFundingRequest, CustomsFundingRequest.id == model.funding_request_id
            ).filter(model.id.in_(ids)).all():
                result[(kind, line_id)] = document_id
    return result
