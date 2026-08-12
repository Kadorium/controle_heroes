# J4-FIN FIN-1C-UX — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1C-UX** |
| Status | **DONE** |
| Runtime | `:8081` / `epic_v2` / Alembic **022** |
| Código | **zero** patch · **zero** limpeza · **zero** FIN-4 implementação |
| Evidência | [`J4_FIN1C_UX_FINDINGS.md`](J4_FIN1C_UX_FINDINGS.md) |

---

## Estado anterior → atual

| Antes | Depois |
|---|---|
| FIN-1B DONE; G6 Ricardo **não aceito**; ambiente sujo | FINDINGS catalogado (N1–N4 + A1–A4); ambiente **ainda** sujo |
| FIN-4 inexistente no mapa | **FIN-4 NOT_STARTED** registrada (cronograma Order) |
| Aviso FIN-3 truncado | Aviso FIN-3 **completo e canônico** no Roadmap + FINDINGS |

---

## Hipóteses

| ID | Hipótese | Resultado |
|---|---|---|
| N1 | Cockpit lista não é do pedido | **CONFIRMADO BLOQUEIA** — `list_payments(supplier_id, currency)` |
| A1 | Cancelados com residual cheio | **CONFIRMADO BLOQUEIA** |
| A2 | Foco modal em Fechar | **CONFIRMADO MAJOR** |
| A3 | “Falta FIN-2 / alocação” | **REFUTADO** — alocação existe; falta Payable |
| A4 | Sem sugestão BRL de cotação | **CONFIRMADO MINOR** (só relatório) |
| FIN-3 porta | Desenho atual fecha Invoice-only? | **NÃO** — multi-origem já existe; FIN-3 deve nascer com replace `ORDER_SCHEDULE` |

---

## FIN-4 (registrar; não construir)

- Termos no **Order** → `Payable.source_type=ORDER_SCHEDULE`.
- Fattura substitui previsões de saldo; antecipo pago (FIN-1) **não** substituído.
- Achados canônicos: `source_type` String barato; `OrderPaymentTerm` novo (shape ≠ FK `PaymentTerm`); ausência termos 589 = **documento**.
- ≠ **J#5-REC** (ex-“FIN-4”).

## FIN-3 (aviso canônico)

Não assumir Invoice como única origem de obrigação. Scadenze **substituem** previsões `ORDER_SCHEDULE` (não duplicam). Porta atual **aberta**.

---

## Gates / entregas

- G2 OK · G1 tabela no FINDINGS · ensaio UI narrativo · vocab N2 · atrito N3 · ciclo N4 · fatias propostas.
- Roadmap **0.5.98**.

## Recomendação

1. Aceitar FINDINGS.
2. Autorizar **FIN-1C-FIX-1** (N1+A1+limpeza pré-G6) depois **FIX-2** (A2+vocab).
3. Novo G6 Ricardo só após FIX + limpeza demos.
4. FIN-2 / FIN-3 / FIN-4 na ordem do mapa; FIN-3 já ciente de FIN-4.

## Pendências

- Advisor decide fatias FIX.
- Ambiente sujo (Payment **16** REGISTERED + 6 CANCELLED) — **não** limpar nesta etapa.

## Arquivos relevantes

- [`J4_FIN1C_UX_FINDINGS.md`](J4_FIN1C_UX_FINDINGS.md)
- [`ROADMAP_V2_EPIC.md`](../../../ROADMAP_V2_EPIC.md) (0.5.98)
- Código citado (somente leitura): `reporting/queries.py`, `OrderCockpitPage.tsx`, `OrderAdvancesPanel.tsx`, `ConfirmationModal.tsx`, `billing/commands.py` `_generate_payables`

---

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j4-fin/J4_FIN1C_UX_FINDINGS.md; docs/v2/etapa-j4-fin/J4_FIN1C_UX_ADVISOR_HANDOFF.md; docs/README.md (se tocado)
- Evidence: docs/v2/etapa-j4-fin/J4_FIN1C_UX_FINDINGS.md; docs/v2/etapa-j4-fin/logs/fin1c_g1_query.py
- Roadmap status: 0.5.97 → 0.5.98 (FIN-1C-UX DONE; FIN-4 NOT_STARTED registrada; ≠ J#5-REC; aviso FIN-3)
- Next TODO: Advisor aceitar FINDINGS → autorizar FIN-1C-FIX-*
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN1C_UX_ADVISOR_HANDOFF.md (+ FINDINGS)
```
