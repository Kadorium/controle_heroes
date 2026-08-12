# Investigação — compromisso → SKU, barras e encerramento

| Campo | Valor |
|---|---|
| Data | **2026-08-12** |
| Status | **DONE** (só leitura de produto; Roadmap §0 ajustada) |
| Runtime | `:8081` / `epic_v2` / Alembic **023** / `schema_ok` |
| Asset | **`index-B-ChOX1L.js`** |
| Health | `GET /api/health` → `status=ok`, `logical_database=epic_v2`, `runtime_lane=Operação`, `alembic_head=023` |
| Pedido | **589** id **31** — não alterado |

Screenshots (quando a palavra não basta): [`01-cockpit.png`](01-cockpit.png), [`02-comercial-itens.png`](02-comercial-itens.png), [`03-faturas-compromisso.png`](03-faturas-compromisso.png).

---

## 1. Percurso de tela (obrigatório)

Sessão **já autenticada** ao abrir `:8081` (não fiz login nesta fatia; não chamei API de escrita). Nenhum passo do percurso foi por API.

### Health e asset (antes de clicar)

- `GET /api/health`: `ok` / `epic_v2` / head `023` / `schema_ok=true`.
- HTML de `/`: script `/assets/index-B-ChOX1L.js`.

### Abri / Vi / Cliquei

1. **Abri** `http://127.0.0.1:8081/`. **Vi** redirecionar para `/orders`. Título **Pedidos**. Subtítulo **Fila operacional de compras**. Chip **Todos** pressionado. Primeiro link da tabela: **589**. Também **FX-…**, **WT-…**, **BILL-…**, **E2E-…**. Rodapé **Exibindo 1–21 · até 50 por página**. Botão câmbio **EUR/BRL 5,9523 · Frankfurter (ECB)**.
2. **Cliquei** **Confirmado**. URL ` /orders?status=CONFIRMED`. **Vi** chip **Status: Confirmado ×**, **Limpar filtros**, **Exibindo 1–16 · até 50 por página**. **589** continua o primeiro link.
3. **Cliquei** **589**. URL `/orders/31` (cockpit, não a ficha de itens). **Vi** título **589**; subtítulo **Heroe's Srl · EUR · Somente leitura**; selo **Confirmado**; **Atualizado 10/08/2026 14:30:06 -03:00**; botões **Adiantamentos** e **Abrir comercial**. Cartões: Pedido **EUR 830.000,00**; Faturado **EUR 0,00**; Pago (alocado) **EUR 0,00**; Adiantado (crédito) **EUR 0,00**; Saldo **EUR 0,00**; Próx. venc. **—**; Exposição FX **BRL 0,00**; FX realizado **BRL 0,00**. **Faturas:** Nenhuma fatura. **Obrigações:** Nenhuma obrigação. **Pagamentos realizados deste pedido:** Nenhum pagamento realizado. **Candidatos a alocação (fornecedor):** aviso *Mesmo fornecedor e moeda — podem ser de outros pedidos. Não substituem a lista de pagamentos deste pedido.* + **Nenhum candidato**. Documento `Ordine_589 (1) (1).pdf`. Auditoria: **Confirmação** 10/08/2026 14:30:06, ator **—**. **Não vi** tabela de itens nem ação de SKU.
4. **Cliquei** **Abrir comercial**. URL `/orders/31/commercial`. **Vi** título **Pedido 589**; **Heroe's Srl · EUR · 04/06/2026**; **Cockpit** / **Voltar à fila**; campo **Motivo do cancelamento** (placeholder **Descreva o motivo**) + botão **Cancelar**; selo **Confirmado**; **Revisão 4**; faixa azul **Pedido somente leitura — Confirmado**.
5. **Vi** cabeçalho: **Data: 04/06/2026**; **Notas: Criada via ingestão — documento IR 26**.
6. **Vi** tabela **Itens** (sem botão Adicionar, sem seletor de produto, células não editáveis):

   | Tipo | SKU / código | Descrição | Qtd | UM | Preço | Total |
   |---|---|---|---|---|---|---|
   | Compromisso | I.V. 2 | racchette 2027 GRAFICATE | 14.600 | PZ | EUR 50,00 | EUR 730.000,00 |
   | Compromisso | I.V. 1 | racchette 2027 NON GRAFICATE | 2.000 | PZ | EUR 50,00 | EUR 100.000,00 |

   **Total comercial: EUR 830.000,00**.
7. **Vi** **Adiantamentos (crédito)** — formulário **editável** apesar da faixa somente leitura: Valor (EUR), Taxa, BRL, datas, referência, **Anexar PDF de câmbio deste adiantamento**, **Registrar adiantamento**. Texto: *Adiantamento é crédito (dinheiro já saiu). Não gera título em Contas a pagar.* **Nenhum adiantamento registrado**.
8. **Vi** **Documentos**: `Ordine_589 (1) (1).pdf` **Abrir** / **Baixar**; **Anexar documento do pedido (Ordine e afins)**.
9. **Vi** **Faturas** — aviso literal:

   > Este pedido só tem linhas de compromisso (artigos ainda sem SKU final). As faturas destes itens entram pela importação da Fattura do fornecedor — os produtos reais chegam por ali. Não é possível criar fatura manual aqui.

   Tabela: GRAFICATE pedida 14.600 / faturada 0 / disponível **—**; NON GRAFICATE 2.000 / 0 / **—**. **Nenhuma fatura**. Sem botão de criar fatura.

**Passos só por API:** nenhum neste percurso.

### Atrito (anotei e segui)

- Clique na fila abre o **cockpit**, não os itens. Para ver compromisso/SKU precisa **Abrir comercial** (segundo clique).
- Faixa **somente leitura** convive com **Cancelar**, **Registrar adiantamento** e **Anexar documento** — a leitura não é total.
- Nota **documento IR 26** e URL `/orders/31` expõem id interno.
- Ator da auditoria **—**.
- Jargão **Candidatos a alocação (fornecedor)** no cockpit de um pedido sem fatura.
- Aviso das faturas promete que **os produtos reais chegam pela Fattura**. O commit da Fattura, no código, **recusa** pedido só-compromisso. A tela mente.
- Fila **Confirmado** ainda mistura dezenas de pedidos de ensaio (FX/BILL/E2E).

---

## 2. Hipótese 1 — dois problemas empilhados

**Reformulada e confirmada na substância.** São dois problemas distintos. Há um terceiro, que a tela já anuncia e o código não cumpre.

### O que impede a linha CONFIRMED de receber produto

Quatro camadas, todas presentes. Não é só “falta tela”.

| Camada | Evidência |
|---|---|
| Guarda de status | `_require_draft` em [`commands.py`](../../../v2/app/orders/commands.py) L25–27. `add_item` L130, `update_item` L222, `remove_item` L245. Erro: *Ordem só pode ser editada em DRAFT* ([`errors.py`](../../../v2/app/orders/errors.py) L16–18). |
| Schema | `ck_order_items_line_kind_product_id`: PRODUCT exige `product_id`; COMMITMENT exige `product_id` nulo ([`models.py`](../../../v2/app/orders/models.py) L66–69). Não dá para “só preencher o produto” sem virar o tipo da linha no mesmo passo. |
| Contrato da API | `ItemUpdate` aceita só quantidade/preço/UM ([`routes.py`](../../../v2/app/orders/routes.py) L53–57). `update_item` não tem parâmetro de produto (L208–236). Fachada pública **não** exporta conversão ([`public.py`](../../../v2/app/orders/public.py)). |
| Tela | `editable = order.status === "DRAFT"` ([`OrderDetailPage.tsx`](../../../v2/frontend/src/features/orders/OrderDetailPage.tsx) L93). Faixa **Pedido somente leitura**. Tabela sem ação. Itens novos só na criação do pedido. |

Não é regra de domínio do tipo “CONFIRMED nunca pode ganhar produto”. É **imutabilidade de rascunho** aplicada a *qualquer* edição de item, mais o check do banco, mais ausência de comando.

### Existe conversão hoje?

**Não.** Nenhuma rota, serviço ou função troca o produto de um `OrderItem` em qualquer status. Incluir produto em COMMITMENT é erro explícito: *Linha COMMITMENT não aceita product_id — use line_kind=PRODUCT* (`commands.py` L143–146) — e isso só no DRAFT.

O adapter do Ordine **proíbe** o atalho silencioso: *I.V. 1 / I.V. 2 NUNCA viram SKU canônico silenciosamente* ([`ordine_heroes_v1.py`](../../../v2/app/ingestion/adapters/ordine_heroes_v1.py) L14–15).

### Auditoria

A infra **já carrega** quem / quando / ação / `details` ([`audit/public.py`](../../../v2/app/audit/public.py) `record_event`). Confirmação com compromisso grava JSON (`commitment_count`, ids, nota) em [`routes.py`](../../../v2/app/orders/routes.py) L440–456. `add_item` **não** grava de-para de produto. `update_item` grava só `item_id=…`.

Acrescentar um evento `bind_product` com `item_id`, `from=COMMITMENT`, `to=PRODUCT`, `product_id`, SKU antigo/novo, ator: **PEQUENO** (mesmo UoW; campo `details` já existe). Não precisa migração.

### O que quebra a jusante se a linha ganhar produto depois de confirmada

O id da linha **pode** permanecer. O que lê `product_id` / faturável:

| Dependência | Efeito |
|---|---|
| Faturar | `create_invoice` só pega linha com `product_id` ([`billing/commands.py`](../../../v2/app/billing/commands.py) L126–129). Match da Fattura igual ([`fattura_line_match.py`](../../../v2/app/ingestion/fattura_line_match.py) L170–178). **Hoje bloqueia o 589; depois da vinculação, destrava.** |
| Disponível | `billable = product_id is not None`; compromisso mostra disponível **—** ([`billing/queries.py`](../../../v2/app/billing/queries.py) L402–409). Passaria a ordered − emitida. |
| Item da fatura | Copia `product_id` **na criação** (`billing/commands.py` L136–137 e L248–249). Fatura já emitida **não** acompanha troca posterior. Guarda necessária: recusar vínculo se já houver item de fatura nessa linha. No 589: zero faturas — seguro. |
| Embarque | Usa `order_item_id` e quantidade do **pedido**, não o produto ([`logistics/commands.py`](../../../v2/app/logistics/commands.py) L366–376). Vínculo **não quebra** embarque existente. |
| Estoque / nacionalização | Precisa `product_id` de catálogo. Sem vínculo, elo 8 não anda. Com vínculo, o SKU passa a existir para receber. |
| Snapshots | `sku_snapshot` / `description_snapshot` na linha do pedido teriam de ser atualizados no mesmo passo (I.V. 2 → EAN do catálogo). |

### Estimativas

| Fatia | Faixa | Por quê |
|---|---|---|
| **1a** Vincular SKU na mão, pedido confirmado, confirmação explícita | **MÉDIO (3)** | Não é 1–2: precisa comando novo (exceção consciente ao rascunho), virar tipo+produto no mesmo flush por causa do check, guarda “sem fatura emitida nessa linha”, auditoria de-para, seletor+modal na comercial. Sem campanha de identidade. |
| **1b** Identidade automática I.V.* → EAN da Fattura | **GRANDE** | Namespaces diferentes por desenho. Ordine recusa auto-match. Fattura casa EAN. Não há tabela de identidade. Isso é campanha de catálogo, não um botão. |
| Caminho que a **tela promete** (produtos chegam na importação da Fattura) | **MÉDIO**, irmão da 1a | O aviso das faturas e o modal de confirmar dizem isso. O commit da Fattura **não** converte compromisso. Dá para fazer o vínculo no preview da Fattura (operador casa EAN ↔ linha I.V.*) com o mesmo esforço da 1a no pedido. Não é 1b. |

**A separação 1a/1b faz sentido no código.** Com 1a (no pedido **ou** na Fattura, operador escolhe o produto), o 589 **pode faturar sem 1b**, se o produto já existir no catálogo. A ordem da §0.4 muda: 1a sobe e deixa de ser GRANDE; 1b fica GRANDE e deixa de ser o primeiro obstáculo.

Não chamo 1a de PEQUENO: a guarda de rascunho + o check do banco + a tela que promete outro caminho pedem fatia própria, não um PATCH no item.

---

## 3. Hipótese 2 — logística 100%

**Confirmada a contradição.** O critério da §0.5 (“o quanto serve numa compra real”) **não** sustenta 100%. Não defendo o número; baixo o percentual. O critério permanece.

O que a logística entrega **sem digitação**:

- Importar packing list cria embarque **planejado vazio** (código gerado, nota, PDF opcional). Sem volumes, sem linhas, sem quantidade ([`dossier_commands.py`](../../../v2/app/ingestion/dossier_commands.py) `create_shipment` + link).
- `create_shipment` não puxa fatura nem pedido ([`logistics/commands.py`](../../../v2/app/logistics/commands.py) L208–235).
- Incluir linha exige `order_item_id` + quantidade na mão; residual = quantidade do **pedido**, não a faturada (L349–376).

Numa compra real o operador **redigita**. Capacidade manual do módulo existe (por isso não é 0%). **~50%.**

Aduana/estoque, mesmo exercício: Doganale do PDF cria processo **vazio**; ligar fatura/embarque é manual; nacionalização precisa de produto; numerário registra obrigação que o tesouro **recusa** pagar. Módulo isolado foi aceito. Compra real: **~65%** (antes ~80% — estava otimista no mesmo vício do 100%).

---

## 4. Hipótese 3 — elo de encerramento

**Confirmada a lacuna.** O modelo reserva `CLOSED` ([`orders/models.py`](../../../v2/app/orders/models.py) L20). O destino de produto lista *fechar ordem* / `close_order`. **Não há** comando, rota, tela, nem `close_order` na fachada. Cancelar CONFIRMED existe (motivo obrigatório). Decisão de fechamento ainda aberta no mapa de decisões.

Elo 10 acrescentado na §0.2 como **NÃO EXISTE**.

---

## 5. O que mudou no plano do advisor

- 1a não é PEQUENO; é **MÉDIO**. A tela promete o vínculo **na Fattura**, não no pedido — os dois sítios são equivalentes em esforço; o da Fattura é o que o operador já lê.
- 1b continua GRANDE e **não** é pré-requisito do 589 se 1a existir.
- Logística 100% era leitura por módulo; corrigido para ~50% sem mudar o critério.
- Aduana/estoque ~80% → ~65% pelo mesmo critério.
- Encerramento entra como elo 10, não como módulo extra.

---

## 6. Próxima etapa lógica (opinião)

A próxima ação **autorizada** no §1 continua a fatia de reais verdadeiros + cronograma. **Não alterei isso.**

Se o critério for “o 589 andar mais um elo”, eu **priorizaria 1a** (vínculo manual com confirmação — no pedido ou na Fattura) **antes** dessa fatia financeira: sem SKU o 589 não fatura, e somar câmbio não destrava faturar. Se o critério for “não abrir campanha nova e fechar o ciclo financeiro já em voo em pedidos com produto”, a fatia financeira autorizada é a certa.

Recomendação: autorizar **1a isolada** (MÉDIO) como exceção consciente; **não** abrir identidade automática nem reconciliação larga.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (§0.2 elo 10, §0.4 item 1, §0.5 barras); este diretório
- Evidence: docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/
- Roadmap status: 0.5.106 — §0 ajustada pela investigação; próxima ação inalterada
- Next TODO: FIN-4 quando autorizado (inalterado)
- Return to advisor: docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/COMPROMISSO_SKU_ADVISOR_HANDOFF.md
```
