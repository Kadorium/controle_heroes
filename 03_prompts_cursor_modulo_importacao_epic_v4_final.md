# 03 — Prompt mestre para Cursor · Módulo de Importação Epic v4 final

## Objetivo

Este arquivo deve comandar a construção do MVP do módulo de importação da Epic no Cursor.

O Cursor deve construir um sistema simples, local, auditável e evolutivo para controlar importações da Epic com a Heroes, fabricação na China, despacho aduaneiro no Brasil, controle financeiro, logística, nacionalização, estoque mínimo, conciliação e landed cost.

Não transformar este projeto em ERP completo. Não começar codando sem checklist e regras permanentes.

---

## Prioridade do MVP

1. Controle financeiro da importação.
2. Invoices, proformas, `ANTECIPO`, pagamentos, saldos, descontos, créditos e conta corrente Brasil.
3. Itens/SKUs e quantidades por etapa.
4. Logística por modal, principalmente navio e avião.
5. Aduana, DI/DUIMP, impostos, despachante e despesas Brasil.
6. Nacionalização.
7. Entrada mínima em estoque.
8. Conciliação Brasil x Itália x despachante x banco.
9. Landed cost estimado, revisado, preliminar e final.
10. Fechamento auditável e reabertura controlada.

---

## Restrição de documentação

Não criar muitos arquivos `.md`.

Arquivos obrigatórios de controle:

1. `CURSOR_RULES_IMPORTACAO_EPIC.md`
2. `CHECKLIST_MVP_IMPORTACAO_EPIC.md`

Toda regra, matriz, decisão, lacuna, evidência, teste, instrução local, backup, restauração e critério de aceite deve ficar nesses dois arquivos, salvo necessidade técnica real.

Se o Cursor quiser criar outro `.md`, deve justificar antes. Preferência: atualizar os dois arquivos obrigatórios.

---

# PROMPT INICIAL — criar regras permanentes e checklist vivo antes de qualquer código

Você é arquiteto de software sênior, product manager e especialista em ERP modular para varejo, comércio exterior, controle financeiro de importações, landed cost, conciliação operacional e implantação pragmática de sistemas em empresas pequenas.

Leia os arquivos existentes do projeto, principalmente:

- o blueprint final do sistema de controle de importação Epic
- o resumo executivo do módulo de importação Epic
- este arquivo de prompts do Cursor

Antes de escrever qualquer código, crie ou atualize estes dois arquivos:

1. `CURSOR_RULES_IMPORTACAO_EPIC.md`
2. `CHECKLIST_MVP_IMPORTACAO_EPIC.md`

Não avance para implementação se esses dois arquivos não incorporarem todos os requisitos abaixo.

---

## 1. Regras permanentes do Cursor

Crie `CURSOR_RULES_IMPORTACAO_EPIC.md` com as regras abaixo.

### 1.1 Escopo e objetivo

- Empresa: Epic.
- Matriz/parceira italiana: Heroes.
- Fabricação: China.
- Há empresa brasileira de aduana/despachante.
- Sistema inicial: web app local em rede interna.
- Objetivo do MVP: controle financeiro, invoices, pagamentos, itens, logística, aduana, nacionalização, estoque mínimo, conciliação e landed cost.
- Não construir ERP completo no MVP.
- Não criar segurança enterprise pesada.
- Não usar Excel, Access ou SQLite como base oficial multiusuário.
- Excel pode ser fonte de importação ou exportação, nunca base oficial.

### 1.2 Arquitetura local obrigatória

A primeira versão deve rodar em um PC da Epic na rede interna.

Modelo obrigatório:

- Um PC da Epic será o servidor local.
- Backend/API roda nesse PC.
- PostgreSQL roda nesse PC.
- Frontend é servido por esse PC.
- Funcionários acessam pelo navegador via rede interna.
- Exemplos de acesso: `http://192.168.x.x:porta` ou `http://epic-importacoes:porta`.
- Nenhum funcionário deve instalar o sistema localmente.
- Cada funcionário deve acessar com login e senha próprios.
- Toda alteração deve registrar o usuário autenticado.
- Não usar Docker nesta fase.

Requisitos técnicos mínimos:

- Criar forma simples de iniciar o sistema no PC servidor.
- Se possível, permitir reinício automático após reboot do PC.
- Incluir instruções no checklist para instalação local.
- Incluir instruções no checklist para acesso pela rede interna.
- Prever firewall do Windows para liberar a porta usada.
- Prever IP fixo ou reserva de IP no roteador.
- Prever pasta local organizada para anexos.
- Prever backup automático do banco e dos documentos.

Se for sugerida arquitetura diferente, justificar por simplicidade, risco operacional, backup, multiusuário e manutenção.

### 1.3 Regras de dados

- Campo vazio nunca vira zero.
- Valor desconhecido deve ficar como `null`, `missing` ou `pending_review`.
- Dado bruto nunca entra como dado oficial.
- Todo dado importado passa por bruto, staging e revisão antes de virar oficial.
- Dado oficial não deve ser deletado fisicamente.
- Dado oficial deve ser anulado, cancelado ou inativado com motivo e log.
- Documento bruto importado não pode ser apagado.
- Arquivo recebido não pode ser sobrescrito.
- Documento substituído mantém histórico.
- Toda importação de arquivo guarda origem, data, usuário, nome/hash e versão.
- Toda migração de banco deve ser rastreável.
- Fazer backup antes de migração relevante.

### 1.4 Flexibilidade operacional

O sistema não deve assumir fluxo linear.

Deve permitir:

- pedido inicialmente por navio e depois alterado para avião;
- pedido parcialmente por navio e parcialmente por avião;
- pedido dividido em múltiplos embarques;
- ordem com 3 faturas ou mais;
- fatura inicial de `ANTECIPO` até cerca de 1 ano antes da chegada;
- câmbio previsto diferente do efetivo;
- desconto europeu que vira crédito ou conta corrente no Brasil;
- despesa nova após fechamento preliminar;
- custo estimado diferente do realizado;
- reabertura de importação fechada.

Regra central:

- Mudança operacional ou financeira é permitida.
- Mudança crítica nunca sobrescreve histórico.
- Mudança crítica exige usuário, data/hora, motivo, valor anterior, valor novo, documento de suporte quando aplicável e impacto estimado.

### 1.5 Logs

Criar dois tipos de log:

1. Audit log de negócio.
2. Log técnico do sistema.

Audit log obrigatório para:

- alteração de modal logístico;
- alteração de custo;
- alteração de invoice;
- alteração de pagamento;
- alteração de câmbio;
- alteração de desconto;
- criação ou uso de crédito;
- conta corrente Brasil;
- alteração de status;
- alteração, substituição, anulação ou cancelamento de documento;
- aprovação ou rejeição;
- fechamento;
- reabertura;
- nacionalização;
- entrada em estoque.

Campos mínimos do audit log:

- usuário;
- data/hora;
- entidade;
- entidade_id;
- campo alterado;
- valor anterior;
- valor novo;
- motivo obrigatório;
- documento de suporte, quando aplicável;
- impacto estimado, quando aplicável.

Log técnico obrigatório para:

- falha de login;
- erro de importação;
- erro de backup;
- erro de restauração;
- erro de banco;
- falha de permissão;
- erro de cálculo;
- erro de upload/anexo.

### 1.6 Backup e restauração

Criar rotina de backup desde o MVP.

Mínimo obrigatório:

- backup diário automático do PostgreSQL;
- backup diário da pasta de anexos/documentos;
- retenção mínima de 30 dias;
- pasta de backup separada da pasta principal do sistema;
- opção de cópia adicional para HD externo, NAS ou pasta sincronizada;
- log de sucesso/falha de backup;
- script ou procedimento simples de restauração;
- teste de restauração documentado;
- backup manual antes de migrações relevantes.

Checklist deve ter seção específica para:

- backup implementado;
- backup testado;
- restauração testada;
- documentos incluídos no backup;
- logs de backup visíveis;
- retenção configurada.

### 1.7 Invoices, faturas e `ANTECIPO`

Uma importação pode ter várias invoices/faturas/proformas.

Uma invoice pode ter vários pagamentos.

Tipos mínimos de invoice:

- `ANTECIPO`
- `PROFORMA`
- `SALDO`
- `COMPLEMENTAR`
- `AJUSTE`
- `CREDITO`
- `OUTRA`

Regra para `ANTECIPO`:

- normalmente emitida quando o pedido é fechado;
- pode ocorrer cerca de 1 ano antes da chegada;
- inicia pedido/produção;
- vinculada ao pedido/importação;
- pode não estar vinculada ao embarque final;
- pode ter câmbio previsto diferente do efetivo;
- impacta saldo financeiro;
- permanece vinculada à importação até o fechamento.

Campos mínimos de invoice:

- tipo;
- número;
- data;
- fornecedor;
- moeda;
- valor;
- itens vinculados, se houver;
- importação vinculada;
- status;
- pagamentos vinculados;
- saldo;
- câmbio previsto;
- câmbio efetivo;
- documento anexado;
- observações;
- log de alterações.

### 1.8 Pagamentos e financeiro

- Suportar pagamento antecipado, parcial, saldo e ajuste.
- Suportar múltiplos pagamentos por invoice.
- Suportar pagamentos em datas diferentes.
- Suportar câmbios diferentes por pagamento.
- Nenhum pagamento sem comprovante ou justificativa aprovada.
- Nenhum desconto sem origem documental.
- Nenhum crédito sem origem, saldo e uso rastreável.
- Fechamento financeiro só pode ocorrer com documentos mínimos, conciliações resolvidas ou exceção aprovada.

### 1.9 Câmbio versionado

Não existe apenas “o câmbio da importação”.

Campos/conceitos mínimos:

- câmbio previsto no pedido;
- câmbio previsto revisado;
- câmbio efetivo do pagamento;
- câmbio usado no landed cost;
- data de referência;
- fonte da taxa;
- usuário que informou;
- motivo da alteração;
- diferença cambial estimada;
- diferença cambial realizada.

Regras:

- câmbio vazio não vira zero;
- alteração de câmbio gera log;
- alteração relevante exige motivo;
- preservar câmbio usado em cada pagamento;
- preservar câmbio usado em cada versão de cálculo;
- histórico não pode ser recalculado silenciosamente com câmbio novo.

### 1.10 Descontos, créditos e conta corrente Brasil

Separar desconto, crédito e conta corrente.

Tipos mínimos:

1. Desconto direto na invoice.
2. Desconto por item.
3. Desconto global.
4. Crédito concedido pela Heroes.
5. Crédito acumulado para uso futuro.
6. Conta corrente/compensação no Brasil.
7. Ajuste financeiro manual aprovado.

Regras:

- desconto direto reduz invoice/custo conforme regra definida;
- crédito não vira desconto automaticamente;
- conta corrente Brasil tem controle próprio;
- uso de crédito reduz saldo disponível;
- crédito não pode ser usado duas vezes;
- crédito/conta corrente exige origem documental;
- crédito europeu convertido em conta corrente Brasil deve registrar potencial impacto financeiro/fiscal;
- tratamento adotado deve ser classificado;
- justificativa e aprovação são obrigatórias quando houver impacto relevante.

Campos mínimos:

- origem;
- tipo;
- valor original;
- moeda;
- data;
- documento de suporte;
- importação/invoice de origem;
- saldo disponível;
- saldo utilizado;
- onde será utilizado;
- impacto financeiro estimado;
- impacto fiscal estimado;
- custo adicional estimado;
- responsável;
- aprovador;
- status;
- histórico de uso.

Status mínimos:

- disponível;
- usado parcialmente;
- usado;
- cancelado;
- em disputa;
- pendente de aprovação.

### 1.11 Planejado, revisado e realizado

Separar planejado, revisado e realizado para:

- custo de produto;
- frete;
- seguro;
- impostos;
- despesas Brasil;
- despesas do despachante;
- câmbio;
- prazo;
- ETA;
- ETD;
- modal;
- pagamentos;
- landed cost;
- entrada em estoque.

Definições:

- Planejado: visão inicial no fechamento do pedido.
- Revisado: visão alterada por mudança de condição.
- Realizado: valor/data final com documento.

Regra:

- O sistema deve sempre permitir comparar planejado vs revisado vs realizado.

### 1.12 Logística e alteração de modal

Suportar pelo menos:

- `AIR`
- `OCEAN`
- `OTHER`

Alteração de modal depois do pedido deve ser permitida, mas controlada.

Regras:

- alteração exige motivo;
- alteração gera log;
- modal anterior é preservado;
- custo estimado é recalculado;
- prazo estimado é recalculado;
- impacto financeiro é registrado;
- impacto operacional é registrado;
- alteração pode exigir aprovação conforme custo/impacto.

Modelo deve permitir:

- uma ordem com um embarque;
- uma ordem com múltiplos embarques;
- uma ordem parcialmente por navio e parcialmente por avião;
- embarques adicionais após planejamento inicial;
- custos diferentes por modal;
- documentos obrigatórios diferentes por modal.

Campos mínimos para alteração de modal:

- modal anterior;
- modal novo;
- data da alteração;
- responsável;
- motivo;
- custo estimado anterior;
- custo estimado novo;
- prazo estimado anterior;
- prazo estimado novo;
- diferença estimada;
- documento/e-mail de suporte;
- status de aprovação.

### 1.13 Aduana, nacionalização e estoque mínimo

O MVP deve conter controle mínimo de nacionalização e entrada em estoque.

Objetivo:

- saber quais itens foram nacionalizados;
- saber quais itens estão disponíveis para estoque;
- saber custo final por SKU;
- manter vínculo entre importação, SKU, DI/DUIMP e estoque.

Regras:

- nacionalização não ocorre sem DI/DUIMP ou processo aduaneiro válido;
- imposto/taxa exige documento;
- despesa do despachante exige evidência;
- entrada em estoque depende de nacionalização;
- quantidade em estoque não pode exceder quantidade nacionalizada sem justificativa;
- divergência de quantidade vai para conciliação.

MVP de estoque deve conter:

- evento de nacionalização;
- quantidade nacionalizada por SKU;
- evento de entrada em estoque;
- quantidade recebida em estoque;
- custo unitário aprovado;
- vínculo com landed cost final;
- data;
- responsável;
- documento;
- divergência, se houver.

### 1.14 Quantidades por etapa

Rastrear por SKU:

- quantidade pedida;
- quantidade faturada;
- quantidade embarcada;
- quantidade nacionalizada;
- quantidade recebida em estoque;
- diferença;
- justificativa da diferença;
- status da conciliação.

Regras:

- divergência de quantidade vai para conciliação;
- entrada em estoque não pode exceder nacionalizado sem justificativa;
- nacionalização exige documento;
- quantidade vazia não vira zero.

### 1.15 Landed cost versionado

Landed cost deve ter versões.

Versões mínimas:

- estimativa inicial;
- estimativa revisada;
- preliminar;
- final;
- final reaberto/revisado.

Regras:

- cada versão registra data, usuário, motivo e premissas;
- nova versão não apaga versão anterior;
- mudança de modal, câmbio, imposto, despesa ou crédito pode gerar nova versão;
- custo final por SKU deve ser rastreável;
- critério de rateio deve ficar explícito;
- fechamento aponta qual versão de landed cost foi aprovada.

### 1.16 Reabertura de importação fechada

Reabertura deve ser permitida, mas controlada.

Regras:

- apenas usuário autorizado pode reabrir;
- reabertura exige motivo;
- reabertura gera log;
- fechamento anterior permanece preservado;
- novo fechamento gera nova versão;
- sistema mostra histórico de fechamentos;
- importação reaberta não apaga dados anteriores.

Status mínimos:

- fechado;
- reaberto;
- fechado revisado;
- fechado com divergência aprovada.

### 1.17 Permissões por ação crítica

Além de permissões por módulo, controlar ações críticas.

Exigem permissão específica:

- alterar modal;
- alterar câmbio;
- alterar valor de invoice;
- aprovar desconto;
- criar crédito;
- usar crédito;
- aprovar conta corrente Brasil;
- registrar pagamento;
- aprovar pagamento sem comprovante;
- registrar imposto;
- nacionalizar produto;
- dar entrada em estoque;
- fechar importação;
- reabrir importação;
- aprovar divergência;
- cancelar/anular documento;
- rodar migração;
- restaurar backup.

### 1.18 Anulação em vez de exclusão

Dados oficiais não devem ser deletados fisicamente.

Devem ser anulados, cancelados ou inativados com motivo e log.

Aplica-se a:

- invoice;
- pagamento;
- despesa;
- imposto;
- documento;
- crédito;
- entrada de estoque;
- fechamento;
- landed cost;
- embarque;
- conciliação.

### 1.19 Conciliação obrigatória

Conciliações mínimas:

- planilha Heroes vs invoice;
- invoice vs pedido;
- invoice vs pagamento bancário;
- pagamento previsto vs realizado;
- desconto informado vs desconto aplicado;
- crédito informado vs crédito usado;
- conta corrente Brasil vs créditos de origem;
- embarque vs documentos logísticos;
- despachante vs despesas;
- imposto calculado vs imposto pago;
- quantidade pedida vs faturada vs embarcada vs nacionalizada vs estocada;
- custo estimado vs custo realizado;
- landed cost preliminar vs final.

Status mínimos:

- conciliado;
- divergente;
- pendente de documento;
- pendente de aprovação;
- ajuste manual aprovado;
- ignorado com justificativa.

Divergência relevante bloqueia fechamento ou exige aprovação formal.

### 1.20 Testes e UI

- Sempre criar ou atualizar testes ao implementar regra crítica.
- Sempre atualizar o checklist após implementar.
- Todo item `DONE` precisa ter evidência e teste associado.
- UI deve ser testada no browser interno do Cursor quando houver interface.
- Antes de testar UI, iniciar o servidor local.
- Não declarar fase concluída sem build/testes/checklist.

---

## 2. Checklist vivo obrigatório

Crie `CHECKLIST_MVP_IMPORTACAO_EPIC.md` com esta estrutura.

Cada item deve ter:

- ID;
- módulo;
- regra/requisito;
- prioridade: `P0`, `P1`, `P2`;
- status: `TODO`, `PARTIAL`, `DONE`, `BLOCKED`;
- dependência;
- evidência;
- teste associado;
- observação.

Seções obrigatórias:

1. Escopo do MVP.
2. Fora de escopo.
3. Arquitetura local sem Docker.
4. Instalação no PC servidor da Epic.
5. Acesso pela rede interna.
6. Configuração de porta/firewall/IP.
7. Banco PostgreSQL local.
8. Pasta local de documentos/anexos.
9. Backup diário do banco.
10. Backup diário de anexos.
11. Teste de restauração.
12. Usuários, papéis e permissões.
13. Permissões por ação crítica.
14. Dados brutos, staging e oficiais.
15. Importação da planilha Heroes.
16. Revisão humana e fila de pendências.
17. Importações/pedidos.
18. SKUs/itens.
19. Quantidades pedidas, faturadas, embarcadas, nacionalizadas e estocadas.
20. Invoices/proformas/faturas.
21. Tipo `ANTECIPO`.
22. Múltiplas invoices por importação.
23. Múltiplos pagamentos por invoice.
24. Pagamentos antecipados, parciais e saldo.
25. Câmbio previsto, revisado e efetivo.
26. Descontos.
27. Créditos Heroes.
28. Conta corrente Brasil.
29. Despesas Brasil.
30. Logística aérea.
31. Logística marítima.
32. Alteração de modal com log.
33. Múltiplos embarques por importação.
34. Aduana, DI/DUIMP e despachante.
35. Impostos e taxas.
36. Nacionalização.
37. Entrada mínima em estoque.
38. Landed cost versionado.
39. Rateio por SKU.
40. Conciliação operacional e financeira.
41. Documentos obrigatórios por etapa.
42. Audit log de negócio.
43. Log técnico.
44. Anulação/cancelamento em vez de exclusão.
45. Fechamento sem divergência.
46. Fechamento com divergência aprovada.
47. Reabertura de importação fechada.
48. Seed/massa de teste.
49. Testes automatizados.
50. Teste manual no browser interno.
51. Relatório de lacunas.
52. Critérios de pronto.

Não avançar para implementação se esses blocos não existirem no checklist.

---

# PROMPT 1 — transformar checklist em plano executável dentro do próprio checklist

Use `CURSOR_RULES_IMPORTACAO_EPIC.md` e `CHECKLIST_MVP_IMPORTACAO_EPIC.md` como fonte obrigatória.

Objetivo:

- transformar o checklist em plano de execução, sem criar novos `.md`;
- ordenar módulos por dependência;
- identificar o caminho mais curto para demo operacional;
- manter foco em controle financeiro e governança.

Atualize o checklist com:

- ordem de implementação;
- dependências;
- riscos;
- critérios de pronto por etapa;
- itens que podem ficar pós-MVP;
- itens bloqueados por decisão de negócio.

Ordem preferencial:

1. Arquitetura local.
2. Banco, usuários, permissões e auditoria.
3. Importações, SKUs e invoices.
4. Financeiro: pagamentos, saldos, câmbio, descontos, créditos.
5. Documentos/anexos.
6. Logística navio/avião e alteração de modal.
7. Aduana/DI/DUIMP.
8. Nacionalização e estoque mínimo.
9. Landed cost versionado.
10. Conciliação.
11. Fechamento e reabertura.
12. Backup, restauração, testes e demo.

Critério de aceite:

- checklist vira o plano central do projeto;
- nenhum documento extra é criado sem justificativa.

---

# PROMPT 2 — implementar arquitetura local sem Docker

Implemente a base técnica local.

Objetivo:

- sistema rodando em um PC servidor da Epic;
- usuários acessando pelo navegador na rede interna;
- PostgreSQL local;
- sem Docker.

Escopo:

- estrutura do projeto;
- backend/API;
- frontend servido pelo PC servidor;
- PostgreSQL local;
- variáveis de ambiente;
- script simples de inicialização;
- instruções no checklist para instalação e acesso;
- orientação de firewall/IP/porta no checklist.

Regras:

- não exigir instalação nas máquinas dos usuários;
- login individual obrigatório;
- preparar storage local de documentos;
- preparar backup desde esta fase;
- atualizar checklist com evidência.

Testes mínimos:

- backend sobe;
- frontend abre;
- outro computador da rede consegue acessar via navegador, quando ambiente permitir;
- banco conecta;
- login funciona;
- checklist atualizado.

Critério de aceite:

- sistema navegável localmente;
- arquitetura documentada dentro do checklist;
- sem Docker.

---

# PROMPT 3 — implementar banco, usuários, permissões, logs e backup

Implemente fundação de governança.

Escopo:

- PostgreSQL schema inicial;
- users;
- roles;
- permissions;
- permissões por ação crítica;
- audit log de negócio;
- log técnico;
- pasta local de documentos;
- rotina de backup do banco;
- rotina de backup dos documentos;
- procedimento de restauração;
- backup antes de migração relevante.

Regras:

- dado oficial não é deletado;
- alteração crítica exige motivo;
- todo log registra usuário, data/hora, entidade, campo, antes/depois e motivo;
- falhas técnicas entram no log técnico;
- backup deve gerar log de sucesso/falha.

Testes mínimos:

- criar usuário;
- login;
- permissão negada;
- alteração crítica com log;
- tentativa de alteração crítica sem motivo bloqueada;
- backup executado;
- restauração testada ou procedimento documentado no checklist.

Critério de aceite:

- governança mínima funcional antes dos módulos operacionais.

---

# PROMPT 4 — implementar importações, SKUs, invoices e `ANTECIPO`

Implemente o núcleo operacional inicial.

Escopo:

- import_orders;
- import_order_items;
- products/SKUs;
- invoices;
- invoice_items;
- tipo formal `ANTECIPO`;
- múltiplas invoices por importação;
- múltiplos itens por invoice;
- vínculo com documentos;
- status inicial da importação.

Regras:

- importação pode ter 1, 3 ou mais invoices;
- `ANTECIPO` pode ocorrer muito antes do embarque;
- invoice pode não estar vinculada ao embarque final no início;
- vazio não vira zero;
- alterações de valor/data/tipo geram log;
- dado oficial não é deletado.

Telas mínimas:

- lista de importações;
- detalhe da importação;
- cadastro de SKU;
- tela de invoice;
- painel simples de pendências.

Testes mínimos:

- importação com 3 invoices incluindo `ANTECIPO`;
- importação com mais de 3 invoices;
- invoice com campo vazio não vira zero;
- alteração de invoice gera log;
- anulação de invoice preserva histórico.

Critério de aceite:

- usuário consegue criar importação, vincular SKUs e registrar invoices múltiplas.

---

# PROMPT 5 — implementar controle financeiro: pagamentos, câmbio, descontos, créditos e conta corrente Brasil

Implemente o módulo financeiro prioritário do MVP.

Escopo:

- payments;
- payment_allocations;
- pagamentos antecipados;
- pagamentos parciais;
- pagamento de saldo;
- câmbio previsto;
- câmbio revisado;
- câmbio efetivo por pagamento;
- descontos;
- créditos Heroes;
- conta corrente Brasil;
- saldo por invoice e por importação;
- diferença previsto vs realizado.

Regras:

- invoice pode ter múltiplos pagamentos;
- pagamento exige comprovante ou justificativa aprovada;
- câmbio é versionado;
- desconto, crédito e conta corrente são conceitos separados;
- crédito não pode ser usado duas vezes;
- conta corrente Brasil registra impacto financeiro/fiscal estimado;
- alteração financeira crítica exige motivo e log.

Telas mínimas:

- painel financeiro da importação;
- tela de pagamentos;
- tela de descontos/créditos;
- saldo por invoice;
- saldo consolidado da importação.

Testes mínimos:

- pagamento parcial;
- pagamento com câmbio diferente do previsto;
- desconto direto em invoice;
- crédito Heroes usado posteriormente;
- tentativa de uso duplicado de crédito bloqueada;
- conta corrente Brasil com impacto estimado;
- alteração de câmbio com log.

Critério de aceite:

- usuário sabe valor previsto, pago, saldo, descontos, créditos, câmbio e pendências por importação.

---

# PROMPT 6 — implementar documentos/anexos e importação bruta/staging da Heroes

Implemente documentos e camada de importação de dados.

Escopo:

- documents;
- raw_import_files;
- staging_import_rows;
- review_queue;
- upload/anexo local;
- preservação de arquivo bruto;
- versionamento de documento;
- substituição sem sobrescrever;
- vínculo de documentos com entidades;
- importação de planilha Heroes para staging;
- revisão humana antes de oficializar.

Regras:

- arquivo bruto não é apagado;
- documento anexado não é sobrescrito;
- documento substituído mantém histórico;
- dado importado não vira oficial sem revisão;
- erros de importação entram no log técnico;
- divergência vira fila de revisão.

Documentos mínimos:

- proforma;
- invoice;
- comprovante de pagamento;
- contrato/acordo;
- e-mail relevante salvo;
- packing list;
- BL/AWB;
- DI/DUIMP;
- documentos do despachante;
- comprovantes de impostos;
- comprovantes de despesas Brasil;
- documentos de crédito/desconto/conta corrente.

Testes mínimos:

- upload de documento;
- substituição preservando histórico;
- documento obrigatório ausente bloqueia fechamento;
- importação Heroes com campo vazio não vira zero;
- linha ambígua cai em review_queue;
- backup inclui anexos.

Critério de aceite:

- documentos estão vinculados, versionados e incluídos no backup.

---

# PROMPT 7 — implementar logística navio/avião, múltiplos embarques e alteração de modal

Implemente logística com flexibilidade operacional.

Escopo:

- shipments;
- shipment_items;
- shipment_modes;
- modal `AIR`;
- modal `OCEAN`;
- modal `OTHER`;
- ETA/ETD planejado, revisado e realizado;
- custos por embarque;
- documentos por modal;
- múltiplos embarques por importação;
- alteração de modal com log e aprovação quando aplicável.

Regras:

- uma importação pode ter múltiplos embarques;
- uma importação pode ser parcialmente aérea e parcialmente marítima;
- modal influencia prazo e custo;
- alteração de modal preserva modal anterior;
- alteração exige motivo, documento/e-mail de suporte e log;
- custos logísticos vinculam-se ao embarque;
- quantidades embarcadas precisam conciliar com pedido/invoice.

Testes mínimos:

- importação marítima simples;
- importação aérea simples;
- importação originalmente marítima alterada para aérea;
- importação parcialmente navio e parcialmente avião;
- alteração de modal recalcula custo/prazo estimado;
- alteração sem motivo bloqueada.

Critério de aceite:

- sistema mostra modal, prazo, custo, documentos e histórico de alterações.

---

# PROMPT 8 — implementar aduana, DI/DUIMP, nacionalização e estoque mínimo

Implemente o fluxo do Brasil até entrada mínima em estoque.

Escopo:

- customs_processes;
- DI/DUIMP;
- taxes;
- customs expenses;
- despachante;
- nationalization_events;
- stock_entries;
- quantidade nacionalizada por SKU;
- quantidade recebida em estoque;
- custo unitário aprovado;
- vínculo com landed cost final.

Regras:

- imposto/taxa exige documento;
- despesa do despachante exige evidência;
- nacionalização exige processo aduaneiro válido;
- entrada em estoque depende de nacionalização;
- entrada em estoque não pode exceder nacionalização sem justificativa;
- divergência de quantidade vai para conciliação;
- nacionalização e entrada em estoque geram audit log.

Testes mínimos:

- nacionalização com DI/DUIMP;
- imposto com comprovante;
- despesa de despachante com documento;
- entrada em estoque após nacionalização;
- tentativa de estoque acima do nacionalizado bloqueada ou exige justificativa;
- divergência de quantidade cria conciliação.

Critério de aceite:

- usuário sabe o que está nacionalizado, o que entrou em estoque e qual custo unitário aprovado.

---

# PROMPT 9 — implementar landed cost versionado, rateio e conciliação

Implemente custo final e conciliação.

Escopo:

- landed_cost_versions;
- landed_cost_allocations;
- custo estimado inicial;
- custo estimado revisado;
- preliminar;
- final;
- final reaberto/revisado;
- critérios de rateio;
- custo por SKU;
- reconciliations.

Componentes mínimos do custo:

- FOB por item;
- descontos;
- crédito/conta corrente aplicável;
- frete;
- seguro;
- impostos;
- despesas Brasil;
- despesas de despachante;
- taxas bancárias;
- armazenagem;
- diferença cambial;
- outros custos aprovados.

Regras:

- fórmula explícita e rastreável;
- versão nova não apaga versão anterior;
- mudança de modal/câmbio/imposto/despesa/crédito pode gerar nova versão;
- critério de rateio explícito;
- fechamento aponta versão aprovada;
- divergência relevante bloqueia fechamento ou exige aprovação.

Conciliações obrigatórias:

- planilha Heroes vs invoice;
- invoice vs pedido;
- invoice vs pagamento bancário;
- pagamento previsto vs realizado;
- desconto informado vs aplicado;
- crédito informado vs usado;
- conta corrente Brasil vs crédito de origem;
- embarque vs documento;
- despachante vs despesas;
- imposto calculado vs pago;
- quantidade pedida vs faturada vs embarcada vs nacionalizada vs estocada;
- custo estimado vs custo realizado.

Testes mínimos:

- landed cost inicial;
- landed cost revisado após mudança de modal;
- landed cost final;
- versão anterior preservada;
- rateio por SKU;
- divergência de custo previsto vs realizado;
- conciliação resolvida;
- conciliação pendente bloqueando fechamento.

Critério de aceite:

- usuário entende como o custo final por SKU foi formado e quais divergências existem.

---

# PROMPT 10 — implementar fechamento, reabertura, testes finais e demo

Implemente fechamento auditável e validação final do MVP.

Escopo:

- fechamento sem divergência;
- fechamento com divergência aprovada;
- reabertura controlada;
- histórico de fechamentos;
- bloqueios de fechamento;
- testes automatizados;
- teste manual no browser interno;
- massa de teste realista;
- relatório de cobertura dentro do checklist.

Regras:

- fechamento exige documentos mínimos;
- fechamento exige conciliações resolvidas ou exceção aprovada;
- fechamento aponta versão de landed cost aprovada;
- fechamento preserva snapshot dos dados críticos;
- reabertura exige permissão, motivo e log;
- novo fechamento gera nova versão;
- importação fechada não pode ser editada sem reabertura.

Massa de teste obrigatória:

1. Importação marítima simples.
2. Importação aérea simples.
3. Importação originalmente marítima alterada para aérea.
4. Ordem com 3 faturas, incluindo `ANTECIPO`.
5. Ordem com mais de 3 faturas.
6. Pagamento parcial.
7. Pagamento com câmbio diferente do previsto.
8. Desconto direto em invoice.
9. Crédito da Heroes usado posteriormente.
10. Conta corrente Brasil com impacto financeiro/fiscal estimado.
11. Divergência entre quantidade pedida e nacionalizada.
12. Divergência entre custo previsto e realizado.
13. Fechamento sem divergência.
14. Fechamento com divergência aprovada.
15. Reabertura de importação fechada.
16. Entrada em estoque após nacionalização.

Testes finais mínimos:

- build/test suite completa;
- fluxo financeiro;
- pagamentos parciais;
- créditos e descontos;
- alteração de modal;
- aduana e nacionalização;
- estoque mínimo;
- conciliação;
- landed cost versionado;
- auditoria;
- permissões;
- bloqueios de fechamento;
- campo vazio não vira zero;
- separação bruto/staging/oficial;
- backup;
- restauração;
- UI no browser interno.

Atualize o checklist com:

- DONE/PARTIAL/BLOCKED/TODO;
- evidência por item;
- teste associado;
- lacunas;
- riscos;
- próxima fase recomendada.

Critério de aceite:

- sistema tem rastreabilidade entre requisito, implementação e teste;
- MVP opera localmente;
- checklist prova o que está pronto e o que falta;
- fechamento incorreto é bloqueado;
- reabertura é controlada;
- backup e restauração foram previstos e testados/documentados.

---

# Itens adicionais que não podem ser esquecidos

Inclua no checklist e mantenha durante toda a construção:

1. Não avançar se `CURSOR_RULES_IMPORTACAO_EPIC.md` e `CHECKLIST_MVP_IMPORTACAO_EPIC.md` estiverem desatualizados.
2. Não criar documentos extras sem necessidade real.
3. Sempre atualizar checklist após cada módulo.
4. Todo item `DONE` precisa ter evidência.
5. Toda regra crítica precisa de teste.
6. UI sempre testada no browser interno do Cursor após iniciar servidor.
7. Servidor local deve ter instrução simples de start/restart.
8. Porta/firewall/IP devem estar documentados no checklist.
9. Backup antes de migração relevante.
10. Restauração deve ser testada ou procedimento deve estar validado.
11. Anexos precisam entrar no backup.
12. Logs de backup precisam ser visíveis.
13. Dado oficial não é deletado fisicamente.
14. Campo vazio nunca vira zero.
15. Mudança crítica exige motivo.
16. Mudança crítica gera log.
17. Histórico nunca é sobrescrito.
18. Cálculo de landed cost é versionado.
19. Fechamento aponta versão aprovada.
20. Reabertura preserva fechamento anterior.
21. Crédito não é desconto.
22. Conta corrente Brasil tem controle próprio.
23. `ANTECIPO` é tipo formal de invoice.
24. Importação pode ter mais de 3 invoices.
25. Invoice pode ter vários pagamentos.
26. Importação pode ter vários embarques.
27. Embarque pode mudar de modal.
28. Quantidade deve ser rastreada até estoque.
29. Divergência não some; vira conciliação/revisão.
30. Arquitetura local sem Docker é premissa desta fase.
