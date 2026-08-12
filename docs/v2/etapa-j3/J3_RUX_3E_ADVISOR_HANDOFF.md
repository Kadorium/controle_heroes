# J3-RUX — RUX-3E (pré-aceite Ricardo) — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-3E** |
| Status | **DONE** (gates desta fatia) |
| Data | 2026-08-07 |
| Alembic | **021** (inalterado) |
| Runtime | `http://127.0.0.1:8081` · dist `index-BqBCO7o3.js` · DB `epic_v2` |
| Pytest | **455** (antes 452) |

---

## R1 — Testes (3 comportamentos)

Arquivo novo: `v2/tests/test_ingestion_rux3e.py` (**+3 testes**).

| Teste | Cobre |
|---|---|
| `test_rux3e_delete_without_create_order_and_audit_survives` | DELETE 204; edição campo+linha; **Audit sobrevive** |
| `test_rux3e_delete_blocked_after_create_order` | DELETE 409; REJECTED 409 pós-pedido |
| `test_rux3e_order_code_collision_and_external_ref_stable` | 409 `commit_order_code_exists`+details; `code`≠`external_ref=589` |

Log: `docs/v2/etapa-j3/logs/rux3e-pytest-full.txt` → **455 passed**.

### Audit vs DELETE

- Tabela: `audit_log` (módulo Audit), **separada** do ledger IR (`ingestion_*`).
- `hard_delete_document` remove IR + commit attempts; **grava** `document_hard_deleted` em Audit **antes** de apagar o doc.
- Eventos anteriores (`document_seeded`, review, field_corrected, …) **permanecem** com `entity_id` do doc deletado.
- **Confirmado por teste:** após DELETE, `audit_log` ainda tem os eventos + `document_hard_deleted`.

---

## R2 — `code` ≠ `external_ref` (PRIORITÁRIO)

**Concordância com a hipótese do advisor.** Sem discordância.

| Destino | Fonte |
|---|---|
| `Order.code` | campo IR `order_code` (editável) **ou** fallback = número impresso no PDF |
| `Order.external_ref` | **sempre** `order_number` raw/normalized do PDF — **ignora** `corrected_value` |

UI:
- “Código interno do pedido” → `PUT /documents/{id}/order-code` (não mexe em `order_number`).
- Resumo: “Número do documento” **somente leitura**.

### Consumidores de `order_number` (inventário)

| Consumidor | Uso |
|---|---|
| Adapter Ordine PDF/XLSX | extrai número impresso |
| `commit_commands` (PDF Ordine) | `external_ref` + fallback de code |
| `xlsx_commit_commands` | ainda usa `order_number` como `code` (**fora do escopo** desta fatia; família XLSX) |
| Fattura match | **não** lê IR `order_number`; casa `supplier_id + Order.external_ref` ↔ nº fatura |
| Fingerprint IR | inclui todos os fields (incl. `order_code` se existir) |
| OrdineSummary / workspace | exibe; edição de `order_number` bloqueada no Resumo |

Prova: teste `external_ref_stable` — code `589-RUX3E-B-{id}`, `external_ref=="589"`.

---

## R3 — Doc #12 REJECTED com pedido criado

### Como chegou nesse estado

1. Commit Ordine **SUCCEEDED** (`create_order` → Order **22 / ING-589**).
2. Operador usou **Descartar / excluir** → Cancelar no confirm de exclusão dura → fluxo “só marcar como rejeitada” → `PATCH review-status=REJECTED`.
3. Evidência: `ingestion_review_changes` doc 12: `IN_REVIEW→REJECTED` (`set_review_status`, actor `1`), **depois** do attempt SUCCEEDED.
4. **Não** é transição automática do commit — é caminho UI que permitia REJECTED pós-pedido.

### Correção

- Backend: `REJECTED` **bloqueado** se `create_order` SUCCEEDED (`document_reject_blocked`).
- Commit SUCCEEDED com pedido → `review_status=READY`.
- Fila: status derivado **“Pedido criado”** + coluna **Pedido** (link); DELETE oculto se já criou.
- Display: se DB ainda tiver REJECTED+pedido, API/UI mostram READY / Pedido criado.

Screenshot: `docs/v2/etapa-j3/screenshots/j3-rux-3e-queue-doc12-not-rejected.png`  
(`#12` = Pedido criado · link `ING-589`, **não** Rejeitado).

---

## R4 — Limpeza epic_v2

Script `docs/v2/etapa-j3/scripts/rux3c_reset_ordine_runtime.py` estendido:

- Remove DRAFT ingestão **com linhas**, se **sem Invoice** e **sem shipment_items**.
- Travas: só `epic_v2`; recusa `epic_v2_test`; aborta se CONFIRMADO ou com vínculos.

Executado nesta rodada:

- Orders 22–25 (ING-589 + 589-RUX3D-*) deletados  
- Heroe's deletado  
- Fila IR zerada  

Estado final (consulta):

| Check | Valor |
|---|---|
| `ingestion_documents` | **0** |
| Orders `%589%` / `ING-%` | **[]** |
| Suppliers Heroes | **[]** |
| UI fila | “Nenhuma importação na fila” |

Screenshot limpo: `docs/v2/etapa-j3/screenshots/j3-rux-3e-queue-empty-for-ricardo.png`

---

## Gates

| Gate | Resultado |
|---|---|
| pytest > 452 | **455** (+3 em `test_ingestion_rux3e.py`) |
| external_ref estável com code alterado | teste OK |
| doc com pedido ≠ rejeitado | screenshot #12 |
| ambiente limpo | consulta + screenshot vazio |
| Chromium + asset | `index-BqBCO7o3.js` servido em 8081; health `schema_ok` / alembic **021** |

---

## Pendências / fora de escopo

- Aceite manual Ricardo (**RUX-3C** jornada) — **próximo**
- XLSX commit ainda amarra code=order_number
- RUX-3A / 020 / RUX-4 / J#6 — não iniciar

## Recomendação

Liberar Ricardo para reteste do zero em `http://127.0.0.1:8081/ingestion` (fila vazia, sem Heroes, sem 589).  
Hard refresh se cache antigo. Reiniciar 8081 se o processo não tiver o dist novo.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/J3_RUX_3E_ADVISOR_HANDOFF.md
- Evidence: docs/v2/etapa-j3/screenshots/j3-rux-3e-queue-doc12-not-rejected.png; docs/v2/etapa-j3/screenshots/j3-rux-3e-queue-empty-for-ricardo.png; docs/v2/etapa-j3/logs/rux3e-pytest-full.txt
- Roadmap status: 0.5.89 — RUX-3E DONE; próxima = aceite manual Ricardo (RUX-3C)
- Next TODO: Aceite manual Ricardo da jornada Ordine (RUX-3C)
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3E_ADVISOR_HANDOFF.md
```
