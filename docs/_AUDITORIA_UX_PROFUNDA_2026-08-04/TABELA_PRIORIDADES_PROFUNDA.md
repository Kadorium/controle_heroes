# Tabela de prioridades — consolidação Fases 2-7

Data: 2026-08-04. Escala: **Impacto** 3 = usuário erra/perde dado/fica confuso/ação invisível · 2 = experiência degradada perceptível · 1 = polish. **Esforço** 3 = alto (arquitetura/nova dependência) · 2 = médio (componente React) · 1 = baixo (CSS/prop pontual).

## 🔴 Crítico (Impacto 3)

| # | Problema | Tela(s) afetada(s) | Impacto | Esforço | Arquivo(s) |
|---|---|---|---|---|---|
| 1 | Valores de exemplo hardcoded no estado inicial de formulários financeiros/fiscais (`payeeName="Bechtrans"`, `bankName="Banco Exemplo"`, `declaredTotal="1500.00"`, `basisAmount="1000"`, `taxAmount="300"`, `expenseAmount="200"`, `ncm="84713012"`, `unitPrice="100"`) — se o usuário não perceber e salvar sem alterar, cria registros de Numerário/Doganale fictícios que parecem reais | Numerário e Doganale (dentro de Processo aduaneiro) | 3 | 1 | `features/customs/NumerarioPanel.tsx`, `features/customs/DoganalePanel.tsx` |
| 2 | `amount` de novo pagamento inicia em `"1000"` hardcoded quando a tela é aberta sem contexto de fila (`g02.amount \|\| "1000"`) — risco de registrar pagamento com valor não intencional | Novo pagamento | 3 | 1 | `features/treasury/PaymentCreatePage.tsx:50` |
| 3 | Taxas de câmbio com default hardcoded ("6.00"/"6.25"/"6.20") em formulários de plano/cotação manual — mesma classe de risco do item 2, aplicada a taxa cambial | Câmbio da obrigação / Câmbio do pagamento | 3 | 1 | `features/treasury/FxPanels.tsx` |
| 4 | Vínculo de fatura/embarque/item por **ID interno numérico digitado à mão**, sem busca, sem lookup, sem confirmação visual do que será vinculado — 9+ campos no módulo de Aduana | Processo aduaneiro (Faturas, Embarques, Alocações), Numerário, Recebimentos, Liberações | 3 | 3 | `features/customs/CustomsDetailPage.tsx`, `features/customs/NationalizationPanel.tsx`, `features/customs/ReceiptPanel.tsx` |
| 5 | Reload pós-ação sobrescreve incondicionalmente campos de formulário não relacionados à ação disparada, apagando texto que o usuário estava digitando em outra seção da mesma tela, sem aviso além de mensagem genérica de conflito | Pedido (comercial) — botão "Atualizar"; Embarque — qualquer 409 em qualquer uma de 11 ações; Processo aduaneiro — qualquer ação bem-sucedida | 3 | 2 | `features/orders/OrderDetailPage.tsx:53-58,430-432`, `features/shipments/ShipmentDetailPage.tsx:356-373`, `features/customs/CustomsDetailPage.tsx:73-95,117-128` |
| 6 | Não existe controle de paginação (próxima/anterior) em nenhuma listagem — só um resumo textual. Combinado com limites fixos de 50-100 registros por chamada, registros além do limite ficam **inacessíveis** pela interface, muitas vezes sem indicação de que há mais dados | Todas as 7 listagens do app | 3 | 3 | `ui/PaginationSummary.tsx` + todas as `*ListPage.tsx` |
| 7 | `listSuppliers()`/`listProducts()` capados em `limit: 50` sem campo de busca (o parâmetro `q` existe na função mas nunca é usado pela UI) — fornecedores/produtos além do 50º ficam invisíveis nos formulários de pedido e pagamento | Novo pedido, Novo pagamento, filtro de fornecedor em Contas a pagar | 3 | 2 | `features/catalog/catalogApi.ts:7-11,26-30` |
| 8 | Classes CSS `btn-primary`/`btn-ghost` usadas no módulo de Aduana **não existem** em `index.css` (só `.ui-button--ghost`/`.btn-secondary`) — o link "Cancelar" da tela de novo processo renderiza como botão sólido de destaque igual ao de "Criar", em vez de link discreto | Processos aduaneiros (lista e criação) | 3 | 1 | `features/customs/CustomsListPage.tsx:96,125`, `features/customs/CustomsCreatePage.tsx:78` |
| 9 | Campo "Moeda" é texto livre (`TextInput` com `.toUpperCase()`) em vez de lista fechada (EUR/BRL) — em um sistema cuja razão de existir é a exposição cambial entre duas moedas específicas, aceitar qualquer string de moeda sem validação é um risco de dado inconsistente | Novo pagamento, filtro de Contas a pagar, Numerário | 3 | 1 | `features/treasury/PaymentCreatePage.tsx:187-194`, `features/billing/ApQueuePage.tsx:373-381`, `features/customs/NumerarioPanel.tsx:149-155` |
| 10 | `EmptyState` e a tabela vazia (com cabeçalho, sem linhas) renderizam **simultaneamente** quando não há obrigações — único ponto do app onde os dois estados coexistem em vez de serem mutuamente exclusivos | Contas a pagar (versão básica, sem `reporting:read`) | 3 | 1 | `features/billing/InvoicesListPage.tsx:154-182` (função `PayablesListPage`) |

## 🟡 Importante (Impacto 2)

| # | Problema | Tela(s) afetada(s) | Impacto | Esforço | Arquivo(s) |
|---|---|---|---|---|---|
| 11 | `ErrorState` sem `onRetry` em todas as telas de detalhe/edição e em 3 das 7 listagens — usuário precisa recarregar a página inteira (F5) para tentar de novo | Pedido, Fatura, Embarque, Pagamento, Processo aduaneiro (detalhe), Câmbio da obrigação, Pedidos/Faturas/Pagamentos (lista) | 2 | 1 | `ui/Feedback.tsx` (uso da prop `onRetry` já existe, só falta passá-la) |
| 12 | `MoneyInput` de alocação de pagamento não recebe a prop `currency` — único campo de valor monetário do app sem indicação de moeda, numa tela que pode alocar entre obrigações de moedas diferentes | Detalhe do pagamento (alocação) | 2 | 1 | `features/treasury/PaymentDetailPage.tsx:332-337` |
| 13 | EUR e BRL nunca são diferenciados visualmente (cor, ícone) — só pelo código de 3 letras em texto — em telas com KPIs das duas moedas lado a lado | Cockpit do pedido (KPIs), Câmbio da obrigação | 2 | 2 | `ui/MoneyDisplay.tsx`, `ui/format.ts` |
| 14 | Módulo de Aduana não usa `OperationalTable`/`StatusBadge` — dados tabulares (liberações, recebimentos, versões Doganale, divergências, Numerário) viram `<ul><li>` de texto corrido, perdendo alinhamento numérico e escaneabilidade de status | Processo aduaneiro + 4 painéis | 2 | 3 | `features/customs/CustomsDetailPage.tsx`, `NationalizationPanel.tsx`, `ReceiptPanel.tsx`, `DoganalePanel.tsx`, `NumerarioPanel.tsx` |
| 15 | Botões do módulo de Aduana usam só `disabled={busy}`, nunca `busy={busy}` — perdem o estado visual "em progresso" (`aria-busy`, opacidade 0.75, `cursor: progress`) que o resto do app usa | 4 painéis de Aduana | 2 | 1 | `NationalizationPanel.tsx`, `ReceiptPanel.tsx`, `DoganalePanel.tsx`, `NumerarioPanel.tsx` |
| 16 | 4 rótulos diferentes ("Voltar à fila", "Voltar", "Voltar aos embarques", "Cancelar") para o mesmo conceito de sair sem salvar; posição também diverge (topo-direito em 4 telas, rodapé-ao-lado-do-Salvar só em Processos aduaneiros) | Novo pagamento, Prestadores logísticos, Novo processo aduaneiro | 2 | 1 | `PaymentCreatePage.tsx`, `LogisticsProvidersPage.tsx`, `CustomsCreatePage.tsx` |
| 17 | Filtro de Movimentos de estoque exige clique em "Filtrar" para aplicar, enquanto todas as outras 6 listagens aplicam o filtro instantaneamente ao clicar/selecionar — modelo de interação diferente para o mesmo conceito | Movimentos de estoque | 2 | 2 | `features/inventory/MovementsPage.tsx` |
| 18 | Duas metáforas diferentes para "ver detalhe de uma linha da fila": navegação para página inteira (Pedidos/Faturas/Embarques/Pagamentos) vs. drawer lateral sem sair da lista (Contas a pagar) — sem critério aparente no código | Contas a pagar vs. demais filas | 2 | 3 | `features/billing/ApQueuePage.tsx` vs. demais `*ListPage.tsx` |
| 19 | Rótulo "Empresa transportadora" no campo de seleção de prestador logístico, mesmo quando a lista de opções inclui armadores, agentes e operadores (não só transportadoras) | Novo embarque, Detalhe do embarque | 2 | 1 | `features/shipments/ShipmentCreatePage.tsx:178`, `ShipmentDetailPage.tsx:907` |
| 20 | Dezenas de campos numéricos (IDs, quantidades, dimensões físicas de volume) sem `inputMode="numeric"`/`"decimal"` — força troca manual de teclado em mobile/tablet | Todo o app, especialmente módulo de Aduana e Volumes de embarque | 2 | 1 | Múltiplos — ver `INVENTARIO_INPUTS.md` |
| 21 | Loading "substitui a tela inteira" (cabeçalho, KPIs e filtros somem) em 6 das 7 listagens a cada troca de filtro, não só na carga inicial — só `ApQueuePage` preserva o chrome durante o refetch | Pedidos, Faturas, Pagamentos, Embarques, Processos aduaneiros, Movimentos de estoque | 2 | 2 | `OrdersListPage.tsx`, `InvoicesListPage.tsx`, `PaymentsListPage.tsx`, `ShipmentsListPage.tsx`, `CustomsListPage.tsx`, `MovementsPage.tsx` |
| 22 | Validação client-side (quando existe) nunca aponta para o campo específico com erro — só um `Notice` genérico no topo da seção; a prop `invalid` dos componentes de input quase não é usada na prática | Novo pedido, Detalhe do pedido, e a maioria dos formulários de escrita | 2 | 2 | Múltiplos |
| 23 | Erro de rede (`TypeError`/"Failed to fetch") só tem tratamento amigável específico no Login — em qualquer outra ação de escrita, o erro genérico do browser aparece cru para o usuário | Todo o app exceto Login | 2 | 2 | Múltiplos — camada de chamada de API |
| 24 | Nenhum campo de data tem `min`/`max` — nada impede registrar chegada prevista antes da saída prevista, ou datas de fatura no futuro | Novo embarque, Detalhe do embarque, Fatura | 2 | 2 | `ShipmentCreatePage.tsx`, `ShipmentDetailPage.tsx`, `InvoiceDetailPage.tsx` |
| 25 | `ApQueuePage.load()` e `OrderCockpitPage` fazem fetch sem guarda de cancelamento (`cancelled` flag) — trocar filtros rapidamente pode exibir uma resposta desatualizada por chegar fora de ordem | Contas a pagar, Cockpit do pedido | 2 | 1 | `ApQueuePage.tsx:141-153`, `OrderCockpitPage.tsx:63-67` |

## 🟢 Desejável (Impacto 1)

| # | Problema | Tela(s) afetada(s) | Impacto | Esforço | Arquivo(s) |
|---|---|---|---|---|---|
| 26 | Campos da linha de item (SKU/Qtd/UM/Preço) sem `FormField`/label persistente — só `placeholder`, que desaparece ao digitar | Novo pedido | 1 | 1 | `OrderCreatePage.tsx:279-309` |
| 27 | Três regras CSS quase idênticas para cabeçalho de tabela (`.data-table th`, `.mini-table th`, `.operational-table th`) sem fonte única de verdade | Todo o app | 1 | 2 | `index.css:299-303,950-954,1482-1486` |
| 28 | Tabela de prestadores cadastrados usa `<table className="data-table">` cru em vez do componente `OperationalTable` | Prestadores logísticos | 1 | 1 | `LogisticsProvidersPage.tsx:157-174` |
| 29 | `ConfirmationModal` tem dois controles que cancelam a mesma ação (botão ghost no cabeçalho + botão secundário no rodapé) — redundante em todo uso do componente | Todos os modais de confirmação (11 usos) | 1 | 1 | `ui/ConfirmationModal.tsx` |
| 30 | `maxLength` ausente na maioria dos campos de texto livre (notas, descrições, motivos de override, nomes de payee) — primeiro feedback de "texto longo demais" só vem do servidor | Múltiplas telas | 1 | 1 | Múltiplos |
| 31 | `.login-form h1` (28px hardcoded) é o único heading do app fora do token `--font-size-title` (22px) usado em todo o resto | Login | 1 | 1 | `index.css:129-135` |

---

## Classificação por tipo de risco de implementação

### Só CSS (`index.css`) — baixo risco
- #8 (classes `btn-primary`/`btn-ghost` inexistentes — trocar para `ui-button ui-button--ghost`)
- #27 (consolidar 3 regras de `<th>` em uma)
- #31 (unificar `.login-form h1` ao token `--font-size-title`)

### Alteração pontual de prop/estado em componente React já existente — risco baixo-médio
- #1, #2, #3 (trocar valores iniciais hardcoded por string vazia)
- #9 (trocar `TextInput` por `SelectField` com opções EUR/BRL)
- #10 (mover a tabela para dentro do ramo `else` da condição de vazio)
- #11 (passar `onRetry` já suportado pelo componente)
- #12 (passar a prop `currency` já suportada pelo componente)
- #15 (trocar `disabled={busy}` por `busy={busy}` nos botões dos painéis de Aduana)
- #16 (padronizar rótulo/posição do link de saída)
- #19 (ajustar o texto do rótulo)
- #20 (adicionar `inputMode` nos campos numéricos)
- #24 (adicionar `min`/`max` no `DateInput`)
- #25 (adicionar guarda `cancelled` nos dois `useEffect` que não têm)
- #26, #28, #29, #30

### Refatoração de componente/página — risco médio
- #13 (design de diferenciação visual EUR/BRL — precisa decisão de design antes da implementação)
- #17 (unificar modelo de filtro do Movimentos de estoque ao padrão de chips instantâneos)
- #21 (adotar em 6 telas o padrão de `ApQueuePage` de não zerar dados durante refetch)
- #22 (passar a validar por campo com a prop `invalid` já existente, exige revisar cada fluxo de validação)
- #23 (criar um tratamento central de erro de rede reutilizável)
- #5 (adicionar guarda de `isDirty` por campo antes de aplicar `reload()`/`syncForm()` — não é uma mudança trivial porque a função de reload é compartilhada por múltiplas ações na mesma tela)

### Arquitetura ou nova dependência — risco alto
- #4 (campos inteligentes de vínculo por ID — precisa de endpoint de busca no backend + componente de combobox/autocomplete no frontend, hoje inexistente)
- #6 (paginação real — precisa de UI de paginação nova e wiring de `offset`/`limit` em todas as listagens, mais decisão de produto sobre tamanho de página)
- #7 (busca server-side em fornecedor/produto — a API já aceita `q`, mas o componente `SelectField` nativo não suporta busca incremental; precisa de um componente de combobox pesquisável, que não existe hoje no design system)
- #14 (refatorar 5 arquivos do módulo de Aduana para o padrão de tabela/badge do resto do app — mudança extensa, não perigosa tecnicamente, mas grande em escopo)
- #18 (decisão de produto sobre qual metáfora de detalhe usar — não é uma correção técnica isolada, é uma escolha de UX que precisa ser tomada antes de qualquer refactor)
