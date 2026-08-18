"""Pydantic schemas — Ingestion I0 HTTP."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BatchCreate(BaseModel):
    notes: str | None = None


class OccurrenceOut(BaseModel):
    id: int
    batch_id: int
    blob_id: int | None
    status: str
    original_filename: str
    declared_mime: str | None
    detected_mime: str | None
    size_bytes: int
    sha256: str | None
    client_upload_key: str | None
    rejection_reason: str | None
    physical_reuse: bool
    rehydrated: bool
    retain_until: datetime | None
    bytes_purged_at: datetime | None
    blob_physical_status: str | None = None
    created_at: datetime | None
    updated_at: datetime | None


class BatchOut(BaseModel):
    id: int
    status: str
    created_by_actor_id: str | None
    notes: str | None
    created_at: datetime | None
    updated_at: datetime | None
    occurrences: list[OccurrenceOut] = Field(default_factory=list)


class UploadResponse(BaseModel):
    batch_id: int
    results: list[OccurrenceOut]


class PurgeRequest(BaseModel):
    dry_run: bool = False


class PurgeBlobOut(BaseModel):
    blob_id: int
    sha256: str
    size_bytes: int
    eligible: bool
    blockers: list[int]
    occurrence_ids: list[int]


class PurgeResponse(BaseModel):
    dry_run: bool
    eligible_occurrence_ids: list[int]
    blobs: list[PurgeBlobOut]
    bytes_to_free: int
    purged_blob_ids: list[int]
    marked_occurrence_ids: list[int]


# --- J3-I1 staging IR ---


class FieldSeedIn(BaseModel):
    field_key: str
    value_type: str = "string"
    raw_value: str | None = None
    normalized_value: str | None = None
    locator_json: str | None = None
    provenance_json: str | None = None
    section_key: str | None = None


class RowSeedIn(BaseModel):
    row_index: int
    row_key: str | None = None
    cells_json: str | None = None
    cells: dict | None = None
    section_key: str | None = None


class SectionSeedIn(BaseModel):
    section_key: str
    title: str | None = None
    ordinal: int = 0


class IssueSeedIn(BaseModel):
    severity: str = "ERROR"
    code: str
    message: str
    target_type: str = "DOCUMENT"
    target_id: int | None = None
    locator_json: str | None = None


class DocumentSeedIn(BaseModel):
    occurrence_id: int
    doc_type: str = "UNKNOWN"
    adapter_id: str = "contract_stub_v1"
    adapter_version: str = "1"
    fields: list[FieldSeedIn] = Field(default_factory=list)
    rows: list[RowSeedIn] = Field(default_factory=list)
    sections: list[SectionSeedIn] = Field(default_factory=list)
    issues: list[IssueSeedIn] = Field(default_factory=list)


class FieldOut(BaseModel):
    id: int
    document_id: int
    section_id: int | None
    field_key: str
    value_type: str
    raw_value: str | None
    normalized_value: str | None
    corrected_value: str | None
    effective_value: str | None = None
    locator_json: str | None
    provenance_json: str | None
    review_status: str
    version: int


class RowOut(BaseModel):
    id: int
    document_id: int
    section_id: int | None
    row_index: int
    row_key: str | None
    cells_json: str
    review_status: str
    version: int


class SectionOut(BaseModel):
    id: int
    document_id: int
    section_key: str
    title: str | None
    ordinal: int
    review_status: str
    version: int


class IssueOut(BaseModel):
    id: int
    document_id: int
    severity: str
    code: str
    message: str
    target_type: str
    target_id: int | None
    status: str
    locator_json: str | None


class DocumentOut(BaseModel):
    id: int
    occurrence_id: int
    batch_id: int
    document_set_id: int | None
    doc_type: str
    adapter_id: str
    adapter_version: str
    ir_schema_version: str
    review_status: str
    version: int
    locked_by_actor_id: str | None
    locked_at: datetime | None
    created_by_actor_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    sections: list[SectionOut] = Field(default_factory=list)
    fields: list[FieldOut] = Field(default_factory=list)
    rows: list[RowOut] = Field(default_factory=list)
    issues: list[IssueOut] = Field(default_factory=list)
    open_issue_count: int = 0
    created_order_id: int | None = None
    created_order_code: str | None = None


class DocumentSummaryOut(BaseModel):
    id: int
    occurrence_id: int
    batch_id: int
    doc_type: str
    review_status: str
    version: int
    adapter_id: str
    open_issue_count: int = 0
    updated_at: datetime | None
    created_order_id: int | None = None
    created_order_code: str | None = None


class OrderCodeOverrideIn(BaseModel):
    order_code: str
    expected_version: int
    reason: str | None = None


class FieldCorrectIn(BaseModel):
    corrected_value: str | None = None
    expected_version: int
    reason: str | None = None


class FieldRestoreIn(BaseModel):
    expected_version: int
    reason: str | None = None


class RowCorrectIn(BaseModel):
    cells_json: str | None = None
    cells: dict | None = None
    expected_version: int
    reason: str | None = None


class RowAddIn(BaseModel):
    cells_json: str | None = None
    cells: dict | None = None
    section_id: int | None = None
    row_key: str | None = None
    expected_version: int  # document version
    reason: str | None = None


class SectionReviewIn(BaseModel):
    review_status: str
    expected_version: int
    reason: str | None = None


class DocumentReviewIn(BaseModel):
    review_status: str
    expected_version: int


class IssueCreateIn(BaseModel):
    severity: str = "ERROR"
    code: str
    message: str
    target_type: str = "DOCUMENT"
    target_id: int | None = None
    locator_json: str | None = None


class IssueResolveIn(BaseModel):
    status: str = "RESOLVED"
    justification: str | None = None


class ReviewChangeOut(BaseModel):
    id: int
    document_id: int
    target_type: str
    target_id: int
    actor_id: str | None
    previous_value: str | None
    new_value: str | None
    previous_review_status: str | None
    new_review_status: str | None
    reason: str | None
    created_at: datetime | None


class DocumentSetCreateIn(BaseModel):
    batch_id: int | None = None
    projection_key: str | None = None
    label: str | None = None


class DocumentSetMemberIn(BaseModel):
    document_id: int
    role: str | None = None


class DocumentSetMemberOut(BaseModel):
    id: int
    document_set_id: int
    document_id: int
    role: str | None


class DocumentSetOut(BaseModel):
    id: int
    batch_id: int | None
    projection_key: str | None
    label: str | None
    created_by_actor_id: str | None
    created_at: datetime | None
    members: list[DocumentSetMemberOut] = Field(default_factory=list)


# --- J3-I3 adapter / commit ---


class RunAdapterIn(BaseModel):
    adapter_id: str | None = None
    doc_type: str | None = None


class RunAdapterOut(BaseModel):
    document_id: int
    doc_type: str
    adapter_id: str
    adapter_version: str
    review_status: str
    open_issue_count: int


class AdapterInfoOut(BaseModel):
    adapter_id: str
    doc_type: str
    label: str
    adapter_version: str = "1"
    mime_kinds: list[str] = Field(default_factory=list)


class ClassifySuggestionOut(BaseModel):
    adapter_id: str
    doc_type: str
    label: str
    confidence: str
    explanation: str


class ClassifyOut(BaseModel):
    occurrence_id: int
    filename: str | None = None
    detected_mime: str | None = None
    suggestions: list[ClassifySuggestionOut] = Field(default_factory=list)


class PreviewOperationOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None
    params: dict = Field(default_factory=dict)


class PreviewCommitOut(BaseModel):
    document_id: int
    fingerprint: str
    operations: list[PreviewOperationOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool
    can_create_order: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    human_summary: str = ""
    readiness_derived: bool = False


class CommitIn(BaseModel):
    operation_key: str
    # Optional override for dry_run / force (future)


class CommitOperationOut(BaseModel):
    id: int
    op_key: str
    status: str
    entity_type: str | None
    entity_id: str | None
    error_message: str | None
    details_json: str | None


class CommitAttemptOut(BaseModel):
    id: int
    document_id: int
    operation_key: str
    payload_fingerprint: str
    status: str
    actor_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    operations: list[CommitOperationOut] = Field(default_factory=list)


# --- J3-I4 Fattura schemas ---


class FatturaLineChoiceIn(BaseModel):
    row_index: int
    order_item_id: int


class FatturaCommitIn(BaseModel):
    operation_key: str
    policy: str  # A | B | C1 | C2
    order_id: int | None = None
    c2_confirm: bool = False
    c2_reason: str | None = None
    line_choices: list[FatturaLineChoiceIn] = Field(default_factory=list)


class FatturaPolicyMatchOut(BaseModel):
    policy: str
    order_id: int | None
    order_status: str | None
    order_code: str | None
    invoice_will_be_created: bool
    warning: str | None


class FatturaPreviewOperationOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None
    params: dict = Field(default_factory=dict)


class FatturaOrderCandidateOut(BaseModel):
    order_id: int
    order_code: str
    status: str
    supplier_id: int
    currency: str
    evidence: list[str] = Field(default_factory=list)
    currency_match: bool = True


class FatturaLineCandidateOut(BaseModel):
    order_item_id: int
    position: int
    unit_price: str | None = None
    remaining: str


class FatturaLineMatchOut(BaseModel):
    row_index: int
    sku: str
    pdf_qty: str
    pdf_unit_price: str | None = None
    order_item_id: int | None = None
    order_unit_price: str | None = None
    remaining_before: str | None = None
    candidate_count: int
    candidates: list[FatturaLineCandidateOut] = Field(default_factory=list)
    price_mismatch: bool = False
    ambiguous_price: bool = False
    status: str


class FatturaPreviewOut(BaseModel):
    document_id: int
    fingerprint: str
    policy_match: FatturaPolicyMatchOut
    operations: list[FatturaPreviewOperationOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool
    order_candidates: list[FatturaOrderCandidateOut] = Field(default_factory=list)
    order_candidates_reason: str | None = None
    line_matches: list[FatturaLineMatchOut] = Field(default_factory=list)
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_invoice_id: int | None = None


# --- J3-I5 Dossier schemas ---


class DossierCommitIn(BaseModel):
    operation_key: str


class DoganaleCommitIn(BaseModel):
    operation_key: str
    process_id: int | None = None
    invoice_id: int | None = None
    shipment_id: int | None = None


class ReconciliationIssueOut(BaseModel):
    code: str
    severity: str
    message: str
    doc_types: list[str] = Field(default_factory=list)


class DossierPreviewItemOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None = None


class DossierPreviewOut(BaseModel):
    document_set_id: int
    documents_found: list[str] = Field(default_factory=list)
    reconciliation_issues: list[ReconciliationIssueOut] = Field(default_factory=list)
    planned_operations: list[DossierPreviewItemOut] = Field(default_factory=list)
    can_commit: bool


class PackingLineChoiceIn(BaseModel):
    group_key: str
    order_item_id: int


class PackingCommitIn(BaseModel):
    operation_key: str
    order_id: int | None = None
    shipment_id: int | None = None
    line_choices: list[PackingLineChoiceIn] = Field(default_factory=list)


class PackingPreviewOperationOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = Field(default_factory=dict)


class PackingOrderCandidateOut(BaseModel):
    order_id: int
    order_code: str
    status: str
    supplier_id: int
    currency: str
    evidence: list[str] = Field(default_factory=list)
    currency_match: bool = True


class PackingShipmentTargetOut(BaseModel):
    shipment_id: int
    code: str
    status: str
    compatible: bool
    evidence: list[str] = Field(default_factory=list)


class PackingLineCandidateOut(BaseModel):
    order_item_id: int
    position: int
    sku: str
    description: str
    remaining: str
    line_kind: str


class PackingLineMatchOut(BaseModel):
    group_key: str
    ncm: str
    description: str
    carton_count: int
    total_qty: str
    packaging: bool
    order_item_id: int | None = None
    remaining_before: str | None = None
    candidate_count: int
    candidates: list[PackingLineCandidateOut] = Field(default_factory=list)
    status: str
    carton_row_indexes: list[int] = Field(default_factory=list)


class PackingCartonOut(BaseModel):
    row_index: int
    pallet_no: str | None = None
    carton_no: str | None = None
    items_per_ctn: str | None = None
    ncm: str
    description: str
    dimensions: str | None = None
    unit_net_weight_kg: str | None = None
    unit_gross_weight_kg: str | None = None
    total_net_weight_kg: str | None = None
    total_gross_weight_kg: str | None = None
    packaging: bool = False


class PackingPreviewOut(BaseModel):
    document_id: int
    fingerprint: str
    operations: list[PackingPreviewOperationOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool
    order_candidates: list[PackingOrderCandidateOut] = Field(default_factory=list)
    order_candidates_reason: str | None = None
    shipment_targets: list[PackingShipmentTargetOut] = Field(default_factory=list)
    shipment_targets_reason: str | None = None
    line_matches: list[PackingLineMatchOut] = Field(default_factory=list)
    cartons: list[PackingCartonOut] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    resolved_order_id: int | None = None
    resolved_shipment_id: int | None = None
    will_create_shipment: bool = False
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_shipment_id: int | None = None


class DoganalePreviewOpOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = Field(default_factory=dict)


class DoganaleProcessTargetOut(BaseModel):
    process_id: int
    code: str
    status: str
    compatible: bool
    evidence: list[str] = Field(default_factory=list)


class DoganaleInvoiceCandidateOut(BaseModel):
    invoice_id: int
    invoice_number: str
    status: str
    order_id: int | None = None
    linked_process_id: int | None = None
    evidence: list[str] = Field(default_factory=list)


class DoganaleShipmentTargetOut(BaseModel):
    shipment_id: int
    code: str
    status: str
    compatible: bool
    linked_process_id: int | None = None
    evidence: list[str] = Field(default_factory=list)


class DoganaleLinePreviewOut(BaseModel):
    position: int
    ncm: str | None = None
    description: str | None = None
    quantity: str | None = None
    unit: str | None = None
    currency: str | None = None
    unit_price: str | None = None
    line_amount: str | None = None


class DoganalePreviewOut(BaseModel):
    document_id: int
    fingerprint: str
    operations: list[DoganalePreviewOpOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool
    process_targets: list[DoganaleProcessTargetOut] = Field(default_factory=list)
    process_targets_reason: str | None = None
    invoice_candidates: list[DoganaleInvoiceCandidateOut] = Field(default_factory=list)
    invoice_candidates_reason: str | None = None
    shipment_targets: list[DoganaleShipmentTargetOut] = Field(default_factory=list)
    shipment_targets_reason: str | None = None
    lines: list[DoganaleLinePreviewOut] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    resolved_process_id: int | None = None
    resolved_invoice_id: int | None = None
    resolved_shipment_id: int | None = None
    will_create_process: bool = False
    reuse_reason: str | None = None
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_process_id: int | None = None
    document_number: str | None = None


class PrintCommitIn(BaseModel):
    operation_key: str
    process_id: int | None = None


class PrintPreviewOpOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = Field(default_factory=dict)


class PrintProcessTargetOut(BaseModel):
    process_id: int
    code: str
    status: str
    compatible: bool
    evidence: list[str] = Field(default_factory=list)


class PrintPreviewOut(BaseModel):
    document_id: int
    fingerprint: str
    operations: list[PrintPreviewOpOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool
    invoice_ref: str | None = None
    process_targets: list[PrintProcessTargetOut] = Field(default_factory=list)
    process_targets_reason: str | None = None
    blockers: list[str] = Field(default_factory=list)
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_process_id: int | None = None
    resolved_process_id: int | None = None


# --- J3-I6 Numerário schemas ---


class NumerarioCommitIn(BaseModel):
    operation_key: str
    process_ids: list[int] = Field(default_factory=list)
    create_process: bool = False


class NumerarioPreviewOpOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None = None
    process_id: int | None = None
    params: dict = Field(default_factory=dict)


class NumerarioProcessCandidateOut(BaseModel):
    process_id: int
    code: str
    status: str
    evidence: list[str] = Field(default_factory=list)


class NumerarioPreviewOut(BaseModel):
    document_id: int
    fingerprint: str
    invoice_refs: list[str] = Field(default_factory=list)
    process_ids_input: list[int] = Field(default_factory=list)
    planned_operations: list[NumerarioPreviewOpOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool
    process_candidates: list[NumerarioProcessCandidateOut] = Field(default_factory=list)
    process_candidates_reason: str | None = None
    already_committed: bool = False
    last_succeeded_attempt_id: int | None = None
    last_succeeded_process_id: int | None = None
    can_create_process: bool = False


class NumerarioOpResultOut(BaseModel):
    op_key: str
    status: str  # SUCCEEDED | FAILED | PARTIAL | UNKNOWN
    entity_type: str | None = None
    entity_id: str | None = None
    error_message: str | None = None
    details_json: str | None = None


class NumerarioCommitResultOut(BaseModel):
    attempt_id: int
    document_id: int
    operation_key: str
    status: str  # SUCCEEDED | PARTIAL | FAILED | UNKNOWN
    operations: list[NumerarioOpResultOut] = Field(default_factory=list)


# --- J3-I7 XLSX schemas ---


class XlsxRunAdapterOut(BaseModel):
    occurrence_id: int
    document_id: int
    adapter_id: str
    doc_type: str
    classified: bool
    field_count: int
    row_count: int
    issue_count: int
    formula_cell_count: int


class XlsxPreviewOperationOut(BaseModel):
    op_key: str
    description: str
    entity_type: str | None = None
    params: dict = Field(default_factory=dict)


class XlsxPreviewOut(BaseModel):
    document_id: int
    fingerprint: str
    operations: list[XlsxPreviewOperationOut] = Field(default_factory=list)
    open_error_count: int
    can_commit: bool


class XlsxCommitIn(BaseModel):
    operation_key: str | None = None


class XlsxCommitOpOut(BaseModel):
    op_key: str
    status: str
    entity_type: str | None = None
    entity_id: str | None = None


class XlsxCommitResultOut(BaseModel):
    attempt_id: int
    document_id: int
    status: str
    operations: list[XlsxCommitOpOut] = Field(default_factory=list)


# --- J3-I7 Metrics schemas ---


class MetricEventOut(BaseModel):
    id: int
    adapter_id: str
    adapter_version: str
    event_type: str
    document_id: int | None
    occurrence_id: int | None
    payload_json: str | None
    created_at: datetime | None


class AdapterMetricsSummaryOut(BaseModel):
    adapter_id: str
    adapter_version: str
    total_runs: int
    classified_count: int
    classification_rate: float
    avg_field_count: float
    avg_issue_count: float
    total_corrections: int
    total_commits: int
    total_retries: int
    commit_success_count: int
    commit_partial_count: int
    commit_failed_count: int
    avg_matched_lines: float
