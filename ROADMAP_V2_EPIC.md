# EPIC Controle V2 — Roadmap operacional

> Fonte operacional: estado, sequência, gates, ADRs, bloqueios e próximos passos.
> Destino de produto: [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md).
> Índice: [`docs/README.md`](docs/README.md).
> Histórico até Inc-6: [`docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md`](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md) (**imutável**).
> Runtime/layout/start: [`README.md`](README.md) · método: [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc).

| Campo | Valor |
|---|---|
| Versão | **0.5.106** — §0: 1a/1b compromisso→SKU; logística ~50%; elo encerrar |
| Atualização | **2026-08-12** |
| Última entrega | Investigação compromisso→SKU; §0 ajustada; próxima **FIN-4** inalterada |
| Próxima ação | **FIN-4** quando autorizado; uso 589 continua não-gate; **não** 3A/020/J#6/J#5-REC |

**Nota:** a numeração J#3/J#4/J#5 é identificador histórico de rastreabilidade (REQ/ADR). A **ordem de execução** vigente é J#4 → J#5 → J#3 → J#6….

---

## 0. Onde estamos

Resumo para o operador. **Não é fonte de verdade** — o estado canônico continua no §1. Atualizar esta seção junto com o §1 a cada entrega.

Módulos verdes não significam compra real andando. Logística, aduana e estoque estão prontos **como módulos**, cada um com a própria massa de teste. Nenhuma compra percorreu pedido → pagamento → embarque → aduana → estoque → custo da raquete.

### 0.1 O que o sistema já faz

Só o que tem aceite ou teste. Se está pronto no papel com ressalva, a ressalva vai na linha.

- Importar o pedido de compra do fornecedor (PDF Ordine) → vira pedido confirmado. Sem SKU de catálogo, a linha fica como **compromisso** (código e quantidade, sem produto). O 589 está assim.
- Montar o pedido na mão, com produto de catálogo, confirmar e faturar.
- Registrar adiantamento em euro com câmbio e reais gastos. Vira **crédito do pedido**, não conta a pagar. Vários adiantamentos no mesmo pedido.
- Importar a Fattura (informando o pedido) → fatura com quantidade e preço **do PDF**, vencimentos literais, banco/IBAN, contas a pagar. Só funciona se o pedido tiver linha de produto. Fatura avulsa ainda nasce com a quantidade do pedido; o operador corrige no rascunho.
- Aplicar o crédito **daquele** pedido na conta a pagar e pagar o saldo, com câmbio próprio do saldo. Não aplica sozinho; não vaza para outro pedido.
- Ver no pedido quanto foi pedido / faturado / ainda disponível (quantidade emitida).
- Registrar embarque, volumes e prestador **na mão**, a partir das linhas do pedido (não da fatura).
- Abrir processo aduaneiro, declaração, nacionalização e posição de estoque por SKU — exercitado com dados montados no próprio módulo. O numerário **registra** a obrigação; **não se paga** pelo tesouro desta versão.
- Filas de contas a pagar, cockpit do pedido, câmbio comercial.

### 0.2 A cadeia de ponta a ponta

Cada elo: funciona? provado com documento real ou só com amostra do módulo? o que atravessa? costura com o próximo.

| Elo | Funciona hoje? | Provado com dado real? | O que atravessa | Costura com o próximo |
|---|---|---|---|---|
| 1. Pedido entra (PDF ou manual) | Sim | **Sim** — Ordine 589 → pedido 31 confirmado | PDF → pedido (fornecedor, total, linhas) | **FRÁGIL** — linha sem catálogo vira compromisso, não SKU |
| 2. Adiantamento → crédito no pedido | Sim | Amostra + ensaio no 589; o 589 está zerado | Pagamento amarrado ao pedido + câmbio | **LIGADO** ao crédito; **FRÁGIL** até existir conta a pagar |
| 3. Fattura → conta a pagar | Sim, se o pedido tiver SKU | Amostra (pedido fabricado com produto). **Não** o 589 | Fatura + vencimentos + IBAN, amarrados ao pedido que o operador digitou | **FRÁGIL** — a Fattura não traz o número do Ordine |
| 4. Crédito + saldo → conta quitada | Sim, no mesmo pedido | Amostra 244, não o 589 | Alocação do crédito + pagamento do resto | **FRÁGIL** — o “reais gastos” da parcela **não soma** o câmbio do adiantamento |
| 5. Quantidade faturada abate o pedido | Sim, em linha de produto | Amostra 14.600 → 200 faturadas → 14.400 | Item da fatura → item do pedido | **NÃO EXISTE** no 589 (não há linha faturável) |
| 6. O faturado vira volumes / packing | Embarque **manual** sim | Módulo logística com massa própria | Hoje: quantidade do **pedido**, não da fatura. Packing do PDF cria embarque **vazio** | **NÃO EXISTE** — operador redigita do outro lado |
| 7. Chegada, DUIMP, impostos, nacionalização | Sim, no módulo | Módulo aduana com massa própria | Processo ↔ embarque e ↔ item da fatura, **ligados na mão**. Doganale do PDF cria processo **vazio** | **FRÁGIL** |
| 8. Nacionalizado → estoque por SKU | Sim, se houver produto de catálogo | Módulo estoque com massa própria | Nacionalização → recebimento → posição do SKU | **NÃO EXISTE** a partir do compromisso (sem produto) |
| 9. Custo da raquete (fatura + frete + imposto + câmbio real) | Não | — | Deveria: euros da Fattura + frete + impostos + reais do adiantamento **e** do saldo → custo unitário | **NÃO EXISTE** |
| 10. Encerrar o pedido de forma auditável | Não | — | Deveria: pedido confirmado → encerrado, com quem/quando/por quê | **NÃO EXISTE** — o estado existe no modelo; não há comando, tela nem decisão fechada |

### 0.3 Se o Ricardo levar o Ordine 589 até a raquete no estoque, hoje

A lista é **longa**. Esta é a ordem em que as paradas aparecem — e é o plano do que falta.

1. **Trava já no faturar.** O 589 está confirmado com duas linhas de compromisso (14.600 e 2.000), sem produto de catálogo. Pedido confirmado **não aceita** incluir SKU. A Fattura responde *nenhuma linha faturável*. Cancelar e refazer perde este pedido; não há conversão compromisso → produto.
2. Mesmo com SKU: a Fattura **não cita** o número do Ordine. O operador informa o pedido na mão (já existe; não trava, mas não amarra sozinho).
3. Adiantamento **pode** ser registrado agora. Aplicar o crédito só depois da conta a pagar.
4. Pagar o saldo funciona na amostra. O número de reais da parcela **mente** se houve adiantamento — não soma os câmbios.
5. Embarque: packing list **não** preenche volumes; a quantidade olha o pedido inteiro, não o que foi faturado. Operador monta na mão.
6. Aduana: a Doganale cria processo vazio. Ligar fatura e embarque é manual. O numerário vira conta que **o tesouro recusa pagar**.
7. Estoque: nacionalização exige produto de catálogo — o 589 não tem.
8. Custo unitário da raquete: **não há módulo**.

### 0.4 O que falta (por costura, o que destrava a cadeia primeiro)

Esforço: **PEQUENO** (1–2 fatias) / **MÉDIO** (3–6) / **GRANDE** (7+). Estimativa desta revisão, pelo código — não pelo tamanho no papel.

1. **Vincular SKU na linha de compromisso** (pedido já confirmado, operador escolhe o produto, confirma na cara). Sem isso o 589 não fatura. **Não** exige traduzir sozinho o código do pedido no código de barras da fatura. **MÉDIO.** A tela hoje promete que o produto chega na importação da Fattura — isso também não existe; o sítio (pedido ou Fattura) é decisão da fatia. **Identidade automática** código do pedido → código de barras continua **GRANDE** e **não** é pré-requisito do 589.
2. **Faturado / packing → volumes preenchidos** — hoje o operador redigita. Sem isso a mercadoria não anda para a aduana com o dado da compra. **MÉDIO.**
3. **Doganale / packing → processo e embarque preenchidos** — hoje nascem cascas vazias. **MÉDIO.**
4. **Reais verdadeiros do pedido** (adiantamento + saldo) e **cronograma no pedido** (previsão substituída pela Fattura, sem duplicar o antecipo). Não destrava o 589, mas o custo que o financeiro lê está errado. **MÉDIO.** (próxima fatia autorizável)
5. **Pagar o numerário no tesouro** — obrigação existe; liquidação não. Importação real para no caixa da aduana. **MÉDIO.**
6. **Custo desembarcado por SKU** — fatura + frete + imposto + câmbio real. **GRANDE.** Adiado de propósito; código de cálculo **não existe**.
7. **Aceite das outras famílias de documento** — Ordine aceito. Fattura tem commit técnico (quantidade do PDF, IBAN, pedido obrigatório) **sem** aceite de família. Packing, Doganale, Numerário, planilha: pipeline técnico, **sem** aceite; commit ainda pode gravar estado pela metade. **GRANDE** se for família a família; não destrava o 589 antes do item 1.
8. **Painel gerencial** — **GRANDE.** Não iniciado.
9. **Aceite final e arquivar o sistema antigo** — **GRANDE.** Só depois da cadeia e do custo.

Dívidas nomeadas: **IBAN resolvido** (extraído depois de Pagamento, gravado na fatura e na conta). O buraco silencioso de linha da Fattura **não aparece mais no código**; o que restou é linha não lida, visível ao operador (ex.: SKU curto). Recálculo percentual: Fattura do PDF fica em **valor literal**; percentual continua só em fatura que não veio do documento. Commit “pela metade” em Numerário / planilha / dossiê: **ainda aberto** (Ordine e Fattura já fecham tudo-ou-nada).

Faturar a quantidade do PDF (não a do pedido): **já feito** nesta data — não está nesta lista.

### 0.5 Barra de progresso

Percentual = o quanto aquilo serve numa compra real, não o quanto o módulo está “DONE” no §1.

```
Cadeia ponta a ponta   ██░░░░░░░░   ~20%  pedido real entra; o resto foi provado em amostra isolada
Ciclo financeiro       ███████░░░   ~70%  falta somar câmbios e cronograma; 589 não é faturável
Ingestão               █████░░░░░   ~50%  Ordine aceito; outras famílias só técnicas, sem aceite
Logística              █████░░░░░   ~50%  embarque manual existe; packing/fatura não preenchem volumes
Aduana / estoque       ██████░░░░   ~65%  PDF cria casca vazia; numerário não se paga; precisa SKU
Custo desembarcado     ░░░░░░░░░░     0%  sem código
Painel gerencial       ░░░░░░░░░░     0%  não iniciado
```

Critério inalterado: compra real, não módulo DONE. Logística **não** é 100% — o 100% era leitura do recorte aceito; numa compra o operador redigita. Aduana/estoque ~65% (não ~80%): mesmo vício. Ingestão ~50%; financeiro ~70%. A pergunta “quanto falta” é a barra da **cadeia**.

---

## 1. Estado atual

**Fonte única de status.**

| Item | Valor |
|---|---|
| Fundação | **DONE** |
| Order-to-Pay (J#2) / Inc-1…Inc-6 | **DONE** |
| Logística (J#4) | **DONE** |
| Patch J4-UX1 (modal + prestador) | **DONE** |
| Patch J4-UX2 (Document Readiness A1 Logistics) | **DONE** |
| Document Readiness A2 (Orders/Billing) | **DONE** |
| DR-UX (fechamento operacional/visual UI) | **DONE** — aceite Logistics **ACCEPTED_WITH_MINOR_BACKLOG**; patch H-FIX 0.5.54 |
| Document Readiness (campanha capacidade) | **DONE** |
| Aduana + Inventory (J#5) | **DONE** — I5-0…I5-6 + patch fechamento C0…C5; SC-07/09/10; fluxo financeiro Customs **PARTIAL** |
| Ingestão (J#3) | I1–I7 **ENTREGUE**; aceite UIV **REJECTED**; **J3-RUX Ordine CONCLUÍDA** (3B…3F-POST-3) |
| **J4-FIN** (ciclo financeiro) | FIN-0…FIN-1C-FIX-2 **DONE** · FIN-1 ACEITO · **FIN-2/FIN-3 DONE** · **FIN-3B DONE** · FIN-4 **NOT_STARTED** |
| **J#5-REC** (reconciliação compromisso↔SKU) | **NOT_STARTED** (campanha futura; **ex-rótulo “FIN-4” antigo** — ≠ FIN-4 cronograma Order) |
| Etapa 9 / 9V (Horizon A) | **DONE** |
| Visual Horizon A | **ACCEPTED_WITH_MINOR_BACKLOG** |
| Horizon B1 (artefato externo) | **NOT_STARTED** — não incorporar sem decisão humana |
| Baseline J#4 | **2026-07-31** — evidências em [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) |
| Evidência J#5 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| Evidência J#3 | [`docs/v2/etapa-j3/`](docs/v2/etapa-j3/) |
| Evidência J4-FIN | [`docs/v2/etapa-j4-fin/`](docs/v2/etapa-j4-fin/) |
| Alembic head | `023_invoice_payable_payment_destination` |
| Foothold ingestão | I0 quarantine + I1 staging IR + **I3 vertical Ordine→Order DRAFT** + ledger idempotente + **I4 Fattura→Invoice DRAFT** + **I5 Dossiê 202** + **I6 Numerário** + **I7 XLSX/F328/métricas/E2E** |
| Docs intermediários | Status em `etapa-*` pode ser histórico; **canônico** = este Roadmap |

### Próxima ação autorizada (única)

**J4-FIN FIN-3B DONE** — Fattura commit fatura qty e preço do PDF (`replace_items` após match; 50+150 no mesmo OrderItem; Disponível = ordered − ISSUED; 422 SKU/qty/COMMITMENT; rastro de divergência de preço). Pytest **492**. Sample FIN3B-244 limpo; 589 preservado.

- UI: [`J4_FIN3B_UI.md`](docs/v2/etapa-j4-fin/J4_FIN3B_UI.md).
- Handoff: [`J4_FIN3B_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN3B_ADVISOR_HANDOFF.md).
- **Próxima:** **FIN-4** (custo BRL = soma das execuções; cronograma) quando autorizado. Uso 589 continua não-gate.
- 3A/020/J#6/J#5-REC **não** iniciar.
---

## 2. Mapa do programa

Ordem de execução (IDs preservados): **J#4 → J#5 → J#3 → J#6 → J#7 → J#8**.

| Fase | Objetivo | Status | Gate de saída | Evidência | Próxima ação |
|---|---|---|---|---|---|
| 0B — Contrato | Roadmap + Blueprint aprovados | **DONE** | APPROVED 2026-07-22 | snapshot 0.5.42 | — |
| Fundação | Layout `v1/`+`v2/`; Identity/Audit/Documents; harness | **DONE** | Gates Fundação | snapshot §N | — |
| Order-to-Pay (J#2) | Orders + Billing + Treasury; equivalência `parse_it` | **DONE** | DoD J#2 (Inc-1…Inc-6) | [`docs/v2/etapa-inc-6/`](docs/v2/etapa-inc-6/) | — |
| Logística (J#4) | Shipment + packages/refs/summaries; operação manual | **DONE** | DoD §§5.10, 7.7–7.8 + Planning | [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) | — |
| Aduana + Inventory (J#5) | ImportProcess 1:N; estoque; Numerário | **DONE** | I5-0…I5-6 + patch C0…C5; SC-07/09/10; UI ACCEPTED_WITH_BACKLOG | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) | — |
| Ingestão (J#3) | Pipeline + adapters + commit via APIs públicas + aceite UI | I1–I7 **ENTREGUE**; **J3-RUX Ordine CONCLUÍDA** | Golden + commit + RUX Ordine ACCEPTED | [`docs/v2/etapa-j3/`](docs/v2/etapa-j3/) | **J4-FIN** (FIN-4) |
| Costing / Reconciliation (J#6) | Landed cost + pares | **ADIADO** | Equivalência de cálculo vs V1 | — | Após RUX-5 ACCEPTED* |
| Dashboard (J#7) | Read models | **TODO** | DoD | — | Após Costing |
| Aceite final (J#8) | SC-* + arquivar V1 | **TODO** | V2 aceita; V1 arquivada | — | Após Dashboard |
| UI Horizon A | Shell + 12 SCR + polish adaptativo | **DONE** | ACCEPTED_WITH_MINOR_BACKLOG | [`docs/v2/etapa-9/`](docs/v2/etapa-9/) · [`docs/v2/etapa-9v/`](docs/v2/etapa-9v/) | MINOR_BACKLOG sob pedido |

Detalhe histórico: snapshot 0.5.42. Inc-6 checkpoints I6-0…I6-4: todos PASS. Aceite SC-01…SC-17: Blueprint §15 (Order-to-Pay cobriu SC-01…04 no E2E Inc-6). SC-05/SC-06 exercitáveis via Logistics J#4. **SC-07/09/10 = aceitos em J#5** (I5-6).

---

## 3. Fase concluída — Logística J#4 (DONE)

**Status: DONE.** Evidências: [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/).

| Campo | Conteúdo |
|---|---|
| Objetivo | Embarques manuais via API/UI (Blueprint §§5.10, 7.7–7.8, 8.15; ADR-12) |
| Entregue | Migration `007`; módulo `logistics`; FE `/shipments`; `e2e:logistics` |
| DECs | Consolidadas no Blueprint 0.2.12 (incl. DEC-SHIP-PROVIDER); **DEC-SHIP-CANCEL aberta** para BOOKED+ |
| L-001 | Tolerância provisória em `logistics/divergence.py` — política final na Reconciliation |
| Patch J4-UX1 | Modal controlado; `LogisticsProvider`; FK + snapshot; BOOKED exige modal+prestador; FE selects + `/logistics-providers` |
| Patch J4-UX2 | PackageContent snapshots; batch packages; DocumentSummary provenance; UI volumes/docs; evidência [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| Fora (J#4) | Ingestion; Customs; Inventory; Horizon B1; Packing List automático; seed de prestador real (nome não comprovado) |
| Document Readiness A2 | Orders/Billing dates/unit/notes/docs — **DONE** (mesmo pacote de evidência `etapa-doc-readiness`) |

---

## 3b. Fase concluída — Aduana + Inventory J#5 (DONE)

**Status: DONE** (core I5-0…I5-6 + patch fechamento operacional). Evidências: [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/). Blueprint **0.2.16**. Aceite UI: **ACCEPTED_WITH_BACKLOG**. Backlog nomeado: **`Treasury settlement for CUSTOMS_FUNDING`**.

| Campo | Conteúdo |
|---|---|
| Objetivo | ImportProcess/DUIMP; Doganale; Numerário; nacionalização; estoque derivado; SC-07/09/10 |
| Entregue | Migrations **011…015**; módulos `customs`/`inventory`; FE `/customs`, `/inventory/*`; papéis `aduana`/`estoque`; `e2e:j5` |
| Aceite | SC-07/09/10 — evidência [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md); relatório [`J5_EXECUTION_REPORT.md`](docs/v2/etapa-j5/J5_EXECUTION_REPORT.md) |
| Fora | J#3 staging/parser; J#6 landed cost; Payment allocation Customs (gap intencional) |

### Checkpoints

| ID | Escopo | Status | Gate |
|---|---|---|---|
| **I5-0** | Decisões Blueprint; scaffold `customs`/`inventory` + public stubs; module_graph; RBAC; docs etapa-j5 | **DONE** | arch + `test_j5_i5_0_scaffold` |
| **I5-1** | Migration **011**: ImportProcess + joins + alocações item + lifecycle DRAFT/SUBMITTED/CANCELLED + UI `/customs` | **DONE** | pytest + vitest + e2e:j5-i5-1 |
| **I5-2** | Migration **012**: Doganale versionada + divergências + UI | **DONE** | supersede / is_current; e2e:j5-i5-2 |
| **I5-3A** | Migration **013**: CustomsFundingRequest + Payee + bases/tax/expense + UI | **DONE** | empty≠0; structured×declared; confirm → I5-3B Payable |
| **I5-3B** | Migration **014** (Billing): Payable extension + FundingPayableLink + regressão Inc-6/AP | **DONE** | suite regressão PASS; gap alocação Payment documentado |
| **I5-4** | Migration **015**: Nationalization + Inventory + SkuPosition + UI | **DONE** | SC-09/SC-10; bonded pré-nac; oversubscription 409 |
| **I5-5** | UX transversal SCR-019/022/024/025 (+ papéis `aduana`/`estoque`) | **DONE** | Vitest + pytest roles + e2e smoke |
| **I5-6** | E2E + screenshots 1366 + aceite | **DONE** | e2e:j5 (4); SC-07/09/10; Roadmap J#5 DONE |

### DECs J#5

| ID | Estado |
|---|---|
| DEC-DUIMP-MULTI-SHIP | **Fechada** (I5-0) — process 1:N shipment + UNIQUE + ShipmentItem alloc |
| L-007 DI vs DUIMP | Aberta — DI = tipo documental opcional |

---

## 3c. Ingestão J#3 — base ENTREGUE / J3-RUX Ordine CONCLUÍDA

**Status:** I1→I7 técnicos **ENTREGUE**; J3-UIV **REJECTED** (2026-08-05); campanha **J3-RUX Ordine CONCLUÍDA** (3B…3F-POST-3). Evidências: [`docs/v2/etapa-j3/`](docs/v2/etapa-j3/). Alembic head global **022** (FIN-1); commitment lines **021**.

| Campo | Conteúdo |
|---|---|
| Objetivo | Central profissional: quarantine→extração→staging→revisão→preview→commit via APIs públicas |
| Escopo base | P0…I7 DONE (entrega técnica) |
| Aceite UIV | **REJECTED** — viewer PDF.js modern, matching tipado, can_commit/skip_order, catálogo vazio, UX técnica |
| J3-RUX Ordine | **CONCLUÍDA** — [`J3_EXECUTION_PLAN.md`](docs/v2/etapa-j3/J3_EXECUTION_PLAN.md) |
| Ponte | **J4-FIN** (FIX-1 DONE; próxima **G6 Ricardo**) |
| Handoff campanha | [`J3_EXECUTION_CAMPAIGN_HANDOFF.md`](docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md) |

### Checkpoints (R5)

| ID | Escopo | Status | Gate |
|---|---|---|---|
| **J3-P0-a** | Forense corpus; hashes; annotations origin; PL Grouped; F181; F328 | **DONE** | Inventário + evidências reproduzíveis |
| **J3-P0-b** | Matrizes + pacote de decisões (sem implementação) | **DONE** | Matrizes + recomendações; **ratificadas** no handoff |
| **J3-I0** | Fundação quarantine/occurrence/hash/RBAC | **DONE** | Migration 016 + gates I0 |
| **J3-I1** | Staging IR + provenance + review APIs | **DONE** | Migration 017; sem escrita owners |
| **J3-I2** | Shell UI fila/workspace/viewer | **DONE** | Shell + contrato estável p/ dados reais |
| **J3-I3** | Vertical Ordine 589 + ledger mínimo | **DONE** (018) | 23 pytest passed; adapter + preview + commit + idempotência |
| **J3-I4** | Fattura 202 + Order confirm explícito + Invoice DRAFT | **DONE** | 31 pytest passed; policy A/B/C1/C2; adapter + preview + commit + scadenze |
| **J3-I5** | Dossiê 202 + PL + Doganale + PrintDecl | **DONE** | Após I4 |
| **J3-I6** | Numerário + orquestração multi-owner | **DONE** | Após I5 |
| **J3-I7** | XLSX/F328/métricas/E2E; OCR backlog | **DONE** (019) | 47 pytest + 248 total; migration 019; gates completos |

---

## 4. Fases posteriores

| Fase | Resumo | Blueprint | Pré-requisito |
|---|---|---|---|
| Ingestão (J#3) | Automação transversal: arquivo→hash→adapter→staging→revisão→`public(owner)`→commit_batch; Ordine/Fattura/Packing/Doganale/Numerário/XLSX/PrintDeclaration | §§5.9, 7.2, 10 | I0…I7 **ENTREGUE**; **J3-RUX Ordine CONCLUÍDA** |
| Costing / Reconciliation (J#6) | Expense + landed cost; pares; L-001 | §§5.13–5.14, 7.12–7.16, 9 | Após J#3 (ordem programa) / Aduana DONE |
| Dashboard (J#7) | Read models; Reporting RO | §§5.15, 8.2, 12 | Costing |
| Aceite final (J#8) | SC-01…SC-17; arquivar V1 | §15 | Dashboard |

---

## 5. Decisões abertas e bloqueios

| ID | Estado | Fase afetada | Bloqueia J#5 agora? | Bloqueia J#3 (após J#5)? | Próxima decisão |
|---|---|---|---|---|---|
| L-001 | Aberto (provisória em J#4) | Conciliação / tolerâncias | Não (J#5 DONE) | Não | Política final na Reconciliation |
| DEC-SHIP-CANCEL | Aberto | Logistics BOOKED+ | Não | Não | Isolar ou resolver em incremento Logistics |
| L-003 | Aberto | Credit / CC BR avançado | Não | Não | Isolar na fase Treasury |
| L-005 | Aberto | RBAC `reporting:read` | Não | Não | Validar matriz de papéis |
| DEC-ACCONTO-INVOICE | Pendente | Billing / ingestão Fattura | Não | **Possível** | Tipagem `PROFORMA\|ACCONTO\|FINAL` — Blueprint §5.7 |
| DEC-DUIMP-MULTI-SHIP | **Fechada** (I5-0) | Customs multi-embarque | Não | Não | Ver Blueprint §6.6 |
| DEC-ENDERECO | Aberto | Modelo de endereços | Não | Não | — |
| DEC-CLOSE-ORDER | Provisória | Orders `CLOSED` | Não | Não | Até decisão explícita |
| DEC-SCONTO-ITEM | **Fechada** | Billing | Não | Não | `NONE\|UNIT_AMOUNT\|PERCENT`; HALF_UP 2 casas |
| DEC-FX-SCOPE | **Fechada** | Treasury FX | Não | Não | Três visões; snapshot §O.4 |
| L-007 | Aberto | DI vs DUIMP | Não | Não | Isolar; DI documental |

---

## 6. ADRs vigentes

Detalhe: snapshot 0.5.42 §M.1 · impacto normativo: Blueprint.

| ADR | Decisão resumida | Impacto atual |
|---|---|---|
| ADR-01 | Monólito modular; stack atual | Stack V2 |
| ADR-02 | Alt. B — portar calculadores com testes | Ingestão / Costing / FX |
| ADR-03 | Separar Order / Shipment / ImportProcess | Modelo J#4+ |
| ADR-04 | Layout `root/{docs,ROADMAP,v1,v2}`; bancos/portas separados | Layout vigente |
| ADR-05 | OpenAPI + client TS gerado | Drift check |
| ADR-06 | Liquidação só via Payable | Billing/Treasury |
| ADR-07 | StockBalance derivado | Inventory J#5 |
| ADR-08 | `document_links` por Documents | Documents sem ciclos |
| ADR-09 | Estados por agregado | Todos os módulos |
| ADR-10 | Conteúdo atual descartável; zero migração de dados | Premissa definitiva |
| ADR-11 | Orders ← Billing ← Treasury; Expense em Costing | Ownership |
| ADR-12 | DUIMP→Invoice 1:N; Shipment sem `order_id` | Customs/Logistics |
| ADR-13 | `.env`/deps isolados; regra Cursor; venv V2 | Runtime |
| ADR-14 | Package-by-domain; grafo acíclico; proibição V2→V1 | Arch gates |
| ADR-15 | Audit atômico — mesma UoW | Fundação+ |
| ADR-16 | V1 congelada (2026-07-22) | Guarda `v1/**` |

GATE-FONTES fechado (ADR-10).

---

## 7. Manutenção do Roadmap

Gates técnicos transversais (Git, bancos, arch, OpenAPI, Audit, evidências): [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc). Atualizar este Roadmap **após** gates da entrega; status só com evidência.

| ID | Regra |
|---|---|
| **R1** | Fase concluída → status, gate, evidência e resumo curto aqui; detalhe em `docs/v2/etapa-*`. **Não** adicionar ao snapshot 0.5.42. |
| **R2** | Pendência de execução → §8 com ID. |
| **R3** | Estado canônico **somente** no §1. A §0 é resumo de operador — não substitui o §1. |
| **R4** | Se > ~600 linhas: condensar DONE; mover detalhe para evidências. **Não** alterar o snapshot. **Não** criar snapshot a cada entrega. |
| **R5** | Ao **iniciar** execução (após plano), decompor checkpoints na seção da fase **antes** de executar. |
| **R6** | A **§0** é atualizada **junto com o §1** a cada entrega material (capacidades, costuras, barras, paradas da cadeia). |

Novo snapshot integral: só com decisão explícita excepcional.

---

## 8. Backlog fora da fase

| Item | Destino | Bloqueia J#5? | Observação |
|---|---|---|---|
| MINOR_BACKLOG UI (InvoiceDetail LOC; row-highlight; aceite SCR-008; virtualização) | UI sob pedido | Não (DONE) | Aceite Horizon A fechado |
| **`Treasury settlement for CUSTOMS_FUNDING`** | Treasury | Não | Alt. B — obrigação registrada; liquidação fora desta release ([`DEC_ALT_B`](docs/v2/etapa-j5/patch-close/DEC_ALT_B_CUSTOMS_PAYMENT.md)) |
| Backlog J#5 residual (users seed aduana/estoque; stubs SkuPosition) | Identity / Reporting | Não | [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md) |
| SCR-028 hub FX | UI futuro | Não | TARGET; sem rota `/fx` |
| Horizon B1 (externo) | Artefato externo | Não | NOT_STARTED |
| Débitos FX (N:M; Σ BRL; weekend provider; LOC FxPanels) | Polish Treasury | Não | Aceitos no Inc-4 DONE |
| Capacidades Blueprint futuras | J#3+ | — | — |

---

## 9. Histórico recente

| Rev | Resumo | Evidência |
|---|---|---|
| **0.5.106** | §0: vínculo SKU manual MÉDIO ≠ identidade automática GRANDE; logística ~50%; aduana ~65%; elo 10 encerrar; próxima ação inalterada | [`COMPROMISSO_SKU_ADVISOR_HANDOFF.md`](docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/COMPROMISSO_SKU_ADVISOR_HANDOFF.md) |
| **0.5.105** | ROADMAP-VIS: §0 Onde estamos (cadeia + costuras + paradas do 589); R6; próxima ação inalterada (FIN-4) | este arquivo |
| **0.5.104** | J4-FIN FIN-3B **DONE** (qty+preço PDF; 2 InvoiceItems 50+150; rastro preço; 492 pytest; sample limpo; 589 intacto) | [`J4_FIN3B_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN3B_ADVISOR_HANDOFF.md) |
| **0.5.103** | J4-FIN FIN-3 + FIN-2 **DONE** (AMOUNT lock; IBAN 023; Policy A order_id; allocate order-scoped; 486 pytest; UI sample 244 limpo) | [`J4_FIN23_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN23_ADVISOR_HANDOFF.md) |
| **0.5.102** | J4-FIN FIN-1C-FIX-2 **DONE** (vocab N2; estados alocação; empty Fattura; atalho adiantamentos; sugestão BRL guarda; 473 pytest) | [`J4_FIN1C_FIX2_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN1C_FIX2_ADVISOR_HANDOFF.md) |
| **0.5.101** | J4-FIN FIN-1C-FIX-1B **DONE** (reset datas pós-registro; uploads câmbio≠pedido; 471 pytest; 589 limpo; G6 roteiro válido) | [`J4_FIN1C_FIX1B_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN1C_FIX1B_ADVISOR_HANDOFF.md) |
| **0.5.100** | J4-FIN FIN-1-G6-DRYRUN **DONE** (ensaio UI G6 pelo agente; passos 1–9; 589 limpo; pronto para valores reais) | [`J4_FIN1_G6_DRYRUN_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN1_G6_DRYRUN_ADVISOR_HANDOFF.md) |
| **0.5.99** | J4-FIN FIN-1C-FIX-1 **DONE** (cockpit order-scoped; CANCELLED residual —; KPI adiantado; foco Motivo; limpeza 589; 471 pytest) | [`J4_FIN1C_FIX1_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN1C_FIX1_ADVISOR_HANDOFF.md) |
| **0.5.98** | J4-FIN FIN-1C-UX **DONE** (FINDINGS G6/N1–N4; FIN-4 cronograma Order registrada NOT_STARTED; ≠ J#5-REC; aviso FIN-3 ORDER_SCHEDULE canônico) | [`J4_FIN1C_UX_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN1C_UX_ADVISOR_HANDOFF.md) |
| **0.5.97** | J4-FIN FIN-1B **DONE** (cancel adiantamento no painel; FX void audit sem migration; 468 pytest; 589 limpo) | [`J4_FIN1B_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN1B_ADVISOR_HANDOFF.md) |
| **0.5.96** | J3-RUX Ordine **CONCLUÍDA**; J4-FIN FIN-0/FIN-1 **DONE** (Payment.order_id; adiantamento N×; zero Payable; Alembic **022**) | [`J4_FIN_PLAN_ADVISOR_HANDOFF.md`](docs/v2/etapa-j4-fin/J4_FIN_PLAN_ADVISOR_HANDOFF.md) |
| **0.5.95** | RUX-3F-POST-3 **DONE**; BLOCKER V5 **fechado** (`MATH_LINE_EDIT_DIVERGENCE` WARNING; 457 passed) | [`J3_RUX_3F_POST3_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3F_POST3_ADVISOR_HANDOFF.md) |
| **0.5.94** | RUX-3F-POST-2 **DONE**; **BLOCKER V5** math não revalida após PATCH qty (sem conserto) | [`J3_RUX_3F_POST2_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3F_POST2_ADVISOR_HANDOFF.md) |
| **0.5.93** | RUX-3F **ACEITO** + RUX-3F-POST **DONE** (V1 sem DDT; V2 math vivo; V3 456; V4 actor admin) | [`J3_RUX_3F_POST_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3F_POST_ADVISOR_HANDOFF.md) |
| **0.5.92** | RUX-3F **DONE** (Faturas COMMITMENT honestas; I3 qty+header; I0 sem chave Ordine; I2 relatório; 589 preservada) | [`J3_RUX_3F_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3F_ADVISOR_HANDOFF.md) |
| **0.5.91** | RUX-3C-DRYRUN **DONE** (UI Ordine 1–15+S1–S3; CONFIRMED limpo com mandato; epic_v2 restaurado) | [`J3_RUX_3C_DRYRUN_UI.md`](docs/v2/etapa-j3/J3_RUX_3C_DRYRUN_UI.md) |
| **0.5.90** | RUX-3C-DRYRUN **BLOCKED** (pré-voo: Order 589 CONFIRMED; reset abortou; jornada não executada) | [`J3_RUX_3C_DRYRUN_UI.md`](docs/v2/etapa-j3/J3_RUX_3C_DRYRUN_UI.md) |
| **0.5.89** | RUX-3E **DONE** (testes DELETE/colisão/edição; code≠external_ref; REJECTED honesto; epic_v2 limpo; 455 pytest) | [`J3_RUX_3E_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3E_ADVISOR_HANDOFF.md) |
| **0.5.88** | RUX-3D **DONE** (colisão código; Resumo editável; DELETE IR; fila PT; P0 ING-589 já existia) | [`J3_RUX_3D_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3D_ADVISOR_HANDOFF.md) |
| **0.5.87** | RUX-3C-FIX **DONE** (D1=uvicorn stale skip_item; restart+UI Q3=B+zoom+sem tech panel; limpeza epic_v2) | [`J3_RUX_3C_FIX_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3C_FIX_ADVISOR_HANDOFF.md) |
| **0.5.86** | RUX-3B-2b **DONE** (UI jornada Ordine; 6 screenshots; E2E; ERROR dismiss+Audit; 452 pytest); próxima = RUX-3C manual | [`J3_RUX_3B_2B_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3B_2B_ADVISOR_HANDOFF.md) |
| **0.5.85** | RUX-3B-2a **DONE** (Ordine commit → COMMITMENT + create_supplier intent; unit PZ; 451 pytest; sem UI) | [`J3_RUX_3B_2A_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3B_2A_ADVISOR_HANDOFF.md) |
| **0.5.84** | RUX-3B 1/2 **DONE** (mig 021 line_kind + guards; 447 pytest) | [`J3_RUX_3B_HALF1_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_RUX_3B_HALF1_ADVISOR_HANDOFF.md) |
| **0.5.74** | J3-I7 **DONE** (XLSX adapter ordine_heroes_xlsx_v1 + migration 019 metrics + F328/181/202 regressions + E2E journey; campanha J#3 DONE; 248 pytest; OpenAPI regenerado) | [`J3_EXECUTION_CAMPAIGN_HANDOFF.md`](docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md) |
| **0.5.73** | J3-I6 **DONE** (Numerário multi-owner: solicitacao_numerario_v1 + numerario_commit_commands + 62 pytest + FE panel; I7 NOT_STARTED; OpenAPI regenerado) | [`J3_EXECUTION_CAMPAIGN_HANDOFF.md`](docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md) |
| **0.5.72** | J3-I5 **DONE** (dossiê 202: 4 adapters + annotations + reconciler + dossier_commands); I6 NOT_STARTED | [`J3_EXECUTION_CAMPAIGN_HANDOFF.md`](docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md) |
| **0.5.69** | J3-I1 **DONE** (017 staging IR); I2 **IN_PROGRESS**; OpenAPI regenerado | [`J3_EXECUTION_CAMPAIGN_HANDOFF.md`](docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md) |
| **0.5.68** | Campanha I1→I7 autorizada; regra plano-mestre em epic-v2; I1 **IN_PROGRESS**; handoff consolidado | [`J3_EXECUTION_CAMPAIGN_HANDOFF.md`](docs/v2/etapa-j3/J3_EXECUTION_CAMPAIGN_HANDOFF.md) |
| **0.5.67** | J3-I0 **DONE** (016 quarantine/Batch/Blob/Occurrence); I1 NOT_STARTED; próxima = revisão advisor | [`J3_I0_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_I0_ADVISOR_HANDOFF.md) |
| **0.5.66** | Handoff P0 (≤2 MD); decisões P0 **ratificadas**; protocolo §6.1; I0 **NOT_STARTED**; próxima = autorizar I0 | [`J3_P0_ADVISOR_HANDOFF.md`](docs/v2/etapa-j3/J3_P0_ADVISOR_HANDOFF.md) |
| **0.5.65** | J3-P0-a/P0-b **DONE** (forense+matrizes+decisões); I0 **NOT_STARTED**; próxima = revisão advisor | [`docs/v2/etapa-j3/`](docs/v2/etapa-j3/) |
| **0.5.64** | J#3 **IN_PROGRESS** (R5); checkpoints P0-a…I7; próxima = **J3-P0-a**; I0 bloqueado até aprovação advisor pós-P0 | [`docs/v2/etapa-j3/`](docs/v2/etapa-j3/) |
| **0.5.63** | Patch fechamento J#5 **DONE** (KPIs multi-moeda; drawer Alt. B; GET funding; RECLASS pareado; SC-10 UI; UI **ACCEPTED_WITH_BACKLOG**; Blueprint 0.2.16); próxima = planejar J#3 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) · [`patch-close/`](docs/v2/etapa-j5/patch-close/) |
| **0.5.62** | J#5 **DONE** (I5-6 E2E + screenshots 1366 + aceite SC-07/09/10; UI ACCEPTED_WITH_MINOR_BACKLOG); Alembic head 015; próxima = planejar J#3 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.61** | J#5 I5-5 **DONE** (UX transversal SCR-019/022/024/025; papéis `aduana`/`estoque`; labels pt-BR; Audit/DocumentActions); J#5 permanece IN_PROGRESS; próxima = I5-6 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.60** | J#5 I5-4 **DONE** (migration 015 Nationalization+Inventory+SkuPosition; UI Liberações/Recebimentos; SCR-024/025 mínimo); J#5 permanece IN_PROGRESS; próxima = I5-5 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.59** | J#5 I5-3B **DONE** (migration 014 Payable Customs + FundingPayableLink; AP denormalizado; sem redesign Treasury); próxima = I5-4 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.58** | J#5 I5-3A **DONE** (migration 013 Payee+FundingRequest+linhas; UI Numerário; confirm sem Payable); próxima = I5-3B | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.56** | J#5 I5-1 **DONE** (migration 011 ImportProcess; joins; alocações; lifecycle; UI `/customs`; e2e:j5-i5-1); sequência 011…015 documentada; próxima = revisar I5-1 → I5-2 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.55** | J#5 **IN_PROGRESS**; I5-0 **DONE** (Blueprint 0.2.15; DEC-DUIMP-MULTI-SHIP fechada; scaffolds customs/inventory; module_graph; RBAC; etapa-j5) | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.54** | DR-UX patch corretivo H-FIX **DONE** (qty wire, Provenance, Invoice 1366, download/gates/screenshots); A1/A2 DONE; próxima = planejar J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.53** | DR-UX **DONE** (UI Documents download, supplier, Logistics contents/`source_line_reference`/summary); A1/A2 capacidade DONE; aceite Logistics ACCEPTED_WITH_MINOR_BACKLOG; próxima = planejar J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.52** | Document Readiness A2 **DONE**; Blueprint 0.2.14; Alembic 010; A1+J#4 DONE; Document Readiness concluído; próxima = planejar J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.51** | J4-UX2 Document Readiness A1 **DONE**; Blueprint 0.2.13; Alembic 009; J#4 DONE; próxima = A2 Orders/Billing depois J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.50** | J4-UX1 **DONE** (modal + LogisticsProvider); Blueprint 0.2.12; J#4 permanece DONE; próxima = planejar J#5 | [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) |
| **0.5.49** | J#4 Logistics **DONE**; Blueprint 0.2.11; próxima = planejar J#5 | [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) |
| **0.5.48** | J#4 Logistics **IN_PROGRESS**; DECs `[PROPOSTA]`; checkpoints I4-0…I4-5 | este arquivo |
| **0.5.47** | Domain-first: ordem de execução J#4 → J#5 → J#3; IDs preservados; Alternativa C (core Ingestion prematuro) rejeitada | este arquivo · Blueprint 0.2.10 |
| **0.5.46** | Slim operacional: remove duplicata layout/runtime/gates genéricos; aponta README/regra/índice | este arquivo |
| **0.5.45** | Gates em `epic-v2.mdc`; DOC_DELTA; gate J#3 = commit operacional do pipeline | regra · docs/README |
| **0.5.44** | docs/README como mapa | [`docs/README.md`](docs/README.md) |
| **0.5.43** | Roadmap operacional; regra unificada; snapshot arquivado | este arquivo · regra |
| **0.5.42** | Inc-6 / Order-to-Pay DONE | [`docs/v2/etapa-inc-6/`](docs/v2/etapa-inc-6/) |
| **0.5.41** | Visual ACCEPTED_WITH_MINOR_BACKLOG; Etapa 9/9V DONE | [`docs/v2/etapa-9v/`](docs/v2/etapa-9v/) |

Changelog integral: [snapshot 0.5.42](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md). Índice de documentos: [`docs/README.md`](docs/README.md).
