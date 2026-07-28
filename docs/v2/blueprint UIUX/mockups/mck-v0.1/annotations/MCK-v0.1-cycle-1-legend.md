# Legenda — MCK v0.1 Ciclo 1

Anotações **fora** do viewport 1440×900. Interface limpa nos SVGs.

---

## MCK-001 — Pedidos (SCR-003)

| # | Elemento | Classificação | Nota |
|---|---|---|---|
| 1 | Shell Compras \| Financeiro | **TARGET** §20 | AS-IS código = Ordens \| Financeiro |
| 2 | Faturas sob Compras | **TARGET** | Ownership Billing inalterado |
| 3 | CTA Nova ordem | **AS-IS** capacidade | Visual TARGET |
| 4 | Busca + chips de filtro | **TARGET** | AS-IS lista sem FilterBar rica |
| 5 | Colunas Faturado / Saldo / Próx. venc. | **TARGET** + **GAP_TECNICO** | Read model financeiro da fila Orders inexistente (H-E3-1). **Não** rotulado na UI |
| 6 | Total com. `3.050,00*` + footnote | **AS-IS** regra | Ausência ≠ 0; unpriced → total completo = — |
| 7 | Exceção “1 sem preço” | **AS-IS** domínio | Item HR-BAG-015 |
| 8 | Linha PO-2026-0181 + Abrir cockpit | **TARGET** affordance | Rota AS-IS `/orders/:id` |
| 9 | Sticky ênfase coluna Código | **TARGET** / decisão visual | |
| 10 | FX strip sidebar stale 6,2180 | **AS-IS** contrato | Visual TARGET claro |
| 11 | Hub Câmbio ausente no nav | **GAP** deliberado | Sem SCR-028 operacional |

**Pergunta A:** Consigo localizar rapidamente o pedido que exige atenção?  
→ PO-2026-0181: foco, vencimento em vermelho, exceção, link cockpit.

**FLW:** entrada da jornada; FLW-006/007 a partir do cockpit (Ciclo 2).

---

## MCK-004 — Contas a pagar (SCR-008)

| # | Elemento | Classificação | Nota |
|---|---|---|---|
| 1 | Mesmo shell da MCK-001 | Família visual | Checkpoint A→B |
| 2 | KPI strip (5) | **AS-IS** capacidade + **TARGET** visual | Valores do cenário canônico |
| 3 | Unalloc. residual 900 / PAY-0042 | **AS-IS** KPI | Não é relação Order↔Payment |
| 4 | Filtros + Order PO-2026-0181 | **AS-IS** parcial URL | Visual TARGET |
| 5 | PY-8841-1 VENCIDO | Cenário | Saldo 315 após alloc 600 |
| 6 | PY-8841-2 selecionado + drawer | **AS-IS** drawer + **TARGET** copy | Origem jornada PAY-2026-0043 |
| 7 | CTA Registrar pagamento | **TARGET** contexto | **G02** = AS-IS sem query; **não** fingir wiring |
| 8 | Mensagem Create ≠ liquidar | **TARGET** / domínio | FLW-003 |
| 9 | Destino PAY-2026-0043 · saldo intacto | Cenário reservado | Ciclo 2 MCK-005/006 |
| 10 | Ações Pag / FX na linha | **AS-IS** | FX → `/payables/:id/fx` |
| 11 | Heroes sem multi-supplier theater | **AS-IS** postura | Blueprint 0.2.8 |

**Pergunta B:** Consigo priorizar e agir sobre obrigações em volume?  
→ Vencido em KPI + linha vermelha; drawer com ação e FX; volume com 8 linhas.

**FLW:** FLW-003 (AP→Payment), FLW-005 (FX), FLW-007 (retorno fila).

---

## Gaps representados só aqui (não na UI)

- Enrichment financeiro Orders (colunas).
- G02 contexto AP→Payment.
- Hub SCR-028.
- Preservação scroll/linha retorno (footnote drawer).
