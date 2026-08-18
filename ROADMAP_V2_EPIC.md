# EPIC Controle V2 — Roadmap operacional

> Produto: [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md) · Índice: [`docs/README.md`](docs/README.md) · Snapshot imutável: [`docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md`](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md) · Método: [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc)

---

# Parte A — Painel

| Campo | Valor |
|---|---|
| Atualizado em | 2026-08-18 |
| Última entrega | Cadastro de produtos, fornecedores e usuários |
| Próxima entrega | Pagar o numerário no tesouro |
| Detalhe técnico | Parte B, abaixo |

## A.1 Quanto está pronto

```
Cadeia ponta a ponta   ████████░░   80%  até estoque, se o produto já está no catálogo
Ciclo financeiro       ██████████  100%  adiantamento, quitação, fatura, câmbio, cronograma
Ingestão               ███████░░░   71%  pipeline, pedido, packing, declaração e numerário do PDF
Logística              ██████████  100%  embarque na mão e packing preenche volumes
Aduana / estoque       ███████░░░   67%  PDF preenche; numerário ainda não se paga
Custo desembarcado     ░░░░░░░░░░    0%  ainda não existe
Painel gerencial       ░░░░░░░░░░    0%  ainda não existe
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
| 9 | Custo da raquete (tudo somado) | FALTA |
| 10 | Encerrar o pedido | FALTA |

Hoje a etapa 8 atravessa quando o produto já está no catálogo. Pedido só compromisso ainda não chega ao estoque. O numerário ainda não se paga.

## A.3 O que o sistema já faz

- Importar pedido do PDF do fornecedor; sem catálogo vira compromisso
- Montar pedido na mão com produto, confirmar e faturar
- Vincular compromisso a produto do catálogo, com confirmação
- Registrar adiantamento em euro com câmbio; vira crédito do pedido
- Importar fatura do PDF; o sistema sugere o pedido e o operador confirma
- Aplicar crédito daquele pedido na conta e pagar o saldo
- Ver pedido / faturado / ainda disponível
- Packing detalhado do PDF preenche o embarque planejado; ao reabrir, o embarque permanece visível
- Embarque e prestador também na mão; chegada registrada no embarque
- PDF aduaneiro preenche o processo; PDF do numerário registra impostos (não paga)
- Nacionalização parcial na tela; receber a quantidade liberada no estoque doméstico, sem digitar código interno
- Filas a pagar, cockpit do pedido, câmbio; cadastro de produtos, fornecedores e usuários
- Cronograma de pagamento no pedido (previsão; não duplica antecipo)

## A.4 O que ainda falta

| # | O que é | Por que importa | Tamanho |
|---|---|---|---|
| 1 | Pagar o numerário no tesouro | Importação para no caixa da aduana | MÉDIO |
| 2 | Compromisso sem produto no catálogo | Esse pedido ainda não vira estoque | MÉDIO |
| 3 | Custo desembarcado por produto | Não há custo unitário da raquete | GRANDE |
| 4 | Aceite das outras famílias de PDF | Pedido, packing, declaração e numerário já têm aceite | GRANDE |
| 5 | Painel gerencial | Sem visão executiva da operação | GRANDE |
| 6 | Aceite final e arquivar o sistema antigo | Só depois da cadeia e do custo | GRANDE |

---

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
| Cadeia | 8/10 | 80 | elos 1–8 (8 só com produto no catálogo — B.2) | 9,10 FALTA |
| Financeiro | 5/5 | 100 | adiantamento; liquidar crédito; fatura→conta; custo BRL=soma câmbios; cronograma no pedido | — |
| Ingestão | 5/7 | 71 | pipeline; aceite pedido PDF; aceite packing PDF; aceite Doganale PDF; aceite Numerário PDF | Fattura (A0 fechou elo 3, não este n); planilha |
| Logística | 2/2 | 100 | embarque manual; packing preenche volumes | — |
| Aduana/estoque | 2/3 | 67 | módulo operável na mão; PDF preenche | numerário se paga |
| Custo | 0/1 | 0 | — | custo por produto |
| Painel | 0/1 | 0 | — | painel executivo |

## B.1 Estado atual

| Item | Valor |
|---|---|
| Versão | **0.5.125** — **MDM-UX DONE**; Elo 8 ENCERRADO; cadeia **8/10 = 80%**; Aduana **2/3**; Ingestão **5/7** |
| Fundação · Order-to-Pay (Inc-1…6) · Horizon A | **DONE** — [`etapa-inc-6/`](docs/v2/etapa-inc-6/) · [`etapa-9/`](docs/v2/etapa-9/) · [`etapa-9v/`](docs/v2/etapa-9v/) |
| Logística (J#4) + Document Readiness | **DONE** — [`etapa-j4/`](docs/v2/etapa-j4/) · [`etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| Aduana + Inventory (J#5) | **DONE**; financeiro Customs **PARTIAL** — [`etapa-j5/`](docs/v2/etapa-j5/) |
| Ingestão (J#3) | I1–I7 **ENTREGUE**; J3-RUX Ordine **CONCLUÍDA** — [`etapa-j3/`](docs/v2/etapa-j3/) |
| J4-FIN | FIN-0…FIN-4 **DONE**; **A0 DONE** — [`etapa-j4-fin/`](docs/v2/etapa-j4-fin/) |
| Elo 7 (chegada / declaração / impostos / nacionalização) | **DONE** + aceite UI **PASS** — [`etapa-elo-7/`](docs/v2/etapa-elo-7/) |
| Elo 8 (nacionalizado → estoque) | **DONE / ENCERRADO** — aceite advisor 2026-08-17 — [`etapa-elo-8/`](docs/v2/etapa-elo-8/) |
| MDM-UX (cadastros mestres) | **DONE** — [`etapa-mdm-ux/`](docs/v2/etapa-mdm-ux/) |
| J#5-REC · J#6 · J#7 · J#8 · Horizon B1 | **NOT_STARTED** / ADIADO |
| Alembic head | `026_catalog_l006_tax_id` |

**Próxima ação:** **pagar numerário** (`Treasury settlement for CUSTOMS_FUNDING`). Fora: B0 / 3A / 020 / J#7 / J#8. **J#5-REC** permanece para compromisso sem Product. J#6 depois. MDM-UX **não** relançar.

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
| 8. Nacionalizado → estoque | Sim — walk operador W1–W8 (2026-08-17, código final) + **verificação final**: família 202 PDFs reais na **mesma** história UI de teste (pedido na tela → 5 PDFs no input → ARRIVED → Doganale/Print/Numerário **sem pagar** → DUIMP de ensaio rotulado → nacionalização parcial → residual recebível → entrada doméstica → saldo/posição; excesso bloqueado). **LIGADO para itens cujo produto já está no catálogo.** Compromisso sem Product **não** atravessa — depende **J#5-REC** (não apagar esta ressalva). DEC-E8-DOC: o recebimento **não** exige PDF novo. Elos 1–6 continuam na 328. | Nacionalização → GoodsReceipt DOMESTIC_IN → StockBalance / SkuPosition | **LIGADO** — condição catálogo; J#5-REC para compromisso |
| 9. Custo da raquete | — | Fatura + frete + imposto + câmbio real | **NÃO EXISTE** |
| 10. Encerrar pedido | — | CONFIRMED → CLOSED auditável | **NÃO EXISTE** (só cancelar) |

Elo composto na barra da cadeia: só é **PRONTO** quando os fatos forem **uma** história comercial/operacional, salvo exceção explicitamente aceita. Elos 1–6 e o elo 7 foram exercitados em compras de ensaio distintas (328 vs 202); isso é aceito — cada elo composto teve a sua história única. Elo 8: costura LIGADA na história 202 (PDFs do fornecedor → nacionalização → estoque na mesma UI); DEC-E8-DOC = sem PDF no receipt. J#5-REC permanece. **Não** rebaixa 8/10.

## B.3 Decisões abertas e bloqueios

| ID | Estado | Bloqueia o quê | Próxima decisão |
|---|---|---|---|
| L-001 | Aberto | Conciliação / tolerâncias | Política final na Reconciliation |
| DEC-SHIP-CANCEL | Aberto | Logistics BOOKED+ | Isolar ou resolver em incremento Logistics |
| L-003 | Aberto | Credit / CC BR | Isolar na fase Treasury |
| L-005 | Aberto | RBAC `reporting:read` | Validar matriz de papéis |
| DEC-ACCONTO-INVOICE | Pendente | Tipagem Fattura | Blueprint §5.7 |
| DEC-ENDERECO | Aberto | Modelo de endereços | — |
| DEC-CLOSE-ORDER | Provisória | Orders `CLOSED` | Até decisão explícita |
| L-007 | **Fechada (Elo 7)** | — | DUIMP/DI: sem PDF no corpus; referência de ensaio digitada e rotulada (nunca extraída) |
| E8-NAT-REVERSE-API | Aberto | Reverse nacionalização após GoodsReceipt pode duplicar saldo se chamado na API | UI oculta Reverter (DEC-E8-NAT-REVERSE = B). Não abrir `customs` → `inventory` (ciclo). Guard futuro sem ciclo |
| Fechadas | DEC-DUIMP-MULTI-SHIP · DEC-SCONTO-ITEM · DEC-FX-SCOPE · DEC-A0-ORDER-CANDIDATES · DEC-A0-AMBIGUOUS · DEC-C6-IDENTITY · DEC-C6-INVOICE-OPTIONAL · DEC-C6-LINE-MATCH · DEC-C6-COMMITMENT · DEC-C6-PLANNED-ONLY · DEC-C6-DETAIL-SOT · DEC-C6-SHIPMENT-TARGET · DEC-E7-DOGANALE-FILL · DEC-E7-IDENTITY · DEC-E7-PROCESS-TARGET · DEC-E7-ARRIVAL · DEC-E7-PRINT · DEC-E7-FUNDING-SCOPE · DEC-E7-BOUNDARY · L-007 | — | Ver Blueprint |

## B.4 Fases e próximos passos

| Fase | Status | Próxima ação | Evidência |
|---|---|---|---|
| 0B / Fundação / Order-to-Pay | DONE | — | snapshot · [`etapa-inc-6/`](docs/v2/etapa-inc-6/) |
| Logística (J#4) | DONE | — | [`etapa-j4/`](docs/v2/etapa-j4/) |
| Aduana + Inventory (J#5) | DONE | settlement CUSTOMS_FUNDING (backlog) | [`etapa-j5/`](docs/v2/etapa-j5/) |
| Ingestão (J#3) | ENTREGUE + RUX Ordine | aceite outras famílias | [`etapa-j3/`](docs/v2/etapa-j3/) |
| J4-FIN | FIN-4 **DONE**; **A0 DONE** | aguardando autorização (**não** B0) | [`etapa-j4-fin/`](docs/v2/etapa-j4-fin/) |
| Cadeia elos 4–6 | **DONE** (hardening C46-HARDEN) | — | [`etapa-cadeia-46/`](docs/v2/etapa-cadeia-46/) |
| Elo 7 | **DONE** + aceite UI **PASS** | — | [`E7_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-7/E7_ADVISOR_HANDOFF.md) |
| Elo 8 | **DONE / ENCERRADO** (aceite advisor) | backlog: `E8-NAT-REVERSE-API`; J#5-REC; Caso A; `E7-ARRIVAL-GATE`; atritos B.6 — **não** corrigir nesta fase | [`E8_ADVISOR_HANDOFF.md`](docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md) |
| MDM-UX | **DONE** | — | [`MDM_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md) |
| Costing (J#6) | ADIADO | Após aceite famílias / RUX | — |
| Dashboard (J#7) | TODO | Após Costing | — |
| Aceite final (J#8) | TODO | Após Dashboard | — |

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
| `Treasury settlement for CUSTOMS_FUNDING` | Treasury | Obrigação registrada; liquidação é a **próxima ação** (B.1) |
| J#5-REC | Inventory / Catalog | Compromisso sem Product **não** atravessa ao estoque. **Não** nesta fase. |
| Elo 8 Caso A (entreposto / BONDED_IN + RECLASS na UI) | Inventory UI | 2026-08-17 — select congelado `DOMESTIC_IN`; domínio/API intactos; **não** alargar nesta campanha |
| Elo 8 atrito — qty proposta não reseta ao residual novo | Inventory UI | 2026-08-17 — walk W4; **não** polir nesta campanha |
| Elo 8 atrito — auditoria coluna Quem mostra `1` | Audit / Identity | 2026-08-17 — walk W8; actor opaco na tabela do processo; **não** polir nesta campanha |
| E7-ARRIVAL-GATE | Customs | Nacionalização hoje **não** exige Shipment ARRIVED. Campanha demonstra chegada; **não** implementa a trava. Avaliar se chegada física/documental deve ser precondição |
| MINOR_BACKLOG UI Horizon A | UI sob pedido | Aceite fechado |
| Backlog J#5 residual (seed aduana/estoque; stubs SkuPosition) | Identity / Reporting | [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md) |
| SCR-028 hub FX | UI futuro | Sem rota `/fx` |
| Horizon B1 | Externo | NOT_STARTED |

## B.7 Histórico recente

| Rev | Resumo | Evidência |
|---|---|---|
| **0.5.125** | **MDM-UX DONE** (PATCH + list-report + 026 L-006/`tax_id` + Users UI; walk 61 SKUs); Alembic **026**; barras **inalteradas** 8/10; próxima = pagar numerário | [`MDM_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md) |
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
