"""Candidatos determinísticos de Order para Packing List Detail (C6).

Nunca usa supplier+document_number como identidade (DEC-C6-IDENTITY).
0 candidatos → não inventa Order. 1 → sugestão. N → lista. Commit exige order_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.catalog import public as catalog_public
from app.ingestion.packing_line_match import ir_cartons
from app.logistics import public as logistics_public
from app.orders import public as orders_public

_LIST_LIMIT = 200
LINE_KIND_PRODUCT = "PRODUCT"


def _ir_field(doc, key: str) -> str | None:
    for f in getattr(doc, "fields", None) or []:
        if f.field_key != key:
            continue
        if getattr(f, "review_status", None) == "CORRECTED":
            return f.corrected_value
        return f.normalized_value or f.raw_value
    return None


def _open_issue_codes(doc) -> set[str]:
    return {
        i.code
        for i in (getattr(doc, "issues", None) or [])
        if getattr(i, "status", "OPEN") == "OPEN"
    }


@dataclass
class PackingOrderCandidate:
    order_id: int
    order_code: str
    status: str
    supplier_id: int
    currency: str
    evidence: list[str] = field(default_factory=list)
    currency_match: bool = True

    def as_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "order_code": self.order_code,
            "status": self.status,
            "supplier_id": self.supplier_id,
            "currency": self.currency,
            "evidence": list(self.evidence),
            "currency_match": self.currency_match,
        }


@dataclass
class PackingOrderSuggestion:
    candidates: list[PackingOrderCandidate] = field(default_factory=list)
    reason: str | None = None


def _supplier_resolution(db: Session, doc) -> tuple[int | None, str]:
    codes = _open_issue_codes(doc)
    raw = _ir_field(doc, "supplier_id_catalog")
    sid = int(raw) if raw and str(raw).strip().isdigit() else None
    if "AMBIGUOUS_SUPPLIER" in codes:
        return None, "ambiguous"
    if sid is not None and "SUPPLIER_NOT_FOUND" not in codes:
        return sid, "ok"
    name = (_ir_field(doc, "supplier_name") or "").strip()
    if not name:
        return None, "missing"
    hits = catalog_public.list_suppliers(db, q=name, active_only=True, limit=8, offset=0)
    needle = name.lower().replace("'", "").strip()
    exact = [
        s
        for s in hits
        if (s.name or "").strip().lower().replace("'", "") == needle
    ]
    if len(exact) == 1:
        return exact[0].id, "ok"
    tight = [
        s
        for s in hits
        if "heroe" in (s.name or "").lower() and "srl" in (s.name or "").lower()
    ]
    if len(tight) == 1:
        return tight[0].id, "ok"
    if len(exact) > 1 or len(tight) > 1 or len(hits) > 1:
        return None, "ambiguous"
    return None, "missing"


def _product_residual(db: Session, order) -> Decimal:
    total = Decimal("0")
    for oi in order.items or []:
        if getattr(oi, "line_kind", LINE_KIND_PRODUCT) != LINE_KIND_PRODUCT:
            continue
        if oi.product_id is None:
            continue
        shipped = logistics_public.shipped_qty_by_order_item(db, oi.id)
        rem = Decimal(str(oi.quantity)) - shipped
        if rem > 0:
            total += rem
    return total


def suggest_packing_orders(db: Session, doc) -> PackingOrderSuggestion:
    cartons = ir_cartons(doc)
    commercial = [c for c in cartons if not c.packaging]
    if not commercial:
        return PackingOrderSuggestion(
            reason=(
                "O packing list não tem cartons comerciais (não-4819) — "
                "não há pedido candidato."
            ),
        )
    need = sum((c.items_per_ctn for c in commercial), Decimal("0"))

    supplier_id, supplier_state = _supplier_resolution(db, doc)
    if supplier_state == "ambiguous":
        return PackingOrderSuggestion(
            reason="Fornecedor ambíguo no IR — packing não escolhe pedido em silêncio.",
        )

    orders = []
    if supplier_id is not None:
        orders = list(
            orders_public.list_orders(
                db,
                status="CONFIRMED",
                supplier_id=supplier_id,
                limit=_LIST_LIMIT,
                offset=0,
            )
        )
    else:
        return PackingOrderSuggestion(
            reason=(
                "Fornecedor do packing não resolveu no catálogo — "
                "não inventamos pedido por número do documento."
            ),
        )

    doc_currency = (_ir_field(doc, "currency") or "").strip().upper() or None
    out: list[PackingOrderCandidate] = []
    for order in orders:
        residual = _product_residual(db, order)
        if residual < need:
            continue
        evidence = ["Fornecedor do catálogo", f"Residual PRODUCT cobre {need} unidades"]
        currency_match = True
        if doc_currency and order.currency and order.currency.upper() != doc_currency:
            currency_match = False
            evidence.append(f"Moeda do pedido {order.currency} ≠ {doc_currency}")
        out.append(
            PackingOrderCandidate(
                order_id=order.id,
                order_code=order.code,
                status=order.status,
                supplier_id=order.supplier_id,
                currency=order.currency,
                evidence=evidence,
                currency_match=currency_match,
            )
        )

    if not out:
        return PackingOrderSuggestion(
            reason=(
                "Nenhum pedido CONFIRMED do fornecedor tem residual PRODUCT "
                "que cubra os cartons comerciais — não inventamos Order."
            ),
        )
    return PackingOrderSuggestion(candidates=out)
