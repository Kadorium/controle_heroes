# J4-FIN FIN-1C-FIX-2 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1C-FIX-2** |
| Status | **DONE** |
| Data | **2026-08-11** |
| Runtime | `:8081` / `epic_v2` / **022** / Operação |
| Asset | **`index-WDdEsUif.js`** |
| Pytest | **473 passed** (ref. 471) |
| UI verify | [`J4_FIN1C_FIX2_UI.md`](J4_FIN1C_FIX2_UI.md) — agente percorreu; literais antes/depois |

---

## Entregas

### V1 — Vocabulário
- Nav/títulos/breadcrumbs: **Pagamentos realizados**
- Contas a pagar inalterado (canônico)
- Subtitle `/payments`: *Dinheiro que saiu do caixa — residual ainda não aplicado a Contas a pagar*
- Estado do pagamento: `crédito em aberto` / `parcialmente alocado` / `totalmente alocado` (lista, detalhe, cockpit)
- Guarda: sem “Contas pagas” / “Liquidados”

### V2 — Atritos
- Empty alocação: explica ausência de Fattura/Conta a pagar
- Atalho Cockpit → `#order-advances` (+ Cockpit na comercial)

### V3 — Sugestão BRL (guarda)
- `GET /api/fx/quotes/for-date?as_of=` — só o dia; missing sem vizinho
- UI: aviso **Sugestão do sistema (não é o extrato)**; botão aplicar; sobrescrevível; missing explícito
- **Não** autofill silencioso

---

## Fora (consciente)

Deep-link liquidação pedido (= FIN-2); demais atritos N3 de baixo ganho — ver UI.md.

---

## Ambiente

Order **31/589** limpo: CONFIRMED · 2 COMMITMENT · só Ordine · painel vazio.

## Próxima sugerida

FIN-1 **ACEITO** operacionalmente: registrar adiantamento real = **uso**, não gate.  
Campanha: **FIN-2** (aplicar crédito do pedido na Conta a pagar) quando o advisor autorizar; FIN-3/4 depois.

```text
DOC_DELTA
- Updated: FIX2 UI + handoff; ROADMAP 0.5.102; OrderAdvancesPanel; AppShell; payments/*; cockpit; fx for-date
- Evidence: J4_FIN1C_FIX2_UI.md; screenshots/fix2-*; logs/fin1c-fix2-*
- Roadmap status: 0.5.102 — FIX-2 DONE
- Next TODO: uso adiantamento real 589 e/ou FIN-2
- Return to advisor: J4_FIN1C_FIX2_ADVISOR_HANDOFF.md
```
