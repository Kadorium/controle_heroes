from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.documents import public as documents_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.errors import AppError
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
from app.identity import public as identity_public
from app.identity.models import User

router = APIRouter(tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    document_key: str
    version: int
    file_hash: str
    original_filename: str
    mime_type: str | None
    size_bytes: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


def _sanitize_filename(name: str | None) -> str:
    raw = (name or "download.bin").replace("\\", "/").split("/")[-1].strip()
    cleaned = "".join(ch for ch in raw if ch.isprintable() and ch not in '<>:"|?*')
    return cleaned[:200] or "download.bin"


def _user_may_access_document(user: User, db: Session, document_id: int) -> bool:
    """documents:read + permissão de leitura de ao menos uma entidade vinculada."""
    links = documents_public.list_links_for_document(db, document_id)
    if not links:
        return False
    for link in links:
        perm = documents_public.entity_read_permission(link.entity_type)
        if perm is None:
            continue
        try:
            identity_public.require_permission(user, perm)
            return True
        except PermissionError:
            continue
    return False


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    role: str = Form("attachment"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "documents:write")
    settings = get_settings()
    content = await file.read()
    with UnitOfWork(db) as uow:
        doc = documents_public.store_document(
            uow.session,
            attachments_path=settings.attachments_path,
            actor_id=str(user.id),
            filename=file.filename or "upload.bin",
            content=content,
            mime_type=file.content_type,
        )
        documents_public.link_document(
            uow.session,
            document_id=doc.id,
            entity_type=entity_type,
            entity_id=entity_id,
            role=role,
        )
        audit_public.record_event(
            uow.session,
            actor_id=str(user.id),
            entity_type="document",
            entity_id=str(doc.id),
            action="store_and_link",
            reason_code="DOC_UPLOAD",
            details=f"{entity_type}:{entity_id}",
        )
        uow.commit()
        uow.session.refresh(doc)
        return doc


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enforce_permission(user, "documents:read")
    return documents_public.list_by_entity(db, entity_type, entity_id)


@router.get("/documents/{document_id}/content")
def download_document_content(
    document_id: int,
    download: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Serve bytes do documento. Sem Audit (mesma política da listagem GET).

    Autorização: documents:read + permissão de leitura de ao menos 1 entidade vinculada
    (menor contrato seguro além da listagem, que só exige documents:read).
    """
    enforce_permission(user, "documents:read")
    doc = documents_public.get_document(db, document_id)
    if not doc or not doc.is_current_version:
        raise AppError("Documento não encontrado", code="document_not_found", status_code=404)
    if not _user_may_access_document(user, db, document_id):
        raise AppError("Permissão insuficiente", code="forbidden", status_code=403)

    settings = get_settings()
    path = documents_public.resolve_content_path(Path(settings.attachments_path), doc)
    if path is None:
        raise AppError("Arquivo não encontrado", code="document_file_missing", status_code=404)

    filename = _sanitize_filename(doc.original_filename)
    media = doc.mime_type or "application/octet-stream"
    # ASCII fallback + UTF-8 filename* (RFC 5987)
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download.bin"
    disposition_type = "attachment" if download else "inline"
    headers = {
        "Content-Disposition": (
            f"{disposition_type}; filename=\"{ascii_name}\"; "
            f"filename*=UTF-8''{quote(filename)}"
        ),
        "X-Content-Type-Options": "nosniff",
    }
    return FileResponse(
        path,
        media_type=media,
        headers=headers,
        filename=None,
    )
