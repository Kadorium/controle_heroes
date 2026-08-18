"""Logistics queries."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.logistics import divergence
from app.logistics import repository as repo
from app.logistics.errors import ShipmentNotFound, ShipmentValidationError
from app.logistics.models import Shipment
from app.orders import public as orders_public


def shipment_item_facts(db: Session, shipment_item_id: int) -> dict:
    """Catalog facts for a ShipmentItem — public contract for Customs UI."""
    item = repo.get_item(db, shipment_item_id)
    if not item:
        raise ShipmentValidationError(
            f"ShipmentItem {shipment_item_id} não encontrado",
            code="shipment_item_not_found",
        )
    oi = orders_public.get_order_item(db, item.order_item_id)
    return {
        "shipment_item_id": item.id,
        "shipment_id": item.shipment_id,
        "order_item_id": item.order_item_id,
        "quantity": str(item.quantity),
        "product_id": oi.product_id,
        "sku": oi.sku_snapshot,
        "description": oi.description_snapshot,
    }


def get_shipment(db: Session, shipment_id: int) -> Shipment:
    s = repo.get_shipment(db, shipment_id)
    if not s:
        raise ShipmentNotFound(shipment_id)
    return s


def get_shipment_by_code(db: Session, code: str) -> Shipment:
    s = repo.get_shipment_by_code(db, code)
    if not s:
        raise ShipmentNotFound(code)
    return s


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
    return repo.list_shipments(
        db,
        status=status,
        modal=modal,
        logistics_provider_id=logistics_provider_id,
        include_cancelled=include_cancelled,
        limit=limit,
        offset=offset,
    )


def get_logistics_provider(db: Session, provider_id: int):
    from app.logistics.errors import ProviderNotFound

    provider = repo.get_provider(db, provider_id)
    if not provider:
        raise ProviderNotFound(provider_id)
    return provider


def list_logistics_providers(
    db: Session,
    *,
    active_only: bool = False,
    shipment_eligible_only: bool = False,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    from app.logistics.models import SHIPMENT_PROVIDER_TYPES

    types = SHIPMENT_PROVIDER_TYPES if shipment_eligible_only else None
    return repo.list_providers(
        db,
        active_only=active_only,
        provider_types=types,
        q=q,
        limit=limit,
        offset=offset,
    )


def find_shipments_by_reference(db: Session, reference_type: str, reference_value: str) -> list[Shipment]:
    return repo.find_by_reference(db, reference_type, reference_value)


def shipped_qty_by_order_item(db: Session, order_item_id: int) -> Decimal:
    return repo.shipped_qty_for_order_item(db, order_item_id)


def residuals_for_order(db: Session, order_id: int) -> list[dict]:
    order = orders_public.get_order(db, order_id)
    rows = []
    for item in order.items:
        shipped = shipped_qty_by_order_item(db, item.id)
        ordered = Decimal(str(item.quantity))
        rows.append(
            {
                "order_item_id": item.id,
                "sku": item.sku_snapshot,
                "description": item.description_snapshot,
                "ordered_qty": ordered,
                "shipped_qty": shipped,
                "residual_qty": ordered - shipped,
            }
        )
    return rows


def physical_totals_derived(db: Session, shipment_id: int) -> dict:
    s = get_shipment(db, shipment_id)
    net = Decimal("0")
    gross = Decimal("0")
    volume = Decimal("0")
    pallet_count = 0
    carton_count = 0
    box_count = 0
    package_rows = 0
    for p in s.packages:
        package_rows += 1
        c = Decimal(p.package_count)
        if p.net_weight_kg is not None:
            net += Decimal(str(p.net_weight_kg)) * c
        if p.gross_weight_kg is not None:
            gross += Decimal(str(p.gross_weight_kg)) * c
        if p.volume_m3 is not None:
            volume += Decimal(str(p.volume_m3)) * c
        if p.package_type == "PALLET":
            pallet_count += p.package_count
        elif p.package_type == "CARTON":
            carton_count += p.package_count
        elif p.package_type == "BOX":
            box_count += p.package_count
    return {
        "net_weight_kg": net,
        "gross_weight_kg": gross,
        "volume_m3": volume,
        "pallet_count": pallet_count,
        "carton_count": carton_count,
        "box_count": box_count,
        "package_row_count": package_rows,
    }


def declared_totals_by_document(db: Session, shipment_id: int) -> list[dict]:
    s = get_shipment(db, shipment_id)
    return [
        {
            "id": row.id,
            "document_id": row.document_id,
            "declared_net_weight_kg": row.declared_net_weight_kg,
            "declared_gross_weight_kg": row.declared_gross_weight_kg,
            "declared_pallet_count": row.declared_pallet_count,
            "declared_carton_count": row.declared_carton_count,
            "declared_volume_m3": row.declared_volume_m3,
            "raw_notes": row.raw_notes,
        }
        for row in s.document_summaries
    ]


def physical_divergences(db: Session, shipment_id: int) -> list[dict]:
    derived = physical_totals_derived(db, shipment_id)
    out = []
    for row in declared_totals_by_document(db, shipment_id):
        diffs = []
        pairs = [
            ("net_weight_kg", row["declared_net_weight_kg"], derived["net_weight_kg"], "weight"),
            ("gross_weight_kg", row["declared_gross_weight_kg"], derived["gross_weight_kg"], "weight"),
            ("volume_m3", row["declared_volume_m3"], derived["volume_m3"], "volume"),
            ("pallet_count", row["declared_pallet_count"], derived["pallet_count"], "count"),
            ("carton_count", row["declared_carton_count"], derived["carton_count"], "count"),
        ]
        any_sig = False
        for field, decl, der, kind in pairs:
            if decl is None:
                continue
            d_dec = Decimal(str(decl)) if not isinstance(decl, int) else decl
            if kind == "weight":
                sig = divergence.weight_significant(
                    Decimal(str(decl)), Decimal(str(der))
                )
            elif kind == "volume":
                sig = divergence.volume_significant(
                    Decimal(str(decl)), Decimal(str(der))
                )
            else:
                sig = divergence.count_significant(int(decl), int(der))
            if sig:
                any_sig = True
            diffs.append(
                {
                    "field": field,
                    "declared": decl,
                    "derived": der if not isinstance(der, Decimal) else str(der),
                    "is_significant": sig,
                }
            )
        out.append(
            {
                "document_id": row["document_id"],
                "summary_id": row["id"],
                "diffs": diffs,
                "is_significant": any_sig,
            }
        )
    return out


def allocation_bases(db: Session, shipment_id: int) -> dict:
    s = get_shipment(db, shipment_id)
    phys = physical_totals_derived(db, shipment_id)
    items = [
        {
            "shipment_item_id": i.id,
            "order_item_id": i.order_item_id,
            "quantity": str(i.quantity),
        }
        for i in s.items
    ]
    return {
        "shipment_id": s.id,
        "items": items,
        "physical": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in phys.items()},
        "packages": [
            {
                "id": p.id,
                "package_type": p.package_type,
                "package_count": p.package_count,
                "net_weight_kg": str(p.net_weight_kg) if p.net_weight_kg is not None else None,
                "gross_weight_kg": str(p.gross_weight_kg) if p.gross_weight_kg is not None else None,
                "volume_m3": str(p.volume_m3) if p.volume_m3 is not None else None,
            }
            for p in s.packages
        ],
    }


def order_item_candidates(
    db: Session,
    *,
    order_id: int | None = None,
    order_code: str | None = None,
    external_ref: str | None = None,
    sku: str | None = None,
    supplier_id: int | None = None,
    limit: int = 50,
) -> list[dict]:
    if not any([order_id, order_code, external_ref]):
        raise ShipmentValidationError(
            "Informe order_id, order_code ou external_ref (SKU isolado não é permitido)",
            code="candidates_scope_required",
        )
    pairs = orders_public.find_confirmed_order_items(
        db,
        order_id=order_id,
        order_code=order_code,
        external_ref=external_ref,
        sku=sku,
        supplier_id=supplier_id,
        limit=limit,
    )
    rows = []
    for order, item in pairs:
        shipped = shipped_qty_by_order_item(db, item.id)
        ordered = Decimal(str(item.quantity))
        residual = ordered - shipped
        if residual <= 0:
            continue
        rows.append(
            {
                "order_id": order.id,
                "order_code": order.code,
                "external_ref": order.external_ref,
                "supplier_id": order.supplier_id,
                "order_item_id": item.id,
                "sku": item.sku_snapshot,
                "description": item.description_snapshot,
                "ordered_qty": str(ordered),
                "shipped_qty": str(shipped),
                "residual_qty": str(residual),
            }
        )
    return rows
