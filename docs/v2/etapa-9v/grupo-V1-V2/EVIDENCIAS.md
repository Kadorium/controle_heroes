# Grupo V1 + V2 — Filas e detalhes Horizon A

## Estado

**DONE** (escopo V1+V2). Etapa 9V permanece **PARTIAL** (V3 não iniciado). Aceite visual Horizon A permanece **NOT_ACCEPTED**.

## Objetivo

Aplicar primitives V0 às oito SCR de filas (V1) e detalhes (V2), com comparação browser vs MCK/Handoff e correção iterativa de BLOCKER/MAJOR.

## Escopo

| Grupo | SCR | Superfície |
|---|---|---|
| V1 | SCR-003 | Pedidos |
| V1 | SCR-006 | Faturas |
| V1 | SCR-008 | Contas a pagar |
| V1 | SCR-010 | Pagamentos |
| V2 | SCR-005 | Cockpit |
| V2 | SCR-007 | Fatura |
| V2 | SCR-009 | Câmbio da obrigação |
| V2 | SCR-012 | Pagamento e alocações |

V3 (formulários + fechamento visual das 12 SCR) **fora de escopo**.

## Decisões técnicas

| Tema | Decisão |
|---|---|
| Backend | Enrichment aditivo de leitura: `order_code` / `supplier_name` em listagens e `InvoiceResponse`; alertas cockpit em PT no reporting |
| Boundaries | `treasury` não importa `orders`; `EligiblePayable.order_code` permanece opcional (FE fallback `Pedido {id}`) |
| Cockpit | Read-only; comercial via rota `/orders/:id/commercial` |
| E2E | `workers: 1` (DB compartilhado `epic_v2_test`); screenshots 1366+1440 após conteúdo carregado |

## Gates

| Gate | Resultado |
|---|---|
| Unit frontend | **PASS** — 41 tests |
| Pytest reporting + arch | **PASS** — 13 passed |
| Typecheck + build | **PASS** |
| E2E `epic_v2_test` V1/V2 + C + Inc-5 | **PASS** |
| Visual 1366 (8 SCR) | Capturado — matriz abaixo |
| Visual 1440 (8 SCR) | Capturado — matriz abaixo |
| BLOCKERS conhecidos | **0** |
| MAJORS conhecidos | **0** (dívidas residuais → V3) |

Log: `logs/grupo-V1-V2-e2e.txt`, `logs/i9v-v1-v2-e2e.txt`

## Screenshots

| SCR | 1366 | 1440 |
|---|---|---|
| SCR-003 | `screenshots/scr-003-orders-1366.png` | `screenshots/scr-003-orders-1440.png` |
| SCR-005 | `screenshots/scr-005-cockpit-1366.png` | `screenshots/scr-005-cockpit-1440.png` |
| SCR-006 | `screenshots/scr-006-invoices-1366.png` | `screenshots/scr-006-invoices-1440.png` |
| SCR-007 | `screenshots/scr-007-invoice-1366.png` | `screenshots/scr-007-invoice-1440.png` |
| SCR-008 | `screenshots/scr-008-ap-1366.png` | `screenshots/scr-008-ap-1440.png` |
| SCR-009 | `screenshots/scr-009-fx-1366.png` | `screenshots/scr-009-fx-1440.png` |
| SCR-010 | `screenshots/scr-010-payments-1366.png` | `screenshots/scr-010-payments-1440.png` |
| SCR-012 | `screenshots/scr-012-payment-1366.png` | `screenshots/scr-012-payment-1440.png` |

## Matriz de comparação (MCK / Handoff)

| SCR | Conteúdo | Datas | Dinheiro | Status | Referências | Layout | MCK/ref. | Veredito |
|---|---|---|---|---|---|---|---|---|
| SCR-003 Pedidos | PT; filtros; CTA Novo pedido; RowLink | DD/MM/AAAA | EUR 400,00; moeda explícita | Confirmado (badge) | Código + fornecedor por nome | Fila densa; hover/seleção | MCK-001 / Handoff SCR-003 | **PASS** |
| SCR-006 Faturas | PT; filtros; sem ACCONTO | DD/MM/AAAA | Líquido/saldo com moeda | Emitida | Número + order_code + fornecedor | Fila operacional | Handoff SCR-006 · análogo MCK-001 | **PASS** |
| SCR-008 Contas a pagar | KPIs PT; sem Payables/unalloc.; G02 | Vencimento localizado | Saldo/FX BRL quando há | Aberto | Fatura/pedido por código | Tabela + drawer | MCK-004 | **PASS** |
| SCR-010 Pagamentos | Sem Create≠Allocate; residual filter | DD/MM/AAAA | Valor/alocado/residual EUR | Registrado | Fornecedor por nome; ref. — | Densidade standard | Handoff SCR-010 · motivador 9V | **PASS** |
| SCR-005 Cockpit | RO; Faturamento/Tesouraria/Docs; alertas PT | Datetime + date | KPIs formatados; sem KPI falso | Confirmado | Deep links proprietários | Blocos MCK-002 | MCK-002 | **PASS** |
| SCR-007 Fatura | Itens/condições/obrigações; Issue preservado | Datas localizadas | Money + qty formatados | Emitida / Aberto | Pedido por código; parcela N | Sem enum crua | MCK-003 | **PASS** |
| SCR-009 Câmbio | Planejado/Mercado/Realizado; FX≠liquidação | Venc. formatado | Rate 4 casas; PnL — | Aberto | Título por venc.; fatura no contexto | Três colunas | MCK-007 | **PASS** |
| SCR-012 Pagamento | Create≠Allocate por comportamento; modal | Data localizada | KPI valor/alocado/residual | Registrado | Fornecedor; elegíveis por fatura | Alocação + FX execução | MCK-006 | **PASS** |

## Correções sistêmicas aplicadas neste ciclo

- Conteúdo PT de produto; remoção de microcopy Inc-4A / Payables / unalloc. / Create≠Allocate
- Datas sem ISO cru; dinheiro `EUR 400,00`; ausência `—`
- Status badges semânticos em PT
- Fornecedor por nome; order_code nas filas e detalhe de fatura
- RowLink / ações DS (sem link HTML cru de linha)
- Cockpit sem embed de escrita
- E2E aguarda conteúdo (não captura loading)

## Dívidas remanescentes (V3 / decisões abertas)

- Formulários de criação/edição (SCR restantes / V3): densificação MCK, inputs ainda com decimais cruos em alguns campos de escrita
- `EligiblePayable.order_code` sem enrichment via treasury→orders (fallback `Pedido {id}` na alocação)
- Pixel-perfect MCK (espaçamento fino, tipografia exata) e revisão externa das 12 SCR
- L-005, ACCONTO, comprador × Treasury — fora de escopo (preservado)
- Nav ativa do shell em rotas de detalhe aninhadas (highlight do módulo pai) — polish V3

## Próxima etapa lógica

V3 + fechamento visual das 12 SCR, após revisão externa das screenshots V1/V2.
