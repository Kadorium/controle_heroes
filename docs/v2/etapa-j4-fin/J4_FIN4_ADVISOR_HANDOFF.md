# J4-FIN-4 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-4** — cronograma de pagamento no pedido |
| Status | **DONE** |
| Data | **2026-08-13** |
| Runtime | `:8081` / `epic_v2` / Alembic **025** / `AMBIENTE: OPERAÇÃO` / `schema_ok=true` |
| Asset | **`index-BdwLLOq0.js`** |
| Blueprint | **0.2.19** |
| Roadmap | **0.5.114** |
| Pytest | **530 passed** |
| Vitest | `OrdersPages.test.tsx` **9 passed**; `check:api-drift` ok |
| Chromium | Chrome/144.0.7559.236 · Electron/40.10.3 · Cursor/3.14.7 |
| Preservado | Pedido **589** id **31** e **TESTE-CICLO-001** id **34** — CONFIRMED; **0** linhas de cronograma |
| Sample | **F4-WALK-f5c640a8** id **36** (dedicado; não é compra real) |

---

## Regra de negócio — uma frase

**O cronograma do pedido é planejamento comercial (quando pagar: data e/ou condição). Não é pagamento, adiantamento nem conta a pagar.**

ADVANCE continua ADVANCE. Fattura não cobre o cronograma. Pago / Adiantado / Exposição FX não somam o previsto.

---

## Estado anterior → atual

| | Antes | Depois |
|---|---|---|
| Pedido | Sem cronograma (tabela/API/UI) | `order_payment_schedule_lines` + GET/PUT `/api/orders/{id}/payment-schedule` |
| Alembic | **024** | **025** (CREATE TABLE; backfill NONE) |
| Cockpit | Sem seção de planejamento | `summary.schedule`; KPIs financeiros intocados |
| Comercial | Só adiantamentos/faturas | Editor de cronograma **ao lado** do painel de adiantamentos |
| Blueprint | 0.2.18 (dívida J4-FIN + sem contrato FIN-4) | **0.2.19** classes A+B |

---

## DECs (ratificadas F0; implementadas)

WHEN · MODE · BASE · AMOUNT · DIVERGE · EDIT · COVER · KPI · INGEST · FX — todas como no plano mestre. Sem enum de marco; sem coluna de modo em Order; sem `ORDER_SCHEDULE` em Payable; sem FxPlanRate; sem parser Ordine→cronograma; sem KPI “Previsto”.

---

## Gates

- Replace-set atômico; lista vazia limpa; xor %/valor; Σ%=100; due_date OU condition_text; 422 sem “quando”
- PERCENT com total incompleto → derivado `null` (não zero)
- AMOUNT DRAFT pode divergir; confirm/CONFIRMED 422 se total calculável e Σ ≠ total
- Itens não mutam cronograma; CANCELLED bloqueia; 409 via `Order.version`
- Emissão de fatura / ADVANCE / FX **não** consomem nem reclassificam o cronograma
- Orders ↛ Billing/Treasury (arch)
- Percurso UI real (abaixo)

Pytest FIN-4 + arch + migration 025: **29 passed** na fatia; suite completa **530 passed**.

---

## Percurso UI (`:8081` / `epic_v2`)

Pedido de ensaio **API-seed** (fornecedor/SKU/pedido DRAFT id **36**). Cronograma, confirmação e leitura no cockpit = **UI**. ADVANCE de EUR 100 = **API** (`register_without_fx_document`).

| # | Runtime / Abri / Vi / Cliquei | Resultado |
|---|---|---|
| 1 | Comercial `/orders/36/commercial` | Vazio: “Sem cronograma — a previsão não duplica antecipo nem obrigação.” |
| 2 | **Definir cronograma** | Editor PERCENT; data e/ou condição |
| 3 | 50% *bonifico anticipato* + 50% *saldo 90 GG DFFM* → **Salvar** | PUT 200; “Alinhado ao total comercial.”; derivado EUR 250 + 250 |
| 4 | Cockpit `/orders/36` | Planejamento visível; Pago/Adiantado/Exposição FX = **0**; Pedido EUR 500 |
| 5 | Recarregar comercial; editar 40/60; salvar | Persistiu 50/50; depois 40/60 alinhado (EUR 200 + 300) |
| 6 | **Confirmar** na UI | CONFIRMED; cabeçalho/itens readonly; cronograma editável com motivo |
| 7 | Salvar confirmado sem motivo → com `TERMS` | Bloqueio no cliente; PUT 200 com reason. ADVANCE API EUR 100: Adiantado **100**, Pago **0**, cronograma intacto |

Atrito (não corrigido): o painel de adiantamentos no comercial não recarregou sozinho após o ADVANCE via API — esperado; o cockpit mostrou o crédito. DateInput nativo `mm/dd/yyyy` no locale do browser — pré-existente.

---

## Riscos / divergências

- Nenhuma dupla contagem observada no walk nem nos testes F4.
- Servidor `:8081` foi recarregado após 025 + `frontend/dist` novo (uvicorn anterior esperava 024).
- 409 exercitado em pytest; no walk UI o bloqueio CONFIRMED sem reason foi no cliente (não chegou a 422 HTTP).

---

## Pendências

Nenhuma bloqueante de FIN-4. Fora de escopo: 3A/020, J#5-REC, J#6, settlement CUSTOMS_FUNDING, parser Ordine→cronograma, unbind Product.

---

## Próxima etapa

**Aguardando autorização.** Não iniciar 3A / 020 / J#6 / J#5-REC. A cadeia continua a parar na Fattura (elo 3 FRÁGIL).

---

## Recomendação

Aceitar FIN-4 **DONE**. Financeiro **5/5** no livro-razão (cronograma operável e documentado).

Evidências âncora: `docs/v2/etapa-j4-fin/` (este handoff; `J4_FIN4_EXECUTION_PLAN.md`; `screenshots/fin4-walk-*`).

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md; docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md; docs/v2/etapa-j4-fin/J4_FIN4_EXECUTION_PLAN.md
- Evidence: docs/v2/etapa-j4-fin/
- Roadmap status: 0.5.113 → 0.5.114 (FIN-4 DONE; Alembic 025; Financeiro 5/5). A/B: A.0 última=cronograma / próxima=aguardando autorização; A.1 Financeiro 100%; A.3 +cronograma; A.4 remove cronograma (itens 1–7); cadeia 20% inalterada. B.1 0.5.114 + head 025; livro-razão Financeiro 5/5; B.4 J4-FIN DONE; B.7 +0.5.114
- Next TODO: aguardando autorização — não iniciar 3A / 020 / J#6 / J#5-REC
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN4_ADVISOR_HANDOFF.md
```
