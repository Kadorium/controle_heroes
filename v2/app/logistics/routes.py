"""HTTP Logistics — /api/shipments."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.uow import UnitOfWork
from app.logistics import public as logistics_public
from app.logistics.errors import LogisticsError
from app.logistics.models import Shipment
from app.orders import public as orders_public

router = APIRouter(tags=["logistics"])


def _map_error(exc: LogisticsError) -> AppError:
    code = getattr(exc, "code", "logistics_error")
    status = 400
    if code in ("shipment_not_found", "provider_not_found"):
        status = 404
    elif code in ("conflict", "overship"):
        status = 409
    elif code in ("invalid_transition", "shipment_not_planned", "invalid_dates"):
        status = 409 if code != "invalid_dates" else 422
    elif code in (
        "invalid_modal",
        "invalid_provider_type",
        "provider_inactive",
        "provider_type_not_eligible",
        "provider_required",
    ):
        status = 422
    elif code == "candidates_scope_required":
        status = 400
    return AppError(exc.message, code=code, status_code=status)


def _dstr(v: Decimal | None) -> str | None:
    return None if v is None else str(v)


class ProviderCreate(BaseModel):
    legal_name: str
    provider_type: str
    trade_name: str | None = None
    active: bool = True


class ProviderUpdate(BaseModel):
    legal_name: str | None = None
    provider_type: str | None = None
    trade_name: str | None = None
    active: bool | None = None


class ProviderOut(BaseModel):
    id: int
    legal_name: str
    trade_name: str | None
    provider_type: str
    active: bool
    created_at: datetime | None
    updated_at: datetime | None


class ProviderEmbed(BaseModel):
    id: int
    legal_name: str
    trade_name: str | None
    provider_type: str


class ShipmentCreate(BaseModel):
    modal: str | None = None
    origin: str | None = None
    destination: str | None = None
    logistics_provider_id: int | None = None
    planned_departure: date | None = None
    planned_arrival: date | None = None
    notes: str | None = None


class ShipmentUpdate(BaseModel):
    expected_version: int
    modal: str | None = None
    origin: str | None = None
    destination: str | None = None
    logistics_provider_id: int | None = None
    planned_departure: date | None = None
    planned_arrival: date | None = None
    notes: str | None = None


class VersionBody(BaseModel):
    expected_version: int


class AdvanceBody(BaseModel):
    expected_version: int
    event_date: date


class ItemCreate(BaseModel):
    expected_version: int
    order_item_id: int
    quantity: str


class ItemUpdate(BaseModel):
    expected_version: int
    quantity: str


class PackageCreate(BaseModel):
    expected_version: int
    package_type: str
    package_count: int = 1
    external_package_no: str | None = None
    description: str | None = None
    packaging_ncm: str | None = None
    length: str | None = None
    width: str | None = None
    height: str | None = None
    dimension_unit: str | None = None
    raw_dimensions: str | None = None
    net_weight_kg: str | None = None
    gross_weight_kg: str | None = None
    volume_m3: str | None = None
    parent_package_id: int | None = None
    source_document_id: int | None = None


class PackageUpdate(BaseModel):
    expected_version: int
    package_type: str | None = None
    package_count: int | None = None
    external_package_no: str | None = None
    description: str | None = None
    packaging_ncm: str | None = None
    length: str | None = None
    width: str | None = None
    height: str | None = None
    dimension_unit: str | None = None
    raw_dimensions: str | None = None
    net_weight_kg: str | None = None
    gross_weight_kg: str | None = None
    volume_m3: str | None = None
    parent_package_id: int | None = None
    source_document_id: int | None = None


class ContentIn(BaseModel):
    shipment_item_id: int
    contained_quantity: str | None = None
    source_unit: str | None = None
    source_line_reference: str | None = None
    source_ncm: str | None = None
    source_description: str | None = None
    units_per_package: str | None = None
    unit_net_weight_kg: str | None = None
    unit_gross_weight_kg: str | None = None
    source_total_net_weight_kg: str | None = None
    source_total_gross_weight_kg: str | None = None


class ContentsReplace(BaseModel):
    expected_version: int
    contents: list[ContentIn]


class PackageSpec(BaseModel):
    package_type: str
    package_count: int = 1
    external_package_no: str | None = None
    description: str | None = None
    packaging_ncm: str | None = None
    length: str | None = None
    width: str | None = None
    height: str | None = None
    dimension_unit: str | None = None
    raw_dimensions: str | None = None
    net_weight_kg: str | None = None
    gross_weight_kg: str | None = None
    volume_m3: str | None = None
    parent_package_id: int | None = None
    source_document_id: int | None = None


class PackagesBatchCreate(BaseModel):
    expected_version: int
    packages: list[PackageSpec] | None = None
    range_from: int | None = None
    range_to: int | None = None
    template: PackageSpec | None = None
    contents_template: list[ContentIn] | None = None


class PackagesBatchUpdate(BaseModel):
    expected_version: int
    package_ids: list[int]
    package_type: str | None = None
    package_count: int | None = None
    description: str | None = None
    packaging_ncm: str | None = None
    length: str | None = None
    width: str | None = None
    height: str | None = None
    dimension_unit: str | None = None
    raw_dimensions: str | None = None
    net_weight_kg: str | None = None
    gross_weight_kg: str | None = None
    volume_m3: str | None = None
    source_document_id: int | None = None


class ReferenceCreate(BaseModel):
    expected_version: int
    reference_type: str
    reference_value: str
    document_id: int | None = None


class SummaryUpsert(BaseModel):
    expected_version: int
    document_id: int
    declared_net_weight_kg: str | None = None
    declared_gross_weight_kg: str | None = None
    declared_pallet_count: int | None = None
    declared_carton_count: int | None = None
    declared_volume_m3: str | None = None
    declared_provenance: str | None = None
    raw_notes: str | None = None


class ItemOut(BaseModel):
    id: int
    order_item_id: int
    quantity: str
    order_id: int | None = None
    order_code: str | None = None
    external_ref: str | None = None
    sku: str | None = None
    description: str | None = None
    ordered_qty: str | None = None
    shipped_qty: str | None = None
    residual_qty: str | None = None


class PackageContentOut(BaseModel):
    id: int
    shipment_item_id: int
    contained_quantity: str | None
    source_unit: str | None
    source_line_reference: str | None
    source_ncm: str | None
    source_description: str | None
    units_per_package: str | None
    unit_net_weight_kg: str | None
    unit_gross_weight_kg: str | None
    source_total_net_weight_kg: str | None
    source_total_gross_weight_kg: str | None


class PackageOut(BaseModel):
    id: int
    package_type: str
    package_count: int
    external_package_no: str | None
    description: str | None
    packaging_ncm: str | None
    length: str | None
    width: str | None
    height: str | None
    dimension_unit: str | None
    raw_dimensions: str | None
    net_weight_kg: str | None
    gross_weight_kg: str | None
    volume_m3: str | None
    volume_is_derived: bool
    parent_package_id: int | None
    source_document_id: int | None
    contents: list[PackageContentOut]


class ReferenceOut(BaseModel):
    id: int
    reference_type: str
    reference_value: str
    document_id: int | None


class SummaryOut(BaseModel):
    id: int
    document_id: int
    declared_net_weight_kg: str | None
    declared_gross_weight_kg: str | None
    declared_pallet_count: int | None
    declared_carton_count: int | None
    declared_volume_m3: str | None
    declared_provenance: str | None
    raw_notes: str | None


class ShipmentOut(BaseModel):
    id: int
    code: str
    status: str
    version: int
    cancelled_at: datetime | None
    modal: str | None
    origin: str | None
    destination: str | None
    logistics_provider_id: int | None
    carrier_name_snapshot: str | None
    logistics_provider: ProviderEmbed | None = None
    planned_departure: date | None
    planned_arrival: date | None
    actual_departure: date | None
    actual_arrival: date | None
    status_changed_at: datetime
    notes: str | None
    created_at: datetime | None
    updated_at: datetime | None
    items: list[ItemOut] = Field(default_factory=list)
    packages: list[PackageOut] = Field(default_factory=list)
    references: list[ReferenceOut] = Field(default_factory=list)
    document_summaries: list[SummaryOut] = Field(default_factory=list)


class ShipmentListItem(BaseModel):
    id: int
    code: str
    status: str
    cancelled_at: datetime | None
    modal: str | None
    origin: str | None
    destination: str | None
    logistics_provider_id: int | None
    carrier_name_snapshot: str | None
    planned_departure: date | None
    actual_departure: date | None
    item_count: int
    package_count: int
    updated_at: datetime | None


class CandidateOut(BaseModel):
    order_id: int
    order_code: str
    external_ref: str | None
    supplier_id: int
    order_item_id: int
    sku: str
    description: str
    ordered_qty: str
    shipped_qty: str
    residual_qty: str


def _serialize(db: Session, s: Shipment, *, enrich_items: bool = True) -> ShipmentOut:
    items_out: list[ItemOut] = []
    for it in s.items:
        row = ItemOut(id=it.id, order_item_id=it.order_item_id, quantity=str(it.quantity))
        if enrich_items:
            try:
                oi = orders_public.get_order_item(db, it.order_item_id)
                order = orders_public.get_order(db, oi.order_id)
                shipped = logistics_public.shipped_qty_by_order_item(db, it.order_item_id)
                ordered = oi.quantity
                residual = ordered - shipped
                row.order_id = order.id
                row.order_code = order.code
                row.external_ref = order.external_ref
                row.sku = oi.sku_snapshot
                row.description = oi.description_snapshot
                row.ordered_qty = str(ordered)
                row.shipped_qty = str(shipped)
                row.residual_qty = str(residual)
            except Exception:
                pass
        items_out.append(row)

    packages = [
        PackageOut(
            id=p.id,
            package_type=p.package_type,
            package_count=p.package_count,
            external_package_no=p.external_package_no,
            description=p.description,
            packaging_ncm=p.packaging_ncm,
            length=_dstr(p.length),
            width=_dstr(p.width),
            height=_dstr(p.height),
            dimension_unit=p.dimension_unit,
            raw_dimensions=p.raw_dimensions,
            net_weight_kg=_dstr(p.net_weight_kg),
            gross_weight_kg=_dstr(p.gross_weight_kg),
            volume_m3=_dstr(p.volume_m3),
            volume_is_derived=p.volume_is_derived,
            parent_package_id=p.parent_package_id,
            source_document_id=p.source_document_id,
            contents=[
                PackageContentOut(
                    id=c.id,
                    shipment_item_id=c.shipment_item_id,
                    contained_quantity=_dstr(c.contained_quantity),
                    source_unit=c.source_unit,
                    source_line_reference=c.source_line_reference,
                    source_ncm=c.source_ncm,
                    source_description=c.source_description,
                    units_per_package=_dstr(c.units_per_package),
                    unit_net_weight_kg=_dstr(c.unit_net_weight_kg),
                    unit_gross_weight_kg=_dstr(c.unit_gross_weight_kg),
                    source_total_net_weight_kg=_dstr(c.source_total_net_weight_kg),
                    source_total_gross_weight_kg=_dstr(c.source_total_gross_weight_kg),
                )
                for c in p.contents
            ],
        )
        for p in s.packages
    ]
    return ShipmentOut(
        id=s.id,
        code=s.code,
        status=s.status,
        version=s.version,
        cancelled_at=s.cancelled_at,
        modal=s.modal,
        origin=s.origin,
        destination=s.destination,
        logistics_provider_id=s.logistics_provider_id,
        carrier_name_snapshot=s.carrier_name_snapshot,
        logistics_provider=(
            ProviderEmbed(
                id=s.logistics_provider.id,
                legal_name=s.logistics_provider.legal_name,
                trade_name=s.logistics_provider.trade_name,
                provider_type=s.logistics_provider.provider_type,
            )
            if s.logistics_provider is not None
            else None
        ),
        planned_departure=s.planned_departure,
        planned_arrival=s.planned_arrival,
        actual_departure=s.actual_departure,
        actual_arrival=s.actual_arrival,
        status_changed_at=s.status_changed_at,
        notes=s.notes,
        created_at=s.created_at,
        updated_at=s.updated_at,
        items=items_out,
        packages=packages,
        references=[
            ReferenceOut(
                id=r.id,
                reference_type=r.reference_type,
                reference_value=r.reference_value,
                document_id=r.document_id,
            )
            for r in s.references
        ],
        document_summaries=[
            SummaryOut(
                id=d.id,
                document_id=d.document_id,
                declared_net_weight_kg=_dstr(d.declared_net_weight_kg),
                declared_gross_weight_kg=_dstr(d.declared_gross_weight_kg),
                declared_pallet_count=d.declared_pallet_count,
                declared_carton_count=d.declared_carton_count,
                declared_volume_m3=_dstr(d.declared_volume_m3),
                declared_provenance=d.declared_provenance,
                raw_notes=d.raw_notes,
            )
            for d in s.document_summaries
        ],
    )


def _provider_out(p) -> ProviderOut:
    return ProviderOut(
        id=p.id,
        legal_name=p.legal_name,
        trade_name=p.trade_name,
        provider_type=p.provider_type,
        active=p.active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/logistics-providers", response_model=list[ProviderOut])
def list_providers(
    q: str | None = None,
    active_only: bool = False,
    shipment_eligible_only: bool = False,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:read")
    rows = logistics_public.list_logistics_providers(
        db,
        q=q,
        active_only=active_only,
        shipment_eligible_only=shipment_eligible_only,
        limit=limit,
        offset=offset,
    )
    return [_provider_out(p) for p in rows]


@router.post("/logistics-providers", response_model=ProviderOut, status_code=201)
def create_provider(
    body: ProviderCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            p = logistics_public.create_logistics_provider(uow.session, **body.model_dump())
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="logistics_provider",
                entity_id=str(p.id),
                action="logistics_provider.create",
            )
            uow.commit()
            return _provider_out(p)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/logistics-providers/{provider_id}", response_model=ProviderOut)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:read")
    try:
        return _provider_out(logistics_public.get_logistics_provider(db, provider_id))
    except LogisticsError as e:
        raise _map_error(e) from e


@router.patch("/logistics-providers/{provider_id}", response_model=ProviderOut)
def patch_provider(
    provider_id: int,
    body: ProviderUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
            p = logistics_public.update_logistics_provider(
                uow.session, provider_id, **payload
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="logistics_provider",
                entity_id=str(p.id),
                action="logistics_provider.update",
            )
            uow.commit()
            return _provider_out(p)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments/order-item-candidates", response_model=list[CandidateOut])
def candidates(
    order_id: int | None = None,
    order_code: str | None = None,
    external_ref: str | None = None,
    sku: str | None = None,
    supplier_id: int | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:read")
    try:
        return logistics_public.order_item_candidates(
            db,
            order_id=order_id,
            order_code=order_code,
            external_ref=external_ref,
            sku=sku,
            supplier_id=supplier_id,
            limit=limit,
        )
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments", response_model=list[ShipmentListItem])
def list_shipments(
    status: str | None = None,
    modal: str | None = None,
    logistics_provider_id: int | None = None,
    include_cancelled: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:read")
    rows = logistics_public.list_shipments(
        db,
        status=status,
        modal=modal,
        logistics_provider_id=logistics_provider_id,
        include_cancelled=include_cancelled,
        limit=limit,
        offset=offset,
    )
    out = []
    for s in rows:
        full = logistics_public.get_shipment(db, s.id)
        out.append(
            ShipmentListItem(
                id=s.id,
                code=s.code,
                status=s.status,
                cancelled_at=s.cancelled_at,
                modal=s.modal,
                origin=s.origin,
                destination=s.destination,
                logistics_provider_id=s.logistics_provider_id,
                carrier_name_snapshot=s.carrier_name_snapshot,
                planned_departure=s.planned_departure,
                actual_departure=s.actual_departure,
                item_count=len(full.items),
                package_count=sum(p.package_count for p in full.packages),
                updated_at=s.updated_at,
            )
        )
    return out


@router.post("/shipments", response_model=ShipmentOut, status_code=201)
def create_shipment(body: ShipmentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.create_shipment(
                uow.session, actor_id=str(user.id), **body.model_dump()
            )
            uow.session.flush()
            s = logistics_public.get_shipment(uow.session, s.id)
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments/by-code/{code}", response_model=ShipmentOut)
def get_by_code(code: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:read")
    try:
        return _serialize(db, logistics_public.get_shipment_by_code(db, code))
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments/{shipment_id}", response_model=ShipmentOut)
def get_shipment(shipment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:read")
    try:
        return _serialize(db, logistics_public.get_shipment(db, shipment_id))
    except LogisticsError as e:
        raise _map_error(e) from e


@router.patch("/shipments/{shipment_id}", response_model=ShipmentOut)
def patch_shipment(
    shipment_id: int, body: ShipmentUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    enforce_permission(user, "logistics:write")
    data = body.model_dump(exclude_unset=True)
    expected = data.pop("expected_version")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.update_shipment(uow.session, shipment_id, expected_version=expected, **data)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="shipment",
                entity_id=str(shipment_id),
                action="shipment.update",
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.post("/shipments/{shipment_id}/advance", response_model=ShipmentOut)
def advance(shipment_id: int, body: AdvanceBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.advance_shipment_status(
                uow.session, shipment_id, expected_version=body.expected_version, event_date=body.event_date
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="shipment",
                entity_id=str(shipment_id),
                action="shipment.advance",
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.post("/shipments/{shipment_id}/annul", response_model=ShipmentOut)
def annul(shipment_id: int, body: VersionBody, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.annul_planned_shipment(
                uow.session, shipment_id, expected_version=body.expected_version
            )
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="shipment",
                entity_id=str(shipment_id),
                action="shipment.annul",
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.delete("/shipments/{shipment_id}", status_code=204)
def delete_shipment(
    shipment_id: int, expected_version: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            logistics_public.delete_shipment(uow.session, shipment_id, expected_version=expected_version)
            audit_public.record_event(
                uow.session,
                actor_id=str(user.id),
                entity_type="shipment",
                entity_id=str(shipment_id),
                action="shipment.delete",
            )
            uow.commit()
    except LogisticsError as e:
        raise _map_error(e) from e


@router.post("/shipments/{shipment_id}/items", response_model=ShipmentOut, status_code=201)
def add_item(shipment_id: int, body: ItemCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.add_shipment_item(
                uow.session,
                shipment_id,
                expected_version=body.expected_version,
                order_item_id=body.order_item_id,
                quantity=body.quantity,
                actor_id=str(user.id),
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.patch("/shipments/{shipment_id}/items/{item_id}", response_model=ShipmentOut)
def patch_item(
    shipment_id: int,
    item_id: int,
    body: ItemUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.update_shipment_item(
                uow.session,
                shipment_id,
                item_id,
                expected_version=body.expected_version,
                quantity=body.quantity,
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.delete("/shipments/{shipment_id}/items/{item_id}", response_model=ShipmentOut)
def delete_item(
    shipment_id: int,
    item_id: int,
    expected_version: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.remove_shipment_item(
                uow.session, shipment_id, item_id, expected_version=expected_version
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.post("/shipments/{shipment_id}/packages", response_model=ShipmentOut, status_code=201)
def add_package(
    shipment_id: int, body: PackageCreate, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    enforce_permission(user, "logistics:write")
    data = body.model_dump()
    expected = data.pop("expected_version")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.add_shipment_package(
                uow.session, shipment_id, expected_version=expected, **data
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.post("/shipments/{shipment_id}/packages/batch", response_model=ShipmentOut, status_code=201)
def add_packages_batch(
    shipment_id: int,
    body: PackagesBatchCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.add_shipment_packages_batch(
                uow.session,
                shipment_id,
                expected_version=body.expected_version,
                packages=(
                    [p.model_dump() for p in body.packages] if body.packages is not None else None
                ),
                range_from=body.range_from,
                range_to=body.range_to,
                template=body.template.model_dump() if body.template is not None else None,
                contents_template=(
                    [c.model_dump() for c in body.contents_template]
                    if body.contents_template is not None
                    else None
                ),
                actor_id=str(user.id),
            )
            uow.commit()
            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.patch("/shipments/{shipment_id}/packages/batch", response_model=ShipmentOut)
def patch_packages_batch(
    shipment_id: int,
    body: PackagesBatchUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    data = body.model_dump(exclude_unset=True)
    expected = data.pop("expected_version")
    package_ids = data.pop("package_ids")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.update_shipment_packages_batch(
                uow.session,
                shipment_id,
                expected_version=expected,
                package_ids=package_ids,
                fields=data,
            )
            uow.commit()
            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.patch("/shipments/{shipment_id}/packages/{package_id}", response_model=ShipmentOut)
def patch_package(
    shipment_id: int,
    package_id: int,
    body: PackageUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    data = body.model_dump(exclude_unset=True)
    expected = data.pop("expected_version")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.update_shipment_package(
                uow.session, shipment_id, package_id, expected_version=expected, **data
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.delete("/shipments/{shipment_id}/packages/{package_id}", response_model=ShipmentOut)
def delete_package(
    shipment_id: int,
    package_id: int,
    expected_version: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.remove_shipment_package(
                uow.session, shipment_id, package_id, expected_version=expected_version
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.put("/shipments/{shipment_id}/packages/{package_id}/contents", response_model=ShipmentOut)
def put_contents(
    shipment_id: int,
    package_id: int,
    body: ContentsReplace,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.set_package_contents(
                uow.session,
                shipment_id,
                package_id,
                expected_version=body.expected_version,
                contents=[c.model_dump() for c in body.contents],
                actor_id=str(user.id),
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.post("/shipments/{shipment_id}/references", response_model=ShipmentOut, status_code=201)
def add_ref(
    shipment_id: int, body: ReferenceCreate, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.add_shipment_reference(
                uow.session,
                shipment_id,
                expected_version=body.expected_version,
                reference_type=body.reference_type,
                reference_value=body.reference_value,
                document_id=body.document_id,
                actor_id=str(user.id),
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.delete("/shipments/{shipment_id}/references/{reference_id}", response_model=ShipmentOut)
def del_ref(
    shipment_id: int,
    reference_id: int,
    expected_version: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.remove_shipment_reference(
                uow.session, shipment_id, reference_id, expected_version=expected_version
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.put("/shipments/{shipment_id}/document-summaries", response_model=ShipmentOut)
def upsert_summary(
    shipment_id: int, body: SummaryUpsert, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    enforce_permission(user, "logistics:write")
    try:
        with UnitOfWork(db) as uow:
            s = logistics_public.upsert_document_summary(
                uow.session,
                shipment_id,
                expected_version=body.expected_version,
                document_id=body.document_id,
                declared_net_weight_kg=body.declared_net_weight_kg,
                declared_gross_weight_kg=body.declared_gross_weight_kg,
                declared_pallet_count=body.declared_pallet_count,
                declared_carton_count=body.declared_carton_count,
                declared_volume_m3=body.declared_volume_m3,
                declared_provenance=body.declared_provenance,
                raw_notes=body.raw_notes,
                actor_id=str(user.id),
            )
            uow.commit()

            return _serialize(uow.session, s)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments/{shipment_id}/totals/derived")
def totals_derived(shipment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:read")
    try:
        d = logistics_public.physical_totals_derived(db, shipment_id)
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in d.items()}
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments/{shipment_id}/totals/divergences")
def totals_div(shipment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:read")
    try:
        return logistics_public.physical_divergences(db, shipment_id)
    except LogisticsError as e:
        raise _map_error(e) from e


@router.get("/shipments/{shipment_id}/allocation-bases")
def alloc_bases(shipment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    enforce_permission(user, "logistics:read")
    try:
        return logistics_public.allocation_bases(db, shipment_id)
    except LogisticsError as e:
        raise _map_error(e) from e
