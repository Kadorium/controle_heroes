from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    RECONCILIATION_TOLERANCE_AMOUNT,
    RECONCILIATION_TOLERANCE_EXCHANGE,
    RECONCILIATION_TOLERANCE_PCT,
    CustomsDocumentStatus,
    ReconciliationPairType,
    ReconciliationStatus,
)
from app.models import (
    CustomsDocument,
    Expense,
    ImportationItem,
    ImportationOrder,
    Invoice,
    InvoiceItem,
    LandedCostVersion,
    Reconciliation,
    StagingImportRow,
    Tax,
)
from app.services.finance import importation_financial_summary, invoice_balance, invoice_paid_total
from app.services.nationalization import quantity_chain


class ReconciliationError(Exception):
    pass


def _d(value: Decimal | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, str):
        return Decimal(value)
    return value


def _within_tolerance(variance: Decimal, base: Decimal, tolerance: Decimal) -> bool:
    if variance.copy_abs() <= tolerance:
        return True
    if base and base != 0:
        pct = variance.copy_abs() / base.copy_abs()
        return pct <= RECONCILIATION_TOLERANCE_PCT
    return False


def _status_for_variance(variance: Decimal, base: Decimal, tolerance: Decimal) -> tuple[str, str]:
    if variance == 0:
        return ReconciliationStatus.OK.value, "WARNING"
    if _within_tolerance(variance, base, tolerance):
        return ReconciliationStatus.WARNING.value, "WARNING"
    return ReconciliationStatus.DIVERGENT.value, "BLOCKING"


def _upsert_reconciliation(
    db: Session,
    *,
    importation_id: int,
    pair_type: str,
    label: str,
    source_a_label: str,
    source_a_value: str,
    source_b_label: str,
    source_b_value: str,
    variance_value: Decimal | None,
    tolerance_value: Decimal | None,
    status: str,
    severity: str,
    entity_ref: str | None = None,
    details: dict | None = None,
) -> Reconciliation:
    existing = (
        db.query(Reconciliation)
        .filter(
            Reconciliation.importation_id == importation_id,
            Reconciliation.pair_type == pair_type,
            Reconciliation.entity_ref == entity_ref,
        )
        .first()
    )
    if existing and existing.status == ReconciliationStatus.APPROVED.value:
        return existing

    if existing:
        rec = existing
    else:
        rec = Reconciliation(importation_id=importation_id, pair_type=pair_type, label=label)
        db.add(rec)

    rec.label = label
    rec.source_a_label = source_a_label
    rec.source_a_value = source_a_value
    rec.source_b_label = source_b_label
    rec.source_b_value = source_b_value
    rec.variance_value = variance_value
    rec.tolerance_value = tolerance_value
    rec.status = status if not (existing and existing.status == ReconciliationStatus.APPROVED.value) else existing.status
    rec.severity = severity
    rec.entity_ref = entity_ref
    rec.details_json = details
    return rec


def run_reconciliations(db: Session, importation_id: int) -> list[Reconciliation]:
    imp = db.query(ImportationOrder).filter(ImportationOrder.id == importation_id).first()
    if not imp:
        raise ReconciliationError("Importação não encontrada")

    results: list[Reconciliation] = []

    invoices = db.query(Invoice).filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True)).all()
    for inv in invoices:
        if inv.amount is None:
            continue
        paid = invoice_paid_total(db, inv)
        bal = invoice_balance(db, inv) or Decimal("0")
        variance = bal
        status, severity = _status_for_variance(variance, inv.amount, RECONCILIATION_TOLERANCE_AMOUNT)
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.INVOICE_PAYMENT.value,
                label=f"Invoice {inv.invoice_number} vs pagamentos",
                source_a_label="Valor invoice",
                source_a_value=str(inv.amount),
                source_b_label="Saldo restante",
                source_b_value=str(bal),
                variance_value=variance,
                tolerance_value=RECONCILIATION_TOLERANCE_AMOUNT,
                status=status,
                severity=severity,
                entity_ref=f"invoice:{inv.id}",
            )
        )

        for pay in inv.payments:
            if not pay.is_active:
                continue
            expected = inv.expected_exchange_rate
            actual = pay.exchange_rate
            if expected is None or actual is None:
                continue
            variance = actual - expected
            status, severity = _status_for_variance(variance, expected, RECONCILIATION_TOLERANCE_EXCHANGE)
            results.append(
                _upsert_reconciliation(
                    db,
                    importation_id=importation_id,
                    pair_type=ReconciliationPairType.PAYMENT_EXCHANGE.value,
                    label=f"Câmbio pagamento invoice {inv.invoice_number}",
                    source_a_label="Câmbio previsto",
                    source_a_value=str(expected),
                    source_b_label="Câmbio pago",
                    source_b_value=str(actual),
                    variance_value=variance,
                    tolerance_value=RECONCILIATION_TOLERANCE_EXCHANGE,
                    status=status,
                    severity=severity,
                    entity_ref=f"payment:{pay.id}",
                )
            )

    items = (
        db.query(ImportationItem)
        .filter(ImportationItem.importation_id == importation_id, ImportationItem.is_active.is_(True))
        .all()
    )
    invoiced_qty = (
        db.query(InvoiceItem)
        .join(Invoice)
        .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True), InvoiceItem.is_active.is_(True))
        .with_entities(InvoiceItem.quantity)
        .all()
    )
    invoiced_qty_sum = sum(q[0] or 0 for q in invoiced_qty)
    ordered_qty = sum(i.quantity_ordered or 0 for i in items)
    inv_item_count = (
        db.query(InvoiceItem)
        .join(Invoice)
        .filter(Invoice.importation_id == importation_id, Invoice.is_active.is_(True), InvoiceItem.is_active.is_(True))
        .count()
    )
    if inv_item_count > 0 and ordered_qty:
        variance = Decimal(invoiced_qty_sum - ordered_qty)
        status, severity = _status_for_variance(variance, Decimal(ordered_qty), Decimal("0"))
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.INVOICE_ORDER.value,
                label="Quantidade pedida vs faturada",
                source_a_label="Qtd pedida",
                source_a_value=str(ordered_qty),
                source_b_label="Qtd faturada",
                source_b_value=str(invoiced_qty_sum),
                variance_value=variance,
                tolerance_value=Decimal("0"),
                status=status,
                severity=severity,
            )
        )

    staging_rows = (
        db.query(StagingImportRow)
        .filter(
            StagingImportRow.merged_entity_type == "importation_order",
            StagingImportRow.merged_entity_id == str(importation_id),
            StagingImportRow.status == "APPROVED",
        )
        .all()
    )
    if staging_rows and invoices:
        heroes_total = sum(
            _d(Decimal(str(r.parsed_data_json.get("quantity") or 0)))
            * _d(Decimal(str(r.parsed_data_json.get("unit_price") or 0)))
            for r in staging_rows
        )
        inv_total = sum(_d(i.amount) for i in invoices if i.amount is not None)
        variance = inv_total - heroes_total
        status, severity = _status_for_variance(variance, heroes_total or inv_total, RECONCILIATION_TOLERANCE_AMOUNT)
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.HEROES_INVOICE.value,
                label="Heroes staging vs invoices",
                source_a_label="Total Heroes",
                source_a_value=str(heroes_total),
                source_b_label="Total invoices",
                source_b_value=str(inv_total),
                variance_value=variance,
                tolerance_value=RECONCILIATION_TOLERANCE_AMOUNT,
                status=status,
                severity=severity,
            )
        )

    agent_expenses = (
        db.query(Expense)
        .filter(
            Expense.importation_id == importation_id,
            Expense.expense_type == "CUSTOMS_AGENT",
            Expense.is_active.is_(True),
        )
        .all()
    )
    agent_total = sum(_d(e.amount) for e in agent_expenses)
    agent_docs = (
        db.query(CustomsDocument)
        .filter(
            CustomsDocument.importation_id == importation_id,
            CustomsDocument.is_active.is_(True),
            CustomsDocument.status == CustomsDocumentStatus.OFFICIAL.value,
        )
        .count()
    )
    doc_expected = Decimal(agent_docs) * agent_total if agent_docs else agent_total
    variance = agent_total - doc_expected if agent_docs == 0 and agent_total > 0 else Decimal("0")
    status = ReconciliationStatus.DIVERGENT.value if agent_total > 0 and agent_docs == 0 else ReconciliationStatus.OK.value
    severity = "BLOCKING" if status == ReconciliationStatus.DIVERGENT.value else "WARNING"
    results.append(
        _upsert_reconciliation(
            db,
            importation_id=importation_id,
            pair_type=ReconciliationPairType.CUSTOMS_EXPENSE.value,
            label="Despachante vs DI/DUIMP",
            source_a_label="Despesas despachante",
            source_a_value=str(agent_total),
            source_b_label="Docs aduaneiros oficiais",
            source_b_value=str(agent_docs),
            variance_value=variance,
            tolerance_value=Decimal("0"),
            status=status,
            severity=severity,
        )
    )

    tax_total = sum(
        _d(t.amount)
        for t in db.query(Tax).filter(Tax.importation_id == importation_id, Tax.is_active.is_(True)).all()
    )
    official_docs = (
        db.query(CustomsDocument)
        .filter(
            CustomsDocument.importation_id == importation_id,
            CustomsDocument.status == CustomsDocumentStatus.OFFICIAL.value,
            CustomsDocument.is_valid.is_(True),
        )
        .all()
    )
    calc_tax = Decimal("0")
    for doc in official_docs:
        if doc.official_data_json and doc.official_data_json.get("tax_total"):
            calc_tax += _d(Decimal(str(doc.official_data_json["tax_total"])))
    if tax_total or calc_tax:
        variance = tax_total - calc_tax
        status, severity = _status_for_variance(variance, calc_tax or tax_total, RECONCILIATION_TOLERANCE_AMOUNT)
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.TAX_CALC_PAID.value,
                label="Imposto calculado vs imposto pago",
                source_a_label="Calculado (doc oficial)",
                source_a_value=str(calc_tax),
                source_b_label="Registrado",
                source_b_value=str(tax_total),
                variance_value=variance,
                tolerance_value=RECONCILIATION_TOLERANCE_AMOUNT,
                status=status,
                severity=severity,
            )
        )

    chain = quantity_chain(db, importation_id)
    for row in chain:
        ordered = row["quantity_ordered"] or 0
        stocked = row["quantity_stocked"]
        if stocked is None:
            continue
        variance = Decimal(stocked - ordered)
        if variance == 0:
            status, severity = ReconciliationStatus.OK.value, "WARNING"
        else:
            status, severity = _status_for_variance(variance, Decimal(ordered or 1), Decimal("0"))
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.QTY_CHAIN.value,
                label=f"Qty item {row['importation_item_id']}: pedida→estocada",
                source_a_label="Pedida",
                source_a_value=str(ordered),
                source_b_label="Estocada",
                source_b_value=str(stocked),
                variance_value=variance,
                tolerance_value=Decimal("0"),
                status=status,
                severity=severity,
                entity_ref=f"item:{row['importation_item_id']}",
                details={
                    "shipped": row["quantity_shipped"],
                    "nationalized": row["quantity_nationalized"],
                },
            )
        )

    lc_final = (
        db.query(LandedCostVersion)
        .filter(
            LandedCostVersion.importation_id == importation_id,
            LandedCostVersion.version_type.in_(["FINAL", "PRELIMINARY", "INITIAL"]),
        )
        .order_by(LandedCostVersion.version_number.desc())
        .all()
    )
    final_v = next((v for v in lc_final if v.version_type == "FINAL"), None)
    prelim_v = next((v for v in lc_final if v.version_type == "PRELIMINARY"), None)
    initial_v = next((v for v in lc_final if v.version_type == "INITIAL"), None)

    if imp.estimated_total and final_v and final_v.total_cost:
        variance = final_v.total_cost - imp.estimated_total
        status, severity = _status_for_variance(variance, imp.estimated_total, RECONCILIATION_TOLERANCE_AMOUNT)
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.COST_ESTIMATED_ACTUAL.value,
                label="Custo estimado vs realizado (LC final)",
                source_a_label="Estimado",
                source_a_value=str(imp.estimated_total),
                source_b_label="LC final",
                source_b_value=str(final_v.total_cost),
                variance_value=variance,
                tolerance_value=RECONCILIATION_TOLERANCE_AMOUNT,
                status=status,
                severity=severity,
            )
        )

    if prelim_v and final_v and prelim_v.total_cost and final_v.total_cost:
        variance = final_v.total_cost - prelim_v.total_cost
        status, severity = _status_for_variance(variance, prelim_v.total_cost, RECONCILIATION_TOLERANCE_AMOUNT)
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.LC_PRELIM_FINAL.value,
                label="Landed cost preliminar vs final",
                source_a_label="Preliminar",
                source_a_value=str(prelim_v.total_cost),
                source_b_label="Final",
                source_b_value=str(final_v.total_cost),
                variance_value=variance,
                tolerance_value=RECONCILIATION_TOLERANCE_AMOUNT,
                status=status,
                severity=severity,
            )
        )
    elif initial_v and final_v and initial_v.total_cost and final_v.total_cost:
        variance = final_v.total_cost - initial_v.total_cost
        status, severity = _status_for_variance(variance, initial_v.total_cost, RECONCILIATION_TOLERANCE_AMOUNT)
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.LC_PRELIM_FINAL.value,
                label="Landed cost inicial vs final",
                source_a_label="Inicial",
                source_a_value=str(initial_v.total_cost),
                source_b_label="Final",
                source_b_value=str(final_v.total_cost),
                variance_value=variance,
                tolerance_value=RECONCILIATION_TOLERANCE_AMOUNT,
                status=status,
                severity=severity,
            )
        )

    summary = importation_financial_summary(db, imp)
    if _d(summary["total_discounts"]) > 0:
        results.append(
            _upsert_reconciliation(
                db,
                importation_id=importation_id,
                pair_type=ReconciliationPairType.DISCOUNT_APPLIED.value,
                label="Descontos aplicados",
                source_a_label="Total descontos",
                source_a_value=str(summary["total_discounts"]),
                source_b_label="Registrado",
                source_b_value=str(summary["total_discounts"]),
                variance_value=Decimal("0"),
                tolerance_value=Decimal("0"),
                status=ReconciliationStatus.OK.value,
                severity="WARNING",
            )
        )

    db.commit()
    for r in results:
        db.refresh(r)
    return results


def approve_reconciliation(
    db: Session,
    rec: Reconciliation,
    *,
    user_id: int | None,
    reason_code_id: int | None,
    justification: str | None,
) -> Reconciliation:
    if rec.status not in (ReconciliationStatus.DIVERGENT.value, ReconciliationStatus.WARNING.value):
        raise ReconciliationError("Conciliação não requer aprovação")
    if not reason_code_id and not (justification or "").strip():
        raise ReconciliationError("Aprovação de divergência exige motivo")
    from datetime import datetime, timezone

    rec.status = ReconciliationStatus.APPROVED.value
    rec.approved_by_id = user_id
    rec.approved_at = datetime.now(timezone.utc)
    rec.approval_reason_code_id = reason_code_id
    rec.approval_justification = justification
    db.commit()
    db.refresh(rec)
    return rec


def blocking_reconciliations(db: Session, importation_id: int) -> list[Reconciliation]:
    return (
        db.query(Reconciliation)
        .filter(
            Reconciliation.importation_id == importation_id,
            Reconciliation.status == ReconciliationStatus.DIVERGENT.value,
            Reconciliation.severity == "BLOCKING",
        )
        .all()
    )
