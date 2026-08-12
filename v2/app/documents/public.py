from __future__ import annotations

import hashlib
import secrets
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.documents.models import Document, DocumentLink


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_document(
    db: Session,
    *,
    attachments_path: Path,
    actor_id: str | None,
    filename: str,
    content: bytes,
    mime_type: str | None = None,
) -> Document:
    """Persiste bytes imutáveis + metadados. Sem commit."""
    attachments_path.mkdir(parents=True, exist_ok=True)
    file_hash = _sha256(content)
    document_key = uuid.uuid4().hex
    rel = f"{document_key[:2]}/{document_key}_{secrets.token_hex(4)}"
    dest = attachments_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    doc = Document(
        document_key=document_key,
        version=1,
        is_current_version=True,
        file_hash=file_hash,
        storage_path=str(dest.relative_to(attachments_path)).replace("\\", "/"),
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
    )
    db.add(doc)
    db.flush()
    return doc


def link_document(
    db: Session,
    *,
    document_id: int,
    entity_type: str,
    entity_id: str,
    role: str = "attachment",
) -> DocumentLink:
    link = DocumentLink(
        document_id=document_id,
        entity_type=entity_type,
        entity_id=entity_id,
        role=role,
    )
    db.add(link)
    db.flush()
    return link


def list_by_entity(db: Session, entity_type: str, entity_id: str) -> list[Document]:
    q = (
        db.query(Document)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .filter(
            DocumentLink.entity_type == entity_type,
            DocumentLink.entity_id == entity_id,
            Document.is_current_version.is_(True),
        )
        .order_by(Document.id.desc())
    )
    return list(q.all())


def get_document(db: Session, document_id: int) -> Document | None:
    return db.get(Document, document_id)


def list_links_for_document(db: Session, document_id: int) -> list[DocumentLink]:
    return (
        db.query(DocumentLink)
        .filter(DocumentLink.document_id == document_id)
        .order_by(DocumentLink.id.asc())
        .all()
    )


def absolute_path(attachments_path: Path, doc: Document) -> Path:
    return attachments_path / doc.storage_path


def resolve_content_path(attachments_path: Path, doc: Document) -> Path | None:
    """Resolve arquivo no storage autorizado. None se path inválido ou arquivo ausente.

    Se só existir o arquivo pendente (crash entre commit de banco e promote),
    promove aqui — o Document existe, logo o arquivo é legítimo.
    """
    root = attachments_path.resolve()
    rel = (doc.storage_path or "").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    candidate = (attachments_path / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        _promote_pending(candidate)
    if not candidate.is_file():
        return None
    return candidate


# entity_type (DocumentLink) → permissão de leitura do módulo owner
ENTITY_READ_PERMISSION: dict[str, str] = {
    "order": "orders:read",
    "invoice": "billing:read",
    "shipment": "logistics:read",
    "import_process": "customs:read",
    "payment": "treasury:read",
    "payable": "billing:read",
    "supplier": "catalog:read",
    "product": "catalog:read",
}


def entity_read_permission(entity_type: str) -> str | None:
    return ENTITY_READ_PERMISSION.get((entity_type or "").strip().lower())


def delete_stored_file(attachments_path: Path, doc: Document) -> None:
    """Remove arquivo físico (cleanup de órfãos após rollback)."""
    path = absolute_path(attachments_path, doc)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def store_document_tracked(
    db: Session,
    *,
    attachments_path: Path,
    actor_id: str | None,
    filename: str,
    content: bytes,
    mime_type: str | None = None,
    pending_files: list[Path] | None = None,
) -> Document:
    """Como store_document, registrando path em pending_files para cleanup se commit falhar."""
    doc = store_document(
        db,
        attachments_path=attachments_path,
        actor_id=actor_id,
        filename=filename,
        content=content,
        mime_type=mime_type,
    )
    if pending_files is not None:
        pending_files.append(absolute_path(attachments_path, doc))
    return doc


# ---------------------------------------------------------------------------
# Escrita em duas fases (RUX-2R-b): TEMP → commit de banco → promote
# ---------------------------------------------------------------------------

PENDING_SUFFIX = ".pending"


def _pending_path(final_path: Path) -> Path:
    return final_path.with_name(final_path.name + PENDING_SUFFIX)


def _promote_pending(final_path: Path) -> bool:
    """Renomeia <final>.pending → <final>. True se o arquivo final existe ao sair."""
    pending = _pending_path(final_path)
    if final_path.is_file():
        if pending.is_file():
            try:
                pending.unlink()
            except OSError:
                pass
        return True
    if not pending.is_file():
        return False
    final_path.parent.mkdir(parents=True, exist_ok=True)
    pending.replace(final_path)
    return True


def store_document_pending(
    db: Session,
    *,
    attachments_path: Path,
    actor_id: str | None,
    filename: str,
    content: bytes,
    mime_type: str | None = None,
    pending_files: list[Path],
) -> Document:
    """Persiste metadados e grava os bytes em ``<destino>.pending``.

    O arquivo definitivo só passa a existir em ``promote_pending_files``, chamada
    depois do commit de banco. Rollback deixa apenas o pendente, removido por
    ``discard_pending_files``.
    """
    attachments_path.mkdir(parents=True, exist_ok=True)
    file_hash = _sha256(content)
    document_key = uuid.uuid4().hex
    rel = f"{document_key[:2]}/{document_key}_{secrets.token_hex(4)}"
    dest = attachments_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    _pending_path(dest).write_bytes(content)
    pending_files.append(dest)
    doc = Document(
        document_key=document_key,
        version=1,
        is_current_version=True,
        file_hash=file_hash,
        storage_path=str(dest.relative_to(attachments_path)).replace("\\", "/"),
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
    )
    db.add(doc)
    db.flush()
    return doc


def promote_pending_files(pending_files: list[Path]) -> list[Path]:
    """Promove os pendentes após commit bem-sucedido. Retorna os que não promoveram."""
    failures: list[Path] = []
    for final_path in pending_files:
        try:
            if not _promote_pending(final_path):
                failures.append(final_path)
        except OSError:
            failures.append(final_path)
    return failures


def discard_pending_files(pending_files: list[Path]) -> None:
    """Remove os arquivos temporários após rollback."""
    for final_path in pending_files:
        try:
            pending = _pending_path(final_path)
            if pending.is_file():
                pending.unlink()
        except OSError:
            pass
