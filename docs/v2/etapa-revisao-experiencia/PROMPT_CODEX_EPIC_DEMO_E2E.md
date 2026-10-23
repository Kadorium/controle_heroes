# EPIC — execução da experiência executiva, demonstração Heroes e testes E2E

**Modo: Agent / execução.**  
**Referências públicas consultadas em 23/10/2026.**  
**Devolutiva obrigatória: um único Markdown autocontido.**

## 1. Objetivo e autorização

Implemente a evolução aprovada da experiência executiva da EPIC, preencha o sistema com uma massa de demonstração consistente baseada em produtos Heroes e teste os percursos de negócio pela interface real.

Leia a versão mais recente de **INTEGRACAO_EXPERIENCIA_EPIC.md**, especialmente N1–N11. A proposta visual do estoque foi aprovada. Execute o pacote **P2 → T1 → C2 → E4-S1 → E4-S2 → Q3 → G2**, adaptando a sequência somente quando uma dependência técnica exigir. A limpeza de textos é a primeira entrega, e o trabalho continua até integrar estoque, custos, preços, finanças, navegação e demonstração.

O usuário declarou expressamente que **100% dos dados internos atuais são fictícios** e autorizou seu uso para testes. Você pode criar, editar e movimentar esses dados: produtos, compras, faturas, pagamentos registrados no sistema, alocações, recebimentos, estoque, custos, preços e preferências. Pode executar as migrations necessárias à implementação aprovada.

Esta autorização substitui a restrição anterior de manter a demonstração congelada. Preserve um snapshot recuperável antes de modificar banco, arquivos e runtime. As transações financeiras deste trabalho são registros internos de demonstração; mantenha integrações externas em modo simulado ou desabilitado.

Prossiga autonomamente nas escolhas de implementação. Resolva falhas encontradas e repita os testes afetados. Uma nova proposta estática ou apenas um plano não conclui esta tarefa.

## 2. Preservação e GitHub antes de começar

Confirme primeiro qual checkout, branch, runtime, banco e storage estão efetivamente em uso. O relatório anterior citava:

- Repositório: `C:\Users\ricar\Desktop\projetos\EPIC\Controle`.
- Remoto: `https://github.com/Kadorium/controle_heroes.git`.
- Runtime servido em `http://127.0.0.1:8082`, em uma cópia diferente do checkout principal.
- Build `experience-r2-integration-20261023.3`, fontes `6911932f132055e196bb0cf65d1f52e74953844b`.

Esses dados são pistas para reconfirmação. O relatório também registrava arquivos locais não rastreados e branches com referências remotas diferentes; um push antigo não comprova que todo o estado atual foi preservado.

Antes de editar:

1. Inspecione status, branch, HEAD, remotos e diferenças relevantes, incluindo arquivos novos necessários ao projeto. Preserve trabalho existente.
2. Faça backup recuperável de banco, anexos, configuração necessária à restauração e versão servida. Guarde os backups fora do repositório público e registre caminho, horário, identificação do ambiente e forma de restauração.
3. Revise o conteúdo a versionar e faça um commit de checkpoint quando houver alterações. Inclua fontes e artefatos de desenvolvimento necessários à reprodução; credenciais, dumps, caches e configurações privadas ficam fora do remoto.
4. Faça push da branch que contém o checkpoint. Confira o commit local com a referência do servidor, por exemplo usando `git rev-parse HEAD` e `git ls-remote origin refs/heads/<branch>`.
5. Se o estado já estiver integralmente versionado e publicado, registre essa igualdade em vez de criar um commit vazio.

Continue em uma branch de trabalho identificável. Preserve o histórico e resolva divergências sem force push. Se autenticação ou acesso impedirem o push, registre o erro concreto e o checkpoint local; prossiga com o trabalho independente possível. A entrega não pode ser descrita como protegida no GitHub enquanto essa verificação estiver pendente.

## 3. Experiência executiva a implementar

Preserve a direção visual já aprovada: hierarquia clara, poucos controles principais, informação útil na primeira tela e texto mínimo. Referências como Apple e ChatGPT traduzem aqui uma navegação simples e consistente; mantenha a identidade da EPIC.

### Consulta de estoque configurável

Implemente três decisões independentes:

- **Filtros:** quais produtos entram na consulta.
- **Agrupar por:** como organizar a mesma população.
- **Exibir:** quantidade, custo, venda e margem potencial, conforme disponibilidade.

O exemplo obrigatório é **(Roupas OU Raquetes OU Bolas) E Beach Tennis**. A regra é OR dentro da mesma dimensão e AND entre dimensões. Roupas e acessórios compatíveis com Beach Tennis e Padel precisam aparecer no recorte Beach Tennis, sem duplicar SKUs ou valores.

Use Beach Tennis como início da experiência para um usuário sem preferência: todos os tipos de item, agrupamento por tipo. A predominância de aproximadamente 95% foi informada pelo usuário como contexto do negócio; não a apresente como estatística calculada do estoque.

O filtro inicial deve ser visível e removível. Respeite a precedência URL explícita → visão pessoal → padrão inicial. Permita seleção múltipla, limpar filtros, agrupamento por tipo/modelo/modalidade/sem agrupamento e escolha das medidas. Alterar agrupamento ou medida conserva população e totais.

Uma seleção explicitamente vazia significa ausência de restrição nessa dimensão. IDs inválidos ou antigos devem gerar indicação de revisão, sem ampliar silenciosamente a consulta. Preserve filtros ativos e contexto ao abrir detalhes e retornar.

Reutilize o catálogo e estenda seus atributos de forma mínima e validada. Separe Bolas de Overgrips por classificação estruturada, conforme o plano, sem classificação dinâmica por palavras do nome. Unidades e embalagens precisam estar explícitas.

### Dashboard e linguagem

A primeira tela deve apresentar informação suficiente para uma conversa executiva: estoque disponível, valor a custo, valor potencial de venda, margem potencial quando calculável e compromissos financeiros.

BRL deve estar acessível e ser a apresentação inicial dos valores comerciais em reais. Obrigações em EUR preservam moeda e saldo originais; um equivalente em BRL precisa ter taxa, data e natureza identificáveis. Não some moedas diferentes diretamente.

Remova os parágrafos explicativos permanentes. Use títulos curtos, rótulos precisos, filtros junto ao bloco afetado e ajuda contextual acessível por clique e teclado. Mantenha moeda, unidade, cobertura e atualização visíveis quando mudarem a interpretação. Um campo ausente aparece como “—” ou indicação curta de cobertura, nunca como zero inventado.

## 4. Catálogo pesquisado para orientar a demonstração

Os nomes e atributos abaixo vêm de páginas públicas. Os preços são referências observadas em 23/10/2026, sujeitas a alterações, promoções e opções. **Eles não são custos de compra da EPIC nem garantem o preço de cada variante.**

A loja brasileira [Heroes Brasil](https://www.heroesbrandbrasil.com/shop/) identifica EPIC SPORT B2C LTDA no rodapé. O [site institucional EPIC](https://epicsport.com.br/) também foi consultado, mas seu catálogo não ficou disponível como texto nesta pesquisa. Para produtos, use as páginas individuais abaixo e o catálogo Heroes; não invente informação atribuída ao site institucional.

| Produto / família | Informação útil para cadastro e teste | Preço público de referência | Fonte |
|---|---|---:|---|
| Raquete SHOW 26 | Beach Tennis; carbono 3K; 20 mm; 50 cm; peso nominal 320 g ± 10; opções com/sem tratamento | R$ 3.289–3.689 | [Página do produto](https://www.heroesbrandbrasil.com/shop/raquete-de-beach-tennis-show-26/) |
| Raquete FIERCE 2026 | Beach Tennis; Silver 12K; 20 mm; 50 cm; peso nominal 325 g ± 5 | R$ 3.000–3.300 | [Página do produto](https://www.heroesbrandbrasil.com/shop/raquete-de-beach-tennis-fierce/) |
| Raquete ARION 2026 | Beach Tennis; 18K Forged; 20 mm; 50 cm; peso nominal 325 g ± 10 | R$ 3.649–4.049 | [Página do produto](https://www.heroesbrandbrasil.com/shop/raquete-de-beach-tennis-arion/) |
| Raquete AURA 2026 | Beach Tennis; Silver 21K; 22 mm; 50 cm; peso nominal 325 g ± 10 | R$ 2.800–3.100 | [Página do produto](https://www.heroesbrandbrasil.com/shop/raquete-de-beach-tennis-aura/) |
| Raquetes THE BULL 26 e STARLIGHT RUBY 26 | Outros modelos de Beach Tennis para comparar composição do estoque | R$ 3.300–3.600 e R$ 3.000–3.300, respectivamente | [Catálogo brasileiro](https://www.heroesbrandbrasil.com/shop/) |
| Raquetes FOREST e HARLEY 24 | Exemplos para uma coleção anterior e menor giro na massa fictícia | R$ 1.900 e R$ 1.599, respectivamente | [Catálogo brasileiro](https://www.heroesbrandbrasil.com/shop/) |
| Camiseta esportiva masculina THE BULL | Grade S, M, L, XL e XXL | R$ 449 | [Página do produto](https://www.heroesbrandbrasil.com/shop/camiseta-esportiva-masculina-the-bull/) |
| Moletom WAVE feminino | Tamanhos S, M e L; cores Purple e Brown anunciadas | R$ 590 na consulta | [Página do produto](https://www.heroesbrandbrasil.com/shop/moletom-wave-feminino/) |
| Saia STARLIGHT | Grade S, M, L e XL | R$ 600 na consulta | [Página do produto](https://www.heroesbrandbrasil.com/shop/saia_starlight/) |
| Mochila GRAVITY FIERCE | Acessório; unidade de venda individual | R$ 1.149 | [Página do produto](https://www.heroesbrandbrasil.com/shop/mochila-gravity-fierce/) |
| Overgrip HIGH LEVEL — pacote 3 | Pacote com 3; espessura 0,55 mm; compatível com Beach Tennis e Padel | R$ 89,90 por pacote | [Página do produto](https://www.heroesbrandbrasil.com/shop/overgrip-3un/) |
| Overgrip HIGH LEVEL — pacote 60 | Pacote com 60; opções branco/misto; espessura 0,55 mm | R$ 1.799,90 por pacote | [Página do produto](https://www.heroesbrandbrasil.com/shop/overgrip-60/) |
| Bolas Heroes — embalagem 3 | Embalagem com 3 bolas; bom caso de preço de tabela versus Pix | R$ 74,90; R$ 67,41 no Pix | [Loja Beach Tennis](https://www.lojadebeachtennis.com.br/produtos/bola-heroes-3-unidades/) |
| Bolas Heroes — embalagem 50 | Produto Stage 2 em embalagem de 50, confirmado no conteúdo indexado do fabricante | Sem preço confiável adotado | [Fabricante italiano](https://www.heroesbrandsport.com/shop/pallina-da-beach-tennis-x50/) |
| Raquete de Padel TOURO 26 e Pickleball NOVA 27 | Pequena amostra de outras modalidades para testar filtros removíveis | R$ 3.059 e R$ 1.945, respectivamente | [Catálogo brasileiro](https://www.heroesbrandbrasil.com/shop/) |

Também foi consultada a [FIERCE 2026 na BP Sport](https://bpsport.com.br/shop/beachtennis/heroes/raquete-de-beach-tennis-fierce-2026/): a página aberta apresentava R$ 3.000 e R$ 2.700 no Pix. Isso serve para testar referências de preço por fonte e condição comercial, sem tratar uma delas como tabela oficial da EPIC.

### Cuidados com a interpretação dos dados públicos

- Use SKUs internos sintéticos claramente identificados; nomes reais não autorizam inventar códigos de fábrica, EANs ou combinações comerciais como se fossem confirmadas.
- O peso técnico da raquete, em gramas, é diferente do peso logístico de 1,9 kg ou 2 kg que algumas páginas exibem. Preserve os significados dos campos.
- A embalagem com 60 overgrips tem preço por pacote. O mesmo cuidado vale para bolas em caixas de 50 e embalagens de 3.
- Um preço “de–até” não determina sozinho qual valor pertence a cada tratamento. Declare o preço escolhido para a fixture como premissa fictícia.
- O estoque anunciado no comércio eletrônico não representa o estoque interno da EPIC.
- A página da saia contém texto descritivo inconsistente com seu título. Cadastre o produto pela identidade validada e não copie descrições extensas automaticamente.
- O acesso direto à página italiana de bolas foi bloqueado nesta pesquisa, e os resultados exibiam preços/moedas inconsistentes. A embalagem pode orientar o cenário; o preço usado nele deverá ser explicitamente sintético.

## 5. Massa de dados persistida, variada e reproduzível

Aproveite o catálogo existente e complete as classificações pertinentes. Evite cadastrar a mesma identidade comercial duas vezes. Mantenha a aplicação conectada ao backend, ao banco e aos documentos reais do ambiente de teste.

Prepare uma massa representativa, usando estas dimensões como referência ajustável:

| Área | Volume e variedade sugeridos |
|---|---|
| Produtos e variantes | Cerca de 40–60 SKUs úteis entre modelos, tratamentos, grades, cores e embalagens. Ajuste o total ao catálogo validado, sem inventar combinações só para atingir uma meta. |
| Foco comercial | Predominância clara de Beach Tennis, incluindo roupas, bolas e acessórios; poucos exemplos de Padel/Pickleball para testar a flexibilidade. |
| Estoque | Vários modelos com saldo, mais de uma origem de custo para o mesmo SKU, duas localizações quando suportado e exemplos domésticos, em trânsito, entrepostados e em quarentena conforme os regimes existentes. |
| Compras e faturas | Aproximadamente 8–12 compras/faturas, distribuídas em fornecedores fictícios e datas coerentes. |
| Contas a pagar | Aproximadamente 20–30 obrigações, incluindo parcelas e despesas locais: vencidas, a vencer, pagas e parcialmente liquidadas. |
| Pagamentos | Cerca de 6–10 eventos, incluindo pagamento não alocado, alocação parcial e liquidação integral. |
| Importação e recebimentos | Cerca de 4–6 processos/embarques, com etapas concluídas e em andamento, recebimentos parciais e despesas associadas. |
| Custos e preços | Custos publicados por origem, revisões controladas, tabela de venda vigente e poucos casos explícitos de falta de custo/preço ou validade expirada. |
| Documentos | PDFs de demonstração válidos, vinculados às respectivas faturas/processos e coerentes com linhas, quantidades, moedas e totais. |

Estes volumes ajudam a preparar a demonstração; a coerência é o critério de aceite. A maioria dos produtos com saldo deve permitir uma visão financeira útil. Reserve poucos registros para casos de ausência, revisão e erro.

Defina um identificador de cenário, versão, chaves estáveis e uma data-base D. D deve usar a data da execução no fuso do sistema, registrado no manifesto. Use vencimentos relativos, por exemplo D−15, D−7, D+5, D+30 e D+60. A demonstração precisa continuar plausível quando for regenerada.

O seed deve ser idempotente: executá-lo novamente não duplica compras, obrigações, movimentos nem pagamentos. A limpeza fica limitada aos registros identificados como pertencentes ao cenário e respeita dependências. Preserve registros de outros trabalhos.

Crie os dados por APIs, comandos ou serviços de domínio apropriados. Evite escrever diretamente em saldos derivados para simular um resultado. A versão final deve sobreviver a recarga e reinicialização.

Gere uma fixture de escala separada, com mais de 500 registros relevantes, para paginação, totais e desempenho. Ela não precisa permanecer na massa apresentada ao CEO.

## 6. Premissas econômicas para a demonstração

Para executar as recomendações de N5/N8 sem outra rodada de planejamento, adote as seguintes premissas **somente como configuração documentada de demonstração e teste**. Elas não constituem aprovação de política contábil definitiva da EPIC.

- **Origem do saldo:** respeite a origem explícita de cada movimento. Para saídas sem origem definida no cenário, use PEPS gerencial e identifique o resultado como estimado quando essa distinção for necessária.
- **Custo:** utilize o custo publicado aplicável à origem/linha e à sua quantidade remanescente. Preserve natureza, versão, cobertura e estado do custo. O último custo do SKU não substitui automaticamente o custo de todas as origens.
- **Preço:** utilize uma tabela demonstrativa Varejo/Venda direta/BRL, com validade e unidade de venda definidas. Os preços de referência podem inspirar essa tabela, identificada como fictícia.
- **População:** custo pode ter recortes por regime; potencial de venda e margem usam saldo elegível para venda. Quarentena, reserva e estoque indisponível não entram silenciosamente como disponíveis.
- **Venda potencial:** soma da quantidade elegível multiplicada pelo preço válido e compatível com a unidade.
- **Margem potencial:** diferença entre venda potencial e custo comparável, dividida pela venda potencial, antes de despesas de venda. Calcule sobre os totais da mesma população; não faça média simples das margens dos produtos.
- **Cobertura:** se parte do saldo não possui custo, preço, taxa ou unidade compatível, mostre cobertura parcial e calcule apenas a população comparável. Dado desconhecido não equivale a zero.
- **Moedas:** preserve valores originais. Diferencie taxa de custo, taxa de pagamento e referência usada para exibição consolidada. Taxas artificiais precisam constar no manifesto do cenário.
- **Embalagens:** conversões exigem fator explícito e compatibilidade de produto. Não some UN, CX e PCT como uma única quantidade nem converta implicitamente preço de pacote em preço individual.

Deixe essas definições no relatório técnico e em ajuda contextual curta quando necessária. Não transforme a página inicial em um manual.

## 7. Cenário numérico obrigatório para reconciliação

Crie um cenário isolável, por exemplo **DEMO-SHOW26-ORIGENS**, com um SKU da SHOW 26. O nome do modelo é real; todos os movimentos, custos, despesas, taxas e o preço escolhido abaixo são fictícios.

### Preparação e resultado esperado

| Elemento | Compra A | Compra B |
|---|---:|---:|
| Quantidade recebida em unidades | 20 | 30 |
| Preço de aquisição fictício | EUR 150/un. | EUR 170/un. |
| Fatura de mercadorias | EUR 3.000 | EUR 5.100 |
| Taxa de custo fictícia | R$ 6/EUR | R$ 6/EUR |
| Mercadorias convertidas | R$ 18.000 | R$ 30.600 |
| Frete atribuído | R$ 2.000 | R$ 3.000 |
| Tributos fictícios atribuídos | R$ 3.000 | R$ 5.400 |
| Outras despesas atribuídas | R$ 1.000 | R$ 1.500 |
| Custo total publicado | R$ 24.000 | R$ 40.500 |
| Custo unitário | R$ 1.200 | R$ 1.350 |

Registre o recebimento da compra A em duas etapas, 12 e 8 unidades, validando o saldo após cada uma. Conclua o recebimento das 30 unidades da compra B. Depois registre uma saída de 8 unidades conforme a regra PEPS gerencial do cenário.

O resultado final esperado para este recorte é:

| Medida | Resultado |
|---|---:|
| Saldo da origem A | 12 un. |
| Saldo da origem B | 30 un. |
| Estoque elegível total | **42 un.** |
| Custo do saldo | **R$ 54.900,00** |
| Custo médio de exibição | **R$ 1.307,14/un.** |
| Preço de venda escolhido para a fixture | **R$ 3.289,00/un.** |
| Venda potencial | **R$ 138.138,00** |
| Diferença entre venda potencial e custo | **R$ 83.238,00** |
| Margem potencial | **60,26%** |

Conserve precisão interna. O custo médio arredondado para exibição não deve ser multiplicado de volta para substituir o total por origem.

Na conta a pagar da compra A, com vencimento D−7:

1. Confirme EUR 3.000 em aberto.
2. Registre um pagamento fictício de EUR 1.000 ainda sem alocação: o saldo da obrigação continua EUR 3.000.
3. Aloque os EUR 1.000 à obrigação: o saldo passa para **EUR 2.000**, parcialmente pago e vencido.
4. A obrigação da compra B, com vencimento D+45, permanece em **EUR 5.100**.
5. O total em aberto das duas obrigações é **EUR 7.100**, mantendo os recortes de vencimento corretos.

Fretes e despesas locais seguem suas próprias obrigações quando o modelo exigir; não duplique essas despesas na fatura em EUR. Os tributos da fixture são valores de teste e não uma simulação tributária validada.

Mantenha resultados esperados em um manifesto independente e confira UI, API e persistência. Gerar o “esperado” chamando a mesma função que está sob teste não comprova a reconciliação.

Se alguma operação necessária ainda não tiver UI, prepare essa parte por serviço de domínio e identifique a limitação. Não declare o percurso inteiro como executado pela interface.

## 8. Testes E2E realistas na aplicação implementada

Faça um inventário breve das funcionalidades realmente disponíveis e cubra os módulos relevantes à apresentação. Aprofunde os percursos abaixo com diferentes perfis.

Nos fluxos principais, automatize o navegador usando a stack de testes existente, com backend, banco e documentos reais do ambiente. A preparação por API é permitida, mas o teste de uma operação pela UI deve preencher o formulário, salvar, observar o resultado, recarregar e conferir persistência.

Respostas HTTP interceptadas ou bancos exclusivamente em memória servem a testes específicos de erro ou unidade; identifique-os separadamente. Os testes antigos do desenho/protótipo não validam esta implementação.

| Percurso | Operação e verificação obrigatória |
|---|---|
| 1. Entrada do executivo | Abrir dashboard com dados úteis, valores em BRL e saldos estrangeiros identificados. Abrir o detalhe de um indicador e reconciliar a população. Testar também usuário sem preferência salva. |
| 2. Estoque transversal | Selecionar Beach Tennis + Roupas/Raquetes/Bolas, alternar agrupamento e medidas, ordenar e paginar. Confirmar os mesmos IDs e totais ao mudar somente a apresentação. |
| 3. Filtros e preferências | Remover Beach Tennis, incluir outra modalidade, limpar a seleção, salvar visão, recarregar, entrar com outro usuário e abrir URL explícita. Confirmar precedência e ausência de vazamento entre usuários. |
| 4. Multimodalidade e unidades | Incluir vestuário/acessório Beach Tennis + Padel sem duplicação. Conferir preço e quantidade de bolas em CX50, pacote 3 e overgrips em pacotes 3/60, sem conversão implícita. |
| 5. Cadastro | Criar ou editar um produto/variante de teste pela UI, com classificação e unidade corretas; validar campos inválidos e confirmar persistência. Verificar reflexo nas facetas. |
| 6. Preços | Criar preço vigente e testar preço ausente/expirado. Executar importação com preview se implementada no pacote: arquivo válido, erro por linha, correção, confirmação e repetição sem duplicação. |
| 7. Compra e obrigação | Criar pedido/fatura pela UI existente, conferir linhas, quantidades, moeda, vencimento e contas a pagar geradas. Validar arredondamento e total da fatura. |
| 8. Pagamento e alocação | Registrar pagamento, conferir o estado não alocado, alocar parcialmente e liquidar outra obrigação. Validar bloqueio de alocação excedente e reflexo no dashboard/agenda. |
| 9. Embarque e recebimento | Percorrer os estados suportados de processo/embarque, liberação e recebimento parcial. Conferir estoque por localização/regime e impedir duplicação por reenvio. |
| 10. Custo por origem | Publicar custos e executar o cenário numérico. Revisar um componente em cenário separado e conferir a versão aplicada, a cobertura e o efeito somente nos saldos correspondentes. |
| 11. PDF e navegação | Abrir PDF real vinculado à fatura e comparar com o registro. Retornar ao produto/estoque preservando filtros, agrupamento, medidas, página e contexto de navegação. |
| 12. Permissões | Usar perfis de administrador, comprador, aduana e estoque disponíveis. Confirmar permissões na UI e no servidor para uma leitura e uma escrita relevantes por perfil; não testar tudo somente como admin. |
| 13. Falhas e recuperação | Validar erro de formulário, indisponibilidade de API, documento ausente, resposta lenta e duplo clique de envio. Apresentar mensagem curta, possibilidade de recuperação e ausência de transação duplicada. |
| 14. Datas e cobertura | Conferir vencidos/atuais/futuros, fronteiras de dia/mês, custo ausente, preço sem validade e seleção sem resultados. Alterar um filtro deve afetar somente os blocos aos quais ele se aplica. |
| 15. Escala | Testar mais de 500 registros, paginação e totais do conjunto filtrado completo. Verificar que limites da API ou paginação não reduzem silenciosamente os indicadores. |
| 16. Demonstração guiada | Navegar pelos módulos e registros reais da massa, abrir detalhes e retomar o tour. Validar pausa/retomada/saída, foco e dimensionamento dos destaques no laptop. |
| 17. Consultas sem efeitos colaterais | Abrir catálogo, facetas, estoque e dashboard e confirmar ausência de escritas de negócio disparadas por GETs. Trate o comportamento de criação de taxonomia identificado no plano antes de reutilizá-lo na navegação. |

Para operações mutáveis, use identificadores únicos e verifique efeitos persistidos. Teste reenvio e idempotência onde existe risco concreto de duplicação. Registre esperado, observado e evidência de cada caso; “clicou sem erro” é insuficiente.

Corrija as falhas encontradas dentro do escopo e reexecute os testes afetados. Marque com precisão o que passou, falhou, ficou bloqueado ou foi preparado fora da UI.

## 9. Verificação visual, tour e estado final

Valide a aplicação entregue em **1366×681, 1366×768, 1920×1080 e 1024×768**, além do viewport efetivo se disponível. Confira dashboard, estoque, filtros, tabelas, formulários, PDF e sobreposições do tour.

O conteúdo principal deve aproveitar o espaço do laptop. Evite modais estreitos para fluxos extensos, cards vazios sem função, colunas cortadas e rolagem horizontal desnecessária. Verifique teclado, foco, contraste, carregamento e mensagens de erro curtas.

Atualize a demonstração guiada para os dados preenchidos: perguntas como “quanto há em estoque?”, “qual é o custo?”, “quanto vence?” e “quais modelos compõem o saldo?” devem levar a interações úteis. Use poucas palavras por etapa e permita ao usuário explorar e retornar. A navegação do tour deve preservar os dados; as operações de teste ficam nos cenários controlados.

Ao terminar:

- Deixe uma massa principal coerente e populada no ambiente que o usuário realmente abre.
- Remova ou isole resíduos dos testes destrutivos e da fixture de escala.
- Mantenha os poucos casos de exceção necessários para demonstrar cobertura e recuperação.
- Reconfirme runtime, banco, migrations e build efetivamente servidos.
- Execute um smoke test final após a atualização do runtime: dashboard → estoque filtrado → produto → compra/custo → PDF → retorno; confira também contas a pagar e visão salva.
- Registre o que foi validado em viewport automatizado e o que dependeria de conferência física do laptop.

Uma versão aprovada apenas no worktree, sem estar acessível no endereço de uso, não encerra a entrega.

## 10. Commit, push e devolutiva final

Depois da implementação e dos testes, revise o diff e versione código, migrations, seeds, fixtures sintéticas necessárias, testes e documentação pertinente. Faça commit e push. Verifique novamente a igualdade entre o commit local e a referência remota correta.

Registre a branch, o hash completo, o comando de verificação e seu resultado, os commits envolvidos e qualquer arquivo relevante que tenha permanecido fora do controle de versão, com motivo. Não exponha credenciais no relatório.

Garanta que o relatório identifique a versão do código efetivamente testada e servida. Se a documentação gerar um commit posterior, diferencie o commit da implementação e o da documentação, evitando um ciclo de autorreferência de hashes. A cópia final de devolutiva pode ser gerada após a verificação do push.

**Entregue exatamente um arquivo: INTEGRACAO_EXPERIENCIA_EPIC.md.**

Ele deve ser autocontido e trazer, de forma objetiva:

1. Estado da entrega, URL de acesso, build e como iniciar ou retomar a demonstração.
2. Mudanças implementadas e decisões relevantes de UI/UX.
3. Massa criada, data-base, identificador/versão do cenário e comando para reproduzi-la.
4. Fontes públicas e distinção entre catálogo real, preços de referência e valores internos fictícios.
5. Premissas de custo, preço, disponibilidade, moeda e margem.
6. Reconciliação numérica com valores esperados e observados.
7. Matriz de testes realmente executados: passou/falhou/bloqueado, perfil, ambiente e limitações.
8. Capturas da aplicação final incorporadas no próprio Markdown, sem depender de arquivos de imagem externos.
9. Problemas encontrados, correções realizadas e pendências materiais.
10. Preservação e restauração: localização dos backups e procedimento verificado.
11. Evidência de commit e push antes e depois, incluindo correspondência com as referências remotas.
12. Relação breve dos arquivos de explicação criados ou atualizados nesta rodada, para que nada fique escondido em outra entrega.

Arquivos técnicos necessários podem existir no repositório, mas a explicação para o usuário deve estar toda nesse único MD. Consolide a versão atual no início e reduza o histórico a referências úteis. Não gere outro relatório, proposal.html, ZIP ou documento de instruções como dependência da devolutiva.

**Critério de conclusão:** aplicação implementada e populada, navegação executiva funcional, testes reais com resultados reconciliados, versão de uso conferida e estado preservado no GitHub com push comprovado. Se houver um impedimento externo, descreva exatamente o que falta e entregue todas as partes concluídas sem declarar o pacote integralmente aprovado.

