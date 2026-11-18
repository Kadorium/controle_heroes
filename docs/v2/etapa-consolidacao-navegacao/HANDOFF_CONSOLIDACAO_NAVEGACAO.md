# EPIC — consolidação da navegação

Data: 18/11/2026. Etapa: consolidação da navegação. Status: **DONE**, com limites anteriores explicitados abaixo. Autorização: execução integral solicitada pelo usuário, incluindo investigação, implementação, ensaio isolado, commit e push. Não houve aprovação documental intermediária.

## 1. Resultado entregue

A lateral passa de **17 entradas de destino para cinco áreas principais e duas entradas secundárias**, conforme as permissões. Cada área abre uma tela de trabalho existente. As demais filas ficam em navegação local; não foram criados hubs de cartões, novas métricas ou rotas de domínio.

Ordem principal: **Visão geral → Produtos → Compras → Importações → Financeiro**. Secundário: **Conferir documentos → Usuários e acessos**. A área sem nenhuma seção permitida fica oculta; a primeira seção permitida é sua entrada. A ordem não depende de contadores ou dados carregados.

O executável existente `EPIC/Iniciar EPIC.exe` foi iniciado e abre a release **executive-20261118.1**, em `http://127.0.0.1:8082`. O frontend promovido é o mesmo validado no laboratório. Backend, banco, ícone e configuração do launcher não foram modificados nesta entrega.

**Decisão material:** Custo desembarcado permanece principalmente em **Importações**, pois a tela real trabalha por processo, caso e versão. A consulta ao custo de um produto continua acessível no estoque, com composição, fonte, base e versão. Receber mercadorias fica em Importações, com fila global e atalho pela operação.

## 2. Investigação, autoridade e referência anterior

- Regras aplicáveis: `.cursor/rules/epic-v2.mdc`; mapa e DOC_DELTA: `docs/README.md`; estado e sequência: Parte B do `ROADMAP_V2_EPIC.md`. A solicitação explícita autorizou commit/push na branch existente, preservando WIP, em lugar de trocar para `main`.
- Roadmap encontrado: **0.5.163**, ativo; atualizado para **0.5.164**. Blueprint de Sistema continua autoridade de domínio e não precisou de alteração.
- Blueprint UI/UX encontrado: **3.13**, referência de design ativa/consultiva, não autoridade de domínio. Atualizado para **3.14**, distinguindo o mapa implementado do arranjo anterior. O histórico 3.13 foi preservado e marcado como superado quanto à navegação.
- Mestre ativo de refinamento: `docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md`; acrescentado §13.5. Nenhum novo `.plan.md`. O mestre já era WIP não versionado; seu trecho novo está também em `delivery-working-tree.patch`, sem incorporar o documento anterior inteiro ao commit.
- Inventário `EPIC/MENU LATERAL - FUNCOES E DIFERENCAS.md`, de 18/11/2026, e `docs/v2/etapa-apresentacao-20261117/menu-inventory/navigation.json`: as **17 entradas e executive-20261117.4 foram confirmadas na UI**. Nova captura independente em `before/navigation.json`, `before/stock.png` e `before/costing.png`.
- Caminhos reais: `v2/frontend/src/app-shell/AppShell.tsx`, `v2/frontend/src/features/catalog/ProductAreaNav.tsx`, rotas em `v2/frontend/src/App.tsx`; retornos em `src/navigation/returnState.ts`; permissões em `v2/app/identity/public.py` e `identity/repository.py`, além das guardas de páginas e APIs.
- Divergências materiais: custo é uma fila por importação; recebimento depende de nacionalização liberada; o atalho de câmbio reutiliza a fila de obrigações. O runtime anterior também continha refinamentos ainda não commitados, além de HEAD. Anexos antigos não foram tratados como retrato obrigatório do sistema.

### Runtime e isolamento verificados

| Uso | URL / processo servido | Banco efetivamente consultado | Build / backend |
|---|---|---|---|
| Referência anterior | `127.0.0.1:8082`, wrapper `audit-runtime/executive-20261117/release-runtime.py` | `epic_v2_test`, PostgreSQL **5458**, diretório `audit-runtime/executive-20261117/postgres`, schema **034** | `executive-20261117.4`; backend empacotado em `audit-runtime/executive-20261117/v2` |
| Laboratório desta entrega | `127.0.0.1:8102`, wrapper `audit-lab/navigation-20261118/serve.py` | Clone independente `epic_v2_test`, PostgreSQL **5460**, diretório `audit-lab/navigation-20261118/postgres`, schema **034** | `dist-navigation`; mesmo backend empacotado, storage próprio |
| Release final do executável | `127.0.0.1:8082`, reiniciada pelo launcher | Mesmo banco **5458**; nenhuma escrita de ensaio promovida | **executive-20261118.1**; mesmo backend e schema |

A identificação usou processo/linha de comando, configuração carregada e SQL `current_database()`, `inet_server_port()` e `current_setting('data_directory')`. A porta 8082 não foi usada como prova de teste. `APP_ENV=test` e o banco foram confirmados. Cotação externa ficou desativada pelos wrappers de ensaio já usados; a faixa mantém seus controles e permissões.

O laboratório foi preparado por cópia, sem reset geral. Novos dados identificáveis `NAV18-*` ficaram exclusivamente em 5460. Identidade/perfis sintéticos foram preparados diretamente no banco isolado; pré-requisitos de compra/importação e documento foram preparados por API. Esses passos **não são evidência de percurso pela UI**. Evidências: `lab.json`, `fixtures.json`, `document-fixture.json` e scripts de preparação.

## 3. Mapa dos destinos e permissões

A permissão abaixo é a de leitura da seção. Escrita continua nas guardas existentes da página e do backend. `admin` conserva sua regra atual. Não há exigência adicional de permissão para a área.

| Destino anterior | Área / seção final | URL preservada | Permissão de leitura |
|---|---|---|---|
| Visão geral | Visão geral, entrada direta | `/dashboard` | `reporting:read` |
| Estoque atual | Produtos → **Estoque atual**, preferencial | `/inventory/positions` | `inventory:read` |
| Catálogo e preços / Produtos | Produtos → Catálogo e preços | `/catalog/products` | `catalog:read` |
| Movimentações | Produtos → Histórico de estoque | `/inventory/movements` | `inventory:read` |
| Pedidos | Compras → **Pedidos**, preferencial | `/orders` | `orders:read` |
| Faturas | Compras → Faturas | `/invoices` | `billing:read` |
| Fornecedores | Compras → Fornecedores | `/catalog/suppliers` | `catalog:read` |
| Operações de importação | Importações → **Operações**, preferencial | `/customs` | `customs:read` |
| Embarques | Importações → Embarques | `/shipments` | `logistics:read` |
| Recebimentos | Importações → Receber mercadorias | `/inventory/receiving` | `inventory:read` |
| Custos de importação | Importações → Custo desembarcado | `/costing` | `costing:read` |
| Prestadores logísticos | Importações → Prestadores logísticos | `/logistics-providers` | `logistics:read` |
| Contas a pagar | Financeiro → **Contas a pagar**, preferencial | `/payables` | `billing:read` |
| Pagamentos | Financeiro → Pagamentos realizados | `/payments` | `treasury:read` |
| Câmbio por obrigação | Pela obrigação; seção de fallback em Financeiro somente sem `billing:read` | `/payables?purpose=fx` e `/payables/:id/fx` | `treasury:fx_read`; lista de contas continua exigindo `billing:read` |
| Conferir documentos | Secundário → Conferir documentos | `/ingestion` | `ingestion:read` |
| Usuários e acessos | Secundário → Usuários e acessos | `/admin/users` | `users:read` |

As visões **Executiva, Comercial e Controle** continuam no painel existente, com catálogo de indicadores e permissões atuais. Não foram adicionadas consultas para construir abas ou badges. Detalhes, formulários, comparações, preços e URLs antigas permanecem nas rotas existentes. A seleção considera o segmento da rota, inclusive subrotas. A aba ativa mantém query/state na própria lista e usa o retorno existente ao sair de detalhes.

### Hipóteses e decisões

| Hipótese | Resultado e evidência | Decisão implementada |
|---|---|---|
| Câmbio repete Contas a pagar | **Confirmada para quem lê Billing; parcial para acesso exclusivo a FX.** `InvoicesListPage.tsx` contém `PayablesListPage`; `purpose=fx` é modo da mesma rota. APIs de FX usam a obrigação como chave. | Removida entrada duplicada para quem já acessa contas. Preservadas URLs e links de câmbio. Sem Billing, Financeiro abre formulário de número da obrigação na rota existente, seguindo para seu FX sem consultar contas. Não foi criado `/fx` nem hub. |
| Receber mercadorias pertence a Importações | **Confirmada.** `inventory/receiving.py` usa `customs.receiving_sources`; fila recebe residual de itens de nacionalização liberados. Ajustes/reclassificações pertencem ao histórico e não constituem outra origem dessa fila. | Localização principal única em Importações; fila global e parcial preservadas. Operação oferece link contextual com `q=<código>` e `state=all`. |
| Custo por produto deve ter localização principal em Produtos | **Confirmação parcial do objetivo; localização proposta refutada pela tela real.** `CostingListPage` lista processos/casos; workspace trabalha com versões, fontes, cobertura e composição do desembarcado. Produto é resultado/consulta, não a unidade primária da fila. | Fila em Importações, rótulo Custo desembarcado. Consulta por produto no estoque preservada, sem confundir custo, pagamento e margem potencial. |
| Cadastros seguem suas jornadas | **Confirmada.** Fornecedor depende de Catalog; prestador depende de Logistics, sem exigir Orders/Customs. | Fornecedores em Compras e prestadores em Importações; fallback permite entrada direta com o cadastro isoladamente autorizado. |
| Documentos é entrada transversal existente | **Confirmada.** Fila/workspace de ingestion, com tipos e vínculos já existentes. | Mantida a fila, incluindo documento de transporte/importação. Nenhuma biblioteca documental nova. |

Relações conferidas no código: uma operação possui coleções de faturas, embarques e nacionalizações; recebimento acompanha residual por item. Fatura/obrigação e pagamento/vinculação continuam objetos distintos; crédito pode existir sem alocação. A navegação conserva coleções e identificadores, sem impor cardinalidade 1:1 ou alterar cálculos, modelos, contratos, dados operacionais ou regras de emissão/liberação.

## 4. Visibilidade e autorização

Os quatro papéis definidos no código foram conferidos; a lista integral de permissões está em `roles.json`. Contagens anteriores referem-se a destinos, finais a áreas e entradas secundárias, não a direitos novos.

| Perfil real | Antes | Depois | Restrições preservadas |
|---|---|---|---|
| admin | 17 destinos | 5 áreas + documentos + usuários | Regras administrativas existentes |
| comprador | 16 destinos, sem usuários | 5 áreas + documentos | Não ganha usuários, recebimento/escrita de estoque, publicação de custo ou escrita aduaneira/logística |
| aduana | Visão geral, operações, custos | Visão geral + Importações: Operações/Custo desembarcado | Não ganha estoque, cadastro, finanças ou publicação de custo |
| estoque | Visão geral, estoque, recebimentos, movimentações | Visão geral + Produtos: Estoque/Histórico + Importações: Receber mercadorias | Não ganha catálogo, pedidos, operações ou custos; escrita de recebimento/ajuste permanece conforme ACL |

Combinações adicionais ensaiadas na UI com permissões sintéticas **somente no laboratório**:

| Permissões isoladas | Entrada observada | Resultado |
|---|---|---|
| `catalog:read/write` | Produtos → Catálogo; Compras → Fornecedores | Cadastro e retorno funcionam sem Orders nem Audit; `/orders` continua negada |
| `costing:read` | Importações → Custo desembarcado | Não depende de Customs; sem publicar custo |
| `inventory:read` | Produtos → Estoque/Histórico; Importações → Receber mercadorias | Sem Catalog/Customs e sem escrita |
| `logistics:read/write` | Importações → Embarques/Prestadores | Sem exigir Customs |
| `treasury:fx_read` | Financeiro → Câmbio por obrigação | Abre obrigação por ID, sem listagem Billing nem controles de escrita FX |
| `treasury:read/write` | Financeiro → Pagamentos realizados | Sem exigir Billing; fila global de pagamentos disponível |

A investigação expôs duas dependências de UI indevidas: detalhes de cadastro consultavam Audit incondicionalmente; a pesquisa de SKU no histórico consultava Catalog. Foram corrigidas com guardas de permissão e a consulta de estoque já autorizada. As APIs e listas de permissões não mudaram. Isso evita que o novo fallback leve um usuário autorizado a uma tela quebrada.

## 5. Alterações e contexto preservado

- `app-shell/navigation.ts`, `AreaNavigation.tsx` e `areaNavigation.css`: definição compartilhada pequena, lateral 5+2, navegação local, seleção, foco, rótulos na lateral recolhida e espaçamento. `AppShell.tsx` integra os componentes. `ProductAreaNav.tsx` deixa de duplicar destinos locais.
- `App.tsx`, `InvoicesListPage.tsx`, `FxObligationAccess.tsx` e `PayableFxPage.tsx`: fila avançada exige leitura Billing; acesso FX isolado não dispara consulta Billing. Os filtros de contas suportados pelo backend são repassados também na lista simples.
- Detalhes de fatura e operação: atalhos **Contas desta fatura** e **Receber mercadorias**, com identificador/filtros e permissão pertinente.
- Páginas de inventário, custos, operações, prestadores e usuários: rótulos/breadcrumbs coerentes. `SupplierDetailPage`, `ProductDetailPage`, `MovementsPage` e `SkuPositionPage`: acesso parcial e contexto de produto preservados.
- `dashboardNavigation.ts`: transporta filtros efetivamente aplicados e suportados pela fila; vencidos, próximos sete dias, agenda de três meses civis, exposição em moeda única, estoque em todos os regimes e pedidos confirmados. Não altera valores dos indicadores.
- Testes focados protegem áreas vazias/fallbacks, rota ativa, parâmetros/retorno e ausência de consultas Billing/Audit sem autorização. E2E existentes de shell e papéis foram adaptados aos novos caminhos.

Não houve mudança de backend, API gerada, permissões, modelo, cálculo ou política econômica. Produtos sem estoque, crédito sem vínculo/adiantamento, recebimento parcial e versões de custo continuam disponíveis.

## 6. Testes executados e correções

| Verificação | Resultado observado | Evidência |
|---|---|---|
| Typecheck + build do working tree validado | **PASS**, bundle final gerado; aviso anterior de chunk grande, sem erro | `build.log`, `candidate-assets.json` |
| Suíte frontend da versão servida | **255/255 PASS** | `unit-results.json`, `unit.log` |
| E2E existentes: shell e três papéis | **4/4 PASS**, sem skip | `existing-e2e.json` |
| Navegação no laboratório | **29 grupos PASS**, sem erro JS: todos os destinos, quatro combinações de resolução/lateral, links antigos e nove perfis não admin | `ui/smoke.json` |
| Percursos funcionais no laboratório | **10/10 PASS** na rodada final | `ui/journeys.json` |
| Conferência posterior à promoção | **20 grupos PASS** no runtime 8082, duas resoluções e dois estados da lateral | `ui-release/smoke.json` |
| Documento efetivamente renderizado e páginas finais | **PASS**; PDF esperado pronto, sem depender apenas da lista | `final-review.json`, `ui/transversal-document-ready.png` |
| Integridade da promoção | **294 arquivos do manifesto conferidos**, índice candidato/release idêntico; launcher terminou com código 0 e health/schema 034 disponíveis | `promotion.json`, `candidate-assets.json` |
| Conteúdo isolado do commit, sem WIP anterior | Typecheck/build e **246/246 testes PASS**; menos testes porque os testes do WIP anterior não foram incorporados | `isolated-commit-build.log`, `isolated-commit-unit.json` |

As verificações de UI usaram Chromium/Playwright real com cliques, teclado, leitura de tela/DOM e screenshots, sem simular respostas do backend. Resoluções: **1366×768 e 1440×900**; lateral expandida/recolhida; foco por teclado, ausência de sobreposição na navegação, recarga, voltar/avançar, URLs antigas e retorno de detalhes/formulários. Os relatórios contam grupos de verificações, não pessoas ou endpoints.

Rodada inicial preservada em `ui/journeys-attempt1.json`: pesquisa de SKU pelo perfil Estoque e detalhe do fornecedor com Catalog sem Audit falharam; corrigidos e repetidos. Também houve ajuste de espera/seletor do ensaio e preparação do documento fictício que não existia no clone. O PASS é da rodada final; falhas anteriores não foram apagadas nem atribuídas a aprovação.

### Percursos — Abri / Vi / Cliquei / Resultado

Todos os percursos abaixo são do runtime **8102 / banco 5460**, salvo indicação. Complementos por API são identificados explicitamente.

| Tarefa / perfil | Abri / Vi / Cliquei / Resultado |
|---|---|
| Produto com saldo e custo — admin | **Abri** Produtos/Estoque com `SHOW26`. **Vi** produto, saldo e base/versão de custo. **Cliquei** produto → compra/composição → histórico → voltar. **Resultado:** filtro e contexto preservados; fonte/composição de custo acessíveis. |
| Produto sem estoque — admin | **Abri** Catálogo e preços. **Vi** `NAV18-SEM-ESTOQUE`. **Cliquei** Ver estoque. **Resultado:** produto encontrável sem saldo físico; catálogo não foi restringido à disponibilidade. |
| Fatura → obrigação → FX → pagamento — admin | **Abri** fatura 2. **Vi** contas filtradas por `invoice_id`. **Cliquei** câmbio, retorno e formulário de pagamento. **Resultado:** obrigação/moeda/valor presentes; formulário e retorno funcionam. Nenhum pagamento foi registrado nesse percurso. |
| Crédito/adiantamento — admin | **Abri** Financeiro/Pagamentos realizados. **Vi** crédito em aberto. **Cliquei** filtro, pagamento 9 e Voltar à fila. **Resultado:** detalhe acessível e `unallocated_only=1` preservado. |
| Chegada ≠ liberação ≠ recebimento — admin | **Abri** Embarques. **Vi** Chegou. **Cliquei** Operações → processo liberado → Receber mercadorias. **Resultado:** fila da operação distingue liberado, recebido e pendente. |
| Recebimento parcial e histórico — estoque | **Abri** Importações por fallback. **Vi** 10 unidades fictícias liberadas. **Confirmei** 4 na UI. **Resultado:** 4 recebidas, 6 pendentes; saldo, recarga e histórico coerentes. A rodada final retomou esse parcial, sem receber novamente. API complementou a conferência 4/6. |
| Documento transversal — admin | **Abri** Conferir documentos. **Vi** documento fictício `PACKING_LIST_DETAIL`. **Cliquei** revisão e retorno. **Resultado:** fila/workspace acessíveis; em revisão final o PDF foi aguardado até renderizar. Upload/staging foram preparação via API; não houve commit documental. |
| Cadastro sem Pedidos — catalog-only | **Abri** Compras por fallback. **Vi** Fornecedores. **Cliquei** Novo fornecedor, gravei `NAV18-UI-2` e retornei. **Resultado:** detalhe/lista funcionam; acesso direto a Pedidos continua negado. |
| Indicador → conjunto correspondente — admin | **Abri** Visão geral com período e EUR. **Vi** vencidos. **Cliquei** Abrir fila de vencidas. **Resultado:** `OVERDUE`, período e EUR preservados; API complementar confirmou as mesmas **4 obrigações / EUR 8.944,63**. |
| FX exclusivo — fx-only | **Abri** Financeiro. **Vi** campo de obrigação. **Informei** 2 e abri câmbio. **Resultado:** painel existente funciona sem consulta à lista/contexto Billing; sem controles de escrita, com retorno ao campo. |

Escritas de negócio pela UI no laboratório: **um recebimento parcial e dois fornecedores fictícios**. O primeiro fornecedor (`NAV18-UI`) foi salvo antes de a falha de Audit aparecer; o segundo confirmou o fluxo corrigido. Preparação de identidades/dados/documento foi separada. Nenhum registro operacional foi alterado para produzir evidência e nenhuma dessas escritas foi copiada à release 5458.

### Comparação de caminhos frequentes

| Tarefa | Caminho anterior típico | Caminho final | Troca |
|---|---|---|---|
| Ver estoque | grupo Produtos → Estoque atual | Produtos | Entrada preferencial imediata |
| Catálogo / histórico | grupo → destino, com repetição local | Produtos → aba | Dois níveis claros; sem repetir destinos na lateral |
| Receber — admin | grupo Produtos → Recebimentos | Importações → Receber mercadorias | Dois passos, agrupamento conforme origem real |
| Receber — estoque | destino permitido no grupo | Importações | Fallback abre diretamente recebimento |
| Custo global | Financeiro → custos | Importações → Custo desembarcado | Mesmo nível, significado explícito; custo pelo produto continua contextual |
| Faturas / pagamentos | grupo → fila | Compras/Financeiro → aba | Fila global continua encontrável |
| Contas de uma fatura | sair para contas e localizar | Fatura → Contas desta fatura | Um atalho contextual com filtro |
| Câmbio | atalho duplicado → obrigação | Contas → câmbio da obrigação | Remove duplicação; URL antiga preservada; FX-only tem caminho próprio permitido |
| Conferir documentos | Compras/documentos → destino | Conferir documentos | Entrada transversal direta |

## 7. Evidências visuais para revisão

- [Antes: estoque e lateral](before/stock.png).
- [Depois: Produtos / estoque, 1366×768](ui-release/final-stock.png).
- [Importações / recebimento](ui-release/final-receiving.png).
- [Importações / custo desembarcado](ui-release/final-costing.png).
- [Lateral recolhida, 1366×768](ui-release/1366-rail-imports.png).
- [Lateral expandida, 1440×900](ui-release/1440-expanded-imports.png).
- [Documento de transporte fictício renderizado](ui/transversal-document-ready.png).

O ZIP de revisão reúne este handoff, as versões commitadas do Roadmap e do Blueprint UI/UX e essas imagens, mantendo as pastas dos links. As alterações locais anteriores dos documentos continuam preservadas fora do commit. Os documentos canônicos de revisão adicionais foram solicitados expressamente pelo usuário; não é um novo plano para aprovação.

## 8. Limites, pendências e próxima etapa

1. Alguns indicadores anteriores ainda abrem filas mais amplas por falta de filtro equivalente: agregados de várias moedas em pagamentos/FX, embarques em múltiplos estados e custo publicado por última versão. O recorte de vencidos foi validado por conjunto/valor; **não se declara equivalência exata para todos os indicadores**. Resolver os demais exige capacidade de fila/contrato fora desta reorganização. Registrado em B.6; sem métrica ou endpoint inventado.
2. O vídeo anterior continua mostrando a navegação antiga. Foi preservado; não foi regravado neste escopo de consolidação. Próxima ação do Roadmap: usar a navegação consolidada e revisar este handoff; avaliar a atualização dos vídeos separadamente.
3. Política econômica para operação, conferência física e I-01/offsite permanecem no backlog anterior. Esta entrega não aprova regras contábeis/tributárias nem promove dados à operação.
4. O repositório continua com WIP anterior extenso. O build entregue reúne o estado local anterior preservado e esta consolidação; o commit inclui apenas o incremento desta entrega. A release mantém `uncommitted_candidate=true`, pois não corresponde a um checkout limpo de HEAD. A separação Git foi validada em checkout isolado, sem substituir a versão servida.
5. Não foi repetida uma campanha integral de domínio/backend. Nenhum teste não executado recebe PASS. A inspeção de cardinalidades, listas de permissões e origem de recebimento foi por código; os percursos listados acima foram pela UI.

## 9. Git, release e rastreabilidade

- Branch preservada: `feat/stock-executive-20261023`.
- HEAD inicial e remoto inicial: `448ca3a8271d326c902babf7d061bff9eb71b7e4`.
- Working tree inicial: **1.718 entradas** com `--untracked-files=all`; index vazio. Backup em `EPIC/backups/navigation-before-20261118`, incluindo patch binário do WIP, fontes anteriores e release anterior.
- Remoto: `origin`, `https://github.com/Kadorium/controle_heroes.git`.
- Commit de implementação: `86cf1c61944405ca966452c6db3f2b29664b5258`.
- Push da implementação: **CONFIRMADO** por push normal e `ls-remote`, remoto igual ao commit acima. Este handoff e evidências têm fechamento documental próprio, sem force push.
- Apenas os hunks desta entrega foram separados sobre HEAD; arquivos existentes permaneceram no working tree. O mestre anterior não versionado e seu conteúdo alheio ficaram fora do commit; o novo §13.5 está registrado no patch incremental desta entrega. Scripts, testes e documentos próprios são identificados no commit.
- Build final: `executive-20261118.1`; assets ativos `index-CoWSD9W0.js` e `index-Bp2zwKZO.css`.
- SHA-256 do `index.html` candidato e servido: `07f1be9d69a86b852f5e8ce79dd63e6edd1bd8539f7c938cea64c1834b13ec9f`. Conferência HTTP dos assets em `final-review.json`; manifesto em `candidate-assets.json`; promoção em `promotion.json`.
- `source-changes.json` e `delivery-working-tree.patch` registram o incremento sobre a referência local real. Os relatórios de testes distinguem working tree validado de conteúdo isolado do commit. Nenhuma alteração funcional foi feita no frontend servido depois da validação final.

## 10. DOC_DELTA e retorno

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md; mestre ativo UI_EXECUTIVA_REFINEMENT_PLAN.md §13.5 (local, delta preservado); frontend de navegação/retornos/permissões de consulta e testes indicados no commit.
- Evidence: docs/v2/etapa-consolidacao-navegacao/ — handoff, referências, resultados JSON/logs, scripts, imagens e patch incremental.
- Roadmap status: 0.5.164, consolidação DONE. A: última/próxima entrega atualizadas. B: estado, gates, próxima ação, referência do handoff e limite dos indicadores. Livro-razão e denominadores inalterados; cadeia 10/10 = 100%, sem nova capacidade de domínio. Arquivo com 300 linhas e Parte A dentro do teto de 70.
- Next TODO: usar a navegação consolidada e revisar o handoff; política econômica para operação, conferência física e I-01/offsite fora do escopo; avaliar atualização dos vídeos existentes.
- Return to advisor: HANDOFF_CONSOLIDACAO_NAVEGACAO.md; ROADMAP_V2_EPIC.md; BLUEPRINT_UI_UX_EPIC_v3.md; PACOTE_CONSOLIDACAO_NAVEGACAO.zip.
```

Entrega concluída para uso da navegação atual. As pendências acima permanecem explicitamente separadas do aceite executado.
