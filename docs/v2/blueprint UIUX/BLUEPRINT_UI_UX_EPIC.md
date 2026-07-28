# Epic Controle — Blueprint de Produto (UI/UX)

> Documento de produto. Define a arquitetura de informação, as seções da interface e o comportamento de cada tela. É o padrão que qualquer implementação segue e o critério pelo qual entregas são aprovadas ou recusadas.
>
> **Versão** 2.0 · **Data** 2026-07-27

---

## Fundamentos

**Produto.** Plataforma de controle de importação para operação de varejo esportivo. Cobre o ciclo do produto: cadastro, pedido ao fornecedor, faturamento, pagamento multimoeda, embarque, desembaraço, entrada em estoque e custo final por SKU.

**Diretriz visual.** Interface clara. Escala tipográfica definida, densidade de dados alta, hierarquia por peso e espaçamento.

**Regra de nomenclatura.** Nenhuma tela pode ser confundida com outra pelo nome. Onde duas telas tratam do mesmo objeto em estados diferentes, o nome carrega o **estado**, não o objeto — "A pagar" e "Liquidados", nunca "Faturas" e "Pagamentos".

**Regra de estrutura.** Uma tela existe se responde a uma pergunta que nenhuma outra responde. Documento pertence ao objeto que o originou, não a uma tela de documentos.

**Modelo mental.** Duas organizações coexistem:
- **Por objeto** — a ficha do pedido e a ficha do produto reúnem tudo sobre um item específico.
- **Por fila de trabalho** — listas do que precisa de ação, atravessando todos os objetos.

Fichas são ricas. Filas são poucas e enxutas.

---

## As sete seções

| # | Seção | Pergunta | Dono |
|---|---|---|---|
| 1 | **Painel** | O que preciso decidir hoje? | Executivo |
| 2 | **Produtos** | O que vendemos e o que sabemos sobre cada item? | Comercial / Comprador |
| 3 | **Pedidos** | O que compramos e em que pé está? | Comprador |
| 4 | **Financeiro** | Quanto devemos e quanto já saiu? | Financeiro |
| 5 | **Abastecimento** | O que tenho, o que chega, o que virá? | Executivo / Comercial |
| 6 | **Custos** | Quanto custou de verdade e o que trava o fechamento? | Financeiro / Gestor |
| 7 | **Administração** | Quem acessa o quê e o que aconteceu? | Admin |

Dezoito telas no total. Cada uma justificada abaixo.

---

## 1 · Painel

Tela única. Não é dashboard de gráficos — é a fila de decisões do dia.

**1.1 Painel.** Três blocos: indicadores de exposição (a pagar, em trânsito, resultado de câmbio); fila de pendências que exigem ação humana, vindas de todas as seções, cada uma com link direto ao ponto de resolução; e calendário dos próximos trinta dias com vencimentos e chegadas previstas.

---

## 2 · Produtos

O cadastro é a fundação da operação. Um SKU incompleto trava desembaraço, impede rateio de frete e corrompe o custo. Esta seção existe para que isso não aconteça em silêncio.

**2.1 Catálogo.** Lista de SKUs com hierarquia comercial: categoria → marca → linha → modelo → SKU. Filtros por categoria, marca, fornecedor, status e completude. Cada linha mostra código, descrição, estoque atual e um indicador de completude do cadastro. Produtos incompletos aparecem sinalizados, não escondidos.

**2.2 Ficha do produto.** O registro completo de um SKU, organizado por quem consome cada informação:

| Bloco | Campos | Quem depende |
|---|---|---|
| **Identificação** | Código interno, código do fornecedor, EAN/GTIN, descrição curta e completa | Todos |
| **Comercial** | Categoria, marca, linha, modelo, temporada, atributos de variante (tamanho, cor, peso, empunhadura) | Comercial |
| **Fiscal** | NCM, país de origem, regime tributário, alíquotas aplicáveis | Aduana — sem NCM não nacionaliza |
| **Logístico** | Peso líquido e bruto, dimensões, cubagem, unidades por caixa | Rateio de frete e seguro |
| **Estoque** | Unidade de medida, estoque mínimo, local padrão | Abastecimento |
| **Histórico** | Preços de compra praticados, custo final por importação, versões do cadastro | Custos |

A ficha exibe **o que falta e o que isso bloqueia** — "sem NCM: não pode ser nacionalizado", "sem peso: não entra no rateio de frete". O usuário vê a consequência, não apenas o campo vazio.

**2.3 Triagem de produtos.** Quando um documento do fornecedor chega com códigos de produto, o sistema propõe correspondências com o catálogo. **Toda correspondência exige confirmação explícita do operador** — inclusive as de alta confiança. Nenhum produto é vinculado ou criado automaticamente. Três saídas por linha: vincular ao SKU existente, criar SKU novo, ou rejeitar. Esta regra é absoluta: correspondência automática silenciosa foi a origem dos problemas de qualidade de dado da versão anterior.

**2.4 Fornecedores.** Cadastro de fornecedores com dados comerciais, condições de pagamento padrão, moeda e documentos.

---

## 3 · Pedidos

O pedido é a espinha do sistema. Tudo — fatura, pagamento, embarque, desembaraço, custo — pendura nele.

**3.1 Pedidos.** Fila de ordens de compra com filtro por status, fornecedor e período. Colunas: código, fornecedor, status, valor, próximo evento (o que acontece a seguir e quando), atualização. Cabeçalho fixo, ação por linha.

**3.2 Ficha do pedido.** Reúne o ciclo inteiro de um pedido em abas. É onde o comprador e o gestor trabalham:

| Aba | Conteúdo |
|---|---|
| **Resumo** | Situação em uma tela: pedido, faturado, pago, embarcado, nacionalizado, custo estimado. Alertas do que trava o avanço. |
| **Itens** | SKUs, quantidades, preços, e o rastreio por etapa — pedido / faturado / embarcado / nacionalizado / recebido, com as diferenças explícitas. |
| **Faturas** | As faturas que cobrem este pedido, com vencimentos e adiantamentos. |
| **Embarque** | Os embarques deste pedido: modal, status, datas, itens embarcados. |
| **Desembaraço** | Processo aduaneiro, impostos, nacionalização parcial e residual. |
| **Custo** | Composição do custo final deste pedido por SKU. |
| **Documentos** | Todos os arquivos deste pedido — do documento original do fornecedor ao comprovante de pagamento — com versionamento. O documento vive aqui, no objeto a que pertence. |

**3.3 Novo pedido.** Criação com adição sequencial de itens otimizada para teclado. Busca de SKU por código, descrição ou código do fornecedor. Produto não encontrado abre criação sem sair do fluxo. Prévia de total antes de confirmar.

---

## 4 · Financeiro

Nomes por estado da obrigação. Sem ambiguidade entre telas.

**4.1 A pagar.** As obrigações em aberto: vencimento, fornecedor, fatura de origem, saldo, moeda, situação do câmbio. Indicadores de vencido / vence hoje / total em aberto. Clicar abre painel lateral com a fatura, os pagamentos parciais e o saldo. **É daqui que se registra pagamento** — com fornecedor, fatura e saldo já preenchidos e prévia do efeito antes de confirmar. Nunca de memória.

**4.2 Liquidados.** O que já foi pago: data, valor, moeda, taxa aplicada, a qual obrigação foi alocado e o comprovante. É o arquivo do que saiu, separado sem ambiguidade do que ainda deve.

**4.3 Faturas.** Os documentos que o fornecedor emitiu, com itens, condições de pagamento e adiantamentos. Uma fatura pode cobrir mais de um pedido e gerar várias obrigações — por isso existe como lista própria, não apenas dentro do pedido. É a origem auditável de tudo em "A pagar".

**4.4 Câmbio.** As três visões que a operação exige — planejado, cotado, executado — com exposição em reais e resultado de cada movimento. Toda cotação carrega data e hora de obtenção.

**4.5 Créditos e descontos.** Adiantamentos, créditos e descontos disponíveis e sua aplicação. Mantidos distintos entre si: crédito não é desconto, e nenhum dos dois é conta-corrente.

---

## 5 · Abastecimento

A seção que o executivo e o comercial abrem primeiro. Aqui o embarque e o desembaraço aparecem como **estágios de um pipeline**, não como telas separadas — o operador de logística e o despachante trabalham na fila desta seção e no detalhe dentro da ficha do pedido.

**5.1 Posição.** A tela central da operação comercial. Por SKU, em três tempos:

```
PRODUTO              EM ESTOQUE    EM TRÂNSITO           PLANEJADO
                     disponível    importação em curso   pedido / previsto
──────────────────────────────────────────────────────────────────────────
Raquete Pro X 300g      120        + 300  chega 15/ago   + 500  Q1 2027
Raquete Air G3           45        —                     + 200  Q1 2027
Grip Series Preto         0 ⚠      + 150  chega 02/set   + 400  Q2 2027
──────────────────────────────────────────────────────────────────────────
```

Cada número navega para sua origem: estoque abre os movimentos, trânsito abre o embarque, planejado abre o pedido. Filtro por categoria, marca e horizonte. É a tela que responde "posso vender isso?" sem abrir mais nada.

**5.2 Em trânsito.** O pipeline de importação em fila única, com o estágio de cada embarque: embarcado → em trânsito → chegada → desembaraço → nacionalizado → em estoque. Colunas de modal, data prevista, atraso e o que trava. Logística e despachante operam daqui; o detalhe abre na ficha do pedido. Substitui as antigas telas separadas de embarques e processo aduaneiro.

**5.3 Movimentos de estoque.** O extrato: entradas, saídas, transferências, entreposto. Saldo sempre derivado dos movimentos, nunca editável à mão. Filtro por SKU, tipo e período.

**5.4 Cobertura.** Leitura de gestão sobre a Posição: dias de estoque por SKU considerando consumo, ruptura projetada, excesso parado. Ordenado por urgência. É a tela que dispara a decisão de comprar.

---

## 6 · Custos

**6.1 Custo por produto.** Landed cost por SKU com as três versões — estimado, revisado, realizado — lado a lado. Composição aberta: produto, frete, seguro, impostos, despesas locais, despachante, câmbio. Rateio explícito com a base usada (valor, peso, volume ou quantidade). Versão nova nunca apaga a anterior.

**6.2 Despesas.** As despesas de importação que compõem o custo, cada uma com documento comprobatório e vínculo ao pedido ou processo. Sem documento, não compõe custo publicado.

**6.3 Fechamento.** As divergências que travam o encerramento de um período: quantidade que não confere, valor que diverge, pagamento sem correspondência. Cada divergência é resolvida com justificativa registrada ou permanece bloqueando. Nada desaparece sem trilha. Concluída a resolução, o período fecha com snapshot; reabertura exige permissão e motivo.

---

## 7 · Administração

**7.1 Usuários e permissões.** Usuários, papéis e o que cada papel acessa. Menu e telas se adaptam à permissão.

**7.2 Auditoria.** Registro imutável de toda ação relevante, consultável por entidade e por autor. Somente leitura.

---

## Mapa de navegação

```
EPIC CONTROLE

  Painel

  Produtos
    Catálogo · Triagem · Fornecedores

  Pedidos
    Pedidos · Novo pedido

  Financeiro
    A pagar · Liquidados · Faturas · Câmbio · Créditos e descontos

  Abastecimento
    Posição · Em trânsito · Movimentos · Cobertura

  Custos
    Custo por produto · Despesas · Fechamento

  Administração
    Usuários · Auditoria
```

Duas fichas não aparecem no menu porque se alcança por objeto, não por navegação: a **ficha do produto** (a partir do Catálogo, da Posição ou de um item de pedido) e a **ficha do pedido** (a partir de Pedidos, de uma obrigação, de um embarque ou de um custo). São os dois pontos de convergência do sistema.

---

## Padrões de tela

**Consistência.** A mesma entidade se apresenta igual em qualquer tela.

**Contexto preservado.** Navegar e voltar mantém filtro, linha e posição de rolagem.

**Hierarquia.** O necessário para decidir vem primeiro; códigos internos ficam discretos.

**Vazio não é zero.** Campo sem dado mostra traço ou "pendente".

**Consequência visível.** Onde falta dado, a tela diz o que isso bloqueia.

**Confirmação explícita.** Vínculo de produto, pagamento, alocação, câmbio e nacionalização exibem o efeito e exigem confirmação. Nenhuma correspondência automática silenciosa.

**Filas idênticas.** Toda lista operacional tem a mesma anatomia: indicadores no topo, filtros com memória, cabeçalho fixo, ação por linha, painel lateral para detalhe.

**Documento no objeto.** Arquivo pertence ao pedido, à fatura ou ao produto que o originou.

---

## Como este documento é usado

- **Aprovar entrega.** Comparar com a seção correspondente e com os padrões. Viola um padrão, volta.
- **Prioridade.** Ordem de construção é decisão de produto, registrada no roadmap. Este documento define o destino.
- **Crescer.** Telas futuras entram nas seções já nomeadas. O mapa não se redesenha.
