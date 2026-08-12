# J3-RUX — RUX-3B-2a (backend Ordine commit → COMMITMENT) — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-3B-2a** — backend commit de ingestão Ordine (sem UI) |
| Status | **DONE** (gates desta fatia) |
| Data | 2026-08-07 |
| Alembic | **021** (inalterado; sem 020) |
| Fora | UI (3B-2b), RUX-3A, mig 020, reextract, RUX-4, J#6 |

---

## WIP na árvore — NÃO desta fatia (C5)

1. UI / CTA cadastrar fornecedor / preview na tela / botão criar pedido / aviso confirm / tela resultado → **3B-2b** (exige auth explícita)
2. Migration **020** isolada em `_wip_isolated_rux3a_rux2rb/` — **não aplicada**
3. reextract rota **501**
4. **Débito RUX-4:** PARTIAL + `uow.commit()` cego em Numerário / XLSX / Dossiê

---

## Registro (não agir) — do aceite 3B 1/2

1. **CHECK `ck_order_items_line_kind_product_id`:** impede que linha `COMMITMENT` receba `product_id` sem mudar `line_kind`. **Intencional.** Quem desenhar reconciliação compromisso↔Fattura precisa saber que essa porta está fechada de propósito.
2. **Unidade (PZ) no snapshot:** confirmada — IR já carrega `unit`; `OrderItem.unit` via `add_item(..., unit=...)`; gate 589 asserta `unit == "PZ"` nas 2 linhas COMMITMENT.

---

## Entregas

### Preview Ordine

Ordem canônica:

`create_supplier` → `store_document` → `create_order` → `add_item(COMMITMENT|PRODUCT)×N` → `link_document`

- Sem Product resolvido → **COMMITMENT** (não `skip_item`)
- Product/`product_id_catalog` resolvido (exceção Q3=B) → **PRODUCT**
- `create_supplier` só com `pending_create_supplier` explícito no IR
- `can_commit`: fornecedor (vinculado **ou** intent) + ≥1 linha com qty + zero ERROR aberto

### Execute commit

- All-or-nothing 2R-b preservado (`.pending` → promote pós DB; falha → discard)
- `create_supplier` **antes** de `store_document` (falha de vínculo sem FS)
- Sem `create_product` a partir de I.V.* / pending
- Snapshot COMMITMENT: `external_code`, `description`, `qty`, **`unit`**, `unit_price`

### create_supplier — dois conflitos 409 (separados)

| Caso | Código | Comportamento |
|---|---|---|
| Ledger já tem `create_supplier` SUCCEEDED | (reuse interno) | Devolve `entity_id`; **não** rechama create |
| Fornecedor já existe (código/nome) e matcher não vinculou | `commit_supplier_link_required` | **409** — pendência humana vincular |

Fingerprint conflict permanece `commit_conflict_fingerprint` (409 distinto).

### Permissão

Commit Ordine: `ingestion:commit` + `orders:write`.  
Se preview inclui `create_supplier`: também **`catalog:write`** (403 se ausente).

---

## Gates provados

| Gate | Evidência |
|---|---|
| 589 catálogo sem Heroes → supplier + Order DRAFT + 2 COMMITMENT (PZ) + Doc + link | `test_rux3b2a_empty_catalog_commit_commitment_with_unit` |
| Reimport: matcher acha fornecedor; sem `create_supplier` | `test_rux3b2a_reimport_matcher_finds_supplier` |
| Falha injetada: zero write / zero órfão / motivo no ledger | `test_rux3b2a_injected_failure_zero_writes` |
| `create_invoice` → "nenhuma linha faturável" | mesmo teste empty (após confirm) |
| 409 vincular | `test_rux3b2a_supplier_exists_link_required_409` |
| pytest completo | **451 passed** — `logs/rux3b2a-pytest-full.txt` |
| Diff goldens | `logs/rux3b2a-golden-diff.md` (+4 testes; sem golden adapter) |

---

## Arquivos relevantes

- `v2/app/ingestion/commit_commands.py` — preview + execute COMMITMENT + create_supplier
- `v2/app/ingestion/routes.py` — `catalog:write` condicional; 409 link
- `v2/app/catalog/public.py` / `queries.py` — `get_supplier_by_code`, `SupplierCodeDuplicate` público
- `v2/tests/test_ingestion_rux3b2a_commitment_commit.py`

---

## Riscos / pendências

- Intent `pending_create_supplier` continua sendo setado via correção de campo (UI = 3B-2b).
- Reconciliação COMMITMENT↔Fattura **não** aberta nesta fatia (CHECK fecha atribuição de `product_id` sem mudar kind).

---

## Próxima etapa lógica

**RUX-3B-2b** (UI jornada) — **exige autorização explícita**.  
Não iniciar 3A / 020 / RUX-4 / J#6 sem auth.

## Recomendação

Aceitar 3B-2a; autorizar 3B-2b quando quiser CTA/preview/confirm na tela.

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_3B_2A_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md; .cursor/plans/j3-rux_operational_ux_6992440c.plan.md
- Evidence: docs/v2/etapa-j3/logs/rux3b2a-pytest-full.txt; docs/v2/etapa-j3/logs/rux3b2a-golden-diff.md
- Roadmap status: 0.5.84 → 0.5.85 (RUX-3B-2a DONE)
- Next TODO: Auth explícita RUX-3B-2b (UI) ou PARAR
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3B_2A_ADVISOR_HANDOFF.md
```
