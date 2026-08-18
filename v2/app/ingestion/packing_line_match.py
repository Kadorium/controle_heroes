"""Casamento Packing List Detail IR → OrderItem PRODUCT (C6).

Cartons agregam por (NCM, descrição). NCM 4819 é embalagem: package físico,
sem Product / OrderItem / quantidade embarcada.

1 candidato PRODUCT com residual → auto. >1 → escolha explícita.
Linha COMMITMENT nunca recebe quantidade de embarque (DEC-C6-COMMITMENT).
Invoice não é gate (DEC-C6-INVOICE-OPTIONAL).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.ingestion.ir_models import IngestionDocument, IngestionRow
from app.logistics import public as logistics_public

LINE_KIND_PRODUCT = "PRODUCT"
LINE_KIND_COMMITMENT = "COMMITMENT"

_RE_DIMS = re.compile(
    r"([\d]+[,\.][\d]+)\s*[xX×]\s*([\d]+[,\.][\d]+)\s*[xX×]\s*([\d]+[,\.][\d]+)"
)
_STOP = frozenset(
    {
        "WITH",
        "BOX",
        "THE",
        "AND",
        "FOR",
        "CTN",
        "CTNS",
        "CARTON",
        "CARTONS",
        "PALLET",
        "ITEM",
        "ITEMS",
        "NCM",
    }
)


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
            return str(cell["corrected"]) if cell["corrected"] is not None else None
        raw = cell.get("normalized") if cell.get("normalized") is not None else cell.get("raw")
        return str(raw) if raw is not None else None
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


def ncm_digits(raw: str | None) -> str:
    return re.sub(r"\D", "", raw or "")


def is_packaging_ncm(raw: str | None) -> bool:
    return ncm_digits(raw).startswith("4819")


def normalize_desc(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").upper()).strip()


def desc_tokens(text: str | None) -> set[str]:
    return {
        t
        for t in re.findall(r"[A-Z0-9]{3,}", normalize_desc(text))
        if t not in _STOP
    }


def parse_dimensions(raw: str | None) -> tuple[str | None, str | None, str | None]:
    from app.ingestion.parse_it import parse_it_number

    m = _RE_DIMS.search(raw or "")
    if not m:
        return None, None, None
    vals = [parse_it_number(g) for g in m.groups()]
    return tuple(_dstr(v) if v is not None else None for v in vals)  # type: ignore[return-value]


def group_key(ncm: str, description: str) -> str:
    return f"{ncm_digits(ncm)}|{normalize_desc(description)}"


@dataclass
class CartonView:
    row_index: int
    pallet_no: str | None
    carton_no: str | None
    items_per_ctn: Decimal
    ncm: str
    description: str
    dimensions: str | None
    unit_net_weight_kg: str | None
    unit_gross_weight_kg: str | None
    total_net_weight_kg: str | None
    total_gross_weight_kg: str | None
    packaging: bool

    def as_dict(self) -> dict:
        return {
            "row_index": self.row_index,
            "pallet_no": self.pallet_no,
            "carton_no": self.carton_no,
            "items_per_ctn": _dstr(self.items_per_ctn),
            "ncm": self.ncm,
            "description": self.description,
            "dimensions": self.dimensions,
            "unit_net_weight_kg": self.unit_net_weight_kg,
            "unit_gross_weight_kg": self.unit_gross_weight_kg,
            "total_net_weight_kg": self.total_net_weight_kg,
            "total_gross_weight_kg": self.total_gross_weight_kg,
            "packaging": self.packaging,
        }


@dataclass
class LineCandidate:
    order_item_id: int
    position: int
    sku: str
    description: str
    remaining: str
    line_kind: str

    def as_dict(self) -> dict:
        return {
            "order_item_id": self.order_item_id,
            "position": self.position,
            "sku": self.sku,
            "description": self.description,
            "remaining": self.remaining,
            "line_kind": self.line_kind,
        }


@dataclass
class GroupMatch:
    group_key: str
    ncm: str
    description: str
    carton_count: int
    total_qty: str
    packaging: bool
    order_item_id: int | None
    remaining_before: str | None
    candidate_count: int
    candidates: list[LineCandidate] = field(default_factory=list)
    status: str = "unmatched"
    carton_row_indexes: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "group_key": self.group_key,
            "ncm": self.ncm,
            "description": self.description,
            "carton_count": self.carton_count,
            "total_qty": self.total_qty,
            "packaging": self.packaging,
            "order_item_id": self.order_item_id,
            "remaining_before": self.remaining_before,
            "candidate_count": self.candidate_count,
            "candidates": [c.as_dict() for c in self.candidates],
            "status": self.status,
            "carton_row_indexes": list(self.carton_row_indexes),
        }


@dataclass
class PackingLinePlan:
    cartons: list[CartonView] = field(default_factory=list)
    groups: list[GroupMatch] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def commercial_groups(self) -> list[GroupMatch]:
        return [g for g in self.groups if not g.packaging]

    @property
    def packaging_groups(self) -> list[GroupMatch]:
        return [g for g in self.groups if g.packaging]


def ir_cartons(doc: IngestionDocument) -> list[CartonView]:
    out: list[CartonView] = []
    rows = sorted(getattr(doc, "rows", None) or [], key=lambda r: r.row_index)
    for row in rows:
        section = getattr(row, "section_key", None)
        if section not in (None, "cartons"):
            continue
        cells = _row_cells(row)
        qty = _dec(_cell_value(cells, "items_per_ctn")) or Decimal("0")
        if qty <= 0:
            continue
        ncm = ncm_digits(_cell_value(cells, "ncm"))
        desc = _compact_cell(_cell_value(cells, "description"))
        packaging = is_packaging_ncm(ncm)
        out.append(
            CartonView(
                row_index=row.row_index,
                pallet_no=_cell_value(cells, "pallet_no"),
                carton_no=_cell_value(cells, "carton_no"),
                items_per_ctn=qty,
                ncm=ncm,
                description=desc,
                dimensions=_cell_value(cells, "dimensions"),
                unit_net_weight_kg=_cell_value(cells, "unit_net_weight_kg"),
                unit_gross_weight_kg=_cell_value(cells, "unit_gross_weight_kg"),
                total_net_weight_kg=_cell_value(cells, "total_net_weight_kg"),
                total_gross_weight_kg=_cell_value(cells, "total_gross_weight_kg"),
                packaging=packaging,
            )
        )
    return out


def _compact_cell(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _product_items(order) -> list:
    return [
        oi
        for oi in (order.items or [])
        if getattr(oi, "line_kind", LINE_KIND_PRODUCT) == LINE_KIND_PRODUCT
        and oi.product_id is not None
    ]


def _commitment_items(order) -> list:
    return [
        oi
        for oi in (order.items or [])
        if getattr(oi, "line_kind", None) == LINE_KIND_COMMITMENT or oi.product_id is None
    ]


def _residual(db: Session, oi) -> Decimal:
    shipped = logistics_public.shipped_qty_by_order_item(db, oi.id)
    return Decimal(str(oi.quantity)) - shipped


def _score(group: GroupMatch, oi) -> int:
    gt = desc_tokens(group.description)
    ot = desc_tokens(oi.description_snapshot)
    return len(gt & ot)


def _apply_choice(group: GroupMatch, choice_id: int | None) -> None:
    if choice_id is None:
        return
    for c in group.candidates:
        if c.order_item_id == choice_id:
            group.order_item_id = choice_id
            group.remaining_before = c.remaining
            group.candidate_count = 1
            group.status = "matched"
            return
    group.status = "invalid_choice"


def plan_packing_lines(
    db: Session,
    doc: IngestionDocument,
    order,
    *,
    line_choices: dict[str, int] | None = None,
) -> PackingLinePlan:
    """Agrega cartons e casa grupos comerciais com OrderItem PRODUCT."""
    cartons = ir_cartons(doc)
    plan = PackingLinePlan(cartons=cartons)
    if not cartons:
        plan.blockers.append("Nenhum carton extraído do packing list detalhado.")
        return plan

    buckets: dict[str, list[CartonView]] = {}
    for ctn in cartons:
        buckets.setdefault(group_key(ctn.ncm, ctn.description), []).append(ctn)

    product_items = _product_items(order) if order is not None else []
    commitments = _commitment_items(order) if order is not None else []
    if order is not None and not product_items and commitments:
        plan.blockers.append(
            "Pedido só tem linha COMMITMENT — vincule Product antes de embarcar quantidade."
        )

    residuals = {oi.id: _residual(db, oi) for oi in product_items}
    choices = line_choices or {}

    for key, members in buckets.items():
        first = members[0]
        total = sum((m.items_per_ctn for m in members), Decimal("0"))
        group = GroupMatch(
            group_key=key,
            ncm=first.ncm,
            description=first.description,
            carton_count=len(members),
            total_qty=_dstr(total) or "0",
            packaging=first.packaging,
            order_item_id=None,
            remaining_before=None,
            candidate_count=0,
            carton_row_indexes=[m.row_index for m in members],
        )
        if group.packaging:
            group.status = "packaging"
            plan.groups.append(group)
            continue

        if order is None:
            group.status = "needs_order"
            plan.groups.append(group)
            continue

        scored: list[tuple[int, object, Decimal]] = []
        for oi in product_items:
            rem = residuals.get(oi.id, Decimal("0"))
            if rem < total:
                continue
            scored.append((_score(group, oi), oi, rem))
        scored.sort(key=lambda t: (-t[0], t[1].position))

        viable = [t for t in scored if t[2] >= total]
        if len(product_items) == 1 and viable:
            oi = product_items[0]
            rem = residuals[oi.id]
            group.candidates = [
                LineCandidate(
                    order_item_id=oi.id,
                    position=oi.position,
                    sku=oi.sku_snapshot,
                    description=oi.description_snapshot,
                    remaining=_dstr(rem) or "0",
                    line_kind=LINE_KIND_PRODUCT,
                )
            ]
            group.candidate_count = 1
            group.order_item_id = oi.id
            group.remaining_before = _dstr(rem)
            group.status = "matched"
        elif not viable:
            group.status = "unmatched"
            group.candidate_count = 0
        else:
            best = viable[0][0]
            tied = [t for t in viable if t[0] == best and (best > 0 or len(viable) == 1)]
            if best == 0 and len(viable) > 1:
                tied = []
            if len(tied) == 1:
                _oi = tied[0][1]
                rem = tied[0][2]
                group.candidates = [
                    LineCandidate(
                        order_item_id=_oi.id,
                        position=_oi.position,
                        sku=_oi.sku_snapshot,
                        description=_oi.description_snapshot,
                        remaining=_dstr(rem) or "0",
                        line_kind=LINE_KIND_PRODUCT,
                    )
                ]
                group.candidate_count = 1
                group.order_item_id = _oi.id
                group.remaining_before = _dstr(rem)
                group.status = "matched"
            else:
                pool = tied if tied else viable
                group.candidates = [
                    LineCandidate(
                        order_item_id=t[1].id,
                        position=t[1].position,
                        sku=t[1].sku_snapshot,
                        description=t[1].description_snapshot,
                        remaining=_dstr(t[2]) or "0",
                        line_kind=LINE_KIND_PRODUCT,
                    )
                    for t in pool
                ]
                group.candidate_count = len(group.candidates)
                group.status = "ambiguous"

        _apply_choice(group, choices.get(group.group_key))
        plan.groups.append(group)

    for g in plan.commercial_groups:
        if g.status == "ambiguous":
            plan.blockers.append(
                f"Grupo '{g.description}' tem {g.candidate_count} itens de pedido — escolha explícita."
            )
        elif g.status == "unmatched":
            plan.blockers.append(
                f"Grupo '{g.description}' NCM {g.ncm} não casa com item PRODUCT do pedido."
            )
        elif g.status == "invalid_choice":
            plan.blockers.append(f"Escolha inválida para o grupo '{g.description}'.")
        elif g.status == "needs_order":
            plan.blockers.append("Informe o pedido explicitamente — packing não inventa Order.")
        elif g.status == "matched" and g.order_item_id is not None:
            rem = _dec(g.remaining_before) or Decimal("0")
            need = _dec(g.total_qty) or Decimal("0")
            if need > rem:
                plan.blockers.append(
                    f"Quantidade do packing ({need}) excede residual ({rem}) no item #{g.order_item_id}."
                )

    if not plan.commercial_groups and not plan.packaging_groups:
        plan.blockers.append("Packing list sem grupos comerciais nem embalagem 4819.")
    elif not plan.commercial_groups:
        plan.blockers.append("Packing só tem cartons 4819 (embalagem) — sem quantidade a embarcar.")

    return plan
