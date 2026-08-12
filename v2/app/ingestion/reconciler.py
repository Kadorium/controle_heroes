"""Reconciler cross-documentale — dossiê ingestão J3-I5.

Cruza campos entre os documentos de um DocumentSet (Fattura, PL Detail,
PL Grouped, Fattura Doganale, PrintDeclaration) e emite issues de reconciliação.

Regras P0:
- PL Grouped = evidência de ambiguidade; suas divergências geram WARNING, não ERROR
- NCM 4819 (embalagem) ≠ produtos comerciais — não gera conflito de qty
- PrintDeclaration = documental; não reconciliado por qty/valor
- Autoridade de qty/valor: Fattura comercial (fattura_heroes_v1)
- Autoridade de peso/pallet: Fattura Doganale (fattura_doganale_v1)
- PL Detail = evidência física de carton-level

Funções puras — sem I/O, sem ORM além de leitura de IR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.ingestion.staging_queries import get_document_set, list_documents_for_set

NCM_PACKAGING_PREFIX = "4819"
TOL_WEIGHT = Decimal("1.0")   # kg tolerance for weight comparison
TOL_VALUE = Decimal("0.02")   # EUR tolerance for value comparison


@dataclass
class ReconciliationIssue:
    code: str
    severity: str  # WARNING | ERROR | INFO
    message: str
    doc_types_involved: list[str]
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers to read IR fields/rows
# ---------------------------------------------------------------------------


def _get_field(doc, key: str) -> str | None:
    for f in doc.fields or []:
        if f.field_key == key:
            if f.review_status == "CORRECTED":
                return f.corrected_value
            return f.normalized_value or f.raw_value
    return None


def _dec(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except Exception:
        return None


def _int_field(doc, key: str) -> int | None:
    v = _get_field(doc, key)
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _row_cells(row) -> dict:
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


# ---------------------------------------------------------------------------
# Aggregate product quantities from PL Detail rows
# ---------------------------------------------------------------------------


def _aggregate_pl_detail(doc) -> dict[str, dict[str, Any]]:
    """Returns {description_canonical: {qty, ncm, total_net_kg}} from carton rows."""
    aggregates: dict[str, dict] = {}
    for row in sorted(doc.rows or [], key=lambda r: r.row_index):
        cells = _row_cells(row)
        desc = _cell_value(cells, "description") or ""
        ncm = _cell_value(cells, "ncm") or ""
        items = _cell_value(cells, "items_per_ctn") or "0"
        net = _cell_value(cells, "total_net_weight_kg") or "0"
        is_pkg = ncm.startswith(NCM_PACKAGING_PREFIX)
        if is_pkg:
            continue
        key = desc.upper().strip()
        if key not in aggregates:
            aggregates[key] = {"qty": 0, "ncm": ncm, "total_net_kg": Decimal("0")}
        try:
            aggregates[key]["qty"] += int(items)
        except ValueError:
            pass
        try:
            aggregates[key]["total_net_kg"] += Decimal(net)
        except Exception:
            pass
    return aggregates


# ---------------------------------------------------------------------------
# Aggregate product quantities from Fattura Doganale rows
# ---------------------------------------------------------------------------


def _aggregate_doganale(doc) -> dict[str, dict[str, Any]]:
    """Returns {description_canonical: {qty, unit, ncm, total_eur}} from doganale rows."""
    agg: dict[str, dict] = {}
    for row in sorted(doc.rows or [], key=lambda r: r.row_index):
        cells = _row_cells(row)
        desc = _cell_value(cells, "description") or ""
        ncm = _cell_value(cells, "ncm") or ""
        qty_str = _cell_value(cells, "quantity") or "0"
        total_str = _cell_value(cells, "line_total") or "0"
        key = desc.upper().strip()
        if key not in agg:
            agg[key] = {"qty": Decimal("0"), "ncm": ncm, "total_eur": Decimal("0")}
        try:
            agg[key]["qty"] += Decimal(qty_str)
        except Exception:
            pass
        try:
            agg[key]["total_eur"] += Decimal(total_str)
        except Exception:
            pass
    return agg


# ---------------------------------------------------------------------------
# Aggregate from Fattura (I4 adapter — rows have sku-based EAN keys)
# ---------------------------------------------------------------------------


def _aggregate_fattura(doc) -> dict[str, dict[str, Any]]:
    """Returns {description_canonical: {qty, ncm_hint, total_eur}} from fattura rows."""
    agg: dict[str, dict] = {}
    for row in sorted(doc.rows or [], key=lambda r: r.row_index):
        cells = _row_cells(row)
        desc = _cell_value(cells, "description") or ""
        qty_str = _cell_value(cells, "quantity") or "0"
        total_str = _cell_value(cells, "line_total") or "0"
        key = desc.upper().strip()
        if not key:
            continue
        if key not in agg:
            agg[key] = {"qty": Decimal("0"), "total_eur": Decimal("0")}
        try:
            agg[key]["qty"] += Decimal(qty_str)
        except Exception:
            pass
        try:
            agg[key]["total_eur"] += Decimal(total_str)
        except Exception:
            pass
    return agg


# ---------------------------------------------------------------------------
# Main reconcile function
# ---------------------------------------------------------------------------


def reconcile_document_set(
    db: Session,
    document_set_id: int,
) -> list[ReconciliationIssue]:
    """Cross-reconcile documents in a DocumentSet.

    Returns list of ReconciliationIssue objects (not written to DB here).
    Call staging_commands.create_issue per result to persist.
    """
    issues: list[ReconciliationIssue] = []

    # Fetch documents from set
    docs_in_set = list_documents_for_set(db, document_set_id)

    by_type: dict[str, Any] = {}
    for doc in docs_in_set:
        dt = doc.doc_type
        by_type.setdefault(dt, []).append(doc)

    fattura = (by_type.get("FATTURA_VENDITA") or [None])[0]
    pl_detail = (by_type.get("PACKING_LIST_DETAIL") or [None])[0]
    pl_grouped = (by_type.get("PACKING_LIST_GROUPED") or [None])[0]
    doganale = (by_type.get("FATTURA_DOGANALE") or [None])[0]
    print_decl = (by_type.get("PRINT_DECLARATION") or [None])[0]

    # --- 1. Document number consistency ---
    ref_numbers: dict[str, str] = {}
    for doc_name, doc in [
        ("fattura", fattura),
        ("pl_detail", pl_detail),
        ("pl_grouped", pl_grouped),
        ("doganale", doganale),
    ]:
        if doc is None:
            continue
        num_key = "invoice_number" if doc.doc_type == "FATTURA_VENDITA" else "document_number"
        num = _get_field(doc, num_key)
        if num:
            ref_numbers[doc_name] = num

    unique_refs = set(ref_numbers.values())
    if len(unique_refs) > 1:
        issues.append(
            ReconciliationIssue(
                code="REF_NUMBER_MISMATCH",
                severity="ERROR",
                message=(
                    f"Documentos do dossiê têm números diferentes: {ref_numbers}. "
                    "Verificar se pertencem ao mesmo dossiê."
                ),
                doc_types_involved=list(ref_numbers.keys()),
                details={"ref_numbers": ref_numbers},
            )
        )

    # --- 2. Fattura vs Doganale: total value ---
    if fattura and doganale:
        fat_total = _dec(_get_field(fattura, "total_document"))
        dog_total = _dec(_get_field(doganale, "total_document_eur"))
        if fat_total is not None and dog_total is not None:
            if abs(fat_total - dog_total) > TOL_VALUE:
                issues.append(
                    ReconciliationIssue(
                        code="FATTURA_DOGANALE_TOTAL_MISMATCH",
                        severity="ERROR",
                        message=(
                            f"Total EUR diverge: Fattura={fat_total} vs Doganale={dog_total}. "
                            "Diferença: " + str(abs(fat_total - dog_total))
                        ),
                        doc_types_involved=["FATTURA_VENDITA", "FATTURA_DOGANALE"],
                        details={"fattura_total": str(fat_total), "doganale_total": str(dog_total)},
                    )
                )

    # --- 3. Weight comparison: PL Detail totals vs Doganale ---
    if pl_detail and doganale:
        pl_net = _dec(_get_field(pl_detail, "total_net_weight_kg"))
        dog_net = _dec(_get_field(doganale, "total_net_weight_kg"))
        pl_gross = _dec(_get_field(pl_detail, "total_gross_weight_kg"))
        dog_gross = _dec(_get_field(doganale, "total_gross_weight_kg"))

        if pl_net is not None and dog_net is not None:
            if abs(pl_net - dog_net) > TOL_WEIGHT:
                issues.append(
                    ReconciliationIssue(
                        code="NET_WEIGHT_MISMATCH",
                        severity="WARNING",
                        message=(
                            f"Peso líquido diverge: PL Detail={pl_net}kg vs Doganale={dog_net}kg."
                        ),
                        doc_types_involved=["PACKING_LIST_DETAIL", "FATTURA_DOGANALE"],
                        details={"pl_detail": str(pl_net), "doganale": str(dog_net)},
                    )
                )

    # --- 4. Pallet count: PL Detail cartons vs Doganale pallets ---
    if pl_detail and doganale:
        pl_cartons = _int_field(pl_detail, "total_cartons")
        dog_pallets = _int_field(doganale, "pallet_count")
        if pl_cartons is not None and dog_pallets is not None:
            if pl_cartons != dog_pallets:
                issues.append(
                    ReconciliationIssue(
                        code="CARTON_PALLET_COUNT_MISMATCH",
                        severity="WARNING",
                        message=(
                            f"PL Detail cartons ({pl_cartons}) ≠ Doganale pallets ({dog_pallets}). "
                            "Verificar se carton=pallet neste dossiê."
                        ),
                        doc_types_involved=["PACKING_LIST_DETAIL", "FATTURA_DOGANALE"],
                        details={"pl_cartons": pl_cartons, "doganale_pallets": dog_pallets},
                    )
                )

    # --- 5. Qty comparison: PL Detail vs Doganale (product-level) ---
    if pl_detail and doganale:
        pl_agg = _aggregate_pl_detail(pl_detail)
        dog_agg = _aggregate_doganale(doganale)

        # Find common product names (case-insensitive partial match)
        for pl_desc, pl_data in pl_agg.items():
            # Find best matching doganale description
            matched_dog_desc = None
            for dog_desc in dog_agg:
                # Match if one contains the other
                if pl_desc in dog_desc or dog_desc in pl_desc:
                    matched_dog_desc = dog_desc
                    break
            if matched_dog_desc:
                pl_qty = pl_data["qty"]
                dog_qty = int(dog_agg[matched_dog_desc]["qty"])
                if pl_qty != dog_qty:
                    issues.append(
                        ReconciliationIssue(
                            code="QTY_PL_DOGANALE_MISMATCH",
                            severity="WARNING",
                            message=(
                                f"Quantidade diverge para '{pl_desc}': "
                                f"PL Detail={pl_qty} vs Doganale={dog_qty}."
                            ),
                            doc_types_involved=["PACKING_LIST_DETAIL", "FATTURA_DOGANALE"],
                            details={
                                "description": pl_desc,
                                "pl_detail_qty": pl_qty,
                                "doganale_qty": dog_qty,
                            },
                        )
                    )

    # --- 6. PL Grouped vs Doganale (ambiguity evidence only — WARNING, not ERROR) ---
    if pl_grouped and doganale:
        dog_agg = _aggregate_doganale(doganale)
        for row in pl_grouped.rows or []:
            cells = _row_cells(row)
            desc = _cell_value(cells, "description") or ""
            ncm = _cell_value(cells, "ncm") or ""
            units_str = _cell_value(cells, "units")
            is_pkg = (_cell_value(cells, "is_packaging") or "false").lower() == "true"

            if is_pkg or not units_str:
                continue

            desc_key = desc.upper().strip()
            matched = None
            for dk in dog_agg:
                if desc_key in dk or dk in desc_key:
                    matched = dk
                    break

            if matched:
                try:
                    grouped_qty = int(units_str)
                except ValueError:
                    continue
                dog_qty = int(dog_agg[matched]["qty"])
                if grouped_qty != dog_qty:
                    issues.append(
                        ReconciliationIssue(
                            code="AMBIGUITY_GROUPED_VS_DOGANALE",
                            severity="WARNING",  # P0: never ERROR for PL Grouped
                            message=(
                                f"PL Grouped '{desc}' units={grouped_qty} ≠ "
                                f"Doganale qty={dog_qty}. "
                                "PL Grouped é evidência de ambiguidade — não bloqueia commit."
                            ),
                            doc_types_involved=["PACKING_LIST_GROUPED", "FATTURA_DOGANALE"],
                            details={
                                "description": desc,
                                "pl_grouped_units": grouped_qty,
                                "doganale_qty": dog_qty,
                            },
                        )
                    )

    # --- 7. PrintDeclaration invoice_ref vs Fattura number ---
    if print_decl and fattura:
        decl_ref = _get_field(print_decl, "invoice_ref")
        fat_num = _get_field(fattura, "invoice_number")
        if decl_ref and fat_num and decl_ref != fat_num:
            issues.append(
                ReconciliationIssue(
                    code="PRINT_DECL_INVOICE_REF_MISMATCH",
                    severity="WARNING",
                    message=(
                        f"PrintDeclaration referencia fattura '{decl_ref}' mas "
                        f"Fattura number='{fat_num}'."
                    ),
                    doc_types_involved=["PRINT_DECLARATION", "FATTURA_VENDITA"],
                    details={"decl_ref": decl_ref, "fattura_number": fat_num},
                )
            )

    # --- 8. Origin annotation cross-check ---
    origin_values: dict[str, str] = {}
    for doc_name, doc in [
        ("pl_detail", pl_detail),
        ("pl_grouped", pl_grouped),
        ("doganale", doganale),
    ]:
        if doc is None:
            continue
        orig = _get_field(doc, "origin_country_declared")
        if orig:
            origin_values[doc_name] = orig

    unique_origins = set(v.lower() for v in origin_values.values())
    if len(unique_origins) > 1:
        issues.append(
            ReconciliationIssue(
                code="ORIGIN_ANNOTATION_MISMATCH",
                severity="WARNING",
                message=(
                    f"Campo 'Country of origin' diverge entre documentos: {origin_values}."
                ),
                doc_types_involved=list(origin_values.keys()),
                details=origin_values,
            )
        )

    return issues
