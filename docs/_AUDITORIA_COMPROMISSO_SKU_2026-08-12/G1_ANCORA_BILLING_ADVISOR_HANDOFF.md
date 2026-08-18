# G1 — Âncora de produto para faturar o compromisso

| Campo | Valor |
|---|---|
| Etapa | **G1 Planning** — âncora de billing para linha de compromisso |
| Status | **PLANNING** — sem código de produto |
| Data | **2026-08-12** |
| Portão | **Parar aqui.** Execução só após o advisor aprovar este G1 |
| Negócio | Ricardo: GRAFICATE / NON GRAFICATE são **categorias**, não SKU final; a Fattura traz a **mesma linha genérica**; split modelo/cor/tamanho é **estoque, depois da nacionalização** |
| Restrição | Linha de compromisso do Ordine **nunca** vira SKU canônico em silêncio; vínculo só com confirmação explícita |

Não reabri o 589 nesta fatia: o percurso de tela de 0.5.106 permanece válido (faixa somente leitura; aviso de Fattura; disponível —).

---

## 0. O que o código exige hoje

O faturamento **não** fatura compromisso:

- `create_invoice` só copia linhas com `product_id` ([`billing/commands.py`](../../../v2/app/billing/commands.py) L126–129).
- `replace_items` recusa `product_id is None` (L221–224).
- Item da fatura tem `product_id` **NOT NULL** ([`billing/models.py`](../../../v2/app/billing/models.py) L101).
- Match da Fattura só considera linhas com produto; casa `product_id` ou `sku_snapshot == SKU do PDF` ([`fattura_line_match.py`](../../../v2/app/ingestion/fattura_line_match.py) L170–178, L229–235).
- Disponível: compromisso → **—** ([`billing/queries.py`](../../../v2/app/billing/queries.py) L402–409).

O estoque **também** exige produto de catálogo na entrada:

- Linha de recebimento `product_id` **NOT NULL** ([`inventory/models.py`](../../../v2/app/inventory/models.py) L116–118).
- `add` de linha: `product_id obrigatório` ([`inventory/commands.py`](../../../v2/app/inventory/commands.py) L206–208).
- Movimento e saldo idem (L150–152).
- Reclassificação atual = **mesmo produto**, troca de local (entreposto → doméstico), L307–332. **Não** parte uma categoria em N modelos.

Nacionalização aceita `product_id` nulo no item ([`customs/models.py`](../../../v2/app/customs/models.py) ~599); o recebimento depois **não**.

Catálogo: `Product` é só `sku` + `description` + `is_active` ([`catalog/models.py`](../../../v2/app/catalog/models.py) L25–35). Sem tipo “categoria”. Criar produto já existe (`POST /api/products`, [`catalog/commands.py`](../../../v2/app/catalog/commands.py) L44–64) e a tela de **novo pedido** já cria SKU na hora ([`OrderCreatePage.tsx`](../../../v2/frontend/src/features/orders/OrderCreatePage.tsx) L125–128).

---

## 1. Caminho A — produto genérico de catálogo

O operador confirma um produto-categoria (“racchette 2027 GRAFICATE”) e a linha de compromisso vira linha de produto (tipo + `product_id` no mesmo passo, por causa do check em [`orders/models.py`](../../../v2/app/orders/models.py) L66–69). O código I.V.* **permanece** em `external_code`.

### O que funciona

- Billing passa a ver a linha. Sem migração de fatura.
- Estoque consegue **receber posição** nesse produto: a arquitetura pede *um* `product_id`, não um EAN. Categoria serve de âncora até o split futuro.
- Criar o produto **antes** ou **no mesmo fluxo** (inline): a API já cria; o novo pedido já faz inline. No confirmado, o bind é que falta — não o catálogo.
- Não viola a restrição se a confirmação for explícita e **não** houver auto-resolve I.V. → EAN. Categoria ≠ SKU canônico inventado em silêncio.

### O que quebra / o que não existe

- **Match da Fattura:** se o snapshot da linha virar o SKU de catálogo (`CAT-…`) e o PDF continuar com `I.V. 2`, o match atual **falha** (compara `sku_snapshot`). Obrigatório casar também `external_code` (e, se o Ricardo confirmar, a descrição). Sem isso o A não fatura o 589 mesmo depois do vínculo.
- **Split no estoque:** não existe. Reclass só muda local do mesmo produto. Partir 14.600 GRAFICATE em modelos é campanha futura de inventário — o G1 não finge que isso já está pronto.
- **Catálogo “poluído”:** dois produtos-categoria no 589. Sem flag de tipo, eles **parecem** SKU normal na posição. Mitigação sem migração: código que **não** é I.V.* nem EAN (ex. categoria visível na descrição). Flag `categoria` no catálogo seria fatia extra — não é necessária para faturar.

### Custo

**MÉDIO (3–4 fatias).** Sem migração de schema para o bind (021 já permite compromisso sem produto e produto com produto). OpenAPI só se nascer rota nova de bind. Companion PEQUENO: match por `external_code`.

Não é PEQUENO: exceção consciente ao rascunho + virar tipo e produto juntos + guarda de fatura emitida + modal + auditoria.

---

## 2. Caminho B — billing sem `product_id`

Compromisso atravessa a fatura com I.V.* como chave; `create_invoice` / match deixam de exigir produto.

### O que funciona no papel

- Casa naturalmente com “a Fattura traz a mesma linha genérica”.
- Não cria linha no catálogo.

### O que quebra

| Ponto | Efeito |
|---|---|
| `invoice_items.product_id` NOT NULL | **Migração** obrigatória. Contrato OpenAPI muda. |
| `create_invoice` / `replace_items` | Reescrever a regra “nunca inventar Product” que hoje *também* recusa compromisso. |
| Disponível | Hoje compromisso = não faturável. Teria de passar a ordered − emitida sem produto. |
| Match | Incluir compromisso e casar `external_code`. PEQUENO se fosse só isso. |
| Nacionalização | Item pode nascer sem produto. |
| **Recebimento / movimento / saldo** | Continuam NOT NULL. O 589 **para de novo** na porta do estoque. O B empurra o problema; não o resolve. |
| Split futuro | Continua inexistente — e ainda sem âncora de catálogo para o saldo genérico. |

### Custo

**GRANDE** se for “a cadeia até o estoque”: billing + migração + OpenAPI + testes + **ainda** precisa de produto na entrada do estoque (ou seja, o A de qualquer forma).  
**MÉDIO** se alguém aceitar faturar para sempre sem estoque — isso contradiz o destino da raquete.

---

## 3. Recomendação

**Caminho A**, com dois acompanhamentos obrigatórios nesta campanha (não depois):

1. Preservar `external_code` (I.V.*) no bind.
2. Match da Fattura por `external_code` (e produto, se houver), porque a Fattura **não** quebra em EAN.

**Não** usar I.V.* como SKU de catálogo — isso *seria* canonizar o código do fornecedor. SKU de categoria distinto; I.V.* fica no código externo da linha.

**Não** caminho B: paga migração no billing e esbarra no `product_id` obrigatório do recebimento. O estoque não opera sem âncora; o A é essa âncora, honesta (categoria, não modelo).

Terceiro caminho (“só na Fattura criar o produto e converter”) **não é terceiro modelo** — é o A no sítio que a tela já anuncia. Escolha de UX, não de domínio. Prefiro o preview da Fattura *ou* a comercial do pedido; os dois são o mesmo comando. Pergunta ao Ricardo abaixo.

Isto **não** é identidade automática I.V. → EAN (1b). O N:1 de EAN contra a categoria **não entra no billing**, como o Ricardo disse; entra no split de estoque, fora desta fatia.

---

## 4. O texto da tela de faturas

Literal atual:

> Este pedido só tem linhas de compromisso (artigos ainda sem SKU final). As faturas destes itens entram pela importação da Fattura do fornecedor — os produtos reais chegam por ali. Não é possível criar fatura manual aqui.

No A, **essa frase é falsa em duas pontas**: os “produtos reais” (modelo/cor) **não** chegam na Fattura; e a Fattura **não** converte compromisso sozinha.

Reescrever, no mesmo tom, para algo como:

> Este pedido tem linhas de categoria (compromisso), ainda sem produto de catálogo. Vincule a categoria com confirmação para faturar. A Fattura traz a mesma linha genérica — não o modelo/cor/tamanho. Isso entra no estoque depois da nacionalização. Sem vínculo, não é possível criar fatura manual.

A frase só vira verdade se o G1 colocar o vínculo **no commit da Fattura** com confirmação no preview. Aí o texto vira: a importação da Fattura, com o operador confirmando a categoria, é o momento do vínculo. Continua **sem** prometer EAN.

---

## 5. Guardas (qualquer caminho)

1. Recusar bind se a linha já tiver item de fatura **emitida** (qty ISSUED > 0 ou InvoiceItem dessa `order_item_id` em fatura ISSUED).
2. Confirmação explícita do operador (modal: de compromisso / I.V.* / descrição → produto SKU / descrição). Sem auto-resolve.
3. Auditoria na mesma UoW: ator, quando, `item_id`, de (`COMMITMENT`, `external_code`, `product_id=null`) para (`PRODUCT`, `product_id`, SKU). Infra `record_event.details` já existe ([`audit/public.py`](../../../v2/app/audit/public.py)).
4. Não reescrever quantidade nem preço no bind.
5. Pedido só **CONFIRMED** (não cancelado).

---

## 6. Perguntas para o Ricardo (o código não decide)

1. O SKU da categoria pode ser sugerido (ex. texto da descrição, **nunca** I.V.*) ou o operador digita sempre?
2. O vínculo acontece na **comercial do pedido**, no **preview da Fattura**, ou nos dois?
3. Até o split de estoque existir, é aceitável a posição mostrar “14.600 racchette 2027 GRAFICATE” como um único produto?
4. As duas categorias do 589 nascem na hora do vínculo ou ele já as cadastra no catálogo antes?

Não decido estas quatro.

---

## 7. Checkpoints (só depois do G1 aprovado)

| ID | O quê | Migração? |
|---|---|---|
| **G1** | Este plano | Não |
| **G2** | Comando `bind_commitment_product` (CONFIRMED; vira tipo+produto; preserva I.V.*; guardas §5; auditoria) + rota | **Não** (schema 021 basta) |
| **G3** | UI: seletor + criar categoria inline (`catalog:write`) + modal de confirmação | Não |
| **G4** | Match da Fattura por `external_code`; reescrever o aviso das faturas | Não |
| **G5** | Testes + percurso no 589 **quando autorizado** (uso 589 continua não-gate até lá) | Não |

Fora: split de estoque; identidade I.V.→EAN; FIN-4; 3A/020.

OpenAPI: só se G2 expuser rota nova — regenerar client na mesma fatia, sem drift.

---

## 8. Tela

Não reandada. Evidência vigente: [`COMPROMISSO_SKU_ADVISOR_HANDOFF.md`](COMPROMISSO_SKU_ADVISOR_HANDOFF.md) §1. Asset naquela passagem: `index-B-ChOX1L.js`.

---

## Recomendação ao advisor

Aprovar G1 no **caminho A** (categoria no catálogo + bind explícito + match por I.V.*). Rejeitar B. Não executar G2 até o sinal. Próxima ação canônica do Roadmap **permanece** a fatia financeira já autorizada, até o advisor dizer o contrário.
