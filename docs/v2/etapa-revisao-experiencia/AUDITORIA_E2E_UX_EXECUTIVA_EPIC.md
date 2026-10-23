# Auditoria integrada — EPIC Controle

23/10/2026 · Brasília · avaliação executada por agente com Playwright, backend e PostgreSQL reais.

## 1. Conclusão executiva

**A versão continua apresentável no roteiro Heroes, mas não deve receber aceite integrado irrestrito.** O percurso novo conseguiu comprar, faturar, alocar pagamento parcial, embarcar, liberar, receber e cadastrar preços pela UI. A ligação final com um custo confiável **falhou no estado incompleto exercitado**. Não foi uma cadeia integralmente aprovada.

Principais problemas desta rodada, sem compensação por média de notas:

1. **Alto — custo incompleto publicado como zero e cobertura completa.** A fatura estava vinculada ao processo, mas seus itens não foram alocados. Mesmo com `NO_INVOICE` e componentes `missing_basis`, o sistema publicou R$ 0,00, exibindo “Completa” e divergências “BLOCKING”. O estoque foi mais defensivo: manteve custo e margem ausentes para esse saldo.
2. **Alto — Contas a pagar não oferece navegação para além da primeira página.** Com 59 obrigações abertas, mostra 50 e “Exibindo 1–50 de 59”, sem controle de próxima página. Foi necessário conhecer `offset` na URL para acessar o restante.
3. **Alto — “Por alocar · fila completa” depende da página.** No mesmo filtro, mudar somente `offset` alterou EUR 2.650,00 para EUR 2.550,00. Saldo aberto e vencidos permaneceram iguais. O problema está no recorte do resumo, não em uma nova liquidação.
4. **Alto — natureza cambial incorreta no custo estimado.** Uma taxa planejada 6,000000 foi apresentada como documental do Numerário, que não forneceu essa taxa.
5. **Médio — “Cancelar” a edição de produto conserva o rascunho na próxima edição.** Salvar outros campos pode acabar gravando o texto que o usuário cancelou.
6. **Médio — retorno pelo caminho produto → composição → PDF → estoque perde foco** quando a URL original tem tabela de preço vazia e o retorno normaliza para `1`. Filtros, ordenação e números sobreviveram; o foco não.

O tour normal percorreu oito etapas em **405 segundos (6min45s)**, com intervalo configurado de 50 segundos, sem gravações de negócio observadas. O saldo SHOW26 e a obrigação A permaneceram intactos na apresentação e na cópia. A inspeção foi de viewport, **não uma conferência física ou um teste humano de compreensão no laptop**.

Nenhum fonte da aplicação, contrato, cálculo, migration ou bundle foi modificado. Não houve build, redesenho, promoção ou correção de produto. O objetivo desta entrega é dar ao advisor uma base verificável para priorizar correções.

### Quatro conclusões distintas

- **Funcionamento integrado: PARCIAL.** Caminhos positivos financeiro/físico e proteções críticas comprovados. Custo incompleto, paginação AP e caminhos não exercitados impedem aceite global.
- **Consistência dos dados: PARCIAL.** Ledger, saldos, alocação, preço vigente, SHOW26 e agregações principais reconciliados. Cobertura do custo e resumo de pagamentos por alocar têm inconsistências confirmadas.
- **UX executiva: utilizável com ressalvas.** Estoque é acessível e tem densidade útil; a comparação financeira funciona no recorte válido. Aduana, custo e cadastro ainda demandam conhecimento técnico; faltam previsibilidade no cancelamento e retorno de foco.
- **Demonstração: pronta no roteiro preservado, com ressalvas.** 8082 permanece disponível, sem a massa AUD26. Não usar o novo caso de custo como exemplo de resultado confiável. Conferência física do apresentador segue pendente.

## 2. Versão, ambientes, perfis e método

### Identidade confirmada, não presumida

| Item | Apresentação preservada | Laboratório desta auditoria |
|---|---|---|
| URL | `http://127.0.0.1:8082/dashboard` | `http://127.0.0.1:8094/dashboard` |
| Diretório relativo à pasta EPIC | `audit-runtime/receiving-stock-20261023` | `audit-lab/integrated-20261023` |
| PostgreSQL / banco | 5451 / `epic_v2_test` | 5452 / `epic_v2_test`, cluster próprio |
| Schema | 034 | 034, restaurado; sem migrations |
| Build | `receiving-stock-20261023.1` | mesmo build, sem recompilar |
| Fonte servido | `e48f7c283ea201e56d658f6ddb2dcb9f1ab96157` | mesma cópia de app/alembic/dist |
| Storage | `storage/attachments`, `storage/quarantine` próprios | cópias próprias, caminhos absolutos validados no launcher |
| Integrações | apresentação não reconfigurada | provedor cambial offline; sem envio bancário, e-mail ou integração externa de negócio |

Checkout de trabalho: `C:\Users\ricar\Desktop\projetos\EPIC\Controle`. Branch `feat/stock-executive-20261023`. HEAD inicial e referência remota eram ambos `b50c8d6d51d95272b60dc01b0660eac4e260bf43`; esse é fechamento documental, **não** o hash do bundle. A tag `delivery/receiving-stock-20261023.1` aponta para `e48f7c283ea201e56d658f6ddb2dcb9f1ab96157`.

A igualdade foi conferida por HTTP do `build-info.json`, manifesto e conteúdo dos dois assets JS/CSS, além da identidade PostgreSQL (porta, banco, `data_directory`, identificador do cluster). Manifesto SHA-256: `ccdffde8486c98773f87f5bdb0416670b09cde00d1de8c089ca6cb36df7c53b9`. JS: `3d95a4cba163fa35b304aeb28dcae9e9006b8c72fc8dac354011edc9e998b614`. CSS: `5426f4d2a6fab4105ae755b886e53e0db7a8edbec248b2af717867b154562171`. Evidência: `evidencias/reconciliation.json`.

**Diferenças deliberadas:** porta, cluster, storage, cookie de sessão e cotação offline; a cópia recebeu AUD26, preferências e operações de teste. A cotação já persistida continuou visível como desatualizada. Não foi alterada a hora do sistema para simular vigências. Todas as datas de “hoje” deste relatório se referem a 23/10/2026 em Brasília.

### Perfis reais

- Administrador: referência executiva e ações administrativas/logísticas/custos/preços.
- Comprador: compra, fatura, pagamento/alocação, edição de produto e fornecedor; sem administração e gestão de preços.
- Aduana: processo, declaração, numerário e liberação; não recebeu permissões financeiras ou de catálogo adicionais.
- Estoque: recebimento, saldo e histórico. Servidor negou consultas de processo aduaneiro, obrigação, pagamento e preço com 403.

Não existem papéis separados “CEO” ou “financeiro” nessa base. A avaliação executiva foi como administrador; isso não transfere suas permissões aos outros perfis. Logins ocorreram pela UI. Credenciais e cookies foram excluídos do pacote.

### Como ler as evidências

**Preparação:** clone recuperável da demonstração e três PDFs sintéticos válidos. A história AUD26 foi criada pela UI. A única preparação de negócio por API foi a fixture auxiliar de paginação **AUD26-PAGE**, explicitada adiante; consultas GET e SQL auxiliar não contam como operações UI.

**Interação:** cliques, preenchimento, teclado, navegação, confirmação, recarga e reabertura em Chromium/Playwright. Nenhum clique é atribuído a um apresentador humano.

**Persistência:** reabertura e leitura na UI, mais consultas de apoio aos endpoints e SQL somente leitura. Resultados esperados foram definidos por aritmética explícita, sem importar os calculadores sob teste.

**Falhas simuladas:** apenas consulta de estoque 503, alvo/manifesto indisponível no tour e perda da resposta após confirmação de recebimento/importação. Nesses dois últimos, o servidor realmente gravou; somente a resposta ao browser foi abortada. Demais percursos usaram respostas reais.

Os testes são jornadas com estado. Retentativas consultaram primeiro os registros persistidos. Correções de localizador, rótulo, espera ou entrada inválida do runner não são defeitos do produto nem operações independentes. A senha foi fornecida por ambiente, nunca registrada nas evidências selecionadas.

Execuções dirigidas registradas em oito arquivos `audit-*.spec.ts`, mais quatro casos do runner existente de tour. O conjunto não é uma suíte verde única pronta para repetir: os cenários de escrita exigem snapshot inicial ou retomada consciente. Tentativas de ADM/FOR/EXE com localizador/rótulo incorreto foram substituídas por `audit-complete`; a tentativa positiva CUS-03 ficou explicitamente bloqueada, e seus scripts iniciais foram marcados `skip` após conservar a evidência. FIN-05 e CUS-02 são testes de caracterização: podem terminar tecnicamente verdes ao registrar um defeito; a matriz continua marcando a função como **falhou**. Não foram executadas suítes integrais/reset, build ou testes unitários nesta auditoria de UI; resultados históricos não foram somados.

## 3. Inventário e matriz de cobertura

Confrontados `App.tsx`, AppShell, páginas, permissões e runtime: **43 declarações de rota**, incluindo `/login` e `/`, mais redirecionamento de índice; **17 destinos de menu** descobertos. O inventário abaixo agrupa cenários verificáveis, não cada botão como uma funcionalidade independente. As linhas de consulta **não** aprovam CRUD/validações da página. O total e a distribuição são calculados das linhas da matriz no empacotamento.

<!-- COVERAGE -->

Legenda: **A** aprovado no alcance descrito; **F** falhou; **B** bloqueado; **N** não executado; **NA** não aplicável. “UI” é execução desta rodada; “API” indica apoio/preparação, não aprovação pela interface. Histórico de suítes antigas não entra nos totais.

| Caso | Módulo / funcionalidade e entrada | Perfil / cenário e evidência | Resultado | Limite ou observado |
|---|---|---|---|---|
| ID-01 | Login, logout, sessão e redirecionamento | Todos; ACL-02 | A | UI real, sair e voltar à rota protegida pede login |
| ID-02 | Permissões no servidor e preços/admin | Comprador, aduana, estoque; ACL-02, REC-02 | A | Negativas 403 e bloqueio UI; sem elevar papel |
| ID-03 | Usuário criar, editar, inativar e negar login | Admin; ADM-02 | A | Conta sintética inativa após recarga; e-mail inválido rejeitado antes |
| ID-04 | Senha nova, autorrevogação e expiração natural | Admin/outros | N | Não abrangidos pelos logins normais |
| NAV-01 | Menu, grupos, recolher, expandir e teclado | Admin; INV-01, EXE-03 | A | 17 destinos identificados; Enter no estoque após recolher |
| NAV-02 | Rotas secundárias e guardas | Todos; ACL-02 / inventário | A | Preços/import e URLs restritas negadas; não todas as combinações de papel × rota |
| EXE-01 | Executiva carregada e rótulos/recortes | Admin; EXE-01 / V-DASH | A | Exposição EUR de referência não rotulada como total AP |
| EXE-02 | Comercial, Controle, Executiva | Admin; EXE-02 | A | Três presets abertos e capturados; não todos os seus filtros |
| EXE-03 | Copiar, ordenar, ocultar visão e recarregar | Admin; EXE-02 | A | Cópia pessoal única; alterações persistem |
| EXE-04 | Restaurar/excluir visão e conflito de versão | Admin | N | Controles existentes, não acionados |
| EXE-05 | Prioridade → origem → Voltar | Admin; EXE-03 | A | Abriu processo; retorno ao dashboard |
| EXE-06 | Período customizado e ausência completa de FX | Admin | N | Cotação desatualizada real foi vista; ausência não foi simulada no painel |
| EST-01 | Consulta física/econômica atual | Admin; EST-01 / V-STOCK | A | Quantidades por unidade, cobertura, custo, venda e margem legíveis |
| EST-02 | Roupas OU Raquetes OU Bolas E Beach Tennis | Admin; EST-02 | A | Multi-seleção real; resumo e tabela coerentes |
| EST-03 | Agrupar por modelo/modalidade/tipo/sem grupo | Admin; EST-02 | A | População e totais não mudam |
| EST-04 | Exibir medidas e ordenar custo decrescente | Admin; EST-02 | A | SHOW26 primeiro; ligar/desligar margem não altera população |
| EST-05 | Remover Beach Tennis; BT + Padel | Admin; EST-02/04, apoio GET EST-03 | A | Consulta ampliada; IDs únicos no resultado multimodal |
| EST-06 | Salvar padrão pessoal, recarregar | Admin; EST-02 | A | Visão e configuração recuperadas no laboratório |
| EST-07 | Página 2, histórico, recarga e totais | Admin; EST-03 | A | 37 resultados; 25 por página; total independe da página |
| EST-08 | Produto → compra → composição → PDF | Admin; EST-02 | A | SHOW26, fonte real renderizada, área contextual única |
| EST-09 | Retorno por breadcrumb e foco | Admin; EST-02-return | F | Filtros/sort preservados; foco perdido com tabela implícita |
| EST-10 | Retorno Back com tabela explícita | Admin; EST-03 | A | Página 2, URL e foco stock-product-4 preservados |
| EST-11 | Vazio, erro 503 e recuperação | Admin; EST-03 | A | Não converte erro em zero; tentar novamente funcionou |
| EST-12 | Cobertura parcial, preço/custo ausentes | Admin; PRE-02, EST-03 | A | AUD26 sem custo/margem; FOREST e BALL50 sem preço |
| EST-13 | Todas as posições/localizações combinadas | Admin/estoque | N | Saldo doméstico e histórico vistos; combinação exaustiva não executada |
| CAT-01 | Lista comercial, atributos e variantes | Admin; CAT-01 | A | Consulta das variantes Heroes; não equivale a editor de taxonomia |
| CAT-02 | Criar SKU e editar classificação/unidade | Comprador; COM-02, CAT-02 | A | Cadastro e unidade UN persistidos |
| CAT-03 | Cancelar formulário de produto | Comprador; CAT-03 | F | Rascunho reaparece ao reeditar e pode ser salvo inadvertidamente |
| CAT-04 | Selecionar dois e comparar diferenças | Admin; CAT-04 | A | SHOW26 × ARION26; filtro de diferenças; retorno à lista |
| CAT-05 | Mídia, EAN, enriquecimento e inativação produto | Comprador | N | Controles/campos existentes não exercitados nesta rodada |
| CAT-06 | Editor completo da taxonomia comercial | Admin | NA | Não há destino de manutenção completo equivalente; não tratado como bug de tela inexistente |
| FOR-01 | Criar fornecedor no pedido | Comprador; COM-02 | A | Fornecedor 5, sintético |
| FOR-02 | Editar, inativar, reativar e recarregar | Comprador; FOR-02 | A | País/código persistem; terminou ativo |
| PRE-01 | Criar preço individual e substituir vigente | Admin; PRE-02 | A | 1.000 → 1.100 BRL/UN; histórico preservado |
| PRE-02 | Encerrar hoje e preço futuro | Admin; PRE-02 | A | Atual 1.100 até 23/10; 1.200 desde 24/10 |
| PRE-03 | Intervalo inválido, sobreposição, histórico/Escape | Admin; PRE-02 | A | Erros específicos; sem criar preço inválido |
| PRE-04 | CSV erros de SKU/unidade, corrigir, prévia | Admin; PRE-03 | A | Arquivo inválido bloqueado; prévia correta explícita |
| PRE-05 | CSV confirmar e repetir após resposta perdida | Admin; PRE-03 | A | Um único preço na tabela auxiliar 5 |
| PRE-06 | CSV substituição em lote, grande volume/multimoeda | Admin | N | Criação foi testada; não extrapolar à substituição em lote |
| PRE-07 | Manutenção completa de tabelas/canais | Admin | N | Seleção de tabelas existentes testada; CRUD de tabela não |
| COM-01 | Lista, novo pedido e confirmação | Comprador; COM-02 | A | AUD26-E2E, 20 UN × EUR 100 |
| COM-02 | Cockpit/comercial, docs e origem | Comprador/admin; COM-02, FAT-02, tour | A | Reabertura com mesmos registros |
| COM-03 | Encerrar/reabrir sem quitar | Comprador; COM-03 | A | Aviso EUR 1.500; obrigação não alterada |
| COM-04 | Cancelar pedido, compromisso não vinculado e cronograma | Comprador | N | Fluxos existentes fora da história exercitada |
| FAT-01 | Criar fatura, linhas, termos, PDF, emitir | Comprador; FAT-02 | A | EUR 2.000; parcela 23/11/2026; reload persistido |
| FAT-02 | PDF por Abrir e PDF embutido | Comprador/admin; DOC-01, EST-02, tour | A | HTTP PDF real; renderização embutida comprovada; visualizador nativo externo não certificado |
| FAT-03 | Várias condições, descontos e cancelamento emitida | Comprador | N | Só NONE e parcela percentual 100% testados pela UI |
| FAT-04 | Trinta parcelas para volume | Admin; FIN-05 | NA | Preparação por API, não aprovação de edição UI de 30 parcelas |
| FIN-01 | AP resumo BRL/EUR, vencidas, filtro, drawer/Escape | Admin; FIN-03 | A | EUR 2.000 vencidos; dados e filtro persistem após reload |
| FIN-02 | AP soma dos saldos versus obrigações | Admin; FIN-03, SQL | A | Saldo aberto por moeda reconciliado |
| FIN-03 | Navegar além de 50 obrigações | Admin; FIN-05 | F | Não existe controle UI; servidor devolve restante via offset |
| FIN-04 | Por alocar independente da página | Admin; FIN-06 | F | EUR 2.650 → EUR 2.550, mesmo filtro |
| FIN-05 | Registrar pagamento sem alocação | Comprador; FIN-02 | A | Obrigação continua EUR 2.000 |
| FIN-06 | Alocar parcialmente e recarregar | Comprador; FIN-02 | A | EUR 500 alocados; saldo EUR 1.500 |
| FIN-07 | Adiantamento, crédito, estorno e dupla alocação | Comprador | N | Não repetidos nesta auditoria; histórico não substitui execução nova |
| FX-01 | Planejado inicial por obrigação | Admin; FX-01/CUS-02 | A | Taxa 6; saldo EUR 1.500 → BRL 9.000 planejados |
| FX-02 | Realizado bancário e nova referência online | Comprador/admin | N | Pagamento não teve FX bancário; integração externa offline |
| LOG-01 | Prestadores e lista de embarques | Admin; LOG-01/02 | A | Consulta carregada; não CRUD do prestador |
| LOG-02 | Criar, selecionar item e exceder residual | Admin; LOG-03/04 | A | 21 rejeitado; 20 aceito; recarga |
| LOG-03 | Reservar, trânsito, chegada | Admin; LOG-04 | A | Eventos UI; ARRIVED persistido |
| LOG-04 | Packing, lotes de volumes, referências/documentos | Admin | N | Implementados, mas não exercitados além de leitura do roteiro; I-01 histórico não resolvido |
| ADU-01 | Criar processo e vínculos | Aduana; ADU-02 | A | Fatura/embarque vinculados por IDs informados pelo auditor |
| ADU-02 | Alocar itens de fatura na história principal | Aduana; ADU-03 | B | Passo omitido por espera incorreta do runner; processo submetido depois; não alegar execução |
| ADU-03 | Alocar embarque, submeter, Doganale e documento | Aduana; ADU-03 | A | 20 UN, versão ativa; sem inventar origem por ingestão |
| ADU-04 | Numerário manual e obrigação BRL | Aduana; ADU-03 | A | 300 BRL de II; confirmado, obrigação 33 |
| ADU-05 | Liberação: excesso e confirmação | Aduana; ADU-03 | A | 21 bloqueado; 20 liberado |
| ADU-06 | Retificação, divergência, cancelamento e reversão | Aduana | N | Não executados; tela identifica reversão indisponível quando recebido |
| ADU-07 | Mesma fatura em outro processo | Admin; CUS-03 | A | 409 invoice_already_linked; nenhum segundo recebimento |
| REC-01 | Fila própria, elegível e excesso | Estoque; REC-02 | A | Estoquista não precisa abrir Aduana |
| REC-02 | Receber parcial, persistência, saldo | Estoque; REC-02 | A | 8 recebidos; 12 pendentes; saldo 8 |
| REC-03 | Completar e repetir após resposta perdida | Estoque; REC-02 | A | +12 uma única vez; total 20, pendente zero |
| REC-04 | Duas sessões disputam residual | Estoque × estoque; REC-03 | A | Auxiliar QA-RCV-RACE: +2 apenas uma vez; outra tentativa bloqueada |
| REC-05 | Origem inelegível e ACL servidor | Estoque; REC-03/ACL-02 | A | Sem ação de receber não liberado; dados restritos 403 |
| REC-06 | Recebimento legado de administrador | Admin | N | Tela carregada no inventário/tour; nova escrita pelo painel legado não repetida |
| MOV-01 | Movimentos e posição SKU | Estoque/admin; REC-02, MOV-01 | A | Dois movimentos 8+12 e saldo atual conferidos |
| MOV-02 | Ajuste, transferência/reclassificação, localizações | Estoque/admin | NA | Comandos de domínio/API existentes; sem entrada UI de escrita identificada equivalente; lacuna de acesso, não teste aprovado |
| CUS-01 | Lista, fontes, versão e composição existentes | Admin; EST-02, CUS-01, tour | A | SHOW26 usa versões por compra, base não recebida |
| CUS-02 | Recalcular/publicar custo incompleto | Admin; CUS-02 | F | 0 publicado / COMPLETE / missing_basis / NO_INVOICE |
| CUS-03 | Natureza da taxa apresentada | Admin; CUS-02 | F | Planejada 6 anunciada como documental |
| CUS-04 | Custo da cadeia nova refletido no estoque | Admin; PRE-02/SQL | B | Origem incompleta; custo/margem permanecem ausentes corretamente |
| CUS-05 | Controle positivo de nova composição completa | Admin; CUS-03 | B | Fatura vinculada exclusivamente ao processo 11; tentativa em 12 negada, não foi criada outra compra para contornar |
| CUS-06 | Despesa, nova revisão, comparação, conciliação | Admin/comprador | N | Controles inventariados, sem nova escrita; não repetir despesas históricas inadvertidamente |
| ING-01 | Fila/intake e arquivo inválido | Comprador; ING-02 | A | TXT rejeitado; UX do status contraditória, ver U-05 |
| ING-02 | PDF genérico e workspace | Comprador/admin; ING-02/03 | A | PDF abriu; sem linhas extraídas; commit corretamente bloqueado |
| ING-03 | Pôr em espera, recarregar e liberar | Admin; ING-03 | A | Persistiu espera; voltou à fila sem gerar pedido |
| ING-04 | Ingestão ponta a ponta de template suportado | Comprador | N | PDF genérico não demonstra os parsers Ordine/Fattura/Packing/Doganale/Numerário/XLSX |
| ING-05 | Dossiê, match, correção de linha, descarte e commit | Comprador/aduana | N | Não executados nesta rodada; não contar antigo J#3 como teste atual |
| DEM-01 | Oito etapas no ritmo normal | Admin; TOUR-01 | A | 405 s; telas/alvos carregados; zero writes de negócio |
| DEM-02 | Pausa/retomada, anterior/próximo, etapa, saída/manual | Admin; TOUR-02 | A | Runner de controles executado nesta rodada |
| DEM-03 | Resize, atraso, alvo ausente, manifesto inválido | Admin; TOUR-03/04 | A | Interrompe/explica/cancela; não disputa navegação manual |
| UX-01 | Quatro viewports e legibilidade crítica | Admin; VIS-01 | A | Avaliação do agente e geometria; ressalvas em §7 |
| UX-02 | Laptop físico / compreensão por executivo | Apresentador | B | Não houve controle nativo nem avaliação humana |
| REP-01 | Exportação gerencial geral/busca global | — | NA | Não identificadas como capacidades implementadas gerais; PDFs específicos não equivalem a exportação global |

### Rotas e alcance fora do menu

O menu contém: Visão geral, Estoque atual, Recebimentos, Produtos, Contas a pagar, Operações; grupos Compras e documentos (Pedidos, Faturas, Conferir documentos), Financeiro (Pagamentos, Câmbio por obrigação, Custos), Logística e histórico (Embarques, Movimentos, Prestadores) e Cadastros (Fornecedores, Usuários).

Destinos secundários implementados: `/catalog/products/new`, `/:id`, `/:id/edit`, `/compare`; `/catalog/prices/import`; fornecedor e usuário novo/detalhe; `/orders/new`, `/:id`, `/:id/commercial`; fatura detalhe; `/payables/:id/fx`; pagamento novo/detalhe; embarque novo/detalhe; processo novo/detalhe e `/customs/funding/:id` (redirecionamento); `/inventory/sku/:id`; ingestão workspace; custo detalhe/comparação. Vários componentes usam drawers/abas, não rotas adicionais.

Importação de preços é acessível pelo catálogo, e o preço individual dentro do produto, não diretamente pelo menu. Movimentos/localizações têm consultas; comandos de ajuste/reclassificação não tiveram uma entrada operacional de escrita encontrada. Isso é uma lacuna concreta de descobrimento/acesso a capacidades existentes, não autorização para implementar uma nova tela nesta rodada.

O inventário inicial fez fallback por URL em algumas páginas porque grupos de menu se recolheram entre navegações. `INV-01.json` indica individualmente “clique no menu” ou “URL direta”. Isso **não prova** que todo destino acessado por URL esteja ausente do menu; os 17 links foram encontrados antes. Nos caminhos que exigiram IDs técnicos — especialmente Aduana — essa necessidade é explicitada como fricção.

## 4. Perguntas do executivo e percursos realizados

### O que há em estoque, quanto vale e onde está o capital?

**Abri** Estoque atual pelo menu. **Vi** padrão Beach Tennis e posição disponível. **Fiz** Tipo de item → marquei Roupas, Raquetes e Bolas (abrir, três marcações, fechar); alternei Agrupar por quatro opções e Exibir margem; ordenei custo decrescente. **Resultado:** mesma população nos agrupamentos/medidas; SHOW26 no topo do capital. Capturas EST-02_01 e EST-02_02.

No momento da leitura combinada após a história AUD26: **26 SKUs; 402 UN, 22 CX e 19 PCT; R$ 242.395,01 de custo disponível; R$ 587.399,10 de venda potencial; margem 59,7%**, calculada somente em 23 SKUs com custo e preço. Custo cobria 25/26 e preço 24/26. Remover BT ampliou para 28 SKUs e R$ 265.223,23 de custo. Unidades diferentes não foram somadas em uma quantidade fictícia única.

**Funciona:** sim. **Correto no recorte:** totais invariantes e aritmética SHOW26 conferidos; a política PEPS gerencial continua estimativa, não aprovação contábil. **Compreensível:** boa comparação na lista, mas “tipo” é uma projeção comercial do Catalog e não idêntico ao rótulo “Categoria” da página de produtos. O custo da compra e custo remanescente exigem atenção ao contexto.

### Qual margem é essa?

Margem potencial, não realizada, sobre venda elegível: `(venda comparável − custo comparável) / venda comparável`. Não é média simples dos percentuais. No recorte BT+Padel, o apoio técnico encontrou 31 IDs únicos; custo comparável R$ 272.450,47 e venda comparável R$ 674.363,20, resultando aproximadamente 59,60%. Total de venda do recorte R$ 696.363,20 inclui AUD26 sem custo e **não** deve ser usado como denominador daquela margem. A UI indica população parcial em uma linha curta. A fórmula foi conferida fora do calculador da aplicação.

### Quanto está vencido e quanto vence?

**Abri** Contas a pagar. **Vi** BRL e EUR separados, vencidos e próximos sete dias. **Cliquei** no vencido EUR, abri obrigação e usei Escape; recarreguei. **Resultado:** obrigação A EUR 2.000 permaneceu vencida, filtro preservado e drawer fechou. Antes do numerário AUD26, próximos sete dias eram BRL 17.600 e EUR 1.130,11; próximos 30 dias EUR 10.304,63. As datas de cada obrigação sustentam esses recortes (FIN-03).

Após volume auxiliar, o acesso a todos os registros falhou: 59 abertos / só 50 mostrados; sem próxima página. Por URL técnica `?offset=50`, os saldos globais continuaram BRL 17.933 / EUR 44.238,43, mas “Por alocar · fila completa” caiu 100 EUR. **Funciona parcialmente, números de saldo corretos, consulta completa e resumo de pagamentos não confiáveis.**

### O que está pendente e qual a próxima ação?

**Abri** Executiva. **Vi** “Conferir declaração” com uma origem. **Cliquei** Consultar origem e Voltar; depois naveguei Recebimentos como estoque. **Resultado:** prioridade chega ao processo e a fila própria distingue liberado/pendente. A Aduana ainda exige IDs e tem longos formulários; o caminho não é autoexplicativo para um executivo sem ajuda. Não foram somadas exceções operacionais e pendências financeiras como se fossem uma contagem única.

### Como comprovar a origem e retornar?

**Abri** SHOW26 (um clique na linha). **Vi** compras e versões. **Cliquei** compra → composição → documento real → Estoque atual (quatro ações após abrir o produto). **Resultado:** leitor PDF embutido carregado; mesma seleção e ordenação no retorno, mas foco vazio em vez de `stock-product-3`. Com tabela explícita e Back na página 2, foco retornou a `stock-product-4`. O número de cliques é do roteiro executado, **não** tempo de usabilidade humana.

## 5. História integrada AUD26 e reconciliação

### O que foi feito, em ordem

1. **Comprador, pedido:** Abri Pedidos → Novo. Vi formulário; preenchi fornecedor sintético e SKU AUD26-RAQ, 20 UN × EUR 100. Cliquei confirmar e recarreguei. Resultado: pedido 14 `AUD26-E2E`, total EUR 2.000.
2. **Comprador, fatura/documento:** Abri comercial → nova fatura 14 `AUD26-FAT`; defini desconto NONE, parcela 100% para 23/11/2026 e anexei PDF correspondente. Conferi modal e emiti. Após recarga: obrigação 32 de EUR 2.000. Documento é sintético válido criado para o teste; **pedido não nasceu de ingestão**.
3. **Comprador, tesouraria:** Abri Pagamentos → Novo, EUR 500 com comprovante sintético. Vi obrigação ainda EUR 2.000 antes de alocar. Aloquei EUR 500 pelo modal. Após recarga: pagamento 10, alocação 11, saldo EUR 1.500. O simples registro de pagamento não liquidou nada.
4. **Admin, logística:** Abri Novo embarque 11; procurei AUD26-E2E. Tentei 21, recebi bloqueio; salvei 20. Registrei reserva, trânsito e chegada pela UI, com data. ARRIVED persistiu. Packing e volumes não foram preenchidos; não declarar esse trecho documental testado.
5. **Aduana:** Criei processo 11 `AUD26-DI`; vinculei fatura/embarque por IDs. Aloquei o embarque, submeti, criei/ativei Doganale com 20 UN e anexei declaração. Criei numerário manual BRL 300 de II, base CIF BRL 12.000 e confirmei; nasceu obrigação 33 BRL 300. Tentei liberar 21 (bloqueado), confirmei 20.
6. **Estoquista:** Abri Recebimentos, filtrei AUD26 e abri item 43. Conferi 8 UN para local doméstico e confirmei. Recarreguei: 8 recebidos, 12 pendentes. Confirmei os 12 restantes com resposta artificialmente perdida; repeti a mesma confirmação. Resultado persistido: apenas dois movimentos, 8 e 12, saldo 20, pendente zero.
7. **Admin, custo:** Planejei câmbio 6 na obrigação 32. Iniciei caso 9, recalculei ESTIMATED e publiquei v1 (id 12). **Resultado incorreto:** BRL zero com cobertura completa. A alocação de itens de fatura havia sido omitida no runner (ver abaixo); esse estado deveria ser incompleto, não apresentado como custo completo zero.
8. **Admin, preços:** Cadastrei BRL 1.000/UN, substituí por 1.100, encerrei a vigência em 23/10 e cadastrei 1.200 para 24/10. Erros de intervalo e sobreposição foram tentados antes e não gravados. Após recarga, venda do saldo = 20 × 1.100 = BRL 22.000. Custo e margem ficaram ausentes, coerentemente com a falta de fonte elegível.
9. **Comprador, fechamento comercial:** Encerrei e reabri pedido com motivo. O aviso mostrou EUR 1.500 em aberto; o saldo não mudou.

### Limite da cadeia e transparência do runner

A fatura estava **vinculada**, mas `invoice_item_allocations` continuou vazio. A automação verificou existência do botão antes de a consulta terminar, pulou essa ação e seguiu. Isso é uma falha de cobertura do runner, **não prova de que o botão de alocação falhou**. O estado persistido é, porém, uma entrada real incompleta aceita pelo sistema: liberação e recebimento via item do embarque ocorreram, e a publicação do custo não impediu nem qualificou adequadamente a ausência de base.

Depois de descobrir isso, não alterei dados por SQL para fazer a cadeia parecer aprovada. Criei pela UI um processo auxiliar 12 `AUD26-CUSTO-CONTROLE`, mas a tentativa de reutilizar a fatura retornou corretamente `invoice_already_linked`. Ficou rascunho vazio. O controle positivo de custo completo nessa história permanece **bloqueado/não demonstrado**, e o achado é sobre a aceitação/apresentação do estado incompleto. O esperado de BRL 12.300 é **condicional à alocação completa**, não uma cobrança para somar valores de fontes não elegíveis.

### Esperado versus observado (aritmética independente)

| Verificação | Esperado | Observado | Conclusão |
|---|---|---|---|
| Compra/fatura AUD26 | 20 × EUR 100 = EUR 2.000 | 20 / 2.000 | Reconciliado |
| Pagamento sem alocação | Obrigação continua EUR 2.000 | 2.000 antes de alocar | Reconciliado |
| Liquidação parcial | 2.000 − 500 = EUR 1.500 | 1.500 após reload; uma alocação | Reconciliado |
| Liberação e estoque | 20 liberadas; 8 + 12 recebidas | Movimentos 45/46, local 2, total 20 | Reconciliado |
| Resposta perdida | Repetir não cria terceiro recebimento | Dois movimentos no SKU | Reconciliado |
| Concorrência auxiliar | Pendente 2; duas tentativas 2; só uma vence | QA-RCV-RACE passou de 6 a 8 recebidos | Reconciliado; só clone |
| Custo com linha não alocada | Ausência/base incompleta; não custo completo zero | Publicado 0 / COMPLETE; II 300 excluído | Falhou |
| Custo se base completa | 2.000 × 6 + 300 = 12.300; 615/UN | Não executado com base completa | Não declarar divergência aritmética de 12.300 nessa população |
| Preço vigente | 1.100/UN em 23/10 | Preço 42; antigo 41 cancelado, futuro 43 | Reconciliado |
| Venda AUD26 | 20 × 1.100 = 22.000 | 22.000; custo/margem ausentes | Reconciliado |
| CSV auxiliar | Um preço 1.500/UN na tabela 5 | Registro 44, mesmo após repetição | Reconciliado; tabela 1 não alterada pelo CSV |
| SHOW26 quantidade | 12 + 8 + 30 − 8 = 42 | 42 em ambos ambientes | Preservado |
| SHOW26 custo disponível | 12 × 1.200 + 30 × 1.350 = 54.900 | 54.900 na UI | Preservado; PEPS gerencial estimado |
| SHOW26 venda/margem | 42 × 3.289 = 138.138; (138.138 − 54.900)/138.138 = 60,2571% | 138.138 / 60,3% | Reconciliado |
| Obrigação A | EUR 2.000 | 2.000 apresentação/lab | Preservada |

Fontes SHOW26 consultadas por SQL: recebimentos da compra A 20 UN, custo revisado v1 = 18.000 mercadoria + 2.000 frete + 3.000 tributos + 1.000 despesas = 24.000 (1.200/UN); compra B 30 UN, 30.600 + 3.000 + 5.400 + 1.500 = 40.500 (1.350/UN). Saída sem lote de 8 consome a origem mais antiga conforme política gerencial vigente; restam 12 A + 30 B. Não multiplicamos todo o saldo pelo custo da última compra. Não se aprovou aqui política contábil definitiva.

### Saldos finais e efeitos da auditoria

Apresentação: **BRL 17.633,00 e EUR 42.708,43** de saldo não cancelado. Laboratório final: **BRL 17.933,00 e EUR 44.238,43**. Deltas explicados: +300 BRL Numerário; +2.000 EUR fatura AUD26 −500 EUR alocação +30 EUR fixture de paginação. SQL somou `amount − allocations` e comparou com o saldo persistido, por moeda; sem função financeira da aplicação.

FIN-03 aconteceu antes de confirmar o Numerário: seu BRL 17.633 é histórico **desta mesma rodada**, não o saldo final 17.933. O tour iniciou antes de a obrigação AUD26 entrar no recorte: exposição EUR 41.940,43 (BRL 237.273,79 à referência 5,6574). Depois viu-se EUR 43.440,43 (BRL 245.759,89). Não forçar igualdade com AP de todos os vencimentos: exposição e agenda têm recortes próprios. A exposição não é consolidado de todas as moedas.

Fixture **AUD26-PAGE**: pedido 15 e fatura 15, 1 UN × EUR 30, 30 parcelas de EUR 1 em dezembro, **preparados por API pública**, emissão sem documento explicitamente marcada para teste de volume. Não há pagamento, embarque ou estoque adicional para ela. Elevou AP para 63 obrigações totais, 59 abertas; permitiu comprovar truncamento UI real com limite padrão 50. Não constitui teste UI da emissão de 30 parcelas.

Banco final do laboratório versus apresentação: produtos 43/42; pedidos 15/13; faturas 15/13; obrigações 63/31; pagamentos 10/9; alocações 11/10; embarques 11/10; processos 12/10; liberações 15/14; recebimentos 16/13; movimentos 47/44; casos de custo 9/8; versões 12/11; preços 44/40; documentos 63/60. Acrescentados ainda usuário sintético inativo, fornecedor ativo, preferências pessoais e intake/rascunho de ingestão. Não confundir IDs sequenciais com contagem: alguns IDs anteriores já tinham lacunas.

## 6. Achados funcionais priorizados

### F-01 — Alto: custo zero publicado apesar da base ausente

**Reprodução:** processo com fatura vinculada, só item do embarque alocado; liberar/receber; custo ESTIMATED → Recalcular → Publicar. **Esperado:** cobertura incompleta/impedimento ou indicação explícita de ausência, nunca “Completa” com mercadoria zero. **Observado:** caso 9/v12 PUBLISHED, `partial_coverage=false`, `NO_INVOICE`, II BRL 300 excluído por `missing_basis`, total 0. A UI também anuncia tributos incluídos, enquanto a lista os marca excluídos. **Impacto:** gestor pode interpretar aquisição sem custo e confiar em cobertura inexistente. **Recomendação:** corrigir conjuntamente cobertura, elegibilidade de publicação e apresentação de linhas sem base; caracterizar diferenças ESTIMATED/REVISED sem inventar rateio. Conferir invariantes do lado servidor. Não corrigido nesta rodada.

Evidência visual: CUS-02_02; JSON CUS-02 e reconciliação. Localização técnica a investigar: `costing/synthesis.py`, `coverage.py`, `fx_alloc.py`, `commands.py`; a publicação considera `blocks_publish`, diferente do simples rótulo BLOCKING. Isso delimita a investigação, não substitui teste da futura correção.

![CUS-02 — custo incompleto publicado](prints/CUS-02_02_publicado.png)

### F-02 — Alto: taxa planejada chamada de documental

**Reprodução:** obrigação 32 com planejamento inicial 6; Numerário manual sem taxa documental persistida; custo estimado. **Observado:** “Câmbio documental da importação (Numerário). Taxa documental 6,000000”, snapshot `fx.kind=documental`, enquanto a fonte da fatura traz `initial_rate/current_rate=6`, sem realizado. O PDF sintético da declaração menciona 6, mas foi apenas anexado, não extraído/vinculado como fato cambial do Numerário; isso não torna a origem do planejamento documental. **Impacto:** natureza econômica incorreta, mesmo com aviso “não bancário”. **Recomendação:** transportar a proveniência correta de cada taxa até o rótulo e preservar estado ausente. Não renomear só na UI sem confirmar o contrato. Evidências CUS-02, FX-01.

### F-03 — Alto: obrigações fora da primeira página sem entrada UI

**Reprodução:** abrir `/payables` com 59 obrigações abertas, rolar até o fim. **Observado:** 50 linhas; resumo 1–50 de 59; nenhum botão/link de paginação. `/payables?offset=50` revela o resto. **Impacto:** executivo não consegue consultar toda a fila pelas ações disponíveis. **Recomendação:** controles de paginação com preservação de filtros, resumo global e retorno/foco. Verificar outras filas que usam apenas `PaginationSummary`. Fonte confirmada: `ApQueuePage.tsx` usa resumo sem callbacks de avanço. API dispõe de offset.

![FIN-05 — final da fila sem acesso à próxima página](prints/FIN-05_01_fila_sem_paginacao.png)

### F-04 — Alto: pagamentos disponíveis dependem da página

**Reprodução:** mesmo filtro de AP, alterar apenas offset 0 → 50. **Esperado:** “fila completa” invariável. **Observado UI:** EUR 2.650 → 2.550; saldos BRL 17.933/EUR 44.238,43 invariáveis. **Causa delimitada pelo código:** `reporting/queries.py` chama `_unallocated_candidates(db, enriched)` sobre linhas já paginadas, restringindo fornecedores/candidatos. **Impacto:** decisão de alocação baseada em resumo incompleto. **Recomendação:** agregar sobre a população filtrada completa com ACL, mantendo candidatos da página separados se necessários; testar também paginação de candidatos (há limite interno 50). Não é prova de erro no saldo de obrigação ou na alocação persistida.

![FIN-06 página 1 — por alocar 2.650](prints/FIN-06_01_resumo_pagina1.png)

![FIN-06 página 2 — por alocar 2.550](prints/FIN-06_02_resumo_pagina2.png)

### F-05 — Médio: cancelamento de edição não descarta o rascunho

**Reprodução:** produto → Editar → alterar nome → Cancelar → Editar novamente. **Observado:** nome alterado reaparece; salvar unidade/classificação grava junto esse nome. Na primeira passagem gravou “NÃO SALVAR”; na reprodução isolada reapareceu “AUD26 NÃO SALVAR CANCELADO”. Nome original foi restaurado pela UI e confirmado nas leituras posteriores. **Impacto:** gravação inadvertida de alteração cancelada. **Recomendação:** redefinir estado de edição a partir do persistido ao cancelar/entrar; testar campos adicionais. Evidência CAT-03. Não é falha de persistência do servidor.

![CAT-03 — rascunho reaparece após cancelar](prints/CAT-03_01_cancelamento_rascunho_retido.png)

### F-06 — Médio: retorno perde foco em contexto normalizado

**Reprodução:** visão salva com `price_list_id=` → SHOW26 → compra → composição → PDF → Estoque atual. **Observado:** retorno substitui parâmetro por `1`; foco fica vazio, não na linha aberta. Filtros, ordenação e números sobreviveram. **Controle:** `price_list_id=1` explícito, página 2 e Back preservaram URL/foco. **Recomendação:** chave canônica do contexto e restauração de foco/posição compatível com parâmetros default. Evidência EST-02-return/EST-03 e capturas EST-02_07, EST-02_04 e EST-02_05. Não afirmar perda de scroll sem medição específica.

## 7. UI/UX: avaliação do agente, por tarefa

### Densidade e viewport

| Tela / linhas totalmente visíveis | 1366×681 | 1366×768 | 1920×1080 | 1024×768 |
|---|---:|---:|---:|---:|
| Estoque atual | 5 | 7 | 13 | 4 |
| Contas a pagar | 5 | 7 | 12 | 7 |
| Recebimentos | 6 | 7 | 11 | 6 |

Medição: linhas `tbody` inteiras dentro do viewport, sem rolagem inicial; `devicePixelRatio=1`, `visualViewport.scale=1`, zoom 100%. A composição do estoque estava recolhida, preservando preferência de densidade. Não houve overflow horizontal do documento nas seis telas críticas; tabelas podem ter seu próprio scroll, especialmente em 1024. Isso não equivale a aprovação visual automática.

**U-01 · Médio — gestão de preços escondida abaixo do cadastro.** No produto AUD26, a primeira linha da tabela de preços começa em y≈1.402 px no laptop; zero linhas de preço na primeira dobra inclusive Full HD. Para mudar preço, atravessa identificação e vários atributos vazios antes de chegar à ação. Recomendação: entrada contextual de preço/âncora visível sem apagar cadastro. Importação CSV, em contraste, cabe com prévia e confirmação em 1366×681. Evidências V-PRICE e PRE-03_02.

**U-02 · Alto — Aduana depende de IDs e vocabulário de implementação.** Vincular fatura e embarque exigiu os IDs que o auditor obteve da URL/consultas. Perfil aduana não tem as mesmas leituras comerciais do admin, portanto instruções “abra a fatura e copie o ID” não são uma solução geral. A página mostra “qty”, “payee”, “Doganale”, rascunho/v1 e avisos longos; a ação importante fica depois de vários blocos. Recomendação: revisão delimitada de escolha/origem operacional e linguagem, preservando ACL e precisão aduaneira. Não construir picker nesta auditoria. Evidências ADU-02, ADU-03 e tour etapa 6.

**U-03 · Médio — catálogo dá mais peso à incompletude que à tarefa.** Todos os 43 produtos aparecem incompletos, embora muitos sejam utilizáveis para venda/estoque; linhas repetem “Sem foto” e várias pendências. Isso reduz a distinção entre falta operacional que bloqueia e enriquecimento opcional. Recomendação: separar impedimento de qualidade de cadastro, sem ocultar unidade/custo/preço ausentes. CAT-01.

**U-04 · Médio — termos internos e números crus em custo/comparação.** A lista de custos apresenta valores como `7080.0000`; detalhe contém `COMPLETE`, `missing_basis`, `BLOCKING`, `declared_total`, além de parágrafos extensos. Comparar produtos mostra “Placeholder” e “sem motor de similaridade”. Isso não ajuda a decidir produto/capital. Recomendação: moeda formatada, qualificador econômico preciso, descrição acionável em vez do enum, detalhes técnicos sob demanda. CUS-01/CUS-02/CAT-04. **Não esconder** cobertura, taxa, versão, base de quantidade ou motivo de bloqueio.

**U-05 · Médio — intake mistura pronto e rejeitado.** Arquivo TXT inválido exibe “Pronto · Rejeitado” e “Extrair dados”; PDF genérico oferece extração sem escolha clara de parser e abre Ordine vazio. Commit ficou bloqueado corretamente, mas o status de ingestão é ambíguo. Recomendação: separar upload concluído de extração válida, orientar tipo compatível e próxima ação. Não alegar parser de fornecedor quebrado a partir de PDF genérico. ING-02/03.

**U-06 · Baixo — preferências de ensaio acumuladas.** Seletor de estoque contém várias “Executiva E2E [timestamp]” herdadas. A visão AUD26 foi salva sem apagar preferências anteriores. É poluição de massa de teste, não evidência de corrupção. Recomendação: gestão explícita de visões e curadoria da demonstração em rodada autorizada, sem apagar automaticamente o padrão de usuários.

**U-07 · Médio — operação de ajuste de estoque sem entrada UI encontrada.** O papel estoque possui `inventory:adjust`, e existem comandos/rotas de ajuste e reclassificação. Navegar Estoque, Recebimentos e Movimentos não ofereceu uma ação equivalente de escrita. Assim, a funcionalidade de domínio não foi testada pela UI e está classificada como somente API nesse alcance. Impacto: correção operacional autorizada depende de instrução técnica. Recomendação: advisor definir se essa operação deve ser disponibilizada ao papel, com origem/motivo/auditoria e validações existentes; não inferir necessidade de conceder novas permissões. Evidência: inventário MOV-01/REC-01 e matriz de permissões, sem inventar uma tela não implementada.

**U-08 · Baixo — comparação de catálogo não preserva seleção.** Marquei SHOW26 e ARION26, comparei e cliquei Voltar à lista. A lista voltou com zero caixas selecionadas (`CAT-04.json`). Repetir/ajustar a comparação exige selecionar os produtos de novo. Recomendação: preservar seleção e contexto de origem, distinguindo isso do defeito de foco no estoque. A comparação em si funcionou.

**U-09 · Médio — contexto mínimo prejudicado nas fronteiras de permissão.** Depois de receber como estoque, “Ver saldo” chega à página que diz somente “Produto 43”, sem nome/SKU/unidade junto da quantidade20: o enriquecimento tenta `/api/products/43`, corretamente negado ao papel sem Catalog. Como aduana, a própria página autorizada do processo mostra um bloco vermelho “Permissão insuficiente” para recebimento, apesar de a liberação ter dado certo. Recomendações: fornecer identificação mínima pelo contrato Inventory já autorizado e não montar painel de ação que o papel não pode usar; **não ampliar ACL** para resolver apresentação. Evidências REC-02_07, ADU-03_02 e FINAL-READ. O servidor preservou a segurança; a UX ainda não explica bem essas fronteiras.

**Pontos positivos observados:** Estoque e Recebimentos imediatamente encontráveis; quadro de estoque alinha quantidade/custo/preço/venda/margem; resumos financeiros separam BRL/EUR; marcação de cotação desatualizada é visível; importação CSV mostra rejeições por linha e confirmação com motivo; PDF contextual não empilha uma segunda janela sobre a composição; foco visível em campos, Escape no drawer/histórico e navegação por teclado funcionaram nos casos exercitados.

**Limites de acessibilidade:** não houve auditoria completa WCAG, leitor de tela nem medição exaustiva de contraste. Quatro viewports não certificam escala do sistema operacional, brilho, DPI físico ou legibilidade humana. Em 1024, descrições longas quebram em mais linhas e algumas colunas financeiras demandam scroll interno; não reduzir fontes globalmente como compensação.

## 8. Demonstração guiada

Novo ensaio, não reaproveitamento histórico: 50 s por etapa, **405 s totais**. Marcas observadas: dashboard 2s; documento do pedido 52s; fatura 103s; pagamento 153s; embarque 203s; aduana 254s; estoque 304s; custo ao final. Intervalos incluem espera por dados/rota. `evidencias/tour-50s-itinerary.json` contém as oito leituras e `writes: []`.

Os oito PNGs `tour-50s-1` a `8` pertencem ao laboratório 8094, admin, 1366×681, escala 1, mesmo build servido. Painel compacto e destaque acompanharam as telas sem sobrepor os valores-alvo nas capturas inspecionadas. Documentação e fatura mostram os mesmos registros Heroes; etapa de estoque mostra 42 UN / R$ 54.900 / R$ 138.138, e etapa de custo tem base da compra, não saldo agregado.

Controles exercitados em testes adicionais desta rodada: pausar/continuar, anterior/próximo, escolher etapa, navegação manual, Escape/sair, redimensionar, atraso no carregamento, alvo indisponível e manifesto alterado. Foram **três testes dirigidos**, aprovados em 29,6 s no total; essa duração **não** é um ensaio executivo. Alvo ausente gerou interrupção explicada (`tour-target-unavailable.png`); saída durante atraso não disparou navegação posterior. Não houve segunda execução integral cronometrada nesta auditoria.

Avaliação de ritmo feita pelo agente: 50 s permite ler o conteúdo curto e olhar o alvo, mas não comprova compreensão humana nem exploração espontânea por executivo. A tela aduaneira continua mais densa que a explicação, e exige cuidado no ensaio presencial. Cotação online não foi declarada disponível: provider offline, referência antiga explicitamente desatualizada. Ausência de atualização não impediu os capítulos.

## 9. Preservação, Git e estado final

### Proteção antes dos dados

Backup inicial recuperável, fora do Git: `C:\Users\ricar\Desktop\projetos\EPIC\backups\integrated-before-20261023-175820`. **1.554 arquivos** copiados e hashes conferidos: app/alembic/dist servido, storage, manifesto, launchers e WIP local. Dump da apresentação SHA-256 `7d15401a7b6bfe4f2b11792bfbd55f20117423be606d045f836f2b0f183f9d83`. `pg_restore` leu o arquivo; restauração efetiva para o novo cluster 5452 confirmou recuperação sem tocar 5451.

WIP histórico incluía muitos PNGs, documentos/protótipos e fixtures não publicados de rodadas anteriores. Não foram descartados nem enviados em bloco ao remoto público. O código da release já estava publicado e HEAD inicial era igual ao remoto; não se criou commit vazio. A proteção desses arquivos não revisados é o backup local completo, **não** uma alegação de novo checkpoint público do WIP inteiro. Ausência de cópia externa dos dados permanece pendência.

Backup final do laboratório, com anexos e dist: `C:\Users\ricar\Desktop\projetos\EPIC\backups\integrated-final-20261023-183441`; **83 arquivos** verificados; dump SHA-256 `33397180f05d33666e7160c5887f6c5cb8bbe317410e4b9bf449732dd35039e5`. Este dump foi integralmente lido por `pg_restore`; **não foi restaurado** sobre nenhum ambiente. Snapshot intermediário 18:31 preservado também; o de 18:34 inclui a fixture de paginação e é o final de dados de negócio.

### Recuperação e abertura

- Apresentação continua em **8082**, mesmo build/e48, sem AUD26. Não é necessário recuperar nem reconstruir para apresentar. Launcher existente, a partir do checkout: `powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-pre-demo-ceo/scripts/open-demo-presenter.ps1`. Não foi aberta/fechada janela do usuário nesta auditoria.
- Laboratório fica em **8094**, com resultados e falhas preservados para revisão. Runtime auxiliar `audit-integrated/runtime.py` exige 5452 e `data_directory` próprio; não executa seed/reset.
- Para recuperar: criar **novo** diretório/cluster PostgreSQL, restaurar o dump escolhido, copiar o storage correspondente e apontar a cópia do app/dist preservado para os novos caminhos/porta. Conferir identidade antes de iniciar. Nunca restaurar a massa AUD26 sobre a apresentação 5451 nem copiar apenas banco sem documentos.
- Código salvo no Git e backups locais de banco/anexos são proteções diferentes. Não há dump, cookie, senha ou ZIP enviado ao GitHub.

### Arquivos desta rodada

Versionáveis após revisão: este relatório; `ROADMAP_V2_EPIC.md` (estado factual/próxima ação, sem aceite); scripts `audit-integrated/{preserve.py,prepare-lab.ps1,runtime.py,inspect.mjs,documents.py,reconcile.py,final-snapshot.py,package.py}`; testes `v2/frontend/e2e/audit-*.spec.ts` específicos desta rodada. São auxiliares de auditoria, **não código de produto**. Os testes com escrita não devem ser executados cegamente em uma base já movimentada; possuem guardas e/ou retomadas explícitas, e as tentativas interrompidas estão qualificadas no relatório.

Locais não destinados ao remoto: staging/package, screenshots PNG, JSON de leituras completas, PDFs sintéticos de preparação, traces/logs com potencial de autenticação, dumps e ZIP. O pacote selecionado contém somente as capturas e reconciliações necessárias; logs de falha do runner que exibiam formulário de senha ficaram fora.

`INTEGRACAO_EXPERIENCIA_EPIC.md` anterior foi mantido como histórico da entrega de produto; este relatório é a avaliação atual. Blueprints não foram alterados: não houve decisão de domínio nem implementação. A violação arquitetural histórica ingestion→foundation, I-01 e a conferência física permanecem abertos; nenhum deles foi declarado corrigido por este teste.

### Governança

**Status da rodada: auditoria executada e empacotada; cobertura funcional PARCIAL.** Fechar o pacote de auditoria não encerra J#8 nem ratifica o sistema todo. Próxima ação recomendada: advisor priorizar F-01 a F-06, começando confiança do custo e integralidade/consistência da fila financeira; planejar reteste da cadeia com alocação explícita de fatura e das famílias de ingestão não exercitadas. Sem implementação automática nesta rodada.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-revisao-experiencia/AUDITORIA_E2E_UX_EXECUTIVA_EPIC.md; auxiliares de auditoria e testes identificados em §9.
- Evidence: pacote desta auditoria, prints/ e evidencias/ relativos ao relatório.
- Roadmap status: 0.5.157; B registra auditoria parcial, achados e schema/runtime reais; A mantém capacidades e barras, sem avanço/aceite.
- Next TODO: revisão do advisor sobre custo incompleto, AP/paginação e cancelamento/retorno; reteste delimitado e conferência física; políticas operacionais, I-01, offsite e arquitetura continuam pendentes.
- Return to advisor: exclusivamente AUDITORIA_E2E_UX_EXECUTIVA_EPIC_<AAAAMMDD-HHMM>.zip.
```

## 10. Evidências visuais e rastreabilidade

Todas as imagens são **capturas da aplicação real**, não protótipos, PNG originais sem mosaico ou redimensionamento. Perfil/rota/viewport e estado vêm nas legendas. Build comum: `receiving-stock-20261023.1`, fonte `e48f7c2`; endereço-base 8094; escala 100%/DPR1. As imagens registram momentos diferentes da sequência, não um snapshot simultâneo. Capturas de loading indevidas e falhas apenas de localizador foram excluídas da seleção.

Para revisar: extrair o ZIP mantendo as pastas, abrir este MD num leitor Markdown ou abrir cada PNG pelo link relativo. Toda a explicação está aqui; JSONs apenas sustentam os números. Não há dependência de outro relatório fora do ZIP.

<!-- GALLERY -->

<!-- GIT_CLOSURE -->
