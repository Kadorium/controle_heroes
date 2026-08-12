# J#3 — Handoff consolidado da campanha I1→I7

> Pacote principal ao advisor. Atualizado progressivamente.  
> Apêndice técnico (opcional): `J3_EXECUTION_CAMPAIGN_TECHNICAL_APPENDIX.md`.  
> Plano mestre: `planning_j3_ingestão_909721db.plan.md` · Espelho: `J3_EXECUTION_PLAN.md`.

| Campo | Valor |
|---|---|
| Campanha | J#3 I1→I7 |
| Início | 2026-08-04 |
| Status campanha | **DONE** |
| Roadmap | **0.5.74** (I7 DONE) |

---

## Preflight

### Estado Git/WIP (registrado)

| Item | Valor |
|---|---|
| Branch | `main` |
| HEAD | `67f73151d8b19d879810fda630766602e9785dac` |
| Alembic ao iniciar | `016_ingestion_foundation` |
| WIP | Preservado (sem commit/reset/clean) |

### Ações de preflight

- [x] Regra de plano mestre inserida em `.cursor/rules/epic-v2.mdc` (§2)
- [x] Handoff consolidado aberto
- [x] Espelho sincronizado
- [x] Roadmap 0.5.68 ao iniciar I1

---

## I1 — Staging IR, provenance e review backend

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Migration | **017_ingestion_staging_ir** (head) |
| Blueprint | 0.2.18 §5.9 |
| Module graph | `ingestion → audit` (sem Documents) |

### Hipóteses

| Hipótese | Veredito |
|---|---|
| IR versionado sustenta review sem UI | **CONFIRMADA** |
| Relação mínima DocumentSet basta | **CONFIRMADA** |
| Deps só Audit | **CONFIRMADA** |

### Entregas

- Models: Document, Section, Field, Row, Issue, ReviewChange, DocumentSet(+members)
- Invariantes: vazio≠zero; raw imutável por correção; locator opcional NULL
- APIs staging/review; lock; optimistic concurrency; Audit; RBAC write/read
- Adapter `contract_stub_v1` apenas para provar contrato (não produção)
- OpenAPI regenerado; drift PASS
- Testes: `test_ingestion_i1_domain.py`, `test_ingestion_i1_api.py` + regressão I0

### Gates

| Gate | Resultado |
|---|---|
| Migration 016→017 | PASS (alembic head 017) |
| pytest I1 + I0 | **27 passed** |
| architecture | PASS |
| OpenAPI drift | PASS |
| Escrita em owners | Nenhuma |
| UI / commit / promote | Fora de I1 |

### Arquivos principais

- `v2/app/ingestion/ir_models.py`, `staging_commands.py`, `staging_queries.py`
- `v2/app/ingestion/routes.py`, `schemas.py`, `errors.py`, `public.py`
- `v2/alembic/versions/017_ingestion_staging_ir.py`
- `v2/tests/test_ingestion_i1_*.py`

### Pendências → I2+

- UI SCR-037/038; viewer/locator; adapters reais; commit ledger; promote Documents

---

## I2 — Fila, workspace e viewer

| Campo | Valor |
|---|---|
| Status | **DONE** |
| SCR | SCR-037 fila · SCR-038 workspace base |
| Gates | Vitest PASS; tsc+build PASS; API drift PASS; content endpoint quarantine |

### Entregas
- `features/ingestion/*` — queue, workspace, PdfViewerPanel (páginas/zoom/locator overlay)
- Nav Compras → Ingestão (`ingestion:read`)
- GET `/api/ingestion/occurrences/{id}/content` (quarantine → viewer; sem promote)
- Contrato UI consome IR real de I1; stub adapter rotulado como contrato, não produção

### Testes
- `IngestionPages.test.tsx` (3)
- build frontend PASS


---

## I3 — Ordine 589 → Order DRAFT vertical

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Migration | **018_ingestion_commit_ledger** (head) |
| Module graph | `ingestion → {audit, documents, orders, catalog}` |
| Alembic head | **018** |
| Pytest I3 | **23 passed** |

### Hipóteses

| Hipótese | Veredito |
|---|---|
| pypdf extrai campos suficientes (Ordine 589) | **CONFIRMADA** — layout mode necessário |
| I.V. 1 / I.V. 2 → AMBIGUOUS_SKU (nunca silencioso) | **CONFIRMADA** |
| Fingerprint estável entre chamadas | **CONFIRMADA** |
| Mesmo op_key + mesmo fingerprint → idempotente | **CONFIRMADA** |
| Mesmo op_key + fingerprint diferente → 409 | **CONFIRMADA** |
| commit path: store_document + create_order + link | **CONFIRMADA** |
| PARTIAL se create_order falha após store_document | **CONFIRMADA** |
| Dual-auth ingestion:commit + orders:write | **CONFIRMADA** |

### Entregas

- **Adapter** `ordine_heroes_v1`: pypdf layout mode + regex space-tolerant; extract() puro; match_catalog() via catalog.public; _validate_math() → issues MATH_TAXABLE_ZERO_MISMATCH
- **Commit ledger**: `IngestionCommitAttempt` + `IngestionCommitOperation` (migration 018); idempotência por `operation_key` + `payload_fingerprint`
- **Preview**: `GET /api/ingestion/documents/{id}/preview-commit` — digest SHA-256 + lista ops, sem escrever owners
- **Commit**: `POST /api/ingestion/documents/{id}/commit` — store_document + create_order(DRAFT) + link_document + add_items best-effort; PARTIAL se alguma op falha após sucesso prévio
- **Adapter endpoint**: `POST /api/ingestion/occurrences/{id}/run-adapter`
- **Ledger endpoints**: `GET /commit-attempts/{id}`, `GET /documents/{id}/commit-attempts`
- **Architecture**: ingestion → {audit, documents, orders, catalog} — sem internals; sem V1

### Gates

| Gate | Resultado |
|---|---|
| Migration 017→018 | PASS |
| pytest I3 (23 tests) | **23 passed** |
| architecture tests | **6 passed** |
| I0 tests regressão | **20 passed** |
| Sem escrita owners em preview | PASS |
| Order criada como DRAFT (nunca auto-confirm) | PASS |
| AMBIGUOUS_SKU nunca silencioso | PASS |
| Dual-auth ingestion:commit + orders:write | PASS |
| Idempotência mesma chave+fingerprint | PASS |
| 409 para chave+fingerprint divergente | PASS |
| PARTIAL bloqueado por open ERROR issues | PASS (422) |

### Nota sobre PDF extraction

O PDF Ordine 589 usa font encoding com espaços entre caracteres (ex: "T O T AL E"). O adapter usa `extraction_mode='layout'` do pypdf e aplica `_spaced()` para gerar regex space-tolerant. Fallback para modo padrão (colunas por linha) para itens de tabela.

### Arquivos principais

- `v2/app/ingestion/adapters/__init__.py`, `ordine_heroes_v1.py`
- `v2/app/ingestion/commit_models.py`, `commit_commands.py`, `commit_queries.py`
- `v2/app/ingestion/routes.py` (endpoints I3), `schemas.py`, `public.py`, `errors.py`
- `v2/app/foundation/module_graph.py` (ingestion deps ampliados)
- `v2/alembic/versions/018_ingestion_commit_ledger.py`
- `v2/tests/test_ingestion_i3.py` (23 testes)
- `v2/tests/test_ingestion_i0_arch.py` (atualizado para I3)

### Pendências → I4+

- FE: painel de commit result / deep-link para Order — **feito** (`CommitResultPanel`)
- OpenAPI regenerado — **feito**
- Gate de reavaliação pós-I3 (§16-A) — **PASS** (IR/UI/locators/matching/preview/ledger/promotion/PARTIAL/idempotência/pytest I0…I3)

### Gate reavaliação pós-I3 (obrigatório)

| Item | Resultado |
|---|---|
| IR I1 vs Ordine real | PASS — adapter usa IR seed |
| UI I2 vs dados reais | PASS — workspace + CommitResultPanel |
| Locators | PASS — overlay + parseLocator |
| Matching AMBIGUOUS_SKU | PASS |
| Preview digest/fingerprint | PASS |
| Ledger todas ops | PASS |
| Promote Documents no commit | PASS |
| PARTIAL/UNKNOWN | PASS |
| Idempotência | PASS |
| Regressão I0…I3 | PASS (35+ pytest) |

---

## I4…I7

| Checkpoint | Status |
|---|---|
| I4 Fattura 202 | **DONE** |
| I5 Dossiê 202 | **DONE** |
| I6 Numerário | **DONE** |
| I7 XLSX/F328/E2E | **DONE** |

---

## I7 — XLSX adapter, F328 regressions, métricas, E2E

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Alembic | **019** (`019_ingestion_metrics_events`) |
| Module graph | `ingestion → {audit, documents, orders, catalog, billing, logistics, customs}` (sem alteração) |
| Pytest I7 | **47 passed** |
| Pytest ingestion suite total | **248 passed** |
| Pytest architecture | **6 passed** |
| Regras hard preservadas | NEVER execute formula cells; NEVER auto-confirm Order XLSX; fórmulas preservadas como raw_value; métricas best-effort |

### Hipóteses

| Hipótese | Veredito |
|---|---|
| openpyxl extrai campos suficientes (ordine758/759) | **CONFIRMADA** — order_number, versato, ship_items, invoice_records, provenance |
| data_only=False preserva fórmulas sem executar | **CONFIRMADA** — formula string como raw_value, is_formula=True, normalized_value=None |
| Provenance locator sheet/row/col é suficiente | **CONFIRMADA** — locator_json com sheet, row, col, source="openpyxl" |
| Adapters existentes cobrem F328 sem adapter dedicado | **CONFIRMADA** — fattura_heroes_v1, packing_list_detail_v1, packing_list_grouped_v1, fattura_doganale_v1, print_declaration_v1 todos funcionam em corpus_328 |
| Audit-based metrics (append-only ingestion_metric_events) suficiente | **CONFIRMADA** — migration 019; record_adapter_run + matching + commit events; best-effort |
| Physical reuse (SHA-256) cobre reupload idempotente | **CONFIRMADA** — occ2.physical_reuse=True para mesmo arquivo |
| Idempotência por operation_key + fingerprint cobre replay/resume | **CONFIRMADA** — attempt_id_1 == attempt_id_2 em commit repetido |

### Entregas

- **Migration** `019_ingestion_metrics_events`: tabela `ingestion_metric_events` (adapter_id, adapter_version, event_type, document_id, occurrence_id, payload_json, created_at)
- **Model** `metrics_models.py`: `IngestionMetricEvent` + `METRIC_EVENT_TYPES`
- **Metrics module** `metrics_commands.py`: `record_adapter_run`, `record_matching_result`, `record_commit_attempt`, `record_commit_complete`, `record_field_corrected`, `record_review_complete`, `get_adapter_metrics` (AdapterMetricsSummary), `list_metric_events`
- **Adapter** `ordine_heroes_xlsx_v1`: openpyxl data_only=False; sheet/row/col provenance; DA SPEDIRE section; invoice tracking; classify(); _validate_items(); match_catalog(); run_adapter() + best-effort metrics
- **Commit** `xlsx_commit_commands.py`: preview_commit_xlsx() + commit_xlsx(); store_document + create_order DRAFT + add_items best-effort + link_document; idempotência ledger reutilizado
- **Schemas I7**: XlsxRunAdapterOut, XlsxPreviewOut, XlsxCommitIn, XlsxCommitResultOut, MetricEventOut, AdapterMetricsSummaryOut
- **Routes I7** (5 endpoints):
  - `POST /api/ingestion/occurrences/{id}/run-adapter-xlsx`
  - `GET /api/ingestion/documents/{id}/preview-commit-xlsx`
  - `POST /api/ingestion/documents/{id}/commit-xlsx` (requer `ingestion:commit` + `orders:write`)
  - `GET /api/ingestion/metrics/adapter/{adapter_id}/{adapter_version}`
  - `GET /api/ingestion/metrics/events`
- **F328 regressions**: 5 adapters × corpus_328 + F181/F202 regressions no test_ingestion_i7.py
- **E2E journey**: upload→classify→run→review→correct→preview→commit(PARTIAL)→reupload→physical_reuse→replay→idempotent→metrics
- **Arch test atualizado**: test_ingestion_i0_arch.py corrigido para I5 (logistics+customs em ingestion deps; treasury+inventory ainda proibidos)
- **OpenAPI**: regenerado; drift PASS; tsc PASS; build frontend PASS; 79 vitest PASS
- **OCR real**: explicitamente BACKLOG (não automatizável neste sprint)
- **module_graph**: `.xlsx_commit_commands`, `.metrics_commands`, `.metrics_models` adicionados a INTERNAL_SUFFIXES

### Gates

| Gate | Resultado |
|---|---|
| Migration 018→019 | PASS |
| Alembic heads | 019 (head) |
| pytest I7 (47 tests) | **47 passed** |
| pytest ingestion suite completo | **248 passed** |
| pytest architecture (6 tests) | **6 passed** |
| F328 regressions (5 adapters) | PASS |
| F181/F202 regressions | PASS |
| Formula preserved NOT executed | PASS |
| Provenance locator sheet/row/col | PASS |
| Métricas event table | PASS |
| E2E upload→commit | PASS |
| Idempotência xlsx | PASS |
| Physical reuse (reupload) | PASS |
| OpenAPI drift | PASS |
| frontend build + tsc | PASS |
| vitest (79 tests) | PASS |
| sem V1 imports | PASS |

### Arquivos principais

- `v2/alembic/versions/019_ingestion_metrics_events.py` (novo)
- `v2/app/ingestion/metrics_models.py` (novo)
- `v2/app/ingestion/metrics_commands.py` (novo)
- `v2/app/ingestion/adapters/ordine_heroes_xlsx_v1.py` (novo)
- `v2/app/ingestion/xlsx_commit_commands.py` (novo)
- `v2/app/ingestion/schemas.py` (+ I7 schemas)
- `v2/app/ingestion/routes.py` (+ 5 endpoints I7)
- `v2/app/foundation/module_graph.py` (+ INTERNAL_SUFFIXES I7)
- `v2/tests/conftest.py` (+ metrics_models import)
- `v2/tests/test_ingestion_i7.py` (47 testes)
- `v2/tests/test_ingestion_i0_arch.py` (atualizado I5)
- `v2/frontend/src/api/generated/` (OpenAPI regenerado)

### Pendências → J#3 DONE / J#6

- OCR real (tesseract/azure-vision): **BACKLOG explícito** — fora do escopo desta campanha
- FE panels para XLSX/metrics: non-blocking (adapters funcionais sem UI dedicada)
- J#6 Costing / Reconciliation: próxima fase

---

## I4 — Fattura 202 → Invoice DRAFT (policy A/B/C1/C2)

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Alembic | **018** (sem nova migration — reusa ledger I3) |
| Module graph | `ingestion → {audit, documents, orders, catalog, billing}` |
| Pytest I4 | **31 passed** |
| Regras hard preservadas | NEVER Invoice with DRAFT order; NEVER silent confirm; NEVER auto Payment; NEVER infer ACCONTO; NEVER auto-emit beyond DRAFT |

### Hipóteses

| Hipótese | Veredito |
|---|---|
| pypdf extrai campos suficientes (Fattura 202) | **CONFIRMADA** — default mode para header/scadenze, layout para linhas |
| policy A/B/C1/C2 cobre todos os cenários reais | **CONFIRMADA** — 4 caminhos testados e passando |
| C1 não busca Order automaticamente (user escolhe reconstruir) | **CONFIRMADA** — auto-search removido para C1/C2 |
| C2 reconstroi + confirma + cria Invoice na mesma sessão com dual-auth | **CONFIRMADA** — requires c2_confirm=True + c2_reason |
| Commit ledger existente (018) reutilizável para Fattura | **CONFIRMADA** — extendido em fattura_commit_commands.py |
| `db.expire(order)` em `_lock` resolve identity-map issue com items | **CONFIRMADA** — fix em orders/commands.py |

### Entregas

- **Adapter** `fattura_heroes_v1`: pypdf dual-mode (default header + layout lines); extrai 7 linhas; EANs; descrições; qtds; preços; totais; EUR 30188; 2 scadenze EUR 15094 cada; termos pagamento; DDT refs
- **Policy A/B/C1/C2** em `fattura_commit_commands.py`: `_find_matching_order` com parâmetro `policy` (C1/C2 não auto-busca); reconstruct code único por document_id
- **C2**: popula itens da IR no reconstruction order antes de confirmar (items obrigatórios)
- **Preview**: `GET /api/ingestion/documents/{id}/preview-commit-fattura` — policy analysis + operations list
- **Commit**: `POST /api/ingestion/documents/{id}/commit-fattura` — store_document + match_order + create_invoice(DRAFT) + set_terms(scadenze) + link_document
- **FE minimal**: `FatturaCommitPanel.tsx` — selector A/B/C1/C2; orderId input; c2Reason; preview; commit
- **Architecture**: `billing` adicionado a `ingestion` ALLOWED_DEPS; test arch atualizado
- **OpenAPI**: regenerado (generate:api ✓)
- **Fix transversal**: `orders/commands.py` `_lock` → `db.expire(order)` antes de re-fetch (identity-map reliability)

### Gates

| Gate | Resultado |
|---|---|
| pytest I4 (31 tests) | **31 passed** |
| pytest regressão (230 outros) | **230 passed** |
| architecture test billing | **PASS** |
| sem escrita owners em preview | PASS |
| Invoice criada como DRAFT (nunca além) | PASS |
| NEVER Invoice with Order DRAFT (policy A+DRAFT → 422) | PASS |
| NEVER silent Order confirmation (policy B → 422 order_draft_must_confirm) | PASS |
| Policy C1: reconstruction DRAFT sem Invoice | PASS |
| Policy C2: dual-auth c2_confirm=True + c2_reason | PASS |
| C2 sem c2_reason → 422 c2_missing_reason | PASS |
| Scadenze set (2 × EUR 15094) | PASS |
| Idempotência mesma op_key+fingerprint | PASS |
| 409 para op_key+fingerprint divergente | PASS |
| Permissões billing:write obrigatórias | PASS |
| OpenAPI drift | PASS |

### Arquivos principais

- `v2/app/ingestion/adapters/fattura_heroes_v1.py` (novo)
- `v2/app/ingestion/fattura_commit_commands.py` (novo)
- `v2/app/ingestion/schemas.py` (FatturaCommitIn, FatturaPreviewOut, FatturaPolicyMatchOut)
- `v2/app/ingestion/routes.py` (endpoints: run-adapter-fattura, preview-commit-fattura, commit-fattura)
- `v2/app/foundation/module_graph.py` (billing adicionado a ingestion)
- `v2/app/orders/commands.py` (_lock fix: db.expire)
- `v2/frontend/src/features/ingestion/FatturaCommitPanel.tsx` (novo)
- `v2/frontend/src/features/ingestion/ingestionApi.ts` (runAdapterFattura, fetchFatturaPreview, commitFatturaDocument)
- `v2/frontend/src/features/ingestion/IngestionWorkspacePage.tsx` (FatturaCommitPanel integrado)
- `v2/tests/test_ingestion_i4.py` (31 testes)
- `v2/tests/test_ingestion_i0_arch.py` (billing dep guard atualizado)
- `v2/frontend/src/api/generated/` (OpenAPI regenerado)

### Pendências → I5

- FE aceite via browser test (I4 gate: pytest suficiente per spec)
- Painel review Fattura no workspace (campo por campo com correção)
- I5: Dossiê 202 + PL Grouped + Doganale + PrintDeclaration

---

## I5 — Dossiê 202: PL Detail + PL Grouped + Doganale + PrintDeclaration

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Alembic | **018** (sem nova migration — reutiliza ledger I3/I4) |
| Module graph | `ingestion → {audit, documents, orders, catalog, billing, logistics, customs}` |
| Pytest I5 | **56 passed** |
| Pytest arch | **6 passed** (total 62 para os dois módulos) |
| Regras hard preservadas | NEVER PL Grouped como SoT; AMBIGUITY\_\* sempre WARNING não ERROR; NO fixed DB column por Y-code; sem Payment |

### Hipóteses

| Hipótese | Veredito |
|---|---|
| pypdf extrai campos suficientes dos 4 tipos de documento | **CONFIRMADA** — layout+default modes |
| "chinaItaly" é padrão de sobreposição de camadas PDF | **CONFIRMADA** — extraído como dual-layer em annotations.py |
| PL Grouped = evidência de ambiguidade, não SoT comercial | **CONFIRMADA** — P0 decision documentada; issues são WARNING |
| Y-codes PrintDeclaration devem ser coleção JSON, não colunas fixas | **CONFIRMADA** — stored como json_field `y_codes_collection_json` |
| Reconciler cross-documentale funciona com mocks | **CONFIRMADA** — 9 casos testados |
| Logistics/Customs via public APIs apenas (sem import de internals) | **CONFIRMADA** — module_graph atualizado |
| Preview sem escrita é possível sem duplicar lógica de commit | **CONFIRMADA** — preview_dossier() puro + reconcile_document_set() lê-only |

### Entregas

- **4 adapters novos**: `packing_list_detail_v1`, `packing_list_grouped_v1`, `fattura_doganale_v1`, `print_declaration_v1`
  - Cada um: `extract()` puro + `classify()` + `run_adapter()` (DB-aware) + `_validate_*()` com issues
  - PL Grouped: emite AMBIGUITY\_PL\_GROUPED (WARNING) e PACKAGING\_LINE\_NCM4819 (INFO); flag `is_sot=false` no IR
  - PrintDeclaration: Y-codes como coleção JSON (`y_codes_collection_json`) + dicionário de títulos; sem coluna fixa por Y-code
  - Fattura Doganale: math validation linha a linha; DUAL\_ORIGIN\_ANNOTATION warning se chinaItaly
- **`annotations.py`**: `extract_origin_annotation(layout_text)` → `OriginAnnotation(raw, declared, possible_other, locator_json)`. Detecta padrão chinaItaly (glued), "china Italy" (space), "Italy" (clean).
- **`reconciler.py`**: `reconcile_document_set(db, set_id)` → `list[ReconciliationIssue]`. Verifica: REF\_NUMBER\_MISMATCH (ERROR), FATTURA\_DOGANALE\_TOTAL\_MISMATCH (ERROR), NET\_WEIGHT\_MISMATCH (WARNING), CARTON\_PALLET\_COUNT\_MISMATCH (WARNING), QTY\_PL\_DOGANALE\_MISMATCH (WARNING), AMBIGUITY\_GROUPED\_VS\_DOGANALE (WARNING), PRINT\_DECL\_INVOICE\_REF\_MISMATCH (WARNING), ORIGIN\_ANNOTATION\_MISMATCH (WARNING). PL Grouped contribui apenas WARNING (nunca ERROR).
- **`dossier_commands.py`**: `preview_dossier()` (read-only), `reconcile_and_persist()`, `commit_pl_detail()` (cria Shipment PLANNED via `logistics.create_shipment`), `commit_doganale()` (cria ImportProcess DRAFT via `customs.create_import_process`). Idempotência por `operation_key + payload_fingerprint`.
- **`staging_queries.list_documents_for_set()`**: nova query que lista documentos de um set via join em IngestionDocumentSetMember.
- **Schemas I5**: `DossierCommitIn`, `DossierPreviewOut`, `DossierPreviewItemOut`, `ReconciliationIssueOut` em `schemas.py`.
- **Routes I5** (4 endpoints):
  - `GET /api/ingestion/document-sets/{id}/preview-dossier`
  - `POST /api/ingestion/documents/{id}/commit-pl-detail` (requer `logistics:write`)
  - `POST /api/ingestion/documents/{id}/commit-doganale` (requer `customs:write`)
  - `POST /api/ingestion/document-sets/{id}/reconcile`
- **module_graph**: `logistics` e `customs` adicionados a `ingestion` ALLOWED\_DEPS; `dossier_commands` e `reconciler` adicionados ao `INTERNAL_SUFFIXES`

### Gates

| Gate | Resultado |
|---|---|
| pytest I5 (56 tests) | **56 passed** |
| pytest architecture (6 tests) | **6 passed** |
| PL Grouped AMBIGUITY\_\* = WARNING (nunca ERROR) | PASS |
| Y-codes = coleção JSON (sem fixed column) | PASS |
| annotations.py — chinaItaly glued detectado | PASS |
| reconciler — cross-doc issues incluem PL Grouped como WARNING | PASS |
| dossier preview sem escrita owners | PASS |
| module_graph logistics+customs em ingestion | PASS |
| No V1 imports em qualquer arquivo I5 | PASS |
| PL Grouped `is_sot=false` no IR | PASS |
| PrintDeclaration `y_codes_collection_json` no IR | PASS |

### Arquivos principais

- `v2/app/ingestion/adapters/packing_list_detail_v1.py` (novo)
- `v2/app/ingestion/adapters/packing_list_grouped_v1.py` (novo)
- `v2/app/ingestion/adapters/fattura_doganale_v1.py` (novo)
- `v2/app/ingestion/adapters/print_declaration_v1.py` (novo)
- `v2/app/ingestion/annotations.py` (novo)
- `v2/app/ingestion/reconciler.py` (novo)
- `v2/app/ingestion/dossier_commands.py` (novo)
- `v2/app/ingestion/staging_queries.py` (+ `list_documents_for_set`)
- `v2/app/ingestion/schemas.py` (+ I5 schemas)
- `v2/app/ingestion/routes.py` (+ 4 endpoints I5)
- `v2/app/foundation/module_graph.py` (logistics + customs em ingestion; dossier_commands + reconciler em INTERNAL_SUFFIXES)
- `v2/tests/test_ingestion_i5.py` (56 testes)

### Pendências → I6

- FE: painel de dossier view (preview + commit PL Detail / Doganale via UI)
- I6: Numerário — Solicitação de Numerário ingestion

---

## I6 — Numerário multi-owner: Solicitação de Numerário

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Alembic | **018** (sem nova migration — reutiliza ledger I3/I4/I5) |
| Module graph | `ingestion → {audit, documents, orders, catalog, billing, logistics, customs}` (sem alteração) |
| Pytest I6 | **62 passed** |
| Pytest arch | **6 passed** |
| Regras hard preservadas | NEVER auto-confirm FundingRequest; NEVER create Payment; NEVER liquidate CUSTOMS_FUNDING; sem cross-owner rollback |

### Hipóteses

| Hipótese | Veredito |
|---|---|
| pypdf extrai campos suficientes (Solicitacao_Numerario.pdf) | **CONFIRMADA** — layout mode; header, trade, expense lines, payee |
| S/REFERÊNCIA contém múltiplos invoice refs (multi-owner) | **CONFIRMADA** — 181/202/203/244/245/246 extraídos como lista |
| customs.public tem API completa para FundingRequest | **CONFIRMADA** — create_funding_request + replace_value/tax/expense_lines |
| Payee pode ser reutilizado por CNPJ (idempotência cross-run) | **CONFIRMADA** — list_payees search antes de create |
| PARTIAL explícito quando algum processo falha | **CONFIRMADA** — succeeded ≥ 1 e failed ≥ 1 → PARTIAL |
| UNKNOWN registrado para ops não executadas após falha upstream | **CONFIRMADA** — replace_* ops recebem UNKNOWN quando create_funding_request falha |
| Sem compensação cross-owner (sem rollback de FundingRequests já criados) | **CONFIRMADA** — por design; rollback não está na API pública |

### Entregas

- **Adapter** `solicitacao_numerario_v1`: pypdf layout mode + fallback default; extrai header (datas, refs, exporter, payee), trade amounts (FOB/freight/CIF com moeda estrangeira + R$ + taxa FX), linhas de despesa/imposto (categoria: tax | expense), payee (BECHTRANS: CNPJ + bank + PIX)
- **`numerario_commit_commands.py`**: `preview_numerario()` (read-only) + `commit_numerario()` (multi-owner); idempotência por `operation_key + fingerprint(doc_id, sorted(process_ids))`; per-op result no ledger; PARTIAL/UNKNOWN explícitos; NEVER confirm; NEVER Payment
- **Schemas I6**: `NumerarioCommitIn`, `NumerarioPreviewOut`, `NumerarioPreviewOpOut`, `NumerarioOpResultOut`, `NumerarioCommitResultOut` em `schemas.py`
- **Routes I6** (3 endpoints):
  - `POST /api/ingestion/occurrences/{id}/run-adapter-numerario`
  - `GET /api/ingestion/documents/{id}/preview-numerario?process_ids=...`
  - `POST /api/ingestion/documents/{id}/commit-numerario` (requer `ingestion:commit` + `customs:write`)
- **`module_graph.py`**: `.numerario_commit_commands` e `.fattura_commit_commands` adicionados a `INTERNAL_SUFFIXES`
- **FE minimal**: `NumerarioCommitPanel.tsx` — inputs de process_ids; preview; commit; per-op result table com PARTIAL/UNKNOWN explícitos; aviso "NUNCA auto-confirma"
- **OpenAPI**: regenerado; drift PASS; tsc PASS

### Gates

| Gate | Resultado |
|---|---|
| pytest I6 (62 tests) | **62 passed** |
| pytest architecture (6 tests) | **6 passed** |
| NEVER auto-confirm FundingRequest | PASS (test + source check) |
| NEVER create Payment | PASS (test + source check) |
| NEVER cross-owner rollback | PASS (by design; PARTIAL é o estado explícito) |
| PARTIAL/UNKNOWN explícitos | PASS |
| Idempotência mesma op_key+fingerprint | PASS |
| 409 para op_key+fingerprint divergente | PASS |
| Payee reutilizado por CNPJ | PASS |
| Owner unavailable → PARTIAL | PASS |
| Timeout-after-commit → PARTIAL | PASS |
| module_graph INTERNAL_SUFFIXES | PASS |
| OpenAPI drift | PASS |
| tsc --noEmit | PASS |
| Sem V1 imports | PASS |

### Arquivos principais

- `v2/app/ingestion/adapters/solicitacao_numerario_v1.py` (novo)
- `v2/app/ingestion/numerario_commit_commands.py` (novo)
- `v2/app/ingestion/schemas.py` (+ I6 schemas)
- `v2/app/ingestion/routes.py` (+ 3 endpoints I6)
- `v2/app/foundation/module_graph.py` (+ .numerario_commit_commands, .fattura_commit_commands em INTERNAL_SUFFIXES)
- `v2/frontend/src/features/ingestion/NumerarioCommitPanel.tsx` (novo)
- `v2/frontend/src/features/ingestion/ingestionApi.ts` (+ I6 funções)
- `v2/frontend/src/features/ingestion/IngestionWorkspacePage.tsx` (NumerarioCommitPanel integrado)
- `v2/frontend/src/api/generated/` (OpenAPI regenerado)
- `v2/tests/test_ingestion_i6.py` (62 testes)

### Pendências → I7

- I7: XLSX (ordine758/759) + F328 adapters + métricas + E2E completo

---

## DOC_DELTA (pós-I7 / campanha J#3 DONE)

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (0.5.74); docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md (I7 final); docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; v2/alembic/versions/019_ingestion_metrics_events.py (novo); v2/app/ingestion/metrics_models.py (novo); v2/app/ingestion/metrics_commands.py (novo); v2/app/ingestion/adapters/ordine_heroes_xlsx_v1.py (novo); v2/app/ingestion/xlsx_commit_commands.py (novo); v2/app/ingestion/schemas.py; v2/app/ingestion/routes.py; v2/app/foundation/module_graph.py; v2/tests/conftest.py; v2/tests/test_ingestion_i7.py (novo); v2/tests/test_ingestion_i0_arch.py (atualizado); v2/frontend/src/api/generated/ (OpenAPI regenerado)
- Evidence: docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md (seção I7)
- Roadmap status: 0.5.74 — I7 DONE; J#3 campanha I1→I7 DONE; próxima = J#6 Costing
- Next TODO: J#6 Costing / Reconciliation
- Return to advisor: docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md
```
