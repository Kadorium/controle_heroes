from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import public as audit_public
from app.documents import public as documents_public
from app.foundation.database import get_db
from app.foundation.deps import enforce_permission, get_current_user
from app.foundation.settings import get_settings
from app.foundation.uow import UnitOfWork
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
