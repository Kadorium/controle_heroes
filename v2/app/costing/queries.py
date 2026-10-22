"""Consultas Costing."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.costing import repository as repo
from app.costing.errors import CostingNotFound
from app.costing.money import decimal_str
from app.customs import public as customs_public
from app.reconciliation import public as reconciliation_public


def case_to_dict(db: Session, case) -> dict:
    process = customs_public.get_import_process(db, case.import_process_id)
    current = repo.get_version(db, case.current_published_id) if case.current_published_id else None
    drafts = [v for v in repo.list_versions(db, case.id) if v.status == "DRAFT"]
    return {
        "id": case.id,
        "import_process_id": case.import_process_id,
        "process_code": process.code,
        "process_reference": process.external_reference,
        "process_status": process.status,
        "freight_choice": case.freight_choice,
        "freight_choice_reason": case.freight_choice_reason,
        "version": case.version,
        "current_published_id": case.current_published_id,
        "current_kind": current.kind if current else None,
        "current_status": current.status if current else None,
        "included_total_brl": decimal_str(current.included_total_brl) if current else None,
        "partial_coverage": current.partial_coverage if current else None,
        "draft_count": len(drafts),
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "title": "Custo desembarcado por produto",
        "subtitle": (
            "Inclui tributos em valor bruto. "
            "Não representa tratamento contábil ou fiscal de recuperabilidade."
        ),
    }


def version_to_dict(db: Session, version, *, include_children: bool = True) -> dict:
    case = repo.get_case(db, version.case_id)
    payload = {
        "id": version.id,
        "case_id": version.case_id,
        "import_process_id": case.import_process_id if case else None,
        "version_number": version.version_number,
        "kind": version.kind,
        "status": version.status,
        "partial_coverage": version.partial_coverage,
        "included_total_brl": decimal_str(version.included_total_brl),
        "gross_total_brl": decimal_str(version.gross_total_brl),
        "snapshot": version.snapshot or {},
        "previous_version_id": version.previous_version_id,
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "publish_reason": version.publish_reason,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "title": "Custo desembarcado por produto",
        "subtitle": (
            "Inclui tributos em valor bruto. "
            "Não representa tratamento contábil ou fiscal de recuperabilidade."
        ),
    }
    if include_children:
        payload["lines"] = [
            {
                "id": ln.id,
                "invoice_item_id": ln.invoice_item_id,
                "shipment_item_id": ln.shipment_item_id,
                "order_item_id": ln.order_item_id,
                "product_id": ln.product_id,
                "sku_snapshot": ln.sku_snapshot,
                "description_snapshot": ln.description_snapshot,
                "qty": decimal_str(ln.qty),
                "foreign_net": decimal_str(ln.foreign_net),
                "currency": ln.currency,
                "merchandise_brl": decimal_str(ln.merchandise_brl),
                "fx_status": ln.fx_status,
            }
            for ln in version.lines
        ]
        payload["components"] = []
        for c in version.components:
            payload["components"].append(
                {
                    "id": c.id,
                    "component_type": c.component_type,
                    "source_kind": c.source_kind,
                    "source_id": c.source_id,
                    "amount_orig": decimal_str(c.amount_orig),
                    "currency": c.currency,
                    "amount_brl": decimal_str(c.amount_brl),
                    "included": c.included,
                    "allocation_method": c.allocation_method,
                    "fx_rule": c.fx_rule,
                    "status": c.status,
                    "notes": c.notes,
                    "allocations": [
                        {
                            "id": a.id,
                            "line_id": a.line_id,
                            "amount_brl": decimal_str(a.amount_brl),
                            "residual_flag": a.residual_flag,
                        }
                        for a in c.allocations
                    ],
                }
            )
        payload["products"] = (version.snapshot or {}).get("products") or []
        payload["pairs"] = [
            reconciliation_public.pair_to_dict(p)
            for p in reconciliation_public.list_pairs_for_version(db, version.id)
        ]
        if case:
            payload["expenses"] = [
                {
                    "id": e.id,
                    "category": e.category,
                    "description": e.description,
                    "amount": decimal_str(e.amount),
                    "currency": e.currency,
                    "expense_date": e.expense_date.isoformat() if e.expense_date else None,
                    "payee_snapshot": e.payee_snapshot,
                    "document_id": e.document_id,
                    "allocation_method": e.allocation_method,
                    "status": e.status,
                }
                for e in case.expenses
            ]
            payload["freight_choice"] = case.freight_choice
    return payload


def get_case(db: Session, case_id: int):
    row = repo.get_case(db, case_id)
    if not row:
        raise CostingNotFound("CostingCase", case_id)
    return row


def get_version(db: Session, version_id: int):
    row = repo.get_version(db, version_id)
    if not row:
        raise CostingNotFound("CostingVersion", version_id)
    return row


def queue(db: Session, *, limit: int = 50, offset: int = 0) -> list[dict]:
    processes = customs_public.list_import_processes(db, limit=limit, offset=offset)
    out = []
    for p in processes:
        case = repo.get_case_by_process(db, p.id)
        if case:
            out.append(case_to_dict(db, case))
        else:
            out.append(
                {
                    "id": None,
                    "import_process_id": p.id,
                    "process_code": p.code,
                    "process_reference": p.external_reference,
                    "process_status": p.status,
                    "freight_choice": None,
                    "current_published_id": None,
                    "current_kind": None,
                    "current_status": None,
                    "included_total_brl": None,
                    "partial_coverage": None,
                    "draft_count": 0,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    "title": "Custo desembarcado por produto",
                    "costing_status": "SEM_CASO",
                }
            )
    return out


def compare_versions(db: Session, left_id: int, right_id: int) -> dict:
    left = get_version(db, left_id)
    right = get_version(db, right_id)
    lprod = {(r.get("sku_snapshot"), r.get("product_id")): r for r in (left.snapshot or {}).get("products") or []}
    rprod = {(r.get("sku_snapshot"), r.get("product_id")): r for r in (right.snapshot or {}).get("products") or []}
    keys = sorted(set(lprod) | set(rprod))
    rows = []
    for k in keys:
        a, b = lprod.get(k), rprod.get(k)
        rows.append(
            {
                "sku_snapshot": k[0],
                "product_id": k[1],
                "description_snapshot": (a or b or {}).get("description_snapshot"),
                "left_qty": (a or {}).get("qty"),
                "right_qty": (b or {}).get("qty"),
                "left_total_brl": (a or {}).get("total_brl"),
                "right_total_brl": (b or {}).get("total_brl"),
                "left_unit_brl": (a or {}).get("unit_brl"),
                "right_unit_brl": (b or {}).get("unit_brl"),
            }
        )

    def _comp_key(c) -> tuple:
        return (c.component_type or "", c.source_kind or "", c.source_id or 0)

    lcomp = {_comp_key(c): c for c in left.components}
    rcomp = {_comp_key(c): c for c in right.components}
    comp_rows = []
    for k in sorted(set(lcomp) | set(rcomp)):
        a, b = lcomp.get(k), rcomp.get(k)
        comp_rows.append(
            {
                "component_type": k[0],
                "source_kind": k[1],
                "left_amount_brl": decimal_str(a.amount_brl) if a else None,
                "right_amount_brl": decimal_str(b.amount_brl) if b else None,
                "left_included": a.included if a else None,
                "right_included": b.included if b else None,
            }
        )
    return {
        "left": version_to_dict(db, left, include_children=False),
        "right": version_to_dict(db, right, include_children=False),
        "products": rows,
        "components": comp_rows,
    }


def operational_summary(db: Session) -> dict:
    """Contagens de casos publicados / rascunhos — sem listar processos."""
    from sqlalchemy import func

    from app.costing.models import CostingCase, CostingVersion

    published = int(
        db.query(func.count(CostingCase.id))
        .filter(CostingCase.current_published_id.isnot(None))
        .scalar()
        or 0
    )
    total_brl = None
    if published:
        raw = (
            db.query(func.coalesce(func.sum(CostingVersion.included_total_brl), 0))
            .join(CostingCase, CostingCase.current_published_id == CostingVersion.id)
            .scalar()
        )
        total_brl = decimal_str(raw)
    drafts = int(
        db.query(func.count(CostingVersion.id)).filter(CostingVersion.status == "DRAFT").scalar() or 0
    )
    blocked = int(
        db.query(func.count(CostingVersion.id))
        .filter(CostingVersion.status == "DRAFT", CostingVersion.partial_coverage.is_(True))
        .scalar()
        or 0
    )
    return {
        "published_cases": published,
        "included_total_brl": total_brl,
        "draft_versions": drafts,
        "blocked_drafts": blocked,
    }


def publish_blockers(db: Session, *, limit: int = 20) -> list[dict]:
    from app.costing.models import CostingCase, CostingVersion
    from app.customs import public as customs_public

    drafts = (
        db.query(CostingVersion)
        .filter(CostingVersion.status == "DRAFT", CostingVersion.partial_coverage.is_(True))
        .order_by(CostingVersion.updated_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for v in drafts:
        snap = v.snapshot if isinstance(v.snapshot, dict) else {}
        reasons = snap.get("reasons") or (snap.get("coverage") or {}).get("reasons") or []
        reason = "; ".join(str(r) for r in reasons) or "Cobertura incompleta — não publica"
        process_id = None
        try:
            case = repo.get_case(db, v.case_id)
            process_id = case.import_process_id if case else None
        except Exception:
            process_id = None
        href = f"/costing/{process_id}" if process_id else "/costing"
        title = f"Custo v{v.version_number}"
        if process_id:
            try:
                proc = customs_public.get_import_process(db, process_id)
                title = proc.code or title
            except Exception:
                title = f"Processo {process_id}"
        out.append(
            {
                "kind": "costing_blocked",
                "severity": "blocker",
                "title": title,
                "reason": reason,
                "entity_id": v.id,
                "href": href,
                "since": v.updated_at.isoformat() if v.updated_at else None,
                "module": "costing",
            }
        )
    return out
