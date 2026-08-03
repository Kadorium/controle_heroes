"""Customs repository — I5-1/I5-2/I5-3A."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.customs.models import (
    CustomsDivergence,
    CustomsDoganale,
    CustomsDoganaleVersion,
    CustomsFundingRequest,
    CustomsPayee,
    CustomsProvenance,
    ImportProcess,
    ImportProcessInvoice,
    ImportProcessInvoiceItem,
    ImportProcessShipment,
    ImportProcessShipmentItem,
)


def get_process(db: Session, process_id: int) -> ImportProcess | None:
    return (
        db.query(ImportProcess)
        .options(
            joinedload(ImportProcess.invoices),
            joinedload(ImportProcess.invoice_items),
            joinedload(ImportProcess.shipments),
            joinedload(ImportProcess.shipment_items),
            joinedload(ImportProcess.doganale).joinedload(CustomsDoganale.versions).joinedload(
                CustomsDoganaleVersion.lines
            ),
            joinedload(ImportProcess.divergences),
        )
        .filter(ImportProcess.id == process_id)
        .first()
    )


def get_process_for_update(db: Session, process_id: int) -> ImportProcess | None:
    return (
        db.query(ImportProcess)
        .filter(ImportProcess.id == process_id)
        .with_for_update()
        .first()
    )


def get_by_code(db: Session, code: str) -> ImportProcess | None:
    return db.query(ImportProcess).filter(ImportProcess.code == code).first()


def list_processes(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ImportProcess]:
    q = db.query(ImportProcess).order_by(ImportProcess.id.desc())
    if status:
        q = q.filter(ImportProcess.status == status)
    return q.offset(offset).limit(limit).all()


def find_invoice_link(db: Session, invoice_id: int) -> ImportProcessInvoice | None:
    return (
        db.query(ImportProcessInvoice)
        .filter(ImportProcessInvoice.invoice_id == invoice_id)
        .first()
    )


def find_invoice_link_on_process(
    db: Session, process_id: int, invoice_id: int
) -> ImportProcessInvoice | None:
    return (
        db.query(ImportProcessInvoice)
        .filter(
            ImportProcessInvoice.process_id == process_id,
            ImportProcessInvoice.invoice_id == invoice_id,
        )
        .first()
    )


def find_shipment_link(db: Session, shipment_id: int) -> ImportProcessShipment | None:
    return (
        db.query(ImportProcessShipment)
        .filter(ImportProcessShipment.shipment_id == shipment_id)
        .first()
    )


def get_invoice_item_alloc(
    db: Session, process_id: int, invoice_item_id: int
) -> ImportProcessInvoiceItem | None:
    return (
        db.query(ImportProcessInvoiceItem)
        .filter(
            ImportProcessInvoiceItem.process_id == process_id,
            ImportProcessInvoiceItem.invoice_item_id == invoice_item_id,
        )
        .first()
    )


def get_shipment_item_alloc(
    db: Session, process_id: int, shipment_item_id: int
) -> ImportProcessShipmentItem | None:
    return (
        db.query(ImportProcessShipmentItem)
        .filter(
            ImportProcessShipmentItem.process_id == process_id,
            ImportProcessShipmentItem.shipment_item_id == shipment_item_id,
        )
        .first()
    )


def sum_allocated_invoice_item(db: Session, invoice_item_id: int) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(ImportProcessInvoiceItem.allocated_qty), 0)).where(
            ImportProcessInvoiceItem.invoice_item_id == invoice_item_id
        )
    )
    return Decimal(str(total or 0))


def sum_allocated_shipment_item(db: Session, shipment_item_id: int) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(ImportProcessShipmentItem.allocated_qty), 0)).where(
            ImportProcessShipmentItem.shipment_item_id == shipment_item_id
        )
    )
    return Decimal(str(total or 0))


def get_doganale(db: Session, doganale_id: int) -> CustomsDoganale | None:
    return db.query(CustomsDoganale).filter(CustomsDoganale.id == doganale_id).first()


def get_doganale_for_update(db: Session, doganale_id: int) -> CustomsDoganale | None:
    return (
        db.query(CustomsDoganale)
        .filter(CustomsDoganale.id == doganale_id)
        .with_for_update()
        .first()
    )


def get_doganale_by_process(db: Session, process_id: int) -> CustomsDoganale | None:
    return (
        db.query(CustomsDoganale)
        .options(
            joinedload(CustomsDoganale.versions).joinedload(CustomsDoganaleVersion.lines),
        )
        .filter(CustomsDoganale.process_id == process_id)
        .first()
    )


def next_version_number(db: Session, doganale_id: int) -> int:
    mx = db.scalar(
        select(func.coalesce(func.max(CustomsDoganaleVersion.version_number), 0)).where(
            CustomsDoganaleVersion.doganale_id == doganale_id
        )
    )
    return int(mx or 0) + 1


def get_version(db: Session, version_id: int) -> CustomsDoganaleVersion | None:
    return (
        db.query(CustomsDoganaleVersion)
        .options(joinedload(CustomsDoganaleVersion.lines))
        .filter(CustomsDoganaleVersion.id == version_id)
        .first()
    )


def get_version_for_update(db: Session, version_id: int) -> CustomsDoganaleVersion | None:
    return (
        db.query(CustomsDoganaleVersion)
        .filter(CustomsDoganaleVersion.id == version_id)
        .with_for_update()
        .first()
    )


def get_current_version(db: Session, doganale_id: int) -> CustomsDoganaleVersion | None:
    return (
        db.query(CustomsDoganaleVersion)
        .options(joinedload(CustomsDoganaleVersion.lines))
        .filter(
            CustomsDoganaleVersion.doganale_id == doganale_id,
            CustomsDoganaleVersion.is_current.is_(True),
        )
        .first()
    )


def get_current_version_for_update(
    db: Session, doganale_id: int
) -> CustomsDoganaleVersion | None:
    return (
        db.query(CustomsDoganaleVersion)
        .filter(
            CustomsDoganaleVersion.doganale_id == doganale_id,
            CustomsDoganaleVersion.is_current.is_(True),
        )
        .with_for_update()
        .first()
    )


def get_version_by_idempotency(
    db: Session, doganale_id: int, key: str
) -> CustomsDoganaleVersion | None:
    return (
        db.query(CustomsDoganaleVersion)
        .options(joinedload(CustomsDoganaleVersion.lines))
        .filter(
            CustomsDoganaleVersion.doganale_id == doganale_id,
            CustomsDoganaleVersion.idempotency_key == key,
        )
        .first()
    )


def list_versions(db: Session, doganale_id: int) -> list[CustomsDoganaleVersion]:
    return (
        db.query(CustomsDoganaleVersion)
        .options(joinedload(CustomsDoganaleVersion.lines))
        .filter(CustomsDoganaleVersion.doganale_id == doganale_id)
        .order_by(CustomsDoganaleVersion.version_number.desc())
        .all()
    )


def list_divergences(db: Session, process_id: int) -> list[CustomsDivergence]:
    return (
        db.query(CustomsDivergence)
        .filter(CustomsDivergence.process_id == process_id)
        .order_by(CustomsDivergence.id.desc())
        .all()
    )


def get_provenance(
    db: Session, entity_type: str, entity_id: str, source_kind: str
) -> CustomsProvenance | None:
    return (
        db.query(CustomsProvenance)
        .filter(
            CustomsProvenance.entity_type == entity_type,
            CustomsProvenance.entity_id == entity_id,
            CustomsProvenance.source_kind == source_kind,
        )
        .first()
    )


def list_provenances(db: Session, process_id: int) -> list[CustomsProvenance]:
    return (
        db.query(CustomsProvenance)
        .filter(CustomsProvenance.process_id == process_id)
        .order_by(CustomsProvenance.id.desc())
        .all()
    )


# —— Payee / Funding (I5-3A) ——


def get_payee(db: Session, payee_id: int) -> CustomsPayee | None:
    return db.query(CustomsPayee).filter(CustomsPayee.id == payee_id).first()


def list_payees(db: Session, *, limit: int = 100, offset: int = 0) -> list[CustomsPayee]:
    return (
        db.query(CustomsPayee)
        .order_by(CustomsPayee.name.asc(), CustomsPayee.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def _funding_options():
    return (
        joinedload(CustomsFundingRequest.payee),
        joinedload(CustomsFundingRequest.value_bases),
        joinedload(CustomsFundingRequest.tax_lines),
        joinedload(CustomsFundingRequest.expense_lines),
        joinedload(CustomsFundingRequest.payable_links),
    )


def get_funding(db: Session, funding_id: int) -> CustomsFundingRequest | None:
    return (
        db.query(CustomsFundingRequest)
        .options(*_funding_options())
        .filter(CustomsFundingRequest.id == funding_id)
        .first()
    )


def get_funding_for_update(db: Session, funding_id: int) -> CustomsFundingRequest | None:
    return (
        db.query(CustomsFundingRequest)
        .filter(CustomsFundingRequest.id == funding_id)
        .with_for_update()
        .first()
    )


def get_funding_by_idempotency(
    db: Session, process_id: int, key: str
) -> CustomsFundingRequest | None:
    return (
        db.query(CustomsFundingRequest)
        .options(*_funding_options())
        .filter(
            CustomsFundingRequest.process_id == process_id,
            CustomsFundingRequest.idempotency_key == key,
        )
        .first()
    )


def list_fundings(db: Session, process_id: int) -> list[CustomsFundingRequest]:
    return (
        db.query(CustomsFundingRequest)
        .options(*_funding_options())
        .filter(CustomsFundingRequest.process_id == process_id)
        .order_by(CustomsFundingRequest.id.desc())
        .all()
    )


def _nat_options():
    from app.customs.models import Nationalization, NationalizationItem

    return (joinedload(Nationalization.items),)


def get_nationalization(db: Session, nat_id: int):
    from app.customs.models import Nationalization

    return (
        db.query(Nationalization)
        .options(*_nat_options())
        .filter(Nationalization.id == nat_id)
        .first()
    )


def get_nationalization_for_update(db: Session, nat_id: int):
    from app.customs.models import Nationalization

    return (
        db.query(Nationalization)
        .filter(Nationalization.id == nat_id)
        .with_for_update()
        .first()
    )


def list_nationalizations(db: Session, process_id: int):
    from app.customs.models import Nationalization

    return (
        db.query(Nationalization)
        .options(*_nat_options())
        .filter(Nationalization.process_id == process_id)
        .order_by(Nationalization.id.desc())
        .all()
    )


def sum_confirmed_nationalized(
    db: Session,
    *,
    doganale_line_id: int | None = None,
    invoice_item_id: int | None = None,
    shipment_item_id: int | None = None,
    exclude_nationalization_id: int | None = None,
) -> Decimal:
    """Soma qty de itens em nationalizations CONFIRMED para um source key."""
    from app.customs.models import Nationalization, NationalizationItem

    q = (
        db.query(func.coalesce(func.sum(NationalizationItem.quantity), 0))
        .join(Nationalization, NationalizationItem.nationalization_id == Nationalization.id)
        .filter(Nationalization.status == "CONFIRMED")
    )
    if doganale_line_id is not None:
        q = q.filter(NationalizationItem.doganale_line_id == doganale_line_id)
    elif invoice_item_id is not None:
        q = q.filter(NationalizationItem.invoice_item_id == invoice_item_id)
    elif shipment_item_id is not None:
        q = q.filter(NationalizationItem.shipment_item_id == shipment_item_id)
    else:
        return Decimal("0")
    if exclude_nationalization_id is not None:
        q = q.filter(Nationalization.id != exclude_nationalization_id)
    return Decimal(str(q.scalar() or 0))


def sum_confirmed_nationalized_by_product(db: Session, product_id: int) -> Decimal:
    from app.customs.models import Nationalization, NationalizationItem

    q = (
        db.query(func.coalesce(func.sum(NationalizationItem.quantity), 0))
        .join(Nationalization, NationalizationItem.nationalization_id == Nationalization.id)
        .filter(
            Nationalization.status == "CONFIRMED",
            NationalizationItem.product_id == product_id,
        )
    )
    return Decimal(str(q.scalar() or 0))


def list_confirmed_nationalization_items_for_product(db: Session, product_id: int):
    from app.customs.models import Nationalization, NationalizationItem

    return (
        db.query(NationalizationItem)
        .join(Nationalization, NationalizationItem.nationalization_id == Nationalization.id)
        .filter(
            Nationalization.status == "CONFIRMED",
            NationalizationItem.product_id == product_id,
        )
        .all()
    )


def get_doganale_line(db: Session, line_id: int):
    from app.customs.models import CustomsDoganaleLine

    return db.query(CustomsDoganaleLine).filter(CustomsDoganaleLine.id == line_id).first()

