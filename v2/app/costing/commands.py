"""Comandos Costing — draft/recalculate/publish/supersede/expense."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.costing import repository as repo
from app.costing.coverage import analyze as analyze_coverage
from app.costing.errors import CostingConflict, CostingNotFound, CostingValidation, PublishBlocked
from app.costing.facts import collect, order_item_estimate
from app.costing.fx_alloc import apply_fx
from app.costing.gather import build_components
from app.costing.models import (
    CostAllocation,
    CostComponent,
    CostingCase,
    CostingExpense,
    CostingLine,
    CostingVersion,
)
from app.costing.money import decimal_str, money2, parse_decimal
from app.costing.recon_build import build_pairs
from app.costing.synthesis import synthesize
from app.customs import public as customs_public
from app.reconciliation import public as reconciliation_public


def _now():
    return datetime.now(timezone.utc)


def ensure_case(db: Session, process_id: int, *, actor_id: str) -> CostingCase:
    existing = repo.get_case_by_process(db, process_id)
    if existing:
        return existing
    try:
        customs_public.get_import_process(db, process_id)
    except customs_public.CustomsError as exc:
        raise CostingNotFound("ImportProcess", process_id) from exc
    case = CostingCase(import_process_id=process_id, version=1)
    db.add(case)
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="costing_case",
        entity_id=str(case.id),
        action="create",
        details=f"process_id={process_id}",
    )
    return case


def add_expense(
    db: Session,
    case_id: int,
    *,
    actor_id: str,
    category: str,
    description: str,
    amount: str,
    currency: str = "BRL",
    expense_date=None,
    payee_snapshot: str | None = None,
    document_id: int | None = None,
    allocation_method: str = "VALUE",
) -> CostingExpense:
    case = repo.get_case(db, case_id)
    if not case:
        raise CostingNotFound("CostingCase", case_id)
    amt = parse_decimal(amount)
    if amt is None or amt <= 0:
        raise CostingValidation("Valor da despesa deve ser > 0")
    if currency != "BRL":
        raise CostingValidation("Expense Costing nesta campanha é BRL")
    row = CostingExpense(
        case_id=case.id,
        category=(category or "OUTRAS").strip()[:64],
        description=(description or "").strip()[:512],
        amount=money2(amt),
        currency="BRL",
        expense_date=expense_date,
        payee_snapshot=payee_snapshot,
        document_id=document_id,
        allocation_method=(allocation_method or "VALUE").upper(),
        status="ACTIVE",
    )
    db.add(row)
    db.flush()
    case.version += 1
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="costing_expense",
        entity_id=str(row.id),
        action="create",
        details=f"case_id={case.id}",
    )
    return row


def set_freight_choice(
    db: Session,
    case_id: int,
    *,
    actor_id: str,
    choice: str,
    reason: str,
) -> CostingCase:
    case = repo.get_case(db, case_id)
    if not case:
        raise CostingNotFound("CostingCase", case_id)
    choice = (choice or "").upper()
    if choice not in ("VALUE_BASIS", "EXPENSE_LINE", "EXCLUDE"):
        raise CostingValidation("freight_choice deve ser VALUE_BASIS, EXPENSE_LINE ou EXCLUDE")
    if not (reason or "").strip():
        raise CostingValidation("reason obrigatório para escolha de frete")
    case.freight_choice = choice
    case.freight_choice_reason = reason.strip()
    case.version += 1
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="costing_case",
        entity_id=str(case.id),
        action="freight_choice",
        reason_code=choice,
        details=reason.strip()[:500],
    )
    return case


def _expense_dicts(case: CostingCase) -> list[dict]:
    return [
        {
            "id": e.id,
            "category": e.category,
            "description": e.description,
            "amount": str(e.amount),
            "currency": e.currency,
            "expense_date": e.expense_date.isoformat() if e.expense_date else None,
            "payee_snapshot": e.payee_snapshot,
            "document_id": e.document_id,
            "allocation_method": e.allocation_method,
            "status": e.status,
        }
        for e in case.expenses
    ]


def _fill_estimated_from_order(db: Session, lines: list[dict], kind: str) -> None:
    if kind != "ESTIMATED":
        return
    for line in lines:
        if line.get("foreign_net") is not None:
            continue
        est = order_item_estimate(db, line.get("order_item_id"))
        if not est or not est.get("estimated_net") or not est.get("quantity"):
            continue
        alloc_qty = parse_decimal(line.get("qty"))
        oi_qty = parse_decimal(est["quantity"])
        oi_net = parse_decimal(est["estimated_net"])
        if alloc_qty and oi_qty and oi_net is not None:
            line["foreign_net"] = alloc_qty * oi_net / oi_qty
            line["currency"] = line.get("currency") or "EUR"
            line["merchandise_source"] = "ORDER_ESTIMATE"


def preview_payload(
    db: Session,
    case: CostingCase,
    *,
    kind: str,
    line_links: list[dict] | None = None,
    methods: dict | None = None,
    manuals: dict | None = None,
) -> dict:
    facts = collect(db, case.import_process_id)
    coverage = analyze_coverage(facts)
    lines = synthesize(facts, line_links=line_links)
    _fill_estimated_from_order(db, lines, kind)
    apply_fx(lines, facts["invoices"], kind=kind)
    expenses = _expense_dicts(case)
    components = build_components(
        lines=lines,
        facts=facts,
        coverage=coverage,
        freight_choice=case.freight_choice,
        expenses=expenses,
        methods=methods,
        manuals=manuals,
        kind=kind,
    )
    pairs = build_pairs(
        kind=kind,
        lines=lines,
        components=components,
        coverage=coverage,
        facts=facts,
        freight_choice=case.freight_choice,
    )
    included = money2(
        sum(
            (c["amount_brl"] for c in components if c.get("included") and c.get("amount_brl") is not None),
            Decimal("0"),
        )
    )
    gross = money2(
        sum((c["amount_brl"] for c in components if c.get("amount_brl") is not None), Decimal("0"))
    )
    sku_rows = _sku_rollup(lines, components)
    fx_statuses = sorted({str(l.get("fx_status") or "") for l in lines if l.get("fx_status")})
    fx_kind = "documental"
    if any(s in ("FX_OPEN", "FX_MISSING", "REVISED_MIXED") for s in fx_statuses):
        fx_kind = "parcial"
    elif fx_statuses and all(s == "REALIZED" for s in fx_statuses):
        fx_kind = "bancario"
    documentary_rates = []
    for inv in facts.get("invoices") or []:
        rate = (inv.get("fx") or {}).get("initial_rate")
        if rate is not None:
            documentary_rates.append(str(rate))
    return {
        "facts": {
            "process": facts["process"],
            "invoices": [
                {
                    "invoice_id": i["invoice_id"],
                    "invoice_number": i["invoice_number"],
                    "status": i["status"],
                    "currency": i["currency"],
                    "net_amount": i.get("net_amount"),
                    "fx": i.get("fx"),
                }
                for i in facts["invoices"]
            ],
            "coverage": coverage,
            "fx": {
                "kind": fx_kind,
                "statuses": fx_statuses,
                "documentary_rate": documentary_rates[0] if documentary_rates else None,
            },
        },
        "lines": [
            {
                **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in line.items()},
            }
            for line in lines
        ],
        "components": [
            {
                **{
                    k: (str(v) if isinstance(v, Decimal) else v)
                    for k, v in comp.items()
                    if k != "allocations"
                },
                "allocations": [
                    {
                        **{ak: (str(av) if isinstance(av, Decimal) else av) for ak, av in a.items()}
                    }
                    for a in comp.get("allocations") or []
                ],
            }
            for comp in components
        ],
        "pairs": pairs,
        "products": sku_rows,
        "included_total_brl": decimal_str(included),
        "gross_total_brl": decimal_str(gross),
        "partial_coverage": coverage.get("coverage") == "INCOMPLETE",
    }


def _component_bucket(comp: dict) -> str | None:
    if not comp.get("included"):
        return None
    kind = comp.get("source_kind")
    ctype = comp.get("component_type") or ""
    if kind == "INVOICE" or ctype == "MERCADORIA":
        return "merchandise"
    if ctype == "FRETE_INTERNACIONAL":
        return "freight"
    if kind == "TAX_LINE":
        return "tax"
    return "expense"


def _sku_rollup(lines: list[dict], components: list[dict]) -> list[dict]:
    from collections import defaultdict

    qty_by: dict[tuple, Decimal] = defaultdict(lambda: Decimal("0"))
    meta: dict[tuple, dict] = {}
    for line in lines:
        key = (line.get("product_id"), line.get("sku_snapshot"))
        qty_by[key] += parse_decimal(line.get("qty")) or Decimal("0")
        meta[key] = {
            "product_id": line.get("product_id"),
            "sku_snapshot": line.get("sku_snapshot"),
            "description_snapshot": line.get("description_snapshot"),
        }
    buckets: dict[tuple, dict[str, Decimal]] = defaultdict(
        lambda: {
            "merchandise": Decimal("0"),
            "freight": Decimal("0"),
            "tax": Decimal("0"),
            "expense": Decimal("0"),
        }
    )
    line_index = {
        (l.get("invoice_item_id"), l.get("shipment_item_id")): (l.get("product_id"), l.get("sku_snapshot"))
        for l in lines
    }
    for comp in components:
        bucket = _component_bucket(comp)
        if not bucket:
            continue
        for a in comp.get("allocations") or []:
            ident = (a.get("invoice_item_id"), a.get("shipment_item_id"))
            sku_key = line_index.get(ident)
            if not sku_key:
                continue
            amt = a["amount_brl"] if isinstance(a["amount_brl"], Decimal) else parse_decimal(a["amount_brl"])
            if amt is None:
                continue
            buckets[sku_key][bucket] += amt
    rows = []
    for key, qty in qty_by.items():
        parts = buckets.get(key) or {}
        merch = money2(parts.get("merchandise", Decimal("0")))
        freight = money2(parts.get("freight", Decimal("0")))
        tax = money2(parts.get("tax", Decimal("0")))
        expense = money2(parts.get("expense", Decimal("0")))
        total = money2(merch + freight + tax + expense)
        unit = money2(total / qty) if qty else None
        rows.append(
            {
                **meta[key],
                "qty": str(qty),
                "merchandise_brl": decimal_str(merch),
                "freight_brl": decimal_str(freight),
                "tax_brl": decimal_str(tax),
                "expense_brl": decimal_str(expense),
                "total_brl": decimal_str(total),
                "unit_brl": decimal_str(unit),
            }
        )
    rows.sort(key=lambda r: r.get("sku_snapshot") or "")
    return rows


def _persist_preview(db: Session, version: CostingVersion, preview: dict) -> None:
    repo.delete_version_children(db, version)
    db.flush()
    line_rows: dict[tuple, CostingLine] = {}
    for line in preview["lines"]:
        row = CostingLine(
            version_id=version.id,
            invoice_item_id=line.get("invoice_item_id"),
            shipment_item_id=line.get("shipment_item_id"),
            order_item_id=line.get("order_item_id"),
            product_id=line.get("product_id"),
            sku_snapshot=(line.get("sku_snapshot") or "")[:64],
            description_snapshot=(line.get("description_snapshot") or "")[:512],
            qty=parse_decimal(line.get("qty")),
            foreign_net=parse_decimal(line.get("foreign_net")),
            currency=line.get("currency"),
            merchandise_brl=parse_decimal(line.get("merchandise_brl")),
            fx_status=line.get("fx_status") or "NONE",
        )
        db.add(row)
        db.flush()
        line_rows[(row.invoice_item_id, row.shipment_item_id)] = row
    for comp in preview["components"]:
        c = CostComponent(
            version_id=version.id,
            component_type=comp["component_type"],
            source_kind=comp["source_kind"],
            source_id=comp.get("source_id"),
            amount_orig=parse_decimal(comp.get("amount_orig")),
            currency=comp.get("currency"),
            amount_brl=parse_decimal(comp.get("amount_brl")),
            included=bool(comp.get("included")),
            allocation_method=comp.get("allocation_method") or "VALUE",
            fx_rule=comp.get("fx_rule"),
            status=comp.get("status") or "OK",
            notes=comp.get("notes"),
        )
        db.add(c)
        db.flush()
        for a in comp.get("allocations") or []:
            ident = (a.get("invoice_item_id"), a.get("shipment_item_id"))
            line = line_rows.get(ident)
            if line is None:
                continue
            db.add(
                CostAllocation(
                    component_id=c.id,
                    line_id=line.id,
                    amount_brl=parse_decimal(a.get("amount_brl")) or Decimal("0"),
                    residual_flag=bool(a.get("residual_flag")),
                )
            )
    version.included_total_brl = parse_decimal(preview.get("included_total_brl"))
    version.gross_total_brl = parse_decimal(preview.get("gross_total_brl"))
    version.partial_coverage = bool(preview.get("partial_coverage"))
    version.snapshot = {
        "coverage": preview["facts"]["coverage"],
        "products": preview["products"],
        "invoices": preview["facts"]["invoices"],
        "fx": preview["facts"].get("fx"),
        "subtitle": "Inclui tributos em valor bruto. Não representa tratamento contábil ou fiscal de recuperabilidade.",
    }
    db.flush()
    reconciliation_public.replace_pairs_for_version(db, version.id, preview["pairs"])


def recalculate(
    db: Session,
    case_id: int,
    *,
    actor_id: str,
    kind: str,
    line_links: list[dict] | None = None,
    methods: dict | None = None,
    manuals: dict | None = None,
) -> CostingVersion:
    case = repo.get_case(db, case_id)
    if not case:
        raise CostingNotFound("CostingCase", case_id)
    kind = (kind or "ESTIMATED").upper()
    if kind not in ("ESTIMATED", "REVISED", "REALIZED"):
        raise CostingValidation("kind deve ser ESTIMATED, REVISED ou REALIZED")
    draft = repo.get_draft(db, case.id, kind)
    if draft is None:
        draft = CostingVersion(
            case_id=case.id,
            version_number=repo.next_version_number(db, case.id),
            kind=kind,
            status="DRAFT",
        )
        db.add(draft)
        db.flush()
    preview = preview_payload(
        db, case, kind=kind, line_links=line_links, methods=methods, manuals=manuals
    )
    _persist_preview(db, draft, preview)
    case.version += 1
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="costing_version",
        entity_id=str(draft.id),
        action="recalculate",
        details=kind,
    )
    return draft


def publish_version(
    db: Session,
    version_id: int,
    *,
    actor_id: str,
    reason: str | None = None,
    allow_partial: bool = False,
) -> CostingVersion:
    version = repo.get_version(db, version_id)
    if not version:
        raise CostingNotFound("CostingVersion", version_id)
    if version.status != "DRAFT":
        raise CostingConflict("Só rascunho pode ser publicado", code="not_draft")
    case = repo.get_case(db, version.case_id)
    pairs = reconciliation_public.list_pairs_for_version(db, version.id)
    blocking = [p for p in pairs if p.blocks_publish and p.status == "OPEN"]
    if blocking:
        raise PublishBlocked(
            "Publicação bloqueada por reconciliação",
            details={"pairs": [p.pair_type for p in blocking]},
        )
    if version.kind in ("REVISED", "REALIZED") and version.partial_coverage:
        raise PublishBlocked(
            "Cobertura incompleta bloqueia publicação REVISED/REALIZED completa",
            details={"coverage": "INCOMPLETE"},
        )
    if version.kind == "ESTIMATED" and version.partial_coverage:
        if not allow_partial or not (reason or "").strip():
            raise PublishBlocked(
                "ESTIMATED com cobertura incompleta só publica rotulado, com reason",
                details={"coverage": "INCOMPLETE", "require": "allow_partial+reason"},
            )
    if not version.lines:
        raise PublishBlocked("Versão sem linhas")
    # qty 0 already blocked by CHECK / pairs
    if case.current_published_id:
        prev = repo.get_version(db, case.current_published_id)
        if prev and prev.status == "PUBLISHED":
            prev.status = "SUPERSEDED"
            version.previous_version_id = prev.id
    version.status = "PUBLISHED"
    version.published_at = _now()
    version.published_by_actor_id = actor_id
    version.publish_reason = (reason or "").strip() or None
    case.current_published_id = version.id
    case.version += 1
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="costing_version",
        entity_id=str(version.id),
        action="publish",
        reason_code=version.kind,
        details=version.publish_reason,
    )
    return version


def revise_from_published(
    db: Session,
    version_id: int,
    *,
    actor_id: str,
    kind: str,
) -> CostingVersion:
    source = repo.get_version(db, version_id)
    if not source:
        raise CostingNotFound("CostingVersion", version_id)
    if source.status != "PUBLISHED":
        raise CostingConflict("Revisão parte de versão publicada")
    if source.status == "PUBLISHED":
        # published is immutable; new draft
        pass
    kind = (kind or source.kind).upper()
    case = repo.get_case(db, source.case_id)
    return recalculate(db, case.id, actor_id=actor_id, kind=kind)
