"""Customs domain models — J#5 ImportProcess + Doganale + Numerário + Nationalization."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.foundation.database import Base

IMPORT_PROCESS_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "IN_CLEARANCE",
    "PARTIALLY_CLEARED",
    "CLEARED",
    "CANCELLED",
)
DOGANALE_VERSION_STATUSES = ("DRAFT", "ACTIVE", "SUPERSEDED", "CANCELLED")
DIVERGENCE_SEVERITIES = ("INFO", "WARN", "ERROR")
DIVERGENCE_STATUSES = ("OPEN", "RESOLVED", "DISMISSED")
FUNDING_REQUEST_STATUSES = ("DRAFT", "CONFIRMED", "CANCELLED")
NATIONALIZATION_STATUSES = ("DRAFT", "CONFIRMED", "REVERSED")


class ImportProcess(Base):
    __tablename__ = "import_processes"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'DRAFT', 'SUBMITTED', 'IN_CLEARANCE', "
            "'PARTIALLY_CLEARED', 'CLEARED', 'CANCELLED'"
            ")",
            name="ck_import_processes_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    invoices: Mapped[list["ImportProcessInvoice"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    invoice_items: Mapped[list["ImportProcessInvoiceItem"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    shipments: Mapped[list["ImportProcessShipment"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    shipment_items: Mapped[list["ImportProcessShipmentItem"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    doganale: Mapped["CustomsDoganale | None"] = relationship(
        back_populates="process", uselist=False, cascade="all, delete-orphan"
    )
    divergences: Mapped[list["CustomsDivergence"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    provenances: Mapped[list["CustomsProvenance"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    funding_requests: Mapped[list["CustomsFundingRequest"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    nationalizations: Mapped[list["Nationalization"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )


class ImportProcessInvoice(Base):
    __tablename__ = "import_process_invoices"
    __table_args__ = (
        UniqueConstraint("invoice_id", name="uq_import_process_invoices_invoice_id"),
        UniqueConstraint("process_id", "invoice_id", name="uq_import_process_invoices_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    process: Mapped[ImportProcess] = relationship(back_populates="invoices")


class ImportProcessInvoiceItem(Base):
    __tablename__ = "import_process_invoice_items"
    __table_args__ = (
        CheckConstraint("allocated_qty > 0", name="ck_import_process_invoice_items_qty"),
        UniqueConstraint(
            "process_id", "invoice_item_id", name="uq_import_process_invoice_items_pair"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_item_id: Mapped[int] = mapped_column(
        ForeignKey("invoice_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    allocated_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    process: Mapped[ImportProcess] = relationship(back_populates="invoice_items")


class ImportProcessShipment(Base):
    __tablename__ = "import_process_shipments"
    __table_args__ = (
        UniqueConstraint("shipment_id", name="uq_import_process_shipments_shipment_id"),
        UniqueConstraint("process_id", "shipment_id", name="uq_import_process_shipments_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    process: Mapped[ImportProcess] = relationship(back_populates="shipments")


class ImportProcessShipmentItem(Base):
    __tablename__ = "import_process_shipment_items"
    __table_args__ = (
        CheckConstraint("allocated_qty > 0", name="ck_import_process_shipment_items_qty"),
        UniqueConstraint(
            "process_id", "shipment_item_id", name="uq_import_process_shipment_items_pair"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shipment_item_id: Mapped[int] = mapped_column(
        ForeignKey("shipment_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    allocated_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    process: Mapped[ImportProcess] = relationship(back_populates="shipment_items")


class CustomsDoganale(Base):
    """Doganale lógica 1:1 com ImportProcess → 1:N versões."""

    __tablename__ = "customs_doganales"
    __table_args__ = (
        UniqueConstraint("process_id", name="uq_customs_doganales_process_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    process: Mapped[ImportProcess] = relationship(back_populates="doganale")
    versions: Mapped[list["CustomsDoganaleVersion"]] = relationship(
        back_populates="doganale", cascade="all, delete-orphan"
    )


class CustomsDoganaleVersion(Base):
    __tablename__ = "customs_doganale_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'SUPERSEDED', 'CANCELLED')",
            name="ck_customs_doganale_versions_status",
        ),
        CheckConstraint("version_number > 0", name="ck_customs_doganale_versions_num"),
        UniqueConstraint(
            "doganale_id", "version_number", name="uq_customs_doganale_versions_num"
        ),
        UniqueConstraint(
            "doganale_id", "idempotency_key", name="uq_customs_doganale_versions_idem"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doganale_id: Mapped[int] = mapped_column(
        ForeignKey("customs_doganales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    doganale: Mapped[CustomsDoganale] = relationship(back_populates="versions")
    lines: Mapped[list["CustomsDoganaleLine"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", order_by="CustomsDoganaleLine.position"
    )


class CustomsDoganaleLine(Base):
    """Linha declaratória — pallet_count owner = Customs (não Logistics)."""

    __tablename__ = "customs_doganale_lines"
    __table_args__ = (
        UniqueConstraint("version_id", "position", name="uq_customs_doganale_lines_pos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("customs_doganale_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    ncm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    line_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    acquisition_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    pallet_count: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    invoice_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoice_items.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    version: Mapped[CustomsDoganaleVersion] = relationship(back_populates="lines")


class CustomsDivergence(Base):
    __tablename__ = "customs_divergences"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO', 'WARN', 'ERROR')",
            name="ck_customs_divergences_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="ck_customs_divergences_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doganale_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("customs_doganale_versions.id", ondelete="SET NULL"), nullable=True
    )
    doganale_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("customs_doganale_lines.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    field_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    process: Mapped[ImportProcess] = relationship(back_populates="divergences")


class CustomsProvenance(Base):
    """Hook mínimo de provenance para handoff J#3."""

    __tablename__ = "customs_provenances"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "source_kind",
            name="uq_customs_provenances_entity_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    adapter_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    process: Mapped[ImportProcess] = relationship(back_populates="provenances")


class CustomsPayee(Base):
    """Favorecido Customs — sem Supplier FK obrigatório (Bechtrans ≠ Heroes)."""

    __tablename__ = "customs_payees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    agency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pix_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    funding_requests: Mapped[list["CustomsFundingRequest"]] = relationship(
        back_populates="payee"
    )


class CustomsFundingRequest(Base):
    """Numerário — cabeçalho da solicitação financeira aduaneira (I5-3B: + FundingPayableLink)."""

    __tablename__ = "customs_funding_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')",
            name="ck_customs_funding_requests_status",
        ),
        UniqueConstraint(
            "process_id", "idempotency_key", name="uq_customs_funding_requests_idem"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payee_id: Mapped[int] = mapped_column(
        ForeignKey("customs_payees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    declared_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    process: Mapped[ImportProcess] = relationship(back_populates="funding_requests")
    payee: Mapped[CustomsPayee] = relationship(back_populates="funding_requests")
    value_bases: Mapped[list["CustomsValueBasis"]] = relationship(
        back_populates="funding_request",
        cascade="all, delete-orphan",
        order_by="CustomsValueBasis.position",
    )
    tax_lines: Mapped[list["CustomsTaxLine"]] = relationship(
        back_populates="funding_request",
        cascade="all, delete-orphan",
        order_by="CustomsTaxLine.position",
    )
    expense_lines: Mapped[list["CustomsExpenseLine"]] = relationship(
        back_populates="funding_request",
        cascade="all, delete-orphan",
        order_by="CustomsExpenseLine.position",
    )
    payable_links: Mapped[list["FundingPayableLink"]] = relationship(
        back_populates="funding_request",
        cascade="all, delete-orphan",
        order_by="FundingPayableLink.sequence",
    )


class FundingPayableLink(Base):
    """Vínculo Customs FundingRequest → Billing Payable (ownership Customs)."""

    __tablename__ = "funding_payable_links"
    __table_args__ = (
        UniqueConstraint(
            "funding_request_id", "payable_id", name="uq_funding_payable_link_pair"
        ),
        UniqueConstraint(
            "funding_request_id", "sequence", name="uq_funding_payable_link_seq"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_request_id: Mapped[int] = mapped_column(
        ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payable_id: Mapped[int] = mapped_column(
        ForeignKey("payables.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    funding_request: Mapped[CustomsFundingRequest] = relationship(back_populates="payable_links")



class CustomsValueBasis(Base):
    __tablename__ = "customs_value_bases"
    __table_args__ = (
        UniqueConstraint("funding_request_id", "position", name="uq_customs_value_bases_pos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_request_id: Mapped[int] = mapped_column(
        ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    funding_request: Mapped[CustomsFundingRequest] = relationship(back_populates="value_bases")


class CustomsTaxLine(Base):
    __tablename__ = "customs_tax_lines"
    __table_args__ = (
        UniqueConstraint("funding_request_id", "position", name="uq_customs_tax_lines_pos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_request_id: Mapped[int] = mapped_column(
        ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    funding_request: Mapped[CustomsFundingRequest] = relationship(back_populates="tax_lines")


class CustomsExpenseLine(Base):
    __tablename__ = "customs_expense_lines"
    __table_args__ = (
        UniqueConstraint("funding_request_id", "position", name="uq_customs_expense_lines_pos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_request_id: Mapped[int] = mapped_column(
        ForeignKey("customs_funding_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    funding_request: Mapped[CustomsFundingRequest] = relationship(back_populates="expense_lines")


class Nationalization(Base):
    """Liberação aduaneira parcial/total — não cria estoque sozinha (I5-4)."""

    __tablename__ = "nationalizations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'REVERSED')",
            name="ck_nationalizations_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("import_processes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    process: Mapped[ImportProcess] = relationship(back_populates="nationalizations")
    items: Mapped[list["NationalizationItem"]] = relationship(
        back_populates="nationalization", cascade="all, delete-orphan"
    )


class NationalizationItem(Base):
    __tablename__ = "nationalization_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_nationalization_items_qty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nationalization_id: Mapped[int] = mapped_column(
        ForeignKey("nationalizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doganale_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("customs_doganale_lines.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invoice_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoice_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    shipment_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipment_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    nationalization: Mapped[Nationalization] = relationship(back_populates="items")
