# J4-FIN FIN-1C-UX — catálogo de achados (ensaio G6)

| Campo | Valor |
|---|---|
| Etapa | **FIN-1C-UX** |
| Status | **DONE** (só findings — **zero** conserto / limpeza / FIN-4 código) |
| Runtime | `http://127.0.0.1:8081` · `epic_v2` · `AMBIENTE: OPERAÇÃO` · Alembic **022** |
| Data | **2026-08-11** |
| Aceite G6 | **NÃO** — G6 Ricardo já rejeitado; este ensaio cataloga o porquê + N1–N4 |
| Ambiente | Order **31** / **589** **permanece sujo** (evidência) |

---

## G2 — health

`schema_ok=true` · `logical_database=epic_v2` · `alembic_head=022` · lane Operação.

## G1 — Payments `order_id=31`

| id | status | EUR | payment_date | FX rate | BRL |
|---|---|---|---|---|---|
| 10 | CANCELLED | 1000 | 2025-06-15 | — | — |
| 11 | CANCELLED | 500 | 2025-07-20 | — | — |
| 12 | CANCELLED | 1000 | 2025-06-15 | 6.20 | 6200 |
| 13 | CANCELLED | 500 | 2025-07-20 | 6.39944 | 3199.72 |
| 14 | CANCELLED | 100 | 2025-08-01 | 6.02 | 602 |
| 15 | CANCELLED | 5000 | 2026-08-13 | 5.89 | 29450 |
| **16** | **REGISTERED** | **25000** | **2026-08-25** | **5.91** | **147750** |

REGISTERED **1** · CANCELLED **6** · Payables do pedido **0** · `fx_market_quotes` ~**491** · outros pagamentos mesmo `supplier_id`+`currency` com `order_id≠31`: **0** (neste DB).

Script: [`logs/fin1c_g1_query.py`](logs/fin1c_g1_query.py).

---

## Ciclo de negócio (N4 — régua)

1. Pedido → compromisso — **existe** (589 CONFIRMED, linhas COMMITMENT).
2. Adiantamento → crédito no pedido — **FIN-1 FEITO** (Payment #16 + FxExecution #13).
3. Fattura → Conta a pagar — **FIN-3 NOT_STARTED** (zero faturas no 589).
4. Liquidação formal do crédito na conta — **FIN-2 NÃO existe** como produto (há Inc-3 Payment→Payable genérico; sem fluxo “aplicar crédito do pedido”).
5. Saldo → nova saída alocada — depende de FIN-2/3.
6. Conta fecha → estoque / landed — J#5/J#6.

Alocação Inc-3 **existe** (`/payments/{id}` · “Obrigações elegíveis” · “Alocar”). No 589: `Nenhuma obrigação elegível` porque **não há Payable** (sem Fattura ISSUED), não porque “FIN-2 sumiu”.

---

## Relato narrativo (clique → literal)

Pré-voo: login `admin@epic.com.br` (sessão anterior expirada; página comercial sem auth mostrava empty state falso — refeito autenticado).

### Passo — Comercial `/orders/31/commercial`

- **Vi:** `Pedido 589` · `Heroe's Srl · EUR · 04/06/2026` · `Total comercial: EUR 830.000,00` · `Nenhuma fatura`.
- Painel **`Adiantamentos (crédito)`**:
  - Notice: `Adiantamento é crédito (dinheiro já saiu). Não gera título em Contas a pagar.`
  - `Total adiantado (EUR)` `EUR 25.000,00` · `Total adiantado (BRL)` `BRL 147.750,00` · `Câmbio médio ponderado` `5,910000`
  - Linha: `25/08/2026 · EUR 25.000,00 → BRL 147.750,00 · taxa 5,910000 · câmbio em 21/08/2026` · botão `Cancelar`
  - Form: `Valor (EUR)` · `Taxa EUR→BRL (opcional se informar BRL)` · `Valor BRL do extrato (opcional se informar taxa)` · `Data do pagamento` · `Data da execução de câmbio` · `Referência (opcional)` · `PDF de câmbio (opcional)` · `Registrar adiantamento`
- **Nota vs roteiro G6:** roteiro espera “Nenhum adiantamento registrado” pós-limpeza FIN-1B; ambiente está **sujo de propósito** pós-G6 Ricardo.

### Passo — Cancel modal (A2, sem confirmar)

- Cliquei `Cancelar` na linha do adiantamento.
- **Vi modal:** título `Cancelar adiantamento` · `Cancelar este adiantamento? O valor sai do consolidado.` · `EUR 25.000,00 → BRL 147.750,00 · taxa 5,910000` · `Motivo (obrigatório)` · botões `Fechar` / `Cancelar` / `Cancelar adiantamento`.
- **Foco inicial:** botão **`Fechar`** (`[active, focused]`) — **não** o campo Motivo.
- Fechei com `Fechar` — Payment **16** permanece REGISTERED.

### Passo — Cockpit `/orders/31` (N1+A1)

- KPIs: `Pedido EUR 830.000,00` · `Faturado EUR 0,00` · `Pago EUR 0,00` · `Saldo EUR 0,00`.
- Pendência: `Pagamentos com residual (candidatos a alocação — não são vínculos com o pedido)`.
- **Tesouraria → Pagamentos** (sem coluna de status): lista com residual cheio:
  - `EUR 25.000,00` residual `EUR 25.000,00`
  - `EUR 5.000,00` residual `EUR 5.000,00`
  - `EUR 100,00` · `EUR 500,00` · `EUR 500,00` · `EUR 1.000,00` · `EUR 1.000,00` (todos residual = valor)
- **Pagamentos com residual** (candidatos): notice `Candidatos a alocação — não são vínculos com o pedido.` · só `EUR 25.000,00` (REGISTERED).
- Faturamento: `Nenhuma fatura` · `Nenhuma obrigação`.

### Passo — Contas a pagar `?order_id=31`

- Título `Contas a pagar` · `Fila operacional · vencidos primeiro`.
- Chip `Pedido: 31` · empty: `Nenhuma obrigação neste filtro` · `Limpe os filtros ou aguarde novas emissões.`
- **ZERO títulos** (passo 8 do G6 OK).

### Passo — Pagamento `#16`

- Título: `Heroe's Srl · 25/08/2026 · EUR 25.000,00` · Status `Registrado`.
- `VALOR EUR 25.000,00` · `ALOCADO EUR 0,00` · `RESIDUAL EUR 25.000,00`.
- `Alocações` → `Nenhuma alocação ainda`.
- `Obrigações elegíveis` → `Nenhuma obrigação elegível` · botão `Alocar` presente.
- `Câmbio realizado`: `25.000,00` · `5,9100` · `BRL 147.750,00`.

### Passo — Lista `/payments`

- Título `Pagamentos` · subtitle `Movimentos financeiros e residual`.
- Filtros: `Todos` / `Somente com residual` · `Novo pagamento`.

---

## Tabela de achados

| # | Tela | Literal / fato | Por que errado | Gravidade | Arquivo |
|---|---|---|---|---|---|
| N1 | Cockpit Tesouraria | Lista “Pagamentos” via `supplier_id`+`currency`, **não** `order_id` | Pode misturar dinheiro de outros pedidos do mesmo fornecedor; painel Adiantamentos já é order-scoped | **BLOQUEIA** | [`reporting/queries.py`](../../../v2/app/reporting/queries.py) `order_cockpit` L241–243 |
| A1 | Cockpit Pagamentos | CANCELLED aparecem com residual = valor cheio; sem badge de status | Residual de cancelado não é crédito ativo; distorce leitura | **BLOQUEIA** | mesmo + UI [`OrderCockpitPage.tsx`](../../../v2/frontend/src/features/orders/OrderCockpitPage.tsx) |
| A2 | Modal cancel adiantamento | Foco inicial em `Fechar` | Teclado: Enter cedo fecha sem motivo; Motivo deveria receber foco | **MAJOR** | [`ConfirmationModal.tsx`](../../../v2/frontend/src/ui/ConfirmationModal.tsx) + `useFocusTrap` |
| A3 | Payment #16 | `Nenhuma obrigação elegível` | **Não é bug FIN-2** — alocação existe; falta Payable/Fattura | **INFO** (gap de ciclo) | Inc-3 + estado 589 |
| A4 | Form adiantamento | Só preview se usuário digita taxa **ou** BRL; sem sugerir BRL de cotação do dia | Cotação existe (ticker `EUR/BRL 5,8910`); painel não sugere. SoT permanece extrato | **MINOR** (só relatório) | [`OrderAdvancesPanel.tsx`](../../../v2/frontend/src/features/treasury/OrderAdvancesPanel.tsx) |
| V1 | Nav | `Pagamentos` (não “Pagamentos realizados”) | Vocab canônico N2 incompleto | **MAJOR** (rename batch) | [`AppShell.tsx`](../../../v2/frontend/src/app-shell/AppShell.tsx) |
| V2 | `/payments` | Subtitle `Movimentos financeiros e residual` | Genérico; não distingue crédito vs liquidação | MAJOR (N2) | `PaymentsListPage` |
| V3 | Cockpit KPI “Pago” | `Pago EUR 0,00` com €25k adiantado | “Pago” via alocações ≠ crédito de adiantamento — honestidade de ciclo | MAJOR | cockpit KPIs |
| E1 | Ambiente | 6 CANCELLED + 1 REGISTERED no 31 | Sujo pós-G6; limpar **só** em FIX antes de novo G6 | INFO | G1 |

---

## A1–A4 + N1 (veredito)

### N1 — **CONFIRMADO / BLOQUEIA**

```241:243:v2/app/reporting/queries.py
    payments = treasury_public.list_payments(
        db, supplier_id=order.supplier_id, currency=order.currency, limit=COCKPIT_LIST_LIMIT, offset=0
    )
```

`Payment.order_id` e `list_payments(..., order_id=)` já existem (FIN-1). Neste `epic_v2` não há outros pagamentos Heroe's EUR fora do 31 — o risco cross-order **não se manifesta em dados**, mas o código **já está errado**. Preferência: lista principal **só** `order_id`; candidatos podem permanecer supplier+currency **com** notice (já há notice nos candidatos).

### A1 — **CONFIRMADO / BLOQUEIA**

Lista principal inclui CANCELLED com residual cheio; sem status na tabela. Candidatos filtram bem (`REGISTERED` + residual > 0).

### A2 — **CONFIRMADO / MAJOR**

Foco em `Fechar` (primeiro focusable do modal).

### A3 — **REFUTADO como “FIN-2 missing”**

Alocação existe. Gap 589 = sem Payable. FIN-2 (liquidação formal do crédito do pedido) continua **ausente** como fluxo de produto — separado.

### A4 — **CONFIRMADO / MINOR (relatório)**

Sem sugestão de BRL a partir de cotação; SoT = extrato.

---

## Inventário vocabulário (N2)

| Onde | Literal atual | Canônico desejado (não renomear agora) |
|---|---|---|
| Nav Financeiro | `Contas a pagar` | Contas a pagar ✓ |
| Nav Financeiro | `Pagamentos` | **Pagamentos realizados** |
| `/payables` título | `Contas a pagar` | ✓ |
| `/payments` título | `Pagamentos` | Pagamentos realizados |
| `/payments` subtitle | `Movimentos financeiros e residual` | Revisar |
| Cockpit | `Pagamentos` / `Pagamentos com residual` | Distinguir realizados vs candidatos |
| Cockpit KPI | `Pago` | Não confundir com adiantamento |
| Painel Order | `Adiantamentos (crédito)` | ✓ |
| Notice painel | `Não gera título em Contas a pagar` | ✓ |
| Payment detail | `Residual` · `Obrigações elegíveis` · `Alocar` | Manter; estados: crédito em aberto / parcial / total |
| domainLabels | `UNALLOCATED_CANDIDATE` → notice longa sobre candidatos | ✓ honestidade parcial |

**Errado se aparecer:** Contas pagas / Liquidados para antecipo.

---

## Atrito de navegação (N3)

| Tarefa | Cliques / telas | Atrito |
|---|---|---|
| Ver crédito do 589 | 1 — Comercial (painel na mesma página) | Baixo |
| Cancelar adiantamento | Comercial → Cancelar → Motivo → confirmar | Foco errado (A2); Motivo obrigatório OK |
| Ver se “pago” no pedido | Cockpit separado (`/orders/31`) | KPI `Pago`=0 com €25k crédito — força ir ao painel Adiantamentos |
| Alocar crédito | Cockpit link pagamento **ou** `/payments` → detalhe | Sem deep-link “liquidar crédito do pedido”; elegíveis vazios sem Fattura |
| Conferir zero Payable | Digitar `order_id=31` em Contas a pagar (ou chip) | Aceitável; roteiro G6 OK |
| Registrar 2ª parcela | Mesmo form sob o consolidado | OK; sem atalho de datas do banco |

Propostas (não implementar): alinhar KPI cockpit ao crédito FIN-1; atalho Cockpit↔Adiantamentos; empty state alocação explicar “sem Fattura/Payable”.

---

## Apêndice — FIN-4 (arquitetura; **não construir**)

### Decisão canônica

- Termos de pagamento no **Order** → previsões `Payable.source_type=ORDER_SCHEDULE`.
- Fattura: scadenze **substituem** previsões do valor faturado.
- Adiantamento **já pago** (crédito FIN-1) **não** é substituído.
- Evitar contagem dupla (previsão + scadenza).

### Verificação técnica (canônica)

| Item | Achado |
|---|---|
| `source_type` | `String(32)` sem CHECK de valores — `ORDER_SCHEDULE` **barato**, sem migration de ENUM |
| `PaymentTerm` | Só de Invoice — FIN-4 precisa `OrderPaymentTerm` (ou generalização); reusar **shape**, não FK |
| Ordine 589 | Sem texto de pagamento no **documento**; parser também não extrai |

### Aviso FIN-3 (canônico)

Ao gerar Payable da Fattura, **não** assumir Invoice como única origem. FIN-3 deve nascer sabendo que `ORDER_SCHEDULE` virá; scadenze **substituem** previsões (não duplicam).

**Porta hoje:** **não fechada.** `_generate_payables` só emite `source_type=INVOICE`, mas o modelo já é multi-origem (`CUSTOMS_FUNDING`) e `source_type` é string. FIN-3 **não** deve “simplificar” para Invoice-only comercial.

≠ **J#5-REC** (ex-rótulo “FIN-4” antigo).

---

## Fatias propostas (advisor decide)

| Fatia | Conteúdo |
|---|---|
| **FIN-1C-FIX-1** | Cockpit lista por `order_id`; CANCELLED honesto; notice lista vs candidatos; empty state alocação; **limpeza** demos 31 pré-novo G6 |
| **FIN-1C-FIX-2** | Foco Motivo (A2); rename vocab N2; atritos N3 de maior ganho; (se autorizar) sugestão BRL A4 |
| **FIN-2** | Liquidação formal crédito→Payable |
| **FIN-3** | Fattura→Payable **com** replace de `ORDER_SCHEDULE` |
| **FIN-4** | Cronograma Order — **só registrada** |

---

## Ambiente

**Não limpo.** Payment **16** REGISTERED permanece.
