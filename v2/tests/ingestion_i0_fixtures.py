"""Helpers — minimal PDF/XLSX fixtures for I0 security tests."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path


def minimal_pdf_bytes(tag: str | None = None) -> bytes:
    """Minimal PDF; optional tag makes content/hash unique across tests."""
    try:
        from pypdf import PdfWriter

        buf = io.BytesIO()
        w = PdfWriter()
        w.add_blank_page(width=72, height=72)
        if tag:
            w.add_metadata({"/Title": tag})
        w.write(buf)
        return buf.getvalue()
    except Exception:
        t = (tag or "").encode("ascii", "ignore")[:32]
        return (
            b"%PDF-1.4\n%"
            + t
            + b"\n"
            b"1 0 obj<<>>endobj\n"
            b"2 0 obj<< /Length 0 >>stream\nendstream\nendobj\n"
            b"3 0 obj<< /Type /Page /Parent 4 0 R /MediaBox [0 0 72 72] /Contents 2 0 R >>endobj\n"
            b"4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            b"5 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n"
            b"trailer<< /Size 6 /Root 5 0 R >>\nstartxref\n0\n%%EOF\n"
        )


def pdf_with_javascript_token() -> bytes:
    base = minimal_pdf_bytes()
    # Ensure token scan catches /JavaScript
    return base.replace(b"%%EOF", b"/JavaScript (app.alert)%%EOF")


def minimal_xlsx_bytes(*, with_vba: bool = False, external_rel: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheets><sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\" "
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets></workbook>',
        )
        rels = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        )
        if external_rel:
            rels += (
                '<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" '
                'Target="http://evil.example/x" TargetMode="External"/>'
            )
        rels += "</Relationships>"
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData/></worksheet>",
        )
        if with_vba:
            zf.writestr("xl/vbaProject.bin", b"FAKEVBA")
    return buf.getvalue()


def write_fixture(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
