# J4-FIN-CICLO — ciclo financeiro integral + custo BRL

| Campo | Valor |
|---|---|
| Etapa | **J4-FIN-CICLO** (O1–O6; O5/O6 só relatório) |
| Status | **DONE** |
| Data | **2026-08-12** |
| Runtime | `:8081` / `epic_v2` / Alembic **023** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-BaRAqabE.js`** |
| Pytest | **496 passed** (ref. 492 + 4 em `test_j4_ciclo.py`) |
| Chromium | Chrome/144.0.7559.236 · Electron/40.10.3 · Cursor/3.14.7 |
| Sample | **`TESTE-CICLO-001` id 34 permanece** em `epic_v2` (não apagar) |
| Preservado | Pedido **589** id **31** — CONFIRMED, 2 COMMITMENT, zeros |

---

## 1. O que foi o ciclo

Pedido fictício **TESTE-CICLO-001** (fornecedor id **27** `TESTE - nao e compra real (CICLO 2026-08-12)`, SKU catálogo `8057628953586` id **19**, **10.000 PZ @ EUR 60,00 = 600.000**). Notas no pedido deixam explícito: não é compra real; não confundir com 589/Heroe's.

| Fatura | Como | Qty @ preço | Líquido | Vencimentos |
|---|---|---|---|---|
| T-001 | Manual, emitir sem documento | 2.000 @ 60,00 | 120.000 | 36.000 20/03 + 84.000 20/05 |
| T-002 | Manual, emitir sem documento | 3.000 @ 60,00 | 180.000 | 90.000 15/05 + 90.000 15/07 |
| 244 | PDF Policy A + `order_id=34` | 50+150 @ 99,83 | 19.966 | 5.000 20/04 + 14.966 30/06 |
| T-003 | Manual, emitir sem documento | 4.800 @ 62,50 | 300.000 | 300.000 01/08 |

Adiantamentos: **120.000 @ 5,80** (pago 15/01, FX 14/01) + **60.000 @ 6,15** (pago 10/02, FX 09/02) = EUR 180.000 · BRL **1.065.000** · ponderado **5,916667** (não média simples 5,975).

Saldos: 30.000 @ 6,20 · 90.000 @ 5,95 · 5.000+14.966+300.000 @ 6,40.

**Disponível fecha em 0.** Faturado **619.966 > 600.000** (qty OK; valor estoura — **relatado, não corrigido**).

Heroe's id **26**, SKU `8057628953586` e pedido **31/589** não foram alterados.

O que tornou o sample óbvio: código `TESTE-CICLO-001`, fornecedor com “TESTE” + “nao e compra real” + data, notas no cabeçalho, não é o 589.

---

## 2. O2 — custo BRL (o que estava errado e o que mudou)

O buraco **não** era `payable_fx_view` somar só o último pagamento. A view já soma `FxAllocationValuation.realized_brl` (P&L congelado). O furo era **antes**: `allocate_payment` criava `PaymentAllocation` e **não** criava `FxExecutionAllocation`. O câmbio do adiantamento ficava no `Payment` + `FxExecution` e não aparecia na obrigação.

Correção (não é arquitetura nova): depois do `flush` das alocações novas, se o pagamento **já tem** `FxExecution`, chama `link_execution_allocation` (rateio BRL = `execution.brl_amount * (fa / execution.foreign_amount)`). **Não** auto-liga em `register_execution` — isso quebraria Inc-4 (alocar → FX → link explícito).

Custo ≠ P&L:

- **Custo BRL** = soma de `FxExecutionAllocation.brl_amount` (obrigação) ou soma de `FxExecution.brl_amount` dos pagamentos REGISTERED do pedido (cockpit, inclusive adiantamento ainda não alocado).
- **`realized_brl`** permanece soma das valuations (Inc-4). As três visões planejado / mercado / P&L **não** foram apagadas.

KPI do cockpit: **“FX realizado” removido** (era resultado vs taxa planejada, não caixa). No lugar: **“Custo BRL”** com hint “Soma dos câmbios deste pedido. Não é média × EUR.”

Prova numérica (T-001, adiantamento 120.000 @ 5,80):

| Parcela | EUR | BRL |
|---|---|---|
| 20/03 | 36.000 | **208.800** |
| 20/05 | 84.000 | **487.200** |
| Soma | 120.000 | **696.000** |

T-002 primeira parcela: 60.000 @ 6,15 + 30.000 @ 6,20 = **555.000** (não média × 90.000).

Pedido fechado: EUR **619.966** · BRL **3.834.282,40** · ponderado **6,184666**.

---

## 3. Walk A–H (o que a tela mostrou)

Login `admin@epic.com.br`. Pedido criado via API (SKU fora da lista de 50 do formulário; file picker MCP não seleciona PDF). Adiantamentos **na UI**. T-001 emitida via API (qty do rascunho copiava 10.000 — operador teria de reduzir; **não corrigido**). Crédito da parcela 36.000 **na UI**. Resto (T-002, 244, T-003, saldos) via API com o mesmo contrato da UI, depois conferência nas telas.

| CP | O que conferir | Resultado |
|---|---|---|
| A | Pedido 600.000, faturado 0, pago 0, disponível 10.000 | PASS — cockpit + comercial |
| B | Adiantamento 1: 120.000 / 696.000 / 5,80 | PASS — UI |
| C | Ambos: 180.000 / 1.065.000 / **5,916667** | PASS — painel e cockpit Custo BRL 1.065.000 **antes** de alocar |
| D | T-001 emitida; 36.000 + 84.000; disponível **8.000** | PASS — faturado 120.000; alertas de vencido esperados (datas no passado) |
| E | Aplicar crédito **na mão** (nunca sozinho); crédito cai; cockpit reflete | PASS — parcela 22 Pago; custo **208.800**; crédito 120.000 → 84.000 |
| F | T-002 → disponível 5.000; 244 PDF; T-003 → **0**; faturado 619.966 | PASS — comercial 10.000 / 10.000 / 0; Invoice 244 qty+preço do PDF |
| G | Saldos 6,20 / 5,95 / 6,40 até fechar | PASS — API + tela parcela 24 = **555.000** |
| H | Da tela: EUR, BRL verdadeiro (soma), média da operação | PASS — Pedido 600.000 · Faturado/Pago 619.966 · Custo BRL **3.834.282,40** · ponderado **6,184666** |

589: **antes** (A) e **depois** (H) iguais: Confirmado · 830.000 · zeros · só Ordine. Meio (após T-002) não teve screenshot dedicado — o lote T-002/244/T-003 foi API; o 589 não foi tocado (GET `/api/orders/31/summary` no meio do script: zeros).

Shots: `docs/v2/etapa-j4-fin/screenshots/ciclo-*`.

---

## 4. Pedido 589

Intocável. Antes, API no fechamento, e UI depois: id **31**, CONFIRMED, 2 COMMITMENT (14.600 + 2.000), faturado/pago/adiantado/custo **0**, uma fatura nenhuma, um pagamento nenhum, documento `Ordine_589 (1) (1).pdf`. Heroe's id **26** intacto.

---

## 5. Atrito e defeitos (não O2)

Relatar; **não** corrigir nesta fatia, salvo o que já era O2.

1. **Fatura avulsa copia a qty integral do pedido** (`create_invoice`). T-001 nasceu com 10.000; o operador (ou a API) reduz no DRAFT. O PDF 244 já usa qty do documento (FIN-3B).
2. **File picker MCP** não anexa PDF. Ingestão 244 e FX de saldo: API. Na UI, FX do saldo **exige PDF** (`PaymentFxPanel`); admin no adiantamento pode sem arquivo.
3. **Painel FX não recarrega** depois de “Aplicar neste vencimento”. A alocação e o auto-link gravaram (API: 208.800); a faixa “Custo BRL” ficou 0,00 até F5. O painel de crédito atualiza; o de câmbio não.
4. **Flash “Nenhum crédito”** no primeiro paint do painel de crédito (lista começa vazia).
5. **`list_order_advances` inclui pagamentos de saldo** com `order_id`. No comercial, “Total adiantado” virou **619.966** (tudo que saiu do caixa), não só os 180.000 de adiantamento. O número BRL coincide com o custo verdadeiro; o **rótulo mente**.
6. **KPI “Exposição FX”** está rotulado BRL e mostra saldo aberto **EUR** (120.000 no checkpoint D).
7. **Faturado 619.966 > pedido 600.000** — qty 10.000 fecha; valor estoura por 244 @ 99,83 e T-003 @ 62,50. Relatado, não bloqueado.
8. T-003 manual **não** gerou o mesmo rastro de auditoria de preço que a Fattura 244.

Nada pior que O2 (crédito não vazou para o 589; qty ISSUED do sample fechou; 589 intacto).

---

## 6. O5 / O6 — só relatório (não construir)

### O5 — 589 + Fattura

Pedido CONFIRMED com só COMMITMENT **não aceita** incluir SKU. Fattura → `fattura_no_billable_lines` / “nenhuma linha faturável”. Cancelar perde o 589. Não há compromisso→produto. Tamanho **GRANDE** = **J#5-REC**. Roadmap §0.3 item 1 já mapeia. Fora desta fatia.

### O6 — ORDER_SCHEDULE

Achados FIN-1C: condições no Order → `Payable.source_type=ORDER_SCHEDULE`; a Fattura **substitui** a previsão do valor faturado; adiantamento **pago não é substituído**; `PaymentTerm` hoje é só da Invoice; Ordine 589 **não tem** texto de pagamento. Não construir. **FIN-4 encolhe para cronograma no pedido.**

---

## 7. Juízo honesto — o Ricardo opera isso no mês 1?

**Num pedido com SKU de catálogo, sim, com atrito.** Ele registra adiantamento (taxa + datas), emite fatura (se lembrar de **cortar a quantidade** no rascunho, ou se vier PDF Policy A), aplica crédito **clicando** em cada vencimento, paga o saldo, e o cockpit passa a mostrar reais gastos = soma dos câmbios — não média × euro. O ciclo TESTE-CICLO-001 fechou: disponível 0, obrigações 0, custo BRL batendo com a soma.

**No 589, não.** Trava no faturar (compromisso sem produto). Isso não mudou.

O que ainda impede “mês 1 sem muleta”: cronograma no pedido (FIN-4); fatura avulsa copiando qty do pedido; FX de saldo preso a PDF na UI; painel de adiantamento misturando saldo; câmbio da obrigação que não atualiza após aplicar crédito; 589 sem SKU.

Não está pronto para a compra Heroes real do 589. Está pronto para **ensaiar o caixa** num pedido fabricado com produto — e o número de reais deixou de mentir.

---

## Gates

| Gate | Resultado |
|---|---|
| Pytest V2 | **496 passed** — `logs/ciclo-pytest-full.txt` |
| O2 auto-link + cost_brl | 4 testes em `v2/tests/test_j4_ciclo.py` (sem xfail) |
| Inc-4 / SC-01/02 / FIN-3B | Intactos (suite completa) |
| UI A–H | PASS (API onde file picker / qty-copy) |
| 589 preservado | PASS — antes e depois |
| Sample | **Permanece** (pedido 34, fornecedor 27, invoices 25–28) |
| Alembic | **023** inalterado |

## Decisões (não reabrir)

- Custo = soma dos câmbios; P&L fica nas valuations.
- Auto-link só em `allocate_payment` se a execução já existe.
- KPI “FX realizado” sai da faixa do cockpit.
- TESTE-CICLO-001 **não** se apaga.
- FIN-4 daqui pra frente = **cronograma Order**, não custo BRL.

## Recomendação

Aceitar J4-FIN-CICLO. Próxima autorizável: **FIN-4 cronograma**. Não iniciar J#5-REC / 3A / 020 / J#6.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (0.5.108); v2/app/treasury/commands.py; v2/app/treasury/fx_queries.py; v2/app/reporting/queries.py; v2/frontend OrderCockpitPage.tsx, FxPanels.tsx, fxApi.ts, OrderAdvancesPanel.tsx, PayableOrderCreditPanel.tsx; v2/tests/test_j4_ciclo.py
- Evidence: docs/v2/etapa-j4-fin/J4_CICLO_INTEGRAL.md; screenshots/ciclo-*; logs/ciclo-pytest-full.txt; logs/ciclo-walk-continue.json
- Roadmap status: 0.5.107 → 0.5.108 (FIN-CICLO DONE; FIN-4 = só cronograma)
- Next TODO: FIN-4 (cronograma no pedido) quando autorizado
- Return to advisor: docs/v2/etapa-j4-fin/J4_CICLO_INTEGRAL.md
```
