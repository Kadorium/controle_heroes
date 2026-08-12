"""Limites de ingestão — sem import de foundation (arch boundary)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionLimits:
    max_upload_bytes: int = 25_000_000
    max_batch_bytes: int = 50_000_000
    max_files_per_request: int = 20
    max_pdf_pages: int = 200
    quarantine_ttl_days: int = 30
    zip_max_entries: int = 500
    zip_max_uncompressed_bytes: int = 80_000_000
    zip_max_compression_ratio: float = 100.0


def limits_from_mapping(m: object) -> IngestionLimits:
    """Aceita Settings ou objeto com atributos ingestion_*."""
    return IngestionLimits(
        max_upload_bytes=int(getattr(m, "ingestion_max_upload_bytes", 25_000_000)),
        max_batch_bytes=int(getattr(m, "ingestion_max_batch_bytes", 50_000_000)),
        max_files_per_request=int(getattr(m, "ingestion_max_files_per_request", 20)),
        max_pdf_pages=int(getattr(m, "ingestion_max_pdf_pages", 200)),
        quarantine_ttl_days=int(getattr(m, "ingestion_quarantine_ttl_days", 30)),
        zip_max_entries=int(getattr(m, "ingestion_zip_max_entries", 500)),
        zip_max_uncompressed_bytes=int(getattr(m, "ingestion_zip_max_uncompressed_bytes", 80_000_000)),
        zip_max_compression_ratio=float(getattr(m, "ingestion_zip_max_compression_ratio", 100.0)),
    )
