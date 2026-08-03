"""Customs nationalization commands — I5-4. Caller owns UoW.

Nationalization NÃO cria StockBalance; GoodsReceipt domestic consome residual.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.customs import repository as repo
from app.customs.errors import (
    NationalizationConflict,
    NationalizationImmutable,
    NationalizationNotFound,
    NationalizationValidationError,
    OverNationalizationError,
    ProcessImmutable,
    ProcessNotFound,
)
from app.customs.models import Nationalization, NationalizationItem


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _opt_str(value: str | None, *, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        raise NationalizationValidationError(
            f"Texto excede {max_len} caracteres", code="text_too_long"
        )
    return s


def _req_dec(value: str | Decimal | None, *, field: str) -> Decimal:
    if value is None or str(value).strip() == "":
        raise NationalizationValidationError(f"{field} obrigatório", code="validation_error")
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise NationalizationValidationError(
            f"Decimal inválido: {value}", code="invalid_decimal"
        ) from exc
    if d <= 0:
        raise NationalizationValidationError(
            f"{field} deve ser > 0", code="invalid_quantity"
        )
    return d


def _require_process(db: Session, process_id: int):
    p = repo.get_process_for_update(db, process_id)
    if not p:
        raise ProcessNotFound(process_id)
    if p.status == "CANCELLED":
        raise ProcessImmutable("Processo cancelado")
    return p


def _require_nat(db: Session, nat_id: int) -> Nationalization:
    n = repo.get_nationalization_for_update(db, nat_id)
    if not n:
        raise NationalizationNotFound(nat_id)
    return n


def _check_ver(n: Nationalization, expected_version: int) -> None:
    if n.version != expected_version:
        raise NationalizationConflict()


def _bump(n: Nationalization) -> None:
    n.version += 1


def _assert_draft(n: Nationalization) -> None:
    if n.status != "DRAFT":
        raise NationalizationImmutable(f"Nationalization {n.status} não permite edição")


def create_nationalization(
    db: Session,
    process_id: int,
    *,
    reference: str | None = None,
    notes: str | None = None,
) -> Nationalization:
    process = _require_process(db, process_id)
    if process.status == "DRAFT":
        raise NationalizationValidationError(
            "Submeta o ImportProcess antes de nacionalizar",
            code="process_not_submitted",
        )
    if process.status == "CLEARED":
        raise NationalizationValidationError(
            "Processo já totalmente liberado",
            code="process_already_cleared",
        )
    nat = Nationalization(
        process_id=process.id,
        reference=_opt_str(reference, max_len=128),
        status="DRAFT",
        version=1,
        notes=_opt_str(notes),
    )
    db.add(nat)
    db.flush()
    return repo.get_nationalization(db, nat.id)  # type: ignore[return-value]


def add_nationalization_items(
    db: Session,
    nationalization_id: int,
    *,
    expected_version: int,
    items: list[dict[str, Any]],
) -> Nationalization:
    nat = _require_nat(db, nationalization_id)
    _check_ver(nat, expected_version)
    _assert_draft(nat)
    _require_process(db, nat.process_id)

    if not items:
        raise NationalizationValidationError("Informe ao menos um item", code="empty_items")

    for raw in items:
        qty = _req_dec(raw.get("quantity"), field="quantity")
        dog_line_id = raw.get("doganale_line_id")
        inv_item_id = raw.get("invoice_item_id")
        shp_item_id = raw.get("shipment_item_id")
        product_id = raw.get("product_id")
        if not any([dog_line_id, inv_item_id, shp_item_id, product_id]):
            raise NationalizationValidationError(
                "Item exige doganale_line_id, invoice_item_id, shipment_item_id ou product_id",
                code="missing_source",
            )

        # Resolve product when possible
        resolved_product = product_id
        if dog_line_id is not None:
            line = repo.get_doganale_line(db, int(dog_line_id))
            if not line:
                raise NationalizationValidationError(
                    f"Doganale line {dog_line_id} não encontrada",
                    code="doganale_line_not_found",
                )
            if line.product_id and not resolved_product:
                resolved_product = line.product_id
            cap = line.quantity
            if cap is not None:
                used = repo.sum_confirmed_nationalized(
                    db, doganale_line_id=int(dog_line_id), exclude_nationalization_id=nat.id
                )
                draft_same = sum(
                    Decimal(str(i.quantity))
                    for i in nat.items
                    if i.doganale_line_id == int(dog_line_id)
                )
                if used + draft_same + qty > Decimal(str(cap)):
                    raise OverNationalizationError(
                        f"Doganale line {dog_line_id}: {used + draft_same + qty} > {cap}"
                    )

        if inv_item_id is not None:
            allocated = repo.sum_allocated_invoice_item(db, int(inv_item_id))
            if allocated <= 0:
                # allow using invoice item qty via billing if not allocated? Prefer allocated.
                raise NationalizationValidationError(
                    f"Invoice item {inv_item_id} sem alocação no processo",
                    code="invoice_item_not_allocated",
                )
            used = repo.sum_confirmed_nationalized(
                db, invoice_item_id=int(inv_item_id), exclude_nationalization_id=nat.id
            )
            draft_same = sum(
                Decimal(str(i.quantity))
                for i in nat.items
                if i.invoice_item_id == int(inv_item_id)
            )
            if used + draft_same + qty > allocated:
                raise OverNationalizationError(
                    f"Invoice item {inv_item_id}: {used + draft_same + qty} > {allocated}"
                )

        if shp_item_id is not None:
            allocated = repo.sum_allocated_shipment_item(db, int(shp_item_id))
            if allocated <= 0:
                raise NationalizationValidationError(
                    f"Shipment item {shp_item_id} sem alocação no processo",
                    code="shipment_item_not_allocated",
                )
            used = repo.sum_confirmed_nationalized(
                db, shipment_item_id=int(shp_item_id), exclude_nationalization_id=nat.id
            )
            draft_same = sum(
                Decimal(str(i.quantity))
                for i in nat.items
                if i.shipment_item_id == int(shp_item_id)
            )
            if used + draft_same + qty > allocated:
                raise OverNationalizationError(
                    f"Shipment item {shp_item_id}: {used + draft_same + qty} > {allocated}"
                )

        if resolved_product is not None:
            try:
                catalog_public.get_product(db, int(resolved_product))
            except Exception as exc:
                raise NationalizationValidationError(
                    f"Produto {resolved_product} não encontrado",
                    code="product_not_found",
                ) from exc

        db.add(
            NationalizationItem(
                nationalization_id=nat.id,
                doganale_line_id=int(dog_line_id) if dog_line_id is not None else None,
                invoice_item_id=int(inv_item_id) if inv_item_id is not None else None,
                shipment_item_id=int(shp_item_id) if shp_item_id is not None else None,
                product_id=int(resolved_product) if resolved_product is not None else None,
                quantity=qty,
                notes=_opt_str(raw.get("notes")),
            )
        )

    _bump(nat)
    db.flush()
    return repo.get_nationalization(db, nat.id)  # type: ignore[return-value]


def _capacity_for_process_residual(db: Session, process_id: int) -> Decimal:
    """Capacidade total alocada (shipment items preferidos; senão invoice items)."""
    process = repo.get_process(db, process_id)
    if not process:
        return Decimal("0")
    total = Decimal("0")
    if process.shipment_items:
        for a in process.shipment_items:
            total += Decimal(str(a.allocated_qty))
        return total
    for a in process.invoice_items:
        total += Decimal(str(a.allocated_qty))
    return total


def _confirmed_cleared_qty(db: Session, process_id: int) -> Decimal:
    nats = repo.list_nationalizations(db, process_id)
    total = Decimal("0")
    for n in nats:
        if n.status != "CONFIRMED":
            continue
        for it in n.items:
            total += Decimal(str(it.quantity))
    return total


def _refresh_process_clearance_status(db: Session, process_id: int) -> None:
    process = repo.get_process_for_update(db, process_id)
    if not process or process.status in ("CANCELLED", "DRAFT"):
        return
    cleared = _confirmed_cleared_qty(db, process_id)
    capacity = _capacity_for_process_residual(db, process_id)
    if capacity <= 0:
        # Sem alocação explícita: se há nationalization confirmada → PARTIALLY_CLEARED
        if cleared > 0:
            process.status = "PARTIALLY_CLEARED"
        return
    if cleared <= 0:
        if process.status in ("PARTIALLY_CLEARED", "CLEARED", "IN_CLEARANCE"):
            process.status = "SUBMITTED"
        return
    if cleared >= capacity:
        process.status = "CLEARED"
    else:
        process.status = "PARTIALLY_CLEARED"
    process.version += 1
    db.flush()


def confirm_nationalization(
    db: Session,
    nationalization_id: int,
    *,
    expected_version: int,
) -> Nationalization:
    nat = _require_nat(db, nationalization_id)
    _check_ver(nat, expected_version)
    _assert_draft(nat)
    _require_process(db, nat.process_id)

    if not nat.items:
        raise NationalizationValidationError(
            "Nationalization sem itens", code="empty_items"
        )

    # Re-validate caps against confirmed peers
    for it in nat.items:
        qty = Decimal(str(it.quantity))
        if it.doganale_line_id is not None:
            line = repo.get_doganale_line(db, it.doganale_line_id)
            if line and line.quantity is not None:
                used = repo.sum_confirmed_nationalized(
                    db, doganale_line_id=it.doganale_line_id
                )
                if used + qty > Decimal(str(line.quantity)):
                    raise OverNationalizationError(
                        f"Doganale line {it.doganale_line_id} oversubscribed"
                    )
        if it.invoice_item_id is not None:
            allocated = repo.sum_allocated_invoice_item(db, it.invoice_item_id)
            used = repo.sum_confirmed_nationalized(db, invoice_item_id=it.invoice_item_id)
            if used + qty > allocated:
                raise OverNationalizationError(
                    f"Invoice item {it.invoice_item_id} oversubscribed"
                )
        if it.shipment_item_id is not None:
            allocated = repo.sum_allocated_shipment_item(db, it.shipment_item_id)
            used = repo.sum_confirmed_nationalized(db, shipment_item_id=it.shipment_item_id)
            if used + qty > allocated:
                raise OverNationalizationError(
                    f"Shipment item {it.shipment_item_id} oversubscribed"
                )

    nat.status = "CONFIRMED"
    nat.confirmed_at = _now()
    _bump(nat)
    db.flush()
    _refresh_process_clearance_status(db, nat.process_id)
    return repo.get_nationalization(db, nat.id)  # type: ignore[return-value]


def reverse_nationalization(
    db: Session,
    nationalization_id: int,
    *,
    expected_version: int,
) -> Nationalization:
    nat = _require_nat(db, nationalization_id)
    _check_ver(nat, expected_version)
    if nat.status != "CONFIRMED":
        raise NationalizationImmutable("Somente CONFIRMED pode ser revertida")
    _require_process(db, nat.process_id)

    nat.status = "REVERSED"
    nat.reversed_at = _now()
    _bump(nat)
    db.flush()
    _refresh_process_clearance_status(db, nat.process_id)
    return repo.get_nationalization(db, nat.id)  # type: ignore[return-value]


def nationalize(
    db: Session,
    nationalization_id: int,
    *,
    expected_version: int,
) -> Nationalization:
    """Alias público Blueprint — confirma liberação (não cria estoque)."""
    return confirm_nationalization(
        db, nationalization_id, expected_version=expected_version
    )


def clearance_residuals(db: Session, process_id: int) -> list[dict]:
    """Residual nacionalizável por shipment_item alocado (fallback invoice_item)."""
    process = repo.get_process(db, process_id)
    if not process:
        raise ProcessNotFound(process_id)
    rows: list[dict] = []
    if process.shipment_items:
        for a in process.shipment_items:
            used = repo.sum_confirmed_nationalized(db, shipment_item_id=a.shipment_item_id)
            cap = Decimal(str(a.allocated_qty))
            rows.append(
                {
                    "source_kind": "shipment_item",
                    "shipment_item_id": a.shipment_item_id,
                    "allocated_qty": str(cap),
                    "nationalized_qty": str(used),
                    "residual_qty": str(cap - used),
                }
            )
        return rows
    for a in process.invoice_items:
        used = repo.sum_confirmed_nationalized(db, invoice_item_id=a.invoice_item_id)
        cap = Decimal(str(a.allocated_qty))
        rows.append(
            {
                "source_kind": "invoice_item",
                "invoice_item_id": a.invoice_item_id,
                "allocated_qty": str(cap),
                "nationalized_qty": str(used),
                "residual_qty": str(cap - used),
            }
        )
    return rows
