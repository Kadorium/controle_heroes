"""Commit Packing List Detail → Logistics Shipment PLANNED (C6).

Ingestion orquestra; Logistics é dono do Shipment. Só APIs públicas.
Sem order_id no header do Shipment. Modal nulo (PLANNED). Sem duplicata silenciosa.
Idempotência: um SUCCEEDED por documento IR (não só operation_key).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.documents import public as documents_public
from app.ingestion import storage as quarantine_storage
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.dossier_commands import (
    DossierCommitBlockedByIssues,
    DossierConflictFingerprint,
)
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.ingestion.packing_line_match import (
    group_key,
    parse_dimensions,
    plan_packing_lines,
)
from app.ingestion.packing_order_candidates import suggest_packing_orders
from app.ingestion.staging_queries import get_document_detail
from app.logistics import public as logistics_public
from app.orders import public as orders_public


class PackingOrderIdRequired(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "order_id é obrigatório — packing não usa número do documento como identidade.",
            code="packing_order_id_required",
        )


class PackingShipmentPickRequired(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "Há mais de um embarque candidato — escolha shipment_id explicitamente.",
            code="packing_shipment_id_required",
        )


class PackingLineAmbiguous(IngestionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="packing_line_ambiguous")


class PackingCommitmentUnbound(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "Não embarca quantidade enquanto a linha for COMMITMENT — vincule Product.",
            code="packing_commitment_unbound",
        )


def _field_value(doc, key: str) -> str | None:
    for f in getattr(doc, "fields", None) or []:
        if f.field_key != key:
            continue
        if getattr(f, "review_status", None) == "CORRECTED":
            return f.corrected_value
        return f.normalized_value or f.raw_value
    return None


def _choices_map(line_choices: list | None) -> dict[str, int]:
    out: dict[str, int] = {}
    if not line_choices:
        return out
    for raw in line_choices:
        if isinstance(raw, dict):
            key = str(raw.get("group_key") or "")
            oid = raw.get("order_item_id")
        else:
            key = str(getattr(raw, "group_key", "") or "")
            oid = getattr(raw, "order_item_id", None)
        if key and oid is not None:
            out[key] = int(oid)
    return out


def _record_op(
    db: Session,
    attempt: IngestionCommitAttempt,
    op_key: str,
    *,
    status: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    error_message: str | None = None,
    details_json: str | None = None,
) -> None:
    op = IngestionCommitOperation(
        attempt_id=attempt.id,
        op_key=op_key,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        error_message=error_message,
        details_json=details_json,
    )
    db.add(op)
    db.flush()


def _lg(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except logistics_public.LogisticsError as exc:
        raise IngestionError(exc.message, code=getattr(exc, "code", "logistics_error")) from exc


def _reload(db: Session, shipment) -> object:
    """Public get_shipment after writes — expire so joinedload isn't stale."""
    db.expire(shipment)
    return _lg(logistics_public.get_shipment, db, shipment.id)


def _prior_entity(db: Session, document_id: int, op_key: str) -> int | None:
    attempts = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.document_id == document_id)
        .order_by(IngestionCommitAttempt.id.desc())
        .all()
    )
    for att in attempts:
        for op in att.operations or []:
            if op.op_key == op_key and op.status == "SUCCEEDED" and op.entity_id:
                try:
                    return int(op.entity_id)
                except (TypeError, ValueError):
                    return None
    return None


def _last_succeeded_attempt(db: Session, document_id: int) -> IngestionCommitAttempt | None:
    return (
        db.query(IngestionCommitAttempt)
        .filter(
            IngestionCommitAttempt.document_id == document_id,
            IngestionCommitAttempt.status == "SUCCEEDED",
        )
        .order_by(IngestionCommitAttempt.id.desc())
        .first()
    )


def _shipment_id_from_attempt(attempt: IngestionCommitAttempt) -> int | None:
    for op in attempt.operations or []:
        if op.entity_type == "shipment" and op.status == "SUCCEEDED" and op.entity_id:
            try:
                return int(op.entity_id)
            except (TypeError, ValueError):
                continue
    return None


@dataclass
class PackingPreviewOperation:
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = field(default_factory=dict)


@dataclass
class ShipmentTargetView:
    shipment_id: int
    code: str
    status: str
    compatible: bool
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "shipment_id": self.shipment_id,
            "code": self.code,
            "status": self.status,
            "compatible": self.compatible,
            "evidence": list(self.evidence),
        }


@dataclass
class PackingPreviewResult:
    document_id: int
    fingerprint: str
    operations: list[PackingPreviewOperation]
    open_error_count: int
    can_commit: bool
    order_candidates: list[dict] = field(default_factory=list)
    order_candidates_reason: str | None = None
    shipment_targets: list[dict] = field(default_factory=list)
    shipment_targets_reason: str | None = None
    line_matches: list[dict] = field(default_factory=list)
    cartons: list[dict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    resolved_order_id: int | None = None
    resolved_shipment_id: int | None = None
    will_create_shipment: bool = False
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_shipment_id: int | None = None


def _compute_fingerprint(
    document_id: int,
    *,
    order_id: int | None,
    shipment_id: int | None,
    line_choices: dict[str, int],
) -> str:
    canonical = json.dumps(
        {
            "doc_id": document_id,
            "order_id": order_id,
            "shipment_id": shipment_id,
            "line_choices": sorted(line_choices.items()),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _shipment_compatible(shipment) -> bool:
    if shipment is None:
        return False
    if getattr(shipment, "cancelled_at", None) is not None:
        return False
    return shipment.status == "PLANNED"


def collect_shipment_targets(db: Session, doc) -> list[ShipmentTargetView]:
    doc_num = (_field_value(doc, "document_number") or "").strip()
    found = []
    if doc_num:
        found = list(
            logistics_public.find_shipments_by_reference(db, "PACKING_LIST", doc_num)
        )
    prior_id = _prior_entity(db, doc.id, "create_shipment_planned")
    if prior_id is not None and all(s.id != prior_id for s in found):
        try:
            found.append(logistics_public.get_shipment(db, prior_id))
        except logistics_public.LogisticsError:
            pass
    out: list[ShipmentTargetView] = []
    seen: set[int] = set()
    for s in found:
        if s.id in seen:
            continue
        seen.add(s.id)
        ok = _shipment_compatible(s)
        evidence = ["Referência PACKING_LIST" if doc_num else "Tentativa anterior"]
        if not ok:
            evidence.append(f"Status {s.status} — não reutilizável em silêncio")
        elif s.items or s.packages:
            evidence.append("Já tem volumes — reuso só se for o mesmo packing")
        else:
            evidence.append("PLANNED vazio — reuso compatível")
        out.append(
            ShipmentTargetView(
                shipment_id=s.id,
                code=s.code,
                status=s.status,
                compatible=ok,
                evidence=evidence,
            )
        )
    return out


def _resolve_shipment_target(
    targets: list[ShipmentTargetView],
    shipment_id: int | None,
) -> tuple[int | None, bool, str | None]:
    """Returns (resolved_id, will_create, reason)."""
    compatible = [t for t in targets if t.compatible]
    if shipment_id is not None:
        hit = next((t for t in targets if t.shipment_id == shipment_id), None)
        if hit is not None and not hit.compatible:
            return None, False, (
                f"Embarque #{shipment_id} não é PLANNED compatível — "
                "packing não duplica em silêncio."
            )
        return shipment_id, False, None
    if not targets:
        return None, True, None
    if len(compatible) == 1 and len(targets) == 1:
        return compatible[0].shipment_id, False, None
    if len(compatible) == 1 and all(not t.compatible for t in targets if t.shipment_id != compatible[0].shipment_id):
        return compatible[0].shipment_id, False, None
    if not compatible:
        return None, False, (
            "Já existe embarque com esta packing list fora de PLANNED — "
            "não criamos duplicata. Escolha outro PLANNED ou avance no existente."
        )
    return None, False, (
        f"{len(compatible)} embarques PLANNED candidatos — escolha shipment_id; "
        "o sistema não escolhe em silêncio."
    )


def preview_commit_pl_detail(
    db: Session,
    document_id: int,
    *,
    order_id: int | None = None,
    shipment_id: int | None = None,
    line_choices: list | None = None,
) -> PackingPreviewResult:
    doc = get_document_detail(db, document_id)
    choices = _choices_map(line_choices)
    fingerprint = _compute_fingerprint(
        document_id, order_id=order_id, shipment_id=shipment_id, line_choices=choices
    )
    open_errors = sum(
        1 for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"
    )

    existing_ok = _last_succeeded_attempt(db, document_id)
    if existing_ok is not None:
        sid = _shipment_id_from_attempt(existing_ok)
        ops = [
            PackingPreviewOperation(
                op_key=op.op_key,
                description=(
                    "Embarque já gerado a partir deste packing"
                    if op.entity_type == "shipment"
                    else op.op_key.replace("_", " ")
                ),
                entity_type=op.entity_type,
                params={"entity_id": op.entity_id} if op.entity_id else {},
            )
            for op in (existing_ok.operations or [])
        ]
        return PackingPreviewResult(
            document_id=document_id,
            fingerprint=existing_ok.payload_fingerprint or fingerprint,
            operations=ops,
            open_error_count=open_errors,
            can_commit=False,
            already_committed=True,
            last_succeeded_attempt_id=existing_ok.id,
            last_succeeded_shipment_id=sid,
            resolved_shipment_id=sid,
            will_create_shipment=False,
        )

    suggestion = suggest_packing_orders(db, doc)
    targets = collect_shipment_targets(db, doc)

    blockers: list[str] = []
    resolved_order_id = order_id
    if resolved_order_id is None:
        extra = suggestion.reason or ""
        n = len(suggestion.candidates)
        if n == 1:
            extra = (
                f" Pedido sugerido #{suggestion.candidates[0].order_id} "
                f"({suggestion.candidates[0].order_code}) — confirme explicitamente."
            )
        elif n > 1:
            extra = f" {n} pedidos candidatos — escolha um explicitamente."
        blockers.append(
            "order_id é obrigatório — packing não usa número do documento como identidade."
            + extra
        )

    order = None
    if resolved_order_id is not None:
        try:
            order = orders_public.get_order(db, resolved_order_id)
        except orders_public.OrdersError as exc:
            blockers.append(str(exc))
            order = None

    plan = plan_packing_lines(db, doc, order, line_choices=choices)
    blockers.extend(plan.blockers)

    resolved_sid, will_create, ship_reason = _resolve_shipment_target(targets, shipment_id)
    if ship_reason:
        blockers.append(ship_reason)

    ops: list[PackingPreviewOperation] = [
        PackingPreviewOperation(
            op_key="store_document",
            description="Promover bytes da quarantine para Documents",
            entity_type="document",
        )
    ]
    if will_create:
        ops.append(
            PackingPreviewOperation(
                op_key="create_shipment_planned",
                description="Criar Shipment PLANNED via logistics.create_shipment (modal nulo)",
                entity_type="shipment",
                params={"modal": None},
            )
        )
    elif resolved_sid is not None:
        ops.append(
            PackingPreviewOperation(
                op_key="reuse_shipment",
                description=f"Reutilizar Shipment PLANNED #{resolved_sid}",
                entity_type="shipment",
                params={"shipment_id": resolved_sid},
            )
        )
    for g in plan.commercial_groups:
        if g.order_item_id is not None:
            ops.append(
                PackingPreviewOperation(
                    op_key=f"add_shipment_item_{g.group_key}",
                    description=(
                        f"Embarcar {g.total_qty} do OrderItem #{g.order_item_id} "
                        f"({g.description})"
                    ),
                    entity_type="shipment_item",
                    params={
                        "order_item_id": g.order_item_id,
                        "quantity": g.total_qty,
                    },
                )
            )
    n_pkg = len(plan.cartons)
    if n_pkg:
        ops.append(
            PackingPreviewOperation(
                op_key="add_shipment_packages_batch",
                description=f"Criar {n_pkg} volume(s) CARTON a partir do packing detalhado",
                entity_type="shipment_package",
                params={"count": n_pkg},
            )
        )
    ops.append(
        PackingPreviewOperation(
            op_key="add_shipment_reference",
            description="Referência PACKING_LIST no embarque (não é identidade do pedido)",
            entity_type="shipment_reference",
        )
    )
    ops.append(
        PackingPreviewOperation(
            op_key="upsert_document_summary",
            description="Totais declarados com proveniência PACKING_LIST",
            entity_type="shipment_document_summary",
            params={"declared_provenance": "PACKING_LIST"},
        )
    )

    can_commit = (
        open_errors == 0
        and not blockers
        and resolved_order_id is not None
        and (will_create or resolved_sid is not None)
        and all(g.status == "matched" for g in plan.commercial_groups)
        and bool(plan.commercial_groups)
    )

    return PackingPreviewResult(
        document_id=document_id,
        fingerprint=fingerprint,
        operations=ops,
        open_error_count=open_errors,
        can_commit=can_commit,
        order_candidates=[c.as_dict() for c in suggestion.candidates],
        order_candidates_reason=suggestion.reason,
        shipment_targets=[t.as_dict() for t in targets],
        shipment_targets_reason=ship_reason,
        line_matches=[g.as_dict() for g in plan.groups],
        cartons=[c.as_dict() for c in plan.cartons],
        blockers=blockers,
        resolved_order_id=resolved_order_id,
        resolved_shipment_id=resolved_sid,
        will_create_shipment=will_create,
    )


def _package_spec(carton, *, promoted_doc_id: int | None) -> dict:
    length, width, height = parse_dimensions(carton.dimensions)
    spec: dict = {
        "package_type": "CARTON",
        "package_count": 1,
        "external_package_no": carton.carton_no,
        "description": carton.description,
        "raw_dimensions": carton.dimensions,
        "net_weight_kg": carton.total_net_weight_kg,
        "gross_weight_kg": carton.total_gross_weight_kg,
        "source_document_id": promoted_doc_id,
    }
    if carton.packaging:
        spec["packaging_ncm"] = carton.ncm or None
    if length and width and height:
        spec["length"] = length
        spec["width"] = width
        spec["height"] = height
        spec["dimension_unit"] = "CM"
    return spec


def commit_pl_detail(
    db: Session,
    *,
    document_id: int,
    operation_key: str,
    actor_id: str,
    attachments_path: Path,
    quarantine_path: Path,
    order_id: int | None = None,
    shipment_id: int | None = None,
    line_choices: list | None = None,
) -> IngestionCommitAttempt:
    doc = get_document_detail(db, document_id)
    if doc.doc_type != "PACKING_LIST_DETAIL":
        raise IngestionError(
            "commit-pl-detail só aceita PACKING_LIST_DETAIL (Grouped não é SoT).",
            code="packing_wrong_doc_type",
        )

    open_errors = [i for i in (doc.issues or []) if i.status == "OPEN" and i.severity == "ERROR"]
    if open_errors:
        raise DossierCommitBlockedByIssues(len(open_errors))

    existing_ok = _last_succeeded_attempt(db, document_id)
    if existing_ok is not None:
        return existing_ok

    preview = preview_commit_pl_detail(
        db,
        document_id,
        order_id=order_id,
        shipment_id=shipment_id,
        line_choices=line_choices,
    )
    if order_id is None:
        raise PackingOrderIdRequired()
    if not preview.can_commit:
        if any("COMMITMENT" in b for b in preview.blockers):
            raise PackingCommitmentUnbound()
        if any("escolha explícita" in b.lower() or "candidatos" in b.lower() for b in preview.blockers):
            if preview.shipment_targets_reason and "embarques" in (preview.shipment_targets_reason or ""):
                raise PackingShipmentPickRequired()
            raise PackingLineAmbiguous("; ".join(preview.blockers))
        raise IngestionError(
            "; ".join(preview.blockers) or "Commit packing bloqueado.",
            code="packing_commit_blocked",
        )

    choices = _choices_map(line_choices)
    fingerprint = preview.fingerprint
    existing_key = (
        db.query(IngestionCommitAttempt)
        .filter(IngestionCommitAttempt.operation_key == operation_key)
        .first()
    )
    if existing_key is not None:
        if existing_key.payload_fingerprint == fingerprint:
            return existing_key
        raise DossierConflictFingerprint(operation_key)

    attempt = IngestionCommitAttempt(
        document_id=document_id,
        operation_key=operation_key,
        payload_fingerprint=fingerprint,
        status="UNKNOWN",
        actor_id=actor_id,
    )
    db.add(attempt)
    db.flush()

    succeeded: list[str] = []
    failed: list[str] = []

    def fail(op_key: str, exc: Exception) -> IngestionCommitAttempt:
        _record_op(db, attempt, op_key, status="FAILED", error_message=str(exc)[:512])
        failed.append(op_key)
        attempt.status = "PARTIAL" if succeeded else "FAILED"
        db.flush()
        return attempt

    promoted_doc_id = _prior_entity(db, document_id, "store_document")
    try:
        if promoted_doc_id is None:
            occ = db.get(IngestionOccurrence, doc.occurrence_id)
            if occ and occ.blob and occ.blob.physical_status == "PRESENT" and occ.blob.storage_path:
                blob_path = quarantine_storage.resolve_quarantine_path(
                    quarantine_path, occ.blob.storage_path
                )
                if blob_path and blob_path.is_file():
                    pdf_bytes = blob_path.read_bytes()
                    promoted = documents_public.store_document(
                        db,
                        attachments_path=attachments_path,
                        actor_id=actor_id,
                        filename=occ.original_filename or f"pl_{document_id}.pdf",
                        content=pdf_bytes,
                        mime_type=occ.detected_mime or "application/pdf",
                    )
                    promoted_doc_id = promoted.id
        _record_op(
            db,
            attempt,
            "store_document",
            status="SUCCEEDED",
            entity_type="document",
            entity_id=str(promoted_doc_id) if promoted_doc_id else None,
        )
        succeeded.append("store_document")
    except Exception as exc:
        return fail("store_document", exc)

    order = orders_public.get_order(db, order_id)
    plan = plan_packing_lines(db, doc, order, line_choices=choices)
    shipment = None
    try:
        if preview.will_create_shipment:
            shipment = _reload(
                db,
                _lg(
                    logistics_public.create_shipment,
                    db,
                    modal=None,
                    notes=(
                        f"Packing list IR {document_id} "
                        f"ref={_field_value(doc, 'document_number') or ''}"
                    ),
                    actor_id=actor_id,
                ),
            )
            op_name = "create_shipment_planned"
        else:
            sid = preview.resolved_shipment_id
            if sid is None:
                raise PackingShipmentPickRequired()
            shipment = _lg(logistics_public.get_shipment, db, sid)
            if not _shipment_compatible(shipment):
                raise IngestionError(
                    f"Embarque #{sid} não é PLANNED compatível",
                    code="packing_shipment_incompatible",
                )
            op_name = "reuse_shipment"
        _record_op(
            db,
            attempt,
            op_name,
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
            details_json=json.dumps(
                {"shipment_code": shipment.code, "status": shipment.status, "modal": shipment.modal}
            ),
        )
        succeeded.append(op_name)
    except Exception as exc:
        return fail("create_shipment_planned", exc)

    assert shipment is not None
    item_by_order_item: dict[int, int] = {
        it.order_item_id: it.id for it in (shipment.items or [])
    }

    try:
        for g in plan.commercial_groups:
            if g.order_item_id is None:
                continue
            if g.order_item_id in item_by_order_item:
                continue
            shipment = _reload(
                db,
                _lg(
                    logistics_public.add_shipment_item,
                    db,
                    shipment.id,
                    expected_version=shipment.version,
                    order_item_id=g.order_item_id,
                    quantity=g.total_qty,
                    actor_id=actor_id,
                ),
            )
            item_by_order_item = {
                it.order_item_id: it.id for it in (shipment.items or [])
            }
        _record_op(
            db,
            attempt,
            "add_shipment_items",
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
            details_json=json.dumps({"item_count": len(shipment.items or [])}),
        )
        succeeded.append("add_shipment_items")
    except Exception as exc:
        return fail("add_shipment_items", exc)

    group_item_id: dict[str, int] = {}
    for g in plan.commercial_groups:
        if g.order_item_id is not None and g.order_item_id in item_by_order_item:
            group_item_id[g.group_key] = item_by_order_item[g.order_item_id]

    try:
        shipment = _reload(db, shipment)
        if not (shipment.packages or []):
            specs = [_package_spec(c, promoted_doc_id=promoted_doc_id) for c in plan.cartons]
            contents_template = None
            commercial = [c for c in plan.cartons if not c.packaging]
            if (
                specs
                and len(plan.commercial_groups) == 1
                and commercial
                and len({str(c.items_per_ctn) for c in commercial}) == 1
            ):
                sid = next(iter(group_item_id.values()), None)
                sample = commercial[0]
                if sid is not None:
                    contents_template = [
                        {
                            "shipment_item_id": sid,
                            "contained_quantity": str(sample.items_per_ctn),
                            "source_ncm": sample.ncm or None,
                            "source_description": sample.description,
                            "units_per_package": str(sample.items_per_ctn),
                            "unit_net_weight_kg": sample.unit_net_weight_kg,
                            "unit_gross_weight_kg": sample.unit_gross_weight_kg,
                            "source_total_net_weight_kg": sample.total_net_weight_kg,
                            "source_total_gross_weight_kg": sample.total_gross_weight_kg,
                        }
                    ]
            if specs:
                shipment = _reload(
                    db,
                    _lg(
                        logistics_public.add_shipment_packages_batch,
                        db,
                        shipment.id,
                        expected_version=shipment.version,
                        packages=specs,
                        contents_template=contents_template,
                        actor_id=actor_id,
                    ),
                )
        _record_op(
            db,
            attempt,
            "add_shipment_packages_batch",
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
            details_json=json.dumps({"package_count": len(shipment.packages or [])}),
        )
        succeeded.append("add_shipment_packages_batch")
    except Exception as exc:
        return fail("add_shipment_packages_batch", exc)

    try:
        shipment = _reload(db, shipment)
        packages = sorted(shipment.packages or [], key=lambda p: p.id)
        fallback_sid = None
        if len(plan.commercial_groups) == 1:
            fallback_sid = next(iter(group_item_id.values()), None)
            if fallback_sid is None and shipment.items:
                fallback_sid = shipment.items[0].id
        applied = 0
        for pkg, carton in zip(packages, plan.cartons):
            if carton.packaging:
                continue
            if list(pkg.contents or []):
                applied += 1
                continue
            gk = group_key(carton.ncm, carton.description)
            sid = group_item_id.get(gk) or fallback_sid
            if sid is None:
                continue
            shipment = _reload(
                db,
                _lg(
                    logistics_public.set_package_contents,
                    db,
                    shipment.id,
                    pkg.id,
                    expected_version=shipment.version,
                    contents=[
                        {
                            "shipment_item_id": sid,
                            "contained_quantity": str(carton.items_per_ctn),
                            "source_ncm": carton.ncm or None,
                            "source_description": carton.description,
                            "units_per_package": str(carton.items_per_ctn),
                            "unit_net_weight_kg": carton.unit_net_weight_kg,
                            "unit_gross_weight_kg": carton.unit_gross_weight_kg,
                            "source_total_net_weight_kg": carton.total_net_weight_kg,
                            "source_total_gross_weight_kg": carton.total_gross_weight_kg,
                        }
                    ],
                    actor_id=actor_id,
                ),
            )
            applied += 1
        commercial_n = sum(1 for c in plan.cartons if not c.packaging)
        if commercial_n and applied == 0:
            raise IngestionError(
                "Packing commit não gravou conteúdo dos cartons comerciais.",
                code="packing_commit_blocked",
            )
        _record_op(
            db,
            attempt,
            "set_package_contents",
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
            details_json=json.dumps({"applied": applied, "package_count": len(packages)}),
        )
        succeeded.append("set_package_contents")
    except Exception as exc:
        return fail("set_package_contents", exc)

    doc_num = (_field_value(doc, "document_number") or "").strip()
    try:
        already = any(
            r.reference_type == "PACKING_LIST"
            and (r.reference_value or "").strip() == doc_num
            for r in (shipment.references or [])
        )
        if doc_num and not already:
            shipment = _lg(
                logistics_public.add_shipment_reference,
                db,
                shipment.id,
                expected_version=shipment.version,
                reference_type="PACKING_LIST",
                reference_value=doc_num,
                document_id=promoted_doc_id,
                actor_id=actor_id,
            )
        _record_op(
            db,
            attempt,
            "add_shipment_reference",
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
        )
        succeeded.append("add_shipment_reference")
    except Exception as exc:
        return fail("add_shipment_reference", exc)

    try:
        net = _field_value(doc, "total_net_weight_kg")
        gross = _field_value(doc, "total_gross_weight_kg")
        cartons_n = _field_value(doc, "total_cartons")
        pallet_nos = {c.pallet_no for c in plan.cartons if c.pallet_no}
        if promoted_doc_id is not None:
            shipment = _lg(
                logistics_public.upsert_document_summary,
                db,
                shipment.id,
                expected_version=shipment.version,
                document_id=promoted_doc_id,
                declared_net_weight_kg=net,
                declared_gross_weight_kg=gross,
                declared_pallet_count=len(pallet_nos) or None,
                declared_carton_count=int(cartons_n) if cartons_n and str(cartons_n).isdigit() else len(plan.cartons),
                declared_provenance="PACKING_LIST",
                raw_notes=f"IR packing {document_id}",
                actor_id=actor_id,
            )
        _record_op(
            db,
            attempt,
            "upsert_document_summary",
            status="SUCCEEDED",
            entity_type="shipment",
            entity_id=str(shipment.id),
        )
        succeeded.append("upsert_document_summary")
    except Exception as exc:
        return fail("upsert_document_summary", exc)

    if promoted_doc_id:
        try:
            documents_public.link_document(
                db,
                document_id=promoted_doc_id,
                entity_type="shipment",
                entity_id=str(shipment.id),
                role="packing_list",
            )
        except Exception:
            pass

    if shipment.status != "PLANNED":
        attempt.status = "FAILED"
        _record_op(
            db,
            attempt,
            "planned_only_guard",
            status="FAILED",
            error_message=f"Shipment saiu de PLANNED ({shipment.status})",
        )
        db.flush()
        return attempt
    if shipment.modal is not None:
        attempt.status = "PARTIAL"
        _record_op(
            db,
            attempt,
            "planned_only_guard",
            status="FAILED",
            error_message=f"modal deveria ser nulo, veio {shipment.modal}",
        )
        db.flush()
        return attempt

    attempt.status = "SUCCEEDED" if not failed else "PARTIAL"
    db.flush()
    audit_public.record_event(
        db,
        actor_id=actor_id,
        entity_type="ingestion_commit_attempt",
        entity_id=str(attempt.id),
        action="commit_pl_detail_completed",
        reason_code="INGEST_PL_COMMIT_DONE",
        details=json.dumps(
            {
                "document_id": document_id,
                "order_id": order_id,
                "shipment_id": shipment.id,
                "status": attempt.status,
                "succeeded": succeeded,
                "failed": failed,
            }
        ),
    )
    return attempt
