"""Massa demo — 16 cenários do checklist F12-001."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import DEFAULT_IMPORT_CURRENCY
from app.models import (
    BrazilCurrentAccount,
    Credit,
    CreditUsage,
    CustomsDocument,
    Discount,
    Expense,
    ImportationItem,
    ImportationOrder,
    Invoice,
    LandedCostVersion,
    Payment,
    Product,
    Shipment,
    Supplier,
    User,
)
from app.services.customs import approve_customs_document, create_customs_document
from app.services.landed_cost import create_landed_cost_version
from app.services.logistics import change_shipment_modal, create_shipment
from app.services.nationalization import create_nationalization, create_stock_entry


def _supplier(db: Session, name: str) -> Supplier:
    s = db.query(Supplier).filter(Supplier.name == name).first()
    if s:
        return s
    s = Supplier(name=name, country="CN", currency_default=DEFAULT_IMPORT_CURRENCY)
    db.add(s)
    db.flush()
    return s


def _product(db: Session, sku: str) -> Product:
    p = db.query(Product).filter(Product.sku_code == sku).first()
    if p:
        return p
    p = Product(sku_code=sku, description=f"Demo {sku}")
    db.add(p)
    db.flush()
    return p


def _imp(
    db: Session,
    po: str,
    supplier: Supplier,
    product: Product,
    *,
    qty: int = 100,
    price: str = "10",
    estimated: str | None = "1000",
) -> ImportationOrder:
    existing = db.query(ImportationOrder).filter(ImportationOrder.po_number == po).first()
    if existing:
        return existing
    imp = ImportationOrder(
        po_number=po,
        supplier_id=supplier.id,
        currency=DEFAULT_IMPORT_CURRENCY,
        incoterm="FOB",
        estimated_total=Decimal(estimated) if estimated else None,
        current_status="ARRIVED",
    )
    db.add(imp)
    db.flush()
    db.add(
        ImportationItem(
            importation_id=imp.id,
            product_id=product.id,
            quantity_ordered=qty,
            unit_price_foreign=Decimal(price),
        )
    )
    db.flush()
    return imp


def _di(db: Session, imp: ImportationOrder, user_id: int | None) -> CustomsDocument:
    doc = create_customs_document(
        db,
        importation_id=imp.id,
        document_type="DI",
        document_number=f"DI-{imp.po_number}",
        document_data_json={"staging": True},
        user_id=user_id,
    )
    return approve_customs_document(
        db, doc, {"number": doc.document_number, "tax_total": "500"}, user_id=user_id
    )


def _lc_final(db: Session, imp: ImportationOrder, user_id: int | None) -> LandedCostVersion:
    create_landed_cost_version(
        db,
        importation_id=imp.id,
        version_type="INITIAL",
        allocation_method="VALUE",
        user_id=user_id,
    )
    return create_landed_cost_version(
        db,
        importation_id=imp.id,
        version_type="FINAL",
        allocation_method="VALUE",
        user_id=user_id,
    )


def run_demo_seed(db: Session, user_id: int | None = None) -> dict[str, int]:
    supplier = _supplier(db, "Heroes Demo CN")
    product = _product(db, "DEMO-SKU-001")
    results: dict[str, int] = {}

    # 1. Marítima simples
    imp1 = _imp(db, "DEMO-01-OCEAN", supplier, product)
    create_shipment(
        db,
        importation_id=imp1.id,
        shipment_number="SH-DEMO-01",
        modal="OCEAN",
        user_id=user_id,
        bl_number="BL-D01",
    )
    results["ocean_simple"] = imp1.id

    # 2. Aérea simples
    imp2 = _imp(db, "DEMO-02-AIR", supplier, product)
    create_shipment(
        db,
        importation_id=imp2.id,
        shipment_number="SH-DEMO-02",
        modal="AIR",
        user_id=user_id,
        awb_number="AWB-D02",
    )
    results["air_simple"] = imp2.id

    # 3. Modal change
    imp3 = _imp(db, "DEMO-03-MODAL", supplier, product)
    ship3 = create_shipment(
        db,
        importation_id=imp3.id,
        shipment_number="SH-DEMO-03",
        modal="OCEAN",
        user_id=user_id,
        bl_number="BL-D03",
    )
    from app.models import ReasonCode

    rc = db.query(ReasonCode).filter(ReasonCode.code == "MODAL_CHANGE_URGENCY").first()
    change_shipment_modal(
        db, ship3, "AIR", user_id=user_id, reason_code_id=rc.id if rc else None, comment="Urgência demo"
    )
    results["modal_change"] = imp3.id

    # 4. 3 invoices com ANTECIPO
    imp4 = _imp(db, "DEMO-04-3INV", supplier, product)
    for itype, num, amt in [("ANTECIPO", "ANT-04", "300"), ("PROFORMA", "PRO-04", "700"), ("SALDO", "SAL-04", "0")]:
        db.add(
            Invoice(
                importation_id=imp4.id,
                invoice_type=itype,
                invoice_number=num,
                amount=Decimal(amt) if amt != "0" else Decimal("1000"),
                currency=DEFAULT_IMPORT_CURRENCY,
            )
        )
    db.flush()
    results["three_invoices"] = imp4.id

    # 5. Mais de 3 invoices
    imp5 = _imp(db, "DEMO-05-MULTI", supplier, product)
    for i in range(5):
        db.add(
            Invoice(
                importation_id=imp5.id,
                invoice_type="PROFORMA" if i == 0 else "COMPLEMENTAR",
                invoice_number=f"INV-05-{i}",
                amount=Decimal("200"),
                currency=DEFAULT_IMPORT_CURRENCY,
            )
        )
    db.flush()
    results["multi_invoices"] = imp5.id

    # 6. Pagamento parcial
    imp6 = _imp(db, "DEMO-06-PARTIAL", supplier, product)
    inv6 = Invoice(
        importation_id=imp6.id,
        invoice_type="PROFORMA",
        invoice_number="PRO-06",
        amount=Decimal("1000"),
        currency=DEFAULT_IMPORT_CURRENCY,
    )
    db.add(inv6)
    db.flush()
    db.add(
        Payment(
            invoice_id=inv6.id,
            payment_type="PARTIAL",
            payment_date=date.today(),
            amount_foreign=Decimal("400"),
            currency_foreign=DEFAULT_IMPORT_CURRENCY,
            exchange_rate=Decimal("5.10"),
            receipt_reference="DEMO-06-REC",
        )
    )
    results["partial_payment"] = imp6.id

    # 7. FX diff
    imp7 = _imp(db, "DEMO-07-FX", supplier, product)
    inv7 = Invoice(
        importation_id=imp7.id,
        invoice_type="PROFORMA",
        invoice_number="PRO-07",
        amount=Decimal("1000"),
        currency=DEFAULT_IMPORT_CURRENCY,
        expected_exchange_rate=Decimal("5.00"),
    )
    db.add(inv7)
    db.flush()
    db.add(
        Payment(
            invoice_id=inv7.id,
            payment_type="FINAL",
            amount_foreign=Decimal("1000"),
            currency_foreign=DEFAULT_IMPORT_CURRENCY,
            exchange_rate=Decimal("5.35"),
        )
    )
    results["fx_diff"] = imp7.id

    # 8. Desconto
    imp8 = _imp(db, "DEMO-08-DISC", supplier, product)
    inv8 = Invoice(
        importation_id=imp8.id,
        invoice_type="PROFORMA",
        invoice_number="PRO-08",
        amount=Decimal("1000"),
        currency=DEFAULT_IMPORT_CURRENCY,
    )
    db.add(inv8)
    db.flush()
    db.add(
        Discount(
            invoice_id=inv8.id,
            discount_type="GLOBAL",
            amount=Decimal("50"),
            currency=DEFAULT_IMPORT_CURRENCY,
            reason="Demo desconto",
        )
    )
    results["discount"] = imp8.id

    # 9. Crédito Heroes
    imp9 = _imp(db, "DEMO-09-CREDIT", supplier, product)
    credit = Credit(
        supplier_id=supplier.id,
        amount=Decimal("500"),
        currency=DEFAULT_IMPORT_CURRENCY,
        amount_used=Decimal("200"),
        amount_available=Decimal("300"),
        status="PARTIAL",
        origin_importation_id=imp9.id,
    )
    db.add(credit)
    db.flush()
    db.add(CreditUsage(credit_id=credit.id, importation_id=imp9.id, amount_used=Decimal("200")))
    results["credit"] = imp9.id

    # 10. Conta corrente Brasil
    imp10 = _imp(db, "DEMO-10-BRAZIL", supplier, product)
    db.add(
        BrazilCurrentAccount(
            supplier_id=supplier.id,
            origin_importation_id=imp10.id,
            description="Conta corrente demo",
            amount=Decimal("1500"),
            currency="BRL",
            amount_used=Decimal("0"),
            amount_available=Decimal("1500"),
            financial_impact_estimated=Decimal("1500"),
            fiscal_impact_estimated=Decimal("200"),
        )
    )
    results["brazil_account"] = imp10.id

    # 11. Qty divergence
    imp11 = _imp(db, "DEMO-11-QTY", supplier, product, qty=100)
    item11 = db.query(ImportationItem).filter(ImportationItem.importation_id == imp11.id).first()
    doc11 = _di(db, imp11, user_id)
    create_nationalization(
        db,
        importation_id=imp11.id,
        customs_document_id=doc11.id,
        items=[{"importation_item_id": item11.id, "quantity_nationalized": 90}],
        user_id=user_id,
    )
    results["qty_divergence"] = imp11.id

    # 12. Cost divergence
    imp12 = _imp(db, "DEMO-12-COST", supplier, product, estimated="800")
    _lc_final(db, imp12, user_id)
    results["cost_divergence"] = imp12.id

    # 13. Close ready (happy path)
    imp13 = _imp(db, "DEMO-13-CLOSE", supplier, product, estimated="1000")
    item13 = db.query(ImportationItem).filter(ImportationItem.importation_id == imp13.id).first()
    doc13 = _di(db, imp13, user_id)
    inv13 = Invoice(
        importation_id=imp13.id,
        invoice_type="PROFORMA",
        invoice_number="PRO-13",
        amount=Decimal("1000"),
        currency=DEFAULT_IMPORT_CURRENCY,
    )
    db.add(inv13)
    db.flush()
    db.add(
        Payment(
            invoice_id=inv13.id,
            payment_type="FINAL",
            amount_foreign=Decimal("1000"),
            currency_foreign=DEFAULT_IMPORT_CURRENCY,
            exchange_rate=Decimal("5.00"),
        )
    )
    nat13 = create_nationalization(
        db,
        importation_id=imp13.id,
        customs_document_id=doc13.id,
        items=[{"importation_item_id": item13.id, "quantity_nationalized": 100}],
        user_id=user_id,
    )
    lc13 = _lc_final(db, imp13, user_id)
    create_stock_entry(
        db,
        nationalization_id=nat13.id,
        importation_item_id=item13.id,
        quantity_received=100,
        user_id=user_id,
        unit_cost_approved=Decimal("10.5"),
        landed_cost_version_id=lc13.id,
    )
    results["close_ready"] = imp13.id

    # 14. Close with variance (qty diff)
    imp14 = _imp(db, "DEMO-14-CLOSE-VAR", supplier, product)
    item14 = db.query(ImportationItem).filter(ImportationItem.importation_id == imp14.id).first()
    doc14 = _di(db, imp14, user_id)
    create_nationalization(
        db,
        importation_id=imp14.id,
        customs_document_id=doc14.id,
        items=[{"importation_item_id": item14.id, "quantity_nationalized": 95}],
        user_id=user_id,
    )
    _lc_final(db, imp14, user_id)
    results["close_with_variance"] = imp14.id

    # 15. Reopen candidate — closed in tests
    imp15 = _imp(db, "DEMO-15-REOPEN", supplier, product, estimated="1000")
    item15 = db.query(ImportationItem).filter(ImportationItem.importation_id == imp15.id).first()
    doc15 = _di(db, imp15, user_id)
    db.add(
        Invoice(
            importation_id=imp15.id,
            invoice_type="PROFORMA",
            invoice_number="PRO-15",
            amount=Decimal("1000"),
            currency=DEFAULT_IMPORT_CURRENCY,
        )
    )
    db.flush()
    create_nationalization(
        db,
        importation_id=imp15.id,
        customs_document_id=doc15.id,
        items=[{"importation_item_id": item15.id, "quantity_nationalized": 100}],
        user_id=user_id,
    )
    _lc_final(db, imp15, user_id)
    results["reopen_candidate"] = imp15.id

    # 16. Stock after nationalization
    imp16 = _imp(db, "DEMO-16-STOCK", supplier, product)
    item16 = db.query(ImportationItem).filter(ImportationItem.importation_id == imp16.id).first()
    doc16 = _di(db, imp16, user_id)
    nat16 = create_nationalization(
        db,
        importation_id=imp16.id,
        customs_document_id=doc16.id,
        items=[{"importation_item_id": item16.id, "quantity_nationalized": 60}],
        user_id=user_id,
    )
    create_stock_entry(
        db,
        nationalization_id=nat16.id,
        importation_item_id=item16.id,
        quantity_received=60,
        user_id=user_id,
    )
    results["stock_entry"] = imp16.id

    db.add(
        Expense(
            importation_id=imp13.id,
            expense_type="CUSTOMS_AGENT",
            amount=Decimal("800"),
            currency="BRL",
            source_document_ref="NF-DESP-13",
        )
    )
    db.commit()
    return results
