# Legenda — MCK v0.4 Ciclo 2 remediação

Anotações **fora do viewport**. Checkpoints **C/D pendentes** de nova revisão externa.

## Problemas R1–R18

Todos **CONFIRMADOS** em v0.3 e **corrigidos** em v0.4 (ver relatório de entrega).

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
| `rebind_valuation` / `fx.valuation.rebind` | **Reatribuir avaliação cambial** (contrato: `POST /fx/valuations/{id}/rebind`) |
| `expected_version` | omitido na UI; só legenda |
| all-or-nothing | omitido na UI; lote atômico na legenda |
| RBAC | ação indisponível fica **oculta**; **403** só em acesso direto/deep link |

## Temporalidade artboards

| Mock | Momento |
|---|---|
| 001 / 002 / 003 / 004 / 005 / 007 | T0 |
| AUX pagamento registrado | T1 |
| 006 | T2 |
| AUX alocação confirmada | T3 |

## MCK-001 / MCK-004

Copiados de v0.3 sem regressão (A/B aprovados).

## Matriz AS-IS / TARGET / GAP

| Tema | Classificação |
|---|---|
| Cockpit read-only | AS-IS capacidade / TARGET visual |
| G02 AP→Payment | TARGET mock · GAP wiring |
| Docs sem página | GAP deep link |
| FX 3 visões + ausência ≠ 0 | AS-IS · TARGET layout |
| SCR-028 | omitido |
