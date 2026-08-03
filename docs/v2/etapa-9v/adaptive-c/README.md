# Adaptive — Onda C filas SCR-003 / 006 / 010

**Status:** DONE técnico  
**Data:** 2026-07-30  
**SCR-008:** `APPROVED_FOR_PROGRESSION` (não `VISUAL_ACCEPTED`)  
**E2E:** **17 passed** (Horizon A 15 + adaptive-B + adaptive-C) @ `epic_v2_test`:8082  

## Evidências

- Log: [`grupo-C-e2e.txt`](grupo-C-e2e.txt)
- Screenshots: `screenshots/scr-{003,006,010}-*-{1024,1366,1440,1920}.png`

## Escopo entregue

| SCR | Página | Colunas |
|---|---|---|
| 003 | `OrdersListPage` | `createOrdersQueueColumns(ctx)` + `useMemo` |
| 006 | `InvoicesListPage` | `INVOICES_QUEUE_COLUMNS` module-scope |
| 010 | `PaymentsListPage` | `PAYMENTS_QUEUE_COLUMNS` (C-010; sem Moeda; Abrir = RowAction) |

- FilterBar adaptive: só `primary` (+ `activeFilters` quando ≠ default); **sem** “Mais filtros” vazio
- `PayablesListPage` continua `children` (não migrado)
- `row-highlight` residual: **deferido** (só visual; OT não alterado)

## Gates

| Gate | Resultado |
|---|---|
| Unit Vitest | 56 passed |
| `test:e2e-guard` | 4 passed |
| tsc + build | OK |
| E2E canônico | **17 passed** |

## Bundle

| Momento | JS | CSS |
|---|---|---|
| Antes C1 | 281447 B (`index-B9kHSdt4.js`) | 22735 B |
| Depois C3 | 282648 B (`index-DhQFeZmv.js`) | 22735 B |
| Delta | **+1201 B (~+0,4%)** | 0 |
| Deps novas | **0** | |

## Fora de escopo (inalterado)

Onda D · Inc-6 · backend · hub FX · polish · `VISUAL_ACCEPTED` · Order-to-Pay DONE
