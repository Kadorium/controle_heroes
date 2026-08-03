# Fechamento — Onda D + polish + aceite Horizon A

**STATUS:** DONE técnico  
**Onda D:** DONE  
**Polish Horizon A:** DONE  
**Aceite visual interno:** ACCEPTED_WITH_MINOR_BACKLOG  
**Etapa 9 / 9V:** DONE  
**Inc-6:** TODO · Order-to-Pay: IN_PROGRESS  

## Bundle

| Momento | JS (B) | CSS (B) |
|---|---|---|
| D0 before | 282648 | 22735 |
| D6 after | 290180 | 24230 |

Delta JS ≈ +7532 (~+2.7%) · CSS ≈ +1495 · **0 deps novas** · 0 API resize.

## Hipóteses

| ID | Veredito |
|---|---|
| H-CAMP-1 Sem GET payable by id | CONFIRMADA → fechada em D0.5 |
| H-CAMP-2 get_payable domínio | CONFIRMADA |
| H-CAMP-3 Scan≤100 FX | CONFIRMADA → eliminado |
| H-CAMP-4 billing:read + PayableResponse | CONFIRMADA |
| H-CAMP-5 Rota fina sem migration | CONFIRMADA |

## Checkpoints

| CP | Resultado |
|---|---|
| D0 harness `e2e:horizon-a` | PASS |
| D0.5 GET `/api/payables/{id}` | PASS (pytest + FE) |
| D1 details RO + CQ | PASS |
| D2 forms + parcial create + 409 | PASS |
| D3 cancel / without-doc / retorno / idempotency | PASS |
| D4 limpeza + suíte | PASS |
| D5 polish objetivo | PASS |
| D6 aceite | ACCEPTED_WITH_MINOR_BACKLOG |

## Gates

- Vitest **58p**
- pytest `test_get_payable_by_id` PASS
- tsc + build PASS
- `npm run e2e:horizon-a` **18p** (Horizon A + adaptive B/C/D) @ `epic_v2_test:8082`
- Scan FX eliminado (`getPayable`)
- Create ≠ Allocate preservado
- Cockpit RO absoluto

## OT `children` (inventário D4)

**API `columns`:** ApQueuePage, OrdersListPage, InvoicesListPage, PaymentsListPage.

**API `children` (mini-tabelas — preservar):** OrderCockpitPage, OrderCreatePage, OrderDetailPage, InvoiceDetailPage (+ OrderInvoicesPanel), PaymentDetailPage, InvoicesListPage (drawer/mini), testes foundation. Sem LegacyTable/V2.

## MINOR_BACKLOG (não bloqueia)

- Decomposição InvoiceDetail (~860 LOC) para orquestrador ≲350 — adiada sem regressão funcional
- `row-highlight` Pagamentos (cosmético)
- Aceite visual externo SCR-008 / refinamentos subjetivos tipográficos
- Hub FX SCR-028 (fora Horizon A)
- Virtualização de filas

## Matriz SCR (resumo)

| SCR | Funcional | Adaptativo | Polish | Veredito |
|---|---|---|---|---|
| 001 Login | OK | n/a | OK (sem reabrir) | ACCEPTED |
| 002 Shell | OK | rail/CQ | OK | ACCEPTED |
| 003 Pedidos | OK | Onda C | OK | ACCEPTED |
| 004 Novo pedido | parcial create | form-grid | OK | ACCEPTED |
| 005 Cockpit | RO | detail-shell | OK | ACCEPTED |
| 006 Faturas | OK | Onda C | OK | ACCEPTED |
| 007 Fatura | cancel/without-doc/409 | detail-shell | OK | ACCEPTED |
| 008 AP | OK | piloto | OK | APPROVED_FOR_PROGRESSION |
| 009 FX | getPayable | CQ fx-shell | OK | ACCEPTED |
| 010 Pagamentos | OK | Onda C | OK | ACCEPTED |
| 011 Novo pagamento | without-doc | form-grid | OK | ACCEPTED |
| 012 Pagamento | cancel/idempotency | detail-shell | OK | ACCEPTED |

## Evidências

- Screenshots: `screenshots/` (D1 cockpit/FX; VF 12 SCR rebaseline via `i9v-vf-12scr`)
- Log E2E: suite horizon-a 18p
- Inventário D0: `INVENTARIO_D0.md` (hipóteses H-CAMP atualizadas abaixo)

### H-CAMP pós-D0.5

| ID | Atualização |
|---|---|
| H-CAMP-1 | FECHADA — rota HTTP existe |
| H-CAMP-3 | FECHADA — `PayableFxPage` usa `getPayable` |
| H-CAMP-5 | CONFIRMADA |
