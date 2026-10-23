// Packaging only: reads frozen evidence; never starts the app or writes business data.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const here=dirname(fileURLToPath(import.meta.url)),repo=resolve(here,'../../../..');
const lab=resolve(repo,'../audit-lab/stock-executive-20261023');
const json=p=>JSON.parse(readFileSync(resolve(lab,p),'utf8').replace(/^\uFEFF/,''));
const proof=json('release-proof.json'),validated=json('scenario/validated.json');
const sha=b=>createHash('sha256').update(b).digest('hex');
const git=(...a)=>execFileSync('git',a,{cwd:repo,encoding:'utf8'}).trim();
const code='88718645c830b16ee4e7860eb17cc3ffbf9d58fa';
if(proof.build.source_commit!==code)throw Error('Unexpected served source');
const receiptPath=resolve(lab,'final-git-receipt.json');
if(process.argv.includes('--record-final-push')){
 const local=git('rev-parse','HEAD'),branch=git('branch','--show-current');
 if(branch!=='feat/stock-executive-20261023')throw Error('Unexpected branch');
 const remote=git('ls-remote','origin','refs/heads/'+branch).split(/\s+/)[0];
 if(local!==remote)throw Error('Final push not verified');
 if(git('diff','--name-only',code,'--','v2/app','v2/frontend/src','v2/alembic'))throw Error('Application source differs from release');
 writeFileSync(receiptPath,JSON.stringify({local,remote,branch,verified_at:new Date().toISOString()},null,2),'utf8');
}
const receipt=existsSync(receiptPath)?JSON.parse(readFileSync(receiptPath,'utf8')):null;
if(receipt&&receipt.local!==receipt.remote)throw Error('Unverified final push');
let md=String.raw`# EPIC — experiência executiva integrada e demonstração Heroes

## 1. Estado atual — execução de 23/10/2026

**Versão de uso implementada, populada e promovida localmente. Apresentável com ressalvas.** O pacote P2 → T1 → C2 → E4-S1 → E4-S2 → Q3 foi executado; G2 técnico local passou no percurso dirigido, com as limitações explícitas abaixo. Não é auditoria integral, aceite visual humano, aprovação de política econômica de produção ou novo encerramento de J#8.

- **Abrir:** http://127.0.0.1:8082/dashboard?view=executiva — administrador, ambiente de demonstração/teste.
- **Build:** stock-executive-20261023.1. **Código servido:** 88718645c830b16ee4e7860eb17cc3ffbf9d58fa. Schema032.
- **Entrega principal:** seleção transversal de produtos, agrupamento e medidas independentes; visão pessoal; custo do saldo por origem; preço vigente; venda e margem potenciais; produto → compra/versão → composição → PDF real → retorno com contexto.
- **Conferido depois da promoção:** 10 testes UI passaram, 11 verificações do manifesto, 5 PDFs por hash e 293 arquivos da cópia de uso. Os assets foram comparados por HTTP, não apenas no checkout.
- **Tour:** oito etapas; ensaio completo de 6min43s; repetição técnica final em20s, sem escrita de negócio. A janela de apresentação é aberta separadamente, com viewport nativo e tour desligado.
- **Limites materiais:** aprovação física do laptop pendente; regra econômica habilitada somente em teste; importação de preços não implementada; lista com todos os controles tem baixa densidade na primeira dobra de681px; uma falha arquitetural preexistente continua registrada. A matriz funcional não é integralmente verde em todos os subcasos.

Este documento substitui a leitura corrente do antigo cabeçalho “Planning”. O plano N1–N11 e a integração G1 anteriores ficam preservados no checkpoint inicial; seus critérios relevantes permanecem consolidados na seção2. Capturas antigas/protótipos não são usados como evidência desta entrega.

### Abrir, retomar e apresentar

Na raiz do checkout, caso8082 ainda não esteja ativo:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-revisao-experiencia/demo-e2e/start-release.ps1
~~~

O comando recusa porta ocupada; não mata outra sessão, não faz build, seed, reset ou restore. Para abrir uma NOVA janela nativa, preservando as outras:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-pre-demo-ceo/scripts/open-demo-presenter.ps1
~~~

O launcher verifica ambiente, sessão admin, manifesto e PDFs. **Uma nova janela foi aberta e deixada no painel**, com confirmação PRESENTATION_READY em presenter-open.log, sem iniciar o tour. Clique em **Iniciar demonstração**. O ritmo padrão de50s por etapa foi ensaiado; Pausar/Continuar, Anterior/Próximo, escolha de etapa, Recolher e Sair continuam disponíveis. A leitura automatizada não retira a capacidade de edição manual do administrador.

**Roteiro manual de contingência, sem gravar:** Visão geral → Explorar estoque → manter Beach Tennis, selecionar Roupas/Raquetes/Bolas → comparar custo e venda → buscar SHOW26 → abrir produto → Origens do saldo e custo → Compra2/v1 → Ver composição → A-commercial.pdf → Escape/Voltar até a lista. Em Contas a pagar, abrir a obrigação da compraA: EUR2.000 restantes. Pagamento2 mostra a alocação deEUR1.000. Se o tour interromper por alvo ausente, sair e seguir este roteiro; não confirmar recebimento ou pagamento para fazê-lo continuar.

## 2. Plano aprovado e execução por gate

| Etapa / base N1–N11 | Executado | Situação e dependências remanescentes |
|---|---|---|
| P2 — proteção e identidade, N1/N11 | WIP, dados, documentos, dist e scripts preservados antes da edição; checkpoint e push consultados no remoto | PASS; backup local restaurado em novo cluster. Offsite de dados ainda pendente |
| T1 — composição e texto, N3/N7 | Filtros financeiros com alcance próprio, posição atual de estoque, cobertura curta e detalhes de valor acessíveis | Implementado no percurso; textos longos residuais de AP/Aduana não foram redesenhados integralmente |
| C2 — taxonomia e consulta, N2/N4/N6 | Modalidade/tipos/modelos multisseleção, agrupamento independente, unidades/embalagens, visões por executivo, totais completos | Implementado; 507 registros em laboratório de escala, sem contaminar a demo |
| E4-S1 — saldo e custo, N5/N8 | Reconstrução das origens remanescentes, custo publicado da origem/linha, cobertura, PEPS gerencial estimado para saída sem origem | Implementado e reconciliado; política autorizada só para demonstração |
| E4-S2 — preços e potencial, N5/N6/N8 | Tabela/canal BRL, unidade e vigência, cadastro UI e histórico, preço ausente/expirado, venda e margem da população comparável | Implementado; importação em lote com preview e edição de vigências existentes não entregues |
| Q3 — qualidade e massa, N9 | Heroes persistido; UI real de compra/fatura/pagamento/alocação/recebimento/custo/preço; perfis e erros; quatro viewports | Passou no escopo descrito na matriz; cobertura de combinações/perfis é parcial, não auditoria integral |
| G2 — promoção, N10/N11 | Bundle validado, cópia separada, snapshot restaurado em banco novo, smoke pós-promoção, HTTP/hash, tour e recuperação disponível | PASS técnico local com ressalvas; físico/humano pendente. Nenhuma promoção de produção |

As decisões do plano foram mantidas: r2; Estoque imediatamente acessível; URL explícita → preferência pessoal → Beach Tennis inicial removível; sem cadeia obrigatória categoria/modalidade/modelo; uma superfície ativa para produto/custo/documento; campos e leitores reais, não formulários simplificados do protótipo. E3-B amplo, política contábil/tributária, margem realizada e integrações comerciais externas continuam fora do pacote.

### O que mudou na experiência

1. **Filtros ≠ agrupamento ≠ medidas.** Dentro de um filtro há OR; entre dimensões há AND. Roupas/Raquetes/Bolas + Beach Tennis usa os IDs estruturados do catálogo. Multimodais participam uma vez; grupo multimodal é disjunto, não soma o mesmo SKU em dois totais.
2. **Dashboard e lista usam a mesma consulta.** Resumo, composição e tabela mantêm seleção. Agrupar por tipo, modelo, modalidade ou não agrupar não muda a população. A composição alterna quantidade/custo/venda. Mais filtros contém modelos, posições e locais; controles frequentes ficam próximos à tabela.
3. **Preferências reais por usuário.** Visão salva conserva filtros, filtros visíveis, agrupamentos, medidas, colunas, ordenação e padrão pessoal. Versionamento otimista impede sobrescrita silenciosa; nome duplicado é rejeitado. URL explicitamente vazia remove a restrição; ID inválido pede revisão, não amplia o resultado.
4. **Consulta com memória.** Busca, filtros, página, ordem e contexto são serializados; histórico do navegador e Escape devolvem foco ao acionador. Resposta atrasada não substitui uma consulta mais nova. Abrir produto/custo/PDF não recalcula/publica custo.
5. **Números antes de explicações.** Estoque aparece na primeira dobra do dashboard de1366×681; custo, preço, venda e margem são medidas distintas, com moeda/unidade/cobertura. As notas financeiras necessárias permanecem no detalhe e nos qualificadores.

| Antes / problema | Agora | Limite preservado |
|---|---|---|
| “Escopo dos filtros” e parágrafo permanente | “Vencimentos financeiros” junto ao filtro financeiro; seleção de estoque no próprio bloco | Agenda mensal continua identificada pelos meses retornados; não equivale à janela de90dias |
| Explicação longa sobre mercado/planejamento/realizado | Referência em reais, taxa/data/fonte e detalhe acessível | Cotação desatualizada permanece visível; não é taxa documental nem bancária |
| “Posição física atual · saldos por regime” redundante | “Estoque atual”, chips e seletor de posição | Trânsito não é saldo disponível; UN/PCT/CX separados |
| Custo da última compra aplicado indiscriminadamente | Custo do saldo + origens; compra, versão e base próprias | PEPS estimado e cobertura explícitos |
| Ausência de preço ocupando KPI inteiro | “—” na linha e cobertura de preço no resumo | Não converter ausência em zero nem calcular margem sem comparabilidade |

O resumo financeiro principal continua sendo **exposição em EUR convertida por referência**, não um total universal de compromissos emBRL. Na captura, EUR41.940,43 ×5,6574 = BRL237.273,79. Contas a pagar apresenta separadamente BRL17.600 e EUR42.708,43; populações diferentes não são reconciliadas por igualdade falsa. O link informa “Abrir fila completa”. A agenda civil Outubro–Dezembro não é renomeada como a janela móvel até21/01/2027.

## 3. Contratos, fronteiras e premissas econômicas

### Implementação efetiva

- **Catalog:** projeção comercial sem truncamento de500 produtos; classificação BALL/OVERGRIP/OTHER; PATCH distingue limpar atributo de campo não enviado; GET de taxonomia não cria registros. Preços pertencem ao Catalog, com moeda BRL, tabela/canal, unidade, validade, motivo, idempotência e auditoria na mesma transação.
- **Inventory:** leitura de movimentos e saldo, origem explícita prioritária, saída genérica PEPS, reversões e reclassificação. Divergência entre ledger e saldo impede afirmar custo completo. Recebimentos distintos da mesma origem econômica são agregados (12UN da compraA, não duas compras artificiais).
- **Customs/Billing/Costing:** contratos públicos relacionam processo, recebimento, linha e unidade; Costing fornece versão publicada/quantidade-base/cobertura/documentos. Reporting não escreve movimentos, preços ou custos.
- **Reporting:** GET /api/reporting/stock-explorer recebe listas de IDs, q, produto, posição/local, agrupamentos, sort, limit/offset e tabela. Retorna linhas paginadas, totais e grupos da população completa. Permissões de leitura física e econômica são independentes. GET/POST /api/reporting/stock-views persiste somente preferências do ator.
- **Preços:** GET /api/catalog/price-lists e /api/catalog/sales-prices; POST /api/catalog/sales-prices. Não há importador CSV/XLSX de preços com preview nesta entrega. Cadastro individual e massa preparada pelos serviços existentes não são confundidos com importação pela UI.
- **Migration032:** tabelas de listas/preços e visões, constraints positivas/unicidade/padrão pessoal. Aplicada somente nos novos clusters de teste; banco operacional e demo anterior não foram migrados.

**A regra econômica está guardada por APP_ENV=test e STOCK_ECONOMICS_POLICY=DEMO_ORIGIN_FIFO_V1.** Em contexto normal sem essa política não se assume aprovação para valorar saldos. Catalog permite guardar preços conforme ACL; isto não aprova política contábil ou fiscal.

### Definições usadas

| Medida | Definição implementada / ausência |
|---|---|
| Quantidade | Saldo por SKU/local/regime; total separado por unidade. Disponível físico = doméstico ativo, não trânsito, entreposto ou quarentena |
| Custo do saldo | Soma da quantidade remanescente de cada origem × custo publicado da linha dessa origem; não é custo total da importação, nem último custo × todo o saldo |
| Estimado | Saída genérica distribuída por PEPS gerencial. Origem explícita é respeitada. Não é avaliação contábil homologada |
| Preço | Varejo demonstração / Venda direta / BRL bruto por unidade de venda; vigência inclusiva; sobreposição rejeitada, histórico preservado |
| Venda potencial | Quantidade elegível × preço vigente compatível. Pacote3 e pacote60 mantêm preço por pacote, caixa50 por caixa |
| Margem potencial | (Venda comparável − custo comparável) / venda comparável, calculada sobre totais da mesma população; antes das despesas de venda. Não é markup, média simples, lucro ou margem realizada |
| Cobertura | Quantidade/SKUs com custo/preço compatível; desconhecido = null/“—”. Total parcial é qualificado. Quarentena sem quantidade elegível pode ter venda0 confirmada; custo desconhecido continua ausente |
| Câmbio | Custo documental6BRL/EUR fictício, distinto da referência de mercado armazenada5,6574 e do registro de pagamento. Sem substituir um pelo outro |

A atualização externa de cotação está desativada no runtime. A leitura reaproveita o cache anterior, com fonte registrada Frankfurter(ECB), data22/10/2026 09:00Brasília e estado desatualizado; não se declarou consulta nova bem-sucedida ao provedor. A indisponibilidade não bloqueia catálogo, estoque, documentos ou tour.

## 4. Massa e reconciliação

**Cenário:** HEROES-EXEC-20261023-v1; tour DEMO-HEROES-EXEC-20261023. **D=23/10/2026, America/Sao_Paulo.** Identidades comerciais de referência são públicas; SKUs internos DEMO-HR-*, transações, taxas de custo, preços escolhidos, fornecedores, despesas e documentos são fictícios.

31SKUs Heroes úteis: oito raquetes Beach Tennis; cinco tamanhos de camiseta THE BULL; seis combinações de moletom WAVE; quatro saias; mochila; três overgrips; duas embalagens de bolas; Padel TOURO e Pickleball NOVA. O volume sugerido de40–60 foi reduzido para não inventar combinações. Há36produtos no banco:31Heroes, dois históricos Atlas/Aurora preservados e três registros QA sem saldo. A escala de507 produtos fica exclusivamente no laboratório5446.

No recorte padrão Beach Tennis/disponível: **29SKUs;404UN +58PCT +22CX; custo R$274.414,54; venda potencial R$643.773,20; margem comparável59,6%; custo29/29 e preço27/29SKUs**. Não somar unidades heterogêneas. FOREST tem preço expirado; BALL50 não tem preço. Entreposto5UN e quarentena2PCT são posições separadas, com custo desconhecido, não disponíveis para venda. O percentual95% foi contexto do usuário, não estatística calculada do cenário.

### Oráculo obrigatório SHOW26: esperado = observado

| Elemento | CompraA | CompraB |
|---|---:|---:|
| Recebido | 20UN (12+8) | 30UN |
| Mercadorias | EUR3.000 | EUR5.100 |
| Taxa documental fictícia | 6BRL/EUR | 6BRL/EUR |
| Mercadoria convertida | R$18.000 | R$30.600 |
| Frete + tributos + outras despesas | R$2.000 +3.000 +1.000 | R$3.000 +5.400 +1.500 |
| Custo publicado / unidade | R$24.000 /1.200 | R$40.500 /1.350 |
| Saldo após saída genérica de8UN | 12UN | 30UN |
| Custo do saldo remanescente | R$14.400 | R$40.500 |

**Total42UN; custo54.900; médio de exibição1.307,14/UN; preço3.289/UN; potencial138.138; diferença83.238; margem60,257134…% (60,26% a duas casas; UI resumida60,3%).** O total vem das origens com precisão interna, não da multiplicação do médio arredondado.

IDs principais preservados: produto3, pedidoA2, faturaA2, pagamentoA2, embarqueA2, processoA2, casoA2/versão2(número1); compraB/caso3/versão3. Documento A-commercial.pdf:20×EUR150=EUR3.000; hash58c5d8f537997c45c3a7fc2647a7c02409000281b52c333bb24e4ccbe85216a9. O custoA usa base20 faturadas, mesmo com saldo remanescente12.

FinanceiroA: obrigaçãoEUR3.000 em D−7 → pagamentoEUR1.000 sem alocação, obrigação ainda3.000 → alocação1.000, obrigação2.000. BvenceD+45 e continua5.100: **A+B=EUR7.100**, sem descontar pagamentoB ainda livre. Essa preparação foi por API; a UI final reabriu os mesmos registros.

Teste financeiro por UI, separado do oráculo: pedido/fatura13×EUR100=1.300, parcelas600+700; pagamento1.000; antes de alocar a fatura permanece1.300; alocações400+300 deixam600; tentativa9.999 bloqueada; nova alocação200 liquida a primeira parcela e deixa fatura400/pagamento livre100. Recarga e consultas técnicas confirmaram persistência.

### Preparação, repetibilidade e resíduos controlados

Dados foram criados por APIs/serviços de domínio e comandos auditados; não por preenchimento direto de saldos. PDFs foram gerados a partir dos valores do cenário e vinculados depois. **Não houve ingestão documental desses pedidos.**36PDFs gerados foram analisados;5documentos do tour conferidos por HTTP/hash; A-commercial foi renderizado e inspecionado no leitor real.

O journal tem529etapas e evita repetir operações completadas. Seed + augment foram repetidos com fingerprint de26tabelas de negócio idêntico. Não apagar o journal nem reapontar scripts para a release. Não se afirma idempotência exatamente-uma-vez sob interrupção entre commit remoto e gravação do journal; nesse caso, reconciliar a operação persistida antes de repetir.

Reprodução no laboratório protegido já configurado, não na versão8082:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-revisao-experiencia/demo-e2e/lab.ps1
# Em processo separado: inicia somente o candidato8088/5445, com identidade verificada.
v2/.venv/Scripts/python.exe docs/v2/etapa-revisao-experiencia/demo-e2e/runtime.py
# Com o candidato ativo, em outro terminal:
v2/.venv/Scripts/python.exe docs/v2/etapa-revisao-experiencia/demo-e2e/seed.py
v2/.venv/Scripts/python.exe docs/v2/etapa-revisao-experiencia/demo-e2e/augment.py
~~~

O seed recompõe a massa-base identificada; **não substitui os atos executados depois pela UI**. Para reproduzir exatamente a massa final, usar o snapshot final em destino novo, com o procedimento da seção8. Os scripts recusam conexão/porta/diretório divergente; não carregam defaults da demo antiga.

Foram mantidos os cenários UI-LOG(6recebidas), UI-PART(6liberadas/3recebidas/residual3), pagamento e preços QA como história sintética identificável. Não há507produtos de escala na apresentação. No casoC0, uma asserção técnica falhou após já publicar despesa120; a repetição válida publicou outra120. **O custo finalC0 inclui240dessas duas operações autorizadas**, ambas persistidas, e não houve descarte silencioso de histórico. SHOW26/A/B não foram afetados. As três fichas QA sem saldo não entram no recorte padrão de estoque positivo; preferências E2E antigas não são padrão pessoal. A visão atual “Beach Tennis · Executiva” foi salva pela UI.

### Fontes públicas e alcance da verificação

Referências de identidade/preço: [SHOW26](https://www.heroesbrandbrasil.com/shop/raquete-de-beach-tennis-show-26/), [FIERCE](https://www.heroesbrandbrasil.com/shop/raquete-de-beach-tennis-fierce/), [THE BULL camiseta](https://www.heroesbrandbrasil.com/shop/camiseta-esportiva-masculina-the-bull/), [WAVE](https://www.heroesbrandbrasil.com/shop/moletom-wave-feminino/), [saia](https://www.heroesbrandbrasil.com/shop/saia_starlight/), [overgrip3](https://www.heroesbrandbrasil.com/shop/overgrip-3un/) e [overgrip60](https://www.heroesbrandbrasil.com/shop/overgrip-60/) foram reconsultadas nesta execução. Demais nomes e atributos seguem as referências fornecidas no prompt, sem alegar reconfirmação individual de todas as páginas. A página de bolas3 não pôde ser recuperada; o preço do exemplo foi explicitamente tratado como fixture. Não foram fabricados EANs/códigos de fábrica, nem atribuídos custos internos aos sites. Preços públicos variáveis não são tabela oficial aprovada da EPIC.

## 5. Matriz de testes: UI real, preparação e limites

Executor de todas as interações abaixo: **runner Playwright**, não apresentador humano. Ambiente de escrita8088/PG5445/storage próprio; versão final8082/PG5447 somente leitura/sessão nos smokes. Interceptações são usadas exclusivamente nos casos de erro/latência indicados, não para provar valores ou persistência.

| # / tarefa | Perfil; preparação | Abri / Vi / Fiz / Resultado observado | Resultado / limite |
|---|---|---|---|
| 1 Executivo | Admin; massaAPI | Abri dashboard / Vi BRL e EUR/cobertura / Fiz Explorar estoque / Resultado: mesma consulta e oráculo ao filtrarSHOW26 | PASS no percurso; referênciaEUR não é total de todas as moedas. Novo usuário/default coberto por testes de modelo/perfis, não sessão humana |
| 2 Estoque transversal | Admin | Abri estoque / Vi BT / Fiz Roupas+Raquetes+Bolas e alterei modelo/modalidade/sem grupo / Resultado: resumo idêntico, contexto mantido | PASS UI; soma integral também backend/escala |
| 3 Preferências | Admin, comprador, estoque | Abri seleção / Vi chips / Fiz salvar padrão, reabrir, URL explícita vazia e recarga / Resultado: preferência preservada, URL vence, outro ator não recebe a visão | PASS; conflito de versão/default concorrente coberto em backend |
| 4 Multimodal/unidades | Admin; fixtureAPI | Abri recortes / Vi UN/PCT/CX separados / Fiz alternar filtros/grupos / Resultado: produtos multimodais sem duplicação; bola50 sem preço | PASS backend + leituraUI; não houve criação manual de todas as embalagens |
| 5 Cadastro | Admin | Abri produtoBALL50 / Vi edição / Fiz descrição inválida, modelo/classificação, salvar e limpar modelo / Resultado: invalidação e persistência, campo não enviado preservado | PASS UI; novo produto/unidade também no formulário de pedido; não é aceite de todo PIM |
| 6 Preços | Admin; produtoQA API | Abri ficha / Vi histórico / Fiz preço futuro e vigente, sobreposição e duplo clique / Resultado: preço persistido, overlap bloqueado, uma entrada por envio | PASS cadastro; ausente/expirado em dados reais. Importação com preview NÃO IMPLEMENTADA |
| 7 Pedido/fatura | Admin; só PDFs preparados | Abri Novo pedido / Vi formulário / Fiz13×100, confirmar, fatura, anexarPDF, parcelas600+700, emitir / Resultado:1.300 e obrigações após recarga | PASS UI; preparaçõesAPI das outras compras não contam como criaçãoUI |
| 8 Pagamento/alocação | Admin | Abri pagamento / Vi saldo livre / Fiz registro1.000, alocações400+300+200 e excedente / Resultado: uma parcela liquidada, fatura400, livre100, excesso bloqueado | PASS UI+persistência; reflexo econômico consultado, não testada cada variante de crédito/adiantamento |
| 9 Logística/recebimento | Admin; processo/itens preparadosAPI | Abri embarqueF0 / Vi avanço / Fiz chegada e recarga; abri liberaçãoUI-LOG/UI-PART, confirmei e recebi / Resultado:6/6 e3/6; exceder7 bloqueado, residual3 | PASS nos estados executados; demais transições preparadasAPI. I-01 histórico permanece sem causa atribuída |
| 10 Custo/origem | Admin; A/B publicadosAPI | Abri C0 / Vi fontes / Fiz revisão/publicação e despesa120 / Resultado: nova versão e efeito sóC0; SHOW26 continua54.900 | PASS após correção do filtro vazio; duas despesas de120 preservadas conforme seção4. OráculoAPI+leituraUI, não todas as publicaçõesA/B pelaUI |
| 11 PDF/retorno | Admin, final8082 | Abri estoque filtrado / Vi saldo42 / Fiz produto, compra, composição, PDF, Escape e histórico / Resultado: PDF renderizado, URL/ordem/foco retornam, reload mantém consulta | PASS quatro viewports; sem escrita de negócio |
| 12 Permissões | Comprador, aduana, estoque | Abri login real e estoque / Vi físico sem valores ou acesso negado / Fiz consulta e POST de preço negado / Resultado:403/valoresnull no servidor, sem vazamento | PASS leiturasUI+escrita negativaAPI; escrita positiva pelaUI de cada perfil não executada; admin tem os fluxos mutáveis |
| 13 Falhas/recuperação | Admin; interceptação explícita | Abri consulta / Vi503 / Fiz Tentar novamente, busca vazia e resposta atrasada / Resultado: recuperação e última busca correta; PDF404 retorna ao retirar interceptação | PASS UI; 503/404/latência são falhas simuladas, não indisponibilidade real do storage |
| 14 Datas/cobertura | Admin + unitários | Abri vencidos/agenda/estoque / Vi datas atuais/futuras, FORESTexpirado, BALL50ausente, quarentena / Fiz filtros / Resultado: zero e ausência distintos, blocos financeiros/estoque separados | PASS dirigido; fronteiras de validade testadas no backend; não há simulaçãoUI de todas as viradas de mês/fuso |
| 15 Escala | Admin; laboratório8089/5446 | Abri507produtos / Vi total507 / Fiz ordem e última página / Resultado:7linhas finais, totais estáveis | PASS; fixture de escala isolada, não promovida |
| 16 Tour | Admin | Abri demo / Vi manifesto válido / Fiz automático8etapas, pausa, retomada, salto, anterior, resize, saída e alvo ausente / Resultado:6min43s e repetição técnica; zero gravação de negócio | PASS funcional; equipamento físico/aceite humano pendentes |
| 17 Pureza de leitura | Admin; fingerprintsSQLread-only | Abri catálogo/facetas/dashboard/estoque/PDF/tour / Vi dados reais / Fiz navegação e recarga / Resultado:26tabelas de domínio com mesmo hash | PASS; sessão, preferências intencionais, audit de acesso e cache de cotação não são incluídos no hash de negócio |

**Resumo de cobertura:**17famílias exercitadas, mas não17famílias integralmente aprovadas em todas as variações. Nenhum bloqueador observado no roteiro final de leitura. Lacunas específicas: importação de preços, escritaUI positiva em cada perfil, todas as fronteiras de datas pelaUI e percurso históricoI-01. O produto inteiro não foi reaud itado nem aceito por inferência.

### Resultados técnicos realmente executados

| Execução | Resultado e escopo |
|---|---|
| Backend final dirigido | **49passed** em18,50s: origemPEPS/reversão, duas entradas mesma origem, cobertura/null, unidades, margem ponderada, preços/vigência/idempotência, visões/atores/versão, população507, ACL e metadados financeiros |
| Frontend final dirigido | **32passed**,3arquivos: ExecutiveOverview18, demoSafety7, stockExplorerModel7. Rodada anterior40tests em7arquivos também passou; não somar execuções sobrepostas como testes únicos |
| Build / contratos | TypeScript/Vite PASS; OpenAPI gerado e drift PASS. Warning de bundle~1,72MB permanece, sem alegar otimização de performance concluída |
| UI escrita e integração candidato |14passed na primeira bateria; chegada1pass; complemento2pass/1fail, seguido do reteste corretivo1pass; preço vigente1pass; escala1pass |
| Candidato final / restaurado |10pass no candidato;6pass na cópia restaurada8090 antes de promover |
| **Versão de uso8082** |**10passed** em1min: tour4 + smoke6; quatro tamanhos, AP/drawer/Escape/custo, regimes/IDinválido/PDFrecuperável |
| Presenter nativo |1passed em3,1s com viewport:null, ambiente/sessão/manifesto/PDFs e medidas de dashboard/orders/new |
| Tour cronometrado |403s, oito etapas, writes=[]; depois repetição técnica final20s. JS final tem o mesmo hash do ensaio403s; CSS de densidade e agregação backend tiveram ajuste posterior, coberto pelo smoke final e repetição técnica, sem novo ensaio longo |
| Arquitetura ampliada |**52passed,1failed**: import preexistente ingestion/xlsx_commit_commands.py → foundation. Não introduzido neste pacote, não corrigido por ampliar escopo; não declarar suíte integral verde |

Âncoras internas (não anexos necessários): audit-lab/stock-executive-20261023/backend-final.log, frontend-final.log, api-drift.log, build-final.log, ui-tests.log, extra-ui.log, revision-retest.log, current-price-ui.log, scale-ui.log, restored-release-ui.log, promoted-ui.log, presenter-verify.log, backend-release.txt, evidence/tour-release/tour-50s-itinerary.json e evidence/promoted-tour/tour-2s-itinerary.json. Resultado relevante de cada um está acima; hashes de evidências selecionadas ficam na seção11.

### Falhas encontradas e corrigidas

- Filtro explicitamente vazio era tratado como inválido; normalizado como ausência de restrição, mantendo422 para ID obsoleto/inválido. Reteste de custo passou.
- Espera do tour comparava só pathname com destino contendo query; etapa7 travava. Espera agora inclui pathname/query/hash; ensaio completo e controle de cancelamento repetidos.
- Dois recebimentos da mesma compra apareciam como duas contribuições visuais; agregados por origem econômica com unidade/versão/base/local, sem mudar o valor.
- Bootstrap do PostgreSQL verificava ExitCode nulo do wrapper; passou a conferir listener e identidade. A restauração foi retomada somente depois de confirmar cluster novo e banco ausente.
- Taxonomia GET eliminada como ponto de escrita; PATCH de atributos deixa limpar valor sem apagar campos não enviados; projeção comercial completa e totais independentes de ordenação/página. Essas correções atendem aos riscosF-01–F-04 do levantamento; não são prova de toda a auditoria anterior.

## 6. Avaliação visual e limites de aceite

As imagensR01–R10 são **capturas da aplicação final8082**, não protótipos. Inspeção visual pelo agente, combinada aos testes; não avaliação humana no equipamento.

- **1366×681:** título, compromissoEUR/BRL, CTA operacional e resumo econômico do estoque cabem sem tour. Com tour, o destaque financeiro e controles permanecem visíveis; o resumo de estoque fica próximo/abaixo da dobra, alcançado na etapa7.
- **1366×768 e1920×1080:** percurso completo reexecutado, tabelas/custos/PDFs e retorno. Em FullHD, composição e agenda aparecem sem as antigas grandes caixas vazias.
- **1024×768:** navegação real disponível, controles quebram linha e PDF usa área de conteúdo; nenhum zoomCSS/transform foi usado para forçar encaixe.
- **Densidade ainda melhorável:** no estoque com grupos e todas as medidas expandidas cabem2linhas completas em1366×681 e10 em1920×1080. Não confundir ausência de overflow com qualidade visual ideal. Próximo recorte recomendado: controles secundários recolhíveis/composição compacta sem reduzir fonte nem ocultar seleção.
- **Tour:** faixa reserva espaço no laptop; lateral somente em espaço suficiente. Na etapa7, valores42/54.900/138.138 ficam visíveis sem sobreposição. Aduana ainda tem rótulos técnicos e pluralizações residuais (“1 itens”, qty), registrados para melhoria local posterior.
- **AP/Custo:** padrão local anterior preservado e revalidado. AP tem muito espaço de resumo antes da tabela; não se afirma modernização de todas as telas. Custo mantém base faturada20, tributos brutos, versão e natureza documental.

Janela nativa medida pelo runner: inner1920×1065; outer1920×1152; document.client1905×1065; visualViewport1904,67×1065,33; scale1; devicePixelRatio1,5. Shell1904,67px e sidebar216px acompanham a área medida. **Isso não certifica maximizar/restaurar/redimensionar manualmente nem legibilidade física.** Não há screenshot da janela inteira com bordas do sistema; controlador nativo não foi contornado. Essas verificações ficam expressamente com o apresentador.

| Cobertura visual | Telas |
|---|---|
| Novo padrão efetivamente aplicado nesta execução | Dashboard Executiva/bloco de estoque, consulta de estoque, detalhe de valor/origens, preços na ficha |
| Padrão integrado anterior preservado e retestado | Shell/r2, composição/PDF contextual, AP, Custo, oito etapas do tour |
| Ainda exigem recorte local | Formulários longos de Aduana, pagamentos/logística, texto residual operacional, densidadeAP/estoque; não houve reforma global |

## 7. Ambientes e versão efetiva

| Uso | URL / DB / storage | Estado |
|---|---|---|
| **Apresentação atual** |8082; PG5447/epic_v2_test, cluster7699897468142402968; audit-runtime/stock-executive-20261023/storage |Schema032, cópia servida com fontes8871864; sem seed ao iniciar |
| Candidato de desenvolvimento |8088; PG5445/epic_v2_test, cluster7699875696163566056; audit-lab/stock-executive-20261023/storage |Escritas e correções isoladas; não é endereço de apresentação |
| Escala |8089/5446; storage próprio scale-storage |507produtos sintéticos; não copiados à demo |
| Unitários destrutivos |PG5448/epic_v2_test, diretório postgres-unit-5448 |Isolado dos bancos5445/5447/5433 |
| Recuperação da demo anterior |audit-runtime/pre-demo-ceo-20261022; PG5433/epic_v2_test, cluster7564039176662693432; demo-storage |Build experience-r2-integration-20261023.3, fonte6911932, schema031, intacto; saiu apenas do bind8082 |

Raiz de todos os caminhos relativos de laboratório/backup/runtime: C:/Users/ricar/Desktop/projetos/EPIC. Checkout editável: Controle. Produção/epic_v2 não foi promovida nem migrada. A autorização de dados fictícios não foi usada para atingir outros ambientes por default.

HTTP conferiu build-info.json, manifesto e os bytes dos assets. ManifestoSHA256: ccdffde8486c98773f87f5bdb0416670b09cde00d1de8c089ca6cb36df7c53b9. IdentidadeDB foi consultada no servidor (nome/porta/data_directory/system_identifier), não inferida pelo banner “Teste”. Integrações financeiras externas não foram chamadas; o runtime bloqueia atualização externa da cotação.

## 8. Preservação e recuperação

### Antes de editar

Backup C:/Users/ricar/Desktop/projetos/EPIC/backups/integration-20261023-114731: **1.346arquivos protegidos** (1.102copiados +244reutilizados por verificação), incluindo WIP, arquivos novos relevantes, scripts, configuração local, aplicação/dist completo e documentos. demo-before.dump foi listado e parseado pelo pg_restore. Esse snapshot corresponde ao estado inicial, não apenas à tag antiga.

Checkpoint inicial e53f4a5093fc3edd670bbd464ba56da9edc3c339 guardou os8arquivos revisados apropriados do plano/código de integração. Centenas de imagens, relatórios históricos, PDFs e auxiliares antigos permaneceram fora do push desta rodada, **preservados separadamente**, sem apagar ou atribuir ao código novo. Não houve reset, clean, force-push ou reescrita de histórico.

### Estado final recuperável

Backup C:/Users/ricar/Desktop/projetos/EPIC/backups/stock-executive-final-20261023-131441 contém final.dump, storage, scenario/journal/manifestos/PDFs, dist e release.json. O dump foi **restaurado de fato em cluster novo5447**, nunca sobre5433 ou a operação. Antes do bind8082,6testesUI passaram em8090; depois,10em8082.293arquivos de fonte/dist/storage conferidos por hash.

SHA256 do dump:3944A6B71C47B88F22CBEA8C4FC1B3616B8DB640B06B97795640903CA151B0F9.

Fingerprint das26tabelas de negócio após seed/leituras e na cópia restaurada: cfdd239142796c826f26482416c341ea65e055924a70b64b41b5f926c70384ae. Sessão/cache/audit de acesso não entram nessa prova; não se afirma banco inteiro imutável por causa desse hash.

Para recuperação imediata da **demo anterior**, somente se necessário:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs/v2/etapa-revisao-experiencia/demo-e2e/recover-previous.ps1
~~~

O script confirma build antigo, build atual e proprietário do processo8082 antes de parar apenas o runtime novo e iniciar a cópia anterior com seu banco5433/storage. Não faz downgradeSQL nem remove5447. As guardas foram revisadas; **a troca de volta na porta8082 não foi executada**, para deixar a apresentação atual pronta. O ensaio de restauração do snapshot final em banco novo foi executado.

Para recuperação a partir do dump: criar diretório/cluster PostgreSQL vazio e porta livre; validar identidade; criar epic_v2_test; pg_restore --no-owner --no-acl nesse destino; copiar storage e dist do mesmo snapshot; apontar configuração de teste; comparar hashes/manifesto e executar smoke antes de trocar o endereço de uso. prepare-release.ps1 implementa esse padrão e recusa sobrescrever release existente. Nunca restaurar em epic_v2 ou presumir que o nome epic_v2_test torna uma base descartável.

**Separação da proteção:** código/migrations/testes/docs revisados no GitHub; banco/PDFs/configuração/dist e WIP não destinado ao público em backup local; cópia externa/offsite desses dados ainda não realizada. GitHub não é backup do PostgreSQL ou storage.

## 9. GitHub: checkpoint, implementação e fechamento

Branch: **feat/stock-executive-20261023**. Remoto público: https://github.com/Kadorium/controle_heroes.git. Não houve push de main nem mudança de visibilidade.

| Momento | Commit completo / evidência |
|---|---|
| Antes da implementação | [e53f4a5093fc3edd670bbd464ba56da9edc3c339](https://github.com/Kadorium/controle_heroes/commit/e53f4a5093fc3edd670bbd464ba56da9edc3c339); push confirmado por consulta à branch remota antes de alterar |
| Implementação principal | [74544c2a5939d4efba1c79255db461aae3cb0d4f](https://github.com/Kadorium/controle_heroes/commit/74544c2a5939d4efba1c79255db461aae3cb0d4f);73arquivos revisados, push verificado |
| **Código testado e servido** | [88718645c830b16ee4e7860eb17cc3ffbf9d58fa](https://github.com/Kadorium/controle_heroes/commit/88718645c830b16ee4e7860eb17cc3ffbf9d58fa); ajuste de origem/densidade e gates, push verificado |

Comando de verificação em cada checkpoint: git rev-parse HEAD e git ls-remote origin refs/heads/feat/stock-executive-20261023. O hash retornado pelo servidor foi igual ao local. A revisão final do documento/auxiliares é discriminada no recibo ao fim desta seção; não muda o commit do bundle servido.

<!-- FINAL_GIT_RECEIPT -->

## 10. Arquivos, pendências e DOC_DELTA

### Arquivos de explicação

- **Único retorno ao advisor:** docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md (este arquivo; conclusões, matrizes, hashes e imagens incorporadas).
- **Canônicos atualizados:** ROADMAP_V2_EPIC.md0.5.154 (B→A,300linhas, barras/denominadores inalterados); docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md0.2.38 (§8.17.1); docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md3.11. Registram execução local, contratos e limites; não avanço global por inferência.
- **Auxiliares técnicos:** demo-e2e/*.py,*.ps1,package-return.mjs; testesunitários/Playwright; logs/manifestações/hashes/imagens em audit-lab e release.json no runtime. Não são relatórios paralelos necessários ao entendimento. Scripts não executam seed ao abrir a aplicação/tour.
- Fontes principais: Catalog(pricing/commercial_read/attributes/taxonomy), Inventory(remaining_sources), contratos públicosBilling/Customs/Costing, Reporting(stock_contract/explorer/economics/views/API), Foundation(configuration/composition/schema), Identity(ACL), migration032; frontendStockExplorer/StockValueDetail/StockPositions/ExecutiveStock/ExecutiveOverview/SalesPrices; tourmanifest/steps/wait; OpenAPI gerado. Relação exata versionada abaixo.

### Pendências concretas / próxima etapa

1. Apresentador conferir maximizar/restaurar/redimensionar e legibilidade física; a aprovação anterior de imagens não cobre esta nova versão automaticamente.
2. Densidade do estoque e AP, linguagem/pluralização de Aduana e demais telas longas: melhoria local posterior, sem reabrir redesign global.
3. Preço em lote com preview e tratamento de validade existente; produção exige definição econômica ratificada, política de origens/saídas, elegibilidade, moeda/unidade e impostos. A demonstração não aprova contabilidade, avaliação fiscal, receita ou margem realizada.
4. Cópia offsite do snapshot; falha arquitetural preexistente ingestion→foundation; investigação históricaI-01 sem causa presumida. Novo percurso de chegada/recebimento passou, mas não demonstra a causa do incidente antigo.
5. Completar escritaUI positiva por perfil e fronteiras temporais mais amplas se o objetivo passar de apresentação para aceite integral. Ingestão/Onda2/IA/mídia não foram ampliadas.

DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md; docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md; docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md.
- Evidence: imagensR01–R10 e hashes incorporados neste MD; resultado de testes na seção5; provas HTTP/DB/Git nas seções7–9; auxiliares em audit-lab/stock-executive-20261023.
- Roadmap status:0.5.154, G2 técnico local com ressalvas; conferência física PENDENTE e auditoria integral PARTIAL. Livro-razão n/d e barras inalterados; nenhum novo aceiteJ#8.
- Next TODO: conferir apresentação no laptop; revisar densidade/ressalvas; ratificar regras operacionais antes de ampliar uso econômico.
- Return to advisor: docs/v2/etapa-revisao-experiencia/INTEGRACAO_EXPERIENCIA_EPIC.md.

## 11. Evidências incorporadas

Todas as capturas abaixo: **runtime8082, administrador, stock-executive-20261023.1, fonte88718645c830b16ee4e7860eb17cc3ffbf9d58fa, visualViewport.scale=1, captura automatizada Playwright**. Nenhuma é do protótipo. Imagens do tour são da repetição técnica de2s por etapa, não do ritmo de apresentação. Cada imagem tem tamanho/hash e viewport próprios. A leitura textual deste arquivo permanece suficiente caso o leitor não renderize dataURIs.
`;
const receiptText=receipt ? `**Fechamento documental/técnico:** [${receipt.local}](https://github.com/Kadorium/controle_heroes/commit/${receipt.local}).\n\nConsulta remota em ${receipt.verified_at}:\n\n\`\`\`text\nlocal:  ${receipt.local}\nremote: ${receipt.remote} refs/heads/feat/stock-executive-20261023\nresultado: IGUAIS; push confirmado no GitHub\n\`\`\`\n\nO commit acima guarda a consolidação e os auxiliares finais; o bundle continua sendo8871864. Este recibo autorreferente foi incorporado à cópia de devolutiva **após** a consulta remota, conforme o contrato do prompt. Somente esse recibo difere da versão do MD no commit; não há código de aplicação posterior não publicado. A cópia final também é preservada no backup local.` : `O código final8871864 já está publicado e verificado. O recibo do commit documental será incorporado à cópia de devolutiva após o push, sem alterar o código servido.`;
md=md.replace('<!-- FINAL_GIT_RECEIPT -->',receiptText).replace('reaud itado','reauditado');
// Readability only, before appending opaque hashes/image payloads. Never rewrite source evidence.
md=md.replace(/(\d)(SKUs?|UN|PCT|CX|PDFs?|produtos|arquivos|tabelas|documentos|testes|etapas|famílias|linhas|controles|registros|SKUs|UN|compras|faturas|produtos|passed|pass|fail|min|dias|sintéticos|Brasília)(?=\b|[,.])/g,'$1 $2')
 .replace(/(R\$|EUR|BRL)(?=\d)/g,'$1 ')
 .replace(/\b(Schema|schema|PG|porta|demo|candidate|candidato|banco|cluster|Compra|compra|pagamento|produto|pedidoA|faturaA|processoA|embarqueA|casoA|versão|prioridade)(?=\d)/g,'$1 ')
 .replace(/\b(8082|8088|8090|5447|5445|5446|5433)(?=\b)/g,'$1')
 .replace(/- (Updated|Evidence|Roadmap status|Next TODO|Return to advisor):\s*/g,'- $1: ');
const images=[
 ['R01','promoted/dashboard-1366x681.png','1366×681','Dashboard sem tour: compromisso, próxima ação e estoque na primeira dobra.','/dashboard?view=executiva'],
 ['R02','promoted/stock-1366x681.png','1366×681','Estoque padrão: grupos e valores reais; baixa densidade inicial explicitamente registrada.','/inventory/positions'],
 ['R03','promoted/product-1366x681.png','1366×681','SHOW26:42UN, duas origens econômicas; custo do saldo separado do custo da compra.','/inventory/positions?product=3'],
 ['R04','promoted/composition-1366x681.png','1366×681','Composição da compraA, base20UN, mercadoria/frete/tributos/despesas e documentos.','/inventory/positions?product=3&case=2&version=2&section=sources'],
 ['R05','promoted/document-1024x768.png','1024×768','PDF real renderizado;20UN×EUR150; origem preparadaAPI explicitada no documento.','/inventory/positions (documento contextual A-commercial.pdf)'],
 ['R06','promoted/dashboard-1920x1080.png','1920×1080','FullHD: seleção, composição e agenda civil de vencimentos com rótulos próprios.','/dashboard?view=executiva'],
 ['R07','promoted-tour/tour-2s-1.png','1366×681','Tour1/8: título e prioridade visíveis, faixa reservada e controles acessíveis.','/dashboard'],
 ['R08','promoted-tour/tour-2s-7.png','1366×681','Tour7/8: saldoSHOW26 destacado sem cobrir valores ou linha.','/inventory/positions?q=DEMO-HR-SHOW26'],
 ['R09','promoted/ap.png','1366×768','AP: saldos por moeda, obrigaçãoA vencida/parcial; não consolida moedas por soma simples.','/payables'],
 ['R10','promoted/cost.png','1366×768','Custo publicadoA:24.000, versão1, base20, câmbio documental6 e tributos brutos.','/costing/2'],
];
for(const [id,file,viewport,caption,route] of images){
 const b=readFileSync(resolve(lab,'evidence',file)),payload=b.toString('base64');
 if(!Buffer.from(payload,'base64').equals(b)||b.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')throw Error('Invalid image '+id);
 md+=`\n### ${id} — ${caption}\n\nViewport:${viewport}; rota:${route}; ${b.length}bytes; SHA256:${sha(b)}.\n\n![${id} — ${caption}](data:image/png;base64,${payload})\n`;
}
md+='\n### Prova HTTP e banco incorporada\n\n```json\n'+JSON.stringify(proof,null,2)+'\n```\n';
md+='\n### Contagens persistidas no congelamento\n\n```json\n'+JSON.stringify(validated.counts,null,2)+'\n```\n';
const files=git('diff','--name-only','e53f4a5..'+code).split('\n');
md+='\n### Relação exata de fontes/testes/auxiliares versionados na implementação\n\n```text\n'+files.join('\n')+'\n```\n\nFechamento acrescenta/atualiza: este MD, ROADMAP_V2_EPIC.md, demo-e2e/package-return.mjs, prepare-release.ps1, start-release.ps1, recover-previous.ps1, verify-release.py e e2e/stock-release.spec.ts. O WIP histórico fora dessa lista não foi descartado nem atribuído a esta implementação.\n';
const logs=['backend-final.log','frontend-final.log','backend-release.txt','build-final.log','api-drift.log','promoted-ui.log','presenter-verify.log','presenter-open.log','tour-release-timed.log','evidence/tour-release/tour-50s-itinerary.json','evidence/promoted-tour/tour-2s-itinerary.json'];
md+='\n### Integridade das evidências técnicas\n\n```text\n'+logs.map(p=>`${sha(readFileSync(resolve(lab,p)))}  ${p}`).join('\n')+'\n```\n';
md+=String.raw`
### Extrair imagens deste único arquivo (opcional)

No diretório deste MD, execute PowerShell abaixo. Ele extrai os dezPNG a partir dos próprios dataURIs, sem baixar arquivos. Compare os hashes exibidos com as legendas; a geração deste relatório já decodificou e validou assinatura/tamanho/hash dos payloads.

~~~powershell
$reportText=Get-Content -LiteralPath './INTEGRACAO_EXPERIENCIA_EPIC.md' -Raw -Encoding UTF8
$imageMatches=[regex]::Matches($reportText,'!\[(R\d+) [^\]]*\]\(data:image/png;base64,([A-Za-z0-9+/=]+)\)')
foreach($item in $imageMatches){
  $outPath=Join-Path (Get-Location) ($item.Groups[1].Value+'.png')
  if(Test-Path -LiteralPath $outPath){throw "Destino existente: $outPath"}
  [IO.File]::WriteAllBytes($outPath,[Convert]::FromBase64String($item.Groups[2].Value))
  Get-FileHash -LiteralPath $outPath -Algorithm SHA256
}
~~~

Nenhum HTML, ZIP, JSON ou outro relatório é necessário para revisar esta entrega. Os linksGitHub são prova remota dos commits; as imagens e conclusões estão no próprioMD.
`;
const out=resolve(here,'../INTEGRACAO_EXPERIENCIA_EPIC.md');writeFileSync(out,md,'utf8');
const found=[...md.matchAll(/!\[(R\d+) [^\]]*\]\(data:image\/png;base64,([A-Za-z0-9+/=]+)\)/g)];
if(found.length!==images.length)throw Error('Missing embedded evidence');
for(let i=0;i<found.length;i++)if(!Buffer.from(found[i][2],'base64').equals(readFileSync(resolve(lab,'evidence',images[i][1]))))throw Error('Extraction mismatch');
console.log(JSON.stringify({out,bytes:Buffer.byteLength(md),sha256:sha(md),embedded_images:found.length,verified_receipt:!!receipt}));
