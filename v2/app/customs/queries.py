"""Customs queries — I5-1/I5-2."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.customs import repository as repo
from app.customs.errors import DoganaleNotFound, ProcessNotFound
from app.customs.models import CustomsDoganale, CustomsDoganaleVersion, ImportProcess
from app.logistics import public as logistics_public


def get_import_process(db: Session, process_id: int) -> ImportProcess:
    p = repo.get_process(db, process_id)
    if not p:
        raise ProcessNotFound(process_id)
    return p


def list_import_processes(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ImportProcess]:
    return repo.list_processes(db, status=status, limit=limit, offset=offset)


def invoice_item_residuals(db: Session, process_id: int) -> list[dict]:
    process = get_import_process(db, process_id)
    rows: list[dict] = []
    for link in process.invoices:
        inv = billing_public.get_invoice(db, link.invoice_id)
        for it in inv.items:
            allocated = repo.sum_allocated_invoice_item(db, it.id)
            qty = Decimal(str(it.quantity))
            rows.append(
                {
                    "invoice_id": inv.id,
                    "invoice_item_id": it.id,
                    "product_sku": it.sku_snapshot,
                    "quantity": str(qty),
                    "allocated_qty": str(allocated),
                    "residual_qty": str(qty - allocated),
                }
            )
    return rows


def shipment_item_residuals(db: Session, process_id: int) -> list[dict]:
    process = get_import_process(db, process_id)
    rows: list[dict] = []
    for link in process.shipments:
        shipment = logistics_public.get_shipment(db, link.shipment_id)
        for it in shipment.items:
            allocated = repo.sum_allocated_shipment_item(db, it.id)
            qty = Decimal(str(it.quantity))
            rows.append(
                {
                    "shipment_id": shipment.id,
                    "shipment_item_id": it.id,
                    "order_item_id": it.order_item_id,
                    "quantity": str(qty),
                    "allocated_qty": str(allocated),
                    "residual_qty": str(qty - allocated),
                }
            )
    return rows


def get_doganale_for_process(db: Session, process_id: int) -> CustomsDoganale | None:
    get_import_process(db, process_id)
    return repo.get_doganale_by_process(db, process_id)


def require_doganale_for_process(db: Session, process_id: int) -> CustomsDoganale:
    dog = get_doganale_for_process(db, process_id)
    if not dog:
        raise DoganaleNotFound(f"process:{process_id}")
    return dog


def list_doganale_versions(db: Session, process_id: int) -> list[CustomsDoganaleVersion]:
    dog = get_doganale_for_process(db, process_id)
    if not dog:
        return []
    return repo.list_versions(db, dog.id)


def get_current_doganale_version(db: Session, process_id: int) -> CustomsDoganaleVersion | None:
    dog = get_doganale_for_process(db, process_id)
    if not dog:
        return None
    return repo.get_current_version(db, dog.id)


def list_process_divergences(db: Session, process_id: int) -> list:
    get_import_process(db, process_id)
    return repo.list_divergences(db, process_id)


def list_process_provenances(db: Session, process_id: int) -> list:
    get_import_process(db, process_id)
    return repo.list_provenances(db, process_id)


def get_payee(db: Session, payee_id: int):
    from app.customs.errors import PayeeNotFound

    row = repo.get_payee(db, payee_id)
    if not row:
        raise PayeeNotFound(payee_id)
    return row


def list_payees(db: Session, *, limit: int = 100, offset: int = 0):
    return repo.list_payees(db, limit=limit, offset=offset)


def get_funding_request(db: Session, funding_id: int):
    from app.customs.errors import FundingNotFound

    fr = repo.get_funding(db, funding_id)
    if not fr:
        raise FundingNotFound(funding_id)
    return fr


def list_funding_requests(db: Session, process_id: int):
    get_import_process(db, process_id)
    return repo.list_fundings(db, process_id)


def get_nationalization(db: Session, nat_id: int):
    from app.customs.errors import NationalizationNotFound

    n = repo.get_nationalization(db, nat_id)
    if not n:
        raise NationalizationNotFound(nat_id)
    return n


def get_nationalization_item(db: Session, item_id: int):
    from app.customs.models import NationalizationItem

    return db.query(NationalizationItem).filter(NationalizationItem.id == item_id).first()


def list_nationalizations(db: Session, process_id: int):
    get_import_process(db, process_id)
    return repo.list_nationalizations(db, process_id)


def sum_nationalized_qty_by_product(db: Session, product_id: int) -> Decimal:
    return repo.sum_confirmed_nationalized_by_product(db, product_id)


def dec_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
