import hashlib
import secrets
import shutil
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import DocumentAttachment
from app.services.auth import write_audit_log


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _unique_storage_name(document_key: str, version: int, file_hash: str, filename: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    return f"{document_key}/v{version}_{file_hash[:12]}_{safe}"


def save_upload_file(content: bytes, relative_path: str, settings: Settings | None = None) -> Path:
    s = settings or get_settings()
    full_path = s.attachments_path / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return full_path


def upload_document(
    db: Session,
    file: UploadFile,
    content: bytes,
    *,
    entity_type: str,
    entity_id: str,
    document_type: str | None,
    user_id: int | None,
    document_key: str | None = None,
    notes: str | None = None,
) -> DocumentAttachment:
    settings = get_settings()
    file_hash = compute_file_hash(content)
    key = document_key or secrets.token_hex(16)

    if document_key:
        current = (
            db.query(DocumentAttachment)
            .filter(
                DocumentAttachment.document_key == document_key,
                DocumentAttachment.is_current_version.is_(True),
            )
            .first()
        )
        if current:
            current.is_current_version = False
            version = current.version + 1
        else:
            version = 1
    else:
        version = 1

    storage_rel = _unique_storage_name(key, version, file_hash, file.filename or "file")
    save_upload_file(content, storage_rel, settings)

    attachment = DocumentAttachment(
        document_key=key,
        version=version,
        is_current_version=True,
        file_hash=file_hash,
        storage_path=storage_rel,
        original_filename=file.filename or "file",
        mime_type=file.content_type,
        size_bytes=len(content),
        entity_type=entity_type,
        entity_id=entity_id,
        document_type=document_type,
        uploaded_by_id=user_id,
        notes=notes,
    )
    db.add(attachment)
    db.flush()
    write_audit_log(
        db,
        user_id=user_id,
        entity_type="document_attachment",
        entity_id=str(attachment.id),
        action="upload" if version == 1 else "new_version",
        new_value=f"v{version}",
        attachment_id=str(attachment.id),
    )
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment_file_path(attachment: DocumentAttachment, settings: Settings | None = None) -> Path:
    s = settings or get_settings()
    return s.attachments_path / attachment.storage_path


def list_entity_documents(
    db: Session,
    entity_type: str,
    entity_id: str,
    *,
    current_only: bool = True,
) -> list[DocumentAttachment]:
    q = db.query(DocumentAttachment).filter(
        DocumentAttachment.entity_type == entity_type,
        DocumentAttachment.entity_id == entity_id,
    )
    if current_only:
        q = q.filter(DocumentAttachment.is_current_version.is_(True))
    return q.order_by(DocumentAttachment.document_key, DocumentAttachment.version.desc()).all()


def list_document_versions(db: Session, document_key: str) -> list[DocumentAttachment]:
    return (
        db.query(DocumentAttachment)
        .filter(DocumentAttachment.document_key == document_key)
        .order_by(DocumentAttachment.version.desc())
        .all()
    )


def backup_attachments_to_zip(settings: Settings | None = None) -> Path:
    """Copia anexos para zip de backup (usado em testes e script)."""
    import zipfile
    from datetime import datetime

    s = settings or get_settings()
    s.backups_attachments_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = s.backups_attachments_path / f"attachments_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if s.attachments_path.exists():
            for f in s.attachments_path.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(s.attachments_path))
    return zip_path
