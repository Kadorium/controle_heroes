# Inventário estrutural — 12 SCR Horizon A

**Documento:** inventário estático autocontido (inspeção de código + contratos + evidências).  
**Origem:** plano `inventário_estrutural_scr_027ff0b2` (rev. filtros combináveis).  
**Data da inspeção:** 2026-07-30.  
**Trilha:** V2 (`v2/**`, `docs/v2/**`).  
**Roadmap:** não alterado por este documento.

**Nota de execução:** a campanha FE correspondente (C-001…C-021 aplicáveis) foi implementada após a aprovação do plano. Este arquivo preserva o inventário e as decisões; o estado AS-IS abaixo descreve a inspeção pré-campanha, e a coluna “Proposta / pós-campanha” indica o alvo.

---

## 0. Linguagens e tecnologias utilizadas

| Camada | Linguagem / formato | Onde | Papel no inventário |
|---|---|---|---|
| Frontend UI | **TypeScript** + **TSX** (React 18) | `v2/frontend/src/**` | Páginas SCR, Design System, filtros, navegação |
| Estilos | **CSS** (tokens / layout) | `v2/frontend/src/index.css` | Shell 220px, densidades tabela, KPIs, 1366/1440 gutters |
| Testes FE unitários | **TypeScript** (Vitest + Testing Library) | `v2/frontend/src/**/*.test.ts(x)` | Prefill login, primitives DS, listas |
| Testes FE E2E | **TypeScript** (Playwright) | `v2/frontend/e2e/**` | Suíte Horizon A / etapa 9V |
| Backend API | **Python 3** (FastAPI) | `v2/app/**` | Rotas, filtros `payables_queue`, payments, reporting |
| Persistência / queries | **Python** + SQLAlchemy (SQL gerado) | `v2/app/*/queries.py`, `repository.py` | Semântica `status` / `due_*` / `pending` |
| Contrato HTTP | **JSON** (OpenAPI) | `v2/frontend/src/api/generated/openapi.json` | Params de listagens |
| Tipagem cliente API | **TypeScript** gerado | `v2/frontend/src/api/generated/schema.ts` | Tipos consumidos pelo FE |
| Documentação de produto | **Markdown** | `docs/v2/**`, Handoff, Blueprint UI/UX, MCK | TARGET vs AS-IS, aceite |
| Evidências etapa 9V | **Markdown** + PNG | `docs/v2/etapa-9v/**` | Screenshots 1366/1440 |
| Config FE | **TypeScript** / JSON | `vite.config`, `tsconfig`, `package.json` | Build Vite; env `VITE_LOGIN_PREFILL` |

**Idioma de interface (produto):** português (Brasil) — labels, badges, notices.  
**Idioma técnico de domínio (códigos):** inglês estável nos enums (`OPEN`, `PARTIALLY_PAID`, `OVERDUE`, etc.) — nunca exibidos crus ao usuário quando há `statusLabels` / `domainLabels`.

---

## 1. Mapa rápido SCR → rota → raiz

| SCR | Nome | Rota | Componente raiz |
|---|---|---|---|
| 001 | Login | `/login` | `features/auth/LoginPage.tsx` |
| 002 | App Shell | chrome `/` | `app-shell/AppShell.tsx` |
| 003 | Pedidos | `/orders` | `features/orders/OrdersListPage.tsx` |
| 004 | Novo pedido | `/orders/new` | `features/orders/OrderCreatePage.tsx` |
| 005 | Cockpit | `/orders/:orderId` | `features/orders/OrderCockpitPage.tsx` |
| 006 | Faturas | `/invoices` | `features/billing/InvoicesListPage.tsx` |
| 007 | Fatura | `/invoices/:invoiceId` | `features/billing/InvoiceDetailPage.tsx` |
| 008 | Contas a pagar | `/payables` | `features/billing/ApQueuePage.tsx` (+ fallback `PayablesListPage`) |
| 009 | Câmbio da obrigação | `/payables/:payableId/fx` | `features/treasury/PayableFxPage.tsx` |
| 010 | Pagamentos | `/payments` | `features/treasury/PaymentsListPage.tsx` |
| 011 | Novo pagamento | `/payments/new` | `features/treasury/PaymentCreatePage.tsx` |
| 012 | Pagamento e alocações | `/payments/:paymentId` | `features/treasury/PaymentDetailPage.tsx` |

Wiring de rotas: `v2/frontend/src/App.tsx`.

---

## 2. Inventário por página (SCR-001…012)

### SCR-001 — Login

| Campo | Conteúdo |
|---|---|
| Rota | `/login` |
| Componente raiz | `LoginPage.tsx` |
| Filhos | `FormField`, `TextInput`, `Notice`, `Button` |
| Estrutura | h1 brand → subtítulo → e-mail/senha → erro → Entrar |
| Filtros | nenhum |
| Ações | Entrar → `POST /api/auth/login` |
| Permissões | público |
| DS | Button, FormField, Notice, TextInput |
| HTML residual | `<form className="login-form">`, `.page-center` |
| Problema | Prefill `admin@epic.com.br` / `admin123` |
| Correção | Prefill só `development` ou `VITE_LOGIN_PREFILL=1`; teste de ausência em production |
| 1366/1440 | form `min(420px,100%)` |
| Veredito inspeção | `FUNCTIONAL_NOT_READY` |

### SCR-002 — App Shell

| Campo | Conteúdo |
|---|---|
| Rota | Outlet autenticado |
| Raiz | `AppShell.tsx` |
| Filhos | NavLink Compras/Financeiro, `FxQuoteStrip`, Button Sair, `roleLabel` |
| Ações | Pedidos, Faturas, Contas a pagar, Pagamentos, Sair |
| Permissões | `orders:read`, `billing:read`, `reporting:read`\|`billing:read`, `treasury:read` |
| 1366/1440 | sidebar 220px; gutter 24→32 @1440 |
| Veredito | `READY` |

### SCR-003 — Pedidos

| Campo | Conteúdo |
|---|---|
| Rota | `/orders` |
| Estrutura | PageHeader + CTA → FilterChip status → OperationalTable → PaginationSummary |
| Filtros | Status: Todos / Rascunho / Confirmado / Cancelado → `status` |
| Ações | Novo pedido (`orders:write`); Código → cockpit |
| Colunas (inspeção) | Código, Data, Fornecedor, Status, Moeda, Subtotal, Faturado, Saldo, Próx. venc., Pendências |
| Proposta | Remover coluna Moeda (redundante com MoneyDisplay) |
| DS | Filter*, OperationalTable, EntityRef, MoneyDisplay, StatusBadge, RowLink |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-004 — Novo pedido

| Campo | Conteúdo |
|---|---|
| Rota | `/orders/new` |
| Estrutura | breadcrumb → header → SectionCards dados/itens → actions → ConfirmationModal |
| Ações | Voltar; Adicionar linha; Criar SKU; Salvar rascunho; Salvar e confirmar |
| Permissão | `orders:write` |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-005 — Cockpit

| Campo | Conteúdo |
|---|---|
| Rota | `/orders/:orderId` |
| Estrutura | breadcrumb → header → KPIs → alertas → Faturamento / Tesouraria / Docs |
| Permissão | `reporting:read` |
| HTML residual | 4× `table.mini-table` → substituir por OperationalTable |
| IDs | fallback título `Pedido {id}` |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-006 — Faturas

| Campo | Conteúdo |
|---|---|
| Rota | `/invoices` |
| Filtros | Status: Todas / Rascunho / Emitida / Cancelada |
| Colunas | Número, Pedido, Fornecedor, Data, Tipo, Status, Líquido, Saldo, Obrigações |
| IDs | `Pedido {order_id}` se sem `order_code` |
| FLW-007 | alinhar `useListReturn` |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-007 — Fatura

| Campo | Conteúdo |
|---|---|
| Rota | `/invoices/:invoiceId` |
| Estrutura | summary → Itens / Documento / Condições / Obrigações → Emitir |
| Ações | Salvar itens/condições; Anexar; Emitir (`billing:issue`) |
| HTML residual | mini-tables → OperationalTable |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-008 — Contas a pagar (**STRUCTURAL_CONFLICT** na inspeção)

| Campo | Conteúdo |
|---|---|
| Rota | `/payables` |
| Raiz | `ApQueuePage.tsx` |
| Estrutura | breadcrumb → header → KpiStrip → filtros → tabela finance → drawer |
| Permissão | `reporting:read` |
| Colunas inspeção (14) | Vencimento, Atraso, Fornecedor, Fatura, Pedido, Moeda, Valor, Alocado, Saldo, Taxa, BRL, Status, Pendências, Câmbio |
| Colunas proposta (10) | Vencimento(+atraso), Fornecedor, Fatura, Pedido, Valor, Saldo, Câmbio/BRL, Status, Pendências, ação Câmbio |
| Ver §3 filtros e §4 KPIs |

### SCR-009 — Câmbio

| Campo | Conteúdo |
|---|---|
| Rota | `/payables/:payableId/fx` |
| Estrutura | breadcrumb → header → SummaryGrid → PayableFxPanel (3 colunas + forms) |
| Problema | títulos empilhados; `Obrigação {id}` no loading |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-010 — Pagamentos

| Campo | Conteúdo |
|---|---|
| Rota | `/payments` |
| Filtros | Todos / Somente com residual → `unallocated_only` |
| Problema | Referência como link (incl. `—`) **e** coluna Abrir → mesmo destino |
| Proposta | Referência = texto; `—` nunca link; uma coluna Abrir (`RowAction`) |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-011 — Novo pagamento

| Campo | Conteúdo |
|---|---|
| Rota | `/payments/new` (+ G02 query) |
| Gap | UI `register_without_document` (decisão externa) |
| IDs | banner G02 com ids crus |
| Veredito | `FUNCTIONAL_NOT_READY` |

### SCR-012 — Pagamento e alocações

| Campo | Conteúdo |
|---|---|
| Rota | `/payments/:paymentId` |
| Ações | Alocar; FX; cancel Payment ausente (decisão externa) |
| IDs | `Pagamento {id}`, `Obrigação {id}`, elegíveis com fallbacks |
| Gap | `EligiblePayable.order_code` enrichment |
| Veredito | `FUNCTIONAL_NOT_READY` |

---

## 3. SCR-008 — taxonomia de filtros (combinável)

### Semântica backend (`payables_queue` / Python)

```text
status set     → Payable.status == status
status omitido → Payable.status != CANCELLED   # inclui PAID
due_before     → due_date <= due_before        # inclusivo
due_after      → due_date >= due_after         # inclusivo
pending=OVERDUE      → due_date < today ∧ status ∈ {OPEN, PARTIALLY_PAID}  # NÃO usar na UI nova
pending=OPEN_BALANCE → balance > 0 ∧ status ∈ {OPEN, PARTIALLY_PAID}
```

Date-only: `date.today()` no servidor.

### Status (somente `status`)

| Label | Valor | Default |
|---|---|---|
| Não canceladas | omitido | URL default de status |
| Aberta | `OPEN` | |
| Parcialmente paga | `PARTIALLY_PAID` | |
| Paga | `PAID` | |
| Cancelada | `CANCELLED` | |

Não usar “Ativas” nem “Todas” (BE omite CANCELLED no default). “Todas incluindo canceladas” = GAP_TECNICO.

### Vencimento (somente `due_before` / `due_after`)

| Label | Params |
|---|---|
| Todos os vencimentos | limpar `due_*` |
| Vencidas | `due_before = today - 1` |
| Vencem hoje | `due_after = due_before = today` |
| Próximos 7 dias | `due_after = today+1`, `due_before = today+7` |

### Saldo (própria; `pending` só OPEN_BALANCE)

| Label | Valor | Default |
|---|---|---|
| Todos | omit / sentinela FE `ALL` (não enviado à API) | |
| Com saldo em aberto | `OPEN_BALANCE` | **SIM (operacional)** |

### Pendências

- `MISSING_FX`: só display de linha; filtro = **GAP_TECNICO** (sem chip FE).

### Campos

| Label produto | Parâmetro |
|---|---|
| Moeda | `currency` |
| Pedido (ID) | `order_id` (não `order_code`) |
| Fornecedor | `supplier_id` (Select nome→id) |
| Fatura | `invoice_id` (defer) |

---

## 4. KPIs SCR-008 (comportamento definitivo)

| KPI | Clique |
|---|---|
| Vencido | filtro Vencidas (`due_before=today-1`) |
| Hoje | filtro Hoje (`due_*=today`) |
| Próx. 7d | filtro 7 dias |
| Saldo aberto | `pending=OPEN_BALANCE` |
| Pagamentos com residual | **navega** `/payments?unallocated_only=1` (não filtra AP) |

---

## 5. Matriz de filtros (filas)

| SCR | Grupo | Label (inspeção) | Parâmetro | Problema | Proposta |
|---|---|---|---|---|---|
| 003 | Status | Todos… | `status` | OK | manter |
| 006 | Status | Todas… | `status` | OK | manter |
| 008 | Status | Abertos | omitido | inclui PAID; label enganosa | Não canceladas |
| 008 | Pendência | Vencido | `pending=OVERDUE` | mistura tempo+status | Vencimento via `due_*` |
| 008 | Pendência | Saldo aberto | `OPEN_BALANCE` | grupo errado | grupo Saldo; default ON |
| 008 | — | — | `supplier_id` | API sem UI | Select |
| 010 | Residual | Todos / residual | `unallocated_only` | OK | manter |

---

## 6. Colunas SCR-008

| Coluna inspeção | Decisão |
|---|---|
| Vencimento + Atraso | Combinar |
| Fornecedor, Fatura, Pedido | Manter |
| Moeda | Remover |
| Valor | Manter |
| Alocado | Mover para drawer |
| Saldo | Manter |
| Taxa + BRL | Combinar `Câmbio / BRL` |
| Status, Pendências, Câmbio | Manter |

Ordem alvo 1366/1440: Vencimento · Fornecedor · Fatura · Pedido · Valor · Saldo · Câmbio/BRL · Status · Pendências · Câmbio.

---

## 7. Referências internas (IDs ao usuário)

Regra: **ID interno nunca é título principal.**

| Caso | Correção |
|---|---|
| `Pedido {id}` | code ou `—` |
| `Fatura {id}` | `invoice_number` ou `—` |
| `Obrigação {id}` | link “Ver obrigação” / venc.; enrichment BE |
| `Pagamento {id}` | ref ou data·fornecedor·valor |
| `Fornecedor {id}` | nome do catálogo |
| G02 banner ids | texto sem números crus |

---

## 8. Gaps funcionais remanescentes

| Gap | Destino |
|---|---|
| `register_without_document` UI (011) | Decisão externa |
| Cancel Payment (012) | Decisão externa |
| FLW-007 Faturas/Pagamentos | Campanha FE (`useListReturn`) |
| `EligiblePayable.order_code` | FE `—` + backlog BE |
| Filtro `MISSING_FX` | GAP_TECNICO BE |
| Sticky coluna | POLISH se overflow |

---

## 9. Matriz de ações (destaques)

| SCR | Ação | Tipo | Regra |
|---|---|---|---|
| 010 | Referência | texto | nunca link |
| 010 | Abrir | `RowAction` | única nav |
| 008 | KPIs V/H/7d/Saldo | filtro URL | wiring |
| 008 | KPI residual | navigate | payments |

Regra transversal: navegação = Link/RowLink/RowAction; mutação = Button; perigosa = Button danger.

---

## 10. Correções executáveis (C-001…C-021)

| ID | Pri | Classe | SCR | Resumo |
|---|---|---|---|---|
| C-001 | P0 | BLOCKER | 008 | Label Não canceladas |
| C-002 | P0 | BLOCKER | 008 | Vencimento só `due_*` |
| C-003 | P0 | BLOCKER | 008 | Grupo Saldo + default OPEN_BALANCE |
| C-004 | P1 | MAJOR | 008 | Labels gênero |
| C-005 | — | GAP | 008 | Sem chip MISSING_FX |
| C-006 | P1 | MAJOR | 008 | Colunas §6 |
| C-007 | P1 | MAJOR | 008 | Pedido (ID) |
| C-008 | P1 | MAJOR | 008 | Select fornecedor |
| C-009 | P0 | BLOCKER | 008 | KPIs wired |
| C-010 | P1 | MAJOR | 010 | Abrir único |
| C-011 | P1 | MAJOR | vários | Refs §7 |
| C-012…014 | P1 | MAJOR | 005/007/012 | mini-tables → OT |
| C-015 | P1 | MAJOR | 009 | Títulos |
| C-016 | P1 | MAJOR | 003 | Remover Moeda |
| C-017 | P2 | POLISH | filas | sticky condicional |
| C-018 | P2 | POLISH | vários | Links DS |
| C-019 | P1 | MAJOR | 001 | Prefill só dev/test |
| C-020 | P2 | POLISH | 008 | drawer CSS |
| C-021 | P1 | MAJOR | 006/010 | FLW-007 returnState |

---

## 11. Componentes compartilhados

| Componente | Consumidores | Nota |
|---|---|---|
| FilterBar / FilterChip | 003,006,008,010 | grupos Status/Vencimento/Saldo em 008 |
| KpiStrip | 005,008 | 008 com `onClick` |
| OperationalTable | filas + detalhes | stickyFirstColumn opcional |
| MoneyDisplay | filas/detalhes | moeda no valor |
| RowAction / RowLink | filas | Abrir 010; Câmbio 008 |
| DetailDrawer | 008 | ações + SummaryGrid |
| statusLabels / domainLabels | badges / pendências | PT sobre códigos EN |

---

## 12. Veredito por página (inspeção)

| SCR | Veredito |
|---|---|
| 001 | FUNCTIONAL_NOT_READY |
| 002 | READY |
| 003–007 | FUNCTIONAL_NOT_READY |
| 008 | STRUCTURAL_CONFLICT |
| 009–012 | FUNCTIONAL_NOT_READY |

**Global (no momento da inspeção):** `READY_FOR_EXTERNAL_REVIEW` = **REFUTADO**.

---

## 13. Fontes consultadas

- Código: `v2/frontend/src/App.tsx`, páginas Horizon A, `ui/*`, `index.css`
- Backend: `v2/app/billing/queries.py` (`payables_queue`), reporting, treasury routes
- Produto: Handoff UI/UX SCR-001…012, Blueprint UI/UX §21.2–§21.11 / §21.7, MCK-004
- Evidências: `docs/v2/etapa-9v/grupo-VF`, `grupo-V1-V2`

---

## 14. Encerramento do inventário

```
ETAPA
Inventário estrutural das 12 SCR Horizon A (documento)

STATUS
DONE

LINGUAGENS REGISTRADAS
TypeScript/TSX, CSS, Python, JSON/OpenAPI, Markdown; UI em PT-BR; enums de domínio em EN

READY_FOR_EXTERNAL_REVIEW (inspeção)
REFUTADO

ARTEFATO
docs/v2/etapa-9v/INVENTARIO_ESTRUTURAL_HORIZON_A.md
```
