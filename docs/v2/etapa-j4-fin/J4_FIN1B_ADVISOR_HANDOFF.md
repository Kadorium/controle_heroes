# J4-FIN FIN-1B — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1B** (cancel adiantamento no painel) |
| Status | **DONE** |
| Data | 2026-08-11 |
| Pytest | **468 passed** (463 + 5) |
| Alembic | **022** (sem migration) |
| Order 31 | CONFIRMED · limpo (0 REGISTERED advances) |
| Asset | `index-CfyfLHV1.js` · Chromium Cursor browser |

## Decisão FxExecution (sem migration)

Ver [`J4_FIN1B_FX_CANCEL_DECISION.md`](J4_FIN1B_FX_CANCEL_DECISION.md).

- Modelo **não tem** `status` em FxExecution → CANCEL tipado exigiria 023.
- **Não apagar.** Ciclo ativo = Payment `REGISTERED`.
- Cancel (painel **e** `/payments/{id}`) emite Audit `fx.realized.void_by_payment_cancel` com EUR/BRL/taxa/pedido/motivo.
- Edit in place: **não** implementado.

## Entregas

- `POST /api/orders/{order_id}/advances/{payment_id}/cancel` (motivo obrigatório)
- UI: botão Cancelar + modal confirmação no `OrderAdvancesPanel`
- Audit payment.cancel + FX void no mesmo caminho de `/payments/{id}/cancel`
- Roteiro G6 atualizado (“Se errar a taxa” → cancel no painel)

## Gates

| # | Resultado |
|---|---|
| 1 | 468 passed · `logs/fin1b-pytest-full.txt` · `test_treasury_fin1b_cancel_advance.py` |
| 2 | Runtime 589: 2 adv → cancel 1 (média 6,399440) → cancel 2 → vazio; FX preservada |
| 3 | Ambiente limpo confirmado (API + UI “Nenhum adiantamento”) |
| 4 | Screenshots cancel button + confirmação |
| 5 | Chromium + dist declarados |

## Próxima

**G6 Ricardo** (adiantamento real 589). Depois FIN-2.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j4-fin/J4_FIN1B_*; J4_FIN1_G6_ROTEIRO.md; ROADMAP_V2_EPIC.md; v2/app/treasury/*; OrderAdvancesPanel.tsx; advanceApi.ts; test_treasury_fin1b_cancel_advance.py
- Evidence: screenshots/fin1b-*; logs/fin1b-pytest-full.txt; J4_FIN1B_FX_CANCEL_DECISION.md
- Roadmap status: 0.5.97 — FIN-1B DONE; próxima G6
- Next TODO: G6 Ricardo adiantamento real 589
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN1B_ADVISOR_HANDOFF.md (+ decisão FX)
```
