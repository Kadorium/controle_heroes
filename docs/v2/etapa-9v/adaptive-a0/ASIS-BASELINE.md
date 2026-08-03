# Adaptive A0 — AS-IS + baseline validation

**Date:** 2026-07-30 · sincronizado no fechamento do piloto (§M.26)

## Checklist AS-IS

1. **C-001…C-021 foram executadas?** CONFIRMADO (parcial só onde GAP/POLISH):
   - C-001…C-004, C-006…C-011, C-015…C-016, C-019, C-021: presentes no código
   - C-005: GAP intencional (sem chip MISSING_FX)
   - C-012…014: mini-tables→OT onde tocados na campanha
   - C-017 sticky condicional / C-018 links DS / C-020 drawer CSS: polish residual

2. **ApQueuePage pós-campanha?** SIM — “Não canceladas”; due via `due_*`; Saldo default `OPEN_BALANCE`; Select fornecedor; KPIs wired; colunas declarativas (`AP_QUEUE_COLUMNS`).

3. **Correções ainda ausentes?** C-005 (GAP); polish C-017/C-018/C-020 parciais.

4. **Ajustes ao plano pelo AS-IS?** Nenhum.

## Narrativa factual da baseline E2E

| # | Evento | Fato |
|---|---|---|
| 1 | Baseline histórico §M.23 | `npm run e2e` → **15 passed / 0 failed**; **sem** patches naquele momento |
| 2 | Descoberta | Uvicorn serve `frontend/dist` **sem** rebuild no script → artefato **stale** vs source pós C-010 |
| 3 | Rebuild | `npm run build` passou a ser pré-requisito (depois fixado em `e2e.mjs`) |
| 4 | Patches legítimos | **(A)** C-010 Abrir/`RowAction`; **(C)** locator do fornecedor no detalhe de pagamento (mais estrito) |
| 5 | Baseline reproduzido | Horizon A **15p** pós-rebuild+patches |
| 6 | Pós-piloto A0+A1+B | E2E **16p** (15 Horizon A + adaptive-B) com build no ciclo; ver §M.24/§M.26 |

**Não afirmar** “0 patches” e “patches A/C” no mesmo estado: “0 patches” aplica-se **somente** ao registro histórico §M.23 (antes da descoberta stale). Após rebuild, houve patches A/C documentados.
