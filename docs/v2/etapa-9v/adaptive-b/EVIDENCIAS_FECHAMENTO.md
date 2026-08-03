# Fechamento técnico — piloto adaptativo SCR-008

**Status:** `PILOTO_READY_FOR_EXTERNAL_REVIEW`  
**Data:** 2026-07-30  
**Onda C:** não iniciada (HARD STOP)

## Evidências

| Artefato | Path |
|---|---|
| Matriz | [`PILOTO_MATRIX.md`](PILOTO_MATRIX.md) |
| E2E log | [`e2e-fechamento-piloto.txt`](e2e-fechamento-piloto.txt) |
| Screenshots | [`screenshots/`](screenshots/) |
| Bundle final | [`bundle-final-sizes.txt`](bundle-final-sizes.txt) |
| ASIS/baseline | [`../adaptive-a0/ASIS-BASELINE.md`](../adaptive-a0/ASIS-BASELINE.md) |
| Guard stale | `v2/frontend/scripts/e2e-stale-guard.test.mjs` (`npm run test:e2e-guard`) |

## Desempenho

| Item | Valor |
|---|---|
| Bundle antes (pré-A0) | `index-*.js` **273724** B |
| Bundle depois (piloto) | `index-*.js` **281020** B (±) |
| Delta | **+7296** B (~**+2,7%**) |
| Deps novas | **0** |
| ResizeObserver | **1** por host OT columns (quando `layoutMode` omitido) |
| Estado por célula | **não** |
| API extra por largura | **não** (0 fetches no resize) |
| Tabela duplicada | **não** |

## Legado

| Item | Destino |
|---|---|
| OT `children` | **Preservado** — Orders, Invoices, Payments, Cockpit, Invoice detail, Payment detail, Create |
| `stickyFirstColumn` | Prop existe; **0** consumidores ativos |
| `.mini-table` | FxPanels + AuditDocumentsBlock (fora do piloto AP) |
| CSS inline AP | **nenhum** |
| Removido no piloto | nada com consumidores externos |

## Gates (fechamento)

- Unit Vitest: 56 passed  
- `test:e2e-guard`: 4 passed  
- tsc + build: OK  
- E2E Horizon A + adaptive-B: **16 passed** @ epic_v2_test:8082 (com build no ciclo)
