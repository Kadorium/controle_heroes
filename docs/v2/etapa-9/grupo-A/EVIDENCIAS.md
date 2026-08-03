# Grupo A — Evidências

## 1. Estado inicial
- Branch `main`; WIP docs + I9-0 prévio preservados
- Roadmap 0.5.28 (I9-0 parcial com “Novo pedido” indevido na sidebar)
- `epic_v2_test` @ localhost:5433 **confirmado** (não `epic_v2`)

## 2. Incrementos executados
- **I9-0 fechamento:** removido “Novo pedido” da sidebar; nav = Compras (Pedidos, Faturas) + Financeiro (Contas a pagar, Pagamentos); sem `/fx`; grid CSS no `[role=group]`; CTA permanece “Nova ordem” na fila
- **I9-1:** `sanitizeNextPath` / `loginUrlWithNext`; redirect autenticado com `?next=`; login sem shell; refresh silencioso pós-login; erros credencial/rede

## 3. Hipóteses
| Hipótese | Veredito |
|---|---|
| Novo pedido na sidebar | **Refutada** (estava) → corrigido |
| E2E isolável em epic_v2_test | **Confirmada** |
| ?next= só FE | **Confirmada** |

## 4. Arquivos
**Alterados:** `AppShell.tsx`, `index.css`, `App.tsx`, `LoginPage.tsx`, `useAuth.tsx`, e2e inc5 + specs, Roadmap/README  
**Criados:** `safeNext.ts`, `safeNext.test.ts`, `e2e/i9-0-shell.spec.ts`, `e2e/i9-1-login-next.spec.ts`, este diretório evidências  
**Removidos:** item NavLink Novo pedido (sidebar)

## 5. Contratos
Nenhum backend alterado.

## 6. Testes
- Unit: **25 passed**
- Build/tsc: **PASS**
- E2E (`E2E_SPECS=i9-0-shell,i9-1-login-next`, db=`epic_v2_test`, port 8082): **3 passed**
- Logs: `logs/grupo-A-e2e.txt`, `logs/i9-0-e2e-shell.txt`

## 7–8. Visual
- 1366: `screenshots/i9-0-shell-1366.png` — shell TARGET, CTA na fila
- 1440: `screenshots/i9-0-shell-1440.png` — nav vertical OK após fix grid

## 9. Telas navegadas
Login → Pedidos → Faturas → Contas a pagar → Pagamentos; deep link `/payables` → login?next= → `/payables`

## 10–12. Regressões / correções
- Nav itens horizontais por falta de grid no wrapper a11y → CSS `[role=group]`
- Inc5 E2E apontava “Novo pedido” sidebar → CTA `main` “Nova ordem”

## 13. Dívidas
- Título página ainda “Ordens” (I9-2)
- CTA copy “Nova ordem” vs TARGET “Novo pedido” (I9-2/3)
- Focus trap / retorno scroll (I9-9)

## 14. Decisões técnicas
| Decisão | Hipótese | Evidência | Solução | Impacto | Rollback |
|---|---|---|---|---|---|
| Remover Novo pedido da nav | Spec TARGET | Matriz + Handoff | Só CTA na fila | E2E/inc5 | Restaurar NavLink |
| refresh silent pós-login | loading flash | App remonta | `refresh({silent:true})` | Auth UX | Remover flag |

## 15. Rollback
Diff WIP nos arquivos listados (§4); sem git revert.

## 16. Status do grupo
**DONE**

## 17. Condição para avançar
Gates A verdes → iniciar Grupo B.
