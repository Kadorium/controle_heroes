import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.permissions import PERM_DOCUMENTS_READ, PERM_DOCUMENTS_WRITE
from app.database import get_db
from app.dependencies import require_permission
from app.models import User
from app.schemas_docs import DocumentResponse
from app.services.attachments import (
    get_attachment_file_path,
    list_document_versions,
    list_entity_documents,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_DOCUMENTS_READ)),
    entity_type: str | None = None,
    entity_id: str | None = None,
    current_only: bool = True,
):
    if entity_type and entity_id:
        return list_entity_documents(db, entity_type, entity_id, current_only=current_only)
    from app.models import DocumentAttachment

    q = db.query(DocumentAttachment)
    if current_only:
        q = q.filter(DocumentAttachment.is_current_version.is_(True))
    return q.order_by(DocumentAttachment.created_at.desc()).limit(200).all()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_doc(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    document_type: str | None = Form(None),
    document_key: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_DOCUMENTS_WRITE)),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    return upload_document(
        db,
        file,
        content,
        entity_type=entity_type,
        entity_id=entity_id,
        document_type=document_type,
        user_id=current_user.id,
        document_key=document_key,
        notes=notes,
    )


@router.get("/{attachment_id}/download")
def download_document(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_DOCUMENTS_READ)),
):
    from app.models import DocumentAttachment

    att = db.query(DocumentAttachment).filter(DocumentAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    path = get_attachment_file_path(att)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco")
    return FileResponse(path, filename=att.original_filename, media_type=att.mime_type or "application/octet-stream")


@router.get("/key/{document_key}/versions", response_model=list[DocumentResponse])
def document_versions(
    document_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_DOCUMENTS_READ)),
):
    return list_document_versions(db, document_key)
