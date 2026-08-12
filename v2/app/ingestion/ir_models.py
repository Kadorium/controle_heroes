"""Ingestion staging IR models — J3-I1 (Document / Section / Field / Row / Issue / Set).

Canonical IR is versioned per document (`ir_schema_version` + optimistic `version`).
Values: NULL = ausente; '' = vazio; '0' = zero — nunca coerção silenciosa vazio→zero.
Locator pode ser NULL (sem fingir precisão). Correção humana não sobrescreve raw.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

DOC_REVIEW_STATUSES = (
    "DRAFT",
    "IN_REVIEW",
    "READY",
    "REJECTED",
)
TARGET_REVIEW_STATUSES = (
    "PENDING",
    "APPROVED",
    "CORRECTED",
    "REJECTED",
)
ISSUE_SEVERITIES = ("ERROR", "WARNING", "INFO")
ISSUE_STATUSES = ("OPEN", "RESOLVED", "DISMISSED")
ISSUE_TARGET_TYPES = ("DOCUMENT", "SECTION", "FIELD", "ROW")
CHANGE_TARGET_TYPES = ("FIELD", "ROW", "SECTION", "DOCUMENT")


class IngestionDocumentSet(Base):
    """Relação mínima de agrupamento documental (não é dossiê rico)."""

    __tablename__ = "ingestion_document_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingestion_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    projection_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["IngestionDocumentSetMember"]] = relationship(
        back_populates="document_set", cascade="all, delete-orphan"
    )


class IngestionDocument(Base):
    __tablename__ = "ingestion_documents"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('DRAFT', 'IN_REVIEW', 'READY', 'REJECTED')",
            name="ck_ingestion_documents_review_status",
        ),
        UniqueConstraint("occurrence_id", name="uq_ingestion_documents_occurrence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurrence_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_occurrences.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingestion_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_set_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_document_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adapter_id: Mapped[str] = mapped_column(String(128), nullable=False, default="contract_stub_v1")
    adapter_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    ir_schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    locked_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sections: Mapped[list["IngestionSection"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    fields: Mapped[list["IngestionField"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    rows: Mapped[list["IngestionRow"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    issues: Mapped[list["IngestionIssue"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class IngestionDocumentSetMember(Base):
    __tablename__ = "ingestion_document_set_members"
    __table_args__ = (
        UniqueConstraint(
            "document_set_id",
            "document_id",
            name="uq_ingestion_document_set_members_set_doc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_set_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_document_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document_set: Mapped[IngestionDocumentSet] = relationship(back_populates="members")


class IngestionSection(Base):
    __tablename__ = "ingestion_sections"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'CORRECTED', 'REJECTED')",
            name="ck_ingestion_sections_review_status",
        ),
        UniqueConstraint(
            "document_id", "section_key", name="uq_ingestion_sections_doc_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    document: Mapped[IngestionDocument] = relationship(back_populates="sections")


class IngestionField(Base):
    __tablename__ = "ingestion_fields"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'CORRECTED', 'REJECTED')",
            name="ck_ingestion_fields_review_status",
        ),
        UniqueConstraint(
            "document_id", "field_key", name="uq_ingestion_fields_doc_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False, default="string")
    # NULL=ausente; ''=vazio; '0'=zero — raw nunca sobrescrito por correção
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped[IngestionDocument] = relationship(back_populates="fields")


class IngestionRow(Base):
    __tablename__ = "ingestion_rows"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'CORRECTED', 'REJECTED')",
            name="ck_ingestion_rows_review_status",
        ),
        UniqueConstraint(
            "document_id", "row_index", name="uq_ingestion_rows_doc_index"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # JSON text: {col: {raw, normalized, corrected, locator}}
    cells_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped[IngestionDocument] = relationship(back_populates="rows")


class IngestionIssue(Base):
    __tablename__ = "ingestion_issues"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('ERROR', 'WARNING', 'INFO')",
            name="ck_ingestion_issues_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="ck_ingestion_issues_status",
        ),
        CheckConstraint(
            "target_type IN ('DOCUMENT', 'SECTION', 'FIELD', 'ROW')",
            name="ck_ingestion_issues_target_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="ERROR")
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, default="DOCUMENT")
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    locator_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped[IngestionDocument] = relationship(back_populates="issues")


class IngestionReviewChange(Base):
    """Histórico de alterações humanas (não altera adapter / raw)."""

    __tablename__ = "ingestion_review_changes"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('FIELD', 'ROW', 'SECTION', 'DOCUMENT')",
            name="ck_ingestion_review_changes_target_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ingestion_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_review_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_review_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
