"""Test suite J3-I6 — Numerário: adapter, commit commands, multi-owner, architecture.

Fixture: tests/fixtures/ingestion/corpus_202/Solicitacao_Numerario.pdf (when present).

Tests organized:
1. Adapter (pure) — extract() from raw text + classify()
2. Adapter extract() from real PDF (skipped if fixture absent)
3. Math validation — total mismatch + no expense lines
4. Commit commands (mocked DB):
   a. preview_numerario — planned ops per process
   b. commit happy path — SUCCEEDED
   c. Owner unavailable (FundingRequest creation fails) → PARTIAL
   d. Payee failure → FAILED
   e. Empty process_ids → blocked
   f. Idempotency / retry / replay
   g. Timeout-after-commit simulation (partial via late failure)
   h. PARTIAL explicit
   i. Resume (same op_key repeated → returns existing attempt)
   j. NEVER auto-confirm, NEVER Payment, NEVER cross-owner rollback
5. Architecture — I6 files no V1 imports; adapter contract; module importable
6. UI minimal — panel importable (tsc gate in FE, skipped if not in scope here)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "ingestion" / "corpus_202"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(doc_type: str, fields: dict, rows: list | None = None, issues: list | None = None):
    """Build a minimal mock IngestionDocument for commit tests."""
    doc = MagicMock()
    doc.id = 42
    doc.doc_type = doc_type
    doc.adapter_id = "solicitacao_numerario_v1"
    doc.adapter_version = "1"
    doc.occurrence_id = 99
    doc.review_status = "PENDING"

    doc_fields = []
    for k, v in fields.items():
        f = MagicMock()
        f.field_key = k
        f.raw_value = str(v) if v is not None else None
        f.normalized_value = str(v) if v is not None else None
        f.corrected_value = None
        f.review_status = "PENDING"
        doc_fields.append(f)
    doc.fields = doc_fields

    doc_rows = []
    for r in (rows or []):
        row = MagicMock()
        row.row_index = r.get("row_index", 0)
        row.cells_json = json.dumps(
            {
                "label": {"raw": r.get("label", ""), "normalized": r.get("label", "")},
                "code": {"raw": r.get("code", ""), "normalized": r.get("code", "")},
                "amount_brl": {"raw": r.get("amount_brl", "0"), "normalized": r.get("amount_brl", "0")},
                "category": {"raw": r.get("category", "expense"), "normalized": r.get("category", "expense")},
            }
        )
        doc_rows.append(row)
    doc.rows = doc_rows
    doc.issues = issues or []
    return doc


def _make_payee(payee_id: int, name: str, tax_id: str | None = None):
    p = MagicMock()
    p.id = payee_id
    p.name = name
    p.tax_id = tax_id
    return p


def _make_attempt(attempt_id: int, status: str, op_key: str, fingerprint: str):
    a = MagicMock()
    a.id = attempt_id
    a.operation_key = op_key
    a.payload_fingerprint = fingerprint
    a.status = status
    a.operations = []
    return a


# ---------------------------------------------------------------------------
# 1. Adapter pure — text extraction
# ---------------------------------------------------------------------------


SAMPLE_TEXT = """\
=== PAGE 1/1 ===
SOLICITAÇÃO DE NUMERÁRIO
DE DUIMP
EMITIDO EM: 19/06/2026 12:37:23 VENCIMENTO: 26/06/2026
A
EPIC SPORTS LTDA
RUA DO ROCIO, 199, CJ 71 / 72, VILA OLIMPIA
SAO PAULO - 65.751.802/0001-89
S/REFERÊNCIA INV. 181/202/203/244/245/246 EMBARQUE MARITIMA ENTRADA
N/REFERÊNCIA D00358/26 AWB/BL HKSTS26054756 INVOICE 181
EXPORTADOR HEROES SRL
FOB EUR 288.195,20 R$ 1.706.259,68 5,9205000 19/06/2026
ACRÉSCIMO EUR 0,00 R$ 0,00 5,9205000 19/06/2026
DEDUÇÃO EUR 0,00 R$ 0,00 5,9205000 19/06/2026
FRETE USD 3.875,00 R$ 20.000,04 5,1613000 19/06/2026
SEGURO 0,00 R$ 0,00
VALOR CIF EUR 291.573,30 R$ 1.726.259,72 5,9205000 19/06/2026
DESPESAS A SEREM DEBITADAS DE NOSSA CONTA: 341 BANCO ITAU S A AGÊNCIA: 0772 CONTA: 68018-7
AFRMM R$ 2.000,00
ICMS R$ 556.000,00
IMPOSTO IMPORTAÇÃO R$ 343.800,00
IMPOSTO PRODUTO INDUSTRIALIZADO R$ 253.500,00
PIS/PASEP R$ 37.700,00
COFINS R$ 167.900,00
TAXA DE UTILIZAÇÃO DO SISCOMEX R$ 223,64
FRETE INTERNACIONAL R$ 28.600,00
DESCONSOLIDACAO R$ 600,00
ARMAZENAGEM SANTOS BRASIL R$ 9.000,00
ARMAZENAGEM CNAGA R$ 8.500,00
FRETE (REMOCAO) R$ 7.300,00
FRETE (ENTREGA) R$ 5.600,00
SDA R$ 2.310,00
HONORARIOS R$ 1.621,00
DESPESAS DIVERSAS R$ 900,00
TOTAL R$ 1.425.554,64
TOTAL DESPESAS DO PROCESSO R$ 1.425.554,64
BECHTRANS MATRIZ - 00.012.365/0001-36
ESTIMADO CLIENTE,
BECHTRANS LOGÍSTICA INTERNATIONAL LTDA CNPJ: 00.012.365/0001-36
BANCO: 341 ITAÚ UNIBANCO S.A AGÊNCIA:
0772 VIEIRA DE MORAIS // CONTA CORRENTE: 68.018-7.
**CHAVE PIX: ADIANTAMENTO@BECHTRANS.COM.BR
SOLICITADO POR: CONFERIDO POR:
GILMAR BUENO _____________________
BECHTRANS MATRIZ - 00.012.365/0001-36
EMITIDO 19/06/2026 12:37:23 AV VEREADOR JOSE DINIZ 3530, 2 ANDAR - SANTO AMARO, SAO PAULO / SP - CEP 06604-006 1
(11) 3594-3600
"""


class TestAdapterPure:
    """Pure extraction tests against synthesized text (no PDF/DB)."""

    def _get_raw(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            _extract_header,
            _extract_trade_amounts,
            _extract_expense_lines,
            _extract_totals,
            _extract_payee,
        )
        header = _extract_header(SAMPLE_TEXT)
        trade = _extract_trade_amounts(SAMPLE_TEXT)
        lines = _extract_expense_lines(SAMPLE_TEXT)
        totals = _extract_totals(SAMPLE_TEXT)
        payee = _extract_payee(SAMPLE_TEXT)
        return header, trade, lines, totals, payee

    def test_issue_date_extracted(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("issue_date_raw") == "19/06/2026"

    def test_due_date_extracted(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("due_date_raw") == "26/06/2026"

    def test_recipient_name(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("recipient_name") == "EPIC SPORTS LTDA"

    def test_recipient_tax_id(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("recipient_tax_id") == "65.751.802/0001-89"

    def test_invoice_refs_multi(self):
        """S/REFERÊNCIA must parse multiple invoice refs: 181/202/203/244/245/246."""
        header, _, _, _, _ = self._get_raw()
        refs = header.get("invoice_refs", [])
        assert "181" in refs
        assert "202" in refs
        assert "246" in refs
        assert len(refs) == 6, f"Expected 6 invoice refs, got {refs}"

    def test_n_reference(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("n_reference") == "D00358/26"

    def test_awb_bl(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("awb_bl") == "HKSTS26054756"

    def test_invoice_ref_first(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("invoice_ref_first") == "181"

    def test_exporter(self):
        header, _, _, _, _ = self._get_raw()
        assert header.get("exporter") is not None
        assert "HEROES" in header["exporter"].upper()

    def test_fob_extracted(self):
        _, trade, _, _, _ = self._get_raw()
        assert trade.get("fob_currency") == "EUR"
        assert trade.get("fob_foreign_amount") == Decimal("288195.20")
        assert trade.get("fob_brl_amount") is not None
        assert trade.get("fob_fx_rate") is not None

    def test_freight_extracted(self):
        _, trade, _, _, _ = self._get_raw()
        assert trade.get("freight_currency") == "USD"
        assert trade.get("freight_foreign_amount") == Decimal("3875.00")
        assert trade.get("freight_brl_amount") is not None

    def test_cif_extracted(self):
        _, trade, _, _, _ = self._get_raw()
        assert trade.get("cif_currency") == "EUR"
        assert trade.get("cif_foreign_amount") == Decimal("291573.30")

    def test_expense_lines_count(self):
        _, _, lines, _, _ = self._get_raw()
        assert len(lines) >= 10, f"Expected at least 10 expense lines, got {len(lines)}"

    def test_tax_lines_present(self):
        """ICMS, II, IPI etc. should be classified as 'tax'."""
        _, _, lines, _, _ = self._get_raw()
        tax_lines = [l for l in lines if l.category == "tax"]
        tax_codes = {l.code for l in tax_lines}
        assert "ICMS" in tax_codes, f"ICMS not found in tax_codes: {tax_codes}"

    def test_expense_lines_present(self):
        _, _, lines, _, _ = self._get_raw()
        exp_lines = [l for l in lines if l.category == "expense"]
        assert len(exp_lines) >= 3, f"Expected at least 3 expense lines, got {len(exp_lines)}"

    def test_total_declared(self):
        _, _, _, totals, _ = self._get_raw()
        assert totals.get("declared_total_brl") is not None
        assert totals["declared_total_brl"] == Decimal("1425554.64")

    def test_payee_name_bechtrans(self):
        _, _, _, _, payee = self._get_raw()
        assert payee.get("payee_name") is not None
        assert "BECHTRANS" in payee["payee_name"].upper()

    def test_payee_cnpj(self):
        _, _, _, _, payee = self._get_raw()
        assert payee.get("payee_cnpj") == "00.012.365/0001-36"

    def test_payee_pix(self):
        _, _, _, _, payee = self._get_raw()
        pix = payee.get("payee_pix")
        assert pix is not None
        assert "@" in pix, f"PIX should contain @, got {pix}"

    def test_classify_true_when_payee_present(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            AdapterRawResult,
            classify,
        )
        raw = AdapterRawResult(
            issue_date_iso="2026-06-19",
            due_date_iso="2026-06-26",
            recipient_name="EPIC SPORTS LTDA",
            recipient_tax_id="65.751.802/0001-89",
            s_reference="INV. 181/202",
            invoice_refs=["181", "202"],
            n_reference="D00358/26",
            awb_bl="HKSTS26054756",
            invoice_ref_first="181",
            exporter="HEROES SRL",
            fob_currency="EUR",
            fob_foreign_amount=Decimal("288195.20"),
            fob_brl_amount=Decimal("1706259.68"),
            fob_fx_rate=Decimal("5.9205"),
            additions_brl=None,
            deductions_brl=None,
            freight_currency="USD",
            freight_foreign_amount=Decimal("3875"),
            freight_brl_amount=Decimal("20000.04"),
            freight_fx_rate=Decimal("5.1613"),
            insurance_brl=None,
            cif_currency="EUR",
            cif_foreign_amount=Decimal("291573.30"),
            cif_brl_amount=Decimal("1726259.72"),
            cif_fx_rate=Decimal("5.9205"),
            debit_bank="BANCO ITAU",
            debit_agency="0772",
            debit_account="68018-7",
            declared_total_brl=Decimal("1425554.64"),
            payee_name="BECHTRANS LOGÍSTICA INTERNATIONAL LTDA",
            payee_cnpj="00.012.365/0001-36",
            payee_pix="ADIANTAMENTO@BECHTRANS.COM.BR",
        )
        assert classify(raw) is True

    def test_classify_false_when_no_payee(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            AdapterRawResult,
            classify,
        )
        raw = AdapterRawResult(
            issue_date_iso=None,
            due_date_iso=None,
            recipient_name=None,
            recipient_tax_id=None,
            s_reference=None,
            invoice_refs=[],
            n_reference=None,
            awb_bl=None,
            invoice_ref_first=None,
            exporter=None,
            fob_currency=None,
            fob_foreign_amount=None,
            fob_brl_amount=None,
            fob_fx_rate=None,
            additions_brl=None,
            deductions_brl=None,
            freight_currency=None,
            freight_foreign_amount=None,
            freight_brl_amount=None,
            freight_fx_rate=None,
            insurance_brl=None,
            cif_currency=None,
            cif_foreign_amount=None,
            cif_brl_amount=None,
            cif_fx_rate=None,
            debit_bank=None,
            debit_agency=None,
            debit_account=None,
        )
        assert classify(raw) is False


# ---------------------------------------------------------------------------
# 2. Adapter extract() from real PDF (skipped if absent)
# ---------------------------------------------------------------------------


class TestAdapterPDFExtract:
    @pytest.fixture
    def pdf_bytes(self):
        p = FIXTURES / "Solicitacao_Numerario.pdf"
        if not p.is_file():
            pytest.skip(f"Fixture not found: {p}")
        return p.read_bytes()

    def test_extract_returns_result(self, pdf_bytes):
        from app.ingestion.adapters.solicitacao_numerario_v1 import extract

        raw = extract(pdf_bytes)
        assert raw is not None

    def test_extract_invoice_refs_present(self, pdf_bytes):
        from app.ingestion.adapters.solicitacao_numerario_v1 import extract

        raw = extract(pdf_bytes)
        assert len(raw.invoice_refs) >= 2, (
            f"Expected multiple invoice refs, got {raw.invoice_refs}"
        )

    def test_extract_payee_bechtrans(self, pdf_bytes):
        from app.ingestion.adapters.solicitacao_numerario_v1 import extract

        raw = extract(pdf_bytes)
        assert raw.payee_name is not None
        assert "BECHTRANS" in raw.payee_name.upper()

    def test_extract_fob_currency_eur(self, pdf_bytes):
        from app.ingestion.adapters.solicitacao_numerario_v1 import extract

        raw = extract(pdf_bytes)
        if raw.fob_currency:
            assert raw.fob_currency == "EUR"

    def test_extract_total_brl(self, pdf_bytes):
        from app.ingestion.adapters.solicitacao_numerario_v1 import extract

        raw = extract(pdf_bytes)
        assert raw.declared_total_brl is not None, "declared_total_brl must be extracted"
        assert raw.declared_total_brl > 0

    def test_extract_expense_lines_non_empty(self, pdf_bytes):
        from app.ingestion.adapters.solicitacao_numerario_v1 import extract

        raw = extract(pdf_bytes)
        assert len(raw.lines) >= 5, (
            f"Expected >=5 expense lines, got {len(raw.lines)}"
        )


# ---------------------------------------------------------------------------
# 3. Math validation
# ---------------------------------------------------------------------------


class TestMathValidation:
    def test_total_mismatch_emits_error(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            AdapterRawResult,
            ExpenseLine,
            _validate_math,
        )
        raw = AdapterRawResult(
            issue_date_iso=None,
            due_date_iso=None,
            recipient_name="EPIC SPORTS",
            recipient_tax_id=None,
            s_reference=None,
            invoice_refs=["101"],
            n_reference=None,
            awb_bl=None,
            invoice_ref_first=None,
            exporter=None,
            fob_currency=None,
            fob_foreign_amount=None,
            fob_brl_amount=None,
            fob_fx_rate=None,
            additions_brl=None,
            deductions_brl=None,
            freight_currency=None,
            freight_foreign_amount=None,
            freight_brl_amount=None,
            freight_fx_rate=None,
            insurance_brl=None,
            cif_currency=None,
            cif_foreign_amount=None,
            cif_brl_amount=None,
            cif_fx_rate=None,
            debit_bank=None,
            debit_agency=None,
            debit_account=None,
            declared_total_brl=Decimal("1000.00"),
            payee_name="BECHTRANS",
            lines=[
                ExpenseLine(
                    label="ICMS",
                    code="ICMS",
                    amount_brl=Decimal("500.00"),
                    category="tax",
                    position=0,
                )
            ],
        )
        issues = _validate_math(raw)
        error_codes = [i["code"] for i in issues if i["severity"] == "ERROR"]
        assert "MATH_TOTAL_MISMATCH" in error_codes

    def test_no_expense_lines_emits_warning(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            AdapterRawResult,
            _validate_math,
        )
        raw = AdapterRawResult(
            issue_date_iso=None,
            due_date_iso=None,
            recipient_name=None,
            recipient_tax_id=None,
            s_reference=None,
            invoice_refs=[],
            n_reference=None,
            awb_bl=None,
            invoice_ref_first=None,
            exporter=None,
            fob_currency=None,
            fob_foreign_amount=None,
            fob_brl_amount=None,
            fob_fx_rate=None,
            additions_brl=None,
            deductions_brl=None,
            freight_currency=None,
            freight_foreign_amount=None,
            freight_brl_amount=None,
            freight_fx_rate=None,
            insurance_brl=None,
            cif_currency=None,
            cif_foreign_amount=None,
            cif_brl_amount=None,
            cif_fx_rate=None,
            debit_bank=None,
            debit_agency=None,
            debit_account=None,
        )
        issues = _validate_math(raw)
        warning_codes = [i["code"] for i in issues if i["severity"] == "WARNING"]
        assert "NO_EXPENSE_LINES" in warning_codes

    def test_no_invoice_refs_emits_warning(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            AdapterRawResult,
            ExpenseLine,
            _validate_math,
        )
        raw = AdapterRawResult(
            issue_date_iso=None,
            due_date_iso=None,
            recipient_name=None,
            recipient_tax_id=None,
            s_reference=None,
            invoice_refs=[],
            n_reference=None,
            awb_bl=None,
            invoice_ref_first=None,
            exporter=None,
            fob_currency=None,
            fob_foreign_amount=None,
            fob_brl_amount=None,
            fob_fx_rate=None,
            additions_brl=None,
            deductions_brl=None,
            freight_currency=None,
            freight_foreign_amount=None,
            freight_brl_amount=None,
            freight_fx_rate=None,
            insurance_brl=None,
            cif_currency=None,
            cif_foreign_amount=None,
            cif_brl_amount=None,
            cif_fx_rate=None,
            debit_bank=None,
            debit_agency=None,
            debit_account=None,
            payee_name="BECHTRANS",
            declared_total_brl=Decimal("500.00"),
            lines=[
                ExpenseLine(
                    label="ICMS",
                    code="ICMS",
                    amount_brl=Decimal("500.00"),
                    category="tax",
                    position=0,
                )
            ],
        )
        issues = _validate_math(raw)
        warning_codes = [i["code"] for i in issues if i["severity"] == "WARNING"]
        assert "NO_INVOICE_REFS" in warning_codes

    def test_total_match_no_error(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import (
            AdapterRawResult,
            ExpenseLine,
            _validate_math,
        )
        raw = AdapterRawResult(
            issue_date_iso=None,
            due_date_iso=None,
            recipient_name=None,
            recipient_tax_id=None,
            s_reference=None,
            invoice_refs=["101"],
            n_reference=None,
            awb_bl=None,
            invoice_ref_first=None,
            exporter=None,
            fob_currency=None,
            fob_foreign_amount=None,
            fob_brl_amount=None,
            fob_fx_rate=None,
            additions_brl=None,
            deductions_brl=None,
            freight_currency=None,
            freight_foreign_amount=None,
            freight_brl_amount=None,
            freight_fx_rate=None,
            insurance_brl=None,
            cif_currency=None,
            cif_foreign_amount=None,
            cif_brl_amount=None,
            cif_fx_rate=None,
            debit_bank=None,
            debit_agency=None,
            debit_account=None,
            declared_total_brl=Decimal("500.00"),
            payee_name="BECHTRANS",
            lines=[
                ExpenseLine(
                    label="ICMS",
                    code="ICMS",
                    amount_brl=Decimal("500.00"),
                    category="tax",
                    position=0,
                )
            ],
        )
        issues = _validate_math(raw)
        errors = [i for i in issues if i["severity"] == "ERROR"]
        assert not errors, f"No errors expected on total match, got: {errors}"


# ---------------------------------------------------------------------------
# 4. Commit commands (mocked DB)
# ---------------------------------------------------------------------------


def _make_commit_doc():
    """Minimal doc for commit tests."""
    return _make_doc(
        "SOLICITACAO_NUMERARIO",
        {
            "payee_name": "BECHTRANS LOGÍSTICA INTERNATIONAL LTDA",
            "payee_cnpj": "00.012.365/0001-36",
            "payee_bank": "ITAÚ UNIBANCO S.A",
            "payee_agency": "0772",
            "payee_account": "68.018-7",
            "payee_pix": "ADIANTAMENTO@BECHTRANS.COM.BR",
            "issue_date": "2026-06-19",
            "due_date": "2026-06-26",
            "n_reference": "D00358/26",
            "awb_bl": "HKSTS26054756",
            "declared_total_brl": "1425554.64",
            "fob_brl_amount": "1706259.68",
            "freight_brl_amount": "20000.04",
            "cif_brl_amount": "1726259.72",
            "invoice_refs_json": json.dumps(["181", "202", "203"]),
        },
        rows=[
            {
                "label": "ICMS",
                "code": "ICMS",
                "amount_brl": "556000.00",
                "category": "tax",
            },
            {
                "label": "FRETE INTERNACIONAL",
                "code": "FRETE_INTERNACIONAL",
                "amount_brl": "28600.00",
                "category": "expense",
            },
        ],
    )


class TestPreviewNumerario:
    def test_preview_plans_store_and_payee_ops(self):
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.preview_numerario(db, 42, [1, 2])

        op_keys = [op.op_key for op in result.planned_operations]
        assert "store_document" in op_keys
        assert "create_or_find_payee" in op_keys

    def test_preview_per_process_has_funding_request_op(self):
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.preview_numerario(db, 42, [10, 20])

        op_keys = [op.op_key for op in result.planned_operations]
        assert "process_10_create_funding_request" in op_keys
        assert "process_20_create_funding_request" in op_keys

    def test_preview_includes_invoice_refs(self):
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.preview_numerario(db, 42, [1])

        assert "181" in result.invoice_refs
        assert "202" in result.invoice_refs

    def test_preview_no_write(self):
        """preview_numerario must not write to DB."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            nc.preview_numerario(db, 42, [1])

        db.add.assert_not_called()
        db.flush.assert_not_called()
        db.commit.assert_not_called()

    def test_preview_empty_process_ids_cannot_commit(self):
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.preview_numerario(db, 42, [])

        assert result.can_commit is False

    def test_preview_blocked_by_open_errors(self):
        from app.ingestion import numerario_commit_commands as nc

        open_error_issue = MagicMock()
        open_error_issue.status = "OPEN"
        open_error_issue.severity = "ERROR"
        doc = _make_commit_doc()
        doc.issues = [open_error_issue]
        db = MagicMock()
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.preview_numerario(db, 42, [1])

        assert result.can_commit is False
        assert result.open_error_count == 1


class TestCommitNumerario:
    """Commit happy path and error cases."""

    def _make_mock_fr(self, fr_id: int, status: str = "DRAFT", version: int = 1):
        fr = MagicMock()
        fr.id = fr_id
        fr.status = status
        fr.version = version
        return fr

    def test_commit_happy_path_two_processes(self):
        """Two processes, all ops succeed → SUCCEEDED."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()
        db.get.return_value = None  # IngestionCommitAttempt not found

        attempt = MagicMock()
        attempt.id = 1
        attempt.operation_key = "op1"
        attempt.payload_fingerprint = "fp"
        attempt.status = "UNKNOWN"
        attempt.operations = []

        payee = _make_payee(10, "BECHTRANS LOGÍSTICA INTERNATIONAL LTDA", "00.012.365/0001-36")
        fr1 = self._make_mock_fr(101)
        fr2 = self._make_mock_fr(102)
        fr1_updated = self._make_mock_fr(101, version=2)
        fr2_updated = self._make_mock_fr(102, version=2)

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = None
        db.query.return_value = query_mock

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", return_value=payee), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", side_effect=[fr1, fr2]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.get_funding_request", side_effect=[fr1_updated, fr2_updated, fr1_updated, fr2_updated]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_value_bases", return_value=fr1_updated), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_tax_lines", return_value=fr1_updated), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_expense_lines", return_value=fr1_updated), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.documents_public.link_document"), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"), \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None):

            mock_store.return_value = MagicMock(id=200)

            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op1",
                process_ids=[1, 2],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        assert result is attempt
        assert attempt.status == "SUCCEEDED"

    def test_commit_blocked_by_open_errors(self):
        """Open ERROR issue → raises NumerarioCommitBlockedByIssues."""
        from app.ingestion import numerario_commit_commands as nc
        from app.ingestion.numerario_commit_commands import NumerarioCommitBlockedByIssues

        open_error = MagicMock()
        open_error.status = "OPEN"
        open_error.severity = "ERROR"
        doc = _make_commit_doc()
        doc.issues = [open_error]
        db = MagicMock()

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            with pytest.raises(NumerarioCommitBlockedByIssues):
                nc.commit_numerario(
                    db,
                    document_id=42,
                    operation_key="op-err",
                    process_ids=[1],
                    actor_id="admin",
                    attachments_path=Path("/tmp"),
                    quarantine_path=Path("/tmp"),
                )

    def test_commit_empty_process_ids_blocked(self):
        """Empty process_ids → commit_blocked_by_issues."""
        from app.ingestion import numerario_commit_commands as nc
        from app.ingestion.errors import IngestionError

        doc = _make_commit_doc()
        db = MagicMock()

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            with pytest.raises(IngestionError) as exc_info:
                nc.commit_numerario(
                    db,
                    document_id=42,
                    operation_key="op-empty",
                    process_ids=[],
                    actor_id="admin",
                    attachments_path=Path("/tmp"),
                    quarantine_path=Path("/tmp"),
                )
        assert exc_info.value.code == "commit_blocked_by_issues"

    def test_commit_idempotency_same_key_same_fingerprint(self):
        """Same operation_key + fingerprint → returns existing attempt (idempotent)."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        process_ids = [1, 2]
        fingerprint = nc._build_fingerprint(42, process_ids)
        existing = _make_attempt(77, "SUCCEEDED", "op-idem", fingerprint)

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = existing
        db.query.return_value = query_mock

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-idem",
                process_ids=process_ids,
                actor_id="admin",
                attachments_path=Path("/tmp"),
                quarantine_path=Path("/tmp"),
            )

        assert result is existing
        assert result.status == "SUCCEEDED"
        db.add.assert_not_called()

    def test_commit_conflict_fingerprint_different_process_ids(self):
        """Same key, different process_ids → fingerprint conflict → 409."""
        from app.ingestion import numerario_commit_commands as nc
        from app.ingestion.numerario_commit_commands import NumerarioCommitConflictFingerprint

        doc = _make_commit_doc()
        db = MagicMock()

        # Existing attempt with process_ids=[1] fingerprint
        existing_fingerprint = nc._build_fingerprint(42, [1])
        existing = _make_attempt(88, "SUCCEEDED", "op-conflict", existing_fingerprint)

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = existing
        db.query.return_value = query_mock

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            # Now attempt with process_ids=[1, 2] → different fingerprint
            with pytest.raises(NumerarioCommitConflictFingerprint):
                nc.commit_numerario(
                    db,
                    document_id=42,
                    operation_key="op-conflict",
                    process_ids=[1, 2],  # different from existing [1]
                    actor_id="admin",
                    attachments_path=Path("/tmp"),
                    quarantine_path=Path("/tmp"),
                )

    def test_commit_owner_unavailable_partial(self):
        """FundingRequest creation fails for one process → PARTIAL (store_document succeeded)."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 2
        attempt.status = "UNKNOWN"
        attempt.operations = []

        payee = _make_payee(10, "BECHTRANS")
        fr1 = self._make_mock_fr(101, version=1)
        fr1_v2 = self._make_mock_fr(101, version=2)

        def funding_side_effect(db_arg, pid, **kwargs):
            if pid == 1:
                return fr1
            raise Exception("Process 2 unavailable — simulated timeout")

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", return_value=payee), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", side_effect=funding_side_effect), \
             patch("app.ingestion.numerario_commit_commands.customs_public.get_funding_request", return_value=fr1_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_value_bases", return_value=fr1_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_tax_lines", return_value=fr1_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_expense_lines", return_value=fr1_v2), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.documents_public.link_document"), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"), \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-partial",
                process_ids=[1, 2],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        assert attempt.status == "PARTIAL"

    def test_commit_payee_failure_is_failed(self):
        """Payee creation failure → FAILED (not PARTIAL)."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 3
        attempt.status = "UNKNOWN"
        attempt.operations = []

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", side_effect=Exception("Payee DB down")), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-payee-fail",
                process_ids=[1],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        assert attempt.status == "FAILED"

    def test_commit_timeout_after_store_document_partial(self):
        """Simulate timeout-after-commit: store_document succeeds, then funding_request times out.
        Result must be PARTIAL (not FAILED since store_document succeeded).
        """
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 4
        attempt.status = "UNKNOWN"
        attempt.operations = []

        payee = _make_payee(10, "BECHTRANS")

        def funding_timeout(*args, **kwargs):
            raise TimeoutError("Connection timed out after 30s")

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", return_value=payee), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", side_effect=funding_timeout), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-timeout",
                process_ids=[1],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        assert attempt.status == "PARTIAL"

    def test_commit_resume_returns_existing_on_retry(self):
        """Retry with same op_key+fingerprint returns existing attempt (resume)."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        process_ids = [5]
        fingerprint = nc._build_fingerprint(42, process_ids)
        existing = _make_attempt(99, "PARTIAL", "op-resume", fingerprint)

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = existing
        db.query.return_value = query_mock

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc):
            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-resume",
                process_ids=process_ids,
                actor_id="admin",
                attachments_path=Path("/tmp"),
                quarantine_path=Path("/tmp"),
            )

        # Should return existing attempt without touching DB further
        assert result is existing
        db.add.assert_not_called()

    def test_commit_never_calls_confirm_funding_request(self):
        """NEVER auto-confirm FundingRequest."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 5
        attempt.status = "UNKNOWN"
        attempt.operations = []

        payee = _make_payee(10, "BECHTRANS")
        fr = self._make_mock_fr(200, version=1)
        fr_v2 = self._make_mock_fr(200, version=2)

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", return_value=payee), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", return_value=fr), \
             patch("app.ingestion.numerario_commit_commands.customs_public.get_funding_request", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_value_bases", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_tax_lines", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_expense_lines", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.confirm_funding_request") as mock_confirm, \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.documents_public.link_document"), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"), \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-no-confirm",
                process_ids=[1],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        # Confirm must NEVER be called
        mock_confirm.assert_not_called()

    def test_commit_partial_explicit_status_set(self):
        """When some process ops fail, status is explicitly PARTIAL."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 6
        attempt.status = "UNKNOWN"
        attempt.operations = []

        payee = _make_payee(10, "BECHTRANS")

        # All fail
        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", return_value=payee), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", side_effect=Exception("All processes failed")), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.documents_public.link_document"), \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-all-fail",
                process_ids=[1, 2],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        # store_document and payee succeeded → at least some ops succeeded → PARTIAL
        assert attempt.status == "PARTIAL"

    def test_commit_unknown_ops_recorded_when_funding_fails(self):
        """When FundingRequest creation fails, subsequent per-process ops are UNKNOWN."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 7
        attempt.status = "UNKNOWN"
        attempt.operations = []

        payee = _make_payee(10, "BECHTRANS")
        recorded_ops = []

        def mock_record_op(db_arg, attempt_arg, op_key, *, status, **kwargs):
            recorded_ops.append({"op_key": op_key, "status": status})

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands._record_op", side_effect=mock_record_op), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee", return_value=payee), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", side_effect=Exception("Process gone")), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-unknown",
                process_ids=[3],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        # The funding request op should be FAILED, subsequent ops should be UNKNOWN
        statuses_by_key = {r["op_key"]: r["status"] for r in recorded_ops}
        assert statuses_by_key.get("process_3_create_funding_request") == "FAILED"
        assert statuses_by_key.get("process_3_replace_value_bases") == "UNKNOWN"
        assert statuses_by_key.get("process_3_replace_tax_lines") == "UNKNOWN"
        assert statuses_by_key.get("process_3_replace_expense_lines") == "UNKNOWN"

    def test_commit_existing_payee_reused_by_cnpj(self):
        """If a payee with matching CNPJ exists, it must be reused (not duplicated)."""
        from app.ingestion import numerario_commit_commands as nc

        doc = _make_commit_doc()
        db = MagicMock()

        attempt = MagicMock()
        attempt.id = 8
        attempt.status = "UNKNOWN"
        attempt.operations = []

        existing_payee = _make_payee(55, "BECHTRANS LOGÍSTICA INTERNATIONAL LTDA", "00.012.365/0001-36")
        fr = self._make_mock_fr(300, version=1)
        fr_v2 = self._make_mock_fr(300, version=2)

        with patch("app.ingestion.numerario_commit_commands.staging_queries.get_document_detail", return_value=doc), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitAttempt", return_value=attempt), \
             patch("app.ingestion.numerario_commit_commands.IngestionCommitOperation"), \
             patch("app.ingestion.numerario_commit_commands.customs_public.list_payees", return_value=[existing_payee]), \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_payee") as mock_create_payee, \
             patch("app.ingestion.numerario_commit_commands.customs_public.create_funding_request", return_value=fr), \
             patch("app.ingestion.numerario_commit_commands.customs_public.get_funding_request", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_value_bases", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_tax_lines", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.customs_public.replace_expense_lines", return_value=fr_v2), \
             patch("app.ingestion.numerario_commit_commands.documents_public.store_document") as mock_store, \
             patch("app.ingestion.numerario_commit_commands.documents_public.link_document"), \
             patch("app.ingestion.numerario_commit_commands.quarantine_storage.resolve_quarantine_path", return_value=None), \
             patch("app.ingestion.numerario_commit_commands.audit_public.record_event"):

            mock_store.return_value = MagicMock(id=200)

            query_mock = MagicMock()
            query_mock.filter.return_value.first.return_value = None
            db.query.return_value = query_mock

            result = nc.commit_numerario(
                db,
                document_id=42,
                operation_key="op-reuse-payee",
                process_ids=[1],
                actor_id="admin",
                attachments_path=Path("/tmp/att"),
                quarantine_path=Path("/tmp/q"),
            )

        # create_payee must NOT be called since existing payee was found
        mock_create_payee.assert_not_called()
        assert attempt.status == "SUCCEEDED"


# ---------------------------------------------------------------------------
# 5. Architecture
# ---------------------------------------------------------------------------


class TestArchitectureI6:
    def test_adapter_has_required_contract(self):
        """solicitacao_numerario_v1 must expose extract/classify/run_adapter/ADAPTER_ID/DOC_TYPE."""
        import importlib

        mod = importlib.import_module("app.ingestion.adapters.solicitacao_numerario_v1")
        assert hasattr(mod, "extract"), "extract() missing"
        assert hasattr(mod, "classify"), "classify() missing"
        assert hasattr(mod, "run_adapter"), "run_adapter() missing"
        assert hasattr(mod, "ADAPTER_ID"), "ADAPTER_ID missing"
        assert hasattr(mod, "DOC_TYPE"), "DOC_TYPE missing"
        assert mod.DOC_TYPE == "SOLICITACAO_NUMERARIO"

    def test_numerario_commit_commands_importable(self):
        import app.ingestion.numerario_commit_commands as nc

        assert hasattr(nc, "preview_numerario")
        assert hasattr(nc, "commit_numerario")
        assert hasattr(nc, "NumerarioCommitBlockedByIssues")
        assert hasattr(nc, "NumerarioCommitConflictFingerprint")

    def test_no_v1_imports_in_i6_files(self):
        i6_files = [
            Path(__file__).parent.parent / "app" / "ingestion" / "adapters" / "solicitacao_numerario_v1.py",
            Path(__file__).parent.parent / "app" / "ingestion" / "numerario_commit_commands.py",
        ]
        for f in i6_files:
            if not f.is_file():
                continue
            content = f.read_text(encoding="utf-8")
            assert "from v1" not in content, f"V1 import in {f.name}"
            assert "import v1" not in content, f"V1 import in {f.name}"
            assert "from app.v1" not in content, f"V1 import in {f.name}"

    def test_numerario_commit_commands_in_internal_suffixes(self):
        from app.foundation.module_graph import INTERNAL_SUFFIXES

        assert ".numerario_commit_commands" in INTERNAL_SUFFIXES, (
            "numerario_commit_commands must be in INTERNAL_SUFFIXES"
        )

    def test_ingestion_customs_dep_still_present(self):
        from app.foundation.module_graph import ALLOWED_DEPS

        assert "customs" in ALLOWED_DEPS.get("ingestion", frozenset()), (
            "ingestion must be allowed to depend on customs (I6 uses customs.create_funding_request)"
        )

    def test_adapter_doc_type_constant(self):
        from app.ingestion.adapters.solicitacao_numerario_v1 import DOC_TYPE, ADAPTER_ID

        assert DOC_TYPE == "SOLICITACAO_NUMERARIO"
        assert ADAPTER_ID == "solicitacao_numerario_v1"

    def test_adapter_result_has_invoice_refs_field(self):
        """AdapterRawResult must have invoice_refs: list[str]."""
        from app.ingestion.adapters.solicitacao_numerario_v1 import AdapterRawResult

        import dataclasses
        field_names = {f.name for f in dataclasses.fields(AdapterRawResult)}
        assert "invoice_refs" in field_names, "AdapterRawResult must have invoice_refs field"

    def test_never_auto_confirm_in_source(self):
        """commit_numerario source must not call confirm_funding_request."""
        f = (
            Path(__file__).parent.parent
            / "app"
            / "ingestion"
            / "numerario_commit_commands.py"
        )
        if not f.is_file():
            pytest.skip("File not found")
        content = f.read_text(encoding="utf-8")
        assert "confirm_funding_request" not in content, (
            "numerario_commit_commands.py must NEVER call confirm_funding_request"
        )

    def test_never_create_payment_in_source(self):
        """commit_numerario source must not call create_payment."""
        f = (
            Path(__file__).parent.parent
            / "app"
            / "ingestion"
            / "numerario_commit_commands.py"
        )
        if not f.is_file():
            pytest.skip("File not found")
        content = f.read_text(encoding="utf-8")
        assert "create_payment" not in content, (
            "numerario_commit_commands.py must NEVER call create_payment"
        )


# ---------------------------------------------------------------------------
# 6. UI minimal — schema importable, panel importable
# ---------------------------------------------------------------------------


class TestUIMinimalI6:
    def test_numerario_schemas_importable(self):
        from app.ingestion.schemas import (
            NumerarioCommitIn,
            NumerarioPreviewOut,
            NumerarioPreviewOpOut,
            NumerarioOpResultOut,
            NumerarioCommitResultOut,
        )
        body = NumerarioCommitIn(operation_key="k1", process_ids=[1, 2])
        assert body.process_ids == [1, 2]

    def test_numerario_preview_op_schema(self):
        from app.ingestion.schemas import NumerarioPreviewOpOut

        op = NumerarioPreviewOpOut(
            op_key="process_1_create_funding_request",
            description="Criar FR DRAFT para processo 1",
            entity_type="customs_funding_request",
            process_id=1,
        )
        assert op.process_id == 1

    def test_numerario_commit_result_schema(self):
        from app.ingestion.schemas import NumerarioCommitResultOut, NumerarioOpResultOut

        result = NumerarioCommitResultOut(
            attempt_id=99,
            document_id=42,
            operation_key="k1",
            status="PARTIAL",
            operations=[
                NumerarioOpResultOut(
                    op_key="store_document",
                    status="SUCCEEDED",
                    entity_type="document",
                    entity_id="200",
                    error_message=None,
                    details_json=None,
                )
            ],
        )
        assert result.status == "PARTIAL"
        assert len(result.operations) == 1
