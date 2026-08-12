"""Erros de domínio Ingestion — sem HTTP."""


class IngestionError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class BatchNotFound(IngestionError):
    def __init__(self, batch_id: int):
        super().__init__(f"Batch {batch_id} não encontrado", code="batch_not_found")


class OccurrenceNotFound(IngestionError):
    def __init__(self, occurrence_id: int):
        super().__init__(f"Occurrence {occurrence_id} não encontrada", code="occurrence_not_found")


class BatchClosed(IngestionError):
    def __init__(self):
        super().__init__("Batch fechado — upload não permitido", code="batch_closed")


class IdempotencyConflict(IngestionError):
    def __init__(self):
        super().__init__(
            "client_upload_key já usado com fingerprint divergente",
            code="idempotency_conflict",
        )


class InvalidTransition(IngestionError):
    def __init__(self, message: str):
        super().__init__(message, code="invalid_transition")


class ValidationRejected(IngestionError):
    """Arquivo rejeitado pela política de segurança — vira occurrence REJECTED."""

    def __init__(self, reason: str, *, code: str = "validation_rejected"):
        super().__init__(reason, code=code)
        self.reason = reason


class RequestLimitExceeded(IngestionError):
    def __init__(self, message: str, *, code: str = "request_limit_exceeded"):
        super().__init__(message, code=code)


class DocumentNotFound(IngestionError):
    def __init__(self, document_id: int):
        super().__init__(f"Document {document_id} não encontrado", code="document_not_found")


class FieldNotFound(IngestionError):
    def __init__(self, field_id: int):
        super().__init__(f"Field {field_id} não encontrado", code="field_not_found")


class RowNotFound(IngestionError):
    def __init__(self, row_id: int):
        super().__init__(f"Row {row_id} não encontrado", code="row_not_found")


class SectionNotFound(IngestionError):
    def __init__(self, section_id: int):
        super().__init__(f"Section {section_id} não encontrada", code="section_not_found")


class IssueNotFound(IngestionError):
    def __init__(self, issue_id: int):
        super().__init__(f"Issue {issue_id} não encontrada", code="issue_not_found")


class IssueJustificationRequired(IngestionError):
    def __init__(self) -> None:
        super().__init__(
            "Ignorar um erro exige justificativa",
            code="issue_justification_required",
        )


class DocumentSetNotFound(IngestionError):
    def __init__(self, set_id: int):
        super().__init__(f"DocumentSet {set_id} não encontrado", code="document_set_not_found")


class VersionConflict(IngestionError):
    def __init__(self, message: str = "Versão desatualizada (optimistic concurrency)"):
        super().__init__(message, code="version_conflict")


class DocumentLocked(IngestionError):
    def __init__(self, message: str = "Documento bloqueado por outro ator"):
        super().__init__(message, code="document_locked")


class OccurrenceNotStored(IngestionError):
    def __init__(self, occurrence_id: int):
        super().__init__(
            f"Occurrence {occurrence_id} não está STORED",
            code="occurrence_not_stored",
        )


class DocumentAlreadyExists(IngestionError):
    def __init__(self, occurrence_id: int):
        super().__init__(
            f"Já existe IR para occurrence {occurrence_id}",
            code="document_already_exists",
        )


class BlobUnavailable(IngestionError):
    def __init__(self, occurrence_id: int):
        super().__init__(
            f"Blob da occurrence {occurrence_id} indisponível",
            code="blob_unavailable",
        )


class ReextractBlocked(IngestionError):
    def __init__(self, document_id: int, reason: str):
        super().__init__(
            f"Reextract bloqueado para document {document_id}: {reason}",
            code="reextract_blocked",
        )


class DocumentDeleteBlocked(IngestionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="document_delete_blocked")


class DocumentRejectBlocked(IngestionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="document_reject_blocked")
