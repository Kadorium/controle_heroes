"""Candidatos determinísticos de Order para Fattura (A0).

Não inventa chave documental. Nunca usa supplier+invoice_number.
0 candidatos → não inventa Order. 1 → sugestão. N → lista. Commit exige order_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ingestion.fattura_line_match import (
    _cell_value,
    _dec,
    _issued_and_draft_qty,
    _product_id_from_cell,
    _row_cells,
    matching_product_items,
)
from app.orders import public as orders_public

_MAX_INSPECT = 80
_LIST_LIMIT = 200


@dataclass
class FatturaOrderCandidate:
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
class FatturaOrderSuggestion:
    candidates: list[FatturaOrderCandidate] = field(default_factory=list)
    reason: str | None = None
    supplier_used: bool = False
    supplier_unreliable: bool = False


def _ir_field(doc, key: str) -> str | None:
    for f in getattr(doc, "fields", None) or []:
        if getattr(f, "field_key", None) != key:
            continue
        if getattr(f, "review_status", None) == "CORRECTED":
            return getattr(f, "corrected_value", None)
        return getattr(f, "normalized_value", None) or getattr(f, "raw_value", None)
    return None


def _open_issue_codes(doc) -> set[str]:
    codes: set[str] = set()
    for issue in getattr(doc, "issues", None) or []:
        if getattr(issue, "status", None) not in (None, "OPEN"):
            continue
        code = getattr(issue, "code", None)
        if code:
            codes.add(str(code))
    return codes


def _pdf_product_lines(doc) -> list[tuple[int, str, Decimal, int | None]]:
    out: list[tuple[int, str, Decimal, int | None]] = []
    rows = sorted(getattr(doc, "rows", None) or [], key=lambda r: r.row_index)
    for row in rows:
        cells = _row_cells(row)
        sku = (_cell_value(cells, "sku") or "").strip()
        qty = _dec(_cell_value(cells, "quantity"))
        pid = _product_id_from_cell(_cell_value(cells, "product_id_catalog"))
        if qty is None or qty <= 0:
            continue
        if not sku and pid is None:
            continue
        out.append((row.row_index, sku, qty, pid))
    return out


def _supplier_resolution(doc) -> tuple[int | None, str]:
    codes = _open_issue_codes(doc)
    raw = _ir_field(doc, "supplier_id_catalog")
    sid = int(raw) if raw and str(raw).strip().isdigit() else None
    if "AMBIGUOUS_SUPPLIER" in codes:
        return None, "ambiguous"
    if sid is None or "SUPPLIER_NOT_FOUND" in codes:
        return None, "missing"
    return sid, "ok"


def _order_covers_residual(order, pdf_lines, remaining: dict[int, Decimal]) -> bool:
    product_items = [oi for oi in (order.items or []) if oi.product_id is not None]
    pool = dict(remaining)
    for _idx, sku, qty, pid in pdf_lines:
        matching = matching_product_items(product_items, sku=sku, product_id=pid)
        if not matching:
            return False
        take = qty
        for oi in matching:
            have = pool.get(oi.id, Decimal("0"))
            if have <= 0:
                continue
            used = have if have <= take else take
            pool[oi.id] = have - used
            take -= used
            if take == 0:
                break
        if take > 0:
            return False
    return True


def suggest_fattura_orders(db: Session, doc) -> FatturaOrderSuggestion:
    """Filtra Orders CONFIRMED por sinais reais do IR. Sem score probabilístico."""
    pdf_lines = _pdf_product_lines(doc)
    if not pdf_lines:
        return FatturaOrderSuggestion(
            reason=(
                "O documento não tem linhas de item com SKU/quantidade — "
                "não há pedido candidato."
            ),
        )

    supplier_id, supplier_state = _supplier_resolution(doc)
    supplier_unreliable = supplier_state != "ok"
    doc_currency = (_ir_field(doc, "currency") or "").strip().upper() or None

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
        seen: set[int] = set()
        skus = {sku for _i, sku, _q, _p in pdf_lines if sku}
        for sku in skus:
            pairs = orders_public.find_confirmed_order_items(
                db, sku=sku, limit=100
            )
            for order, _item in pairs:
                if order.id in seen:
                    continue
                seen.add(order.id)
                orders.append(orders_public.get_order(db, order.id))
                if len(orders) >= _MAX_INSPECT:
                    break
            if len(orders) >= _MAX_INSPECT:
                break

    candidates: list[FatturaOrderCandidate] = []
    saw_cover_no_residual = False
    saw_currency_skip = False

    for order in orders[:_MAX_INSPECT]:
        if order.status != "CONFIRMED":
            continue
        order_ccy = (order.currency or "").strip().upper()
        currency_match = not (doc_currency and order_ccy and doc_currency != order_ccy)
        if not currency_match:
            saw_currency_skip = True
            continue

        product_items = [oi for oi in (order.items or []) if oi.product_id is not None]
        if not product_items:
            continue

        issued, _draft = _issued_and_draft_qty(db, order.id)
        remaining = {
            oi.id: oi.quantity - issued.get(oi.id, Decimal("0"))
            for oi in product_items
        }
        if not _order_covers_residual(order, pdf_lines, remaining):
            # distingue cobertura vs saldo
            covered = True
            for _i, sku, _q, pid in pdf_lines:
                if not matching_product_items(
                    product_items, sku=sku, product_id=pid
                ):
                    covered = False
                    break
            if covered:
                saw_cover_no_residual = True
            continue

        evidence: list[str] = []
        if supplier_id is not None:
            evidence.append(f"Fornecedor do catálogo (id {supplier_id})")
        else:
            evidence.append("Referências das linhas (SKU/produto) — fornecedor não usado")
        evidence.append(f"{len(pdf_lines)} linha(s) do PDF cobertas pelo pedido")
        evidence.append("Saldo a faturar (qty emitida) comporta as quantidades do PDF")
        if doc_currency and order_ccy == doc_currency:
            evidence.append(f"Moeda {order_ccy} (evidência fraca)")

        candidates.append(
            FatturaOrderCandidate(
                order_id=order.id,
                order_code=order.code,
                status=order.status,
                supplier_id=order.supplier_id,
                currency=order.currency,
                evidence=evidence,
                currency_match=True,
            )
        )

    reason = None
    if not candidates:
        if supplier_unreliable and not orders:
            reason = (
                "Fornecedor ausente ou ambíguo no catálogo e nenhum pedido CONFIRMED "
                "casa as referências das linhas. Não inventamos um pedido."
            )
        elif supplier_id is not None and not orders:
            reason = (
                "Nenhum pedido CONFIRMED deste fornecedor. "
                "Não inventamos um pedido."
            )
        elif saw_cover_no_residual:
            reason = (
                "Há pedido(s) que cobrem as referências, mas o saldo já emitido "
                "não comporta as quantidades da Fattura."
            )
        elif saw_currency_skip:
            reason = (
                "Pedidos do fornecedor existem, mas a moeda não coincide com a do documento."
            )
        else:
            reason = (
                "Nenhum pedido CONFIRMED cobre todas as linhas deste documento "
                "com saldo a faturar. Não inventamos um pedido."
            )

    return FatturaOrderSuggestion(
        candidates=candidates,
        reason=reason,
        supplier_used=supplier_id is not None,
        supplier_unreliable=supplier_unreliable,
    )
