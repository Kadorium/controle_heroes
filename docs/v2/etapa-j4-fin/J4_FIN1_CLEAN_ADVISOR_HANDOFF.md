# J4-FIN FIN-1-CLEAN — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1-CLEAN** |
| Status | **DONE** |
| Data | 2026-08-11 |
| Pytest | **463 passed** |
| Order 31 | CONFIRMED · 2 COMMITMENT · documento intacto |

## C1 — Ambiente limpo para G6

Demo Payments **10** e **11** (`fin1-gate-a*`) → `CANCELLED` (`FIN1_CLEAN_DEMO`).
FxExecutions **7** e **8** removidos (órfãos sem alocação).

Consulta:
- `REGISTERED` em order_id=31 → **0**
- `GET /api/orders/31/advances` → count=0 · EUR 0 · BRL 0 · avg=null
- Order 31: `CONFIRMED`, code `589`, 2 itens

UI: painel **“Nenhum adiantamento registrado”** — `screenshots/fin1-clean-order-589-advances-empty.png`

## C2 — Corrigir adiantamento errado? (só investigação)

| Pergunta | Achado |
|---|---|
| Caminho na UI do `OrderAdvancesPanel`? | **Não.** Só registrar + lista. Sem botão cancelar/editar. |
| Cancel API existe? | **Sim** — `POST /api/payments/{id}/cancel` (Inc-3); UI em `PaymentDetailPage` (`/payments/:id`), não no painel do pedido. |
| Consolidado após cancel? | **Sim, recalcula.** `list_order_advances` filtra `status=REGISTERED` → cancelados saem da soma e da média. |
| FxExecution tratado no cancel? | **Não.** `cancel_payment` não toca FX; execução fica órfã no Payment CANCELLED. Neste CLEAN, FX demo foi apagado à mão. Sem “edit in place”. |

### Veredito (tamanho do buraco)

**Buraco médio, operacionalmente relevante antes do G6:** o Ricardo **não consegue** corrigir taxa errada pela tela do pedido. Workaround possível (não guiado no painel): abrir `/payments/{id}` → Cancelar → registrar de novo. Isso recalcula o consolidado, mas deixa FxExecution órfão (não deletado/cancelado pelo domínio). Não há edição de taxa/BRL.

**Recomendação ao advisor:** fatia curta (cancel no painel + política FX no cancel) **antes ou no início do FIN-2** — não bloquear G6 se o Ricardo conferir os valores com cuidado; bloquear se houver risco alto de typo.

**Não implementado** (mandato).

## Próxima

G6 Ricardo com ambiente limpo — [`J4_FIN1_G6_ROTEIRO.md`](J4_FIN1_G6_ROTEIRO.md). Depois FIN-2 (+ possível fatia cancel UI).

```text
DOC_DELTA
- Updated: docs/v2/etapa-j4-fin/J4_FIN1_CLEAN_ADVISOR_HANDOFF.md; J4_FIN1_G6_ROTEIRO.md (nota limpo)
- Evidence: screenshots/fin1-clean-order-589-advances-empty.png; logs/fin1-clean-pytest-full.txt; logs/fin1_clean_check.py
- Roadmap status: UNCHANGED (0.5.96; G6 permanece próxima)
- Next TODO: G6 Ricardo adiantamento real 589
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN1_CLEAN_ADVISOR_HANDOFF.md
```
