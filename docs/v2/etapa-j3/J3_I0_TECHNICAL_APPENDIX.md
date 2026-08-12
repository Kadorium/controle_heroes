# J3-I0 — Technical Appendix

Handoff de decisão: [`J3_I0_ADVISOR_HANDOFF.md`](J3_I0_ADVISOR_HANDOFF.md).

## 1. Schema (resumo)

- `ingestion_batches` — status OPEN/CLOSED; actor; timestamps
- `ingestion_blobs` — UNIQUE(sha256); physical_status PRESENT/PURGED; storage_path; purged_at
- `ingestion_occurrences` — FK batch/blob; status lifecycle; retain_until; bytes_purged_at; physical_reuse; rehydrated; partial UNIQUE(batch_id, client_upload_key) WHERE key IS NOT NULL

## 2. Ordem FS × DB

1. Stream → `_tmp/*.part` + SHA-256 incremental + limite
2. Validação (falha → occurrence REJECTED; unlink temp)
3. Lock blob by hash (`SELECT FOR UPDATE`)
4. PRESENT+file → reuse; PURGED/missing → rename atômico + rehydrate
5. Insert/update DB + Audit na UoW
6. Commit; rollback → cleanup `pending_files`

## 3. Purge compartilhado

Blob elegível iff todas occurrences ∈ {REJECTED, ABANDONED, FAILED} e `retain_until <= now`. Dry-run lista blockers por blob.

## 4. Segurança

- PDF: pypdf + token scan; policy REJECT conteúdo ativo
- XLSX: zipfile; REJECT macro/external/OLE/traversal/bomb
- Settings: `ingestion_max_*`, TTL 30d, quarantine_path

## 5. Testes

`test_ingestion_i0_{domain,security,api,arch}.py` + fixtures sintéticas em `tests/ingestion_i0_fixtures.py`.

## 6. Comandos de gate (execução)

```text
pytest tests/test_ingestion_i0_*.py tests/architecture/test_import_boundaries.py
alembic upgrade/downgrade 015↔016 (DATABASE_URL=epic_v2_test)
npm run generate:api && npm run check:api-drift && npm run build
```
