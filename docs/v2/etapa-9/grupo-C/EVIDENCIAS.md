# Grupo C — Evidências

## 1. Estado inicial
- Grupo B **DONE**; sem backend autorizado neste grupo
- AP com drawer/CTA sem query; PaymentsPages monolítico; FX em `/payables/:id/fx`

## 2. Incrementos
- **I9-6** G02: CTA drawer ? `/payments/new?supplier_id&payable_id&amount&currency&order_id`; banner manual se ausente
- **I9-7** Split `PaymentsListPage` / `PaymentCreatePage` / `PaymentDetailPage`; DS; preview Allocation + ConfirmationModal; residual explícito
- **I9-8** PayableFxPage TARGET (3 colunas planejado/mercado/realizado); sem `/fx`; FX?liquidação

## 3. Hipóteses
| Hipótese | Veredito |
|---|---|
| Payment create reduz Payable | **Refutada** (E2E saldo igual pós-create) |
| Allocation reduz saldo | **Confirmada** |
| Asserções FX online estáveis | **Refutada** (cotação live) ? assert só realizado |

## 4. Arquivos
**Criados:** `PaymentsListPage.tsx`, `PaymentCreatePage.tsx`, `PaymentDetailPage.tsx`, `e2e/i9-grupo-c.spec.ts`  
**Alterados:** `ApQueuePage.tsx`, `PaymentsPages.tsx` (façade), `PayableFxPage.tsx`, `FxPanels.tsx`, `index.css`, E2E inc3/inc4  
**Removidos:** corpo monolítico de PaymentsPages (substituído por re-exports)

## 5. Contratos
Nenhum backend alterado.

## 6. Testes
- Unit 25p · build PASS
- E2E `i9-grupo-c,inc3-treasury,inc4-fx` @ `epic_v2_test`: **3 passed**
- Log: `logs/grupo-C-e2e.txt`

## 7–8. Visual
- 1366: `i9-6-ap-1366.png`, `i9-7-payment-new-g02-1366.png`, `i9-8-fx-1366.png`
- 1440: `i9-7-payments-1440.png`

## 9. Telas
AP drawer ? Novo pagamento (G02) ? Detalhe ? Allocation ? FX obrigação ? Pagamentos

## 10–12. Regressões
- Residual regex frágil com `MoneyDisplay` currency prefix ? assert `EUR N`
- FX online PnL dependente de mercado ? assert realizado -40

## 13. Dívidas
- Focus trap / Escape / retorno scroll = I9-9
- `register_without_document` UI; cancel payment; supplier name na lista payments
- L-005 aberto

## 14. Decisões
| Decisão | Hipótese | Evidência | Solução | Impacto | Rollback |
|---|---|---|---|---|---|
| Split Payments | god file | plano I9-7 | 3 arquivos + façade | imports estáveis | reunir exports |
| G02 query string | GAP confirmado | Handoff/UIUX | URLSearchParams no CTA | FLW-003 | link bare |

## 15. Rollback
Diff WIP §4.

## 16. Status
**DONE**

## 17. Avançar
Gates C verdes ? Grupo D.
