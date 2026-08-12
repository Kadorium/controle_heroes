# J4-FIN FIN-1C-FIX-2 — verificação UI (agente) — **DONE**

| Campo | Valor |
|---|---|
| Etapa | **FIN-1C-FIX-2** |
| Status | **DONE** |
| Data | **2026-08-11** |
| Runtime | `:8081` / `epic_v2` / Alembic **022** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-WDdEsUif.js`** |
| Pytest | **473 passed** (ref. 471 → +2) |
| Valores | teste do agente (não extrato real) |

---

## Checklist inventário N2 (item a item)

| Onde (FINDINGS) | Antes | Depois | OK |
|---|---|---|---|
| Nav Financeiro `Contas a pagar` | Contas a pagar | Contas a pagar | ✓ |
| Nav Financeiro `Pagamentos` | Pagamentos | **Pagamentos realizados** | ✓ |
| `/payables` título | Contas a pagar | Contas a pagar | ✓ |
| `/payments` título | Pagamentos | **Pagamentos realizados** | ✓ |
| `/payments` subtitle | Movimentos financeiros e residual | **Dinheiro que saiu do caixa — residual ainda não aplicado a Contas a pagar** | ✓ |
| Cockpit lista | Pagamentos deste pedido | **Pagamentos realizados deste pedido** | ✓ |
| Cockpit KPI Pago | Pago (alocado) | Pago (alocado) (+ hint) | ✓ |
| Painel Order | Adiantamentos (crédito) | Adiantamentos (crédito) | ✓ |
| Notice painel | Não gera título em Contas a pagar | idem | ✓ |
| Payment detail Residual | Residual | **Aberto** + **Estado** (crédito/parcial/total) | ✓ |
| Breadcrumb payments | Pagamentos | **Pagamentos realizados** | ✓ |
| domainLabels | — | `paymentAllocationStateLabel` | ✓ |
| Contas pagas / Liquidados | — | **não aparecem** (só comentário de guarda) | ✓ |

Busca no código FE (`*.tsx`/`*.ts` src, exceto openapi): zero `title="Pagamentos"`, zero `Movimentos financeiros`, zero `Nenhuma obrigação elegível`.

---

## Relato literal (clique → o que vi)

### Nav
- **Vi:** `Contas a pagar` · `Pagamentos realizados`.

### `/payments`
- **Vi título:** `Pagamentos realizados`
- **Vi subtitle:** `Dinheiro que saiu do caixa — residual ainda não aplicado a Contas a pagar`
- **Vi filtro:** `Somente crédito em aberto` (antes: Somente com residual)
- **Vi Estados na fila:** `crédito em aberto` (#22, #3) · `parcialmente alocado` (#4, #2, #1) · `totalmente alocado` (#9…)

### `/payments/22` (adiantamento teste 589)
- Breadcrumb: `Pagamentos realizados`
- Empty elegíveis: `Sem Fattura emitida, não há Conta a pagar (obrigação) para alocar este crédito.` · `A alocação existe no sistema; falta a fatura gerar a obrigação.`

### Cockpit `/orders/31`
- Link **`Adiantamentos`** → `/orders/31/commercial#order-advances`
- Título seção: `Pagamentos realizados deste pedido`
- Estado do pagamento de teste: `crédito em aberto`
- KPI: `Pago (alocado) EUR 0,00` · `Adiantado (crédito) EUR 200,00`

### Atalho
- **Cliquei** `Adiantamentos` no cockpit → URL `#order-advances` · painel `order-advances` na comercial.

### Sugestão BRL (V3)
1. Preenchi EUR `200` + execução `2026-08-11`.
2. **Vi (campo BRL ainda vazio):**  
   `Sugestão do sistema (não é o extrato). Cotação 11/08/2026 · Frankfurter (ECB): taxa 5,891000 → BRL 1.178,20. O valor verdadeiro é o do seu extrato bancário.` · botão `Preencher BRL com a sugestão`
3. **Cliquei** aplicar → BRL `1.178,20` · `Sugestão aplicada — confira e sobrescreva…`
4. Sobrescrevi para `1.200,00` (depois `1.190,00` no registro) — aceito.
5. Mudei execução para `2026-01-01` → sugestão some · `Sem cotação de mercado para …` (missing, sem inventar vizinho).
6. Registrei com BRL sobrescrito `1.190,00` → linha `12/08/2026 · EUR 200,00 → BRL 1.190,00 · taxa 5,950000`.

---

## Atritos N3 — o que ficou de fora

| Item | Feito? | Por quê |
|---|---|---|
| Empty state alocação sem Fattura | **SIM** | Barato, alto ganho |
| Atalho Cockpit ↔ Adiantamentos | **SIM** | Link + hash `#order-advances` |
| Deep-link “liquidar crédito do pedido” | **NÃO** | É FIN-2 |
| Atalho datas do banco / pré-preencher calendário | **NÃO** | Baixo ganho vs risco; FIX-1B já limpa datas |
| Renomear “Candidatos a alocação” em bloco | **NÃO** | Já honesto pós-FIX-1; evitar redesenho |
| Filtro AP “Crédito em aberto” KPI label | **SIM** (parcial) | Label/hint alinhados |

---

## Limpeza

Payments de teste (#22 + FX) removidos. Order **31** CONFIRMED · 2 linhas · só `Ordine_589 (1) (1).pdf`. Painel: `Nenhum adiantamento registrado`.  
Screenshot: [`screenshots/fix2-commercial-empty.png`](screenshots/fix2-commercial-empty.png).

---

## Gates

| # | Gate | Resultado |
|---|---|---|
| 1 | pytest | **473 passed** |
| 2 | Sem termo antigo no código FE | PASS |
| 3 | Sugestão BRL marcada + sobrescrevível + missing | PASS |
| 4 | Ambiente limpo | PASS |
| 5 | Chromium + asset | `index-WDdEsUif.js` |

```text
DOC_DELTA
- Updated: J4_FIN1C_FIX2_UI.md; J4_FIN1C_FIX2_ADVISOR_HANDOFF.md; ROADMAP 0.5.102; código FE/BE FIX-2
- Evidence: screenshots/fix2-*; logs/fin1c-fix2-*
- Roadmap status: 0.5.102 — FIX-2 DONE; next = uso normal (adiantamento real) / FIN-2
- Next TODO: registrar adiantamento real 589 (uso) ou FIN-2 conforme advisor
- Return to advisor: J4_FIN1C_FIX2_ADVISOR_HANDOFF.md
```
