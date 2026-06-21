"""Commit de preview Heroes XLSX para dados oficiais."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import DEFAULT_IMPORT_CURRENCY
from app.core.enums import HeroesImportRunStatus, InvoiceType, ProductCategory
from app.core.parse import optional_decimal, optional_int
from app.models import (
    HeroesImportRun,
    ImportationItem,
    ImportationOrder,
    Invoice,
    InvoiceItem,
    Payment,
    Product,
    Supplier,
)
from app.services.auth import write_audit_log
from app.services.product_category import suggest_product_category


def _parse_date(val: str | None):
    if not val:
        return None
    from datetime import date as date_cls
    try:
        return date_cls.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def _slug_sku(name: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.upper()).strip("-")
    return (base[:60] or "PROD-UNK")


def _get_heroes_supplier(db: Session) -> Supplier:
    for name in ("Heroes Itália", "Heroes Italia", "Heroes Demo CN", "Heroes Import"):
        s = db.query(Supplier).filter(Supplier.name == name, Supplier.is_active.is_(True)).first()
        if s:
            return s
    s = db.query(Supplier).filter(Supplier.is_active.is_(True)).first()
    if not s:
        s = Supplier(name="Heroes Itália", country="IT", currency_default=DEFAULT_IMPORT_CURRENCY)
        db.add(s)
        db.flush()
    return s


def _resolve_category(name: str, overrides: dict[str, str] | None) -> str:
    if overrides and name in overrides:
        return overrides[name]
    cat, _, _ = suggest_product_category(name)
    return cat


def commit_heroes_import_run(
    db: Session,
    run_id: int,
    *,
    user_id: int | None,
    category_overrides: dict[str, str] | None = None,
    confirmed_order_number: str | None = None,
    confirm_sheet_match: bool = False,
    confirm_import: bool = False,
) -> ImportationOrder:
    run = db.query(HeroesImportRun).filter(HeroesImportRun.id == run_id).first()
    if not run:
        raise ValueError("Import run não encontrado")
    if run.status == HeroesImportRunStatus.COMMITTED.value:
        existing = db.query(ImportationOrder).filter(ImportationOrder.id == run.importation_id).first()
        if existing:
            return existing
        raise ValueError("Run já commitado mas ordem não encontrada")

    preview = run.preview_json
    if preview.get("errors"):
        raise ValueError("Preview contém erros — corrija antes de importar")

    if not confirm_import:
        raise ValueError("Confirme a importação explicitamente (confirm_import=true)")
    if not confirm_sheet_match:
        raise ValueError("Confirme que a sheet selecionada está correta (confirm_sheet_match=true)")

    order_number = confirmed_order_number or preview.get("confirmed_order_number") or preview.get("order_number") or run.order_number
    if not order_number:
        raise ValueError("Número da ordem não detectado — informe confirmed_order_number")

    if preview.get("order_number_divergence") and not confirmed_order_number:
        raise ValueError(
            "Divergência entre nome da sheet e conteúdo — informe confirmed_order_number antes do commit"
        )

    po_number = f"HEROES-{order_number}"
    existing = db.query(ImportationOrder).filter(ImportationOrder.po_number == po_number).first()
    if existing:
        raise ValueError(
            f"Ordem {po_number} já existe (id={existing.id}). "
            "Use reset operacional ou escolha atualizar staging."
        )

    supplier = _get_heroes_supplier(db)
    imp = ImportationOrder(
        po_number=po_number,
        supplier_id=supplier.id,
        currency=DEFAULT_IMPORT_CURRENCY,
        incoterm="FOB",
        current_status="PROFORMA_RECEIVED",
        created_by_id=user_id,
    )
    db.add(imp)
    db.flush()

    product_cache: dict[str, Product] = {}
    item_by_product: dict[str, ImportationItem] = {}

    def get_or_create_product(name: str) -> Product:
        if name in product_cache:
            return product_cache[name]
        sku = _slug_sku(name)
        prod = db.query(Product).filter(Product.sku_code == sku).first()
        cat = _resolve_category(name, category_overrides)
        if not prod:
            prod = Product(sku_code=sku, description=name, category=cat)
            db.add(prod)
            db.flush()
        elif category_overrides and name in category_overrides:
            prod.category = category_overrides[name]
        product_cache[name] = prod
        return prod

    invoice_cache: dict[str, Invoice] = {}

    for row in preview.get("invoice_items") or []:
        name = row.get("product_name_raw")
        if not name:
            continue
        prod = get_or_create_product(name)
        inv_num = row.get("invoice_number") or "SEM-NUMERO"
        if inv_num not in invoice_cache:
            inv = Invoice(
                importation_id=imp.id,
                invoice_type=InvoiceType.PROFORMA.value,
                invoice_number=str(inv_num),
                invoice_date=_parse_date(row.get("invoice_date")),
                currency=DEFAULT_IMPORT_CURRENCY,
                amount=None,
            )
            db.add(inv)
            db.flush()
            invoice_cache[inv_num] = inv
        else:
            inv = invoice_cache[inv_num]

        qty = optional_int(row.get("item_quantity"))
        db.add(
            InvoiceItem(
                invoice_id=inv.id,
                product_id=prod.id,
                quantity=qty,
                unit_price=None,
                amount=None,
            )
        )

        if name not in item_by_product:
            item_by_product[name] = ImportationItem(
                importation_id=imp.id,
                product_id=prod.id,
                supplier_sku=prod.sku_code,
                description=name,
                quantity_ordered=qty,
            )
            db.add(item_by_product[name])
        elif qty is not None:
            cur = item_by_product[name].quantity_ordered
            item_by_product[name].quantity_ordered = (cur or 0) + qty

        acconto = optional_decimal(row.get("acconto_amount"))
        if acconto is not None and acconto > 0:
            inv_date = row.get("invoice_date")
            pay_date = None
            if inv_date:
                from datetime import date as date_cls
                try:
                    pay_date = date_cls.fromisoformat(str(inv_date)[:10])
                except ValueError:
                    pay_date = None
            db.add(
                Payment(
                    invoice_id=inv.id,
                    payment_type="ADVANCE",
                    amount_foreign=acconto,
                    currency_foreign=DEFAULT_IMPORT_CURRENCY,
                    payment_date=pay_date,
                    receipt_reference=f"ACCONTO-{inv_num}",
                )
            )

    for da in preview.get("da_spedire") or []:
        name = da.get("product_name_raw")
        if not name:
            continue
        prod = get_or_create_product(name)
        qty = optional_int(da.get("quantity_to_dispatch"))
        if name not in item_by_product:
            item_by_product[name] = ImportationItem(
                importation_id=imp.id,
                product_id=prod.id,
                supplier_sku=prod.sku_code,
                description=name,
                quantity_ordered=qty,
            )
            db.add(item_by_product[name])
        elif qty is not None:
            cur = item_by_product[name].quantity_ordered
            item_by_product[name].quantity_ordered = max(cur or 0, qty)

    run.status = HeroesImportRunStatus.COMMITTED.value
    run.importation_id = imp.id
    run.committed_at = datetime.now(timezone.utc)
    run.normalized_json = {"po_number": po_number, "importation_id": imp.id}

    write_audit_log(
        db,
        user_id=user_id,
        entity_type="heroes_import_run",
        entity_id=str(run.id),
        action="commit",
        new_value=str(imp.id),
    )
    db.commit()
    db.refresh(imp)
    return imp
