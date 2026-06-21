from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import AllocationMethod, LandedCostComponentType, LandedCostVersionType
from app.models import (
    Expense,
    ImportationItem,
    LandedCostComponent,
    LandedCostSkuAllocation,
    LandedCostVariance,
    LandedCostVersion,
    Product,
    Tax,
)
from app.services.auth import write_audit_log


class LandedCostError(Exception):
    pass


def _d(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _next_version_number(db: Session, importation_id: int) -> int:
    current = (
        db.query(LandedCostVersion)
        .filter(LandedCostVersion.importation_id == importation_id)
        .order_by(LandedCostVersion.version_number.desc())
        .first()
    )
    return (current.version_number + 1) if current else 1


def gather_components(db: Session, importation_id: int) -> list[tuple[str, Decimal, str | None]]:
    components: list[tuple[str, Decimal, str | None]] = []
    items = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    fob = sum(
        _d(item.unit_price_foreign) * _d(Decimal(item.quantity_ordered or 0))
        for item in items
        if item.quantity_ordered and item.unit_price_foreign
    )
    if fob > 0:
        components.append((LandedCostComponentType.FOB.value, fob, "importation_items"))

    for exp in (
        db.query(Expense)
        .filter(Expense.importation_id == importation_id, Expense.is_active.is_(True))
        .all()
    ):
        if exp.amount is None:
            continue
        ctype = LandedCostComponentType.BRAZIL_EXPENSE.value
        if exp.expense_type == "CUSTOMS_AGENT":
            ctype = LandedCostComponentType.CUSTOMS_AGENT.value
        elif exp.expense_type == "FREIGHT":
            ctype = LandedCostComponentType.FREIGHT.value
        elif exp.expense_type == "INSURANCE":
            ctype = LandedCostComponentType.INSURANCE.value
        elif exp.expense_type == "BANK_FEE":
            ctype = LandedCostComponentType.BANK_FEE.value
        elif exp.expense_type == "STORAGE":
            ctype = LandedCostComponentType.STORAGE.value
        components.append((ctype, exp.amount, f"expense:{exp.id}"))

    for tax in db.query(Tax).filter(Tax.importation_id == importation_id, Tax.is_active.is_(True)).all():
        components.append((LandedCostComponentType.TAX.value, tax.amount, f"tax:{tax.id}"))

    return components


def _allocation_weights(
    db: Session,
    items: list[ImportationItem],
    method: str,
    manual: dict[int, Decimal] | None = None,
) -> dict[int, Decimal]:
    if method == AllocationMethod.MANUAL.value:
        if not manual:
            raise LandedCostError("Rateio manual exige valores por item")
        return manual

    weights: dict[int, Decimal] = {}
    if method == AllocationMethod.EQUAL.value:
        for item in items:
            weights[item.id] = Decimal("1")
        return weights

    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first() if item.product_id else None
        qty = Decimal(item.quantity_ordered or 0)
        price = _d(item.unit_price_foreign)
        if method == AllocationMethod.VALUE.value:
            weights[item.id] = qty * price
        elif method == AllocationMethod.QUANTITY.value:
            weights[item.id] = qty
        elif method == AllocationMethod.WEIGHT.value:
            weights[item.id] = _d(product.weight_kg if product else None) * qty
        elif method == AllocationMethod.VOLUME.value:
            weights[item.id] = _d(product.volume_m3 if product else None) * qty
        else:
            weights[item.id] = qty * price
    return weights


def create_landed_cost_version(
    db: Session,
    *,
    importation_id: int,
    version_type: str,
    allocation_method: str,
    user_id: int | None,
    trigger_event: str | None = None,
    trigger_notes: str | None = None,
    manual_allocations: dict[int, Decimal] | None = None,
    manual_reason_code_id: int | None = None,
    manual_justification: str | None = None,
) -> LandedCostVersion:
    if allocation_method == AllocationMethod.MANUAL.value:
        if not manual_reason_code_id and not (manual_justification or "").strip():
            raise LandedCostError("Rateio manual exige motivo")

    previous = (
        db.query(LandedCostVersion)
        .filter(
            LandedCostVersion.importation_id == importation_id,
            LandedCostVersion.is_current_version.is_(True),
        )
        .first()
    )
    if previous:
        previous.is_current_version = False

    version_number = _next_version_number(db, importation_id)
    components_data = gather_components(db, importation_id)
    total = sum(amount for _, amount, _ in components_data)

    version = LandedCostVersion(
        importation_id=importation_id,
        version_number=version_number,
        version_type=version_type,
        is_current_version=True,
        previous_version_id=previous.id if previous else None,
        trigger_event=trigger_event,
        trigger_notes=trigger_notes,
        total_cost=total,
        created_by_id=user_id,
    )
    db.add(version)
    db.flush()

    for ctype, amount, source_ref in components_data:
        db.add(
            LandedCostComponent(
                landed_cost_version_id=version.id,
                component_type=ctype,
                amount=amount,
                source_ref=source_ref,
            )
        )

    items = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    weights = _allocation_weights(db, items, allocation_method, manual_allocations)
    weight_sum = sum(weights.values()) or Decimal("1")

    for item in items:
        w = weights.get(item.id, Decimal("0"))
        share = (total * w / weight_sum) if weight_sum else Decimal("0")
        qty = item.quantity_ordered or 1
        unit = share / Decimal(qty) if qty else share
        db.add(
            LandedCostSkuAllocation(
                landed_cost_version_id=version.id,
                importation_item_id=item.id,
                allocation_method=allocation_method,
                allocated_amount=share,
                unit_cost=unit,
                quantity_basis=item.quantity_ordered,
                manual_reason_code_id=manual_reason_code_id if allocation_method == AllocationMethod.MANUAL.value else None,
                manual_justification=manual_justification if allocation_method == AllocationMethod.MANUAL.value else None,
            )
        )

    if previous and previous.total_cost is not None:
        db.add(
            LandedCostVariance(
                importation_id=importation_id,
                version_from_id=previous.id,
                version_to_id=version.id,
                variance_type=f"{previous.version_type}_vs_{version_type}",
                amount=total - previous.total_cost,
            )
        )

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="landed_cost_version",
        entity_id=str(version.id),
        action="create",
        new_value=f"v{version_number}:{version_type}",
    )
    db.commit()
    db.refresh(version)
    return version
