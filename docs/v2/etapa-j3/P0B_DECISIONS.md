> **Superseded for advisor reading** by [`J3_P0_ADVISOR_HANDOFF.md`](J3_P0_ADVISOR_HANDOFF.md) (decisões **ratificadas**). Kept as internal evidence of pre-ratification proposals.

# J3-P0-b — Pacote de decisões (recomendações ao advisor)

Cada tema: estado · alternativas · **recomendação** · evidências · impacto · riscos · decisão solicitada.

---

## 1. Agrupamento documental (H-P0-05)

**Estado:** Dossier 202 é real operacionalmente; Blueprint só `IngestionBatch`/`StagingRow`/`AdapterResult`; sem tabela Dossier.

**Alternativas:** (A) entidade `IngestionDossier`; (B) edges/relações File↔File; (C) projeção derivada por business keys; (D) Batch = único contêiner.

**Recomendação: (B)+(C) no I0/I1 — `IngestionDocumentSet` como relação explícita opcional (join table) + projeção por keys; adiar entidade rica até I5 se UI exigir agregado nomeado.** Evita migration Dossier prematura; atende agrupamento funcional.

**Evidências:** corpus 202; plano V1–V7; Blueprint §5.9 mínimo.

**Impacto:** I0 sem tabela Dossier obrigatória; UI “dossiê” pode ser projeção.

**Riscos:** UI pobre se só keys; mitigar com set explícito confirmado pelo operador.

**Decisão advisor:** aceitar join+projeção vs forçar entidade Dossier no I0.

---

## 2. Occurrence, hash, blob, reuso

**Estado:** Documents indexa `file_hash` mas sempre cria novo `document_key`.

**Recomendação:** Occurrence first-class; dedupe físico opcional na quarantine; **mesmo hash ≠ bloquear** nova occurrence; reuso de Document oficial só na promoção com política explícita + ledger.

**Evidências:** `documents/public.py` store; H-REV-03.

**Decisão advisor:** confirmar política de reuso na promote (default: reusar Document se hash idêntico **e** operador não força nova versão).

---

## 3. Promoção quarantine → Documents (H-P0-06)

**Estado:** HTTP Documents = store+link imediato; inadequado para ingestão pré-aprovação.

**Recomendação:** bytes em storage **Ingestion quarantine** até commit aprovado; promote chama `store_document` (+ link na mesma UoW do group); **proibido** link oficial antes. DocumentVersion Blueprint = gap (campos version na row); supersede = follow-up.

**Decisão advisor:** confirmar momento = commit (não no approve parcial de campo).

---

## 4. Retenção / cleanup

**Recomendação:** REJECTED → purge quarantine após TTL curto (ex. 7–30d) + Audit; ABANDONED job; oficial imutável sob Documents. Defaults configuráveis.

**Decisão advisor:** TTL numérico preferido.

---

## 5. Idempotência / extensões públicas (H-P0-07)

**Recomendação:**

| Owner | Garantia I0–I3 sem extensão | Extensão desejável |
|---|---|---|
| Ingestion ledger | **Obrigatório** (operation_key+fingerprint+replay) | — |
| Documents | hash+ledger | find-by-hash / promote API |
| Catalog | unique sku/code + ledger; **409+fingerprint diverge = conflito** | version no response; idempotency_key |
| Orders/Billing/Logistics | natural key + version + ledger | HTTP Idempotency-Key |
| Customs Doganale/Funding | **usar keys nativas** | — |

Não tratar 409→GET como suficiente se payload pode divergir.

**Decisão advisor:** autorizar extensões no escopo J#3 ou follow-up explícito.

---

## 6. Política I4 — Order × Fattura (H-P0-08)

**Estado:** sem Ordine 202; `create_invoice` exige CONFIRMED (`billing/commands.py:90-91`).

**Caminhos:**

| | Descrição | Uso |
|---|---|---|
| **A** | Order CONFIRMED existente → match → Invoice DRAFT | **Caminho normal preferido** |
| **B** | Order DRAFT existente → confirm explícito auditado → Invoice DRAFT | Normal quando pedido já no sistema |
| **C1** | Sem Order → criar Order DRAFT (reconstrução) → Invoice **aguarda** confirm posterior | Preferido se operador não quer confirmar já |
| **C2** | Sem Order → create+confirm na sessão com warning, reason, provenance `FATTURA_RECONSTRUCTION`, preview separado, Audit, perm `orders:write` (+ opcional `ingestion:commit`) | Exceção explícita |

**Recomendação:** **A/B como default; C1 como default sem match; C2 só com ação explícita tipada (não caminho normal).** Nunca Invoice+Order DRAFT; nunca confirm silencioso; nunca Payment; nunca ACCONTO inferido.

**Decisão advisor:** ratificar A/B/C1/C2.

---

## 7. SCR IDs / UI

**Recomendação:** propor ao Blueprint UI/UX (futuro, não agora):

| SCR | Superfície |
|---|---|
| SCR-037 | Fila de ingestão |
| SCR-038 | Workspace conferência (+ viewer) |
| SCR-039 | Preview/commit + ledger result |
| SCR-017 | Triagem SKU (já previsto) integrado ao workspace |

**Decisão advisor:** aceitar IDs ou remapear.

---

## 8. RBAC inicial

**Recomendação (conservadora):**

| Role | Perms |
|---|---|
| admin | read/write/review/commit/reprocess/waive |
| comprador | read/write/review/commit/reprocess (**sem** waive) |
| aduana | read (+ review docs Customs staging se necessário) |
| estoque | nenhuma ingestion |

L-005 permanece aberto; sem wildcard; sem ampliar reporting.

**Decisão advisor:** ratificar baseline.

---

## 9. XLSX

**Recomendação:** manter em **J3-I7** (após vertical PDF). Não checkpoint próprio salvo se advisor priorizar Heroes planilha.

---

## 10. Tooling PDF produção

**Recomendação:** baseline produção = **pypdf** (+ poppler opcional em worker isolado). pdfplumber = tooling análise apenas até ADR de dependência. Annotations via pypdf `/Annots`.

**Decisão advisor:** aceitar baseline pypdf.

---

## 11. Política de annotations

**Recomendação:**

1. Extrair FreeText `/Contents` + Rect como locator.
2. Preferência **por layout versionado** (ex. Doganale/PL Heroes **202**: origin ← annotation).
3. Se content na banda do campo diverge → issue `ANNOTATION_VS_CONTENT_MISMATCH`.
4. **Não** generalizar para layouts sem evidência (F328: content Italy, sem FreeText china).
5. Render/screenshot = QA, não SoT do parser.

**Decisão advisor:** ratificar.

---

## 12. Métricas / thresholds

**Recomendação:** P0 registra hipóteses qualitativas (matrizes 5.5); **calibração numérica só após I3** (Ordine golden + correções humanas). Não inventar % agora.

**Decisão advisor:** aceitar adiamento da calibração.

---

## Hipóteses H-P0 (síntese)

| ID | Veredito |
|---|---|
| H-P0-01 | **CONFIRMADA** — texto digital suficiente; OCR não necessário nos prioritários |
| H-P0-02 | **PARCIAL** — 202 = FreeText china + content Italy; **328 sem FreeText china** |
| H-P0-03 | **CONFIRMADA** — Grouped ambíguo/diferente; não pré-condenar |
| H-P0-04 | **CONFIRMADA** — F181 no ZIP, copiada hash-ok; não fecha DEC |
| H-P0-05 | **CONFIRMADA** necessidade; persistência = recomendação join+projeção |
| H-P0-06 | **CONFIRMADA** — quarantine ≠ Document; promote no commit |
| H-P0-07 | **CONFIRMADA** — ledger necessário; extensões owner desejáveis |
| H-P0-08 | **CONFIRMADA** — política A/B/C1/C2 acima |
