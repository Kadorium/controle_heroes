"""Validação de segurança de upload — PDF/XLSX; sem executar conteúdo ativo."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.limits import IngestionLimits

SAFE_FILENAME_RE = re.compile(r"^[^\\/:\*\?\"<>\|]+$")
ALLOWED_EXTENSIONS = {".pdf", ".xlsx"}


@dataclass
class ValidationResult:
    ok: bool
    reason: str | None = None
    detected_mime: str | None = None
    kind: str | None = None  # pdf | xlsx


def sanitize_original_filename(name: str | None) -> str:
    raw = (name or "unnamed").strip() or "unnamed"
    # strip path components if client sent a path
    raw = raw.replace("\\", "/").split("/")[-1]
    if not raw or raw in (".", ".."):
        return "unnamed"
    if len(raw) > 200:
        raw = raw[:200]
    return raw


def check_filename_safe(filename: str) -> str | None:
    if not filename or filename in (".", ".."):
        return "unsafe_filename"
    if filename.startswith("/") or (len(filename) > 1 and filename[1] == ":"):
        return "absolute_filename"
    if ".." in filename or "/" in filename or "\\" in filename:
        return "path_traversal_filename"
    if not SAFE_FILENAME_RE.match(filename):
        return "unsafe_filename_chars"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return "extension_not_allowed"
    return None


def _detect_kind(path: Path) -> tuple[str | None, str | None]:
    with path.open("rb") as f:
        head = f.read(8)
    if head.startswith(b"%PDF"):
        return "pdf", "application/pdf"
    if head.startswith(b"PK"):
        return "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return None, None


def _pdf_has_active_content(reader) -> str | None:
    """Inspeção conservadora — REJECT se indícios de conteúdo ativo."""
    try:
        root = reader.trailer.get("/Root")
        if root is not None:
            root_obj = root.get_object() if hasattr(root, "get_object") else root
            for key in ("/OpenAction", "/AA", "/AcroForm"):
                if key in root_obj:
                    # AcroForm alone is not always active JS; still inspect Names
                    if key != "/AcroForm":
                        return f"pdf_active_{key.strip('/').lower()}"
            names = root_obj.get("/Names")
            if names is not None:
                names_obj = names.get_object() if hasattr(names, "get_object") else names
                if "/JavaScript" in names_obj or "/EmbeddedFiles" in names_obj:
                    return "pdf_javascript_or_embedded_files"
            if "/JavaScript" in root_obj:
                return "pdf_javascript"
    except Exception:
        pass

    try:
        for page in reader.pages:
            annots = page.get("/Annots")
            if not annots:
                continue
            annots_obj = annots.get_object() if hasattr(annots, "get_object") else annots
            for annot in annots_obj:
                a = annot.get_object() if hasattr(annot, "get_object") else annot
                subtype = str(a.get("/Subtype", ""))
                if subtype in ("/FileAttachment", "/RichMedia", "/Movie", "/Sound"):
                    return f"pdf_annot_{subtype.strip('/').lower()}"
                action = a.get("/A") or a.get("/AA")
                if action is not None:
                    act = action.get_object() if hasattr(action, "get_object") else action
                    if isinstance(act, dict) or hasattr(act, "get"):
                        s = str(act.get("/S", "")) if hasattr(act, "get") else ""
                        if s in ("/JavaScript", "/JS", "/Launch", "/SubmitForm", "/ImportData"):
                            return f"pdf_action_{s.strip('/').lower()}"
                if "/JS" in a or "/JavaScript" in a:
                    return "pdf_annot_javascript"
    except Exception:
        pass

    # brute text scan of raw for common tokens (small files already on disk)
    return None


def _validate_pdf(path: Path, limits: IngestionLimits) -> ValidationResult:
    try:
        from pypdf import PdfReader
        from pypdf.errors import FileNotDecryptedError, PdfReadError
    except ImportError as exc:
        raise RuntimeError("pypdf required for PDF validation") from exc

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            return ValidationResult(False, "pdf_encrypted")
        n = len(reader.pages)
        if n > limits.max_pdf_pages:
            return ValidationResult(False, "pdf_too_many_pages")
        active = _pdf_has_active_content(reader)
        if active:
            return ValidationResult(False, active)
        # raw token scan
        raw = path.read_bytes()
        lowered = raw.lower()
        for token, code in (
            (b"/javascript", "pdf_javascript"),
            (b"/js(", "pdf_js"),
            (b"/openaction", "pdf_openaction"),
            (b"/launch", "pdf_launch"),
            (b"/richmedia", "pdf_richmedia"),
            (b"/embeddedfiles", "pdf_embedded_files"),
        ):
            if token in lowered:
                return ValidationResult(False, code)
        return ValidationResult(True, detected_mime="application/pdf", kind="pdf")
    except FileNotDecryptedError:
        return ValidationResult(False, "pdf_encrypted")
    except PdfReadError:
        return ValidationResult(False, "pdf_corrupted")
    except Exception:
        return ValidationResult(False, "pdf_corrupted")


_XLSX_REJECT_NAMES = (
    "xl/vbaProject.bin",
    "xl/macrosheets/",
    "xl/externalLinks/",
    "xl/externalLinks/_rels/",
    "xl/embeddings/",
    "xl/activeX/",
)


def _validate_xlsx(path: Path, limits: IngestionLimits) -> ValidationResult:
    try:
        if not zipfile.is_zipfile(path):
            return ValidationResult(False, "xlsx_not_zip")
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            if len(names) > limits.zip_max_entries:
                return ValidationResult(False, "xlsx_too_many_entries")
            if "[Content_Types].xml" not in names:
                return ValidationResult(False, "xlsx_missing_content_types")
            if not any(n.startswith("xl/") for n in names):
                return ValidationResult(False, "xlsx_missing_workbook")

            total_uncomp = 0
            seen: set[str] = set()
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if name in seen:
                    return ValidationResult(False, "xlsx_duplicate_entry")
                seen.add(name)
                if name.startswith("/") or name.startswith("../") or "/../" in f"/{name}/":
                    return ValidationResult(False, "xlsx_zip_traversal")
                if ".." in name.split("/"):
                    return ValidationResult(False, "xlsx_zip_traversal")
                total_uncomp += max(info.file_size, 0)
                if total_uncomp > limits.zip_max_uncompressed_bytes:
                    return ValidationResult(False, "xlsx_uncompressed_too_large")
                if info.compress_size > 0:
                    ratio = info.file_size / max(info.compress_size, 1)
                    if ratio > limits.zip_max_compression_ratio and info.file_size > 1_000_000:
                        return ValidationResult(False, "xlsx_compression_bomb")

            lower_names = [n.lower() for n in names]
            for bad in _XLSX_REJECT_NAMES:
                if any(n.startswith(bad.lower()) or n == bad.lower() for n in lower_names):
                    return ValidationResult(False, "xlsx_active_or_external")
            if any("vbaproject" in n for n in lower_names):
                return ValidationResult(False, "xlsx_macro")
            if any("externallink" in n for n in lower_names):
                return ValidationResult(False, "xlsx_external_link")
            if any("/embeddings/" in n or n.endswith(".bin") and "ole" in n for n in lower_names):
                return ValidationResult(False, "xlsx_ole_or_embedded")

            # relationships with external TargetMode
            for n in names:
                if n.endswith(".rels"):
                    try:
                        data = zf.read(n).decode("utf-8", errors="ignore").lower()
                    except Exception:
                        return ValidationResult(False, "xlsx_malformed_rels")
                    if 'targetmode="external"' in data or "targetmode='external'" in data:
                        return ValidationResult(False, "xlsx_external_relationship")

        return ValidationResult(
            True,
            detected_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            kind="xlsx",
        )
    except zipfile.BadZipFile:
        return ValidationResult(False, "xlsx_malformed")
    except Exception:
        return ValidationResult(False, "xlsx_malformed")


def validate_uploaded_file(
    path: Path,
    *,
    original_filename: str,
    declared_mime: str | None,
    limits: IngestionLimits | None = None,
) -> ValidationResult:
    limits = limits or IngestionLimits()
    fn_err = check_filename_safe(original_filename)
    if fn_err:
        return ValidationResult(False, fn_err)

    kind, detected = _detect_kind(path)
    if kind is None:
        return ValidationResult(False, "unsupported_or_spoofed_type")

    ext = Path(original_filename).suffix.lower()
    if kind == "pdf" and ext != ".pdf":
        return ValidationResult(False, "extension_mime_mismatch")
    if kind == "xlsx" and ext != ".xlsx":
        return ValidationResult(False, "extension_mime_mismatch")

    if declared_mime:
        dm = declared_mime.lower().split(";")[0].strip()
        if kind == "pdf" and dm not in ("application/pdf", "application/x-pdf", ""):
            if dm and "pdf" not in dm:
                return ValidationResult(False, "declared_mime_mismatch")
        if kind == "xlsx" and dm and "sheet" not in dm and "excel" not in dm and dm != "application/zip":
            if dm not in (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/octet-stream",
                "application/zip",
            ):
                return ValidationResult(False, "declared_mime_mismatch")

    if kind == "pdf":
        return _validate_pdf(path, limits)
    return _validate_xlsx(path, limits)
