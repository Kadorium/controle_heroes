"""Logistics repository."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.logistics.models import (
    LogisticsProvider,
    Shipment,
    ShipmentDocumentSummary,
    ShipmentItem,
    ShipmentPackage,
    ShipmentPackageContent,
    ShipmentReference,
)


def get_provider(db: Session, provider_id: int) -> LogisticsProvider | None:
    return db.get(LogisticsProvider, provider_id)


def list_providers(
    db: Session,
    *,
    active_only: bool = False,
    provider_types: list[str] | tuple[str, ...] | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[LogisticsProvider]:
    query = db.query(LogisticsProvider)
    if active_only:
        query = query.filter(LogisticsProvider.active.is_(True))
    if provider_types:
        query = query.filter(LogisticsProvider.provider_type.in_(list(provider_types)))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                LogisticsProvider.legal_name.ilike(like),
                LogisticsProvider.trade_name.ilike(like),
            )
        )
    return (
        query.order_by(LogisticsProvider.legal_name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def add_provider(db: Session, provider: LogisticsProvider) -> LogisticsProvider:
    db.add(provider)
    db.flush()
    return provider


def get_shipment(db: Session, shipment_id: int) -> Shipment | None:
    return (
        db.query(Shipment)
        .options(
            joinedload(Shipment.logistics_provider),
            joinedload(Shipment.items),
            joinedload(Shipment.packages).joinedload(ShipmentPackage.contents),
            joinedload(Shipment.references),
            joinedload(Shipment.document_summaries),
        )
        .filter(Shipment.id == shipment_id)
        .first()
    )


def get_shipment_by_code(db: Session, code: str) -> Shipment | None:
    return db.query(Shipment).filter(Shipment.code == code).first()


def list_shipments(
    db: Session,
    *,
    status: str | None = None,
    modal: str | None = None,
    logistics_provider_id: int | None = None,
    include_cancelled: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Shipment]:
    q = db.query(Shipment)
    if status == "CANCELLED":
        q = q.filter(Shipment.cancelled_at.isnot(None))
    else:
        if not include_cancelled:
            q = q.filter(Shipment.cancelled_at.is_(None))
        if status:
            q = q.filter(Shipment.status == status)
    if modal:
        q = q.filter(Shipment.modal == modal)
    if logistics_provider_id is not None:
        q = q.filter(Shipment.logistics_provider_id == logistics_provider_id)
    return q.order_by(Shipment.updated_at.desc()).offset(offset).limit(limit).all()


def add_shipment(db: Session, shipment: Shipment) -> Shipment:
    db.add(shipment)
    db.flush()
    return shipment


def get_item(db: Session, item_id: int) -> ShipmentItem | None:
    return db.query(ShipmentItem).filter(ShipmentItem.id == item_id).first()


def get_item_by_order_item(db: Session, shipment_id: int, order_item_id: int) -> ShipmentItem | None:
    return (
        db.query(ShipmentItem)
        .filter(
            ShipmentItem.shipment_id == shipment_id,
            ShipmentItem.order_item_id == order_item_id,
        )
        .first()
    )


def shipped_qty_for_order_item(
    db: Session, order_item_id: int, *, exclude_shipment_id: int | None = None
):
    from decimal import Decimal

    from sqlalchemy import func

    q = (
        db.query(func.coalesce(func.sum(ShipmentItem.quantity), 0))
        .join(Shipment, Shipment.id == ShipmentItem.shipment_id)
        .filter(
            ShipmentItem.order_item_id == order_item_id,
            Shipment.cancelled_at.is_(None),
        )
    )
    if exclude_shipment_id is not None:
        q = q.filter(ShipmentItem.shipment_id != exclude_shipment_id)
    val = q.scalar()
    return Decimal(str(val or 0))


def find_by_reference(db: Session, reference_type: str, reference_value: str) -> list[Shipment]:
    return (
        db.query(Shipment)
        .join(ShipmentReference)
        .filter(
            ShipmentReference.reference_type == reference_type,
            ShipmentReference.reference_value == reference_value,
            Shipment.cancelled_at.is_(None),
        )
        .all()
    )


def get_package(db: Session, package_id: int) -> ShipmentPackage | None:
    return (
        db.query(ShipmentPackage)
        .options(joinedload(ShipmentPackage.contents))
        .filter(ShipmentPackage.id == package_id)
        .first()
    )


def get_reference(db: Session, ref_id: int) -> ShipmentReference | None:
    return db.query(ShipmentReference).filter(ShipmentReference.id == ref_id).first()


def get_summary(db: Session, summary_id: int) -> ShipmentDocumentSummary | None:
    return db.query(ShipmentDocumentSummary).filter(ShipmentDocumentSummary.id == summary_id).first()


def get_summary_by_doc(db: Session, shipment_id: int, document_id: int) -> ShipmentDocumentSummary | None:
    return (
        db.query(ShipmentDocumentSummary)
        .filter(
            ShipmentDocumentSummary.shipment_id == shipment_id,
            ShipmentDocumentSummary.document_id == document_id,
        )
        .first()
    )
