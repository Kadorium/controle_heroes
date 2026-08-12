# Layout por tela

Data: 2026-08-04.

## Páginas de listagem

| Tela | Título (posição) | Ação primária | FilterBar | Paginação |
|---|---|---|---|---|
| OrdersListPage | `PageHeader` esquerda | "Novo pedido" — topo direito (`PageHeader.actions`) | Sim (chips) | `PaginationSummary` (texto), sem controle de próxima página |
| InvoicesListPage | idem | **Nenhuma** (fatura só se cria a partir do pedido) | Sim (chips) | idem |
| PayablesListPage (fallback) | idem | Nenhuma | **Não** — sem filtros | Nenhuma (nem resumo) |
| ApQueuePage | idem | "Atualizar" (secundário, topo direito) | Sim (chips + campos `FormField` em "secondary") | `PaginationSummary` com `total` real, sem controle de próxima página |
| PaymentsListPage | idem | "Novo pagamento" — topo direito | Sim (chips) | idem |
| ShipmentsListPage | idem | "Prestadores" (secundário) + "Novo embarque" (primário) — topo direito | Sim (chips + 2 `SelectField` sem `FormField`) | idem |
| CustomsListPage | idem | "Novo processo" — topo direito (`<Link className="btn btn-primary">`) | Sim, mas em modo legado (`<FilterBar>{children}</FilterBar>`, só chips, sem primary/secondary) | idem |
| MovementsPage | idem | Nenhuma (ledger somente leitura) | **Não usa o componente `FilterBar`** — usa um `SectionCard` "Filtros" próprio com botão "Filtrar" explícito | idem |
| LogisticsProvidersPage | idem | "Voltar aos embarques" (não é bem uma ação primária de lista — é navegação) | Não (não tem filtro) | Nenhuma |

### Achado: título sempre à esquerda, ação primária sempre no topo direito

Confirmado como **padrão consistente** em todas as 9 telas de listagem — via o componente `PageHeader`, que usa `justify-content: space-between` (`index.css:596-602`). Não há nenhuma tela com botão de ação primária acima da tabela (fora do cabeçalho) ou à esquerda. Isso é um ponto positivo — não é reportado como inconsistência.

### Achado: dois modelos de filtro diferentes coexistem

`FilterBar` (chips clicáveis, aplicação instantânea via `onClick` → atualiza a URL) é o padrão em 6 das 9 listagens. `MovementsPage` usa um modelo completamente diferente: campo de texto + botão "Filtrar" que precisa ser clicado para aplicar (`MovementsPage.tsx:88-100`) — o único ponto do app onde filtrar exige uma ação de submit explícita em vez de resposta imediata ao clique/seleção. Um usuário que aprendeu o padrão de clique-instantâneo nas outras 6 telas pode digitar um ID em "Filtrar" no Movimentos e não perceber que precisa clicar em "Filtrar" para a busca surtir efeito.

### Achado crítico: não existe controle de paginação em nenhuma lista do app

`PaginationSummary` (`PaginationSummary.tsx`) é **só texto** ("Exibindo 1–50 de 340", por exemplo) — não há nenhum botão "Próxima página"/"Anterior", nem seletor de tamanho de página, em nenhuma das 9 telas de listagem revisadas. Combinado com limites fixos de 50–100 registros por chamada (`limit: 50` em Orders/Invoices/Shipments/Payments, `limit: 100` em Payables básico/Movimentos), **qualquer lista com mais registros do que o limite simplesmente não pode ser vista além do primeiro lote pela interface** — o único jeito de "ver mais" é estreitar os filtros até a contagem cair abaixo do limite. Em `ApQueuePage`/`CustomsListPage`, que exibem `total` real vindo da API, ao menos o usuário sabe que há mais registros (o texto diz "de 340", por exemplo); nas demais listagens (`loadedCount` sem `total`), nem essa pista existe — a lista parece completa mesmo quando está truncada.

## Páginas de formulário / criação

| Tela | Layout | Botão(ões) de ação principal | "Cancelar/Voltar" |
|---|---|---|---|
| OrderCreatePage | Coluna única com `SectionCard`s empilhados, campos em `.form-grid` responsivo (`auto-fill, minmax(14rem,1fr)`) | "Salvar rascunho" (secundário) + "Salvar e confirmar" (primário) — **rodapé da página**, depois da seção Itens | "Voltar à fila" — link secundário no topo direito (`PageHeader.actions`) |
| ShipmentCreatePage | idem | "Criar embarque" (primário) — rodapé | "Voltar à fila" — topo direito |
| PaymentCreatePage | idem | "Registrar" (primário, dentro do `<form>`) — rodapé do `SectionCard` | "Voltar" — topo direito (nota: label diferente das outras telas, ver abaixo) |
| CustomsCreatePage | Coluna única, um `SectionCard` | "Criar" (primário) — **ao lado de** "Cancelar" na mesma linha (`div.form-actions`) | "Cancelar" — **rodapé, ao lado do botão de salvar**, não no topo |
| LogisticsProvidersPage | Formulário de cadastro + tabela de cadastrados na mesma página | "Cadastrar" — rodapé do `SectionCard` | "Voltar aos embarques" — topo direito |

### Achado: posição do "cancelar/voltar" não é consistente

Em 4 das 5 telas de criação, o link para desistir/voltar fica **no topo direito**, junto com o `PageHeader` (padrão "breadcrumb mental": vim de uma fila, saio pela mesma região visual por onde entrei). `CustomsCreatePage` é a única exceção: o link "Cancelar" fica **no rodapé, ao lado do botão "Criar"** (`CustomsCreatePage.tsx:74-81`), como se fossem um par de ações de formulário — modelo diferente das outras 4 telas. Um usuário que aprendeu "para desistir, olho no topo direito" não vai encontrar essa opção no topo da tela de novo processo aduaneiro.

### Achado: rótulo do link de saída/cancelamento diverge entre 4 variações para o mesmo conceito

| Rótulo | Onde |
|---|---|
| "Voltar à fila" | `OrderCreatePage`, `OrderDetailPage`, `InvoiceDetailPage`, `ShipmentCreatePage`, `ShipmentDetailPage`, `PaymentDetailPage`, `PayableFxPage` |
| "Voltar" | `PaymentCreatePage` (única tela com este rótulo mais curto) |
| "Voltar aos embarques" | `LogisticsProvidersPage` (única tela com rótulo nomeando o destino em vez do gênero "fila") |
| "Cancelar" | `CustomsCreatePage` (única tela que trata o link de saída como "Cancelar" em vez de "Voltar") |

São 4 rótulos distintos para a mesma ação funcional (sair sem salvar / voltar à listagem anterior). Não chega a ser um bug, mas é ruído terminológico perceptível para quem navega entre módulos.

## Páginas de detalhe/edição

| Tela | Layout | Ações principais (posição) |
|---|---|---|
| OrderCockpitPage | Coluna única, `.cockpit-grid` (grid responsivo `auto-fit, minmax(260px,1fr)`) para as 3 seções (Faturamento/Tesouraria/Auditoria) | "Abrir comercial" — topo direito |
| OrderDetailPage | Coluna única, `SectionCard`s empilhados | Confirmar/Cancelar — topo direito (`PageHeader.actions`); "Atualizar" — **solto no rodapé da página, fora de qualquer `SectionCard`** |
| InvoiceDetailPage | idem | Cancelar rascunho — topo direito; Emitir — bloco próprio (`.stack-row.page-actions`) antes dos modais, no meio do fluxo da página, não no topo nem fixo no rodapé |
| ShipmentDetailPage | idem | Avançar/Anular/Excluir — topo direito; "Salvar resumo" — dentro do `SectionCard` "Resumo" |
| PaymentDetailPage | idem | Cancelar pagamento — topo direito; "Alocar" — dentro do `SectionCard` "Obrigações elegíveis" |
| CustomsDetailPage | Coluna única, sem `PageHeader.actions` (todas as ações ficam dentro dos próprios `SectionCard`s, inclusive Submeter/Cancelar processo) | Nenhuma ação no topo — diverge das outras 4 telas de detalhe, que sempre têm ao menos uma ação de topo |

### Achado: nenhuma tela usa layout de duas colunas ou sidebar de resumo

Todas as telas de detalhe/edição são de **coluna única com seções empilhadas verticalmente** (`SectionCard` após `SectionCard`). Não existe em nenhuma tela um painel lateral fixo de resumo/KPIs enquanto o usuário rola o conteúdo principal — os KPIs (`KpiStrip`, `SummaryGrid`) aparecem inline, no topo do fluxo, e somem de vista ao rolar para baixo em páginas longas (ex.: `ShipmentDetailPage`, que chega a ter 6+ `SectionCard`s). Isso não é uma inconsistência entre telas (é consistente em 100% delas), mas é uma limitação estrutural do layout: em telas longas, o usuário perde a visão do status/KPI ao editar itens mais abaixo na página.

### Achado: posição da ação de "salvar/confirmar" varia dentro da própria tela de detalhe

`OrderDetailPage` e `InvoiceDetailPage` colocam a ação de escrita mais crítica (Confirmar / Emitir) em posições diferentes relativas ao fluxo da página: `OrderDetailPage` tem "Confirmar" no topo (`PageHeader.actions`), mas o botão de salvar cabeçalho ("Salvar cabeçalho") fica dentro do próprio `SectionCard` "Cabeçalho"; já em `InvoiceDetailPage`, "Emitir" (ação equivalente a "Confirmar") **não** está no topo — está numa `div.page-actions` separada, logo depois da seção "Obrigações", ou seja, em posição de rolagem diferente conforme quantidade de itens/parcelas da fatura. `CustomsDetailPage` não tem nenhuma ação no topo — "Submeter"/"Cancelar processo" ficam dentro do primeiro `SectionCard` ("Resumo"). Resultado prático: a ação mais importante de cada tela ("tornar isto oficial/irreversível") não está sempre no mesmo lugar relativo ao layout, ao contrário do padrão consistente das listagens.

## Drawer lateral (`DetailDrawer`)

- Largura única e tokenizada: `--detail-drawer-width: 460px` (`index.css:47`) — consistente onde é usado.
- Estrutura sempre título + botão "Fechar" (`drawer-header`) + corpo — garantida pelo próprio componente `DetailDrawer.tsx`, não pode divergir entre usos.
- **Uso real no app: só `ApQueuePage`** (drawer com detalhe da obrigação ao clicar numa linha). Nenhuma outra listagem usa drawer — todas as outras (`OrdersListPage`, `InvoicesListPage`, `ShipmentsListPage`, `PaymentsListPage`) navegam para uma **página inteira** ao clicar numa linha.

### Achado: duas metáforas diferentes para "ver detalhe de uma linha da fila"

Clicar numa linha de pedido leva a uma página nova (`/orders/:id`, cockpit inteiro). Clicar numa linha de obrigação em `/payables` abre um drawer lateral sem sair da lista. Não há uma razão de produto documentada no código para essa diferença (não é sobre volume de dados — o drawer de `ApQueuePage` já mostra bastante informação via `SummaryGrid` com 11 itens). Um usuário que aprendeu "clicar na linha = nova página" em Pedidos vai se surpreender com o comportamento de painel deslizante em Contas a pagar, e vice-versa.

## Modal de confirmação (`ConfirmationModal`)

- Estrutura sempre igual (garantida pelo componente): título + `<header>` com botão ghost de fechar (rotulado com `cancelLabel`) + corpo + rodapé com botão secundário (`cancelLabel`) e botão primário (`confirmLabel`), nessa ordem esquerda→direita.
- Largura fixa `min(420px, 100%)` — mas definida via `style` inline no próprio componente (`ConfirmationModal.tsx:35-41`), não via token CSS — funcionalmente idêntica em todos os usos porque é um único componente, mas arquiteturalmente destoa do resto do design system (que usa `var(--...)` para tudo) por estar embutida como estilo inline.
- **Não há inversão de ordem Cancelar/Confirmar entre telas** — como é um único componente reutilizado (11 usos: pedido, fatura×2, pagamento×2, embarque×2, picker de item), a ordem é estruturalmente garantida e não pode divergir. Este é um ponto positivo, não uma inconsistência.
- Nota: o modal tem **dois controles que cancelam a mesma ação** — o botão ghost no cabeçalho (rotulado com `cancelLabel`, ex. "Cancelar", mas com `aria-label="Fechar"`) e o botão secundário no rodapé (mesmo `cancelLabel`). Funcionalmente redundante, mas não é uma inconsistência *entre* telas — é assim em todo lugar.

## Outras divergências de terminologia encontradas

- **"Prestador logístico" vs. "Empresa transportadora"**: `LogisticsProvidersPage` trata a entidade pelo nome genérico correto — "Prestadores logísticos: transportadoras, armadores, agentes e operadores" (a entidade tem 4 subtipos, via `PROVIDER_TYPE_OPTIONS`). Porém, o campo de seleção do mesmo prestador em `ShipmentCreatePage`/`ShipmentDetailPage` é rotulado como **"Empresa transportadora"** (`FormField label="Empresa transportadora"`, `ShipmentCreatePage.tsx:178`) — rótulo que sugere apenas o subtipo "transportador", mesmo que a lista de opções inclua armadores, agentes e operadores. Um usuário selecionando um "agente de carga" nesse campo está preenchendo um campo rotulado como se fosse exclusivamente uma transportadora.
- **Título de página em sentence case é consistente** — todas as telas revisadas (`Pedidos`, `Faturas`, `Contas a pagar`, `Prestadores logísticos`, `Processos aduaneiros`, `Movimentos de estoque`, `Novo pedido`, `Novo embarque`, etc.) seguem o mesmo padrão de capitalização (só a primeira palavra maiúscula). **Não foi encontrada divergência Title Case vs. Sentence case** — item verificado e descartado como problema real, ao contrário do que o roteiro original da auditoria antecipava.
