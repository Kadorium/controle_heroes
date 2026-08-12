# J3-I0 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | J3-I0 — Fundação segura da ingestão |
| Status | **DONE** |
| Data | 2026-08-04 |
| Roadmap | **0.5.67** |
| Alembic | **016_ingestion_foundation** (head) |
| Plano canônico da fase | [`J3_EXECUTION_PLAN.md`](J3_EXECUTION_PLAN.md) |
| Apêndice | [`J3_I0_TECHNICAL_APPENDIX.md`](J3_I0_TECHNICAL_APPENDIX.md) |
| I1 | **NOT_STARTED** |

Planos Cursor externos (`.cursor/plans/*`) **não** são a autoridade da fase; o detalhe operacional versionado é `J3_EXECUTION_PLAN.md`.

---

## 1. Estado inicial

| Item | Valor |
|---|---|
| Branch | `main` |
| Roadmap | 0.5.66 → I0 NOT_STARTED |
| Alembic | 015 |
| Ingestion | foothold `parse_it` only; `ALLOWED_DEPS=∅` |
| WIP | preservado (sem commit/reset) |

---

## 2. Hipóteses H-I0-01…12

| ID | Veredito | Evidência |
|---|---|---|
| H-I0-01 | **CONFIRMADA** | 0.5.66; P0 DONE; Alembic 015 |
| H-I0-02 | **CONFIRMADA** | só parse_it |
| H-I0-03 | **CONFIRMADA** | Batch/Blob/Occurrence distintos |
| H-I0-04 | **CONFIRMADA** | mesmo hash → N occurrences / 1 blob |
| H-I0-05 | **CONFIRMADA** | sem Document/Link |
| H-I0-06 | **CONFIRMADA** | `ingestion → audit` only (sem Documents sem uso) |
| H-I0-07 | **CONFIRMADA** | path `{sha[:2]}/{sha}_{nonce}` |
| H-I0-08 | **CONFIRMADA** | validação PDF/XLSX + limites |
| H-I0-09 | **CONFIRMADA** | purge service + `POST /purge`; sem cron |
| H-I0-10 | **CONFIRMADA** | `read/write/commit/purge`; comprador read+write |
| H-I0-11 | **CONFIRMADA** | temp→validate→rename→UoW+pending cleanup |
| H-I0-12 | **CONFIRMADA** | sem adapters/IR/FE/commit |

---

## 3. Correções H-I0-FIX-01…08

| FIX | Decisão |
|---|---|
| **01** | PK `Integer` serial — alinhado a todos os módulos V2 |
| **02** | Occurrence **sem** status PURGED; bytes via Blob `PRESENT`/`PURGED` + `bytes_purged_at` |
| **03** | Purge físico só se **todas** occurrences do blob terminais + `retain_until` vencido; dry-run com blockers |
| **04** | Blob PURGED + reupload → reidrata bytes; `rehydrated=true`; nunca STORED sem arquivo |
| **05** | Multi-upload parcial: inválido → REJECTED; válidos seguem; limites de arquivos/bytes |
| **06** | PDF ativo (`/JavaScript`, `/OpenAction`, `/Launch`, embedded…) → **REJECT** |
| **07** | XLSX macro/external/OLE/traversal/bomb → **REJECT**; sem openpyxl; fórmulas não executadas |
| **08** | Ordem temp→validate→dedup/rehydrate→rename→DB; pending cleanup; unique hash + savepoint |

---

## 4. Entregas

- Migration `016`; models; quarantine storage; validation; commands/queries; routes
- RBAC `ingestion:*`; Audit eventos batch/upload/abandon/purge
- `pypdf>=5.0.0` (baseline; não exclusivo de adapters)
- OpenAPI regenerado; arch tests PASS
- Blueprint §5.9 atualizado (fundação I0)
- `J3_EXECUTION_PLAN.md` criado/sincronizado

### APIs

| Método | Path | Perm |
|---|---|---|
| POST | `/api/ingestion/batches` | write |
| POST | `/api/ingestion/batches/{id}/files` | write |
| GET | `/api/ingestion/batches/{id}` | read |
| GET | `/api/ingestion/occurrences/{id}` | read |
| POST | `/api/ingestion/occurrences/{id}/abandon` | write |
| POST | `/api/ingestion/purge` | purge |

### Estados

- Batch: OPEN/CLOSED
- Occurrence: RECEIVED → VALIDATING → STORED \| REJECTED \| FAILED; STORED → ABANDONED
- Blob: PRESENT \| PURGED

---

## 5. Gates

| Gate | Resultado |
|---|---|
| Alembic 015↔016 | **PASS** (`epic_v2_test`) |
| pytest I0 + arch | **PASS** (26) |
| OpenAPI drift | **PASS** |
| FE build | **PASS** |
| I1 iniciado? | **Não** |

---

## 6. Divergências

- Handoff P0 §8 sugeria aresta Documents em I0; **não** adicionada (H-I0-06 / uso efetivo zero).
- Blueprint mínimo expandido em §5.9 para Batch/Blob/Occurrence + quarantine.

---

## 7. Pendências / fora de I0

- I1 staging IR + DocumentSet; adapters; FE; promote Documents; commit ledger; scheduler de purge; OCR

---

## 8. Próxima etapa

**Revisão J3-I0 pelo advisor — não iniciar I1.**

---

## 9. Arquivos de código relevantes (se advisor quiser inspecionar)

`v2/app/ingestion/{models,commands,storage,validation,routes,limits}.py` · `v2/alembic/versions/016_ingestion_foundation.py` · `v2/app/foundation/{settings,module_graph,create_app}.py` · `v2/app/identity/public.py` · `v2/tests/test_ingestion_i0_*.py`

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md §5.9; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/README.md; .cursor/rules unchanged
- Evidence: docs/v2/etapa-j3/ (I0 handoff + appendix + execution plan)
- Roadmap status: 0.5.67 — J3-I0 DONE; I1 NOT_STARTED; próxima = revisão advisor I0
- Next TODO: Revisão J3-I0 pelo advisor — não iniciar I1
- Return to advisor: docs/v2/etapa-j3/J3_I0_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_I0_TECHNICAL_APPENDIX.md
```
