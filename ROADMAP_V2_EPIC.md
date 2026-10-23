# EPIC Controle V2 — Roadmap operacional

> Produto: [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md) · Índice: [`docs/README.md`](docs/README.md) · Snapshot imutável: [`docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md`](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md) · Método: [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc)

---

# Parte A — Painel

| Campo | Valor |
|---|---|
| Atualizado em | 2026-10-23 |
| Última entrega | Estoque por modalidade e família, quantidade, custo por origem, preço e venda potencial; visões pessoais e demonstração populada, com recuperação |
| Próxima entrega | Conferir a apresentação no laptop e ratificar as regras econômicas antes do uso operacional; melhorar a densidade da consulta |
| Detalhe técnico | Parte B, abaixo |

## A.1 Quanto está pronto

```
Cadeia ponta a ponta   ██████████  100%  a compra fecha no pedido
Ciclo financeiro       ██████████  100%  adiantamento, quitação, fatura, câmbio, cronograma
Ingestão               ██████████  100%  pipeline, pedido, packing, declaração, numerário, fatura e planilha
Logística              ██████████  100%  embarque na mão e packing preenche volumes
Aduana / estoque       ██████████  100%  PDF preenche; numerário se paga no tesouro
Custo desembarcado     ██████████  100%  mercadoria, impostos e despesas numa compra real
Painel gerencial       ██████████  100%  quanto pagar, o que oferecer e o que está atrasado
```

A resposta a “quanto falta” é a barra da cadeia.

## A.2 A cadeia de uma compra

PRONTO = o dado atravessa · FRÁGIL = atravessa, mas o operador refaz parte · FALTA = o operador refaz do zero do outro lado

| # | Etapa | Estado |
|---|---|---|
| 1 | Pedido entra (PDF ou manual) | PRONTO |
| 2 | Adiantamento vira crédito do pedido | PRONTO |
| 3 | Fatura vira conta a pagar | PRONTO |
| 4 | Crédito + saldo quitam a conta | PRONTO |
| 5 | Quantidade faturada abate o pedido | PRONTO |
| 6 | O faturado vira volumes / packing | PRONTO |
| 7 | Chegada, declaração, impostos, nacionalização | PRONTO |
| 8 | Nacionalizado vira estoque por produto | PRONTO |
| 9 | Custo da raquete (tudo somado) | PRONTO |
| 10 | Encerrar o pedido | PRONTO |

Hoje a cadeia atravessa até encerrar numa compra real, com o câmbio do documento (não o do banco). Compromisso vira estoque depois de vincular ao catálogo.

## A.3 O que o sistema já faz

- Importar pedido do PDF do fornecedor; sem catálogo vira compromisso
- Montar pedido na mão com produto, confirmar e faturar
- Vincular compromisso a produto do catálogo, com confirmação; aviso no cockpit até vincular; depois a linha segue até o estoque
- Registrar adiantamento em euro com câmbio; vira crédito do pedido
- Importar fatura do PDF na tela do pedido confirmado ou na fila de arquivos; o operador confirma o pedido; o código de barras não vira o código interno
- Importar pedido da planilha na tela de novo pedido; sem catálogo vira compromisso
- Aplicar crédito daquele pedido na conta e pagar o saldo
- Ver pedido / faturado / ainda disponível; na fatura digitada, marcar as linhas que ainda faltam
- Packing detalhado do PDF preenche o embarque planejado; ao reabrir, o embarque permanece visível
- Embarque e prestador também na mão; chegada registrada no embarque
- PDF aduaneiro preenche o processo; PDF do numerário registra impostos; o tesouro registra o pagamento já feito e aplica na obrigação
- Nacionalização parcial na tela; receber a quantidade liberada no estoque doméstico, sem digitar código interno
- Filas a pagar, cockpit do pedido, câmbio; cadastro de produtos (revisão geral, classificação e descrição), fornecedores e usuários
- Cronograma de pagamento no pedido (previsão; não duplica antecipo)
- Custo desembarcado bruto por produto numa compra real (tributos em valor cheio; várias faturas no mesmo processo; câmbio do documento de numerário, não o do banco)
- Encerrar o pedido confirmado com motivo; reabrir com motivo (nada some sem rastro)
- Fatura emitida permanece no histórico; não se apaga nem se altera
- Ver o painel: quanto pagar, o que há para oferecer, o que está atrasado; ir à fila

## A.4 O que ainda falta

| # | O que é | Por que importa | Tamanho |
|---|---|---|---|
| 1 | Levar a consulta econômica da demonstração ao uso operacional | Consulta entregue em teste; regras definitivas, importação de preços e conferência no laptop ainda pendentes | MÉDIO |
| 2 | Enriquecer o cadastro de produtos (descrição, mídia) | O cadastro operacional já existe | GRANDE |

# Contrato de coerência (A ↔ B)

Cursor **lê a Parte B** para trabalhar. Usa este Contrato **ao fechar** cada entrega material.

| Item da Parte A | Derivado de | Regra |
|---|---|---|
| A.0 última/próxima | B.1 próxima ação | frase de operador; ID canônico só em B |
| A.1 cada barra | livro-razão (abaixo) | `% = 100×n/d`; n=feito+documentado; FRÁGIL=0 |
| A.2 estado | B.2 | PRONTO = costura LIGADA **e** exercitado com documento do fornecedor; elo composto só conta na cadeia se os fatos forem **uma** história comercial/operacional |
| A.2 “onde para hoje” | primeiro elo não-PRONTO de A.2 | uma linha |
| A.3 capacidades | B.1 DONE sem bloqueio de uso | só entra se B sustenta |
| A.4 o que falta | B.2 não-LIGADA/FALTA + B.4 aberto + B.6 | ordem = próxima etapa da cadeia |

Checklist de entrega: (1) atualizar B; (2) recalcular livro-razão → A.1; (3) percorrer a tabela de derivação no resto de A; (4) tetos A≤70 e arquivo≤300; (5) busca na A: zero jargão interno e zero IDs de ensaio; (6) DOC_DELTA A/B; (7) se algum **denominador** d mudou: handoff declara d antigo/novo, % antigo/novo e motivo.

Regra de verdade: estado canônico vive só na Parte B; A nunca afirma além de B; snapshot 0.5.42 é imutável.

---

# Parte B — Operação

## Livro-razão das barras

`% = n/d`. Denominador só muda com declaração explícita no handoff.

| Barra | n/d | % | Feitos | Faltam |
|---|---|---|---|---|
| Cadeia | 10/10 | 100 | elos 1–10 (8 = produto no catálogo; compromisso só após vincular — B.2; 9 = revisado documental; 10 = encerrar) | — |
| Financeiro | 5/5 | 100 | adiantamento; liquidar crédito; fatura→conta; custo BRL=soma câmbios; cronograma no pedido | — |
| Ingestão | 7/7 | 100 | pipeline; aceite pedido PDF; aceite packing PDF; aceite Doganale PDF; aceite Numerário PDF; aceite Fattura PDF; aceite planilha | — |
| Logística | 2/2 | 100 | embarque manual; packing preenche volumes | — |
| Aduana/estoque | 3/3 | 100 | módulo operável na mão; PDF preenche; numerário se paga | — |
| Custo | 1/1 | 100 | custo por produto numa compra real (REVISED documental; família 202) | — |
| Painel | 1/1 | 100 | painel de leitura; três visões (executiva, comercial, controle) | — |

## B.1 Estado atual

| Item | Valor |
|---|---|
| Versão | **0.5.154** — P2→T1→C2→E4-S1→E4-S2→Q3 implementados; **G2 técnico local PASS com ressalvas**, build `stock-executive-20261023.1`, fontes `8871864`, demo8082/PG5447. 49 BE, 32 FE dirigidos, 10 UI pós-promoção; tour 6min43s e repetição técnica. Preços/PEPS/valoração somente política de demonstração. Físico **PENDENTE**, auditoria integral **PARTIAL**, barras inalteradas |
| Fundação · Order-to-Pay (Inc-1…6) · Horizon A | **DONE** — [`etapa-inc-6/`](docs/v2/etapa-inc-6/) · [`etapa-9/`](docs/v2/etapa-9/) · [`etapa-9v/`](docs/v2/etapa-9v/) |
| Logística (J#4) + Document Readiness | **DONE** — [`etapa-j4/`](docs/v2/etapa-j4/) · [`etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| Aduana + Inventory (J#5) | **DONE**; financeiro Customs **DONE** (BRL) — [`etapa-j5/`](docs/v2/etapa-j5/) · [`etapa-customs-funding/`](docs/v2/etapa-customs-funding/) |
| Ingestão (J#3) | I1–I7 **ENTREGUE**; J3-RUX Ordine **CONCLUÍDA**; famílias Fattura + planilha **ACEITAS** — [`etapa-j3/`](docs/v2/etapa-j3/) · [`ING_FAM_ADVISOR_HANDOFF.md`](docs/v2/etapa-ing-fam/ING_FAM_ADVISOR_HANDOFF.md) |
| J4-FIN | FIN-0…FIN-4 **DONE**; **A0 DONE** — [`etapa-j4-fin/`](docs/v2/etapa-j4-fin/) |
| Elo 7 (chegada / declaração / impostos / nacionalização) | **DONE** + aceite UI **PASS** — [`etapa-elo-7/`](docs/v2/etapa-elo-7/) |
| Elo 8 (nacionalizado → estoque) | **DONE / ENCERRADO** — aceite advisor 2026-08-17 — [`etapa-elo-8/`](docs/v2/etapa-elo-8/) |
| MDM-UX (cadastros mestres HTTP) | **DONE** — [`etapa-mdm-ux/`](docs/v2/etapa-mdm-ux/) |
| MDM-UX-R (reconstrução visual) | **DONE** — proto = contrato visual; produção alinhada |
| CAT-PIM (catálogo comercial) | **DONE** em `epic_v2` — 027 + 92 históricos; proto = North Star; Onda 2 **não** iniciada |
| Costing / Reconciliation (J#6) | **DONE** — capacidade + Elo 9 PRONTO (REVISED documental) — [`E9_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-9/E9_ADVISOR_HANDOFF.md) |
| J#7 | **DONE** + **J7-EXEC-UX PASS** + **PAINEL-UX2 PASS** — [`PAINEL_UX2_ADVISOR_HANDOFF.md`](docs/v2/etapa-painel-ux2/PAINEL_UX2_ADVISOR_HANDOFF.md) |
| J#8 aceite UI | **DONE** — V1 arquivada — [`J8_CLOSE_ADVISOR_HANDOFF.md`](docs/v2/etapa-j8/J8_CLOSE_ADVISOR_HANDOFF.md) |
| J#5-REC | **DONE** — compromisso → vincular (SKU próprio) → estoque — [`J5_REC_ADVISOR_HANDOFF.md`](docs/v2/etapa-j5-rec/J5_REC_ADVISOR_HANDOFF.md) |
| Alembic head | código **032**; demo `epic_v2_test`/5447 = **032**; demo anterior/5433 e operação `epic_v2` = **031**, não migradas nesta entrega |

**Próxima ação:** conferência física do apresentador e revisão das ressalvas de G2 no handoff único; depois densidade da consulta, importação de preços e políticas para uso operacional. I-01 histórico sem causa presumida; cenário novo de chegada/recebimento passou. Offsite e violação preexistente ingestion→foundation pendentes. Onda 2 / IA / mídia e E3-B amplo não iniciados. Não equivale a aceite global/J#8.

Manutenção pré-demo CEO: escopo autorizado executado em `epic_v2_test`; prontidão do roteiro separada da auditoria integral **PARTIAL**. Fontes, runtime, manifesto, gates e pendências: [`PRE_DEMO_CEO_AUDIT.md`](docs/v2/etapa-pre-demo-ceo/PRE_DEMO_CEO_AUDIT.md) e [`PRE_DEMO_CEO_PLAN.md`](docs/v2/etapa-pre-demo-ceo/PRE_DEMO_CEO_PLAN.md). Livro-razão e denominadores inalterados; sem promoção para operação.

Refinamento visual autorizado: composição só na Executiva de sistema; visões pessoais e demais presets preservados; AP/Custo com variantes locais; presenter nativo e tour sem gravações. Preservação incremental inclui dist anterior completo. Implementação, gates e recuperação: [`UI_EXECUTIVA_REFINEMENT_PLAN.md §12`](docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md#12-execução-autorizada--22102026). Não é modernização integral nem encerramento de fase.

Histórico de22/10: aprovação das capturas da170116 limitada ao roteiro ensaiado. Autorização posterior de23/10 permitiu integrar e promover localmente após G1, preservando a release anterior. Maximizar/restaurar/redimensionar e legibilidade humana continuam pendentes do apresentador; viewport nativo validado pelo runner não substitui essa conferência.

Histórico da auditoria ampliada: laboratório8084/5441, então distinto da demo8082/5433. [`AUDITORIA_UI_UX_EXECUTIVA_EPIC.md`](docs/v2/etapa-auditoria-uiux-executiva/AUDITORIA_UI_UX_EXECUTIVA_EPIC.md) documenta aquele estado; não descreve a release atual. Cobertura integral continua parcial.

Revisão de experiência: P01–P08 rejeitados; r2 aprovada. [`INTEGRACAO_EXPERIENCIA_EPIC.md`](docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md) consolida execução atual, matriz, imagens e GitHub. 31 SKUs Heroes, 12 compras/faturas e saldo SHOW26 de42UN/R$54.900; preços e margem potencial na política fictícia autorizada. Nova cópia/runtime/cluster/storage; release anterior recuperável. Sem publicação em produção nem aprovação contábil/tributária.

Manutenção: fase DONE → status+evidência aqui, detalhe em `docs/v2/etapa-*` (não no snapshot). Checkpoint de fase nova nasce em `etapa-*` antes de executar. Teto do arquivo vivo ≤300 linhas.

## B.2 Cadeia: evidência e costuras

| Elo | Provado com? | O que atravessa | Costura |
|---|---|---|---|
| 1. Pedido entra | Sim — Ordine PDF de ensaio → pedido confirmado | PDF → pedido | **LIGADO** — compromisso vira produto com confirmação |
| 2. Adiantamento → crédito | Sim — no pedido de origem PDF; na cadeia 328 o crédito foi alocado | Pagamento amarrado ao pedido + câmbio | **LIGADO** |
| 3. Fatura → conta a pagar | Sim — Fattura real do fornecedor (corpus 244) → candidatos → confirmação → Invoice DRAFT → issue → Payables | Fatura + vencimentos + IBAN; Order sugerido e confirmado (não inventado) | **LIGADO** |
| 4. Crédito + saldo → quitação | Sim — Fattura real 328 no mesmo pedido (UI C4 + cockpit aceite 1→6) | ADVANCE + alocação + SETTLEMENT do residual; Payables PAID | **LIGADO** |
| 5. Qty faturada abate pedido | Sim — mesmo pedido; Fattura 328 ISSUED | Pedida/faturada/disponível; overbill bloqueia no emitir | **LIGADO** |
| 6. Faturado → volumes | Sim — Packing List Detail 328 (PDF real); walk integral 1→6 2026-08-14 | 5 caixas × 10 = 50 no embarque planejado; modal nulo; Order confirmado (não nº do PDF); estado pós-commit visível ao recarregar; auditoria no embarque | **LIGADO** |
| 7. Chegada / DUIMP / nacionalização | Sim — família 202 na **mesma** história, aceite **UI** 2026-08-14: catálogo na tela → 5 PDFs no input → ARRIVED → Doganale preenche → Print anexo → Numerário (tributos+despesas = declarado R$ 1.425.554,64; **não** a soma com bases) → AP CUSTOMS_FUNDING OPEN (zero Payment) → DUIMP de ensaio rotulado → nacionalização parcial → excesso bloqueado na UI. Tributos = PDF Numerário (nível DUIMP 181/202/…). | Chegada + declaração PDF + impostos PDF + nacionalização | **LIGADO** |
| 8. Nacionalizado → estoque | Sim — walk operador W1–W8 (2026-08-17) + verificação 202 (PDFs → nacionalização → estoque). **LIGADO para itens com produto no catálogo.** Compromisso sem Product **não** atravessa; após vincular (J#5-REC **DONE**, SKU próprio ≠ código de barras / I.V.*) segue o mesmo caminho. DEC-E8-DOC: recebimento **não** exige PDF novo. Elos 1–6 na 328. | Nacionalização → GoodsReceipt DOMESTIC_IN → StockBalance / SkuPosition | **LIGADO** — catálogo; compromisso só após vincular |
| 9. Custo da raquete | Sim — seis Fatturas reais da família 202 no mesmo processo (181, 202, 203, 244, 245, 246); FOB = soma das mercadorias; câmbio documental 5,9205 do Numerário; frete por papel (base CIF não vira componente). Publicado REVISED na UI; recarregar mantém. SKU ≠ EAN. Não é câmbio bancário. | Fatura + frete + imposto + câmbio documental no **mesmo** processo com cobertura 6/6 | **LIGADO** — REVISED documental |
| 10. Encerrar pedido | Sim — família 202 na operação: pedido no catálogo 92; 6 Fatturas A0; REVISED documental; Encerrar na UI (`FAMILIA-202` CLOSED). Motivo + audit na mesma UoW; reabrir com motivo. Bloqueio local: linha COMMITMENT. Sem exigir payables/custo REALIZED/processo CLEARED. | CONFIRMED → CLOSED auditável; CLOSED → CONFIRMED | **LIGADO** |

Elo composto na barra da cadeia: só é **PRONTO** quando os fatos forem **uma** história comercial/operacional, salvo exceção explicitamente aceita. Elos 1–6 e o elo 7 foram exercitados em compras de ensaio distintas (328 vs 202); isso é aceito — cada elo composto teve a sua história única. Elo 8: costura LIGADA na história 202 (PDFs do fornecedor → nacionalização → estoque na mesma UI); DEC-E8-DOC = sem PDF no receipt. Elo 9: costura LIGADA na mesma família 202 (seis faturas + Numerário; câmbio documental ≠ bancário). Elo 10: costura LIGADA na operação (`FAMILIA-202` encerrado; 1 caso de custo publicado). J#5-REC **DONE** (compromisso atravessa após vincular). **Não** rebaixa 10/10.

## B.3 Decisões abertas e bloqueios

| ID | Estado | Bloqueia o quê | Próxima decisão |
|---|---|---|---|
| L-001 | Aberto | Conciliação / tolerâncias | Política final na Reconciliation |
| DEC-SHIP-CANCEL | Aberto | Logistics BOOKED+ | Isolar ou resolver em incremento Logistics |
| L-003 | Aberto | Credit / CC BR | Isolar na fase Treasury |
| L-005 | **PARTIAL** | Matriz completa papéis × ações críticas | Chrome do painel = `reporting:read` (admin, comprador, aduana, estoque). Widget exige owner `*:read`. Sem papéis `financeiro`/`gestor` |
| DEC-J7-MOBILE | **Fechada (J#7)** | Overlay do rail <1024 | Walk 390: rail 56px usável; overlay **não** nesta onda |
| DEC-J7-EXEC-* | **Fechadas (J7-EXEC-UX)** | — | CASH; FX; COMPACT-MONEY; HUMAN-TITLE; PERIOD; CHROME; FLOW; MY-VIEW. Blueprint §8.2 |
| DEC-UX2-* | **Fechadas (PAINEL-UX2)** | — | CHART (Recharts; revoga J7-CHART); TOKENS; THREE-VIEWS; SECTIONS; TOOLTIP; NO-DEMAND; FX-SERIES. Blueprint §8.0 / §8.2 / §12 |
| DEC-ACCONTO-INVOICE | Pendente | Tipagem Fattura | Blueprint §5.7 |
| DEC-ENDERECO | Aberto | Modelo de endereços | — |
| DEC-CLOSE-ORDER | **Fechada (Elo 10)** | — | CLOSED = lifecycle do pedido comercial; `orders:write`; bloqueio local COMMITMENT; reopen auditado. Não reutiliza `orders:cancel`. Blueprint §5.6 / §7.16 |
| L-007 | **Fechada (Elo 7)** | — | DUIMP/DI: sem PDF no corpus; referência de ensaio digitada e rotulada (nunca extraída) |
| E8-NAT-REVERSE-API | Aberto | Reverse nacionalização após GoodsReceipt pode duplicar saldo se chamado na API | UI oculta Reverter (DEC-E8-NAT-REVERSE = B). Não abrir `customs` → `inventory` (ciclo). Guard futuro sem ciclo |
| Fechadas | DEC-DUIMP-MULTI-SHIP · DEC-SCONTO-ITEM · DEC-FX-SCOPE · DEC-A0-ORDER-CANDIDATES · DEC-A0-AMBIGUOUS · DEC-C6-IDENTITY · DEC-C6-INVOICE-OPTIONAL · DEC-C6-LINE-MATCH · DEC-C6-COMMITMENT · DEC-C6-PLANNED-ONLY · DEC-C6-DETAIL-SOT · DEC-C6-SHIPMENT-TARGET · DEC-E7-DOGANALE-FILL · DEC-E7-IDENTITY · DEC-E7-PROCESS-TARGET · DEC-E7-ARRIVAL · DEC-E7-PRINT · DEC-E7-FUNDING-SCOPE · DEC-E7-BOUNDARY · L-007 · **DEC-J7-MOBILE** · **DEC-J7-EXEC-*** · **DEC-UX2-*** · **DEC-J8-ARCHIVE** | — | V2 é o sistema em operação; `v1/` congelado (ADR-16); sem migração (ADR-10) |

## B.4 Fases e próximos passos

| Fase | Status | Próxima ação | Evidência |
|---|---|---|---|
| 0B / Fundação / Order-to-Pay | DONE | — | snapshot · [`etapa-inc-6/`](docs/v2/etapa-inc-6/) |
| Logística (J#4) | DONE | — | [`etapa-j4/`](docs/v2/etapa-j4/) |
| Aduana + Inventory (J#5) | DONE | — | [`etapa-j5/`](docs/v2/etapa-j5/) · [`CFUND_ADVISOR_HANDOFF.md`](docs/v2/etapa-customs-funding/CFUND_ADVISOR_HANDOFF.md) |
| Ingestão (J#3) | **DONE** (Fattura + planilha na tela do pedido) | — | [`etapa-j3/`](docs/v2/etapa-j3/) · [`ING_FAM_ADVISOR_HANDOFF.md`](docs/v2/etapa-ing-fam/ING_FAM_ADVISOR_HANDOFF.md) |
| J4-FIN | FIN-4 **DONE**; **A0 DONE**; **B0 DONE** | aguardando autorização (**não** Onda 2) | [`etapa-j4-fin/`](docs/v2/etapa-j4-fin/) · [`B0_ADVISOR_HANDOFF.md`](docs/v2/etapa-b0/B0_ADVISOR_HANDOFF.md) |
| Cadeia elos 4–6 | **DONE** (hardening C46-HARDEN) | — | [`etapa-cadeia-46/`](docs/v2/etapa-cadeia-46/) |
| Elo 7 | **DONE** + aceite UI **PASS** | — | [`E7_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-7/E7_ADVISOR_HANDOFF.md) |
| Elo 8 | **DONE / ENCERRADO** (aceite advisor) | backlog: `E8-NAT-REVERSE-API`; Caso A; `E7-ARRIVAL-GATE`; atritos B.6 — **não** corrigir nesta fase | [`E8_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md) |
| MDM-UX | **DONE** (HTTP) | — | [`MDM_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md) |
| MDM-UX-R | **DONE** | — | [`MDM_UX_R_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux-r/MDM_UX_R_ADVISOR_HANDOFF.md) |
| CAT-PIM | **DONE** (Onda 1 em operação) | Onda 2 / IA / mídia **não** iniciadas | [`CAT_PIM_OPERATIONAL_COMPLETION_ADVISOR_HANDOFF.md`](docs/v2/etapa-cat-pim/CAT_PIM_OPERATIONAL_COMPLETION_ADVISOR_HANDOFF.md) |
| Costing (J#6) | **DONE** (capacidade + Elo 9 PRONTO) | — | [`COSTING_ADVISOR_HANDOFF.md`](docs/v2/etapa-costing/COSTING_ADVISOR_HANDOFF.md) · [`E9_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-9/E9_ADVISOR_HANDOFF.md) |
| Elo 9 | **DONE** (REVISED documental; 6 Fatturas) | — | [`E9_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-9/E9_ADVISOR_HANDOFF.md) |
| Dashboard (J#7) | **DONE** + **J7-EXEC-UX PASS** + **PAINEL-UX2 PASS** | — | [`PAINEL_UX2_ADVISOR_HANDOFF.md`](docs/v2/etapa-painel-ux2/PAINEL_UX2_ADVISOR_HANDOFF.md) |
| Elo 10 | **DONE** (CONFIRMED→CLOSED na operação) | — | [`E10_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-10/E10_ADVISOR_HANDOFF.md) |
| Aceite final (J#8) | **DONE** (V1 arquivada) | — | [`J8_CLOSE_ADVISOR_HANDOFF.md`](docs/v2/etapa-j8/J8_CLOSE_ADVISOR_HANDOFF.md) |
| J#5-REC | **DONE** (compromisso → vincular → estoque) | — | [`J5_REC_ADVISOR_HANDOFF.md`](docs/v2/etapa-j5-rec/J5_REC_ADVISOR_HANDOFF.md) |

Checkpoints I5-0…I5-6, J3-P0…I7: já em `etapa-j5/` e `etapa-j3/`.

## B.5 ADRs vigentes

| ADR | Decisão resumida | Impacto atual |
|---|---|---|
| ADR-01 | Monólito modular; stack atual | Stack V2 |
| ADR-02 | Alt. B — portar calculadores com testes | Ingestão / Costing / FX |
| ADR-03 | Separar Order / Shipment / ImportProcess | Modelo J#4+ |
| ADR-04 | Layout `root/{docs,ROADMAP,v1,v2}` | Layout vigente |
| ADR-05 | OpenAPI + client TS gerado | Drift check |
| ADR-06 | Liquidação só via Payable | Billing/Treasury |
| ADR-07 | StockBalance derivado | Inventory |
| ADR-08 | `document_links` por Documents | Documents sem ciclos |
| ADR-09 | Estados por agregado | Todos os módulos |
| ADR-10 | Conteúdo atual descartável; zero migração de dados | Premissa definitiva |
| ADR-11 | Orders ← Billing ← Treasury; Expense em Costing | Ownership |
| ADR-12 | DUIMP→Invoice 1:N; Shipment sem `order_id` | Customs/Logistics |
| ADR-13 | `.env`/deps isolados; regra Cursor | Runtime |
| ADR-14 | Package-by-domain; grafo acíclico; V2↛V1 | Arch gates |
| ADR-15 | Audit atômico — mesma UoW | Fundação+ |
| ADR-16 | V1 congelada | Guarda `v1/**` |

## B.6 Backlog fora da fase

| Item | Destino | Observação |
|---|---|---|
| Estoque executivo / texto mínimo | Entregue em teste; operacional pendente | Multisseleção/agrupamento/medidas/visões, custo por origem e preços vigentes; falta política operacional, importação de preços, maior densidade e conferência física. E3-B amplo/I-01 independentes; handoff único em B.1 |
| Pós-reunião — origem/natureza da taxa no detalhe de Contas a pagar | Billing UI / Treasury | Explicitar fonte e se é planejada, de mercado, documental ou realizada conforme o dado existente; não alterar cálculo nem atribuir natureza não comprovada |
| Pós-reunião — erro cambial longo na sidebar | Resolvido no pacote r2 | Mensagem curta, detalhe acessível; sem alterar mecanismo de cotação |
| Pós-reunião — linguagem e ação operacional | UI local / E3-B | Primeiro percurso com rótulos/qualificadores e ação; demais telas e redação residual permanecem locais, não modernização integral |
| Elo 8 Caso A (entreposto / BONDED_IN + RECLASS na UI) | Inventory UI | 2026-08-17 — select congelado `DOMESTIC_IN`; domínio/API intactos; **não** alargar nesta campanha |
| Elo 8 atrito — qty proposta não reseta ao residual novo | Inventory UI | 2026-08-17 — walk W4; **não** polir nesta campanha |
| Elo 8 atrito — auditoria coluna Quem mostra `1` | Audit / Identity | 2026-08-17 — walk W8; actor opaco na tabela do processo; **não** polir nesta campanha |
| E7-ARRIVAL-GATE | Customs | Nacionalização hoje **não** exige Shipment ARRIVED. Campanha demonstra chegada; **não** implementa a trava. Avaliar se chegada física/documental deve ser precondição |
| MINOR_BACKLOG UI Horizon A | UI sob pedido | Aceite fechado |
| Backlog J#5 residual (seed aduana/estoque; stubs SkuPosition) | Identity / Reporting | [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md) |
| SCR-028 hub FX | UI futuro | Sem rota `/fx` |
| Horizon B1 | Externo | J#5-REC DONE; resto NOT_STARTED |

## B.7 Histórico recente

| Rev | Resumo | Evidência |
|---|---|---|
| **0.5.154** | Estoque econômico/visões/preços + Heroes; G2 técnico local, 032 apenas na nova demo, snapshots restaurados e push verificado; físico/global pendentes, barras inalteradas | [`INTEGRACAO_EXPERIENCIA_EPIC.md`](docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md) |
| **0.5.153** | Planning de estoque executivo e texto mínimo; inspeção da .3/catálogo real, proposta incorporada, parcela E4-S e recomendações; demo/dados/código preservados, sem avanço de barras | [`INTEGRACAO_EXPERIENCIA_EPIC.md`](docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md) |
| **0.5.152** | Gate P→G1 integrado, leituras E0/posição/proveniência, shell r2, testes novos, demo local promovida com recuperação; físico pendente, barras inalteradas | [`INTEGRACAO_EXPERIENCIA_EPIC.md`](docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md) |
| **0.5.151** | Direção r2 aprovada; E0–E4 ajustado para pacote integrado painel/estoque/produto/custo/PDF/retorno. Planning, runtime e WIP preservados; sem implementação ou avanço de barras | [`INTEGRACAO_EXPERIENCIA_EPIC.md`](docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md) |
| **0.5.150** | Nova proposta interativa isolada após rejeição de P01–P08; três jornadas testadas, pacote autocontido; revisão pendente; demo e barras preservadas | [`REVISAO_EXPERIENCIA_EPIC.md`](docs/v2/etapa-revisao-experiencia/REVISAO_EXPERIENCIA_EPIC.md) |
| **0.5.149** | Auditoria ampla + testes laboratoriais + protótipo isolado; cobertura PARTIAL, sem redesenho implementado ou mudança da demo/barras. Revisão do advisor pendente | [`AUDITORIA_UI_UX_EXECUTIVA_EPIC.md`](docs/v2/etapa-auditoria-uiux-executiva/AUDITORIA_UI_UX_EXECUTIVA_EPIC.md) |
| **0.5.148** | Aprovação das capturas pelo advisor, restrita ao roteiro ensaiado; janela/legibilidade pelo apresentador pendentes; três ajustes pós-reunião registrados. Sem implementação ou avanço de barras | [`UI_EXECUTIVA_REFINEMENT_PLAN.md §12.10`](docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md#1210-aprovação-das-capturas-e-preservação-para-a-reunião) |
| **0.5.147** | Refinamento local Executiva/AP/Custo/tour/presenter; funcional dirigido validado, janela nativa/aceite visual humano pendentes. Barras/denominadores inalterados | [`UI_EXECUTIVA_REFINEMENT_PLAN.md`](docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md) |
| **0.5.146** | Manutenção pré-demo: correções locais, massa única e tour automático no teste; auditoria integral permanece parcial. Barras/aceites inalterados | [`PRE_DEMO_CEO_AUDIT.md`](docs/v2/etapa-pre-demo-ceo/PRE_DEMO_CEO_AUDIT.md) |
| **0.5.145** | **B0 DONE** (fatura na mão escolhe linhas e quantidade residual; SKU ≠ EAN). Cadeia **10/10**. Ingestão **7/7**. Alembic **031** | [`B0_ADVISOR_HANDOFF.md`](docs/v2/etapa-b0/B0_ADVISOR_HANDOFF.md) |
| **0.5.144** | **ING-FAM DONE** (Fattura PDF na comercial + planilha no novo pedido; SKU ≠ EAN). Ingestão **7/7 = 100%** (d 7 inalterado; n 5→7). Cadeia **10/10**. Alembic **031** | [`ING_FAM_ADVISOR_HANDOFF.md`](docs/v2/etapa-ing-fam/ING_FAM_ADVISOR_HANDOFF.md) |
| **0.5.143** | **J#5-REC DONE** (compromisso vinculado chega ao estoque; SKU ≠ EAN/I.V.*; cockpit + E2E UI). Cadeia **10/10**. Alembic **031** | [`J5_REC_ADVISOR_HANDOFF.md`](docs/v2/etapa-j5-rec/J5_REC_ADVISOR_HANDOFF.md) |
| **0.5.142** | **J#8 DONE** (13 suítes E2E UI; SC-08/10/17; V1 arquivada). Cadeia **10/10**. Alembic **031** | [`J8_CLOSE_ADVISOR_HANDOFF.md`](docs/v2/etapa-j8/J8_CLOSE_ADVISOR_HANDOFF.md) |
| **0.5.141** | **J8-0 PASS** (12 suítes E2E UI isoladas; CTA `orders-new-cta`). Cadeia **10/10**. J#8 IN_PROGRESS; V1 não arquivada | [`J8_0_ADVISOR_HANDOFF.md`](docs/v2/etapa-j8/J8_0_ADVISOR_HANDOFF.md) |
| **0.5.140** | **Elo 10 PRONTO** (CONFIRMED→CLOSED na operação; família 202; Alembic **031**; 1 CostingCase REVISED). Cadeia **10/10**. `DEC-CLOSE-ORDER` fechada. Próxima = aceite (J#8) — STOP | [`E10_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-10/E10_ADVISOR_HANDOFF.md) |
| **0.5.139** | **Elo 9 PASS** (custo REVISED documental; 6 Fatturas família 202; Alembic **030** inalterado; 0 CostingCase). Cadeia **9/10**. Custo **1/1**. Elo 10 **FALTA**. Próxima = Elo 10 / aceite (J#8) — STOP | [`E9_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-9/E9_ADVISOR_HANDOFF.md) |
| **0.5.138** | **PAINEL-UX2 PASS** (três visões; Alembic **030** inalterado; 0 CostingCase). Cadeia **inalterada** 8/10. Custo **0/1**. Painel **1/1**. Elo 9 **FALTA**. Próxima = aceite (J#8) — STOP | [`PAINEL_UX2_ADVISOR_HANDOFF.md`](docs/v2/etapa-painel-ux2/PAINEL_UX2_ADVISOR_HANDOFF.md) |
| **0.5.137** | **J7-EXEC-UX PASS** (visão Executiva comercial; Alembic **030** inalterado; 0 CostingCase). Cadeia **inalterada** 8/10. Custo **0/1**. Painel **1/1**. Elo 9 **FALTA**. Próxima = aceite (J#8) — STOP | [`J7_EXEC_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-j7/J7_EXEC_UX_ADVISOR_HANDOFF.md) |
| **0.5.136** | **J#7 DONE** (painel gerencial; Alembic **030** em `epic_v2`; 0 CostingCase). Cadeia **inalterada** 8/10. Custo **0/1**. Painel **1/1**. Elo 9 **FALTA**. Próxima = aceite (J#8) — STOP | [`J7_ADVISOR_HANDOFF.md`](docs/v2/etapa-j7/J7_ADVISOR_HANDOFF.md) |
| **0.5.135** | **J6-UI-CLOSE PASS** (Expense + Compare na UI real; walk 9B sem mutação Costing pós-fixture). Alembic **029** inalterado. Cadeia **inalterada** 8/10. Custo **0/1**. Elo 9 **FALTA**. Próxima = painel (J#7) | [`COSTING_ADVISOR_HANDOFF.md`](docs/v2/etapa-costing/COSTING_ADVISOR_HANDOFF.md) |
| **0.5.134** | **J#6 DONE** (custo desembarcado bruto; Alembic **029** em `epic_v2`; 0 casos na operação). Cadeia **inalterada** 8/10. Custo **0/1**. Elo 9 **FALTA**. Próxima = painel (J#7) | [`COSTING_ADVISOR_HANDOFF.md`](docs/v2/etapa-costing/COSTING_ADVISOR_HANDOFF.md) |
| **0.5.133** | **CUSTOMS-FUNDING DONE** (Numerário BRL pago no tesouro; Alembic 028 em `epic_v2`). Aduana **3/3**. Cadeia **inalterada** 8/10. Pagamento do numerário **não** é elo 9 | [`CFUND_ADVISOR_HANDOFF.md`](docs/v2/etapa-customs-funding/CFUND_ADVISOR_HANDOFF.md) |
| **0.5.132** | **CAT-PIM Onda 1 DONE em operação** (027 + 92 em `epic_v2`; import no-op; backup retido). Barras **inalteradas** 8/10. Próxima = numerário (`CUSTOMS_FUNDING`). Onda 2/IA/mídia não iniciadas | [`CAT_PIM_OPERATIONAL_COMPLETION_ADVISOR_HANDOFF.md`](docs/v2/etapa-cat-pim/CAT_PIM_OPERATIONAL_COMPLETION_ADVISOR_HANDOFF.md) |
| **0.5.131** | **CAT-PIM promotion readiness PASS** (review 40/13/38; import no-op; ensaio sobre cópia de `epic_v2`). Onda 1 **DONE** em teste. `epic_v2` **026** intocado. Barras **inalteradas** 8/10. Numerário pausado. Próxima = autorização de promoção | [`CAT_PIM_PROMOTION_READINESS_ADVISOR_HANDOFF.md`](docs/v2/etapa-cat-pim/CAT_PIM_PROMOTION_READINESS_ADVISOR_HANDOFF.md) |
| **0.5.130** | **CAT-PIM Onda 1 DONE** em `epic_v2_test` (027+taxonomia+92+UI). `epic_v2` **026** intocado. Barras **inalteradas** 8/10. Numerário pausado. Próxima = autorização de promoção | [`CAT_PIM_ONDA1_ADVISOR_HANDOFF.md`](docs/v2/etapa-cat-pim/CAT_PIM_ONDA1_ADVISOR_HANDOFF.md) |
| **0.5.129** | **CAT-PIM Onda 1 IN_PROGRESS** (gate proto APROVADO; execução em `epic_v2_test`). Barras **inalteradas** 8/10. Numerário pausado. **Não** promover `epic_v2` | [`CAT_PIM_PROTO_ADVISOR_HANDOFF.md`](docs/v2/etapa-cat-pim/CAT_PIM_PROTO_ADVISOR_HANDOFF.md) |
| **0.5.128** | **CAT-PIM proto IN_PROGRESS** (92 honestos; Comparar na Onda 1; XLSX de revisão; sem migration). Barras **inalteradas** 8/10. Numerário pausado | [`CAT_PIM_PROTO_ADVISOR_HANDOFF.md`](docs/v2/etapa-cat-pim/CAT_PIM_PROTO_ADVISOR_HANDOFF.md) |
| **0.5.127** | **MDM-UX-R DONE** (Product List/ficha/Users/rail no V2 real; proto = contrato). Barras **inalteradas** 8/10. Próxima da cadeia = numerário (B.6) | [`MDM_UX_R_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux-r/MDM_UX_R_ADVISOR_HANDOFF.md) |
| **0.5.126** | **MDM-UX-R IN_PROGRESS** (GATE VISUAL R0–R2.2 aprovado; R3–R6 autorizados). Barras **inalteradas** 8/10. Settlement numerário permanece B.6 | [`MDM_UX_R_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux-r/MDM_UX_R_ADVISOR_HANDOFF.md) |
| **0.5.125** | **MDM-UX DONE** (PATCH + list-report + 026 L-006/`tax_id` + Users UI; walk 61 SKUs); Alembic **026**; barras **inalteradas** 8/10 | [`MDM_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md) |
| **0.5.124** | Campanha **MDM-UX** vira B.1; settlement numerário permanece B.6; barras **inalteradas** 8/10 | [`MDM_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md) |
| **0.5.123** | Elo 8 verificação final + **aceite advisor**: 202 documental → estoque; **ENCERRADO**; barras **inalteradas** 8/10; J#5-REC permanece | [`E8_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md) |
| **0.5.122** | Elo 8: massa do walk = mock (`E8-202-MOCK`); atrito qty/Quem em B.6; barras **inalteradas** 8/10 | [`E8_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md) |
| **0.5.121** | Elo 8 **PRONTO/LIGADO** (produto no catálogo); cadeia 8/10 = 80%; Aduana 2/3; `E8-NAT-REVERSE-API` | [`E8_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md) |
| **0.5.120** | Aceite UI Elo 7 **PASS**; Elo 7 PRONTO/LIGADO; cadeia 7/10; Ingestão 5/7; Aduana 2/3 | [`E7_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-7/E7_ADVISOR_HANDOFF.md) |
| **0.5.119** | Campanha Elo 7 **DONE** (história 202; Doganale/Numerário/nacionalização). Barras **inalteradas** 6/10; propostas no CF | [`E7_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-7/E7_ADVISOR_HANDOFF.md) |
| **0.5.118** | Hardening C4–C6 (jornada UI 1→6; packing persistente; auditoria no embarque). Barras **inalteradas** 6/10 | [`CADEIA_46_ADVISOR_HANDOFF.md`](docs/v2/etapa-cadeia-46/CADEIA_46_ADVISOR_HANDOFF.md) |
| **0.5.117** | Elos 4–6 **DONE**; cadeia 6/10 = 60%; Ingestão 3/7; Logística 2/2 | [`CADEIA_46_ADVISOR_HANDOFF.md`](docs/v2/etapa-cadeia-46/CADEIA_46_ADVISOR_HANDOFF.md) |
| **0.5.116** | Campanha elos 4–6 **IN_PROGRESS** (P0; barras 3/10 inalteradas) | [`etapa-cadeia-46/`](docs/v2/etapa-cadeia-46/) |
| **0.5.115** | A0 **DONE** (Fattura assistida; elo 3 LIGADO/PRONTO; cadeia 3/10 = 30%) | [`J4_BILLING_CAPACITY_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_BILLING_CAPACITY_ADVISOR_HANDOFF.md) |
| **0.5.114** | FIN-4 **DONE** (cronograma planejamento; Alembic 025; Financeiro 5/5) | [`J4_FIN4_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN4_ADVISOR_HANDOFF.md) |
| **0.5.113** | ROADMAP A/B **DONE** (painel+contrato+livro-razão n/d; cadeia 20%; próxima FIN-4) | [`ROADMAP_AB_ADVISOR_HANDOFF.md`](docs/v2/archive/roadmap/ROADMAP_AB_ADVISOR_HANDOFF.md) |
| **0.5.112** | G4+G5 **DONE** (match Fattura; aceite UI bind; 507 pytest) | [`G3_G4_G5_BIND_UI_ADVISOR_HANDOFF.md`](docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G3_G4_G5_BIND_UI_ADVISOR_HANDOFF.md) |
| **0.5.111** | G3 UI bind **DONE** | mesmo handoff G3–G5 |
| **0.5.110** | FIN-CICLO-FIX **DONE** (purpose; exposição EUR; Alembic 024) | [`J4_FIN_CICLO_FIX_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN_CICLO_FIX_ADVISOR_HANDOFF.md) |
| **0.5.109** | G2 bind backend **DONE** | [`G2_BIND_PRODUCT_ADVISOR_HANDOFF.md`](docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G2_BIND_PRODUCT_ADVISOR_HANDOFF.md) |
| **0.5.108** | J4-FIN-CICLO **DONE** (custo BRL = soma câmbios) | [`J4_CICLO_INTEGRAL.md`](docs/v2/etapa-j4-fin/J4_CICLO_INTEGRAL.md) |
| **0.5.107** | G1 âncora billing PLANNING | [`G1_ANCORA_BILLING_ADVISOR_HANDOFF.md`](docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G1_ANCORA_BILLING_ADVISOR_HANDOFF.md) |
| **0.5.106** | §0 vínculo SKU; logística 50%; aduana 65% | [`COMPROMISSO_SKU_ADVISOR_HANDOFF.md`](docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/COMPROMISSO_SKU_ADVISOR_HANDOFF.md) |
| **0.5.105** | ROADMAP-VIS §0 | este arquivo (histórico) |
| **0.5.104** | FIN-3B **DONE** | [`J4_FIN3B_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN3B_ADVISOR_HANDOFF.md) |

Anteriores: [`ROADMAP_HISTORICO.md`](docs/v2/archive/roadmap/ROADMAP_HISTORICO.md). Até Inc-6: [snapshot 0.5.42](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md).
