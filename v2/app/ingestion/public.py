"""API pública do módulo Ingestion."""

from app.ingestion.commands import (
    abandon_occurrence,
    create_batch,
    execute_purge,
    plan_purge,
    upload_files,
)
from app.ingestion.commit_commands import (
    CommitAttemptNotFound,
    CommitBlockedByIssues,
    CommitConflictFingerprint,
    CommitDocumentNotReady,
    execute_commit,
    preview_commit,
)
from app.ingestion.commit_queries import (
    get_commit_attempt,
    list_commit_attempts_for_document,
)
from app.ingestion.parse_it import parse_it_date, parse_it_number
from app.ingestion.queries import get_batch_with_occurrences, get_occurrence_detail
from app.ingestion.staging_commands import (
    add_document_to_set,
    add_row,
    correct_field,
    correct_row,
    create_document_set,
    create_issue,
    effective_field_value,
    lock_document,
    remove_row,
    resolve_issue,
    restore_field,
    seed_document_from_occurrence,
    set_document_review_status,
    unlock_document,
)
from app.ingestion.staging_queries import (
    get_document_detail,
    get_document_set,
    list_documents_for_batch,
    list_review_changes,
    staging_queue,
)

__all__ = [
    "parse_it_date",
    "parse_it_number",
    "create_batch",
    "upload_files",
    "abandon_occurrence",
    "execute_purge",
    "plan_purge",
    "get_batch_with_occurrences",
    "get_occurrence_detail",
    "seed_document_from_occurrence",
    "correct_field",
    "restore_field",
    "correct_row",
    "add_row",
    "remove_row",
    "set_document_review_status",
    "lock_document",
    "unlock_document",
    "create_issue",
    "resolve_issue",
    "create_document_set",
    "add_document_to_set",
    "effective_field_value",
    "get_document_detail",
    "list_documents_for_batch",
    "list_review_changes",
    "get_document_set",
    "staging_queue",
    # J3-I3 commit ledger
    "preview_commit",
    "execute_commit",
    "get_commit_attempt",
    "list_commit_attempts_for_document",
    "CommitAttemptNotFound",
    "CommitBlockedByIssues",
    "CommitConflictFingerprint",
    "CommitDocumentNotReady",
]
