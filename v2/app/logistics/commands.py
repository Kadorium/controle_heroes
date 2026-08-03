"""Logistics commands — caller owns UoW."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.logistics import repository as repo
from app.logistics.errors import (
    InvalidTransition,
    LogisticsError,
    OvershipError,
    ProviderNotFound,
    ShipmentConflict,
    ShipmentNotFound,
    ShipmentNotPlanned,
    ShipmentValidationError,
)
from app.logistics.models import (
    DECLARED_PROVENANCES,
    PACKAGE_TYPES,
    PROVIDER_TYPES,
    REFERENCE_TYPES,
    SHIPMENT_MODALS,
    SHIPMENT_PROVIDER_TYPES,
    SHIPMENT_STATUSES,
    LogisticsProvider,
    Shipment,
    ShipmentDocumentSummary,
    ShipmentItem,
    ShipmentPackage,
    ShipmentPackageContent,
    ShipmentReference,
)

_BATCH_MAX_PACKAGES = 500
from app.orders import public as orders_public

TRANSITIONS = {
    "PLANNED": "BOOKED",
    "BOOKED": "IN_TRANSIT",
    "IN_TRANSIT": "ARRIVED",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dec(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _require_shipment(db: Session, shipment_id: int) -> Shipment:
    s = repo.get_shipment(db, shipment_id)
    if not s:
        raise ShipmentNotFound(shipment_id)
    return s


def _check_version(shipment: Shipment, expected_version: int) -> None:
    if shipment.version != expected_version:
        raise ShipmentConflict()


def _bump(shipment: Shipment) -> None:
    shipment.version += 1


def _assert_planned_active(shipment: Shipment) -> None:
    if shipment.cancelled_at is not None:
        raise ShipmentNotPlanned("Embarque anulado")
    if shipment.status != "PLANNED":
        raise ShipmentNotPlanned()


def _assert_structure_mutable(shipment: Shipment) -> None:
    _assert_planned_active(shipment)


def _gen_code() -> str:
    return f"SHP-{uuid.uuid4().hex[:12].upper()}"


def _derive_volume(
    *,
    length: Decimal | None,
    width: Decimal | None,
    height: Decimal | None,
    dimension_unit: str | None,
    volume_m3: Decimal | None,
) -> tuple[Decimal | None, bool]:
    if volume_m3 is not None:
        return volume_m3, False
    if length is None or width is None or height is None:
        return None, False
    unit = (dimension_unit or "").upper()
    if unit != "CM":
        return None, False
    raw = (length * width * height) / Decimal("1000000")
    return raw.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP), True


def _validate_modal(modal: str | None) -> str | None:
    if modal is None:
        return None
    value = modal.strip().upper()
    if value not in SHIPMENT_MODALS:
        raise ShipmentValidationError(
            f"Modal inválido: {modal}",
            code="invalid_modal",
        )
    return value


def _provider_display_name(provider: LogisticsProvider) -> str:
    name = (provider.trade_name or provider.legal_name or "").strip()
    return name[:128] if name else provider.legal_name[:128]


def _resolve_shipment_provider(
    db: Session, logistics_provider_id: int | None
) -> tuple[int | None, str | None]:
    if logistics_provider_id is None:
        return None, None
    provider = repo.get_provider(db, logistics_provider_id)
    if not provider:
        raise ProviderNotFound(logistics_provider_id)
    if not provider.active:
        raise ShipmentValidationError(
            "Prestador logístico inativo",
            code="provider_inactive",
        )
    if provider.provider_type not in SHIPMENT_PROVIDER_TYPES:
        raise ShipmentValidationError(
            "Tipo de prestador não elegível para embarque",
            code="provider_type_not_eligible",
        )
    return provider.id, _provider_display_name(provider)


def create_logistics_provider(
    db: Session,
    *,
    legal_name: str,
    provider_type: str,
    trade_name: str | None = None,
    active: bool = True,
) -> LogisticsProvider:
    name = legal_name.strip()
    if not name:
        raise ShipmentValidationError("Razão social obrigatória")
    ptype = provider_type.strip().upper()
    if ptype not in PROVIDER_TYPES:
        raise ShipmentValidationError(
            f"Tipo de prestador inválido: {provider_type}",
            code="invalid_provider_type",
        )
    trade = trade_name.strip() if trade_name else None
    provider = LogisticsProvider(
        legal_name=name,
        trade_name=trade or None,
        provider_type=ptype,
        active=active,
    )
    return repo.add_provider(db, provider)


def update_logistics_provider(
    db: Session,
    provider_id: int,
    *,
    legal_name: str | None = ...,
    trade_name: str | None = ...,
    provider_type: str | None = ...,
    active: bool | None = ...,
) -> LogisticsProvider:
    provider = repo.get_provider(db, provider_id)
    if not provider:
        raise ProviderNotFound(provider_id)
    if legal_name is not ...:
        name = (legal_name or "").strip()
        if not name:
            raise ShipmentValidationError("Razão social obrigatória")
        provider.legal_name = name
    if trade_name is not ...:
        trade = trade_name.strip() if trade_name else None
        provider.trade_name = trade or None
    if provider_type is not ...:
        ptype = (provider_type or "").strip().upper()
        if ptype not in PROVIDER_TYPES:
            raise ShipmentValidationError(
                f"Tipo de prestador inválido: {provider_type}",
                code="invalid_provider_type",
            )
        provider.provider_type = ptype
    if active is not ...:
        provider.active = bool(active)
    db.flush()
    return provider


def create_shipment(
    db: Session,
    *,
    modal: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    logistics_provider_id: int | None = None,
    planned_departure: date | None = None,
    planned_arrival: date | None = None,
    notes: str | None = None,
) -> Shipment:
    modal_value = _validate_modal(modal)
    provider_id, snapshot = _resolve_shipment_provider(db, logistics_provider_id)
    shipment = Shipment(
        code=_gen_code(),
        status="PLANNED",
        version=1,
        modal=modal_value,
        origin=origin,
        destination=destination,
        logistics_provider_id=provider_id,
        carrier_name_snapshot=snapshot,
        planned_departure=planned_departure,
        planned_arrival=planned_arrival,
        notes=notes,
        status_changed_at=_now(),
    )
    return repo.add_shipment(db, shipment)


def update_shipment(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    modal: str | None = ...,
    origin: str | None = ...,
    destination: str | None = ...,
    logistics_provider_id: int | None = ...,
    planned_departure: date | None = ...,
    planned_arrival: date | None = ...,
    notes: str | None = ...,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    if s.cancelled_at is not None:
        raise ShipmentValidationError("Embarque anulado")
    if s.status == "PLANNED":
        if modal is not ...:
            s.modal = _validate_modal(modal)
        if origin is not ...:
            s.origin = origin
        if destination is not ...:
            s.destination = destination
        if logistics_provider_id is not ...:
            pid, snapshot = _resolve_shipment_provider(db, logistics_provider_id)
            s.logistics_provider_id = pid
            s.carrier_name_snapshot = snapshot
        if planned_departure is not ...:
            s.planned_departure = planned_departure
        if planned_arrival is not ...:
            s.planned_arrival = planned_arrival
        if notes is not ...:
            s.notes = notes
    elif s.status == "BOOKED":
        if logistics_provider_id is not ...:
            pid, snapshot = _resolve_shipment_provider(db, logistics_provider_id)
            if pid is None:
                raise ShipmentValidationError(
                    "BOOKED exige prestador logístico",
                    code="provider_required",
                )
            s.logistics_provider_id = pid
            s.carrier_name_snapshot = snapshot
        if planned_departure is not ...:
            s.planned_departure = planned_departure
        if planned_arrival is not ...:
            s.planned_arrival = planned_arrival
        if notes is not ...:
            s.notes = notes
        if any(x is not ... for x in (modal, origin, destination)):
            raise ShipmentValidationError("Campos de modal/rota só editáveis em PLANNED")
    else:
        if notes is not ...:
            s.notes = notes
        if any(
            x is not ...
            for x in (
                modal,
                origin,
                destination,
                logistics_provider_id,
                planned_departure,
                planned_arrival,
            )
        ):
            raise ShipmentValidationError("Somente notes editável neste status")
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def advance_shipment_status(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    event_date: date,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    if s.cancelled_at is not None:
        raise InvalidTransition("Embarque anulado")
    nxt = TRANSITIONS.get(s.status)
    if not nxt:
        raise InvalidTransition(f"Sem transição a partir de {s.status}")
    if s.status == "PLANNED":
        if not s.items:
            raise InvalidTransition("BOOKED exige ao menos um ShipmentItem")
        if not s.modal:
            raise InvalidTransition("BOOKED exige modal de transporte")
        if not s.logistics_provider_id:
            raise InvalidTransition("BOOKED exige prestador logístico")
    if nxt == "IN_TRANSIT":
        s.actual_departure = event_date
        if s.actual_arrival is not None and s.actual_arrival < event_date:
            raise ShipmentValidationError("actual_arrival < actual_departure")
    if nxt == "ARRIVED":
        s.actual_arrival = event_date
        if s.actual_departure is not None and event_date < s.actual_departure:
            raise ShipmentValidationError(
                "actual_arrival deve ser >= actual_departure",
                code="invalid_dates",
            )
    s.status = nxt
    s.status_changed_at = _now()
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def add_shipment_item(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    order_item_id: int,
    quantity: str | Decimal,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    qty = _dec(quantity)
    if qty is None or qty <= 0:
        raise ShipmentValidationError("quantity deve ser > 0")
    if repo.get_item_by_order_item(db, shipment_id, order_item_id):
        raise ShipmentValidationError("OrderItem já no embarque — edite a quantidade", code="duplicate_item")

    oi = orders_public.get_order_item(db, order_item_id)
    order = orders_public.get_order_locked(db, oi.order_id)
    if order.status != "CONFIRMED":
        raise ShipmentValidationError("OrderItem só de Order CONFIRMED")

    shipped = repo.shipped_qty_for_order_item(db, order_item_id)
    residual = Decimal(str(oi.quantity)) - shipped
    if qty > residual:
        raise OvershipError(f"overship: qty={qty} residual={residual}")

    item = ShipmentItem(shipment_id=s.id, order_item_id=order_item_id, quantity=qty)
    db.add(item)
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def update_shipment_item(
    db: Session,
    shipment_id: int,
    item_id: int,
    *,
    expected_version: int,
    quantity: str | Decimal,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    item = repo.get_item(db, item_id)
    if not item or item.shipment_id != shipment_id:
        raise ShipmentNotFound(f"item {item_id}")
    qty = _dec(quantity)
    if qty is None or qty <= 0:
        raise ShipmentValidationError("quantity deve ser > 0")

    oi = orders_public.get_order_item(db, item.order_item_id)
    orders_public.get_order_locked(db, oi.order_id)
    shipped_others = repo.shipped_qty_for_order_item(
        db, item.order_item_id, exclude_shipment_id=shipment_id
    )
    # also exclude this item's current contribution within shipment by excluding whole shipment
    # then add other items in this shipment for same order_item (unique so none)
    residual = Decimal(str(oi.quantity)) - shipped_others
    if qty > residual:
        raise OvershipError(f"overship: qty={qty} residual={residual}")
    item.quantity = qty
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def remove_shipment_item(
    db: Session,
    shipment_id: int,
    item_id: int,
    *,
    expected_version: int,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    item = repo.get_item(db, item_id)
    if not item or item.shipment_id != shipment_id:
        raise ShipmentNotFound(f"item {item_id}")
    oi = orders_public.get_order_item(db, item.order_item_id)
    orders_public.get_order_locked(db, oi.order_id)
    db.delete(item)
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def add_shipment_package(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    package_type: str,
    package_count: int = 1,
    external_package_no: str | None = None,
    description: str | None = None,
    packaging_ncm: str | None = None,
    length: str | Decimal | None = None,
    width: str | Decimal | None = None,
    height: str | Decimal | None = None,
    dimension_unit: str | None = None,
    raw_dimensions: str | None = None,
    net_weight_kg: str | Decimal | None = None,
    gross_weight_kg: str | Decimal | None = None,
    volume_m3: str | Decimal | None = None,
    parent_package_id: int | None = None,
    source_document_id: int | None = None,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    if package_type not in PACKAGE_TYPES:
        raise ShipmentValidationError(f"package_type inválido: {package_type}")
    if package_count < 1:
        raise ShipmentValidationError("package_count deve ser >= 1")
    if parent_package_id is not None:
        if package_count != 1:
            raise ShipmentValidationError("parent_package_id exige package_count=1")
        parent = repo.get_package(db, parent_package_id)
        if not parent or parent.shipment_id != shipment_id:
            raise ShipmentValidationError("parent_package inválido")
        if parent.package_count != 1:
            raise ShipmentValidationError("parent deve ter package_count=1")

    L, W, H = _dec(length), _dec(width), _dec(height)
    vol_in = _dec(volume_m3)
    vol, derived = _derive_volume(
        length=L, width=W, height=H, dimension_unit=dimension_unit, volume_m3=vol_in
    )

    pkg = ShipmentPackage(
        shipment_id=s.id,
        parent_package_id=parent_package_id,
        external_package_no=external_package_no.strip() if external_package_no else None,
        package_type=package_type,
        package_count=package_count,
        description=description,
        packaging_ncm=packaging_ncm,
        length=L,
        width=W,
        height=H,
        dimension_unit=dimension_unit,
        raw_dimensions=raw_dimensions,
        net_weight_kg=_dec(net_weight_kg),
        gross_weight_kg=_dec(gross_weight_kg),
        volume_m3=vol,
        volume_is_derived=derived,
        source_document_id=source_document_id,
    )
    db.add(pkg)
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def update_shipment_package(
    db: Session,
    shipment_id: int,
    package_id: int,
    *,
    expected_version: int,
    **fields,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    pkg = repo.get_package(db, package_id)
    if not pkg or pkg.shipment_id != shipment_id:
        raise ShipmentNotFound(f"package {package_id}")

    if "package_type" in fields and fields["package_type"] is not None:
        if fields["package_type"] not in PACKAGE_TYPES:
            raise ShipmentValidationError("package_type inválido")
        pkg.package_type = fields["package_type"]
    if "package_count" in fields and fields["package_count"] is not None:
        pc = int(fields["package_count"])
        if pc < 1:
            raise ShipmentValidationError("package_count deve ser >= 1")
        if pkg.parent_package_id is not None and pc != 1:
            raise ShipmentValidationError("parent_package_id exige package_count=1")
        pkg.package_count = pc
    for key in (
        "external_package_no",
        "description",
        "packaging_ncm",
        "dimension_unit",
        "raw_dimensions",
        "source_document_id",
    ):
        if key in fields:
            setattr(pkg, key, fields[key])
    for key in ("length", "width", "height", "net_weight_kg", "gross_weight_kg", "volume_m3"):
        if key in fields:
            setattr(pkg, key, _dec(fields[key]))
    if "parent_package_id" in fields:
        pid = fields["parent_package_id"]
        if pid is not None:
            if pkg.package_count != 1:
                raise ShipmentValidationError("parent_package_id exige package_count=1")
            parent = repo.get_package(db, pid)
            if not parent or parent.shipment_id != shipment_id or parent.package_count != 1:
                raise ShipmentValidationError("parent_package inválido")
        pkg.parent_package_id = pid

    if "volume_m3" in fields and fields["volume_m3"] is not None:
        pkg.volume_m3 = _dec(fields["volume_m3"])
        pkg.volume_is_derived = False
    else:
        vol2, der2 = _derive_volume(
            length=pkg.length,
            width=pkg.width,
            height=pkg.height,
            dimension_unit=pkg.dimension_unit,
            volume_m3=None,
        )
        if vol2 is not None:
            pkg.volume_m3 = vol2
            pkg.volume_is_derived = True

    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def remove_shipment_package(
    db: Session,
    shipment_id: int,
    package_id: int,
    *,
    expected_version: int,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    pkg = repo.get_package(db, package_id)
    if not pkg or pkg.shipment_id != shipment_id:
        raise ShipmentNotFound(f"package {package_id}")
    db.delete(pkg)
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def _apply_package_contents(
    db: Session,
    shipment: Shipment,
    pkg: ShipmentPackage,
    contents: list[dict],
) -> None:
    """Replace contents of a package (no version bump)."""
    item_ids = {i.id for i in shipment.items}
    for c in list(pkg.contents):
        db.delete(c)
    db.flush()
    seen: set[int] = set()
    for row in contents:
        sid = int(row["shipment_item_id"])
        if sid in seen:
            raise ShipmentValidationError("shipment_item duplicado no package")
        seen.add(sid)
        if sid not in item_ids:
            raise ShipmentValidationError("shipment_item não pertence ao embarque")
        ncm = row.get("source_ncm")
        if ncm is not None and isinstance(ncm, str):
            ncm = ncm.strip() or None
        desc = row.get("source_description")
        if desc is not None and isinstance(desc, str):
            desc = desc.strip() or None
        db.add(
            ShipmentPackageContent(
                package_id=pkg.id,
                shipment_item_id=sid,
                contained_quantity=_dec(row.get("contained_quantity")),
                source_unit=row.get("source_unit"),
                source_line_reference=row.get("source_line_reference"),
                source_ncm=ncm,
                source_description=desc,
                units_per_package=_dec(row.get("units_per_package")),
                unit_net_weight_kg=_dec(row.get("unit_net_weight_kg")),
                unit_gross_weight_kg=_dec(row.get("unit_gross_weight_kg")),
                source_total_net_weight_kg=_dec(row.get("source_total_net_weight_kg")),
                source_total_gross_weight_kg=_dec(row.get("source_total_gross_weight_kg")),
            )
        )


def set_package_contents(
    db: Session,
    shipment_id: int,
    package_id: int,
    *,
    expected_version: int,
    contents: list[dict],
) -> Shipment:
    """Replace contents. Snapshots documentais (NCM produto, pesos unitários/linha) ≠ pesos físicos do package."""
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    pkg = repo.get_package(db, package_id)
    if not pkg or pkg.shipment_id != shipment_id:
        raise ShipmentNotFound(f"package {package_id}")
    _apply_package_contents(db, s, pkg, contents)
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def _package_kwargs_from_spec(spec: dict) -> dict:
    return {
        "package_type": spec["package_type"],
        "package_count": int(spec.get("package_count") or 1),
        "external_package_no": spec.get("external_package_no"),
        "description": spec.get("description"),
        "packaging_ncm": spec.get("packaging_ncm"),
        "length": spec.get("length"),
        "width": spec.get("width"),
        "height": spec.get("height"),
        "dimension_unit": spec.get("dimension_unit"),
        "raw_dimensions": spec.get("raw_dimensions"),
        "net_weight_kg": spec.get("net_weight_kg"),
        "gross_weight_kg": spec.get("gross_weight_kg"),
        "volume_m3": spec.get("volume_m3"),
        "parent_package_id": spec.get("parent_package_id"),
        "source_document_id": spec.get("source_document_id"),
    }


def _insert_package_row(
    db: Session,
    shipment: Shipment,
    *,
    package_type: str,
    package_count: int = 1,
    external_package_no: str | None = None,
    description: str | None = None,
    packaging_ncm: str | None = None,
    length: str | Decimal | None = None,
    width: str | Decimal | None = None,
    height: str | Decimal | None = None,
    dimension_unit: str | None = None,
    raw_dimensions: str | None = None,
    net_weight_kg: str | Decimal | None = None,
    gross_weight_kg: str | Decimal | None = None,
    volume_m3: str | Decimal | None = None,
    parent_package_id: int | None = None,
    source_document_id: int | None = None,
) -> ShipmentPackage:
    if package_type not in PACKAGE_TYPES:
        raise ShipmentValidationError(f"package_type inválido: {package_type}")
    if package_count < 1:
        raise ShipmentValidationError("package_count deve ser >= 1")
    if parent_package_id is not None:
        if package_count != 1:
            raise ShipmentValidationError("parent_package_id exige package_count=1")
        parent = repo.get_package(db, parent_package_id)
        if not parent or parent.shipment_id != shipment.id:
            raise ShipmentValidationError("parent_package inválido")
        if parent.package_count != 1:
            raise ShipmentValidationError("parent deve ter package_count=1")

    L, W, H = _dec(length), _dec(width), _dec(height)
    vol_in = _dec(volume_m3)
    vol, derived = _derive_volume(
        length=L, width=W, height=H, dimension_unit=dimension_unit, volume_m3=vol_in
    )
    pkg = ShipmentPackage(
        shipment_id=shipment.id,
        parent_package_id=parent_package_id,
        external_package_no=external_package_no.strip() if external_package_no else None,
        package_type=package_type,
        package_count=package_count,
        description=description,
        packaging_ncm=packaging_ncm,
        length=L,
        width=W,
        height=H,
        dimension_unit=dimension_unit,
        raw_dimensions=raw_dimensions,
        net_weight_kg=_dec(net_weight_kg),
        gross_weight_kg=_dec(gross_weight_kg),
        volume_m3=vol,
        volume_is_derived=derived,
        source_document_id=source_document_id,
    )
    db.add(pkg)
    db.flush()
    return pkg


def add_shipment_packages_batch(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    packages: list[dict] | None = None,
    range_from: int | None = None,
    range_to: int | None = None,
    template: dict | None = None,
    contents_template: list[dict] | None = None,
) -> Shipment:
    """Atomic batch: explicit package list OR numbered range with shared template."""
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)

    specs: list[dict] = []
    if packages is not None:
        if range_from is not None or range_to is not None or template is not None:
            raise ShipmentValidationError("batch: use packages OU range+template, não ambos")
        specs = list(packages)
    else:
        if range_from is None or range_to is None or template is None:
            raise ShipmentValidationError("batch range exige range_from, range_to e template")
        if range_from > range_to:
            raise ShipmentValidationError("range_from deve ser <= range_to")
        for n in range(range_from, range_to + 1):
            spec = dict(template)
            spec["external_package_no"] = str(n)
            spec["package_count"] = int(spec.get("package_count") or 1)
            if spec["package_count"] != 1 and spec.get("parent_package_id") is not None:
                raise ShipmentValidationError("parent_package_id exige package_count=1")
            specs.append(spec)

    if not specs:
        raise ShipmentValidationError("batch vazio")
    if len(specs) > _BATCH_MAX_PACKAGES:
        raise ShipmentValidationError(f"batch máximo {_BATCH_MAX_PACKAGES} packages")

    created: list[ShipmentPackage] = []
    for spec in specs:
        if "package_type" not in spec:
            raise ShipmentValidationError("package_type obrigatório em cada package")
        created.append(_insert_package_row(db, s, **_package_kwargs_from_spec(spec)))

    if contents_template:
        for pkg in created:
            _apply_package_contents(db, s, pkg, contents_template)

    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def update_shipment_packages_batch(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    package_ids: list[int],
    fields: dict,
) -> Shipment:
    """Apply the same field updates to multiple packages (one version bump)."""
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    if not package_ids:
        raise ShipmentValidationError("package_ids vazio")
    if len(package_ids) > _BATCH_MAX_PACKAGES:
        raise ShipmentValidationError(f"batch máximo {_BATCH_MAX_PACKAGES} packages")

    # Apply via update_shipment_package without re-checking version each time:
    # temporarily use internal path — first check all exist, then mutate, one bump.
    pkgs: list[ShipmentPackage] = []
    for pid in package_ids:
        pkg = repo.get_package(db, pid)
        if not pkg or pkg.shipment_id != shipment_id:
            raise ShipmentNotFound(f"package {pid}")
        pkgs.append(pkg)

    for pkg in pkgs:
        if "package_type" in fields and fields["package_type"] is not None:
            if fields["package_type"] not in PACKAGE_TYPES:
                raise ShipmentValidationError("package_type inválido")
            pkg.package_type = fields["package_type"]
        if "package_count" in fields and fields["package_count"] is not None:
            pc = int(fields["package_count"])
            if pc < 1:
                raise ShipmentValidationError("package_count deve ser >= 1")
            if pkg.parent_package_id is not None and pc != 1:
                raise ShipmentValidationError("parent_package_id exige package_count=1")
            pkg.package_count = pc
        for key in (
            "external_package_no",
            "description",
            "packaging_ncm",
            "dimension_unit",
            "raw_dimensions",
            "source_document_id",
        ):
            if key in fields:
                setattr(pkg, key, fields[key])
        for key in ("length", "width", "height", "net_weight_kg", "gross_weight_kg", "volume_m3"):
            if key in fields:
                setattr(pkg, key, _dec(fields[key]))
        if "volume_m3" in fields and fields["volume_m3"] is not None:
            pkg.volume_m3 = _dec(fields["volume_m3"])
            pkg.volume_is_derived = False
        elif any(k in fields for k in ("length", "width", "height", "dimension_unit")):
            vol2, der2 = _derive_volume(
                length=pkg.length,
                width=pkg.width,
                height=pkg.height,
                dimension_unit=pkg.dimension_unit,
                volume_m3=None,
            )
            if vol2 is not None:
                pkg.volume_m3 = vol2
                pkg.volume_is_derived = True

    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def add_shipment_reference(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    reference_type: str,
    reference_value: str,
    document_id: int | None = None,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    if reference_type not in REFERENCE_TYPES:
        raise ShipmentValidationError("reference_type inválido")
    value = reference_value.strip()
    if not value:
        raise ShipmentValidationError("reference_value obrigatório")
    db.add(
        ShipmentReference(
            shipment_id=s.id,
            reference_type=reference_type,
            reference_value=value,
            document_id=document_id,
        )
    )
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def remove_shipment_reference(
    db: Session,
    shipment_id: int,
    reference_id: int,
    *,
    expected_version: int,
) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    ref = repo.get_reference(db, reference_id)
    if not ref or ref.shipment_id != shipment_id:
        raise ShipmentNotFound(f"reference {reference_id}")
    db.delete(ref)
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def upsert_document_summary(
    db: Session,
    shipment_id: int,
    *,
    expected_version: int,
    document_id: int,
    declared_net_weight_kg: str | Decimal | None = None,
    declared_gross_weight_kg: str | Decimal | None = None,
    declared_pallet_count: int | None = None,
    declared_carton_count: int | None = None,
    declared_volume_m3: str | Decimal | None = None,
    declared_provenance: str | None = None,
    raw_notes: str | None = None,
) -> Shipment:
    """Declared totals are documentary snapshots. FATTURA_DOGANALE is not Logistics SoT (J#5)."""
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_structure_mutable(s)
    if declared_provenance is not None and declared_provenance not in DECLARED_PROVENANCES:
        raise ShipmentValidationError(
            f"declared_provenance inválido: use {', '.join(DECLARED_PROVENANCES)}"
        )
    row = repo.get_summary_by_doc(db, shipment_id, document_id)
    if not row:
        row = ShipmentDocumentSummary(shipment_id=shipment_id, document_id=document_id)
        db.add(row)
    row.declared_net_weight_kg = _dec(declared_net_weight_kg)
    row.declared_gross_weight_kg = _dec(declared_gross_weight_kg)
    row.declared_pallet_count = declared_pallet_count
    row.declared_carton_count = declared_carton_count
    row.declared_volume_m3 = _dec(declared_volume_m3)
    row.declared_provenance = declared_provenance
    row.raw_notes = raw_notes
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]


def delete_shipment(db: Session, shipment_id: int, *, expected_version: int) -> None:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_planned_active(s)
    if s.items or s.packages:
        raise ShipmentValidationError("Delete só se PLANNED sem items e packages")
    db.delete(s)
    db.flush()


def annul_planned_shipment(db: Session, shipment_id: int, *, expected_version: int) -> Shipment:
    s = _require_shipment(db, shipment_id)
    _check_version(s, expected_version)
    _assert_planned_active(s)
    s.cancelled_at = _now()
    _bump(s)
    db.flush()
    return repo.get_shipment(db, shipment_id)  # type: ignore[return-value]
