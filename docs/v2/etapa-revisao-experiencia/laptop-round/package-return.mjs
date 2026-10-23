// Single self-contained advisor artifact. Inputs are verified local evidence, never business writes.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';import {execFileSync} from 'node:child_process';
const here=dirname(fileURLToPath(import.meta.url)),repo=resolve(here,'../../../..'),lab=resolve(repo,'../audit-lab/stock-executive-20261023/laptop');
const sha=b=>createHash('sha256').update(b).digest('hex'),json=p=>JSON.parse(readFileSync(resolve(lab,p),'utf8').replace(/^\uFEFF/,''));
const git=(...a)=>execFileSync('git',a,{cwd:repo,encoding:'utf8'}).trim();
const proof=json('release-proof-8082.json'),code=proof.build.source_commit,branch='feat/stock-executive-20261023';
if(code!=='36f1ea79a28e0347dc27b1f63d0d108248030d32'||proof.build.uncommitted_candidate)throw Error('Unverified served source');
const remote=git('ls-remote','origin','refs/heads/'+branch).split(/\s+/)[0];
if(remote!==git('rev-parse','HEAD'))throw Error('Push must be verified before packaging');
if(git('diff',code,'--name-only','--','v2/app','v2/frontend/src','v2/alembic'))throw Error('Application differs from tested code');
const report=resolve(repo,'docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md');
const body=String.raw`# EPIC — laptop, estoque executivo e gestão de preços

## 1. Estado atual e como apresentar

**Implementado e promovido localmente; apresentável com ressalvas.** A rodada melhora a entrega Heroes existente, sem redesenho geral. Estoque e Contas a pagar passaram de **2 e 0 linhas completas para 5 e 5**, respectivamente, em **1366×681, escala 100%, texto de tabela 14 px**. Composição e filtros secundários podem ser recolhidos; preços têm substituição, encerramento, histórico e importação CSV conferida antes de gravar.

- **URL:** http://127.0.0.1:8082/dashboard?view=executiva.
- **Build:** ${proof.build.build_id}; **código servido/testado:** ${code}; **schema 033**.
- **Runtime separado:** ../audit-runtime/laptop-prices-20261023; PostgreSQL **5449**, epic_v2_test, storage próprio. O anterior **8082/5447** foi preservado; 8082 agora aponta para a nova cópia. O banco 5447 não foi migrado nem sobrescrito.
- **Massa:** Heroes preservada; SHOW26 continua com **42 UN, custo R$ 54.900, venda potencial R$ 138.138 e obrigação A EUR 2.000 aberta**. Tabelas QA isolam os testes de preço.
- **Gate técnico/visual do runner:** aprovado no recorte descrito. **Conferência física do laptop: PENDENTE.** Não houve validação humana de maximizar/restaurar/redimensionar ou legibilidade no equipamento. Capturas são viewports do navegador, não a janela inteira.
- **Lacuna não mascarada:** comprador e aduana realizaram gravações operacionais pela UI. Estoque salvou/reabriu uma consulta pessoal, mas recebimento operacional pela UI continua bloqueado pela entrada aduaneira. Nenhuma permissão foi ampliada. Auditoria integral, aceite global e J#8 não são encerrados.

Se o servidor estiver parado, execute na raiz do checkout:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-revisao-experiencia/laptop-round/start-release.ps1
~~~

O comando não faz build, seed, reset, migration ou restore; recusa porta ocupada e valida o banco. Para uma nova janela nativa de apresentação:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-pre-demo-ceo/scripts/open-demo-presenter.ps1
~~~

Nova janela aberta pelo launcher: PRESENTATION_READY em 23/10/2026, 16:06 (Brasília), administrador, manifesto e PDFs verificados, viewport nativo (sem emulação fixa), tour inicialmente desligado. Clique **Iniciar demonstração**; ritmo padrão 50 s/etapa, oito etapas, controles de pausa/retomada, anterior/próximo, escolha, recolher e sair. O tour não grava operações; o administrador continua podendo trabalhar manualmente.

**Contingência manual:** Visão geral → Explorar estoque → Beach Tennis + Roupas/Raquetes/Bolas → comparar custo/venda → buscar SHOW26 → produto → compra A → composição → A-commercial.pdf → Escape/Voltar até a lista. Depois Contas a pagar → vencido EUR → obrigação A. Preços: Produtos → ficha → Preços de venda, ou Produtos → Importar preços; usar **Conferir prévia** sem confirmar durante uma apresentação de leitura.

## 2. O que mudou e o que permaneceu

| Recorte | Entrega efetiva | Preservado / limite |
|---|---|---|
| Estoque | Cabeçalho/margens compactos; resumo em linha; barra Agrupar/Exibir/Ordenar; composição e filtros secundários recolhíveis com estado em URL/visão e fallback local por usuário | OR dentro da faceta, AND entre facetas; agrupamento/medidas não mudam população; totais antes da página/ordem; fonte operacional legível |
| Retorno | Produto, compra, versão, composição e PDF reais; foco, filtros, página e ordenação preservados | Tabela de preços selecionada acompanha o detalhe, inclusive quando vem de uma visão pessoal |
| Contas a pagar | Uma linha por BRL/EUR: saldo, vencido, hoje, próximos 7 dias e pagamentos por alocar; filtros perto da lista | Moedas não somadas. Pagamento sem alocação não reduz obrigação. Drawer, Escape, URL e links preservados |
| Dashboard | “Exposição em EUR · referência BRL”; estoque/custo/venda/margem visíveis; cobertura comparável curta; leitura no fuso local | Não foi criado um total consolidado de todas as obrigações em BRL |
| Linguagem | Identificação compacta de teste/tour, metadados secundários, unidades em vez de qty, singular/plural na liberação; tour Heroes fala em liberação/recebimento, não residual inexistente | Qualificadores de referência, desatualização, estimado, quantidade-base e cobertura mantidos |
| Preço individual | Novo, Substituir, Encerrar, Histórico; motivo obrigatório e versão lida; datas inclusivas, futuro preservado | Encerrar informa o último dia válido. Substituição na mesma data retém o anterior como substituído; não apaga preço/auditoria |
| CSV | Prévia por linha, criar/substituir/rejeitar, anterior/novo, erros específicos, confirmação explícita atômica | Até 500 linhas/1 MB, UTF-8, tabela/canal existente, preço bruto BRL e unidade cadastrada. Sem editor novo de tabelas/canais |
| Tour | Oito etapas e automação preservadas; testes de pausa/resize/saída/alvo indisponível e ausência de escrita | Ensaio cronometrado de 6min43s pertence à entrega anterior; nesta rodada houve repetição técnica acelerada, não novo ensaio humano |

### Densidade medida, mesma escala e mesma consulta-base

Uma linha conta somente se sua caixa inteira cabe no viewport, após carregamento, fontes prontas e scroll no topo. Não contamos linha parcial nem header. “0” em AP antes significa que a tabela ficava abaixo da dobra, não ausência de dados. Medidas incluem a faixa real de demonstração desligada; a primeira medição intermediária sem essa faixa mostrou 6/6, mas **o resultado entregue é 5/5** no laptop conservador.

{{DENSITY}}

Avaliação visual do agente sobre capturas: primeira dobra mostra busca, seleções, números e linhas comparáveis; tabela começa cedo; no dashboard aparecem compromissos e o resumo econômico do estoque. Em 1024 px o resumo quebra em duas linhas e a densidade cai para quatro produtos: legível, sem redução global de fonte. Composição expandida usa espaço por escolha do usuário. Não é aceite visual humano.

## 3. Preços: contratos, segurança e efeito econômico

Catalog permanece dono da escrita. Novos endpoints: POST /api/catalog/sales-prices/{id}/change, GET /api/catalog/sales-prices/{id}/history, POST /api/catalog/price-import/preview e /confirm. ACL catalog:prices_read/write preservada (sem concessões aos perfis testados). Reporting só lê preços e agrega.

Migration aditiva 033: marcador de substituição em sales_price_entries e sales_price_operations, com chave de requisição única, ator, hash e resultado. Alteração do intervalo antigo e inserção do novo preço/auditoria ocorrem na mesma UoW. Lock por produto evita intervalos concorrentes; o token impede confirmar sobre uma leitura antiga. CSV trava produtos em ordem e confirma o lote inteiro ou nada. Uma prévia não cria preços.

**Repetição comprovada:** após o servidor confirmar dois preços, o runner descartou a resposta HTTP para simular falha de rede. A UI mostrou erro. O usuário simulado clicou novamente em Confirmar; a mesma chave recuperou o resultado e o banco continuou com dois registros, não quatro. Nova prévia/edição é uma nova intenção; a confirmação antiga usa token/chave, não “apagar e reimportar”. Não houve sobrescrita silenciosa de histórico.

Validações: SKU inexistente/repetido, quantidade de colunas, UTF-8, aspas, preço positivo/precisão, unidade incompatível, tabela inexistente/incompatível, datas inexistentes/invertidas, sobreposição e mudança posterior à prévia. Sem inferir unidade, canal ou preço pelo nome do produto. Erros por linha bloqueiam toda a confirmação até correção.

### Reconciliação preservada e testes isolados

| Cenário | Esperado e observado |
|---|---|
| SHOW26 / produto 3 | 42 UN = 12 da origem A + 30 da B. R$ 14.400 + R$ 40.500 = R$ 54.900. Preço R$ 3.289/UN → R$ 138.138. Diferença R$ 83.238; margem comparável 60,257134…% |
| Compra A / caso 2, versão 2 (número 1) | Base faturada 20 UN; custo publicado R$ 24.000, R$ 1.200/UN. Saldo remanescente 12 não substitui a base 20. Documento A-commercial: 20 × EUR 150 = EUR 3.000 |
| Obrigação A / fatura 2 | EUR 3.000 − alocação EUR 1.000 = EUR 2.000. Não foi criado pagamento/alocação adicional nesta rodada |
| Estoque padrão Beach Tennis | 29 SKUs, 404 UN + 58 PCT + 22 CX; R$ 274.414,54 de custo; R$ 643.773,20 de venda potencial; preço 27/29, margem 59,6% sobre população comparável. Unidades heterogêneas não somadas |
| AP completo aberto | BRL 17.600,00 e EUR 42.708,43, reconciliados com as obrigações do recorte; vencido EUR 2.000; pagamentos EUR 2.650 ainda por alocar. Sem abatimento automático |
| Indicador principal | EUR 41.940,43 × referência 5,6574 = BRL 237.273,79. É exposição EUR, não todo AP; não forçamos igualdade com a fila mais ampla |
| QA individual, tabela 4, FIERCE26 | 10 UN; custo imutável R$ 12.189,86. Preço 1.200 → 1.300 pela UI; potencial atual R$ 13.000, margem 6,231846…%. Vigência atual encerrada em 23/10; novo preço 1.400 inicia 24/10; histórico anterior preservado |
| QA CSV, tabela 5 | FIERCE26 1.500 → 1.600, BULL-M 500 → 550. FIERCE26: 10 × 1.600 = R$ 16.000; custo R$ 12.189,86; margem 23,813375%. BULL-M: 13 × 550 = R$ 7.150. A tabela Heroes não mudou |

Não mudamos métodos de valoração, impostos ou regras financeiras. Custo por origem/publicação, PEPS gerencial estimado para saída genérica e margem potencial continuam limitados à política **DEMO_ORIGIN_FIFO_V1 em APP_ENV=test**, não homologação contábil de produção. Taxa documental de custo, taxa de pagamento e referência de exibição continuam distintas. Cotação externa permanece desabilitada; cache identificado/desatualizado não é consulta nova bem-sucedida.

Ao final: 37 produtos (31 Heroes + históricos/QA), 12 pedidos, 12 faturas, 30 obrigações, 9 pagamentos, 10 alocações, 10 embarques, 9 processos, 40 movimentos, 8 casos/11 versões de custo, 60 documentos, 40 registros de preços. Delta desta rodada: um produto sem saldo e um rascunho aduaneiro pelos perfis, duas tabelas QA e sete registros de preços; configurações pessoais testadas sem apagar visões antigas. A visão “Beach Tennis · Executiva” foi recolocada como padrão pela UI.

**Histórico preservado:** C0 já contém duas despesas de R$ 120 (R$ 240), decorrentes da rodada anterior. Não repetimos essa transação. Nos testes interrompidos desta rodada, o preço substituído e o processo aduaneiro foram consultados antes de retomar; nenhum foi criado duas vezes. I-01 permanece inconclusivo, sem atribuição de causa.

## 4. Testes realmente executados

- **67 backend:** operações de preço, retry, histórico, fechamento, futuro, sobreposição, CSV inválido/prévia obsoleta, unidade/canal, oráculos de estoque, totais/ACL, visões, dashboard e leituras. PostgreSQL real exclusivo **5448**, storage temporário. A fixture unitária remove/cria suas tabelas somente nesse cluster verificado; não foi apontada para 5445/5447/5449.
- **52 frontend dirigidos:** estados do dashboard, referência EUR/BRL, zero/null/erro/loading, datas, composição, preferências, ACL de estoque e resumo AP/drills. Build TypeScript/Vite passou; OpenAPI regenerado e drift passou. Warning de bundle grande continua, sem nova dependência.
- **23 UI no candidato final:** quatro densidades, quatro percursos produto/custo/PDF/retorno, responsividade de preços/tour nos quatro tamanhos, filtros multisseleção, agrupamento/medidas, paginação, visão salva, atraso/erro/recuperação, AP reconciliado/drawer, preço do contexto, manifesto/tour e smoke.
- **5 cenários UI com escrita/ACL nesta rodada:** preço individual; CSV com correção/confirmação/retry/substituição; comprador; aduana; estoque (preferência, não movimento). A primeira execução teve 3 passagens e duas falhas do runner após gravação (seletor de status ambíguo e test-id incorreto). Efeitos foram reconciliados; as continuações passaram. Houve ainda correção da expectativa do runner: FIERCE26 tem 10 UN, não 25.
- **Preferência final:** teste adicional da persistência dos filtros secundários e retorno à visão de apresentação, sem apagar preferências. A primeira tentativa recarregou antes do evento de toggle atualizar a URL; o runner passou a aguardar a URL e confirmou a persistência real sem mudança no código da aplicação.
- **Após promoção:** {{POST_TESTS}}. Prova HTTP: ${proof.files_checked} arquivos, ${proof.manifest_checks} checks do manifesto e ${proof.documents_checked} documentos por SHA-256; assets correspondem ao bundle revisado.

Falhas encontradas durante preparação não são omitidas: o primeiro build candidato usou nome incorreto da flag do tour; o gate detectou ausência de Iniciar e bloqueou a promoção. Corrigido para VITE_ENABLE_DEMO. Uma asserção media destaque após Pausar (pausa remove destaque intencionalmente); ajustada para medir enquanto o passo está ativo. Retorno rápido do runner sem esperar foco foi corrigido para aguardar cada transição. A versão anterior permaneceu disponível durante isso. Não houve regressão de negócio detectada nesses casos. O tour completo após promoção durou **20 s** no ritmo técnico de 2 s/etapa, com lista de escritas vazia; essa duração não mede usabilidade humana nem substitui o ensaio anterior.

### Percursos adicionais — executor: runner Playwright, não apresentador humano

| Abri / Vi / Fiz / Resultado | Classificação |
|---|---|
| Abri Estoque / vi Beach Tennis / selecionei Roupas, Raquetes e Bolas; alternei agrupamentos / mesma população e totais; SKU multimodal não duplicado | Aprovado UI + consulta técnica |
| Abri segunda página / vi saldo e resumo / abri produto, custo, PDF e usei Escape/histórico / página, busca, ordem e foco retornaram; recarga preservou consulta | Aprovado UI |
| Abri Mais filtros e composição / recolhi, recarreguei / preferência mantida; medidas continuam independentes | Aprovado UI |
| Abri AP / vi BRL/EUR separados / cliquei Vencido EUR, abri drawer e Escape / EUR 2.000 e contexto preservados; resumos reconciliados com o contrato | Aprovado UI + consulta técnica |
| Abri ficha FIERCE26 / vi preço QA / substituí, encerrei e cadastrei futuro; tentei intervalo inválido / erro específico, histórico e persistência; estoque usa tabela escolhida | Aprovado UI + consulta técnica |
| Abri Importar preços / vi linha rejeitada / corrigi arquivo, conferi prévia, confirmei e repeti após falha de rede / lote atômico sem duplicação; substituição preservou anteriores | Aprovado UI; falha de rede induzida, backend/banco reais |
| Entrei como comprador / criei produto sintético / reabri / cadastro persistido; importação de preço negada | Aprovado UI/ACL |
| Entrei como aduana / criei rascunho / reabri após falha do seletor / uma criação persistida; importação de preço negada | Aprovado UI/ACL |
| Entrei como estoque / salvei e reabri consulta / importação de preço negada / preferência persistiu, sem acesso a custo/preço | Aprovado para preferência/ACL; gravação operacional bloqueada |
| Iniciei tour / oito telas reais / pausei, retomei, mudei etapa, resize, navegação manual, saída durante loading e erro de alvo / automação cancelada/retomada corretamente, sem POST de negócio | Aprovado runner |

Preparação por serviço/API: somente tabelas QA e leituras de reconciliação nesta rodada. Login rápido do administrador é preparação de sessão. Criação/edição de preço, lote, produto do comprador, processo da aduana e preferências foram interações UI. Testes de falha/latência usam interceptação declarada, não simulam aprovação funcional de um backend inexistente. As operações positivas principais usaram navegador/backend/PostgreSQL reais.

## 5. Preservação, GitHub, promoção e recuperação

### Antes de editar

Confirmados: branch ${branch}; HEAD/remoto f864cbbe19b77cb1c28d8b16c122c7f695d189ac; aplicação servia 88718645c830b16ee4e7860eb17cc3ffbf9d58fa, build stock-executive-20261023.1, schema032, PG5447. O delta documental pós-push foi revisado e preservado no checkpoint **7467a1ba3fde79774b3dbe4fb842eabc0fec12e3**, com push e consulta remota iguais antes das alterações.

Backup inicial: **C:\Users\ricar\Desktop\projetos\EPIC\backups\laptop-prices-before-20261023-151328**. Preservou WIP modificado/não versionado, release completa (código/dist/scripts/manifesto), anexos e os bancos apresentação5447/candidato5445. **1.546 arquivos verificados por hash**; dumps lidos integralmente por pg_restore. SHA-256 apresentação: 7e6313e13660f3a1091759a1e8104a07de6137730f80474d412481a4d5b03d91; candidato: c89c97ba4d3d438332f03d05ef838112b172d6c2b6fab8e7de7732cdeddec002. Não foi restaurado sobre base existente.

Código/delta revisado estão no Git. Dumps, storage, credenciais/configurações locais e evidências brutas permanecem **fora do remoto público**. WIP legado de capturas/protótipos e fixtures documentais não relacionado a esta implementação foi preservado no snapshot, não descartado nem incluído indiscriminadamente no commit. O Git ainda pode mostrar esse WIP; isso não significa fonte servida divergente. **Cópia externa dos dados continua pendente**.

### Commit e prova do remoto

- Remoto público: https://github.com/Kadorium/controle_heroes.git — sem mudança de visibilidade, histórico ou force-push.
- [Checkpoint inicial 7467a1b](https://github.com/Kadorium/controle_heroes/commit/7467a1ba3fde79774b3dbe4fb842eabc0fec12e3).
- [Código testado e servido ${code.slice(0,7)}](https://github.com/Kadorium/controle_heroes/commit/${code}). git rev-parse HEAD e git ls-remote origin refs/heads/${branch} devolveram **${code}** após o push do código; a API pública do GitHub confirmou o mesmo SHA/URL.
- Fechamento posterior contém somente handoff, empacotamento, verificadores/teste de preferência e launcher; não muda app/assets. É identificado pela tag **delivery/laptop-prices-20261023.1** no [GitHub](https://github.com/Kadorium/controle_heroes/tree/delivery/laptop-prices-20261023.1). A referência da tag e a ponta da branch são conferidas após publicar. O próprio SHA do commit que contém este texto não é embutido nele por autorreferência; a tag identifica esse fechamento sem deixar recibo local não commitado. Não é afirmação de CI remoto aprovado.

### Promoção e recuperação

Candidato desenvolvido em checkout atual/8088, PG5445, storage isolado. Snapshot final **${proof.backup}**, dump SHA-256 **${proof.dump_sha256}**. Preparação criou **nova** cópia/runtime e **novo** cluster5449, restaurou o snapshot, validou em8091 e só então trocou o processo8082 identificado. O antigo diretório stock-executive-20261023 e cluster5447 ficaram intactos.

Identidade nova verificada: ${proof.database.join(' · ')}. Anexos: ../audit-runtime/laptop-prices-20261023/storage/attachments; quarentena no mesmo storage próprio. Fonte/dist/manifesto de uso comparados por hash e HTTP, não inferidos do checkout.

Após o smoke, 14 tabelas de negócio foram comparadas integralmente (contagem e SHA-256 de todas as linhas ordenadas) entre candidato congelado5445 e apresentação5449: iguais. Sessões e consultas não são movimentos de negócio. Manifesto SHA-256 ${proof.build.manifest_sha256}; assets de uso: ${Object.entries(proof.build.assets).map(([name,hash])=>name+' = '+hash).join('; ')}.

Para recuperar imediatamente a apresentação anterior, preservando também a nova:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-revisao-experiencia/laptop-round/recover-previous.ps1
~~~

O script recusa processo estranho em8082; para somente o runtime novo identificado e inicia o release antigo com seu dist, storage, manifesto e banco5447. **Não reverte migration no lugar, não reseta Git e não restaura sobre dados.** Reabra http://127.0.0.1:8082/dashboard. O novo conjunto/5449 permanece para diagnóstico. Para recuperação de desastre, o dump deve ser restaurado em diretório/cluster novo previamente identificado, com o storage e release correspondentes — nunca aplicar o dump às cegas em5447 ou no operacional.

## 6. Pendências e cobertura honesta

1. **Recebimento pelo perfil estoque:** API autoriza inventory:write; a única UI de recebimento usa ReceiptPanel dentro de CustomsDetailPage, que exige customs:read e consultas aduaneiras. O perfil estoque não possui esse acesso. Propor entrada própria de recebimentos com leitura mínima autorizada; não conceder permissão ampla nem marcar movimento aprovado porque uma visão pessoal foi salva.
2. **Laptop físico:** maximizar/restaurar/redimensionar e avaliar legibilidade no equipamento são tarefas do apresentador. Ausência de overflow no runner não substitui esse aceite. Não há captura de janela inteira certificada nesta rodada.
3. **Políticas operacionais:** valoração/PEPS/margem continuam de demonstração; ratificação fiscal/contábil, preços líquidos/comissões, margem realizada, reservas, editor de tabelas/canais, XLSX e importação de catálogo em massa permanecem fora deste recorte.
4. **Arquitetura preexistente:** violação ingestion→foundation registrada antes permanece pendente; não foi declarada corrigida nem se executou suíte integral para produzir essa alegação. **I-01 histórico** permanece investigação delimitada; estes testes não demonstram sua causa/correção.
5. **Preservação externa e acabamento residual:** offsite de dados pendente; bundle grande; revisão mais ampla de linguagem operacional e origem/natureza da taxa no detalhe AP não encerradas globalmente. Não modernizamos todas as telas. Sidebar mostra erro cambial resumido/desatualização já existente, sem declarar integração externa nova.

Prioridade seguinte: conferência humana desta versão, seguida da entrada de recebimento do estoquista com ACL existente. Não condicionar o uso do roteiro executivo a redesenho geral.

## 7. Arquivos e governança

**Documentos vigentes alterados:** este único handoff; ROADMAP_V2_EPIC.md (0.5.155, B e derivação da A, arquivo300 linhas/ParteA sob o teto, sem mudar barras/n/d); docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md (0.2.39, §8.17.1); docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md (3.12, referência visual consultiva). Não foi criado relatório paralelo para o advisor. Planos N1–N11/P2–G2 anteriores permanecem historicamente no Git; esta seção e o estado inicial substituem afirmações antigas de “CSV não implementado” e baixa densidade como pendência.

**Código:** Catalog models/pricing/price_changes/price_import/pricing_api; migration033 e schema_revision; Reporting stock_contract/stock_economics (preferências/metadados de cobertura, sem mudar fórmula); frontend App/gerados, billing ApCompactSummary/ApQueuePage/colunas/CSS, catalog SalesPrices/PriceImportPage/ProductListPage/CSS, inventory StockExplorer/model/CSS/StockPositionsPage/StockValueDetail, dashboard ExecutiveOverview/DashboardPage/localDateTime/CSS, demo Tour/steps/CSS, Customs NationalizationPanel.

**Testes/auxiliares:** test_price_operations.py, testes unitários AP/data e ajustes de expectativas; laptop-*.spec.ts/stock-executive.spec.ts; laptop-round/{preserve,prepare-tests,prepare-release,release-runtime,start-release,recover-previous,verify-release,package-return}; launcher open-demo-presenter.ps1. Logs, JSON de reconciliação e PNGs ficam em ../audit-lab/stock-executive-20261023/laptop, fora do Git. Auxiliares não são documentos canônicos nem anexos obrigatórios. As evidências essenciais estão abaixo e os resultados completos foram consolidados acima.

DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md; docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md; docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md.
- Evidence: capturas E01–E12 e provas de runtime/Git incorporadas neste MD; auxiliares técnicos e logs em laptop-round/laboratório.
- Roadmap status: 0.5.155, B.1/B.6 e A última/próxima/falta atualizadas. Livro-razão, n/d, percentuais e estados globais preservados; não é auditoria integral/aceite J#8.
- Next TODO: conferência física do apresentador; entrada própria de recebimento com ACL do estoquista; ratificação econômica e offsite.
- Return to advisor: docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md.

## 8. Evidências incorporadas

Todas as imagens abaixo são capturas reais de navegador, não protótipos. E01/E03 são **antes** (build8871864/stock-executive,8082). As demais são **depois**, build${proof.build.build_id}, código${code},8082. Perfil administrador, escala visual1/DPR1, dados carregados, tour desligado salvo indicação. Interações executadas pelo runner. Screenshots do viewport não provam a janela física inteira.

Se o leitor não renderizar data URI, salve somente este MD e extraia as imagens, sem outro anexo:

~~~python
import re,base64,pathlib
text=pathlib.Path('INTEGRACAO_EXPERIENCIA_EPIC.md').read_text(encoding='utf-8')
for name,payload in re.findall(r'!\[(E\d+)[^\]]*\]\(data:image/png;base64,([A-Za-z0-9+/=]+)\)',text):
    pathlib.Path(name+'.png').write_bytes(base64.b64decode(payload,validate=True))
~~~

A empacotagem verifica assinatura PNG, dimensões, decodificação e hash de cada payload contra o arquivo capturado. Nenhuma evidência indispensável exige outro MD/HTML/ZIP/JSON.
`;
const sizes=['1366x681','1366x768','1920x1080','1024x768'];
const density='| Viewport | Estoque antes → depois | AP antes → depois |\n|---|---:|---:|\n'+sizes.map(s=>{const a=json(`before/density-${s}.json`),b=json(`promoted/density-${s}.json`);return `| ${s} | ${a.screens.stock.rows} → ${b.screens.stock.rows} | ${a.screens.ap.rows} → ${b.screens.ap.rows} |`;}).join('\n');
let md=body.replace('{{DENSITY}}',density).replace('{{POST_TESTS}}',process.env.POST_TESTS||'Smoke/capturas e tour no runtime8082; ver logs verificados ao fechar');
const imgs=[
 ['E01','before/stock-1366x681.png','Antes · estoque: duas linhas completas · 1366×681'],
 ['E02','promoted/stock-1366x681.png','Depois · estoque: cinco linhas completas, resumo e controles · 1366×681'],
 ['E03','before/ap-1366x681.png','Antes · AP abaixo da primeira dobra · 1366×681'],
 ['E04','promoted/ap-1366x681.png','Depois · AP: cinco obrigações completas, resumos separados · 1366×681'],
 ['E05','promoted/dashboard-1366x681.png','Dashboard: referência EUR/BRL, próxima ação e estoque · 1366×681'],
 ['E06','promoted/tour-1-1366x681.png','Tour ativo: faixa compacta e alvo sem cobertura · 1366×681'],
 ['E07','promoted/stock-1920x1080.png','Estoque Full HD: treze linhas completas · 1920×1080'],
 ['E08','promoted/stock-1024x768.png','Janela estreita: quatro linhas, números e unidades legíveis · 1024×768'],
 ['E09','promoted/prices-history.png','Histórico real: vigente, futuro e substituído nas tabelas QA · 1366×681'],
 ['E10','promoted/prices-preview.png','Prévia real de duas substituições; esta captura não confirma operação · 1366×681'],
 ['E11','promoted/tour-2-1366x681.png','PDF comercial real renderizado e tour sem sobreposição · 1366×681'],
 ['E12','promoted/tour-8-1366x681.png','Custo publicado: versão/base/qualificadores preservados · 1366×681']
];
const evidence=[];
const routes=['/inventory/positions','/inventory/positions','/payables','/payables','/dashboard?view=executiva','/dashboard','/inventory/positions','/inventory/positions','/catalog/products/4','/catalog/prices/import','/orders/2/commercial','/costing/2'];
for(const[id,path,caption]of imgs){const buffer=readFileSync(resolve(lab,path));if(buffer.subarray(1,4).toString()!=='PNG')throw Error('Not PNG');const payload=buffer.toString('base64'),decoded=Buffer.from(payload,'base64');if(sha(buffer)!==sha(decoded))throw Error('Decode mismatch');const width=buffer.readUInt32BE(16),height=buffer.readUInt32BE(20);md+=`\n### ${id} — ${caption}\n\nRota ${routes[evidence.length]}; ${width}×${height}; SHA-256 ${sha(buffer)}.\n\n![${id} ${caption}](data:image/png;base64,${payload})\n`;evidence.push({id,path,width,height,sha256:sha(buffer)});}
writeFileSync(report,md,'utf8');writeFileSync(resolve(lab,'package-proof.json'),JSON.stringify({report,bytes:Buffer.byteLength(md),sha256:sha(md),evidence,code,remote},null,2));console.log(JSON.stringify({report,bytes:Buffer.byteLength(md),sha256:sha(md),images:evidence.length,code}));
