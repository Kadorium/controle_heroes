"""Casamento Fattura IR → OrderItem PRODUCT (FIN-3B).

Uma linha do PDF vira uma InvoiceItem. Qty e preço vêm do documento.
Várias linhas do mesmo SKU podem apontar ao mesmo OrderItem.
Não inventa Product nem OrderItem. Não parte uma linha do PDF em dois itens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.billing import public as billing_public
from app.ingestion.ir_models import IngestionDocument, IngestionRow


PRICE_DIVERGENCE_MARKER = "Divergência de preço"


def _row_cells(row: IngestionRow) -> dict:
    try:
        return json.loads(row.cells_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _cell_value(cells: dict, col: str) -> str | None:
    cell = cells.get(col)
    if cell is None:
        return None
    if isinstance(cell, dict):
        if cell.get("corrected") is not None:
            return cell["corrected"]
        return cell.get("normalized") or cell.get("raw")
    return str(cell)


def _dec(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _dstr(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


@dataclass
class LineBlocker:
    code: str
    message: str
    sku: str | None = None


@dataclass
class CandidateView:
    order_item_id: int
    position: int
    unit_price: str | None
    remaining: str


@dataclass
class PdfLineMatch:
    row_index: int
    sku: str
    pdf_qty: str
    pdf_unit_price: str | None
    unit: str | None
    order_item_id: int | None
    order_unit_price: str | None
    remaining_before: str | None
    candidate_count: int
    candidates: list[CandidateView]
    price_mismatch: bool
    ambiguous_price: bool

    def as_params(self) -> dict:
        return {
            "row_index": self.row_index,
            "sku": self.sku,
            "pdf_qty": self.pdf_qty,
            "pdf_unit_price": self.pdf_unit_price,
            "order_item_id": self.order_item_id,
            "order_unit_price": self.order_unit_price,
            "remaining_before": self.remaining_before,
            "candidate_count": self.candidate_count,
            "candidates": [
                {
                    "order_item_id": c.order_item_id,
                    "position": c.position,
                    "unit_price": c.unit_price,
                    "remaining": c.remaining,
                }
                for c in self.candidates
            ],
            "price_mismatch": self.price_mismatch,
            "ambiguous_price": self.ambiguous_price,
        }


@dataclass
class FatturaLinePlan:
    matches: list[PdfLineMatch] = field(default_factory=list)
    blockers: list[LineBlocker] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    commitment_only: bool = False
    draft_overcommit: bool = False
    items_payload: list[dict] = field(default_factory=list)
    price_divergence_lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blockers and not self.commitment_only

    @property
    def order_item_ids(self) -> list[int]:
        ids: list[int] = []
        seen: set[int] = set()
        for m in self.matches:
            if m.order_item_id is None:
                continue
            if m.order_item_id not in seen:
                seen.add(m.order_item_id)
                ids.append(m.order_item_id)
        return ids


def _product_id_from_cell(raw: str | None) -> int | None:
    if not raw:
        return None
    s = raw.strip()
    if not s.lstrip("-").isdigit():
        return None
    n = int(s)
    return n if n > 0 else None


def _issued_and_draft_qty(db: Session, order_id: int) -> tuple[dict[int, Decimal], dict[int, Decimal]]:
    avail = billing_public.order_qty_availability(db, order_id)
    issued: dict[int, Decimal] = {}
    for row in avail:
        oid = int(row["order_item_id"])
        issued[oid] = _dec(str(row["issued_qty"])) or Decimal("0")
    draft: dict[int, Decimal] = {}
    drafts = billing_public.list_invoices(db, order_id=order_id, status="DRAFT", limit=200)
    for inv in drafts:
        for it in inv.items or []:
            oid = int(it.order_item_id)
            draft[oid] = draft.get(oid, Decimal("0")) + it.quantity
    return issued, draft


def plan_fattura_lines(db: Session, doc: IngestionDocument, order) -> FatturaLinePlan:
    """Casa cada linha IR a um OrderItem PRODUCT; não escreve nada."""
    plan = FatturaLinePlan()
    product_items = [oi for oi in (order.items or []) if oi.product_id is not None]
    if not product_items:
        plan.commitment_only = True
        plan.blockers.append(
            LineBlocker(
                code="fattura_no_billable_lines",
                message="nenhuma linha faturável",
            )
        )
        return plan

    issued, draft_qty = _issued_and_draft_qty(db, order.id)
    remaining: dict[int, Decimal] = {}
    for oi in product_items:
        remaining[oi.id] = oi.quantity - issued.get(oi.id, Decimal("0"))

    rows = sorted(doc.rows or [], key=lambda r: r.row_index)
    if not rows:
        plan.blockers.append(
            LineBlocker(
                code="fattura_sku_not_on_order",
                message="Fattura sem linhas de item — não é possível faturar o documento.",
            )
        )
        return plan

    this_take: dict[int, Decimal] = {}

    for row in rows:
        cells = _row_cells(row)
        sku = (_cell_value(cells, "sku") or "").strip()
        qty = _dec(_cell_value(cells, "quantity"))
        pdf_price = _dec(_cell_value(cells, "unit_price"))
        unit = _cell_value(cells, "unit") or None
        pdf_pid = _product_id_from_cell(_cell_value(cells, "product_id_catalog"))

        if qty is None or qty <= 0:
            plan.blockers.append(
                LineBlocker(
                    code="fattura_sku_not_on_order",
                    message=(
                        f"Linha {row.row_index} do PDF sem quantidade válida"
                        + (f" (SKU {sku})" if sku else "")
                        + "."
                    ),
                    sku=sku or None,
                )
            )
            continue
        if not sku and pdf_pid is None:
            plan.blockers.append(
                LineBlocker(
                    code="fattura_sku_not_on_order",
                    message=f"Linha {row.row_index} do PDF sem SKU — não casa com o pedido.",
                )
            )
            continue

        same_key: list = []
        for oi in product_items:
            if pdf_pid is not None and oi.product_id == pdf_pid:
                same_key.append(oi)
                continue
            snap = (oi.sku_snapshot or "").strip()
            if sku and snap == sku:
                same_key.append(oi)

        # unique by id, keep position order
        seen_ids: set[int] = set()
        unique_same: list = []
        for oi in sorted(same_key, key=lambda x: x.position):
            if oi.id in seen_ids:
                continue
            seen_ids.add(oi.id)
            unique_same.append(oi)

        if not unique_same:
            plan.blockers.append(
                LineBlocker(
                    code="fattura_sku_not_on_order",
                    message=(
                        f"SKU {sku or pdf_pid} do PDF não está no pedido. "
                        "Selecione outro pedido, inclua a linha PRODUCT, ou rejeite o documento."
                    ),
                    sku=sku or str(pdf_pid),
                )
            )
            plan.matches.append(
                PdfLineMatch(
                    row_index=row.row_index,
                    sku=sku or str(pdf_pid or ""),
                    pdf_qty=_dstr(qty) or "0",
                    pdf_unit_price=_dstr(pdf_price),
                    unit=unit,
                    order_item_id=None,
                    order_unit_price=None,
                    remaining_before=None,
                    candidate_count=0,
                    candidates=[],
                    price_mismatch=False,
                    ambiguous_price=False,
                )
            )
            continue

        fitting = [oi for oi in unique_same if remaining.get(oi.id, Decimal("0")) >= qty]
        cand_views = [
            CandidateView(
                order_item_id=oi.id,
                position=oi.position,
                unit_price=_dstr(oi.unit_price),
                remaining=_dstr(remaining.get(oi.id, Decimal("0"))) or "0",
            )
            for oi in unique_same
        ]
        prices = {
            _dstr(oi.unit_price)
            for oi in fitting
        }
        ambiguous = len(fitting) > 1 and len(prices) > 1

        if not fitting:
            best = unique_same[0]
            rem = remaining.get(best.id, Decimal("0"))
            already = issued.get(best.id, Decimal("0"))
            plan.blockers.append(
                LineBlocker(
                    code="fattura_qty_exceeds_remaining",
                    message=(
                        f"SKU {sku}: quantidade do PDF ({qty}) excede o saldo a faturar "
                        f"no item #{best.id}: pedida={best.quantity}, já emitida={already}, "
                        f"nesta Fattura={qty}, restante={rem}."
                    ),
                    sku=sku,
                )
            )
            plan.matches.append(
                PdfLineMatch(
                    row_index=row.row_index,
                    sku=sku,
                    pdf_qty=_dstr(qty) or "0",
                    pdf_unit_price=_dstr(pdf_price),
                    unit=unit,
                    order_item_id=best.id,
                    order_unit_price=_dstr(best.unit_price),
                    remaining_before=_dstr(rem),
                    candidate_count=len(unique_same),
                    candidates=cand_views,
                    price_mismatch=False,
                    ambiguous_price=ambiguous,
                )
            )
            continue

        chosen = fitting[0]
        rem_before = remaining[chosen.id]
        remaining[chosen.id] = rem_before - qty
        this_take[chosen.id] = this_take.get(chosen.id, Decimal("0")) + qty

        mismatch = (
            pdf_price is not None
            and chosen.unit_price is not None
            and pdf_price != chosen.unit_price
        )
        match = PdfLineMatch(
            row_index=row.row_index,
            sku=sku,
            pdf_qty=_dstr(qty) or "0",
            pdf_unit_price=_dstr(pdf_price),
            unit=unit,
            order_item_id=chosen.id,
            order_unit_price=_dstr(chosen.unit_price),
            remaining_before=_dstr(rem_before),
            candidate_count=len(unique_same),
            candidates=cand_views if len(unique_same) > 1 else [],
            price_mismatch=mismatch,
            ambiguous_price=ambiguous,
        )
        plan.matches.append(match)

        row_payload: dict = {
            "order_item_id": chosen.id,
            "quantity": str(qty),
            "discount_type": "NONE",
        }
        if pdf_price is not None:
            row_payload["unit_price_gross"] = str(pdf_price)
        elif chosen.unit_price is not None:
            row_payload["unit_price_gross"] = str(chosen.unit_price)
        if unit:
            row_payload["unit"] = unit
        elif chosen.unit:
            row_payload["unit"] = chosen.unit
        plan.items_payload.append(row_payload)

        if mismatch:
            plan.price_divergence_lines.append(
                f"SKU {sku} linha PDF {row.row_index}: pedido {_dstr(chosen.unit_price)} "
                f"· Fattura {_dstr(pdf_price)} (item pedido #{chosen.id})"
            )
        if len(unique_same) > 1:
            plan.warnings.append(
                f"Linha PDF {row.row_index} SKU {sku}: {len(unique_same)} candidatos no pedido; "
                f"escolhido item #{chosen.id} (posição {chosen.position}, "
                f"preço {_dstr(chosen.unit_price)}, saldo antes {_dstr(rem_before)})."
            )
        if ambiguous:
            plan.warnings.append(
                f"Ambiguidade de preço na linha PDF {row.row_index} SKU {sku}: "
                "dois itens do pedido cabem a quantidade e têm preços diferentes. "
                "O operador pode trocar o pedido ou seguir com a escolha por posição."
            )

    if plan.price_divergence_lines:
        plan.warnings.append(
            PRICE_DIVERGENCE_MARKER
            + " (Fattura ≠ pedido; a fatura segue o documento): "
            + "; ".join(plan.price_divergence_lines)
        )

    for oid, take in this_take.items():
        issued_q = issued.get(oid, Decimal("0"))
        draft_q = draft_qty.get(oid, Decimal("0"))
        ordered = next(oi.quantity for oi in product_items if oi.id == oid)
        if issued_q + draft_q + take > ordered:
            plan.draft_overcommit = True
            plan.warnings.append(
                f"Há rascunhos de fatura que, somados a esta Fattura, ultrapassam o pedido "
                f"no item #{oid} (pedida={ordered}, emitida={issued_q}, "
                f"rascunho={draft_q}, nesta Fattura={take}). "
                "O rascunho não reserva saldo; o bloqueio ocorre na emissão."
            )

    return plan


def notes_with_price_divergence(base_notes: str, plan: FatturaLinePlan) -> str:
    if not plan.price_divergence_lines:
        return base_notes
    block = (
        f"{PRICE_DIVERGENCE_MARKER} (Fattura ≠ pedido; a fatura segue o documento):\n"
        + "\n".join(plan.price_divergence_lines)
    )
    return f"{base_notes}\n\n{block}" if base_notes else block
