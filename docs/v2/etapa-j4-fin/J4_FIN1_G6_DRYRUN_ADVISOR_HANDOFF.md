# J4-FIN FIN-1-G6-DRYRUN — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1-G6-DRYRUN** |
| Status | **DONE** |
| Data | **2026-08-11** |
| Runtime | `:8081` / `epic_v2` / Alembic **022** / `index-CZIF-k93.js` / Operação |
| Código produto | **ZERO** alteração nesta fatia |

---

## O que foi feito

Agente percorreu o roteiro G6 **inteiro pela UI** (valores de teste), registrou textos literais, anotou atrito/divergências **sem consertar**, e **limpou** o Order 31.

Detalhe narrativo: [`J4_FIN1_G6_DRYRUN.md`](J4_FIN1_G6_DRYRUN.md).

---

## Gates do ensaio

| # | Cobertura | Resultado |
|---|---|---|
| Pré-voo | health 022 + asset + painel vazio | PASS |
| 1 | EUR + taxa → BRL derivado | PASS |
| 2 | EUR + BRL → taxa derivada | PASS |
| 3 | Consolidado soma EUR/BRL + médio ponderado | PASS |
| 4 | Cancel: foco Motivo; teclado harness PARCIAL | PASS produto / PARTIAL harness |
| 5 | Badge `Cancelado` + residual `—` | PASS |
| 6 | Consolidado recalcula | PASS |
| 7 | Cockpit Adiantado / Pago 0 / lista do 589 | PASS |
| 8 | Payables order 31 = zero títulos | PASS |
| 9 | Com PDF e sem PDF | PASS |
| Limpeza | payments 0 · só Ordine · CONFIRMED 2 linhas | PASS |

---

## Divergências (resumo)

- **MINOR:** datas do formulário não limpam após registrar.
- **MINOR:** dois file inputs na comercial (pedido vs câmbio).
- **MINOR/harness:** Tab/Enter no modal de cancel sob Browser MCP incompleto; foco Motivo OK.
- **Nenhum BLOCKER** antes do G6 Ricardo.

---

## Ambiente

Order **31 / 589**: `CONFIRMED`, 2 COMMITMENT, PDF Ordine. Painel `Nenhum adiantamento registrado`. Cockpit `Adiantado (crédito) EUR 0,00` · `Nenhum pagamento`.

---

## Recomendação

**Liberar G6 Ricardo** com valores reais do extrato — roteiro [`J4_FIN1_G6_ROTEIRO.md`](J4_FIN1_G6_ROTEIRO.md).  
FIX-2 (limpar datas / atrito upload) **opcional pós-G6**, não gate.

```text
DOC_DELTA
- Updated: J4_FIN1_G6_DRYRUN.md; J4_FIN1_G6_DRYRUN_ADVISOR_HANDOFF.md; ROADMAP 0.5.100; G6_ROTEIRO nota
- Evidence: screenshots/g6-dryrun-*; logs/fin1_g6_dryrun_*
- Roadmap status: 0.5.100 — dryrun DONE; next = G6 Ricardo
- Next TODO: G6 Ricardo valores reais 589
- Return to advisor: J4_FIN1_G6_DRYRUN_ADVISOR_HANDOFF.md
```
