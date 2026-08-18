"""Inventory commands — I5-4. Caller owns UoW.

Regras:
- ARRIVED sozinho NÃO cria stock
- BONDED_IN pode preceder nacionalização
- DOMESTIC_IN / RECLASS exigem nacionalização cobrindo qty
- Movimentos append-only; reverse = movimento inverso
- StockBalance só via post/rebuild
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.customs import public as customs_public
from app.inventory import repository as repo
from app.inventory.errors import (
    InventoryValidationError,
    LocationNotFound,
    NationalizationRequired,
    OverReceiptError,
    ReceiptConflict,
    ReceiptImmutable,
    ReceiptNotFound,
)
from app.inventory.models import GoodsReceipt, GoodsReceiptLine, InventoryMovement, StockBalance


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _req_dec(value: str | Decimal | None, *, field: str) -> Decimal:
    if value is None or str(value).strip() == "":
        raise InventoryValidationError(f"{field} obrigatório", code="validation_error")
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise InventoryValidationError(
            f"Decimal inválido: {value}", code="invalid_decimal"
        ) from exc
    if d <= 0:
        raise InventoryValidationError(f"{field} deve ser > 0", code="invalid_quantity")
    return d


def _opt_str(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s or None


def _require_receipt(db: Session, receipt_id: int) -> GoodsReceipt:
    r = repo.get_receipt_for_update(db, receipt_id)
    if not r:
        raise ReceiptNotFound(receipt_id)
    return r


def _check_ver(r: GoodsReceipt, expected_version: int) -> None:
    if r.version != expected_version:
        raise ReceiptConflict()


def _bump(r: GoodsReceipt) -> None:
    r.version += 1


def _assert_draft(r: GoodsReceipt) -> None:
    if r.status != "DRAFT":
        raise ReceiptImmutable(f"Receipt {r.status} não permite edição")


def _movement_type_for_receipt(receipt_type: str, location_type: str) -> str:
    if receipt_type == "BONDED_IN":
        return "BONDED_IN"
    if receipt_type == "DOMESTIC_IN":
        return "DOMESTIC_IN"
    if receipt_type == "RECLASS":
        return "RECLASS_IN"
    if receipt_type == "ADJUSTMENT":
        return "ADJUSTMENT"
    if location_type == "QUARANTINE":
        return "QUARANTINE_IN"
    return "ADJUSTMENT"


_FROM_LOC_MARKER = "from_location_code="


def _encode_from_location(notes: str | None, from_code: str) -> str:
    base = (notes or "").strip()
    marker = f"{_FROM_LOC_MARKER}{from_code}"
    return f"{marker}\n{base}" if base else marker


def _decode_from_location(notes: str | None) -> tuple[str | None, str | None]:
    if not notes:
        return None, None
    if notes.startswith(_FROM_LOC_MARKER):
        first, _, rest = notes.partition("\n")
        code = first[len(_FROM_LOC_MARKER) :].strip() or None
        return code, (rest.strip() or None)
    return None, notes


def create_receipt(
    db: Session,
    *,
    location_id: int | None = None,
    location_code: str | None = None,
    from_location_code: str | None = None,
    process_id: int | None = None,
    nationalization_id: int | None = None,
    receipt_type: str,
    document_id: int | None = None,
    notes: str | None = None,
) -> GoodsReceipt:
    repo.ensure_default_locations(db)
    if receipt_type not in ("BONDED_IN", "DOMESTIC_IN", "RECLASS", "ADJUSTMENT"):
        raise InventoryValidationError(
            f"receipt_type inválido: {receipt_type}", code="invalid_receipt_type"
        )

    loc = None
    if location_id is not None:
        loc = repo.get_location(db, location_id)
    elif location_code:
        loc = repo.get_location_by_code(db, location_code)
    if not loc:
        raise LocationNotFound(location_id or location_code or "?")

    if receipt_type == "BONDED_IN" and loc.location_type != "BONDED":
        raise InventoryValidationError(
            "BONDED_IN exige location BONDED", code="location_type_mismatch"
        )
    if receipt_type == "DOMESTIC_IN" and loc.location_type != "DOMESTIC":
        raise InventoryValidationError(
            "DOMESTIC_IN exige location DOMESTIC", code="location_type_mismatch"
        )
    if receipt_type == "RECLASS" and loc.location_type != "DOMESTIC":
        raise InventoryValidationError(
            "RECLASS exige location destino DOMESTIC", code="location_type_mismatch"
        )

    stored_notes = _opt_str(notes)
    if receipt_type == "RECLASS":
        src_code = (from_location_code or "BONDED-MAIN").strip()
        src = repo.get_location_by_code(db, src_code)
        if not src or src.location_type != "BONDED":
            raise InventoryValidationError(
                f"RECLASS exige origem BONDED ({src_code})",
                code="location_type_mismatch",
            )
        stored_notes = _encode_from_location(stored_notes, src.code)

    if process_id is not None:
        try:
            customs_public.get_import_process(db, process_id)
        except customs_public.CustomsError as exc:
            raise InventoryValidationError(str(exc), code="process_not_found") from exc

    if nationalization_id is not None:
        nat = customs_public.get_nationalization(db, nationalization_id)
        if nat.status != "CONFIRMED" and receipt_type in ("DOMESTIC_IN", "RECLASS"):
            raise NationalizationRequired(
                "Nationalization deve estar CONFIRMED para receipt doméstico"
            )

    receipt = GoodsReceipt(
        location_id=loc.id,
        process_id=process_id,
        nationalization_id=nationalization_id,
        receipt_type=receipt_type,
        status="DRAFT",
        version=1,
        document_id=document_id,
        notes=stored_notes,
    )
    db.add(receipt)
    db.flush()
    return repo.get_receipt(db, receipt.id)  # type: ignore[return-value]


def add_receipt_lines(
    db: Session,
    receipt_id: int,
    *,
    expected_version: int,
    lines: list[dict[str, Any]],
) -> GoodsReceipt:
    receipt = _require_receipt(db, receipt_id)
    _check_ver(receipt, expected_version)
    _assert_draft(receipt)

    if not lines:
        raise InventoryValidationError("Informe ao menos uma linha", code="empty_lines")

    for raw in lines:
        product_id = raw.get("product_id")
        if product_id is None:
            raise InventoryValidationError("product_id obrigatório", code="validation_error")
        try:
            catalog_public.get_product(db, int(product_id))
        except Exception as exc:
            raise InventoryValidationError(
                f"Produto {product_id} não encontrado", code="product_not_found"
            ) from exc
        qty = _req_dec(raw.get("quantity"), field="quantity")
        nat_item_id = raw.get("nationalization_item_id")
        shp_item_id = raw.get("shipment_item_id")

        if receipt.receipt_type in ("DOMESTIC_IN", "RECLASS"):
            if nat_item_id is None:
                raise NationalizationRequired(
                    "Linha doméstica exige nationalization_item_id"
                )
            nat_item = customs_public.get_nationalization_item(db, int(nat_item_id))
            if nat_item is None:
                raise NationalizationRequired(
                    f"NationalizationItem {nat_item_id} não encontrado"
                )
            if nat_item.product_id is not None and int(product_id) != int(nat_item.product_id):
                raise InventoryValidationError(
                    "O produto da linha não coincide com o item da liberação",
                    code="product_mismatch",
                )
            if (
                receipt.nationalization_id is not None
                and int(nat_item.nationalization_id) != int(receipt.nationalization_id)
            ):
                raise InventoryValidationError(
                    "O item da liberação não pertence ao recebimento",
                    code="validation_error",
                )

        db.add(
            GoodsReceiptLine(
                receipt_id=receipt.id,
                product_id=int(product_id),
                quantity=qty,
                nationalization_item_id=int(nat_item_id) if nat_item_id is not None else None,
                shipment_item_id=int(shp_item_id) if shp_item_id is not None else None,
                notes=_opt_str(raw.get("notes")),
            )
        )

    _bump(receipt)
    db.flush()
    return repo.get_receipt(db, receipt.id)  # type: ignore[return-value]


def _assert_domestic_coverage(db: Session, receipt: GoodsReceipt) -> None:
    """Domestic/reclass: qty ≤ residual do mesmo nationalization_item_id (item-level)."""
    for line in receipt.lines:
        qty = Decimal(str(line.quantity))
        if line.nationalization_item_id is None:
            raise NationalizationRequired(
                "Linha doméstica exige nationalization_item_id"
            )
        nat_item = customs_public.get_nationalization_item(db, line.nationalization_item_id)
        if nat_item is None:
            raise NationalizationRequired(
                f"NationalizationItem {line.nationalization_item_id} não encontrado"
            )
        if nat_item.product_id is not None and int(line.product_id) != int(nat_item.product_id):
            raise InventoryValidationError(
                "O produto da linha não coincide com o item da liberação",
                code="product_mismatch",
            )
        nat = customs_public.get_nationalization(db, nat_item.nationalization_id)
        if nat.status != "CONFIRMED":
            raise NationalizationRequired(
                f"Nationalization {nat.id} não está CONFIRMED"
            )
        cleared = Decimal(str(nat_item.quantity))
        used = repo.sum_domestic_received_for_nat_item(db, line.nationalization_item_id)
        if used + qty > cleared:
            raise OverReceiptError(
                f"Nat item {line.nationalization_item_id}: "
                f"{used + qty} > nacionalizado {cleared}"
            )


def confirm_receipt(
    db: Session,
    receipt_id: int,
    *,
    expected_version: int,
) -> GoodsReceipt:
    receipt = _require_receipt(db, receipt_id)
    _check_ver(receipt, expected_version)
    _assert_draft(receipt)

    loaded = repo.get_receipt(db, receipt_id)
    if not loaded or not loaded.lines:
        raise InventoryValidationError("Receipt sem linhas", code="empty_lines")

    loc = repo.get_location(db, receipt.location_id)
    if not loc:
        raise LocationNotFound(receipt.location_id)

    if receipt.receipt_type in ("DOMESTIC_IN", "RECLASS"):
        _assert_domestic_coverage(db, loaded)

    if receipt.receipt_type == "RECLASS":
        from_code, _ = _decode_from_location(receipt.notes)
        from_code = from_code or "BONDED-MAIN"
        from_loc = repo.get_location_by_code(db, from_code)
        if not from_loc or from_loc.location_type != "BONDED":
            raise InventoryValidationError(
                f"RECLASS origem BONDED inválida: {from_code}",
                code="location_type_mismatch",
            )
        for line in loaded.lines:
            delta = Decimal(str(line.quantity))
            bal = repo.get_balance(
                db, location_id=from_loc.id, product_id=line.product_id
            )
            have = Decimal(str(bal.qty)) if bal else Decimal("0")
            if have < delta:
                raise InventoryValidationError(
                    f"Saldo BONDED insuficiente para produto {line.product_id}: "
                    f"tem {have}, precisa {delta}",
                    code="insufficient_bonded",
                )
            mov_out = InventoryMovement(
                location_id=from_loc.id,
                product_id=line.product_id,
                quantity_delta=-delta,
                movement_type="RECLASS_OUT",
                receipt_line_id=line.id,
                nationalization_item_id=line.nationalization_item_id,
                reason=f"receipt:{receipt.id}:reclass_out",
            )
            db.add(mov_out)
            repo.apply_balance_delta(
                db,
                location_id=from_loc.id,
                product_id=line.product_id,
                delta=-delta,
            )
            mov_in = InventoryMovement(
                location_id=receipt.location_id,
                product_id=line.product_id,
                quantity_delta=delta,
                movement_type="RECLASS_IN",
                receipt_line_id=line.id,
                nationalization_item_id=line.nationalization_item_id,
                reason=f"receipt:{receipt.id}:reclass_in",
            )
            db.add(mov_in)
            repo.apply_balance_delta(
                db,
                location_id=receipt.location_id,
                product_id=line.product_id,
                delta=delta,
            )
    else:
        mov_type = _movement_type_for_receipt(receipt.receipt_type, loc.location_type)
        for line in loaded.lines:
            delta = Decimal(str(line.quantity))
            mov = InventoryMovement(
                location_id=receipt.location_id,
                product_id=line.product_id,
                quantity_delta=delta,
                movement_type=mov_type,
                receipt_line_id=line.id,
                nationalization_item_id=line.nationalization_item_id,
                reason=f"receipt:{receipt.id}",
            )
            db.add(mov)
            repo.apply_balance_delta(
                db,
                location_id=receipt.location_id,
                product_id=line.product_id,
                delta=delta,
            )

    receipt.status = "CONFIRMED"
    receipt.received_at = _now()
    _bump(receipt)
    db.flush()
    return repo.get_receipt(db, receipt.id)  # type: ignore[return-value]


def reverse_receipt(
    db: Session,
    receipt_id: int,
    *,
    expected_version: int,
    reason: str | None = None,
) -> GoodsReceipt:
    receipt = _require_receipt(db, receipt_id)
    _check_ver(receipt, expected_version)
    if receipt.status != "CONFIRMED":
        raise ReceiptImmutable("Somente CONFIRMED pode ser revertido")

    loaded = repo.get_receipt(db, receipt_id)
    assert loaded is not None
    # Find movements posted by this receipt's lines and reverse them
    for line in loaded.lines:
        originals = (
            db.query(InventoryMovement)
            .filter(
                InventoryMovement.receipt_line_id == line.id,
                InventoryMovement.reversal_of_id.is_(None),
                InventoryMovement.movement_type != "REVERSAL",
            )
            .all()
        )
        for orig in originals:
            # skip if already reversed
            existing_rev = (
                db.query(InventoryMovement)
                .filter(InventoryMovement.reversal_of_id == orig.id)
                .first()
            )
            if existing_rev:
                continue
            inv = InventoryMovement(
                location_id=orig.location_id,
                product_id=orig.product_id,
                quantity_delta=-Decimal(str(orig.quantity_delta)),
                movement_type="REVERSAL",
                receipt_line_id=line.id,
                nationalization_item_id=orig.nationalization_item_id,
                reversal_of_id=orig.id,
                reason=_opt_str(reason) or f"reverse receipt:{receipt.id}",
            )
            db.add(inv)
            repo.apply_balance_delta(
                db,
                location_id=orig.location_id,
                product_id=orig.product_id,
                delta=-Decimal(str(orig.quantity_delta)),
            )

    receipt.status = "REVERSED"
    _bump(receipt)
    db.flush()
    return repo.get_receipt(db, receipt.id)  # type: ignore[return-value]


def record_receipt(
    db: Session,
    *,
    location_code: str,
    receipt_type: str,
    lines: list[dict[str, Any]],
    process_id: int | None = None,
    nationalization_id: int | None = None,
    notes: str | None = None,
) -> GoodsReceipt:
    """Convenience: create + add lines + confirm."""
    r = create_receipt(
        db,
        location_code=location_code,
        process_id=process_id,
        nationalization_id=nationalization_id,
        receipt_type=receipt_type,
        notes=notes,
    )
    r = add_receipt_lines(db, r.id, expected_version=r.version, lines=lines)
    return confirm_receipt(db, r.id, expected_version=r.version)


def record_adjustment(
    db: Session,
    *,
    location_code: str,
    product_id: int,
    quantity_delta: str | Decimal,
    movement_type: str = "ADJUSTMENT",
    reason: str | None = None,
) -> InventoryMovement:
    """Ajuste direto (shortage/surplus/damage/quarantine/adjustment)."""
    repo.ensure_default_locations(db)
    loc = repo.get_location_by_code(db, location_code)
    if not loc:
        raise LocationNotFound(location_code)
    if movement_type not in (
        "ADJUSTMENT",
        "SHORTAGE",
        "SURPLUS",
        "DAMAGE",
        "QUARANTINE_IN",
        "QUARANTINE_OUT",
    ):
        raise InventoryValidationError(
            f"movement_type inválido para ajuste: {movement_type}",
            code="invalid_movement_type",
        )
    try:
        catalog_public.get_product(db, int(product_id))
    except Exception as exc:
        raise InventoryValidationError(
            f"Produto {product_id} não encontrado", code="product_not_found"
        ) from exc

    try:
        delta = Decimal(str(quantity_delta))
    except (InvalidOperation, ValueError) as exc:
        raise InventoryValidationError(
            f"Decimal inválido: {quantity_delta}", code="invalid_decimal"
        ) from exc
    if delta == 0:
        raise InventoryValidationError("quantity_delta não pode ser 0", code="invalid_quantity")

    if movement_type == "SHORTAGE" and delta > 0:
        delta = -delta
    if movement_type == "SURPLUS" and delta < 0:
        delta = abs(delta)
    if movement_type == "DAMAGE" and delta > 0:
        delta = -delta

    mov = InventoryMovement(
        location_id=loc.id,
        product_id=int(product_id),
        quantity_delta=delta,
        movement_type=movement_type,
        reason=_opt_str(reason),
    )
    db.add(mov)
    repo.apply_balance_delta(
        db, location_id=loc.id, product_id=int(product_id), delta=delta
    )
    db.flush()
    return mov


def rebuild_stock_balances(db: Session, *, product_id: int | None = None) -> int:
    """Rebuild StockBalance cache from movements. Returns number of balance rows."""
    if product_id is not None:
        db.query(StockBalance).filter(StockBalance.product_id == product_id).delete()
        pairs = (
            db.query(InventoryMovement.location_id, InventoryMovement.product_id)
            .filter(InventoryMovement.product_id == product_id)
            .distinct()
            .all()
        )
    else:
        repo.clear_all_balances(db)
        pairs = (
            db.query(InventoryMovement.location_id, InventoryMovement.product_id)
            .distinct()
            .all()
        )
    count = 0
    for loc_id, prod_id in pairs:
        total = repo.sum_movements(db, location_id=loc_id, product_id=prod_id)
        db.add(StockBalance(location_id=loc_id, product_id=prod_id, qty=total))
        count += 1
    db.flush()
    return count
