# J4-FIN — Advisor Handoff (FIN-0 + FIN-1)

| Campo | Valor |
|---|---|
| Campanha | **J4-FIN** (≠ Logística J#4) |
| Status | FIN-0 **DONE** · FIN-1 **DONE** |
| Data | 2026-08-10 |
| Modelo ACCONTO | **Opção B** — Payment + `order_id` + FxExecution |
| Order 589 | id **31** — só Payments novos; sem Payable de compromisso |
| Pytest | **463 passed** |
| Alembic | **022** `payments.order_id` · health `schema_ok` |

## Decisões

- Opção B ratificada; Fattura no 589 depois; FIN-3 = pedido amostra PRODUCT.
- Migration `payments.order_id` + reuso `FxExecution` (sem colunas BRL em Payment).
- N Payments por Order; consolidado EUR / BRL (soma) / câmbio médio ponderado.
- Adiantamento **não** entra em `/payables` (crédito).
- Arredondamento: EUR+BRL = SoT → taxa derivada; EUR+taxa → BRL derivado (sobrescrevível).

## Débitos nomeados (não consertados)

| ID | Nota |
|---|---|
| `FATTURA_LINE_PARSE_ORPHAN_GAP` | pré-FIN-3 |
| `PAYABLE_PERCENT_RECALC` | **BLOCKER gate FIN-3** |
| `FATTURA_IBAN_NOT_EXTRACTED` | pré-FIN-3 |
| Doganale NCM/peso | valor J#6 |
| **J#5-REC** | campanha (ex-FIN-4) |

## FIN-1 entregue

- Alembic **022** `payments.order_id`
- API: `GET/POST /api/orders/{id}/advances` (+ with-document)
- UI: `OrderAdvancesPanel` no comercial
- Gates: `J4_FIN1_UI_VERIFICATION.md` + pytest full
- Roteiro G6: `J4_FIN1_G6_ROTEIRO.md`

## Próxima

Aceite G6 Ricardo (adiantamento real 589). Depois **FIN-2**. Sem 3A/020/J#6/J#5-REC.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j4-fin/*; ROADMAP_V2_EPIC.md (0.5.96); docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; v2/app/treasury/*; v2/alembic/versions/022_*; v2/frontend/.../OrderAdvancesPanel.tsx
- Evidence: docs/v2/etapa-j4-fin/J4_FIN1_UI_VERIFICATION.md; screenshots/; logs/fin1-pytest-full.txt; v2/tests/test_treasury_fin1_advance.py
- Roadmap status: 0.5.96 — J3 Ordine CONCLUÍDA; J4-FIN FIN-1 DONE
- Next TODO: G6 Ricardo; depois FIN-2
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN_PLAN_ADVISOR_HANDOFF.md (+ J4_FIN1_UI_VERIFICATION.md como evidência UI)
```
