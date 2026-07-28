# Legenda — MCK v1.0 (aprovado)

Anotações **fora do viewport**. Checkpoints **A–D APROVADOS**.

## Status

| Item | Valor |
|---|---|
| Versão | **MCK v1.0** |
| UI/UX | **v3.6** (§25) |
| Etapa 5 | **DONE** |
| Família visual | aprovada |
| Mockup ≠ implementação | explícito |

## Ajustes editoriais v0.4 → v1.0

| Mock | Correção |
|---|---|
| 002 | pedido inteiro; Pago por alocação; Abrir Câmbio da obrigação |
| 003 | Disponibilidade no pedido; Prévia da emissão; removido helper de contorno |
| 005 | Origem: contas a pagar |
| 006 | Prévia da alocação; removida nota de AUX |
| 007 | título **Câmbio da obrigação**; Resultado cambial realizado |

## Códigos técnicos (não na UI)

| Domínio | UI |
|---|---|
| `issue Invoice` | Fatura emitida |
| `fx.plan INITIAL` | Plano cambial criado · INITIAL |
| `NONE` | Sem desconto |
| `PERCENT` | Percentual |
| `ISSUED` | Emitida |
| `due_date` | Data de vencimento |
| `REFORECAST` | Replanejar |
| `CORRECTION` | Corrigir plano |
| `rebind_valuation` | Reatribuir avaliação cambial |
| `expected_version` | omitido na UI |
| all-or-nothing | omitido na UI |
| PnL | Resultado cambial realizado |
| FX Workspace | Câmbio da obrigação |
| RBAC | ação indisponível oculta; 403 só deep link |

## Temporalidade

| Mock | Momento |
|---|---|
| 001 / 002 / 003 / 004 / 005 / 007 | T0 |
| AUX pagamento registrado | T1 |
| 006 | T2 |
| AUX alocação confirmada | T3 |

## AS-IS / TARGET / GAP (resumo)

| Tema | Classificação |
|---|---|
| Cockpit read-only | AS-IS capacidade / TARGET visual |
| G02 AP→Payment | TARGET mock · GAP wiring |
| Docs/audit deep link | GAP |
| Enrichment Orders | GAP read model |
| FX 3 visões + ausência ≠ 0 | AS-IS · TARGET layout |
| SCR-028 hub | omitido · GAP |
| Fallback reporting:read | legenda |

Gaps técnicos seguem para **Etapa 9** (plano de implementação). Design System = **Etapa 7**.
