"""Registry tipado de adapters de ingestão — run/classify unificados (J3-UIV)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.ingestion.adapters import (
    fattura_doganale_v1,
    fattura_heroes_v1,
    ordine_heroes_v1,
    ordine_heroes_xlsx_v1,
    packing_list_detail_v1,
    packing_list_grouped_v1,
    print_declaration_v1,
    solicitacao_numerario_v1,
)
from app.ingestion.errors import IngestionError
from app.ingestion.ir_models import IngestionDocument


RunFn = Callable[..., IngestionDocument]
BuildPayloadFn = Callable[..., dict]


@dataclass(frozen=True)
class AdapterEntry:
    adapter_id: str
    doc_type: str
    label: str
    mime_kinds: tuple[str, ...]  # "pdf" | "xlsx"
    run: RunFn
    classify_hint: Callable[[bytes, str | None], tuple[bool, str]]
    build_payload: BuildPayloadFn | None = None


def _pdf_hint_ordine(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "ordine" in name and not name.endswith((".xlsx", ".xls")):
        return True, "filename sugere Ordine PDF"
    try:
        text = data[:8000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "ordine di acquisto" in text or ("heroe" in text and "ordine" in text):
        return True, "texto PDF sugere Ordine Heroes"
    return False, "não classificado"


def _pdf_hint_fattura(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "fattura" in name and "doganale" not in name:
        return True, "filename sugere Fattura"
    try:
        text = data[:12000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "fattura" in text and "doganale" not in text and "scadenze" in text:
        return True, "texto PDF sugere Fattura vendita"
    if "fattura" in text and "doganale" not in text:
        return True, "texto PDF sugere Fattura"
    return False, "não classificado"


def _pdf_hint_doganale(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "doganale" in name:
        return True, "filename sugere Fattura Doganale"
    try:
        text = data[:12000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "doganale" in text or "fattura doganale" in text:
        return True, "texto PDF sugere Fattura Doganale"
    return False, "não classificado"


def _pdf_hint_pl_detail(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "packinglist" in name.replace("_", "") and "grouped" not in name:
        return True, "filename sugere Packing List detalhado"
    if "packing" in name and "grouped" not in name:
        return True, "filename sugere Packing List"
    try:
        text = data[:12000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "packing list" in text and "grouped" not in text:
        return True, "texto PDF sugere Packing List"
    return False, "não classificado"


def _pdf_hint_pl_grouped(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "grouped" in name:
        return True, "filename sugere Packing List Grouped"
    try:
        text = data[:12000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "grouped" in text and "packing" in text:
        return True, "texto PDF sugere Packing List Grouped"
    return False, "não classificado"


def _pdf_hint_print_decl(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "declaration" in name or "printdeclaration" in name.replace("_", ""):
        return True, "filename sugere Print Declaration"
    try:
        text = data[:12000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "declaration" in text and "print" in text:
        return True, "texto PDF sugere Print Declaration"
    return False, "não classificado"


def _pdf_hint_numerario(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if "numerario" in name or "solicita" in name:
        return True, "filename sugere Solicitação de Numerário"
    try:
        text = data[:16000].decode("latin-1", errors="ignore").lower()
    except Exception:
        return False, "não classificado"
    if "numer" in text and ("solicita" in text or "funding" in text or "aduaneir" in text):
        return True, "texto PDF sugere Solicitação de Numerário"
    return False, "não classificado"


def _xlsx_hint(data: bytes, filename: str | None) -> tuple[bool, str]:
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return True, "extensão XLSX"
    if data[:4] == b"PK\x03\x04":
        return True, "ZIP/OOXML (possível XLSX)"
    return False, "não classificado"


def _run_wrapped(mod: Any) -> RunFn:
    def _run(
        db: Session,
        *,
        occurrence_id: int,
        actor_id: str,
        quarantine_path: Path,
    ) -> IngestionDocument:
        return mod.run_adapter(
            db,
            occurrence_id=occurrence_id,
            actor_id=actor_id,
            quarantine_path=quarantine_path,
        )

    return _run


def _build_payload_wrapped(mod: Any) -> BuildPayloadFn:
    def _build(
        db: Session,
        *,
        occurrence_id: int,
        quarantine_path: Path,
    ) -> dict:
        return mod.build_ir_payload(
            db,
            occurrence_id=occurrence_id,
            quarantine_path=quarantine_path,
        )

    return _build


ADAPTERS: dict[str, AdapterEntry] = {
    ordine_heroes_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=ordine_heroes_v1.ADAPTER_ID,
        doc_type=ordine_heroes_v1.DOC_TYPE,
        label="Ordine Heroes (PDF)",
        mime_kinds=("pdf",),
        run=_run_wrapped(ordine_heroes_v1),
        classify_hint=_pdf_hint_ordine,
        build_payload=_build_payload_wrapped(ordine_heroes_v1),
    ),
    fattura_heroes_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=fattura_heroes_v1.ADAPTER_ID,
        doc_type=fattura_heroes_v1.DOC_TYPE,
        label="Fattura Heroes",
        mime_kinds=("pdf",),
        run=_run_wrapped(fattura_heroes_v1),
        classify_hint=_pdf_hint_fattura,
    ),
    packing_list_detail_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=packing_list_detail_v1.ADAPTER_ID,
        doc_type=packing_list_detail_v1.DOC_TYPE,
        label="Packing List detalhado",
        mime_kinds=("pdf",),
        run=_run_wrapped(packing_list_detail_v1),
        classify_hint=_pdf_hint_pl_detail,
    ),
    packing_list_grouped_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=packing_list_grouped_v1.ADAPTER_ID,
        doc_type=packing_list_grouped_v1.DOC_TYPE,
        label="Packing List Grouped",
        mime_kinds=("pdf",),
        run=_run_wrapped(packing_list_grouped_v1),
        classify_hint=_pdf_hint_pl_grouped,
    ),
    fattura_doganale_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=fattura_doganale_v1.ADAPTER_ID,
        doc_type=fattura_doganale_v1.DOC_TYPE,
        label="Fattura Doganale",
        mime_kinds=("pdf",),
        run=_run_wrapped(fattura_doganale_v1),
        classify_hint=_pdf_hint_doganale,
    ),
    print_declaration_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=print_declaration_v1.ADAPTER_ID,
        doc_type=print_declaration_v1.DOC_TYPE,
        label="Print Declaration",
        mime_kinds=("pdf",),
        run=_run_wrapped(print_declaration_v1),
        classify_hint=_pdf_hint_print_decl,
    ),
    solicitacao_numerario_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=solicitacao_numerario_v1.ADAPTER_ID,
        doc_type=solicitacao_numerario_v1.DOC_TYPE,
        label="Solicitação de Numerário",
        mime_kinds=("pdf",),
        run=_run_wrapped(solicitacao_numerario_v1),
        classify_hint=_pdf_hint_numerario,
    ),
    ordine_heroes_xlsx_v1.ADAPTER_ID: AdapterEntry(
        adapter_id=ordine_heroes_xlsx_v1.ADAPTER_ID,
        doc_type=ordine_heroes_xlsx_v1.DOC_TYPE,
        label="Ordine Heroes (XLSX)",
        mime_kinds=("xlsx",),
        run=_run_wrapped(ordine_heroes_xlsx_v1),
        classify_hint=_xlsx_hint,
    ),
}

DOC_TYPE_TO_ADAPTER: dict[str, str] = {
    e.doc_type: e.adapter_id for e in ADAPTERS.values()
}


class UnknownAdapter(IngestionError):
    def __init__(self, adapter_id: str):
        super().__init__(f"Adapter desconhecido: {adapter_id}", code="unknown_adapter")


def get_adapter(adapter_id: str) -> AdapterEntry:
    entry = ADAPTERS.get(adapter_id)
    if entry is None:
        raise UnknownAdapter(adapter_id)
    return entry


def resolve_adapter_id(*, adapter_id: str | None, doc_type: str | None) -> str:
    if adapter_id:
        if adapter_id not in ADAPTERS:
            raise UnknownAdapter(adapter_id)
        return adapter_id
    if doc_type:
        mapped = DOC_TYPE_TO_ADAPTER.get(doc_type)
        if mapped:
            return mapped
        raise UnknownAdapter(f"doc_type:{doc_type}")
    # default histórico: Ordine PDF
    return ordine_heroes_v1.ADAPTER_ID


def list_adapters() -> list[AdapterEntry]:
    return list(ADAPTERS.values())


def classify_occurrence_bytes(
    data: bytes,
    *,
    filename: str | None,
    detected_mime: str | None,
) -> list[dict[str, Any]]:
    """Sugestões tipadas sem executar adapter completo."""
    mime = (detected_mime or "").lower()
    name = (filename or "").lower()
    is_xlsx = (
        "sheet" in mime
        or "excel" in mime
        or name.endswith((".xlsx", ".xlsm", ".xls"))
        or (data[:4] == b"PK\x03\x04" and name.endswith((".xlsx", ".xlsm")))
    )
    kind = "xlsx" if is_xlsx else "pdf"
    hits: list[dict[str, Any]] = []
    for entry in ADAPTERS.values():
        if kind not in entry.mime_kinds:
            continue
        ok, explanation = entry.classify_hint(data, filename)
        if ok:
            hits.append(
                {
                    "adapter_id": entry.adapter_id,
                    "doc_type": entry.doc_type,
                    "label": entry.label,
                    "confidence": "likely",
                    "explanation": explanation,
                }
            )
    if not hits and kind == "xlsx":
        entry = ADAPTERS[ordine_heroes_xlsx_v1.ADAPTER_ID]
        hits.append(
            {
                "adapter_id": entry.adapter_id,
                "doc_type": entry.doc_type,
                "label": entry.label,
                "confidence": "possible",
                "explanation": "arquivo XLSX — adapter padrão Ordine XLSX",
            }
        )
    return hits
