# J3 — Aceite operacional da ingestão pela UI

| Campo | Valor |
|---|---|
| Data | 2026-08-05 |
| Método | Playwright (UIV) + **teste manual operador** (Vite `:5174` → API) |
| Roadmap | **0.5.76** |
| Plano | `j3-rux_operational_ux_6992440c.plan.md` |
| Veredito UIV | **REJECTED** |
| Campanha corretiva | **J3-RUX** IN_PROGRESS |

---

## 0. Downgrade UIV → REJECTED (RUX-0)

O veredito **ACCEPTED_WITH_MINOR_BACKLOG** (2026-08-04, E2E `@8082`) foi **refutado** pelo teste manual do operador (PDF cinza/`getOrInsertComputed`, matching SKU→fornecedor, `can_commit`+`skip_order`, catálogo vazio sem Criar, parede IR).

**Regra G6:** nenhum `ACCEPTED*` de UI vale sem validação manual no runtime do operador + screenshot + versão de browser.

Baseline G4: [`rux-g4-render/Ordine_589-1.png`](rux-g4-render/Ordine_589-1.png) — números OK; descrições fragmentadas = bug texto.

Histórico UIV abaixo é arquivo; **não** constitui aceite vigente.

---

## 1. Estado anterior → atual (histórico UIV)

| Antes (UIV-0) | Depois |
|---|---|
| Fila sem upload; empty state apontava seed API | Intake com DnD/multi-upload, classify, run-adapter, abrir IR |
| Adapters dossiê sem HTTP | Registry tipado `GET /adapters` + `POST …/classify` + `POST …/run-adapter` body |
| Review parcial na UI | Campos/seções/linhas (+add/remove)/issues/READY/lock + matching catalog |
| Locator iframe aproximado | PDF.js canvas + highlight; fallback iframe com aviso |
| Sem Dossier/XLSX/Fattura estruturada | Painéis dedicados |
| Zero E2E browser J3 | `e2e/j3-uiv-acceptance.spec.ts` PASS |

Screenshots: `docs/v2/etapa-j3/screenshots/uiv/before/` e `…/after/`.

---

## 2. Matriz de hipóteses (H-UIV)

| ID | Hipótese | Resultado |
|---|---|---|
| H1 | Operador não sobe IR só pela UI | **REFUTED** — intake + adapter criam IR |
| H2 | Dossiê adapters só library | **REFUTED** — registry HTTP |
| H3 | Matching só texto de issue | **PARTIAL→FIXED** — MatchingPanel + catalog search/vínculo |
| H4 | Locator não determinístico (iframe) | **MITIGATED** — PDF.js; fallback documentado |
| H5 | Jornadas finais dependem de seed de ingestão | **REFUTED** — E2E só seed de owners/catalog |
| H6 | XLSX sem painel | **REFUTED** — XlsxCommitPanel |
| H7 | openpyxl ausente quebrava XLSX em runtime | **FIXED** — adicionado a `requirements.txt` |

---

## 3. Checkpoints

| CP | Status | Notas |
|---|---|---|
| UIV-0 Baseline | DONE | before shot + gaps confirmados |
| UIV-1 Intake/classify/registry | DONE | B-UIV-01/02/04 |
| UIV-2 Workspace/PDF/matching/rows | DONE | B-UIV-06…09 |
| UIV-3 Ordine+Fattura | DONE | shots A/B; commit Ordine |
| UIV-4 Dossiê | DONE | DossierPanel + PL adapter |
| UIV-5 Numerário+XLSX | DONE | shots D/E; openpyxl |
| UIV-6 RBAC/hardening | PARTIAL | admin exercitado; matriz completa de papéis = backlog |
| UIV-7 Aceite | DONE | Playwright PASS; pytest registry; OpenAPI drift OK |

---

## 4. BLOCKERs

| ID | Status |
|---|---|
| B-UIV-01 upload UI | **CLOSED** |
| B-UIV-02 run-adapter/classify UI | **CLOSED** |
| B-UIV-03 dossiê UI | **CLOSED** (operacional mínimo; comparação visual rica = backlog) |
| B-UIV-04 HTTP adapters dossiê | **CLOSED** (registry) |
| B-UIV-05 XLSX UI | **CLOSED** |
| B-UIV-06 revisão estrutural | **CLOSED** |
| B-UIV-07 matching operacional | **CLOSED** (vínculo/busca/pendente; create product via catalog se autorizado) |
| B-UIV-08 locator confiável | **CLOSED** com PDF.js (fallback iframe = MINOR) |
| B-UIV-09 persistência revisão | **CLOSED** (version conflict 409 explícito) |

Nenhum BLOCKER aberto → elegível a ACCEPTED / ACCEPTED_WITH_MINOR_BACKLOG.

---

## 5. Jornadas A–E (só UI de ingestão)

API permitida: reset `epic_v2_test`, login seed, Supplier/Products/Order CONFIRMED.  
Proibido: seed de Batch/IR/review/commit — **não usado**.

| Jornada | Evidência | Resultado |
|---|---|---|
| A Ordine 589 | `uiv-a-*.png` | PASS (intake→workspace→commit) |
| B Fattura 202 | `uiv-b-fattura-workspace.png` | PASS (estruturado + policy panel) |
| C Dossiê PL | `uiv-c-dossier-panel.png` | PASS (painel conjunto) |
| D Numerário | `uiv-d-numerario.png` | PASS (copy sem Payment) |
| E XLSX 758 | `uiv-e-xlsx.png` | PASS |

Suite: `npm run e2e:j3-uiv` → **PASS** (log `docs/v2/etapa-j3/logs/j3-uiv-e2e.txt`).

---

## 6. Permissões

| Papel | Exercício nesta campanha |
|---|---|
| admin | E2E completo |
| comprador / aduana / estoque / sem acesso | **BACKLOG** — matriz formal UIV-6 estendida |

Backend permanece autoridade; dual-auth nos commits preservado.

---

## 7. Backlog nomeado (MINOR / BACKLOG)

1. Matriz RBAC completa (comprador/aduana/estoque/bundles) em Playwright dedicado.  
2. Dossiê: comparação cruzada campo-a-campo mais rica (NCM/pesos/pallets) além de issues do reconciler.  
3. Métricas admin UI (`/metrics`) — BACKLOG permitido pelo plano.  
4. Remover documento de DocumentSet via UI (API de remove member ainda limitada).  
5. Fallback iframe do PDF quando PDF.js falha — aviso explícito; preferir sempre canvas.  
6. E2E: probe de porta stale adicionado em `e2e.mjs` (hardening operacional).

---

## 8. Gates técnicos

| Gate | Resultado |
|---|---|
| Playwright J3-UIV | PASS |
| pytest `test_ingestion_uiv_registry` + xlsx upload run | PASS |
| Vitest ingestion | PASS (5) |
| `check:api-drift` | PASS |
| Architecture boundaries | PASS (rodado na campanha) |
| Owners enfraquecidos | Não |

---

## 9. Veredito

**REJECTED** (UIV) — supersedido por campanha **J3-RUX**.

- E2E A–E em 8082/dist mascarou falha no runtime operador (5174→8081 + PDF.js modern).  
- J#6 **não** liberado.  
- Aceite operacional só fecha em **RUX-5** com regra G6.

### 9.1 J3-RUX — estado pós-implementação (2026-08-05)

| Item | Status |
|---|---|
| RUX-0…RUX-4 | **DONE** (código + docs) |
| Gates técnicos | pytest i3+i4 **54 passed**; frontend build PASS; vitest **81 passed**; pdfjs **legacy** no bundle |
| Veredito ACCEPTED* | **PENDENTE** — exige validação manual G6 (runtime operador + screenshot + browser) |
| J#6 | **adiado** |

Mudanças materiais RUX: viewer legacy; math Heroes 2 camadas; unsqueeze layout-scoped; `can_commit`/`readiness_derived`; create supplier/product via intent+preview; matching tipado; sem botão Marcar READY; Descartar/Bloquear.

---

## 10. Validação manual do advisor

> Preparado em **2026-08-05**. Ambiente: `http://127.0.0.1:8082` · banco `epic_v2_test` · Alembic **019**.  
> **Veredito automático da campanha (seção 9) NÃO é alterado aqui** — o advisor confirma após executar A–F.  
> Seed script: `v2/scripts/prepare_j3_uiv_advisor.py` (somente `epic_v2_test`).

### 10.1 Ambiente e logins

| Item | Valor |
|---|---|
| URL | `http://127.0.0.1:8082` |
| Banco | `postgresql://postgres@localhost:5433/epic_v2_test` |
| Ops (não usar neste teste) | `:8081` / `epic_v2` |
| Admin | `admin@epic.com.br` / `admin123` |
| Senha dos usuários UIV | `advisor123` |
| Order CONFIRMED seed | `ORD-UIV-ADVISOR-202` (supplier Heroe's; produtos `I.V. 1` / `I.V. 2`) |

| Login | Papel / uso |
|---|---|
| `comprador@epic.com.br` | upload/review; **sem** `ingestion:commit` |
| `orders-commit@epic.com.br` | commit Ordine/XLSX |
| `billing-commit@epic.com.br` | commit Fattura |
| `logistics-commit@epic.com.br` | commit Packing List |
| `customs-commit@epic.com.br` | commit Doganale/Numerário |
| `noaccess@epic.com.br` | sem `ingestion:*` |

### 10.2 Fixtures (ordem A→F)

| Teste | Arquivos |
|---|---|
| A | `v2/tests/fixtures/ingestion/corpus_589/Ordine_589.pdf` |
| B | `v2/tests/fixtures/ingestion/corpus_202/Fattura_202.pdf` |
| C | `…/corpus_202/Fattura_202.pdf`, `PackingList_202.pdf`, `PackingListGrouped_202.pdf`, `FatturaDoganale_202.pdf`, `PrintDeclaration_202.pdf` |
| D | `…/corpus_202/Solicitacao_Numerario.pdf` |
| E | `…/xlsx/ordine758.xlsx` ou `ordine759.xlsx` |
| F | mesmos fluxos com logins da tabela 10.1 |

### 10.3 Resultados (preencher pelo advisor)

| Teste | Resultado | Observação | Screenshot | Defeito | Severidade |
|---|---|---|---|---|---|
| A — Ordine 589 | **não executado** | | | | |
| B — Fattura 202 | **não executado** | | | | |
| C — Dossiê 202 completo | **não executado** | | | | |
| D — Numerário | **não executado** | | | | |
| E — XLSX | **não executado** | | | | |
| F — Permissões | **não executado** | | | | |

Valores permitidos em Resultado: `PASS` · `FAIL` · `não executado`.

### 10.4 Checklist curto (ordem)

1. **A** — login `comprador@…` → Ingestão → upload Ordine → classify/adapter → workspace (PDF, I.V. sem SKU silencioso, matching, edit/restore, add/remove row, reload) → logout → login `orders-commit@…` → preview → Order DRAFT → deep link → reupload/idempotência.  
2. **B** — Fattura 202 → 7 linhas / 30188 / scadenze → policies A/B/C1 + warning C2 → `billing-commit@…` → Invoice DRAFT → sem Payment/ACCONTO.  
3. **C** — cinco PDFs do corpus 202 no mesmo fluxo → conjunto completo (não só PL) → issues china×Italy → PL Grouped WARNING → commits Logistics/Customs → deep links.  
4. **D** — Numerário → process IDs → FR DRAFT → sem Payment/confirm.  
5. **E** — XLSX → fórmula raw → Order DRAFT → replay.  
6. **F** — permissões por login da tabela 10.1.

Screenshots manuais sugeridos: `docs/v2/etapa-j3/screenshots/uiv/advisor/`.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/J3_UI_RUNTIME_ACCEPTANCE.md
- Evidence: docs/v2/etapa-j3/rux-g4-render/Ordine_589-1.png
- Roadmap status: 0.5.75 → 0.5.76; UIV REJECTED; J3-RUX; J#6 adiado
- Next TODO: J3-RUX (RUX-1…RUX-5)
- Return to advisor: docs/v2/etapa-j3/J3_UI_RUNTIME_ACCEPTANCE.md
```
