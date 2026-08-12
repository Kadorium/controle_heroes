# J4-FIN FIN-1 — UI / runtime verification

| Campo | Valor |
|---|---|
| Data | 2026-08-10 |
| Runtime | `:8081` / `epic_v2` |
| Alembic | **022** · `schema_ok=true` · expected=022 |
| Chromium | Cursor browser (Chromium) |
| Asset | `v2/frontend/dist` (build Vite `index-CPUOKEyx.js`) |

## Gates

| # | Gate | Resultado |
|---|---|---|
| 1 | pytest completo | **463 passed** — `logs/fin1-pytest-full.txt` |
| 2 | Migration + health | Alembic **022**; `schema_ok=true` |
| 3 | Adiantamento 589 EUR+taxa+BRL + datas ≠ | Payment **10**: EUR 1000 @ 6.20 → BRL 6200; pay 15/06 ≠ FX 10/06 |
| 4 | 2º adiantamento + consolidado | Payment **11**: EUR 500 + BRL 3199.72 (taxa derivada 6.399440); cons EUR **1500** / BRL **9399.72** / média **6,266480** |
| 5 | `/payables?order_id=31` → ZERO | Screenshot `screenshots/fin1-payables-order-31-zero.png` |
| 6 | PDF câmbio + manual sem PDF | pytest `test_fin1_advance_with_fx_pdf` + `test_fin1_advance_manual_without_pdf` |
| 7 | Chromium + dist | Declarado acima |

## Screenshots

- `screenshots/fin1-order-589-advances-panel.png` — painel crédito + consolidado + 2 parcelas
- `screenshots/fin1-payables-order-31-zero.png` — filtro Pedido 31 → 0 títulos

## Nota

Payments 10/11 no 589 são **demo de gate** (idempotency `fin1-gate-a*`). G6 Ricardo: valores reais do extrato — ver `J4_FIN1_G6_ROTEIRO.md`.
