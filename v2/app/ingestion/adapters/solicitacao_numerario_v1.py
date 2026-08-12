"""Adapter solicitacao_numerario_v1 — Solicitação de Numerário (funding request from customs broker).

Corpus: corpus_202/Solicitacao_Numerario.pdf (1 página).
Emitido por BECHTRANS para EPIC SPORTS LTDA.

Campos extraídos:
- issue_date / due_date
- s_reference (INV. 181/202/203/244/245/246) — múltiplas referências de invoice
- n_reference (D00358/26), awb_bl, invoice_ref_first
- exporter (HEROES SRL)
- fob_amount_eur, fob_amount_brl, fob_fx_rate
- freight_amount_usd, freight_amount_brl, freight_fx_rate
- insurance_brl
- cif_amount_eur, cif_amount_brl, cif_fx_rate
- debit_bank, debit_agency, debit_account
- Expense/tax lines: AFRMM, ICMS, II, IPI, PIS, COFINS, TAXA_SISCOMEX, FRETE_INT, etc.
- declared_total_brl, declared_total_expenses_brl
- payee_name, payee_cnpj, payee_bank, payee_agency, payee_account, payee_pix
- invoice_refs (list) — base do multi-owner matching

Notas:
- Valores monetários em R$ (BRL) para despesas/impostos
- FOB/CIF têm moeda estrangeira + R$ + taxa de câmbio
- Total declarado deve igualar soma das despesas
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion import staging_commands
from app.ingestion import storage as quarantine_storage
from app.ingestion.errors import IngestionError
from app.ingestion.models import IngestionOccurrence
from app.ingestion.parse_it import parse_it_date, parse_it_number

ADAPTER_ID = "solicitacao_numerario_v1"
ADAPTER_VERSION = "1"
DOC_TYPE = "SOLICITACAO_NUMERARIO"


def _compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_brl(s: str) -> Decimal | None:
    """Parse R$ values: '1.425.554,64' → Decimal('1425554.64')."""
    cleaned = re.sub(r"R\$\s*", "", s).strip()
    return parse_it_number(cleaned)


def _parse_fx_triplet(line: str) -> tuple[str | None, Decimal | None, Decimal | None, Decimal | None]:
    """Extract (currency, foreign_amount, brl_amount, fx_rate) from a line.

    Pattern: 'EUR 288.195,20 R$ 1.706.259,68 5,9205000 19/06/2026'
    or:       'USD 3.875,00 R$ 20.000,04 5,1613000 19/06/2026'
    """
    m = re.search(
        r"\b(EUR|USD|GBP|CHF|JPY|CNY)\s+([\d.,]+)\s+"
        r"R\$\s*([\d.,]+)\s+"
        r"([\d,]+)",
        line,
        re.IGNORECASE,
    )
    if not m:
        return None, None, None, None
    currency = m.group(1).upper()
    foreign_amount = parse_it_number(m.group(2))
    brl_amount = parse_it_number(m.group(3))
    fx_rate = parse_it_number(m.group(4))
    return currency, foreign_amount, brl_amount, fx_rate


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ExpenseLine:
    label: str
    code: str
    amount_brl: Decimal
    category: str  # "tax" | "expense"
    position: int


@dataclass
class AdapterRawResult:
    # Header
    issue_date_iso: str | None
    due_date_iso: str | None
    # Recipient
    recipient_name: str | None
    recipient_tax_id: str | None
    # References
    s_reference: str | None
    invoice_refs: list[str]  # parsed from S/REFERÊNCIA
    n_reference: str | None
    awb_bl: str | None
    invoice_ref_first: str | None
    # Exporter
    exporter: str | None
    # Trade amounts
    fob_currency: str | None
    fob_foreign_amount: Decimal | None
    fob_brl_amount: Decimal | None
    fob_fx_rate: Decimal | None
    additions_brl: Decimal | None
    deductions_brl: Decimal | None
    freight_currency: str | None
    freight_foreign_amount: Decimal | None
    freight_brl_amount: Decimal | None
    freight_fx_rate: Decimal | None
    insurance_brl: Decimal | None
    cif_currency: str | None
    cif_foreign_amount: Decimal | None
    cif_brl_amount: Decimal | None
    cif_fx_rate: Decimal | None
    # Debit account
    debit_bank: str | None
    debit_agency: str | None
    debit_account: str | None
    # Expense / tax lines
    lines: list[ExpenseLine] = field(default_factory=list)
    # Totals
    declared_total_brl: Decimal | None = None
    declared_total_expenses_brl: Decimal | None = None
    # Payee
    payee_name: str | None = None
    payee_cnpj: str | None = None
    payee_bank: str | None = None
    payee_agency: str | None = None
    payee_account: str | None = None
    payee_pix: str | None = None
    # Raw
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Known expense/tax codes for classification
# ---------------------------------------------------------------------------

_TAX_CODES: dict[str, str] = {
    "AFRMM": "AFRMM",
    "ICMS": "ICMS",
    "IMPOSTO IMPORTACAO": "II",
    "IMPOSTO IMPORTAÇÃO": "II",
    "IMPOSTO PRODUTO INDUSTRIALIZADO": "IPI",
    "PIS/PASEP": "PIS",
    "COFINS": "COFINS",
    "TAXA DE UTILIZAÇÃO DO SISCOMEX": "SISCOMEX",
    "TAXA DE UTILIZACAO DO SISCOMEX": "SISCOMEX",
}

_EXPENSE_LABELS: set[str] = {
    "FRETE INTERNACIONAL",
    "DESCONSOLIDACAO",
    "DESCONSOLIDAÇÃO",
    "ARMAZENAGEM",
    "FRETE",
    "SDA",
    "HONORARIOS",
    "HONORÁRIOS",
    "DESPESAS DIVERSAS",
    "SEGURO",
    "THC",
    "BL FEE",
}


def _classify_line(label_upper: str) -> str:
    for key in _TAX_CODES:
        if label_upper.startswith(key):
            return "tax"
    return "expense"


def _line_code(label_upper: str) -> str:
    for key, code in _TAX_CODES.items():
        if label_upper.startswith(key):
            return code
    return re.sub(r"[^A-Z0-9]", "_", label_upper[:32]).strip("_")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _extract_header(text: str) -> dict:
    """Extract header fields from first ~15 lines."""
    result: dict = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for i, line in enumerate(lines[:30]):
        low = line.lower()

        # Issue date and due date: "EMITIDO EM: 19/06/2026 12:37:23 VENCIMENTO: 26/06/2026"
        m = re.search(r"EMITIDO\s+EM[:\s]+(\d{1,2}/\d{2}/\d{4})", line, re.IGNORECASE)
        if m:
            result.setdefault("issue_date_raw", m.group(1))

        m = re.search(r"VENCIMENTO[:\s]+(\d{1,2}/\d{2}/\d{4})", line, re.IGNORECASE)
        if m:
            result.setdefault("due_date_raw", m.group(1))

        # Recipient EPIC SPORTS
        if "epic sports" in low:
            result.setdefault("recipient_name", "EPIC SPORTS LTDA")

        # Recipient tax_id: "65.751.802/0001-89"
        m = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", line)
        if m:
            result.setdefault("recipient_tax_id", m.group(1))

        # S/REFERÊNCIA: "S/REFERÊNCIA INV. 181/202/203/244/245/246 EMBARQUE MARITIMA ENTRADA"
        m = re.search(r"S/REFER[EÊ]NCIA\s+(.+?)(?:\s+EMBARQUE|$)", line, re.IGNORECASE)
        if m:
            result.setdefault("s_reference", _compact(m.group(0)))
            # Extract invoice numbers from "INV. 181/202/203/244/245/246"
            inv_m = re.search(r"INV\.?\s+([\d/]+)", line, re.IGNORECASE)
            if inv_m:
                refs = [r.strip() for r in inv_m.group(1).split("/") if r.strip()]
                result.setdefault("invoice_refs", refs)

        # N/REFERÊNCIA: "N/REFERÊNCIA D00358/26 AWB/BL HKSTS26054756 INVOICE 181"
        m = re.search(r"N/REFER[EÊ]NCIA\s+(\S+)", line, re.IGNORECASE)
        if m:
            result.setdefault("n_reference", m.group(1))

        m = re.search(r"AWB/BL\s+(\S+)", line, re.IGNORECASE)
        if m:
            result.setdefault("awb_bl", m.group(1))

        m = re.search(r"INVOICE\s+(\d+)", line, re.IGNORECASE)
        if m:
            result.setdefault("invoice_ref_first", m.group(1))

        # Exporter: "EXPORTADOR HEROES SRL"
        m = re.search(r"EXPORTADOR\s+(.+)", line, re.IGNORECASE)
        if m:
            result.setdefault("exporter", _compact(m.group(1)))

    return result


def _extract_trade_amounts(text: str) -> dict:
    """Extract FOB, freight, CIF, insurance from structured lines."""
    result: dict = {}

    for line in text.splitlines():
        strip = line.strip()
        up = strip.upper()

        if up.startswith("FOB "):
            curr, foreign, brl, rate = _parse_fx_triplet(strip)
            if foreign is not None:
                result["fob_currency"] = curr
                result["fob_foreign_amount"] = foreign
                result["fob_brl_amount"] = brl
                result["fob_fx_rate"] = rate

        elif up.startswith("ACRÉSCIMO") or up.startswith("ACRESCIMO"):
            m = re.search(r"R\$\s*([\d.,]+)", strip)
            if m:
                result["additions_brl"] = parse_it_number(m.group(1))

        elif up.startswith("DEDUÇÃO") or up.startswith("DEDUCAO"):
            m = re.search(r"R\$\s*([\d.,]+)", strip)
            if m:
                result["deductions_brl"] = parse_it_number(m.group(1))

        elif up.startswith("FRETE ") and "VALOR" not in up and "DESP" not in up:
            # "FRETE USD 3.875,00 R$ 20.000,04 5,1613000 19/06/2026"
            curr, foreign, brl, rate = _parse_fx_triplet(strip)
            if foreign is not None:
                result["freight_currency"] = curr
                result["freight_foreign_amount"] = foreign
                result["freight_brl_amount"] = brl
                result["freight_fx_rate"] = rate

        elif up.startswith("SEGURO ") and "R$" in strip:
            m = re.search(r"R\$\s*([\d.,]+)", strip)
            if m:
                result["insurance_brl"] = parse_it_number(m.group(1))

        elif up.startswith("VALOR CIF"):
            curr, foreign, brl, rate = _parse_fx_triplet(strip)
            if foreign is not None:
                result["cif_currency"] = curr
                result["cif_foreign_amount"] = foreign
                result["cif_brl_amount"] = brl
                result["cif_fx_rate"] = rate

    return result


def _extract_debit_account(text: str) -> dict:
    """Extract bank debit info from 'DESPESAS A SEREM DEBITADAS DE NOSSA CONTA:'."""
    result: dict = {}
    m = re.search(
        r"DESPESAS A SEREM DEBITADAS.*?CONTA\s*:\s*(\d+)[^\n]*?"
        r"(?:BANCO\s+(.+?)\s+AG[EÊ]NCIA\s*:\s*(\S+)\s+CONTA\s*:\s*(\S+))?",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        result["debit_account_number"] = m.group(1)

    # Simpler per-line parsing
    for line in text.splitlines():
        strip = line.strip()
        up = strip.upper()

        if "DESPESAS A SEREM DEBITADAS" in up:
            # "...CONTA: 341 BANCO ITAU S A AGÊNCIA: 0772 CONTA: 68018-7"
            bank_m = re.search(r"(\d+)\s+BANCO\s+(.+?)\s+AG[EÊ]NCIA\s*:\s*(\S+)\s+CONTA\s*:\s*(\S+)", strip, re.IGNORECASE)
            if bank_m:
                result.setdefault("debit_bank_code", bank_m.group(1))
                result.setdefault("debit_bank", _compact(bank_m.group(2)))
                result.setdefault("debit_agency", bank_m.group(3))
                result.setdefault("debit_account", bank_m.group(4))

    return result


def _extract_expense_lines(text: str) -> list[ExpenseLine]:
    """Extract individual expense/tax lines and totals.

    Lines like:
      'AFRMM R$ 2.000,00'
      'ICMS R$ 556.000,00'
    """
    lines_out: list[ExpenseLine] = []
    position = 0

    # Pattern: label starting at line start, then R$ amount
    # Stop before TOTAL and payee section
    _RE_EXPENSE = re.compile(
        r"^([A-ZÁÉÍÓÚÃÕÇÀÜ][A-ZÁÉÍÓÚÃÕÇÀÜ\s/()\.]{1,60}?)\s+R\$\s*([\d.,]+)\s*$",
        re.IGNORECASE,
    )

    in_expenses = False
    for line in text.splitlines():
        strip = line.strip()
        up = strip.upper()

        # Start capture after "CONTA: ..." debit line
        if "DESPESAS A SEREM DEBITADAS" in up or (
            re.search(r"BANCO\s+ITAU", up) and "CONTA" in up
        ):
            in_expenses = True
            continue

        if not in_expenses:
            continue

        # Stop at payee section
        if "BECHTRANS" in up and "CNPJ" in up:
            break
        if up.startswith("TOTAL DESPESAS DO PROCESSO"):
            break

        # TOTAL R$ ...
        if re.match(r"^TOTAL\s+R\$", strip, re.IGNORECASE):
            continue

        m = _RE_EXPENSE.match(strip)
        if m:
            label = _compact(m.group(1))
            amount = parse_it_number(m.group(2))
            if amount is not None and amount > 0:
                label_up = label.upper()
                cat = _classify_line(label_up)
                code = _line_code(label_up)
                lines_out.append(
                    ExpenseLine(
                        label=label,
                        code=code,
                        amount_brl=amount,
                        category=cat,
                        position=position,
                    )
                )
                position += 1

    return lines_out


def _extract_totals(text: str) -> dict:
    result: dict = {}
    for line in text.splitlines():
        strip = line.strip()
        up = strip.upper()

        # "TOTAL R$ 1.425.554,64"
        if re.match(r"^TOTAL\s+R\$\s*[\d.,]+", strip, re.IGNORECASE) and "DESPESAS" not in up:
            m = re.search(r"R\$\s*([\d.,]+)", strip)
            if m:
                result.setdefault("declared_total_brl", parse_it_number(m.group(1)))

        # "TOTAL DESPESAS DO PROCESSO R$ 1.425.554,64"
        if up.startswith("TOTAL DESPESAS DO PROCESSO"):
            m = re.search(r"R\$\s*([\d.,]+)", strip)
            if m:
                result["declared_total_expenses_brl"] = parse_it_number(m.group(1))

    return result


def _extract_payee(text: str) -> dict:
    """Extract payee (BECHTRANS) info from bottom of document."""
    result: dict = {}

    # Payee name + CNPJ from: "BECHTRANS LOGÍSTICA INTERNATIONAL LTDA CNPJ: 00.012.365/0001-36"
    m = re.search(
        r"(BECHTRANS\s+LOG[IÍ]STICA\s+INTERNATIONAL\s+LTDA|BECHTRANS\s+MATRIZ)\s*[-–]?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
        text,
        re.IGNORECASE,
    )
    if m:
        result["payee_name"] = "BECHTRANS LOGÍSTICA INTERNATIONAL LTDA"
        result["payee_cnpj"] = m.group(2)

    # Bank from: "BANCO: 341 ITAÚ UNIBANCO S.A AGÊNCIA:\n0772 VIEIRA DE MORAIS // CONTA CORRENTE: 68.018-7."
    bank_m = re.search(r"BANCO:\s*341\s+ITAÚ\s+UNIBANCO\s+S\.?A", text, re.IGNORECASE)
    if bank_m:
        result["payee_bank"] = "ITAÚ UNIBANCO S.A"
        result["payee_bank_code"] = "341"

    agency_m = re.search(r"AG[EÊ]NCIA\s*:\s*\n?\s*(\d+)", text, re.IGNORECASE)
    if not agency_m:
        agency_m = re.search(r"(\d{4})\s+VIEIRA\s+DE\s+MORAIS", text, re.IGNORECASE)
    if agency_m:
        result["payee_agency"] = agency_m.group(1)

    # Conta from: "CONTA CORRENTE: 68.018-7."
    conta_m = re.search(r"CONTA\s+CORRENTE\s*:\s*([\d.\-]+)", text, re.IGNORECASE)
    if conta_m:
        result["payee_account"] = conta_m.group(1).rstrip(".")

    # PIX from: "**CHAVE PIX: ADIANTAMENTO@BECHTRANS.COM.BR"
    pix_m = re.search(r"CHAVE\s+PIX\s*:\s*([^\s\n*]+@[^\s\n*]+)", text, re.IGNORECASE)
    if not pix_m:
        pix_m = re.search(r"\*{0,2}CHAVE\s+PIX\s*:\s*([^\s\n*]+)", text, re.IGNORECASE)
    if pix_m:
        result["payee_pix"] = pix_m.group(1).strip("*.")

    return result


# ---------------------------------------------------------------------------
# Main extract
# ---------------------------------------------------------------------------


def extract(pdf_bytes: bytes) -> AdapterRawResult:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout") or ""
        if not text.strip():
            text = page.extract_text() or ""
        pages.append(text)
    raw_text = "\n".join(pages)

    header = _extract_header(raw_text)
    trade = _extract_trade_amounts(raw_text)
    debit = _extract_debit_account(raw_text)
    expense_lines = _extract_expense_lines(raw_text)
    totals = _extract_totals(raw_text)
    payee = _extract_payee(raw_text)

    issue_iso, _ = parse_it_date(header.get("issue_date_raw"))
    due_iso, _ = parse_it_date(header.get("due_date_raw"))

    return AdapterRawResult(
        issue_date_iso=issue_iso,
        due_date_iso=due_iso,
        recipient_name=header.get("recipient_name"),
        recipient_tax_id=header.get("recipient_tax_id"),
        s_reference=header.get("s_reference"),
        invoice_refs=header.get("invoice_refs", []),
        n_reference=header.get("n_reference"),
        awb_bl=header.get("awb_bl"),
        invoice_ref_first=header.get("invoice_ref_first"),
        exporter=header.get("exporter"),
        fob_currency=trade.get("fob_currency"),
        fob_foreign_amount=trade.get("fob_foreign_amount"),
        fob_brl_amount=trade.get("fob_brl_amount"),
        fob_fx_rate=trade.get("fob_fx_rate"),
        additions_brl=trade.get("additions_brl"),
        deductions_brl=trade.get("deductions_brl"),
        freight_currency=trade.get("freight_currency"),
        freight_foreign_amount=trade.get("freight_foreign_amount"),
        freight_brl_amount=trade.get("freight_brl_amount"),
        freight_fx_rate=trade.get("freight_fx_rate"),
        insurance_brl=trade.get("insurance_brl"),
        cif_currency=trade.get("cif_currency"),
        cif_foreign_amount=trade.get("cif_foreign_amount"),
        cif_brl_amount=trade.get("cif_brl_amount"),
        cif_fx_rate=trade.get("cif_fx_rate"),
        debit_bank=debit.get("debit_bank"),
        debit_agency=debit.get("debit_agency"),
        debit_account=debit.get("debit_account"),
        lines=expense_lines,
        declared_total_brl=totals.get("declared_total_brl"),
        declared_total_expenses_brl=totals.get("declared_total_expenses_brl"),
        payee_name=payee.get("payee_name"),
        payee_cnpj=payee.get("payee_cnpj"),
        payee_bank=payee.get("payee_bank"),
        payee_agency=payee.get("payee_agency"),
        payee_account=payee.get("payee_account"),
        payee_pix=payee.get("payee_pix"),
        raw_text=raw_text,
    )


def classify(raw: AdapterRawResult) -> bool:
    return bool(raw.payee_name and raw.declared_total_brl is not None)


# ---------------------------------------------------------------------------
# Math validation
# ---------------------------------------------------------------------------


def _validate_math(raw: AdapterRawResult) -> list[dict]:
    issues: list[dict] = []

    if not raw.lines:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_EXPENSE_LINES",
                "message": "Nenhuma linha de despesa extraída da Solicitação de Numerário.",
                "target_type": "DOCUMENT",
            }
        )
        return issues

    computed = sum(line.amount_brl for line in raw.lines)
    declared = raw.declared_total_brl

    if declared is not None and abs(computed - declared) > Decimal("0.10"):
        issues.append(
            {
                "severity": "ERROR",
                "code": "MATH_TOTAL_MISMATCH",
                "message": (
                    f"Soma linhas R$ {computed:.2f} ≠ Total declarado R$ {declared:.2f} "
                    f"(diferença R$ {abs(computed - declared):.2f})"
                ),
                "target_type": "DOCUMENT",
            }
        )

    if not raw.invoice_refs:
        issues.append(
            {
                "severity": "WARNING",
                "code": "NO_INVOICE_REFS",
                "message": "S/REFERÊNCIA não contém referências de invoice.",
                "target_type": "DOCUMENT",
            }
        )

    if not raw.payee_name:
        issues.append(
            {
                "severity": "ERROR",
                "code": "MISSING_PAYEE_NAME",
                "message": "Nome do beneficiário não identificado.",
                "target_type": "DOCUMENT",
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Full adapter run
# ---------------------------------------------------------------------------


def run_adapter(
    db: Session,
    *,
    occurrence_id: int,
    actor_id: str,
    quarantine_path: Path,
) -> "IngestionDocument":  # noqa: F821
    occ = db.get(IngestionOccurrence, occurrence_id)
    if occ is None:
        from app.ingestion.errors import OccurrenceNotFound
        raise OccurrenceNotFound(occurrence_id)

    if occ.blob is None or occ.blob.physical_status != "PRESENT" or not occ.blob.storage_path:
        raise IngestionError(
            f"Blob da occurrence {occurrence_id} indisponível", code="blob_unavailable"
        )

    path = quarantine_storage.resolve_quarantine_path(quarantine_path, occ.blob.storage_path)
    if path is None or not path.is_file():
        raise IngestionError(
            f"Arquivo físico não encontrado para occurrence {occurrence_id}",
            code="blob_unavailable",
        )

    pdf_bytes = path.read_bytes()
    raw = extract(pdf_bytes)
    issues = _validate_math(raw)

    sections = [
        {"section_key": "header", "title": "Cabeçalho Numerário", "ordinal": 0},
        {"section_key": "trade", "title": "Valores Comerciais (FOB/CIF)", "ordinal": 1},
        {"section_key": "expenses", "title": "Despesas e Impostos", "ordinal": 2},
        {"section_key": "payee", "title": "Beneficiário", "ordinal": 3},
    ]

    def _loc(section: str) -> str:
        return json.dumps({"page": 0, "section": section, "source": "pypdf_layout"})

    str_or_none = lambda v: str(v) if v is not None else None

    fields = [
        # Header
        {
            "section_key": "header",
            "field_key": "issue_date",
            "value_type": "date",
            "raw_value": raw.issue_date_iso,
            "normalized_value": raw.issue_date_iso,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "due_date",
            "value_type": "date",
            "raw_value": raw.due_date_iso,
            "normalized_value": raw.due_date_iso,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "recipient_name",
            "value_type": "string",
            "raw_value": raw.recipient_name,
            "normalized_value": raw.recipient_name,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "recipient_tax_id",
            "value_type": "string",
            "raw_value": raw.recipient_tax_id,
            "normalized_value": raw.recipient_tax_id,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "s_reference",
            "value_type": "string",
            "raw_value": raw.s_reference,
            "normalized_value": raw.s_reference,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "invoice_refs_json",
            "value_type": "json",
            "raw_value": json.dumps(raw.invoice_refs),
            "normalized_value": json.dumps(raw.invoice_refs),
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "n_reference",
            "value_type": "string",
            "raw_value": raw.n_reference,
            "normalized_value": raw.n_reference,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "awb_bl",
            "value_type": "string",
            "raw_value": raw.awb_bl,
            "normalized_value": raw.awb_bl,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "invoice_ref_first",
            "value_type": "string",
            "raw_value": raw.invoice_ref_first,
            "normalized_value": raw.invoice_ref_first,
            "locator_json": _loc("header"),
        },
        {
            "section_key": "header",
            "field_key": "exporter",
            "value_type": "string",
            "raw_value": raw.exporter,
            "normalized_value": raw.exporter,
            "locator_json": _loc("header"),
        },
        # Trade amounts
        {
            "section_key": "trade",
            "field_key": "fob_currency",
            "value_type": "string",
            "raw_value": raw.fob_currency,
            "normalized_value": raw.fob_currency,
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "fob_foreign_amount",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.fob_foreign_amount),
            "normalized_value": str_or_none(raw.fob_foreign_amount),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "fob_brl_amount",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.fob_brl_amount),
            "normalized_value": str_or_none(raw.fob_brl_amount),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "fob_fx_rate",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.fob_fx_rate),
            "normalized_value": str_or_none(raw.fob_fx_rate),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "freight_currency",
            "value_type": "string",
            "raw_value": raw.freight_currency,
            "normalized_value": raw.freight_currency,
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "freight_foreign_amount",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.freight_foreign_amount),
            "normalized_value": str_or_none(raw.freight_foreign_amount),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "freight_brl_amount",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.freight_brl_amount),
            "normalized_value": str_or_none(raw.freight_brl_amount),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "freight_fx_rate",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.freight_fx_rate),
            "normalized_value": str_or_none(raw.freight_fx_rate),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "insurance_brl",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.insurance_brl),
            "normalized_value": str_or_none(raw.insurance_brl),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "cif_currency",
            "value_type": "string",
            "raw_value": raw.cif_currency,
            "normalized_value": raw.cif_currency,
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "cif_foreign_amount",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.cif_foreign_amount),
            "normalized_value": str_or_none(raw.cif_foreign_amount),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "cif_brl_amount",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.cif_brl_amount),
            "normalized_value": str_or_none(raw.cif_brl_amount),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "cif_fx_rate",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.cif_fx_rate),
            "normalized_value": str_or_none(raw.cif_fx_rate),
            "locator_json": _loc("trade"),
        },
        {
            "section_key": "trade",
            "field_key": "declared_total_brl",
            "value_type": "decimal",
            "raw_value": str_or_none(raw.declared_total_brl),
            "normalized_value": str_or_none(raw.declared_total_brl),
            "locator_json": _loc("trade"),
        },
        # Payee
        {
            "section_key": "payee",
            "field_key": "payee_name",
            "value_type": "string",
            "raw_value": raw.payee_name,
            "normalized_value": raw.payee_name,
            "locator_json": _loc("payee"),
        },
        {
            "section_key": "payee",
            "field_key": "payee_cnpj",
            "value_type": "string",
            "raw_value": raw.payee_cnpj,
            "normalized_value": raw.payee_cnpj,
            "locator_json": _loc("payee"),
        },
        {
            "section_key": "payee",
            "field_key": "payee_bank",
            "value_type": "string",
            "raw_value": raw.payee_bank,
            "normalized_value": raw.payee_bank,
            "locator_json": _loc("payee"),
        },
        {
            "section_key": "payee",
            "field_key": "payee_agency",
            "value_type": "string",
            "raw_value": raw.payee_agency,
            "normalized_value": raw.payee_agency,
            "locator_json": _loc("payee"),
        },
        {
            "section_key": "payee",
            "field_key": "payee_account",
            "value_type": "string",
            "raw_value": raw.payee_account,
            "normalized_value": raw.payee_account,
            "locator_json": _loc("payee"),
        },
        {
            "section_key": "payee",
            "field_key": "payee_pix",
            "value_type": "string",
            "raw_value": raw.payee_pix,
            "normalized_value": raw.payee_pix,
            "locator_json": _loc("payee"),
        },
    ]

    rows = []
    for line in raw.lines:
        cells = {
            "label": {"raw": line.label, "normalized": line.label},
            "code": {"raw": line.code, "normalized": line.code},
            "amount_brl": {
                "raw": str(line.amount_brl),
                "normalized": str(line.amount_brl),
            },
            "category": {"raw": line.category, "normalized": line.category},
        }
        rows.append(
            {
                "section_key": "expenses",
                "row_index": line.position,
                "row_key": f"num_{line.code}_{line.position}",
                "cells_json": json.dumps(cells, ensure_ascii=False),
            }
        )

    return staging_commands.seed_document_from_occurrence(
        db,
        occurrence_id=occurrence_id,
        actor_id=actor_id,
        doc_type=DOC_TYPE,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        sections=sections,
        fields=fields,
        rows=rows,
        issues=issues,
    )
