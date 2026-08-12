"""Quarantine storage — path controlado pelo servidor; dedup / rehydrate."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass
class StreamedUpload:
    temp_path: Path
    sha256: str
    size_bytes: int


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def stream_to_temp(
    quarantine_root: Path,
    source: BinaryIO,
    *,
    max_bytes: int,
    chunk_size: int = 1024 * 256,
) -> StreamedUpload:
    """Escreve em arquivo temporário sob quarantine; calcula SHA-256 incremental."""
    quarantine_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = quarantine_root / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = tmp_dir / f"up_{secrets.token_hex(16)}.part"
    h = hashlib.sha256()
    size = 0
    try:
        with temp_path.open("wb") as out:
            while True:
                chunk = source.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("file_too_large")
                h.update(chunk)
                out.write(chunk)
            out.flush()
        if size == 0:
            raise ValueError("empty_file")
        return StreamedUpload(temp_path=temp_path, sha256=h.hexdigest(), size_bytes=size)
    except Exception:
        _safe_unlink(temp_path)
        raise


def final_relative_path(sha256: str) -> str:
    nonce = secrets.token_hex(4)
    return f"{sha256[:2]}/{sha256}_{nonce}"


def resolve_quarantine_path(quarantine_root: Path, rel: str) -> Path | None:
    root = quarantine_root.resolve()
    cleaned = (rel or "").replace("\\", "/").lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        return None
    candidate = (quarantine_root / cleaned).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def commit_temp_to_final(
    quarantine_root: Path,
    temp_path: Path,
    sha256: str,
    *,
    pending_files: list[Path] | None = None,
) -> str:
    """Rename atômico para path final; registra em pending_files para cleanup."""
    rel = final_relative_path(sha256)
    dest = quarantine_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_path.replace(dest)
    if pending_files is not None:
        pending_files.append(dest)
    return rel.replace("\\", "/")


def delete_quarantine_file(quarantine_root: Path, rel: str | None) -> None:
    if not rel:
        return
    path = resolve_quarantine_path(quarantine_root, rel)
    _safe_unlink(path)


def cleanup_paths(paths: list[Path]) -> None:
    for p in paths:
        _safe_unlink(p)


def blob_file_exists(quarantine_root: Path, rel: str | None) -> bool:
    if not rel:
        return False
    path = resolve_quarantine_path(quarantine_root, rel)
    return path is not None and path.is_file()
