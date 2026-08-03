# Grupo D — Evidências

## 1. Estado inicial
- Grupos A–C **DONE**; retorno/a11y pendentes; CSS duplicado skip-link

## 2. Incrementos
- **I9-9** `returnState` + `useListReturn`; Pedidos com `?status=` na URL; `location.state.returnTo`; focus trap + Escape em ConfirmationModal/DetailDrawer; skip-link; row selected
- **I9-10** consolidação: suite E2E Horizon A; façades preservadas; CSS órfão skip duplicado removido; sem remoção agressiva de `.data-table`/`.btn` (ainda consumidores)

## 3. Hipóteses
| Hipótese | Veredito |
|---|---|
| sessionStorage sozinho basta no breadcrumb | **Parcial** ? complementar com `location.state.returnTo` |
| Fila CONFIRMED vazia no DB fresco | **Confirmada** ? E2E cria pedido primeiro |

## 4. Arquivos
**Criados:** `navigation/returnState.ts`, `returnState.test.ts`, `useListReturn.ts`, `ui/useFocusTrap.ts`, `e2e/i9-grupo-d.spec.ts`  
**Alterados:** ConfirmationModal, DetailDrawer, OrdersListPage, OrderCockpitPage, ApQueuePage, index.css  
**Removidos:** CSS skip-link duplicado

## 5. Contratos
Nenhum backend.

## 6. Testes
- Unit **28 passed**
- Build PASS
- E2E `i9-grupo-d` PASS; suite Horizon A (shell+login+B+C+D) — ver `logs/horizon-A-e2e.txt`

## 7–8. Visual
- 1366: `i9-9-orders-filter-1366.png`
- 1440: `i9-10-ap-1440.png`

## 9. Telas
Login ? Novo pedido (Escape modal) ? Cockpit ? Pedidos filtrados ? retorno com query ? AP

## 10–12. Regressões
- Breadcrumb perdia query ? `state.returnTo` + sessionStorage

## 13. Dívidas
- Retorno linha/scroll em Invoices/Payments ainda parcial
- Virtualização; SR completo; L-005; ACCONTO; SCR-028; Inc-6
- Cockpit embed comercial (escrita) = dívida leve RO

## 14. Decisões
| Decisão | Hipótese | Evidência | Solução | Impacto | Rollback |
|---|---|---|---|---|---|
| returnTo via location.state | session only | E2E falhou | state + session | FLW-007 | remover state |
| Não apagar `.data-table` | legado | ainda usado Invoice/Order detail | preservar | — | — |

## 15. Rollback
Diff WIP §4.

## 16. Status
**DONE**

## 17. Avançar
Horizon A implementado ? revisão externa antes de nova fatia.
