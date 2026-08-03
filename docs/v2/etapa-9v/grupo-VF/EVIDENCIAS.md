# Etapa 9V — Grupo VF · Evidências

**Data:** 2026-07-29  
**Veredito interno:** `READY_FOR_EXTERNAL_REVIEW`  
**Aceite visual:** `PENDING_EXTERNAL_REVIEW` (não declarar `VISUAL_ACCEPTED`)  
**Banco E2E:** exclusivamente `epic_v2_test`

## Escopo

Finalização visual real das 12 SCR Horizon A (Checkpoints A–E): fundação DS, filas, detalhes, formulários, estados por aplicabilidade, comparação MCK e suíte completa.

## Gates

| Gate | Resultado |
|---|---|
| Unit (`vitest`) | **49 passed** |
| Typecheck + build | **OK** |
| E2E Horizon A @ `epic_v2_test` | **15 passed** (shell, login-next, grupos B–D, V0, V1-V2, VF-12scr, Inc-1…Inc-5) |
| Backend / migration | **Nenhuma alteração** neste ciclo VF |
| Teclado / Escape / retorno | Exercitado em I9-9 / drawer / modais |

Log: [`logs/grupo-VF-e2e.txt`](logs/grupo-VF-e2e.txt)

## Matriz SCR × veredito interno

| SCR | Ref MCK | Shell | Hierarquia | Componentes | Form | Table | Conteúdo | 1366 | 1440 | Veredito |
|---|---|---|---|---|---|---|---|---|---|---|
| 001 Login | análogo | sem shell | card | FormField/TextInput/Button | DS | — | PT | ✓ | ✓ | READY |
| 002 Shell | transversal | 220px | grupos | roleLabel/Button | — | — | PT | ✓ | ✓ | READY |
| 003 Pedidos | MCK-001 | ✓ | header+chips | FilterChip/OT/Pagination | — | standard | formatado | ✓ | ✓ | READY |
| 004 Novo pedido | análogo | ✓ | cards | SectionCard/MoneyInput | DS | linhas | sem null/DRAFT | ✓ | ✓ | READY |
| 005 Cockpit | MCK-002 | ✓ | 3 cards | Notice/mini-table/ADB | RO | mini | PT | ✓ | ✓ | READY |
| 006 Faturas | análogo | ✓ | como 003 | FilterChip/OT | — | standard | formatado | ✓ | ✓ | READY |
| 007 Fatura | MCK-003 | ✓ | sections | editors feature + DS | DS | OT | formatado | ✓ | ✓ | READY |
| 008 AP | MCK-004 | ✓ | KPI+drawer | chips/SummaryGrid | — | finance 44 | G02 | ✓ | ✓ | READY |
| 009 FX | MCK-007 | ✓ | 3 cards | RateInput/SectionCard | DS | — | sem nota técnica | ✓ | ✓ | READY |
| 010 Pagamentos | análogo | ✓ | chips | FilterChip/OT | — | standard | formatado | ✓ | ✓ | READY |
| 011 Novo pagamento | MCK-005 | ✓ | card | FileUpload/MoneyInput | DS | — | G02 legível | ✓ | ✓ | READY |
| 012 Pagamento | MCK-006 | ✓ | SummaryGrid | MoneyInput/FileUpload | DS | eligible | Create≠Alloc | ✓ | ✓ | READY |

## Estados por SCR (aplicabilidade)

| SCR | Aplicáveis | Exercitados | Não aplicáveis | Evidência |
|---|---|---|---|---|
| 001 | loading/busy, error, disabled, focus | busy+error login; focus inputs | empty/no-results/409/selected | e2e login-next + SCR-001 shots |
| 002 | hover/focus/active nav | active em rotas aninhadas | empty/409 | i9-0 + SCR-002 |
| 003 | loading, empty, hover, selected, focus | empty filter; selected row | 409 emit | OrdersList + I9-9 |
| 004 | busy, error, disabled, focus | anti-duplo-submit; validação | selected fila | OrderCreate + Inc-1 |
| 005 | loading, empty alerts, error | loading+empty alerts | forms/409 write | Cockpit + Inc-5 |
| 006 | loading, empty, focus | empty filter | 409 | InvoicesList |
| 007 | loading, error, blockers Notice, disabled RO, busy, 409 via version | blockers+readonly+issue | selected fila | InvoiceDetail + Inc-2 |
| 008 | loading, empty, error+retry, selected, hover | drawer selected; empty filter | form write | AP + G02 |
| 009 | loading, error, busy, focus | plan/quote save | allocation | FX panel + Inc-4 |
| 010 | loading, empty, hover residual | residual chip | 409 | PaymentsList |
| 011 | busy, error, disabled, focus | file required; anti-duplo | selected | PaymentCreate + G02 |
| 012 | loading, empty elegíveis, error, busy, confirm | alloc preview; error over-alloc | — | PaymentDetail + Inc-3/4 |

## Screenshots (24)

Diretório: [`screenshots/`](screenshots/)

- `scr-001-login-{1366,1440}.png`
- `scr-002-shell-{1366,1440}.png`
- `scr-003-orders-{1366,1440}.png`
- `scr-004-order-new-{1366,1440}.png`
- `scr-005-cockpit-{1366,1440}.png`
- `scr-006-invoices-{1366,1440}.png`
- `scr-007-invoice-{1366,1440}.png`
- `scr-008-ap-{1366,1440}.png`
- `scr-009-fx-{1366,1440}.png`
- `scr-010-payments-{1366,1440}.png`
- `scr-011-payment-new-{1366,1440}.png`
- `scr-012-payment-{1366,1440}.png`

## Componentes criados / adaptados

**Novos:** SectionCard, SummaryGrid, FormField, TextInput, SelectField, MoneyInput, RateInput, DateInput, FileUpload, Notice, PaginationSummary, RowAction, AuditDocumentsBlock  

**Adaptados:** Button (+danger), OperationalTable (sticky/zebra), EmptyState/ErrorState, AppShell (NavLink sem `end`, roleLabel), index.css (sidebar 220, dedup filter-bar, tokens)

## Consumidores legados remanescentes

- Classes `.btn` / `.data-table` / `.info-banner` ainda existem no CSS para compat transitória; superfícies Horizon A migradas para DS.
- `PayablesListPage` básica (não-SCR-008) permanece como fallback sem reporting.

## Pendências / fora de escopo

- Aceite visual externo
- Inc-6
- L-005, ACCONTO, comprador × Treasury, SCR-028
- Gap: `Pedido {id}` em elegíveis quando `order_code` ausente (boundary treasury↛orders)

## Próxima etapa lógica

Revisão externa das 24 screenshots + matriz → promoção ou ajustes pontuais. **Não** iniciar Inc-6 neste fechamento.
