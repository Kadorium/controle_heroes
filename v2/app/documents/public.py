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


def absolute_path(attachments_path: Path, doc: Document) -> Path:
    return attachments_path / doc.storage_path


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
