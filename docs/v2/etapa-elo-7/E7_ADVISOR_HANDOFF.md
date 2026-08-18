# Elo 7 — retorno ao advisor (E7-CF)

**Etapa:** Elo 7 (E7-0…E7-4 / E7-TAX / walk / CF / **E7-UI-ACCEPT**)  
**Status da campanha:** **DONE**. Aceite UI **PASS**. Barras aplicadas no Roadmap **0.5.120** (Elo 7 PRONTO/LIGADO; cadeia 7/10; Ingestão 5/7; Aduana 2/3).  
**Runtime:** Vite `localhost:5174` → `:8082` / `epic_v2_test`. `epic_v2` só inspecionado. Pedidos 589/id31 e TESTE-CICLO-001/id34 intocados. Sem migration.

Oito decisões ratificadas e executadas: DEC-E7-DOGANALE-FILL, IDENTITY, PROCESS-TARGET, ARRIVAL, PRINT, FUNDING-SCOPE, BOUNDARY, L-007.

---

## 1. Status por fase

| Fase | Status | Evidência |
|---|---|---|
| E7-0 | **DONE** | Corpus inteiro; única história documental completa = família **202** (`P0_RUNTIME.md`) |
| E7-1 | **DONE** | Embarque #1 **ARRIVED** na UI (notice visível; sem trava de domínio) |
| E7-2 | **DONE** | Doganale 202 preenche processo #2; 7 linhas NCM; alocação de ShipmentItems; 0/1/N; sem associação silenciosa |
| E7-3 | **DONE** | Print Declaration anexado ao mesmo processo (Documents-only) |
| E7-TAX | **DONE** | Numerário real → bases + tax lines + expenses + FundingRequest CONFIRMADO + Payable **CUSTOMS_FUNDING OPEN**. Sem Payment |
| E7-4 | **DONE** | DUIMP de ensaio `TEST-DUIMP-E7-202` (rótulo L-007); submit; nacionalização parcial qty 50; over-nationalization **409**; residual permanece |
| Walk | **DONE** | **Uma história 202** (não é soma 328+202) |
| E7-CF | **DONE** | Este arquivo; proposta de barras abaixo — **não aplicada** |

---

## 2. Capacidades novas operacionais

- Chegada **ARRIVED** na jornada Logistics (UI).
- Commit **Fattura Doganale** preenche o processo existente (linhas, NCM, vínculo fatura/embarque, alocação de itens de embarque).
- Commit **Print Declaration** só anexa documento.
- Commit **Numerário** registra tributos/despesas/bases no FundingRequest; confirmar nasce Payable CUSTOMS_FUNDING **OPEN** (não paga).
- DUIMP digitado como referência de ensaio (nunca alegado como extraído de PDF).
- Nacionalização quantitativa na UI (SKU/nome; residual; parcial; bloqueio de excesso).
- Fronteira Elo 7 / Elo 8 visível: recebimento em estoque permanece, mas não foi usado.

---

## 3. Documentos reais que sustentaram fatos

| Fato | PDF real |
|---|---|
| Fatura comercial 202 (7 SKUs, EUR 30.188) | `corpus_202/Fattura_202.pdf` |
| Packing / volumes | `corpus_202/PackingList_202.pdf` |
| Declaração / NCM / linhas Doganale | `corpus_202/FatturaDoganale_202.pdf` |
| Print | `corpus_202/PrintDeclaration_202.pdf` |
| Tributos II/IPI/PIS/COFINS/AFRMM/ICMS/SISCOMEX + despesas + total R$ 1.425.554,64 | `corpus_202/Solicitacao_Numerario.pdf` |

**Honestidade tributária:** o Numerário cita faturas **181/202/203/244/245/246**. Os valores são do PDF (nível DUIMP), **não** da Fattura comercial 202 isolada. A Doganale 202 **não** contém tributos BR — não foram derivados dela.

A 328 **não** foi usada neste walk. Existe no corpus (Doganale+Print, sem Numerário); aceite de família Doganale poderia usar 328 noutro ensaio, mas a história única escolhida é 202.

---

## 4. O que foi mock / seed (não é evidência documental)

- Order `E7-202-MOCK` (id 1), Products/SKUs, Supplier Heroe's, prestador Mock Carrier — seed (`logs/e7_walk_seed.py`).
- DUIMP `TEST-DUIMP-E7-202` — digitado (L-007).
- Adapter/upload dos PDFs nesta automação foi via API (`e7_walk_upload.py`); **commits Elo 7 e nacionalização foram clicados na UI**.
- Não há Ordine 202 no corpus.

---

## 5. História única atravessou o Elo 7?

**Sim.** Família 202, mesmo pedido/fatura/embarque/processo:

Pedido (mock) → Fattura 202 ISSUED → packing → Shipment ARRIVED → Doganale preenche processo #2 → Print anexo → Numerário registra e confirma funding → Payable CUSTOMS_FUNDING OPEN → DUIMP ensaio → submit → nacionalização parcial.

**Não** chamar isto de “compra 1→7 comercialmente quitada”: os payables da Fattura 202 (EUR 15.094+15.094) permaneceram **OPEN**. Elo 4 desta compra **não** foi exercitado. A cadeia 1→6 já estava aceita noutro pedido (328); aqui o elo 7 foi exercitado na 202.

Processo órfão do 500 inicial **não** restou no banco (só processo #2).

---

## 6–8. Proposta de estado (NÃO aplicada no Roadmap)

Critério usado: elos 1–6 já PRONTOS noutros walks; elo 7 **nesta** campanha com história única 202.

| Item | Atual (Roadmap 0.5.118) | **Proposta ao advisor** | Motivo |
|---|---|---|---|
| Elo 7 | FRÁGIL | **PRONTO, com limitações** (ver juízo) | Mesma história: chegada, declaração PDF, impostos PDF, nacionalização |
| Cadeia | **6/10** | **7/10** | Elo 7 proposto PRONTO; 8 permanece FRÁGIL; 9–10 FALTA |
| Ingestão | 3/7 | **5/7** | Aceite de família **Doganale** e **Numerário** com PDFs reais (202). Fattura comercial nesta barra continua de fora (A0 fechou elo 3, não este n). Planilha falta |
| Aduana/estoque | 1/3 | **2/3** | “PDF preenche” exercitado. “Numerário se paga” = settlement Treasury — **fora desta campanha**; **não** propor 3/3 |
| Denominadores | — | **inalterados** | Nenhum d muda |

**Não misturar:** ingestão pode aceitar famílias com PDFs de compras distintas; a **cadeia** exigiu (e teve) a mesma história.

---

## 9. Clarificação proposta do contrato da cadeia (não aplicar sozinho)

Redação mínima sugerida na Parte B / Contrato:

> Para a barra da cadeia, um elo composto por múltiplos fatos só é PRONTO quando esses fatos forem exercitados como uma mesma história comercial/operacional, salvo exceção explicitamente aceita.

---

## 10. Dívida E7-ARRIVAL-GATE

Registrada em Roadmap B.6 (não implementada, não descrita como bug resolvido):

O domínio Customs permite nacionalização sem exigir evidência de Shipment ARRIVED. A campanha demonstra ARRIVED na jornada; **não** cria a trava. Avaliar se chegada física/documental deve ser precondição de nacionalização.

---

## 11. Testes

| Suite | Resultado | Nota |
|---|---|---|
| `v2/tests/test_elo7.py` + pytest V2 | **564 passed** **antes** do walk | `conftest` drop_all apagaria o walk; **não reexecutado** após a massa 202 |
| Vitest painéis Doganale / Numerário / Nationalization | **5 passed** após o walk | Sem drop de schema |

---

## 12. UI walks (protocolo Runtime / Database / Abri / Vi / Cliquei / Resultado)

Lane teste. Screenshots: `docs/v2/etapa-elo-7/screenshots/e7-01` … `e7-14`.

| Passo | Resultado |
|---|---|
| Pedido confirmado | e7-01 |
| Fattura commit + emitida | e7-02, e7-03 |
| Packing + chegada ARRIVED | e7-04, e7-05 |
| Doganale preenche processo #2 | e7-06 |
| Print anexado | e7-07 |
| Numerário registrado (FundingRequest #1 DRAFT) | e7-08 |
| Confirmar funding → AP #3 OPEN BRL 1.425.554,64 | e7-09, e7-13 |
| DUIMP ensaio + Submetido | e7-10 |
| Nacionalização parcial qty 50 (SKU na tabela, sem ID cru) | e7-11 |
| Over-qty 999 → **409 over_nationalization** | e7-12 |
| Recarregar `/customs/2` → PARTIALLY_CLEARED, DUIMP, funding, liberação #1 | e7-14 |

DB: `logs/e7-walk-db.json`. Sem GoodsReceipt.

---

## 13. Regressões / gaps observados (não bloqueiam o CF)

- Alocação **invoice item** ficou 0; nacionalização usou **shipment items** (Doganale alocou embarque).
- Totais Numerário: declarado R$ 1.425.554,64 vs estruturado R$ 4.878.074,08 — bases FOB/CIF entram no estruturado junto com tributos; **não** foi “corrigido” fabricando valores.
- UI de auditoria do processo mostra poucos eventos (`update`, `submit`); ações de funding/nacionalização podem não aparecer nessa tabela.
- Upload de PDF pelo file picker da UI não foi automável neste browser; operador consegue pela UI.
- Primeiro commit Doganale 500 (`uq_ingestion_commit_operations_attempt_key`) — corrigido (op_key por item + expire shipments). Sem migration.

---

## 14. Blueprint delta (aplicado em 0.2.23)

Doganale do PDF preenche Customs; tributos BR só do Numerário; L-007 = referência digitada; REGISTRAR ≠ PAGAR; Elo 7 termina na liberação confirmada (estoque = Elo 8).

---

## 15. DOC_DELTA proposto

Ver mensagem de fechamento. Roadmap **0.5.119**: campanha Elo 7 **DONE**; **barras 6/10 inalteradas** até aceite destas propostas.

---

## 16. Próxima etapa lógica — **não iniciar**

Revisão do advisor deste pacote (barras / Elo 7 / clarificação “mesma história”). **Não** iniciar Elo 8 / Inventory / settlement CUSTOMS_FUNDING / J#6.

Fora: Dashboard, B0, PaymentOrder, ACCONTO, 3A/020, adapter DUIMP, redesign, reabrir C4–C6.

---

## Juízo operacional

**SIM, COM LIMITAÇÕES.**

Depois desta campanha, um operador **consegue pela UI** levar uma importação de ensaio **desde a chegada até a nacionalização parcial**, com PDFs reais de Doganale, Print e Numerário, no mesmo processo.

Ainda exige:

| Tipo | O quê |
|---|---|
| Seed / catálogo | Pedido e SKUs se não houver Ordine; nesta história o pedido foi mock |
| Digitação | Referência DUIMP de ensaio (não há PDF de DUIMP/DI no corpus) |
| Documento ausente | DUIMP/DI real; Numerário *desta* fatura isolada (o PDF 202 é multi-fatura) |
| Fora do Elo 7 | Pagar o Numerário; receber em estoque; quitar a Fattura nesta mesma compra |

**Primeiro bloqueio operacional real** numa compra nova, com catálogo já batendo com o packing: **não existe PDF de DUIMP** — o operador tem de digitar uma referência de teste (ou o processo não identifica a declaração oficial). O segundo bloqueio de caixa é **pagar o Numerário** (Treasury, fora desta campanha).

Não maquiar: capacidades implementadas ≠ barras promovidas neste CF.

---

## Recomendação

1. Aceitar Elo 7 **PRONTO com limitações** e Cadeia **7/10**.  
2. Aceitar Ingestão **5/7** e Aduana **2/3**.  
3. Aceitar a clarificação “mesma história”.  
4. Manter L-007 fechada (digitação explícita).  
5. Backlog: E7-ARRIVAL-GATE; settlement CUSTOMS_FUNDING; Elo 8.  
6. **Não** iniciar a próxima etapa nesta volta.

**Arquivos âncora:** `docs/v2/etapa-elo-7/` (este handoff, `P0_RUNTIME.md`, `screenshots/`, `logs/`).

---

# E7-UI-ACCEPT — aceite operacional na UI servida

**Gate:** PASS. **Data:** 2026-08-14. Mesmo arquivo; sem segundo handoff.  
**Massa:** nova `epic_v2_test` após pytest 564 (antes do walk). Nunca `epic_v2`. Pedidos 31/34 intocados.  
**Código do walk = código final** (UX Numerário/auditoria/excesso foi **antes** do pytest+massa; nada alterado depois do último clique).

## 1. Ações feitas na UI (operador)

Login → Pedido **202** + 7 SKUs + fornecedor Heroe's (criar na tela) → confirmar → Fattura_202 no input → classificar → extrair → confirmar pedido → commit → Emitir fatura (com PDF) → PackingList_202 → SKUs ambíguos na tela → commit embarque #1 → modal Marítimo + prestador criado na tela → BOOKED → IN_TRANSIT → ARRIVED (reload persiste) → FatturaDoganale_202 → confirmar fatura **e** embarque (sem vínculo silencioso) → criar processo e preencher declaração → PrintDeclaration_202 → confirmar processo → anexar → Solicitacao_Numerario → aviso multi-fatura 181/202/203/244/245/246 → confirmar processo → registrar tributos → confirmar obrigação no processo → **não pagar** → DUIMP digitado `TEST-DUIMP-E7-202` (rótulo ensaio) → Submeter → nacionalização parcial qty 50 no SKU 3814 (resto residual completo) → excesso 151>150 bloqueado na tela.

## 2. O que restou em API/script (com justificativa)

| Uso | Justificativa |
|---|---|
| Pytest completo **antes** da massa | `conftest` drop_all; obrigatório antes do walk |
| `e2e_prepare.py` + restart `:8082` | Só schema/seed admin em `epic_v2_test` |
| GET `/api/audit?...` | Diagnóstico da trilha (a tabela da UI já estava visível) |
| SQL read-only `e7_ui_accept_db.py` | Snapshot JSON; **não** muta |
| Cópias em `v2/frontend/public/e7-ui-accept/` | Limitação do file-picker MCP — **não** é API de produto |

**Não** houve POST de commit/upload/adapter/advance/nationalization fora da UI servida.

## 3. Como o PDF entrou no input

O file-picker nativo do browser MCP não injeta ficheiro. Em cada envio: **Começar novo envio** → `fetch('/e7-ui-accept/NOME.pdf')` → `DataTransfer` → `input[data-testid=intake-file-input]` → `change`. O operador real usa o mesmo input (arrastar/clicar). Classificar, extrair, confirmar e commit foram cliques na UI.

## 4. Abri / Vi / Cliquei / Resultado (resumo)

| Passo | Abri | Vi | Cliquei | Resultado |
|---|---|---|---|---|
| A Pedido | `/orders/new` | formulário | SKUs + Salvar e confirmar | Pedido **#1 CONFIRMED** EUR 30.188 |
| Prestador | `/logistics-providers` | fila | criar Transportadora Ensaio 202 | prestador #1 |
| B Fattura | `/ingestion` | IR #1 | confirmar pedido + Commit | Invoice **#1**; depois Emitir = **Emitida** |
| C Packing | `/ingestion` | 100 CARTON; grupos ambíguos | rádios SKU + Commit | Shipment **#1** PLANNED |
| D Chegada | `/shipments/1` | notice BOOKED precisa modal | SEA + prestador + Reservar / saída / chegada | **Chegou** após reload |
| E Doganale | `/ingestion/3` | 7 linhas NCM; sem processo prévio | confirmar fatura #1 + embarque ARRIVED + criar processo | Processo **#1**; Doganale v1 ACTIVE |
| F Print | `/ingestion/4` | invoice_ref 202 | confirmar processo + Anexar | Print no processo; visível após reload |
| G Numerário | `/ingestion/5` | aviso multi-fatura; II/IPI/PIS/COFINS/AFRMM/ICMS/SISCOMEX + despesas | confirmar processo + Registrar + Confirmar obrigação | FundingRequest #1 CONFIRMADO; AP **#3** CUSTOMS_FUNDING OPEN BRL 1.425.554,64; **zero Payment** |
| H DUIMP | `/customs/1` | “não veio de PDF” | `TEST-DUIMP-E7-202` + Salvar + Submeter | **Submetido** v12 |
| I Nacionalização | mesmo processo | tabela SKU / embarcada / já / residual / proposta | proposta 50 no 3814 + Criar + Adicionar + Confirmar | **Parcialmente liberado** v13; residual 150 no 3814 |
| J Excesso | mesma tabela | residual 150 | proposta **151** + Criar + Adicionar | “Não é possível nacionalizar mais do que o residual…” — **sem** “409 · code” |

## 5. Screenshots (`docs/v2/etapa-elo-7/screenshots/`)

`e7-ui-01` pedido · `02` Fattura · `03` fatura emitida · `04` packing (reload, já gravado) · `05` embarque Chegou · `06` Doganale processada · `07` processo após Doganale · `08` Print anexado · `09` Numerário sucesso · `10` totais tributos+despesas · `11` APs abertas · `12` pagamentos vazios · `13` DUIMP + Submetido · `14` residual 150 · `15` bloqueio de excesso · `16` auditoria.

## 6. Reload

Embarque Chegou, processo Doganale v1, Print no dossiê, Numerário confirmado, DUIMP, PARTIALLY_CLEARED e residual 150 persistiram após F5. IR #2/#3/#5 mostram “já processado / não duplica”.

## 7. Idempotência

Primeiros commits **na UI**. Reload: banners “não cria outro processo / não duplica payable”. `ingestion_commit_attempts`: 5 linhas, todas **SUCCEEDED**, uma por documento (Fattura, packing, Doganale, Print, Numerário). Botão de commit some após sucesso — retry de botão escondido **não** foi POST extra (prova técnica = GET/SQL das attempts).

## 8. Auditoria

Tabela do processo (`e7-ui-16`): coluna **Onde** (Processo / Numerário / Liberação) + aviso de que commits de ingestão (Doganale/Print/Numerário PDF) ficam no documento em Ingestão. Eventos: processo atualizado/submetido; Numerário confirmado (obrigação); liberação criada/itens/confirmada. `doganale.version.create` **não** aparece no processo (coerente com o aviso de âmbito). Quem = `1` (id do actor — opaco, não e-mail).

## 9. Excesso

Digitado **151** com residual **150** na UI. Hint “Acima do residual — o sistema bloqueia.” + Notice operacional (não 409 cru). Liberação rascunho #2 ficou vazia (artefacto do ensaio).

## 10. Totais Numerário (conclusão)

UI **não** apresenta `structured_total` (~R$ 4.878.074,08 = bases+tributos+despesas) como total comparável. Mostra: declarado **BRL 1.425.554,64**; tributos **1.361.123,64** + despesas **64.431,00** = obrigação **1.425.554,64**; diferença **0,00**. Aviso: bases FOB/CIF não são o total a pagar. Matemática de domínio `structured_total()` **inalterada**. Valores = PDF; não inventados. Multi-fatura avisada (nível DUIMP).

## 11. Testes

| Suite | Resultado | Nota |
|---|---|---|
| Pytest V2 completo | **564 passed** | **Antes** da massa do walk |
| Vitest (display, permissions, painéis) | **13 passed** | Depois do walk; sem drop |
| `check:api-drift` | OpenAPI client up to date | Depois do walk |
| `tests/architecture/test_import_boundaries.py` | **6 passed** | Depois do walk |
| Pytest completo após walk | **não** | drop_all apagaria a massa |

## 12. Código depois do último clique

**Nenhum.** UX (totais, aviso multi-fatura, auditoria, copy de excesso) foi anterior ao pytest+bootstrap+walk.

## 13. Barras (aplicadas — advisor já tinha ratificado o critério)

| Item | Antes (0.5.119) | Agora (0.5.120) |
|---|---|---|
| Elo 7 | FRÁGIL | **PRONTO** + costura **LIGADO** |
| Cadeia | 6/10 = 60% | **7/10 = 70%** |
| Ingestão | 3/7 = 43% | **5/7 = 71%** (Doganale + Numerário) |
| Aduana/estoque | 1/3 = 33% | **2/3 = 67%** (PDF preenche; **não** se paga) |
| Denominadores | — | **inalterados** |

Clarificação ratificada no Contrato A↔B e em B.2: elo composto só é PRONTO na cadeia quando os fatos são **uma** história.

## 14. Roadmap

**0.5.120** — B primeiro, A derivada. Zero jargão/IDs de ensaio na Parte A. Blueprint **não** bumpado.

## 15. Blueprint

**Inalterado (0.2.23).** Nenhuma invariante durável nova: totais na UI são apresentação; regras de produto Elo 7 já estavam no 0.2.23.

## 16. DOC_DELTA

Ver mensagem de fechamento desta volta.

## 17. Pendências / limitações (não bloqueiam PASS)

- Pedido 202 foi **manual** (não há Ordine 202 no corpus); nomes de SKU = o próprio código (criar SKU não tem campo descrição).
- Alocação de **item de fatura** ficou 0; nacionalização usou **itens de embarque**.
- Rascunho de liberação #2 vazio (tentativa de excesso).
- E7-ARRIVAL-GATE: nacionalizar sem ARRIVED ainda é possível no domínio; a jornada **demonstrou** Chegou; **não** implementámos a trava.
- Payables comerciais EUR 15.094+15.094 **OPEN** (Elo 4 desta compra não exercitado). CUSTOMS_FUNDING **não pago**. Sem GoodsReceipt / StockBalance.
- File-picker MCP: cópias estáticas só para injecção; o input do produto é o mesmo.

## 18. Próxima etapa

**Não iniciar** Elo 8 / Inventory / settlement CUSTOMS_FUNDING / J#6. Fora: Dashboard, B0, ACCONTO, 3A/020, adapter DUIMP, redesign, reabrir C4–C6.

**Recomendação:** aceite UI **PASS**; barras já no Roadmap 0.5.120. Parar.
