# Elo 8 — retorno ao advisor (DONE)

**Etapa:** Elo 8 — nacionalizado → estoque por produto (E8-0…E8-6)  
**Status:** **DONE / ENCERRADO**. Advisor **ACEITO** (2026-08-17). E8-FINAL-VERIFY **PASS**. Barras 8/10 inalteradas. Roadmap **0.5.123** aceito. Blueprint **0.2.24** aceito.  
**Campanha Elo 8:** **ENCERRADA** — não relançar E8-0…E8-6; não hardening.  
**Campanha Elo 7:** **ENCERRADA** (não reaberta).  
**Plano mestre (único, coerente com Q1–Q7):** [`E8_EXECUTION_PLAN.md`](E8_EXECUTION_PLAN.md) — campanha **fechada**.  
**Runtime do walk:** Vite `dev:test` `http://localhost:5174` → API `:8082` / `epic_v2_test` / cookie `epic_v2_test_session` / Alembic **025**. Login `admin@epic.com.br`. `epic_v2` / 589 / TESTE-CICLO-001 intocados. Sem migration.

Residual recebível do processo é provado pela query item-level; SkuPosition é verificação agregada física (todos os processos), não o residual deste processo.

---

## E8-FINAL-VERIFY (2026-08-17)

**STATUS:** **PASS**. Código de produto **não** mudou depois da suite V1 + bootstrap + walks. Barras **não** sobem. Settlement CUSTOMS_FUNDING / J#5-REC / J#6 **não** iniciados.

### V0 — código depois do walk W1–W8 original?

Arquivos de produto Elo 8 (Inventory + ReceiptPanel / NationalizationPanel / SkuPosition) **mais antigos** que o walk `e8-walk-log.json` (15:41). Docs (Roadmap 0.5.122, este handoff) mudaram depois. A verificação final **correu mesmo assim**.

HEAD `main` @ `3b10deb`. Alembic **025**. `:8082` / `epic_v2_test` / `schema_ok`. `:8081` / `epic_v2` só inspeção.

### V1 — suite no código atual (antes da massa)

| Gate | Comando | Resultado | Quando |
|---|---|---|---|
| Pytest V2 completo | `v2\.venv\Scripts\python.exe -m pytest -q --tb=line` | **566 passed**, 1 warning, 316.87s, exit 0 | 16:15 |
| Inventory + arch | `pytest tests/test_inventory_i5_4.py tests/architecture/test_import_boundaries.py -v` | **18 passed**, 36.35s; multi-processo `cleared_not_received` = 16 **PASSED** | 16:16 |
| Vitest | `npx vitest run` ReceiptPanel / NationalizationPanel / inventoryLabels / customsPermissions | **4 files / 18 tests passed**, 2.45s | 16:16 |
| Drift | `npm run check:api-drift` | OpenAPI client up to date | V1 |
| Frontend build | `tsc --noEmit && vite build` (primeiro `e2e:j5`) | PASS | ~16:22 |
| E2E `e2e:j5` | `npm run e2e:j5` | 1ª: 3 passed / 1 failed (timeout no painel de nacionalização ainda em `/payables`) | 16:22 |
| E2E reteste | `$env:E2E_SKIP_BUILD="1"; npm run e2e:j5` | **4 passed (24.7s)** após correção **só do spec** | 16:23 |

**E2E obrigatório:** `e2e:j5` (4 specs: `i5-1-customs`, `i5-2-doganale`, `i5-5-ux-smoke`, `j5-acceptance`). Inventory/Nationalization no `j5-acceptance`: tabela residual; `receipt-type` = DOMESTIC_IN; sem `receipt-product-id`; clique `receipt-receive`; SkuPosition disponível; movimentos **Entrada doméstica** / DOMESTIC-MAIN. Prereqs de pedido/fatura/embarque ainda usam `page.evaluate(fetch)` — **não** para descobrir IDs de Inventory. Correção do spec: `goto /customs/${processId}` depois do AP; asserção de movimento alinhada ao PATH Elo 8. **Não** é spec dedicado novo: o J#5 atual ficou verde contra a UI atual.

Logs: [`logs/e8-final-pytest.txt`](logs/e8-final-pytest.txt) · [`logs/e8-final-inventory-arch.txt`](logs/e8-final-inventory-arch.txt) · [`logs/e8-final-vitest.txt`](logs/e8-final-vitest.txt) · [`logs/e8-final-e2e-j5.txt`](logs/e8-final-e2e-j5.txt) · [`logs/e8-final-e2e-j5-retest.txt`](logs/e8-final-e2e-j5-retest.txt).

### V2 / V3 — massa + W1–W8 no código final

Pytest/e2e fazem `drop_all`. Depois da suite: rebuild `epic_v2_test` Alembic 025 + seed admin/DOMESTIC-MAIN; 8082; fixture pré-W1 **sem** POST de receipt; walk [`logs/e8_final_w18.mjs`](logs/e8_final_w18.mjs).

Processo do W18: `IMP-C63AD235DDA3`. **WALK PASS.** 13 POSTs Inventory (create/lines/confirm/reverse) **só** após W1, todos originados pela UI. Double-click no mesmo tick. V5: Reverter nacionalização **oculto** (`Reverter indisponível — já há estoque recebido`); API `E8-NAT-REVERSE-API` **não** fechada.

Screenshots: [`screenshots/final-w18/`](screenshots/final-w18/). Log: [`logs/e8-final-w18-log.json`](logs/e8-final-w18-log.json).

### V4 — 202 documental → estoque (mesma UI)

Invoice `202` do mock colide com `UniqueConstraint(supplier, number)`. Depois do W18: **segundo** rebuild (código de produto intocado) para a história documental.

Percurso UI (`intake-file-input.setInputFiles`, não POST de upload/adapter/commit por script): pedido **202** + 7 SKUs + Heroe's na tela → `Fattura_202.pdf` → emitir → `PackingList_202.pdf` (rádios SKU) → embarque ARRIVED → `FatturaDoganale_202.pdf` → `PrintDeclaration_202.pdf` → `Solicitacao_Numerario.pdf` → confirmar obrigação **sem pagar** → DUIMP ensaio `TEST-DUIMP-E8-DOC-202` → nacionalização parcial qty 50 no 3814 → Recebimentos: residual 50; DOMESTIC_IN; 20 + over-block + 30; Disponível 20 depois 50; movimentos Entrada doméstica; Reverter nacionalização oculto.

Processo final: `IMP-85C5825D8EB3` `PARTIALLY_CLEARED`. Receipts #1 e #2 CONFIRMED DOMESTIC_IN. Residual 3814 = 0.

O runner foi retomado por segmentos (packing radios / locator Doganale / Confirmada vs Confirmado) — **falhas do script de evidência, não do produto.** Toda a história ficou no mesmo `epic_v2_test` após o rebuild documental.

Screenshots: [`screenshots/final-doc202/`](screenshots/final-doc202/) (`01`…`20`). Log do fecho (receipts): [`logs/e8-final-doc202-log.json`](logs/e8-final-doc202-log.json). 6 POSTs Inventory no fecho = 2 receipts × create/lines/confirm pela UI.

**Não feito (fora do objetivo):** pagar Payables comerciais; pagar CUSTOMS_FUNDING; Caso A BONDED; reverter nacionalização.

### Código testado = código final

**SIM** para produto. Inventory / ReceiptPanel / NationalizationPanel / SkuPosition **anteriores** à suite 16:15. Única alteração na V1: `e2e/j5-acceptance.spec.ts` (16:23), **antes** do bootstrap V2/W18/V4. Depois da massa: só docs + runners em `docs/v2/etapa-elo-8/logs/`.

### Veredito

| | |
|---|---|
| A. Conformidade com o plano Elo 8 | **PASS** |
| B. Teste técnico completo | **PASS** |
| C. W1–W8 integralmente pela UI | **PASS** |
| D. E2E automatizado final | **PASS** (`e2e:j5` 4/4) |
| E. História documental 202 → estoque | **PASS** |
| F. Código testado = código final | **SIM** |
| G. Elo 8 permanece PRONTO / 8/10 | **SIM** |

### Aceite do advisor

**ACEITO.** Elo 8 **ENCERRADO**: DONE / PRONTO / LIGADO; cadeia **8/10 = 80%**; Roadmap **0.5.123**; Blueprint **0.2.24**; 202 documental → estoque; `e2e:j5` 4/4; W1–W8 final. Sem novo hardening. Sem relançar E8-0…E8-6. Sem alterar barras.

Backlog **preservado, sem correção nesta campanha:**

- `E8-NAT-REVERSE-API` (B.3)
- **J#5-REC** — compromisso sem Product
- Caso A `BONDED_IN` + `RECLASS` na UI (B.6)
- `E7-ARRIVAL-GATE` (B.6)
- Atritos menores já em B.6 (qty proposta; coluna Quem)

---

## Execução (E8-0…E8-6)

| Campo | Valor |
|---|---|
| Estado anterior | Elo 8 **FRÁGIL** no Roadmap 0.5.120; cadeia 7/10; domínio Inventory existia (I5-4); operador digitava IDs; `receipts: []` após Elo 7 |
| Estado atual | Elo 8 **PRONTO / LIGADO** para itens cujo produto já está no catálogo; cadeia **8/10 = 80%**; Aduana/estoque **2/3** (inalterada). Verificação final: 202 documental → estoque (Roadmap **0.5.123**) |
| Hipótese central | Domínio já existia; gap = costura UI residual → `DOMESTIC_IN` → saldo — **confirmada** |
| Migration | **Não** (head 025) |
| NAT-REVERSE | **B** (UI oculta). API nomeada **`E8-NAT-REVERSE-API`** em B.3 — não anónima |

### Gates

| Fatia | Status | Prova |
|---|---|---|
| E8-0 | **DONE** | `:8082` / `epic_v2_test` / Alembic 025; `epic_v2` só inspeção ([`P0_RUNTIME.md`](P0_RUNTIME.md)) |
| E8-1 | **DONE** | `GET …/receipt-residuals`; confirm doméstico exige `nationalization_item_id`; multi-processo: residuais 6 e 10, `cleared_not_received` = 16; sem ciclo `customs` → `inventory` |
| E8-2 | **DONE** | ReceiptPanel só `DOMESTIC_IN`; sem `receipt-product-id`; hide Reverter; busy/double-click; fixture `EAN_DESC` |
| E8-3 | **DONE** | Copy `over_receipt`; `balances`; `goods_receipt` na auditoria do processo; rótulo de escopo em Liberado não recebido |
| E8-4 | **DONE** | Pytest **full** verde **antes** da massa 202; vitest Elo 8; `check:api-drift` OK |
| E8-5 | **DONE / PASS** | W1–W8 só UI após W1 ([`logs/e8-walk-log.json`](logs/e8-walk-log.json)) |
| E8-6 | **DONE** | Este bloco; B.2 com condição catálogo + J#5-REC; Blueprint PATH/BIND/COVERAGE/STUBS |

### Walk W1–W8 (texto literal)

**Cabeçalho:** Vite `dev:test` **`:5174`** (`localhost`, não `127.0.0.1`) → `:8082` / `epic_v2_test` / Alembic **025**. Playwright contra essa UI. Fixture pré-W1: processo `IMP-C053F7E3E212` `PARTIALLY_CLEARED`; nat CONFIRMED; **zero** receipts; pedido mock `E8-202-MOCK`. **Não** é a 202 do corpus com PDFs reais (DEC-E8-DOC). A massa Elo 7 em `epic_v2_test` cai no `drop_all` do pytest E8-4 (planeado, antes do walk); o loop Q2 apagou de novo. Reconstruir os 5 PDFs seria relançar o Elo 7 — a fixture POST foi o caminho autorizado.

| Passo | Resultado literal | Canal | Atrito |
|---|---|---|---|
| W1 | Tabela: `WASH BAG STARLIGHT - RED` + `8057628953814` 50/0/50; `WASH BAG FIERCE` + `8057628953104` 10/0/10; tipo só `DOMESTIC_IN`; `receipt-product-id` ausente | UI | — |
| W2 | `#1 · Entrada doméstica · Confirmado · DOMESTIC-MAIN`; residual 3814 = 30 (50/20/30); double-click no mesmo tick ≠ segundo receipt | **UI** | Extra clique: zerar qty proposta do FIERCE para receber só 20 do STARLIGHT |
| W3 | Movimento Δ 20 · `Entrada doméstica` · `DOMESTIC-MAIN`. `Disponível 20`. `Liberado não recebido 30` + «Agregado do produto em todos os processos — não é o residual deste processo.» Saldo `DOMESTIC-MAIN` / Doméstico / 20. Persiste após reload | UI | — |
| W4 | Segundo receipt 30; `Disponível 50`; STARLIGHT sai da tabela (residual 0) | **UI** | Qty proposta não volta sozinha ao residual novo (ficou 20 com residual 30); walk preencheu 30 |
| W5 | Hint «Acima do residual — o sistema bloqueia.» Copy «Não é possível receber mais do que o residual nacionalizado disponível. Reduza a quantidade.» Sem rascunho extra | **UI** | Excesso no FIERCE (99): STARLIGHT já tinha saído da tabela |
| W6 | FIERCE qty 10 → `#3 · Entrada doméstica · Confirmado`; texto «Nada a receber» | **UI** | — |
| W7 | Reverter liberação **oculto** («Reverter indisponível — já há estoque recebido»). Estorno do receipt mais novo → `Estornado`; re-receber `#4 · Confirmado`; ledger sem duplicar | **UI** | — |
| W8 | Auditoria na UI: Recebimento criado / linhas / confirmado / estornado (escopo Recebimento) | **UI** | Coluna Quem mostra `"1"` (não um nome) |

Screenshots: [`screenshots/`](screenshots/) (`e8-w1-residual.png` … `e8-w8-audit.png`).

**Não no walk:** pagar numerário; Caso A; reverter nacionalização; POST inventory fora da UI.

### APIs

**Pré-W1 (fixture):** `GET /api/health`; `POST /api/auth/login`; `POST /api/suppliers`; `POST /api/products`; `POST /api/orders` + items + confirm; `POST /api/invoices` + items + terms + documents + issue; `POST /api/logistics-providers`; `POST /api/shipments` + items + advance; `POST /api/import-processes` + invoices/shipments + allocate + submit; `POST …/nationalizations` + items + confirm; `GET …/receipt-residuals`; `GET /api/inventory/receipts` (vazio).

**Pós-W1:** só GET disparado pela página (processo, residuals, receipts, locations, movements, sku position, products, audit). Inventory **POST** (create / lines / confirm / reverse) **somente** pelos cliques da UI. Nenhum script POST inventory após W1.

### Decisões ratificadas (produto)

PATH / BIND / COVERAGE / STUBS no Blueprint **0.2.24** §5.12 / §7.11. NAT-REVERSE **B** (hide UI) no handoff; furo API = **`E8-NAT-REVERSE-API`**. Caso A (entreposto na UI) = backlog datado B.6.

### Pendências / próxima etapa

- **Próxima ação (Roadmap B.1):** pagar numerário no tesouro (settlement CUSTOMS_FUNDING).
- **Não iniciar:** J#5-REC (compromisso sem Product), J#6, Dashboard, B0, 3A/020, fechar o furo `E8-NAT-REVERSE-API` com ciclo `customs` → `inventory`.
- Caso A / entreposto UI: backlog 2026-08-17.

### Recomendação

Aceitar Elo 8 **DONE** com a ressalva de catálogo escrita em B.2. Não apagar J#5-REC. Não subir Aduana/estoque além de 2/3.

O planeamento Q1–Q7 abaixo é **histórico da autorização**. O mestre coerente (autorizado → feito, sem futuro misturado) está em [`E8_EXECUTION_PLAN.md`](E8_EXECUTION_PLAN.md). Não reler este bloco como lista de tarefas.

---

## Histórico de planeamento (autorização Q1–Q7)

---

## Respostas desta revisão (autorização)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | DEC-E8-NAT-REVERSE | **A refutado. C refutado.** Reverse UI+API sem guard. `customs/routes` **não** pode importar `inventory.public`: o arch test aplica `ALLOWED_DEPS` a **todo** o pacote, inclusive `nationalization_routes.py`. Precedente de rota→public existe **só** nas arestas permitidas (ex. treasury→billing). `customs` + `inventory` no grafo = **ciclo**. **Decisão: B** (ocultar Reverter via GET residual / receipts, na UI). Furo da API → item **nomeado** `E8-NAT-REVERSE-API` no Roadmap B.3/B.4 **no E8-6**. Não promover com furo anónimo. Walk não reverte nat após estoque. |
| 2 | Fonte única do residual recebível | Query E8-1 **item-level**: `NationalizationItem CONFIRMED` → `nationalized_qty` → `received_qty` do **mesmo** `nationalization_item_id` → `residual_qty`. ReceiptPanel **só** isso. SkuPosition **não** decide qty. |
| 3 | Teste multi-processo | Mesmo Product em Process A/Item A e Process B/Item B. Receber A reduz só residual A; B intacto. `product_id` de B + `nationalization_item_id` de A → rejeição. Fecha o fallback global no caminho operador. |
| 4 | Receipt types na UI Elo 8 | **Só `DOMESTIC_IN`**, congelado até o Ricardo decidir entreposto. Se a resposta for “usamos entreposto”, Caso A vira item **datado no backlog** — **não** entra no select desta campanha. |
| 5 | W1–W8 obrigatoriamente UI | A partir de W1: criar receipt, qty, tipo/location, confirm, segundo receipt, over-receipt, reverse receipt, re-receber. W8 = tabela de auditoria **na UI** (incluir `goods_receipt`; hoje falta). Fixture só **pré-W1**. |
| 6 | Double-click / idempotência | Busy/disabled no confirm; um draft; double-click ≠ dois movements; reload não devolve qty consumida; segundo receipt = residual restante. `receipt_immutable` continua no domínio. |
| 7 | DECs no Blueprint se PASS | **PATH, BIND, COVERAGE, STUBS** como invariantes (sem IDs 202, screenshots, pytest, logs, runtime). |
| 8 | Executar sem novo aceite? | **Sim** — E8-0…E8-6. Parar só: migration inesperada; NAT-REVERSE a exigir ciclo/arquitectura transversal; CUSTOMS_FUNDING; reabrir E7. |

---

## Respostas objetivas (P0 — inalteradas na substância)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Quanto do Elo 8 já existe? | **Domínio ~I5-4 completo.** `GoodsReceipt` → `InventoryMovement` → `StockBalance` derivado já passam pytest e passaram no aceite J#5 (IDs digitados). **Jornada de operador após Elo 7: quase nula.** A cadeia 202 parou na nacionalização confirmada (`receipts: []`). |
| 2 | Primeiro gap real | **Costura UI:** o operador ainda digita `product_id`, `nationalization_id` e `nationalization_item_id`. Não há tabela de residual **recebível**. Sem isso o Elo 8 permanece FRÁGIL (o dado atravessa na API; o operador refaz identidade). |
| 3 | GoodsReceipt já funciona? | **Sim, no domínio/API.** Confirm posta movimentos e saldo. **Não** é operável por um operador sem IDs internos. |
| 4 | StockBalance já funciona? | **Sim.** Cache persistido `(location, product)`, atualizado no post, rebuildível a partir do ledger. Não é view SQL; não deve ser editado à mão (ADR-07). |
| 5 | SkuPosition já é confiável? | **Parcial.** Fatos reais: `available`, `bonded`, `quarantine`, `cleared_not_received`. Stubs: `in_clearance` e `in_transit` (API devolve `"0"`; UI mostra “Não disponível”). `future_order` = `null`. Não usar stubs como prova do Elo 8. |
| 6 | Precisa de migration? | **Não**, se as DECs abaixo forem ratificadas como costura (query + UI + guards). Alembic head permanece `025`. Só haveria migration se se inventasse `operation_key`, segunda entidade ou saldo em Customs — **proibido**. |
| 7 | História de teste | **Família 202**, continuação conceitual do Elo 7: Shipment **ARRIVED** → processo **PARTIALLY_CLEARED** → nacionalização parcial (SKU `8057628953814` qty 50 de 200) → **DOMESTIC_IN** do residual → saldo/posição → reload → segundo receipt → over-receipt bloqueado. Sem quitar Payables nem CUSTOMS_FUNDING. |
| 8 | DECs a ratificar | **DEC-E8-PATH**, **DEC-E8-BIND**, **DEC-E8-COVERAGE**, **DEC-E8-ARRIVAL**, **DEC-E8-DOC**, **DEC-E8-NAT-REVERSE**, **DEC-E8-STUBS** (secção 12). |
| 9 | Após ratificação, executar sem novo aceite? | **Sim.** E8-0…E8-6. Parar só: migration inesperada; NAT-REVERSE a exigir ciclo/arquitectura transversal; CUSTOMS_FUNDING; reabrir E7. |

**Hipótese central do advisor: CONFIRMADA.** Grande parte do domínio existe desde J#5 I5-4. A nacionalização do Elo 7 **não** desemboca numa jornada clara de recebimento/estoque. O gap não é “falta tabela StockBalance”.

---

## Pré-autorização Q1–Q7 (código real, 2026-08-17)

### Q1 — NAT-REVERSE: onde cabe o guard — **C refutado; fica B**

Hipótese (“a proibição de ciclo vale entre domínios, não na camada de rota”) — **refutada**.

- Grafo: `customs` ↛ `inventory`; `inventory` → `customs` ([`module_graph.py`](../../../v2/app/foundation/module_graph.py) L84–85).
- Arch test [`test_module_deps_respect_graph`](../../../v2/tests/architecture/test_import_boundaries.py) L69–99: **qualquer** `.py` do pacote, incluindo `nationalization_routes.py`. `app.inventory` a partir de Customs = `customs -> inventory not in ALLOWED_DEPS`.
- Excepção de `routes.py` é só **foundation** (`FOUNDATION_ALLOWED_FILENAMES`), não outros módulos.
- Precedente de rota a ler `public` alheio: **sim**, mas só em aresta permitida — [`treasury/routes.py`](../../../v2/app/treasury/routes.py) L8–11 (billing/catalog/documents); [`logistics/routes.py`](../../../v2/app/logistics/routes.py) L20 (`orders_public`). Nenhum precedente contra o grafo.
- Abrir `customs → inventory` no grafo falha [`test_no_cycles_in_allowed_graph`](../../../v2/tests/architecture/test_import_boundaries.py) L128–144.
- Guard em `reverse_nationalization` ([`nationalization_commands.py`](../../../v2/app/customs/nationalization_commands.py) L344–361) hoje: só `CONFIRMED` + versão. UI: [`NationalizationPanel.tsx`](../../../v2/frontend/src/features/customs/NationalizationPanel.tsx) L194–207.
- `inventory.public` não exporta “nat reversível”; mesmo que exportasse, Customs não pode importar.

**Decisão (cai agora, não espera E8-1 para escolher C):** **B**. E8-2 oculta/desabilita Reverter quando o residual item-level (GET Inventory) ou receipts CONFIRMED do processo mostram `received_qty > 0` naquela nat. Sem aceite extra.

**Parágrafo para o diário E8-1 (já decidido):** NAT-REVERSE = B. C local na rota Customs é ciclo. API `POST .../nationalizations/{id}/reverse` permanece capaz de duplicar saldo — item nomeado `E8-NAT-REVERSE-API` no Roadmap **só no E8-6** (Roadmap agora inalterado). Elo 8 não promove com furo anónimo: o handoff de fecho tem de trazer o id.

### Q2 — Loop de reparo vs drop_all — **aceite; escrito no mestre**

`conftest` drop_all em `epic_v2_test`. Se E8-5 falhar e a correção exigir pytest: **corrigir → pytest full → re-bootstrap fixture 202 → re-walk do zero**. Proibido: pular pytest para preservar massa; enfraquecer asserção; `.skip`/`.only`; editar OpenAPI gerado. Três falhas no mesmo ponto = parar.

### Q3 — `cleared_not_received` — **confirmado agregado global**

[`queries.py`](../../../v2/app/inventory/queries.py) L135–137: `sum_nationalized_qty_by_product` + `sum_domestic_received_for_product` (ambos **por product_id, todos os processos**). Label UI hoje: “Liberado não recebido” ([`inventoryLabels.ts`](../../../v2/frontend/src/features/inventory/inventoryLabels.ts) L11–12) — **sem escopo**.

No teste multi-processo (Product P; A nacionaliza 10; B nacionaliza 10; receber 4 de A):

| Vista | Valor |
|---|---|
| Residual item-level processo A | 6 |
| Residual item-level processo B | 10 |
| `SkuPosition.cleared_not_received` | **16** |

Na 202 limpa o número **coincide com o residual do processo por acidente** (um processo, aqueles SKUs).

**Escolha: rotular o escopo na UI (E8-3), não só item aberto.** Justificativa: o campo é facto real (não stub); deixar sem rótulo faria o walk 202 “provar” o sentido errado. Texto: deixar claro que é **agregado do produto em todos os processos**, não o residual deste processo. ReceiptPanel continua a ignorar o campo. Não esconder o número (não transformar em stub).

### Q4 — Identidade 202 — **catálogo sim; slug-shell no caminho UI**

- `Product` só tem `sku` + `description` — **não existe grupo de produto** ([`catalog/models.py`](../../../v2/app/catalog/models.py) L25–35).
- Seed API [`e7_walk_seed.py`](../etapa-elo-7/logs/e7_walk_seed.py) L18–27 / L66–70 grava nomes (`WASH BAG STARLIGHT - RED`, etc.).
- Aceite UI Elo 7: pedido na mão via [`OrderCreatePage.tsx`](../../../v2/frontend/src/features/orders/OrderCreatePage.tsx) L125–128: `createProduct({ sku, description: sku })`. Handoff E7 §17: “nomes de SKU = o próprio código”.
- Residual de nacionalização lê `shipment_item_facts` → `sku_snapshot` / `description_snapshot` do OrderItem ([`logistics/queries.py`](../../../v2/app/logistics/queries.py) L16–33), não um “nome de grupo”.
- W1 (query E8-1 + Catalog): se a fixture for **seed com EAN_DESC**, a tabela mostra **WASH BAG STARLIGHT - RED** + muted `8057628953814`. Se for **pedido na mão** como o aceite E7, mostra **8057628953814** duas vezes (strong + muted). Em nenhum caso mostra `product_id` / `nationalization_item_id`.
- **“Sem ID cru” é nominal para o caminho UI:** não há ID interno, mas também não há nome distinto do código. Elo 8 **não** corrige `OrderCreatePage`. Fixture E8 prefere o seed com descrição humana (já existe) para o walk ser legível; o handoff declara a limitação do pedido na mão.

### Q5 — Elo 8 × J#5-REC — **confirmado**

B.2 hoje: elo 8 FRÁGIL — “exige produto de catálogo”. Isso mistura (a) FK Inventory→Product e (b) campanha J#5-REC (compromisso↔SKU, **não** iniciada).

Após PASS: elo **LIGADO para itens cujo produto já está no catálogo**. A 202 do gate entra nesse conjunto. Pedido só-compromisso continua fora. **E8-6 reescreve a linha B.2 com essa condição e declara dependência de J#5-REC. Não apagar a ressalva ao subir 8/10.** A barra só sobe com a condição escrita. Roadmap **agora** inalterado.

### Q6 — Caso A / entreposto — **congelar select; decisão Ricardo**

Não alterar o conjunto de tipos até resposta. Select Elo 8 = **só DOMESTIC_IN**. Se “usamos entreposto”: Caso A → item **datado** em B.6 (não escopo desta campanha). Domínio BONDED/RECLASS intacto (pytest).

### Q7 — Atrito no walk — **aceite; escrito no mestre**

Mesmo percurso W1–W8 anota e **segue**: cliques a mais, dado pedido duas vezes, jargão, ID interno, passo só via API. Não consertar no meio do walk. Cabeçalho: asset do frontend (build + porta) + Runtime + Database. Texto literal das telas; screenshot só se a palavra não bastar.

---

## 1. Contrato atual Nationalization ↔ Inventory

Direção única: **Inventory → Customs public**. Customs **não** importa Inventory (grafo: `customs` ↛ `inventory`; o inverso criaria ciclo).

`confirm_nationalization` / `nationalize`:

- marca `Nationalization.status = CONFIRMED`;
- atualiza `ImportProcess` para `PARTIALLY_CLEARED` / `CLEARED`;
- grava audit `nationalization.confirm`;
- **não** cria `GoodsReceipt`, movimento nem `StockBalance`.

Comentário canónico no domínio: *“Nationalization NÃO cria StockBalance; GoodsReceipt domestic consome residual.”*

Estoque só nasce com `confirm_receipt` (HTTP `POST /api/inventory/receipts/{id}/confirm`).

`GoodsReceiptLine.nationalization_item_id` **já existe** (FK opcional). Header `nationalization_id` e `process_id` também. `shipment_item_id` na linha é **armazenado e não usado** em guards.

---

## 2–6. P0 — o que o código faz hoje

### Movimentos

| Tipo | Existe? | Como entra | Notas |
|---|---|---|---|
| `BONDED_IN` | Sim | Receipt `BONDED_IN` em location BONDED | Pode **preceder** nacionalização. **Sem teto** vs embarque/nac. |
| `DOMESTIC_IN` | Sim | Receipt `DOMESTIC_IN` em DOMESTIC | Exige cobertura de nacionalização CONFIRMED |
| `RECLASS_OUT` + `RECLASS_IN` | Sim | Receipt `RECLASS` (par) | Destino DOMESTIC; origem BONDED (`BONDED-MAIN` default); exige cobertura **e** saldo bonded |
| `QUARANTINE_IN` / `OUT` | Sim | Só `record_adjustment` (perm `inventory:adjust`) | **Sem** receipt type QUARANTINE. Sem UI. Fora do Elo 8 |
| `ADJUSTMENT` / SHORTAGE / SURPLUS / DAMAGE | Sim | adjustment API | Fora do Elo 8 |
| `REVERSAL` | Sim | `reverse_receipt` | Append-only; devolve residual recebível |

Não existem entidades paralelas. Não há `Location` aparte: é `StockLocation` (seed `BONDED-MAIN`, `DOMESTIC-MAIN`, `QUARANTINE-MAIN`).

### StockBalance

Derivado: `qty := qty + delta` no post; `rebuild_stock_balances` = Σ movimentos. GET sem linha devolve `"0"` sem inserir. Pode ficar negativo em adjustment (sem CK) — fora do Elo 8.

### SkuPosition

Não é tabela. Query `GET /api/inventory/sku/{product_id}/position`.

| Campo | Hoje | Classificação |
|---|---|---|
| `available_qty` | Σ DOMESTIC | Fato real |
| `bonded_qty` | Σ BONDED | Fato real |
| `quarantine_qty` | Σ QUARANTINE | Fato real |
| `cleared_not_received_qty` | nacionalizado − DOMESTIC_IN/RECLASS confirmados, **por produto global** | Fato real, **escopo largo** |
| `in_clearance_qty` | hardcoded `0` | Stub (API mente zero; UI “Não disponível”) |
| `in_transit_qty` | sempre `0` (`ShipmentItem` sem `product_id`; Inventory ↛ Orders) | Stub |
| `future_order_qty` | `null` | Stub honesto |
| `balances` | por localização | Fato real na API; **UI não renderiza** |

### UI hoje — o operador consegue sem API?

| Ação | UI sem API? |
|---|---|
| Nacionalizar (residual SKU, parcial, over-qty) | **Sim** (Elo 7) |
| Ver residual **nacionalizável** | **Sim** |
| Ver residual **recebível** | **Não** (não há endpoint nem tabela) |
| Criar/confirmar/reverter GoodsReceipt | **Parcial** — botões existem; exige IDs internos |
| Escolher localização / tipo sem código cru | **Não** (texto livre; lista só em muted) |
| Escolher SKU do contexto da liberação | **Não** |
| Consultar movimentos | **Sim** (leitura) `/inventory/movements` |
| Abrir SkuPosition sem saber `product_id` | **Não**, salvo clicar num movimento já existente |
| Ver `GET /balances`, ajustar, rebuild | **Não** — só API |
| `/stock` V2 | **Não existe** |

O único write de estoque na UI é `ReceiptPanel` em `/customs/:processId` (`customs-section-recebimentos`). Inventory pages são read-only.

J#5 E2E (`j5-acceptance.spec.ts`) **preenche IDs** e ainda chama `nationalization-product-id` — testid **removido** no Elo 7. Suite J#5 de UI está **obsoleta** contra a nacionalização atual.

Walk Elo 7 (`e7-ui-accept-db.json`): `"receipts": []`. Fronteira visível (`receipt-elo8-notice`).

---

## 7–10. Onde a cadeia quebra / bug vs costura

**Quebra operacional após Elo 7:**

```
Nationalization CONFIRMED
    ✗  (não há residual recebível na cara)
    ✗  (operador não identifica SKU sem ID)
GoodsReceipt DRAFT/CONFIRMED
    ✓  domínio
InventoryMovement + StockBalance
    ✓  domínio
SkuPosition (available / cleared_not_received)
    ✓  domínio; UI só depois de saber product_id
```

O operador ainda precisaria redigitar: tipo enum, código de localização, ID da liberação, ID do produto, ID do item da liberação, quantidade.

**Não é ausência de Inventory.** Classificação do gap principal: **EXISTENTE MAS NÃO COSTURADA** + **UX INSUFICIENTE**.

Buracos reais (não bloqueiam o gate se o walk não os exercitar, mas devem ser nomeados):

1. Cobertura **product-level** (sem `nationalization_item_id`) soma nacionalizado/recebido **em todos os processos**. Associação silenciosa entre compras.
2. `product_id` da linha **não é validado** contra `NationalizationItem.product_id`.
3. `reverse_nationalization` **não** vê estoque (Customs ↛ Inventory; ciclo proibido). Re-nacionalizar + re-receber o mesmo SKU **duplica saldo**.
4. `BONDED_IN` sem teto e sem exigir Shipment ARRIVED — estoque bonded pode nascer sem facto físico de chegada.
5. `insufficient_bonded` cai em HTTP **400** (não está no mapa 409/422).
6. `over_receipt` na UI vira `Conflito (409 · over_receipt): …` — não tem copy de operador como o Elo 7 fez para `over_nationalization`.

Itens 1–2 fecham-se no teste multi-processo (E8-1/E8-4). Item 3: **DEC-E8-NAT-REVERSE** (B na UI ou PARAR). Itens 4–6: ARRIVAL/DOC/copy; 5–6 não bloqueiam o gate.

### Investigação NAT-REVERSE (código real, este turno)

1. **UI:** botão Reverter em `NationalizationPanel` se `CONFIRMED` + `customs:write`. Sem olhar para receipts. Mesma página que Recebimentos → jornada operacional normal **hoje** consegue reverter nat com estoque.
2. **API:** `POST .../nationalizations/{id}/reverse` pública (`customs:write`).
3. **Guard:** só status CONFIRMED + versão.
4. **Com receipt CONFIRMED:** nat vira REVERSED; movimentos/saldo ficam; novo item de nat tem received=0 → segundo DOMESTIC_IN duplica.

**A está refutado.** Execução: B (ocultar botão) sem novo aceite; C só se local e sem ciclo; senão PARAR.

---

## Classificação de capacidades

| Capacidade | Owner | Classe | Reutilizar | Proibido reimplementar |
|---|---|---|---|---|
| `GoodsReceipt` + Line + confirm/reverse | Inventory | EXISTENTE E OPERÁVEL (API) | Sim | Segunda entidade de recebimento |
| `InventoryMovement` append-only | Inventory | EXISTENTE E OPERÁVEL | Sim | Ledger paralelo |
| `StockBalance` derivado + rebuild | Inventory | EXISTENTE E OPERÁVEL | Sim | Segundo saldo; persistir estoque em Customs/Order |
| Locations default BONDED/DOMESTIC/QUARANTINE | Inventory | EXISTENTE E OPERÁVEL | Sim | Product paralelo; status de estoque na Order |
| `DOMESTIC_IN` consome nat | Inventory | EXISTENTE E OPERÁVEL | Sim | Movimento manual “para fechar” |
| `RECLASS` pareado | Inventory | EXISTENTE E OPERÁVEL (API/pytest) | Sim (regressão) | Reclass “fake” |
| `BONDED_IN` pré-nac | Inventory | EXISTENTE E OPERÁVEL (API) | Sim se Caso A | — |
| Residual **nacionalizável** | Customs | EXISTENTE E OPERÁVEL | Só leitura | Não copiar para estoque |
| Residual **recebível** | Inventory | **REALMENTE AUSENTE** (query) | Calcular de nats CONFIRMED + receipts | Não guardar residual em Customs |
| ReceiptPanel | Frontend Customs | **UX INSUFICIENTE** | Painel/secção | Não criar `/stock` V1 |
| Identidade SKU no receipt | Frontend | **UX INSUFICIENTE** | Padrão da tabela Elo 7 (não A0/C6) | Digitar `product_id` |
| SkuPosition física + cleared_not_received | Inventory | EXISTENTE E OPERÁVEL | **Verificação** W3 (não elegibilidade) | Não usar para qty do processo; não stub→zero |
| SkuPosition in_clearance / in_transit / future | Inventory | Stub / **SOMENTE FALTA DE EVIDÊNCIA** futura | UI já diz “Não disponível” | Ampliar Elo 8 a Reporting |
| `pos.balances` na UI | Frontend | EXISTENTE MAS NÃO COSTURADA | Campo já no JSON | Novo ecrã de saldos |
| Audit HTTP receipt | Inventory routes + Audit | EXISTENTE E OPERÁVEL | Mesma UoW | Log paralelo |
| `document_id` no receipt | Inventory | EXISTENTE MAS NÃO COSTURADA | FK opcional | Exigir PDF novo |
| Ajuste / quarentena UI | Inventory | EXISTENTE (API) / UX ausente | Fora | Não no Elo 8 |
| J#5 E2E inventory | Frontend e2e | EXISTENTE COM BUG (stale) | Atualizar | Nova suite paralela sem necessidade |
| E7-ARRIVAL-GATE | Customs | Backlog | Não implementar | Não confundir com Elo 8 |
| Reverse nacionalização após stock | Customs UI+API | **EXISTENTE COM BURACO** | Hide/disable (B) | Ciclo Customs→Inventory; orquestração transversal |

---

## Fronteira física × aduaneira — Caso A vs Caso B

O Blueprint §7.11 já admite **os dois**:

- **Caso A:** ARRIVED → `BONDED_IN` → (depois) Nationalization → `RECLASS` BONDED→DOMESTIC. Conservação física: bonded↓ + available↑; total físico constante.
- **Caso B:** Nationalization → `DOMESTIC_IN` quando **não** há estoque bonded prévio.

Elo 7 na 202 fez ARRIVED + nacionalização **sem** nenhum receipt (`receipts: []`). O elo 8 da cadeia (“nacionalizado vira estoque por produto”) é o consumo da qty **nacionalizada** em saldo por SKU — isso é `DOMESTIC_IN` ou `RECLASS`, não `BONDED_IN` sozinho (entreposto ≠ disponível).

**Proposta DEC-E8-PATH:** o **gate do Elo 8** é o **Caso B** (`DOMESTIC_IN`). Caso A permanece **regressão de domínio** (pytest SC-10).

Na UI do ReceiptPanel Elo 8, **qualquer tipo mostrado como opção normal tem de ser executável sem IDs crus**. `BONDED_IN` / `RECLASS` **não** entram no select deste fluxo. Isso é **escopo de UI**, não remoção da API/domínio.

Não colapsar dimensões: bonded ≠ domestic ≠ nacionalizado ≠ arrived.

---

## Onde o Elo 8 termina

**Termina quando**, na mesma história 202:

1. o operador vê qty nacionalizada / já recebida / residual recebível (SKU/nome, sem ID cru);
2. registra o movimento físico correto (`DOMESTIC_IN` **pela UI**);
3. `StockBalance` DOMESTIC muda;
4. movimentos + SkuPosition.available verificam o resultado (**SkuPosition não escolhe qty**);
5. `cleared_not_received` agregado é coerente no contexto limpo da 202; stubs não se vendem como feitos;
6. reload persiste; residual item-level não reapresenta qty consumida;
7. segundo receipt do residual e over-receipt na UI;
8. reverse receipt na UI + re-receber; reverse de nacionalização **não** disponível após estoque;
9. W8 na tabela de auditoria do processo;
10. double-click não duplica.

**Não inclui:** landed cost, costing, fechar Order, Dashboard, pagar numerário, quarentena operacional, stubs logísticos, J#5-REC (compromisso↔SKU — outra campanha).

---

## Quantidade / residual — gates a exigir na execução

Três residuais distintos (não misturar):

| Residual | Fórmula | Dono |
|---|---|---|
| Alocação processo | item − alocado | Customs |
| Nacionalizável | alocado − nacionalizado CONFIRMED | Customs (`clearance-residuals`) |
| **Recebível (canónico do Elo 8)** | nacionalizado CONFIRMED − DOMESTIC_IN/RECLASS CONFIRMED **do mesmo NationalizationItem** | Inventory (query E8-1). **Única** fonte de qty do ReceiptPanel |

| Gate | Esperado |
|---|---|
| 1. Receipt parcial | Receber 50 do SKU 3814 (já nacionalizado 50) **ou** receber parte se o walk nacionalizar mais; na 202 o parcial já é 50/200 nacionalizados — receber p.ex. 20 depois 30 do mesmo item |
| 2. Segundo receipt do residual | Após parcial, o restante aparece; segundo confirm soma saldo |
| 3. Tentativa > residual | 409 `over_receipt` + copy pt-BR (espelho Elo 7) |
| 4. Nacionalização parcial | Já existe (Elo 7); Elo 8 consome só o nacionalizado, não o embarcado restante |
| 5. Múltiplos SKU | 202 tem 7 itens na nat #1; receber 3814 e pelo menos mais um SKU |
| 6. Múltiplas localizações | **Não** criar location nova. Prova dimensional = DOMESTIC-MAIN no gate. Caso A (BONDED vs DOMESTIC) fica na regressão pytest |
| 7. Reload | Reabrir processo + SkuPosition; saldos iguais |
| 8. Retry / double-click | Busy/disabled; um draft; double-click ≠ dois receipts; reload não devolve qty consumida; `receipt_immutable` no domínio |
| 9. Cancel/reversal | Reverse **receipt** na UI. Reverse **nacionalização** oculto após estoque (DEC-E8-NAT-REVERSE B). Walk não reverte nat |
| 10. Audit | W8 na tabela UI do processo (`goods_receipt.*` a agregar em E8-3). GET só complemento |

Nenhuma qty nasce de reload. Draft não consome residual (já é assim).

---

## Identidade do produto

Elo 7 já resolve SKU/nome no residual **nacionalizável**. Inventory recebe identidade via `product_id` obrigatório na linha + Catalog `get_product`.

**Não copiar A0/C6** (candidatos de documento). A chave estrutural já existe: **`NationalizationItem`** (`product_id` + qty + id).

Política 0/1/N para residual **recebível**:

| N | UI |
|---|---|
| 0 | EmptyState “Nada a receber” |
| 1 | Uma linha visível; qty proposta = residual; **não** confirmar sozinho |
| N | Tabela completa; operador escolhe qty > 0; sem associação silenciosa |

Proibido: digitar `product_id` / `nationalization_item_id`; SKU arbitrário do catálogo global.

---

## Documentos / provenance / audit

- Receipt HTTP já audita create / add_lines / confirm / reverse na mesma UoW.
- `document_id` opcional, **sem** `documents.public`.
- **DEC-E8-DOC:** Elo 8 **não** exige documento novo. Provenance = `process_id` + `nationalization_item_id` no movimento. ARRIVED + Doganale + nat já documentam a compra 202.

---

## E7-ARRIVAL-GATE × Elo 8

Inventory **não** exige Shipment ARRIVED. `BONDED_IN` / `DOMESTIC_IN` não lêem status de embarque. Comentário de domínio: ARRIVED sozinho não cria stock (provado em teste).

A 202 do gate **já está ARRIVED**. Integridade do walk Elo 8 não depende de implementar a trava.

**Proposta:** **não** resolver E7-ARRIVAL-GATE nesta campanha (pedido do advisor). Não adicionar gate ARRIVED em Inventory. Risco residual: bonded pode nascer sem chegada — backlog permanece em Customs. Se o advisor quiser trava física no receipt, isso é DEC nova e **não** está no menor conjunto.

---

## CUSTOMS_FUNDING

Nenhuma regra de domínio liga pagamento do Numerário a `confirm_receipt`. Obrigação financeira ≠ liberação ≠ recebimento. **Fora.**

---

## Barras (planeadas na autorização; **aplicadas no E8-6** → Roadmap **0.5.121**)

Denominadores inalterados. Aduana/estoque **não** subiu.

| Barra | Antes (0.5.120) | Depois (0.5.121) |
|---|---|---|
| Cadeia | 7/10 = 70% (elo 8 FRÁGIL = 0 no numerador) | **8/10 = 80%** — elo 8 LIGADO só com produto no catálogo (B.2) |
| Aduana/estoque | 2/3 = 67% (falta **numerário se paga**) | **Inalterada** |
| Ingestão / Financeiro / Logística / Custo / Painel | — | **Inalteradas** |

J#5-REC **não** é Elo 8 (reconciliação compromisso↔SKU) — permanece na ressalva de B.2.

---

## DECs (deste mestre — a ratificar na autorização de execução)

| ID | Redação |
|---|---|
| **DEC-E8-PATH** | Gate = Caso B (`DOMESTIC_IN`). Select congelado (só esse tipo) até o Ricardo decidir entreposto. Se “usamos entreposto”, Caso A = item datado no backlog — **não** desta campanha. APIs BONDED/RECLASS intactas. |
| **DEC-E8-BIND** | Residual item-level; 0/1/N; sem IDs crus; sem auto-confirm. |
| **DEC-E8-COVERAGE** | Query item-level = única fonte de qty. SkuPosition não elege. Teste dois processos / mesmo Product. Sem fallback global no operador. |
| **DEC-E8-ARRIVAL** | Não implementar E7-ARRIVAL-GATE; não exigir ARRIVED no receipt. |
| **DEC-E8-DOC** | Sem PDF novo no receipt. |
| **DEC-E8-NAT-REVERSE** | **B.** C na rota Customs = ciclo (arch test). Ocultar Reverter na UI se received_qty > 0. API continua aberta → `E8-NAT-REVERSE-API` nomeado no E8-6. Walk não reverte nat após estoque. |
| **DEC-E8-STUBS** | Não implementar stubs; não pintar zero. SkuPosition = verificação agregada, não prova única nem elegibilidade. |

Se PASS, **PATH / BIND / COVERAGE / STUBS** entram no Blueprint como invariantes (E8-6). Sem massa 202 no Blueprint.

---

## Plano resumido (autorização única)

Preflight → query residual + guards → UI ReceiptPanel → copy/links/balances → testes → walk 202 → documentar/barras.

Detalhe modular: [`E8_EXECUTION_PLAN.md`](E8_EXECUTION_PLAN.md).

| Fase | Problema | Existente vs novo | Owner | UI gate | Fecha Elo 8? |
|---|---|---|---|---|---|
| E8-0 | Runtime / pytest baseline | existente | Foundation | — | Não |
| E8-1 | Residual recebível + bind | query + guards novos; entidades velhas | Inventory | — | Não |
| E8-2 | IDs crus; tipos incompletos; reverse nat após stock | UI nova; domínio intacto | ReceiptPanel + hide reverse nat | Só DOMESTIC_IN; residual item-level; um draft | Não |
| E8-3 | Copy; balances; audit sem goods_receipt | UI sobre JSON/audit existentes | Frontend | over-receipt; SkuPosition verificação; W8 visual | Não |
| E8-4 | Testes stale / cobertura | pytest+e2e+vitest | Tests | e2e sem `fetch` de IDs | Não |
| E8-5 | Cadeia 7→8 na 202 | massa 202 + cliques | Inventory+Customs UI | Abri/Vi/Cliquei/Resultado `:8082` | **Sim, se PASS** |
| E8-6 | Fechar docs/barras | só documentação | Roadmap/Blueprint no **fecho** | — | Fecha o relato |

---

## Riscos

- Pytest `drop_all` em `epic_v2_test` apaga a massa 202 — walk **depois** do pytest, como Elo 7.
- Não tocar `epic_v2` nem Orders 31/34.
- J#5 E2E quebrado até E8-4.
- Fallback product-level: mudança de contrato se DEC-E8-COVERAGE.
- SC-10 (Caso A) fica em pytest — UI Elo 8 não oferece BONDED/RECLASS incompletos.
- Reverse nat na mesma página que receipts: E8-2 tem de ocultar; senão não promover.
- Audit do processo hoje não lista `goods_receipt` — E8-3 agrega para W8 visual.

---

## Recomendação

**Aceito pelo advisor (2026-08-17).** Elo 8 **ENCERRADO**. Ressalva de catálogo em B.2 permanece. Backlog intocado (`E8-NAT-REVERSE-API`, J#5-REC, Caso A, `E7-ARRIVAL-GATE`, atritos B.6). Próxima ação canónica em B.1 = pagar numerário — **não** iniciada nesta ratificação.

---

## Fechamento

**ETAPA:** Elo 8  
**STATUS:** **DONE / ENCERRADO** (aceite advisor; E8-FINAL-VERIFY **PASS**; barras 8/10 inalteradas; Roadmap **0.5.123**)

**Hipóteses (execução)**

| Hipótese | Veredicto |
|---|---|
| Domínio Inventory já existia desde J#5 | **Confirmada** |
| Gap = costura UI residual item-level → DOMESTIC_IN → saldo | **Confirmada** |
| Precisa reimplementar Inventory / segundo saldo / migration | **Refutada** |
| SkuPosition decide qty do receipt | **Refutada** (agregado; rótulo no W3) |
| C local na rota Customs fecha NAT-REVERSE | **Refutada** (ciclo); ficou B + `E8-NAT-REVERSE-API` |
| Settlement do numerário é precondição de estoque | **Refutada** |

**DECs:** PATH (select congelado), BIND, COVERAGE, ARRIVAL, DOC, NAT-REVERSE **B**, STUBS — no Blueprint salvo hide UI e ARRIVAL/DOC (handoff).  
**Riscos restantes:** `E8-NAT-REVERSE-API`; compromisso sem Product (J#5-REC); Caso A entreposto.  
**Próxima etapa lógica:** pagar numerário no tesouro (B.1).  
**Arquivos de produto (campanha):** `v2/app/inventory/{commands,queries,public,routes}.py`; `v2/tests/test_inventory_i5_4.py`; `v2/frontend/src/features/customs/{ReceiptPanel,ReceiptPanel.test,NationalizationPanel,NationalizationPanel.test,CustomsDetailPage,customsPermissions}.tsx|ts`; `inventory/{SkuPositionPage,inventoryApi,inventoryLabels}`; `ui/domainLabels.ts`; `e2e/j5-acceptance.spec.ts`; client OpenAPI regenerado (`openapi.json` / `schema.ts`).

**Arquivos a retornar:** este handoff (mestre e evidências brutas em Updated/Evidence).

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/README.md; docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md; docs/v2/etapa-elo-8/E8_EXECUTION_PLAN.md; docs/v2/etapa-elo-8/E8_DIARY.md
- Evidence: docs/v2/etapa-elo-8/
- Roadmap status: 0.5.123 **aceito** — Elo 8 ENCERRADO; barras inalteradas 8/10; backlog preservado; próxima = pagar numerário (não iniciada)
- Next TODO: pagar numerário no tesouro (settlement CUSTOMS_FUNDING)
- Return to advisor: docs/v2/etapa-elo-8/E8_ADVISOR_HANDOFF.md
```
