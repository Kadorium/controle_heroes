# J3-RUX — RUX-3B (1/2) migration + guards — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-3B primeira metade** — migration Orders + guards backend |
| Status | **DONE** (gates desta fatia) |
| Data | 2026-08-06 |
| Alembic | **021** (`021_orders_commitment_lines`, down_revision **019**) |
| Fora | UI jornada, aviso visual confirm, RUX-3A, mig 020, reextract, Catalog refs, J#6, 3B-2 |

---

## WIP na árvore — NÃO desta fatia (C5)

1. UI / preview / CTA / aviso visual no confirm (V2-b UI) — **segunda metade 3B**
2. Migration **020** isolada em `_wip_isolated_rux3a_rux2rb/` — **não aplicada**
3. reextract rota **501**
4. Ingestão Ordine ainda **não** cria linhas COMMITMENT no commit (só API Orders pública nesta fatia)
5. **Débito RUX-4:** PARTIAL + `uow.commit()` incondicional ainda vivos em **Numerário / XLSX / Dossiê**

---

## Entregas

### Migration 021

- `order_items.product_id` **nullable**
- `line_kind` NOT NULL (`PRODUCT` \| `COMMITMENT`), default `PRODUCT`
- Backfill: **22** linhas em `epic_v2` → todas `PRODUCT`; **zero** `line_kind` nulo
- `external_code` nullable (código do documento)
- CHECK: PRODUCT ⇔ product_id NOT NULL; COMMITMENT ⇔ product_id NULL
- **Não** reutiliza 020

### Downgrade (honesto)

| Situação | Comportamento |
|---|---|
| Zero `product_id` NULL e zero COMMITMENT | Remove `line_kind`/`external_code`; restaura `product_id` NOT NULL |
| Qualquer `product_id` NULL | **RuntimeError** — não finge reversibilidade |
| Qualquer COMMITMENT | **RuntimeError** |

Provado: insert probe COMMITMENT → `alembic downgrade 019` → recusa explícita; cleanup; permanece em **021**.

### Guards

| Site | Comportamento |
|---|---|
| `_order_response` | `product_id: int \| null` + `line_kind` + `external_code` |
| `add_item` | Aceita `line_kind=COMMITMENT` sem Product; PRODUCT resolve catálogo |
| `confirm_order` | Variante A (≥1 item); Audit `ORDER_CONFIRM_WITH_COMMITMENT` + details |
| `create_invoice` | Só linhas com `product_id`; zero → **"nenhuma linha faturável"**; não inventa Product |
| `replace_items` | Rejeita order_item COMMITMENT |

### C3 drift

`EXPECTED_ALEMBIC_REVISION = "021"`; `assert_schema_revision` OK em `epic_v2`.

### OpenAPI

Regenerado; `client.ts` intacto; schema Orders com nullable + `line_kind`.

### Gate pytest

**447 passed** — `logs/rux3b-pytest-full-run3.txt`  
Diff: `logs/rux3b-golden-diff.md`

---

## Débito conhecido → RUX-4

Numerário, XLSX e Dossiê ainda:

- Emitem **PARTIAL** com a semântica antiga
- Provavelmente ainda chamam `uow.commit()` **incondicional** (defeito corrigido só em Ordine/Fattura no 2R-b)

Registrar para campanha RUX-4 — essas famílias **não** podem herdar o defeito.

---

## Próxima etapa lógica

1. Aceite advisor desta metade.
2. **Segunda metade RUX-3B** (auth explícita): jornada UI Ordine → linhas COMMITMENT no commit de ingestão + aviso visual no confirm.
3. **Não** iniciar 3A / 020 / J#6 / RUX-4 sem auth.

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/J3_RUX_3B_HALF1_ADVISOR_HANDOFF.md; .cursor/plans/j3-rux_operational_ux_6992440c.plan.md
- Evidence: docs/v2/etapa-j3/logs/rux3b-pytest-full-run3.txt; docs/v2/etapa-j3/logs/rux3b-golden-diff.md
- Roadmap status: 0.5.84 — RUX-3B half-1 DONE; alembic 021
- Next TODO: Aceite; auth 3B-2 (UI/jornada) ou PARAR
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3B_HALF1_ADVISOR_HANDOFF.md
```
