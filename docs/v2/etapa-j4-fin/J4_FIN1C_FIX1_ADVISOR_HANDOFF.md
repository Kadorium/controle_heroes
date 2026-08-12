# J4-FIN FIN-1C-FIX-1 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1C-FIX-1** |
| Status | **DONE** |
| Runtime | `:8081` / `epic_v2` / Alembic **022** |
| Pytest | **471 passed** (ref. 468 + 3) — [`logs/fin1c-fix1-pytest-full.txt`](logs/fin1c-fix1-pytest-full.txt) |
| Chromium | Cursor browser (Chromium) |
| Asset | `v2/frontend/dist` · `index-CZIF-k93.js` |

---

## Entregas (F1–F5)

| ID | O quê | Como |
|---|---|---|
| **F1** | Lista cockpit = pedido | `order_cockpit` lista `list_payments(order_id=…)`; candidatos permanecem supplier+currency com notice/títulos distintos |
| **F2** | CANCELLED honesto | Badge `Cancelado` + residual `—` (`amount_unallocated=null`) |
| **F3** | KPI crédito | `Pago (alocado)` = Σ alocações em Payable; `Adiantado (crédito)` = residual REGISTERED com `order_id` |
| **F4** | Foco Motivo | `ConfirmationModal.initialFocusSelector` (padrão global inalterado); painel passa `#adv-cancel-reason` |
| **F5** | Limpeza (último) | Payments 10–16 + FxExecutions removidos; Order 31 CONFIRMED + 2 linhas + PDF preservados |

### F3 — investigação KPI (antes da mudança)

- `kpis.paid` / `treasury.paid_via_allocations` = Σ `(amount−balance)` dos Payables do pedido (só alocação).
- `kpis.invoiced` / `kpis.balance` = totais de obrigações (0 sem Fattura) — **honestos**; sem outro KPI mentindo no mesmo sentido.
- Sem Fattura: Faturado=0 e Saldo=0 corretos; o falso era só o rótulo único “Pago” com dinheiro já saído.

---

## Gates

| # | Gate | Resultado |
|---|---|---|
| 1 | pytest completo | **471 passed** |
| 2 | Cockpit lista order-scoped + CANCELLED badge/`—` | Screenshot + API tests F1/F2 |
| 3 | KPI dois números | `Pago (alocado) EUR 0,00` · `Adiantado (crédito) EUR 25.000,00` (pré-limpeza) |
| 4 | Modal foco Motivo (teclado) | Snapshot `[focused]` em Motivo; digitou sem clicar no campo; Escape fecha |
| 5 | Ambiente limpo | SQL 0 payments order_id=31; UI `Nenhum adiantamento registrado` |
| 6 | Chromium + dist | Declarado |

## Screenshots

- [`screenshots/fin1c-fix1-cockpit-kpis-payments.png`](screenshots/fin1c-fix1-cockpit-kpis-payments.png)
- [`screenshots/fin1c-fix1-modal-focus-motivo.png`](screenshots/fin1c-fix1-modal-focus-motivo.png)
- [`screenshots/fin1c-fix1-advances-empty.png`](screenshots/fin1c-fix1-advances-empty.png)

## Fora (FIX-2)

Vocab N2, atrito N3, sugestão BRL A4.

## Próxima

**G6 Ricardo** — [`J4_FIN1_G6_ROTEIRO.md`](J4_FIN1_G6_ROTEIRO.md) (atualizado: passo Cockpit + foco Motivo).

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j4-fin/J4_FIN1C_FIX1_ADVISOR_HANDOFF.md; docs/v2/etapa-j4-fin/J4_FIN1_G6_ROTEIRO.md; docs/README.md
- Evidence: docs/v2/etapa-j4-fin/logs/fin1c-fix1-pytest-full.txt; screenshots/fin1c-fix1-*; logs/fin1c_fix1_clean_order31.py
- Roadmap status: 0.5.98 → 0.5.99 (FIN-1C-FIX-1 DONE; próxima = G6 Ricardo)
- Next TODO: G6 Ricardo (adiantamento real 589)
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN1C_FIX1_ADVISOR_HANDOFF.md
```
