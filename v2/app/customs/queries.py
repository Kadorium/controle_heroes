"""Customs queries — I5-1/I5-2."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.customs import repository as repo
from app.customs.errors import DoganaleNotFound, ProcessNotFound
from app.customs.models import CustomsDoganale, CustomsDoganaleVersion, ImportProcess
from app.logistics import public as logistics_public


def get_import_process(db: Session, process_id: int) -> ImportProcess:
    p = repo.get_process(db, process_id)
    if not p:
        raise ProcessNotFound(process_id)
    return p


def list_import_processes(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ImportProcess]:
    return repo.list_processes(db, status=status, limit=limit, offset=offset)


def process_counts_by_status(db: Session) -> dict[str, int]:
    from sqlalchemy import func

    from app.customs.models import IMPORT_PROCESS_STATUSES

    rows = (
        db.query(ImportProcess.status, func.count(ImportProcess.id))
        .group_by(ImportProcess.status)
        .all()
    )
    out = {s: 0 for s in IMPORT_PROCESS_STATUSES}
    for status, cnt in rows:
        out[str(status)] = int(cnt or 0)
    operational = sum(v for k, v in out.items() if k != "CANCELLED")
    return {**out, "operational_total": operational}


def find_process_for_invoice(db: Session, invoice_id: int) -> ImportProcess | None:
    link = repo.find_invoice_link(db, invoice_id)
    if not link:
        return None
    return repo.get_process(db, link.process_id)


def find_process_for_shipment(db: Session, shipment_id: int) -> ImportProcess | None:
    link = repo.find_shipment_link(db, shipment_id)
    if not link:
        return None
    return repo.get_process(db, link.process_id)


def invoice_item_residuals(db: Session, process_id: int) -> list[dict]:
    process = get_import_process(db, process_id)
    rows: list[dict] = []
    for link in process.invoices:
        inv = billing_public.get_invoice(db, link.invoice_id)
        for it in inv.items:
            allocated = repo.sum_allocated_invoice_item(db, it.id)
            qty = Decimal(str(it.quantity))
            rows.append(
                {
                    "invoice_id": inv.id,
                    "invoice_item_id": it.id,
                    "product_sku": it.sku_snapshot,
                    "quantity": str(qty),
                    "allocated_qty": str(allocated),
                    "residual_qty": str(qty - allocated),
                }
            )
    return rows


def shipment_item_residuals(db: Session, process_id: int) -> list[dict]:
    process = get_import_process(db, process_id)
    rows: list[dict] = []
    for link in process.shipments:
        shipment = logistics_public.get_shipment(db, link.shipment_id)
        for it in shipment.items:
            allocated = repo.sum_allocated_shipment_item(db, it.id)
            qty = Decimal(str(it.quantity))
            rows.append(
                {
                    "shipment_id": shipment.id,
                    "shipment_item_id": it.id,
                    "order_item_id": it.order_item_id,
                    "quantity": str(qty),
                    "allocated_qty": str(allocated),
                    "residual_qty": str(qty - allocated),
                }
            )
    return rows


def get_doganale_for_process(db: Session, process_id: int) -> CustomsDoganale | None:
    get_import_process(db, process_id)
    return repo.get_doganale_by_process(db, process_id)


def require_doganale_for_process(db: Session, process_id: int) -> CustomsDoganale:
    dog = get_doganale_for_process(db, process_id)
    if not dog:
        raise DoganaleNotFound(f"process:{process_id}")
    return dog


def list_doganale_versions(db: Session, process_id: int) -> list[CustomsDoganaleVersion]:
    dog = get_doganale_for_process(db, process_id)
    if not dog:
        return []
    return repo.list_versions(db, dog.id)


def get_current_doganale_version(db: Session, process_id: int) -> CustomsDoganaleVersion | None:
    dog = get_doganale_for_process(db, process_id)
    if not dog:
        return None
    return repo.get_current_version(db, dog.id)


def list_process_divergences(db: Session, process_id: int) -> list:
    get_import_process(db, process_id)
    return repo.list_divergences(db, process_id)


def list_process_provenances(db: Session, process_id: int) -> list:
    get_import_process(db, process_id)
    return repo.list_provenances(db, process_id)


def get_payee(db: Session, payee_id: int):
    from app.customs.errors import PayeeNotFound

    row = repo.get_payee(db, payee_id)
    if not row:
        raise PayeeNotFound(payee_id)
    return row


def list_payees(db: Session, *, limit: int = 100, offset: int = 0):
    return repo.list_payees(db, limit=limit, offset=offset)


def get_funding_request(db: Session, funding_id: int):
    from app.customs.errors import FundingNotFound

    fr = repo.get_funding(db, funding_id)
    if not fr:
        raise FundingNotFound(funding_id)
    return fr


def list_funding_requests(db: Session, process_id: int):
    get_import_process(db, process_id)
    return repo.list_fundings(db, process_id)


def get_nationalization(db: Session, nat_id: int):
    from app.customs.errors import NationalizationNotFound

    n = repo.get_nationalization(db, nat_id)
    if not n:
        raise NationalizationNotFound(nat_id)
    return n


def get_nationalization_item(db: Session, item_id: int):
    from app.customs.models import NationalizationItem

    return db.query(NationalizationItem).filter(NationalizationItem.id == item_id).first()


def list_nationalizations(db: Session, process_id: int):
    get_import_process(db, process_id)
    return repo.list_nationalizations(db, process_id)


def sum_nationalized_qty_by_product(db: Session, product_id: int) -> Decimal:
    return repo.sum_confirmed_nationalized_by_product(db, product_id)


def sum_nationalized_qty_bulk(db: Session, product_ids: list[int] | set[int]) -> dict[int, Decimal]:
    from sqlalchemy import func

    from app.customs.models import Nationalization, NationalizationItem

    ids = sorted({int(i) for i in product_ids})
    if not ids:
        return {}
    rows = (
        db.query(
            NationalizationItem.product_id,
            func.coalesce(func.sum(NationalizationItem.quantity), 0),
        )
        .join(Nationalization, NationalizationItem.nationalization_id == Nationalization.id)
        .filter(
            Nationalization.status == "CONFIRMED",
            NationalizationItem.product_id.in_(ids),
        )
        .group_by(NationalizationItem.product_id)
        .all()
    )
    return {int(pid): Decimal(str(qty or 0)) for pid, qty in rows}


def _qty_s(value) -> str:
    q = Decimal(str(value or 0))
    return f"{q:.4f}".rstrip("0").rstrip(".") or "0"


def clearance_residuals_by_product(
    db: Session, product_ids: list[int] | set[int] | None = None
) -> dict[str, object]:
    """Residual de desembaraço por produto (lote). Itens sem product_id vão para unassigned."""
    from sqlalchemy import func

    from app.customs.models import (
        ImportProcess,
        ImportProcessInvoiceItem,
        ImportProcessShipmentItem,
        Nationalization,
        NationalizationItem,
    )

    open_status = ("DRAFT", "SUBMITTED", "IN_CLEARANCE", "PARTIALLY_CLEARED")
    wanted = set(int(i) for i in product_ids) if product_ids is not None else None

    nat_si = (
        db.query(
            NationalizationItem.shipment_item_id.label("sid"),
            func.coalesce(func.sum(NationalizationItem.quantity), 0).label("used"),
        )
        .join(Nationalization, NationalizationItem.nationalization_id == Nationalization.id)
        .filter(
            Nationalization.status == "CONFIRMED",
            NationalizationItem.shipment_item_id.isnot(None),
        )
        .group_by(NationalizationItem.shipment_item_id)
        .subquery()
    )
    ship_alloc = (
        db.query(
            ImportProcessShipmentItem.shipment_item_id,
            func.coalesce(func.sum(ImportProcessShipmentItem.allocated_qty), 0),
            func.coalesce(func.max(nat_si.c.used), 0),
        )
        .join(ImportProcess, ImportProcess.id == ImportProcessShipmentItem.process_id)
        .outerjoin(nat_si, nat_si.c.sid == ImportProcessShipmentItem.shipment_item_id)
        .filter(ImportProcess.status.in_(open_status))
        .group_by(ImportProcessShipmentItem.shipment_item_id)
        .all()
    )
    prod_ship = logistics_public.product_ids_for_shipment_items(
        db, [row[0] for row in ship_alloc]
    )

    nat_ii = (
        db.query(
            NationalizationItem.invoice_item_id.label("iid"),
            func.coalesce(func.sum(NationalizationItem.quantity), 0).label("used"),
        )
        .join(Nationalization, NationalizationItem.nationalization_id == Nationalization.id)
        .filter(
            Nationalization.status == "CONFIRMED",
            NationalizationItem.invoice_item_id.isnot(None),
        )
        .group_by(NationalizationItem.invoice_item_id)
        .subquery()
    )
    processes_with_ship = (
        db.query(ImportProcessShipmentItem.process_id).distinct().subquery()
    )
    inv_alloc = (
        db.query(
            ImportProcessInvoiceItem.invoice_item_id,
            func.coalesce(func.sum(ImportProcessInvoiceItem.allocated_qty), 0),
            func.coalesce(func.max(nat_ii.c.used), 0),
        )
        .join(ImportProcess, ImportProcess.id == ImportProcessInvoiceItem.process_id)
        .outerjoin(nat_ii, nat_ii.c.iid == ImportProcessInvoiceItem.invoice_item_id)
        .filter(
            ImportProcess.status.in_(open_status),
            ~ImportProcess.id.in_(db.query(processes_with_ship.c.process_id)),
        )
        .group_by(ImportProcessInvoiceItem.invoice_item_id)
        .all()
    )
    prod_inv = billing_public.invoice_item_product_ids(db, [row[0] for row in inv_alloc])

    by_product: dict[int, Decimal] = {}
    unassigned = Decimal("0")

    def _acc(pid, allocated, used):
        nonlocal unassigned
        residual = max(Decimal(str(allocated or 0)) - Decimal(str(used or 0)), Decimal("0"))
        if residual <= 0:
            return
        if pid is None:
            unassigned += residual
            return
        pid = int(pid)
        if wanted is not None and pid not in wanted:
            return
        by_product[pid] = by_product.get(pid, Decimal("0")) + residual

    for sid, allocated, used in ship_alloc:
        _acc(prod_ship.get(int(sid)), allocated, used)
    for iid, allocated, used in inv_alloc:
        _acc(prod_inv.get(int(iid)), allocated, used)

    return {
        "by_product": {pid: _qty_s(qty) for pid, qty in by_product.items()},
        "unassigned_qty": _qty_s(unassigned),
        "unassigned": unassigned > 0,
    }


def blocked_exceptions(db: Session, *, limit: int = 20) -> list[dict]:
    """Bloqueio derivado: divergência ERROR, sem Doganale ativa, residual ou numerário divergente."""
    from app.customs.funding_commands import funding_divergence
    from app.customs.models import (
        CustomsDivergence,
        CustomsDoganale,
        CustomsDoganaleVersion,
        CustomsFundingRequest,
        ImportProcess,
    )

    open_status = ("DRAFT", "SUBMITTED", "IN_CLEARANCE", "PARTIALLY_CLEARED")
    processes = (
        db.query(ImportProcess)
        .filter(ImportProcess.status.in_(open_status))
        .order_by(ImportProcess.updated_at.desc())
        .limit(200)
        .all()
    )
    if not processes:
        return []
    pids = [p.id for p in processes]
    error_div = {
        row.process_id
        for row in db.query(CustomsDivergence.process_id)
        .filter(
            CustomsDivergence.process_id.in_(pids),
            CustomsDivergence.severity == "ERROR",
            CustomsDivergence.status == "OPEN",
        )
        .distinct()
        .all()
    }
    active_dog = {
        row.process_id
        for row in (
            db.query(CustomsDoganale.process_id)
            .join(CustomsDoganaleVersion, CustomsDoganaleVersion.doganale_id == CustomsDoganale.id)
            .filter(
                CustomsDoganale.process_id.in_(pids),
                CustomsDoganaleVersion.status == "ACTIVE",
            )
            .distinct()
            .all()
        )
    }
    out: list[dict] = []
    for p in processes:
        reasons = []
        if p.id in error_div:
            reasons.append("divergência em aberto")
        if p.id not in active_dog and p.status in ("IN_CLEARANCE", "PARTIALLY_CLEARED", "SUBMITTED"):
            reasons.append("declaração sem versão ativa")
        funds = (
            db.query(CustomsFundingRequest)
            .filter(
                CustomsFundingRequest.process_id == p.id,
                CustomsFundingRequest.status == "CONFIRMED",
            )
            .all()
        )
        if any(funding_divergence(fr) != 0 for fr in funds):
            reasons.append("numerário divergente")
        if not reasons:
            continue
        out.append(
            {
                "kind": "customs_blocked",
                "severity": "blocker",
                "title": p.code or f"Importação {p.id}",
                "reason": "; ".join(reasons),
                "entity_id": p.id,
                "href": f"/customs/{p.id}",
                "since": p.updated_at.isoformat() if p.updated_at else None,
                "module": "customs",
            }
        )
        if len(out) >= limit:
            break
    return out


def dec_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _line_dict(row) -> dict:
    return {
        "id": row.id,
        "position": row.position,
        "label": row.label,
        "code": row.code,
        "amount": dec_str(row.amount),
        "currency": row.currency,
        "notes": row.notes,
    }


def process_cost_facts(db: Session, process_id: int) -> dict:
    """Alocações + Numerário separados. Não expõe structured_total como custo."""
    process = get_import_process(db, process_id)
    fundings = list_funding_requests(db, process_id)
    funding_payloads = []
    for fr in fundings:
        funding_payloads.append(
            {
                "id": fr.id,
                "status": fr.status,
                "reference": fr.reference,
                "notes": fr.notes,
                "currency": fr.currency,
                "declared_total": dec_str(fr.declared_total),
                "value_bases": [_line_dict(x) for x in fr.value_bases],
                "tax_lines": [_line_dict(x) for x in fr.tax_lines],
                "expense_lines": [_line_dict(x) for x in fr.expense_lines],
                "payable_link_ids": [lk.payable_id for lk in fr.payable_links],
            }
        )
    return {
        "process_id": process.id,
        "code": process.code,
        "external_reference": process.external_reference,
        "status": process.status,
        "invoice_ids": [lnk.invoice_id for lnk in process.invoices],
        "shipment_ids": [lnk.shipment_id for lnk in process.shipments],
        "invoice_item_allocations": [
            {
                "invoice_item_id": a.invoice_item_id,
                "allocated_qty": dec_str(a.allocated_qty),
            }
            for a in process.invoice_items
        ],
        "shipment_item_allocations": [
            {
                "shipment_item_id": a.shipment_item_id,
                "allocated_qty": dec_str(a.allocated_qty),
            }
            for a in process.shipment_items
        ],
        "fundings": funding_payloads,
    }
