# J3-RUX — RUX-3F-POST-3 ADVISOR HANDOFF

| Campo | Valor |
|---|---|
| Etapa | **RUX-3F-POST-3** |
| Status | **DONE** — BLOCKER V5 fechado (aviso sem bloquear) |
| Data | 2026-08-10 |
| Decisão | Advisor: **WARNING** `MATH_LINE_EDIT_DIVERGENCE`; commit **não** bloqueia |
| epic_v2 Order 31/589 | **não mutados** (screenshot usou IR throwaway `#28`) |

---

## Entrega

### Backend

Em `correct_row` → `sync_math_line_edit_divergence`:
- Após gravar `cells_json`, compara `qty×price` com **`line_total.raw`** (total impresso no PDF; a UI pode recalcular `normalized`).
- Se diverge (> €0,02): cria/atualiza issue `severity=WARNING`, `code=MATH_LINE_EDIT_DIVERGENCE`, mensagem literal pedida.
- Se alinha de novo (revert ou qty coerente): `RESOLVED` automático.
- `MATH_TOTAL_MISMATCH` / `MATH_LINE_TOTAL_MISMATCH` **inalterados** (ERROR).

### UI

`OrdineBeforeCreatePanel`: Notice `tone=warning` com a mensagem (`data-testid=ordine-math-line-edit-divergence`). Botão criar pedido permanece disponível.

### Prova

| Caso | Resultado |
|---|---|
| 1. PATCH qty `99999`, line_total PDF intacto | WARNING OPEN |
| 2. commit | **SUCCEEDED** |
| 3. PATCH qty original | issue **RESOLVED** / some |
| 4. qty coerente com PDF | sem WARNING |

Teste: [`v2/tests/test_ingestion_rux3f_post2_v5.py`](../../v2/tests/test_ingestion_rux3f_post2_v5.py)  
Log casos: [`logs/rux3f-post3-v5-pytest.txt`](logs/rux3f-post3-v5-pytest.txt)

### Suíte

**457 passed** — [`logs/rux3f-post3-pytest-full.txt`](logs/rux3f-post3-pytest-full.txt) (ref. 456 → +1).

### Screenshot

[`screenshots/rux3f/rux3f-post3-math-line-edit-divergence-warning.png`](screenshots/rux3f/rux3f-post3-math-line-edit-divergence-warning.png)  
Runtime `:8081` · asset `index-D22eJxa8.js` · IR `#28` · Notice visível + **Criar pedido em rascunho** ativo.

---

## BLOCKER V5

**FECHADO** — divergência pós-edição deixa de ser silenciosa; correção legítima continua possível.

## Próxima

Decisão advisor: exposição Reporting vs RUX-4. Sem 3A/020/J#6.

```text
DOC_DELTA
- Updated: staging_commands.py; OrdineBeforeCreatePanel.tsx; test_ingestion_rux3f_post2_v5.py; J3_RUX_3F_POST3_ADVISOR_HANDOFF.md; J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md
- Evidence: logs/rux3f-post3-pytest-full.txt; logs/rux3f-post3-v5-pytest.txt; screenshots/rux3f/rux3f-post3-math-line-edit-divergence-warning.png
- Roadmap status: 0.5.94 → 0.5.95 RUX-3F-POST-3 DONE; BLOCKER V5 closed
- Next TODO: decisão Reporting vs RUX-4
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3F_POST3_ADVISOR_HANDOFF.md
```
