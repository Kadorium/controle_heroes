# Regras Permanentes — Módulo de Importação Epic

**Versão:** 1.0  
**Última atualização:** 2026-06-20  
**Status:** Ativo — fonte obrigatória antes de qualquer implementação

---

## 1. Escopo e objetivo

### 1.1 Contexto operacional

| Elemento | Definição |
|---|---|
| Empresa | Epic |
| Parceira italiana | Heroes |
| Fabricação | China |
| Despacho aduaneiro | Empresa brasileira (despachante) |
| Objetivo do MVP | Controle financeiro, invoices, pagamentos, itens, logística, aduana, nacionalização, estoque mínimo, conciliação e landed cost |

### 1.2 O que o MVP deve entregar

- Cadastro de importações, fornecedores e SKUs
- Invoices/proformas (incluindo `ANTECIPO`), pagamentos, saldos, descontos, créditos e conta corrente Brasil
- Status operacional com transições bloqueantes
- Anexos/documentos versionados
- Landed cost estimado, revisado, preliminar e final
- Conciliação operacional e financeira
- Nacionalização e entrada mínima em estoque
- Fechamento auditável e reabertura controlada
- Backup diário e restauração testada
- Trilha de auditoria de ponta a ponta

### 1.3 Fora de escopo do MVP

- ERP completo
- Contabilidade, fiscal ou WMS completos
- Integração bancária automática complexa
- Integração direta com Portal Único
- Motor tributário sofisticado
- Workflow corporativo pesado
- Multiempresa avançado
- Permissões excessivamente granulares
- Microservices
- Arquitetura cloud/SaaS
- Docker (nesta fase)
- Next.js, Electron
- SQLite, Access ou Excel como base oficial multiusuário

Excel pode ser **fonte de importação** ou **destino de exportação**, nunca base oficial.

### 1.4 Regras de ouro (nunca violar)

1. Nenhum custo, desconto, imposto ou pagamento entra sem origem/documento.
2. Campo vazio **nunca** vira zero automaticamente.
3. Nenhuma divergência desaparece — vira fila de revisão ou conciliação.
4. Dado oficial não é deletado fisicamente — apenas anulado/cancelado/inativado com motivo e log.
5. Mudança crítica nunca sobrescreve histórico.
6. Status é regra de negócio, não campo editável livremente.

---

## 2. Stack técnica do MVP (definida)

### 2.1 Decisões positivas

| Camada | Tecnologia |
|---|---|
| Backend | Python + FastAPI |
| ORM / migrações | SQLAlchemy + Alembic |
| Validação / schema | Pydantic |
| Banco de dados | PostgreSQL local (instalado diretamente no PC servidor; **verificar porta** — ex.: 5433) |
| Frontend | React + TypeScript + Vite |
| Produção local | Frontend buildado servido pelo backend FastAPI, **preferencialmente em porta única** |
| Autenticação | Login individual; senha com hash; sessão/cookie `httpOnly` |
| Anexos | Pasta local controlada; banco guarda metadata, hash, versão, entidade vinculada e usuário |
| Backup | Scripts PowerShell: `pg_dump` + cópia/compactação de anexos; Task Scheduler; retenção ≥ 30 dias |
| Testes backend | pytest + testes de validação das regras críticas |
| Testes UI | Browser interno do Cursor após iniciar servidor local; Playwright apenas se não aumentar complexidade |

### 2.2 Scripts mínimos esperados

- `start` — iniciar sistema local (backend + frontend servido)
- `backup-manual` — backup sob demanda
- `backup-daily` — rotina agendável pelo Task Scheduler
- `restore` / `test-restore` — restauração e teste documentado
- Instruções de acesso pela rede interna (IP, porta, firewall)

### 2.3 Decisões negativas (proibido no MVP)

- Docker
- Next.js
- Electron
- SQLite, Access ou Excel como base oficial
- Microservices
- Arquitetura cloud/SaaS
- Documentos `.md` extras além deste arquivo e do `CHECKLIST_MVP_IMPORTACAO_EPIC.md`, salvo justificativa objetiva

---

## 3. Arquitetura local obrigatória

### 3.1 Modelo de implantação

```text
PC servidor Epic (rede interna)
├── PostgreSQL (local, não containerizado)
├── Backend FastAPI (Python)
│   ├── API REST
│   ├── Sessões httpOnly
│   ├── Static files (frontend build Vite)
│   └── Upload handler → pasta de anexos
├── Pasta de anexos (local, versionada)
├── Pasta de backups (separada da pasta principal)
└── Scripts PowerShell (start, backup, restore)

Usuários (navegador)
└── http://192.168.x.x:porta  ou  http://epic-importacoes:porta
```

### 3.2 Requisitos operacionais

- Um PC da Epic será o servidor local
- Nenhum funcionário instala o sistema localmente
- Cada funcionário acessa com login e senha próprios
- Toda alteração registra o usuário autenticado
- IP fixo ou reserva de IP no roteador
- Firewall do Windows liberando a porta usada
- Reinício automático após reboot do PC (quando possível)
- Backup antes de migração relevante do banco

### 3.3 Estrutura de pastas sugerida (referência)

```text
C:\EpicImportacoes\
├── app\              # código backend
├── frontend\         # código React/Vite
├── data\
│   ├── attachments\  # anexos versionados
│   └── imports\      # arquivos brutos Heroes
├── backups\
│   ├── db\
│   └── attachments\
├── logs\
└── scripts\          # PowerShell: start, backup, restore
```

---

## 4. Regras de dados

### 4.1 Camadas de dado

| Camada | Finalidade | Regra |
|---|---|---|
| Bruta | Arquivo original recebido | Nunca alterado, nunca apagado |
| Staging | Dados parseados linha a linha | Aguardam revisão humana |
| Revisão | `review_queue` | Itens ambíguos ou com problema |
| Oficial | Entidades aprovadas | Nunca deletado; anulação com log |
| Calculada | Landed cost, conciliações, câmbio | Versionada e auditável |
| Auditoria | `audit_log`, `status_transition_log` | Histórico imutável |

### 4.2 Regras universais

- Campo vazio → `null`, `missing` ou `pending_review` — **nunca** zero
- Dado bruto nunca entra como dado oficial
- Todo dado importado passa: bruto → staging → revisão → oficial
- Arquivo recebido não pode ser sobrescrito
- Documento substituído mantém histórico (hash, versão)
- Toda importação de arquivo guarda: origem, data, usuário, nome, hash, versão
- Toda migração Alembic deve ser rastreável; backup antes de migração relevante

---

## 5. Flexibilidade operacional

O sistema **não** assume fluxo linear. Deve permitir:

- Pedido inicialmente marítimo, depois alterado para aéreo
- Pedido parcialmente navio e parcialmente avião
- Pedido dividido em múltiplos embarques
- Ordem com 3+ faturas/invoices
- Fatura `ANTECIPO` até ~1 ano antes da chegada
- Câmbio previsto diferente do efetivo
- Desconto europeu que vira crédito ou conta corrente no Brasil
- Despesa nova após fechamento preliminar
- Custo estimado diferente do realizado
- Reabertura de importação fechada

**Regra central:** mudança operacional ou financeira é permitida; mudança crítica exige usuário, data/hora, motivo (`reason_code`), valor anterior, valor novo, documento de suporte (quando aplicável) e impacto estimado.

---

## 6. Logs

### 6.1 Audit log de negócio (obrigatório)

Eventos que devem gerar log:

- Alteração de modal logístico
- Alteração de custo / landed cost
- Alteração de invoice
- Alteração de pagamento
- Alteração de câmbio
- Alteração de desconto
- Criação ou uso de crédito
- Conta corrente Brasil
- Alteração de status
- Alteração, substituição, anulação ou cancelamento de documento
- Aprovação ou rejeição
- Fechamento
- Reabertura
- Nacionalização
- Entrada em estoque

Campos mínimos:

```text
user_id, timestamp, entity_type, entity_id, action,
field_changed, old_value, new_value,
reason_code_id, justification, attachment_id, impact_estimate
```

### 6.2 Log técnico (obrigatório)

- Falha de login
- Erro de importação (Heroes)
- Erro de backup / restauração
- Erro de banco
- Falha de permissão
- Erro de cálculo
- Erro de upload/anexo

---

## 7. Backup e restauração

### 7.1 Rotina mínima (desde o MVP)

| Item | Especificação |
|---|---|
| Banco | `pg_dump` diário via PowerShell |
| Anexos | Cópia/compactação diária da pasta de anexos |
| Agendamento | Windows Task Scheduler |
| Retenção | Mínimo 30 dias |
| Destino | Pasta separada da pasta principal; opcional HD externo/NAS |
| Log | Sucesso/falha registrado |
| Restauração | Script + procedimento documentado e testado |
| Migração | Backup manual antes de migração Alembic relevante |

### 7.2 Critérios de aceite backup

- Backup implementado e agendado
- Backup testado (execução manual)
- Restauração testada ou procedimento validado
- Documentos incluídos no backup
- Logs de backup visíveis no sistema ou arquivo de log

---

## 8. Invoices, faturas e ANTECIPO

### 8.1 Modelo

- Uma importação pode ter **N invoices**
- Uma invoice pode ter **N pagamentos**
- Proforma é entidade própria (não apenas campo do PO)

### 8.2 Tipos mínimos de invoice

`ANTECIPO` · `PROFORMA` · `SALDO` · `COMPLEMENTAR` · `AJUSTE` · `CREDITO` · `OUTRA`

### 8.3 Regras para ANTECIPO

- Normalmente emitida no fechamento do pedido
- Pode ocorrer ~1 ano antes da chegada
- Inicia pedido/produção
- Vinculada à importação; pode não estar vinculada ao embarque final
- Pode ter câmbio previsto diferente do efetivo
- Impacta saldo financeiro até o fechamento

### 8.4 Campos mínimos de invoice

tipo, número, data, fornecedor, moeda, valor, itens vinculados, importação vinculada, status, pagamentos vinculados, saldo, câmbio previsto, câmbio efetivo, documento anexado, observações, log de alterações

---

## 9. Pagamentos e financeiro

- Tipos: adiantamento (`ADVANCE`), parcial (`PARTIAL`), final (`FINAL`), ajuste (`ADJUSTMENT`)
- Múltiplos pagamentos por invoice, em datas diferentes, com câmbios diferentes
- Nenhum pagamento sem comprovante ou justificativa aprovada
- Nenhum desconto sem origem documental
- Nenhum crédito sem origem, saldo e uso rastreável
- Fechamento financeiro só com documentos mínimos e conciliações resolvidas (ou exceção aprovada)

---

## 10. Câmbio versionado

Não existe "o câmbio da importação". Conceitos mínimos:

- Câmbio previsto no pedido
- Câmbio previsto revisado
- Câmbio efetivo do pagamento
- Câmbio usado no landed cost
- Data de referência, fonte, usuário, motivo da alteração
- Diferença cambial estimada vs realizada

Regras:

- Câmbio vazio não vira zero
- Alteração de câmbio gera log
- Preservar câmbio usado em cada pagamento e em cada versão de cálculo
- Histórico não pode ser recalculado silenciosamente

---

## 11. Descontos, créditos e conta corrente Brasil

### 11.1 Separação conceitual (nunca misturar)

| Conceito | Efeito |
|---|---|
| Desconto direto na invoice | Reduz invoice/custo conforme regra |
| Desconto por item / global | Reduz landed cost do produto |
| Crédito Heroes | Não vira desconto automaticamente; saldo rastreável |
| Conta corrente/compensação Brasil | Controle próprio; impacto financeiro/fiscal estimado |
| Ajuste financeiro manual | Custo financeiro se atribuível à importação |

### 11.2 Regras

- Crédito não pode ser usado duas vezes
- Crédito/conta corrente exige origem documental
- Crédito europeu convertido em conta corrente Brasil registra impacto financeiro/fiscal estimado
- Justificativa e aprovação obrigatórias quando houver impacto relevante

Status mínimos: disponível · usado parcialmente · usado · cancelado · em disputa · pendente de aprovação

---

## 12. Planejado, revisado e realizado

Separar as três visões para: custo de produto, frete, seguro, impostos, despesas Brasil, despachante, câmbio, prazo, ETA, ETD, modal, pagamentos, landed cost, entrada em estoque.

- **Planejado:** visão inicial no fechamento do pedido
- **Revisado:** alterada por mudança de condição
- **Realizado:** valor/data final com documento

O sistema deve sempre permitir comparar planejado vs revisado vs realizado.

---

## 13. Logística e alteração de modal

Modais: `AIR` · `OCEAN` · `OTHER`

Regras de alteração de modal:

- Exige `reason_code` e log
- Modal anterior preservado
- Custo e prazo estimados recalculados
- Impacto financeiro e operacional registrados
- Pode exigir aprovação conforme custo/impacto

Modelo: uma ordem pode ter um ou múltiplos embarques; parcialmente aéreo e marítimo; embarques adicionais após planejamento inicial.

---

## 14. Aduana, nacionalização e estoque mínimo

- Nacionalização exige DI/DUIMP ou processo aduaneiro válido
- Imposto/taxa exige documento
- Despesa do despachante exige evidência
- Entrada em estoque depende de nacionalização
- Quantidade em estoque não pode exceder nacionalizada sem justificativa
- Divergência de quantidade → conciliação

MVP de estoque: evento de nacionalização, quantidade nacionalizada por SKU, evento de entrada, quantidade recebida, custo unitário aprovado, vínculo com landed cost final.

---

## 15. Quantidades por etapa (por SKU)

Rastrear: pedida · faturada · embarcada · nacionalizada · recebida em estoque · diferença · justificativa · status de conciliação.

---

## 16. Landed cost versionado

Versões mínimas: estimativa inicial · estimativa revisada · preliminar · final · final reaberto/revisado

Componentes: FOB, descontos, crédito/conta corrente aplicável, frete, seguro, impostos, despesas Brasil, despachante, taxas bancárias, armazenagem, diferença cambial, outros aprovados.

Regras:

- Nova versão não apaga versão anterior
- Mudança de modal/câmbio/imposto/despesa/crédito pode gerar nova versão
- Rateio explícito (valor, quantidade, peso, volume, igual, manual auditado)
- Fechamento aponta versão aprovada

Fórmula:

```text
Landed Cost = Produto + Frete + Seguro + Impostos + Despesas locais + Custo financeiro
Custo unitário = Landed Cost total alocado ao SKU / Quantidade recebida
```

---

## 17. Status operacional

### 17.1 Princípio

Status muda por **ação controlada**, não por edição de campo. Cada transição valida três travas:

| Trava | Valida |
|---|---|
| Documental | Documentos obrigatórios da etapa existem e são versão atual |
| Permissão | Usuário tem papel suficiente |
| Conciliação financeira | Valores dentro da tolerância ou justificados |

### 17.2 Taxonomia principal

Pedido: `PO_CREATED`, `SI_OPEN`, `PROFORMA_RECEIVED`  
Financeiro: `ADVANCE_PAID`, `PARTIAL_PAID`, `FULL_PAID`  
Licenciamento: `LI_PENDING`, `LI_APPROVED`, `LPCO_PENDING`, `LPCO_APPROVED`  
Embarque: `BOOKED`, `SHIPPED`, `IN_TRANSIT`, `ARRIVED`, `UNLOADED`  
Aduaneiro: `DI_SUBMITTED`, `DUIMP_REGISTERED`, `ANUENCIA_PENDING`, `ANUENCIA_APPROVED`, `CUSTOMS_RELEASED`, `CLEARED`  
Logística interna: `DELIVERED`, `RECEIVED_IN_STOCK`  
Fiscal: `NF_IMPORT_ISSUED`, `INVOICED`  
Conciliação: `CONCILIATION_PENDING`, `CONCILIATION_DONE`, `CLOSED`  
Exceção: `ON_HOLD`, `DISCREPANCY_OPEN`, `REOPENED`, `CANCELLED`

---

## 18. Conciliação obrigatória

Pares mínimos:

- Planilha Heroes vs invoice
- Invoice vs pedido
- Invoice vs pagamento bancário
- Pagamento previsto vs realizado
- Desconto informado vs aplicado
- Crédito informado vs usado
- Conta corrente Brasil vs crédito de origem
- Embarque vs documentos logísticos
- Despachante vs despesas
- Imposto calculado vs pago
- Quantidade pedida vs faturada vs embarcada vs nacionalizada vs estocada
- Custo estimado vs realizado
- Landed cost preliminar vs final

Status: conciliado · divergente · pendente de documento · pendente de aprovação · ajuste manual aprovado · ignorado com justificativa

Divergência relevante bloqueia fechamento ou exige aprovação formal.

---

## 19. Fechamento e reabertura

### 19.1 Fechamento

- Exige documentos mínimos por fase
- Exige conciliações resolvidas ou exceção aprovada
- Aponta versão de landed cost aprovada
- Preserva snapshot dos dados críticos
- Importação fechada não editável sem reabertura

### 19.2 Reabertura

- Apenas usuário autorizado
- Exige `reason_code`, justificativa e log
- Fechamento anterior preservado
- Novo fechamento gera nova versão

Status: fechado · reaberto · fechado revisado · fechado com divergência aprovada

---

## 20. Permissões por ação crítica

Além de permissões por módulo, controlar ações:

alterar modal · alterar câmbio · alterar valor de invoice · aprovar desconto · criar crédito · usar crédito · aprovar conta corrente Brasil · registrar pagamento · aprovar pagamento sem comprovante · registrar imposto · nacionalizar · dar entrada em estoque · fechar importação · reabrir importação · aprovar divergência · cancelar/anular documento · rodar migração · restaurar backup

---

## 21. Anulação em vez de exclusão

Aplica-se a: invoice, pagamento, despesa, imposto, documento, crédito, entrada de estoque, fechamento, landed cost, embarque, conciliação.

---

## 22. Reason codes

Justificativas críticas usam códigos controlados; texto livre apenas como complemento.

Eventos que exigem `reason_code`: reabertura, cancelamento, divergência de quantidade/financeira, alteração de modal, troca de fornecedor/SKU/NCM/Incoterm, override de landed cost/rateio, substituição de documento oficial, baixa manual de pendência.

Categorias sugeridas: Reabertura · Cancelamento · Divergência · Logística · Custo · Documento

Motivos inativos permanecem no histórico; não aparecem para novas ações.

---

## 23. Documentos obrigatórios por fase

| Fase | Documento |
|---|---|
| Proforma | Proforma Invoice |
| Pagamento antecipado | Comprovante bancário e/ou contrato de câmbio |
| Embarque | BL, AWB ou equivalente |
| Desembaraço | DI/DUIMP e documentos do despachante |
| Fiscal | NF de Importação |
| Recebimento | Conferência de estoque |
| Fechamento | Relatório de conciliação |
| Reabertura | Justificativa e termo/documento |

---

## 24. Navegação relacional (UI)

O processo de importação é o **hub relacional**. De qualquer card, documento, pagamento, invoice, item ou evento, o usuário deve navegar para objetos conectados sem "caçar" em módulos isolados.

Abas mínimas no detalhe da importação: Resumo · Itens/SKUs · Invoices · Pagamentos/Câmbio · Logística · Aduaneiro · Landed Cost · Conciliação · Documentos · Linha do tempo · Auditoria

---

## 25. Testes e qualidade

- Toda regra crítica implementada deve ter teste (pytest)
- Todo item `DONE` no checklist precisa evidência e teste associado
- UI testada no browser interno do Cursor após iniciar servidor
- Não declarar fase concluída sem build/testes/checklist atualizado
- Playwright opcional; usar apenas se não aumentar complexidade

---

## 26. Governança de documentação

1. Não avançar implementação se este arquivo ou o checklist estiverem desatualizados
2. Não criar documentos `.md` extras sem justificativa objetiva
3. Sempre atualizar checklist após cada módulo
4. Preferir atualizar estes dois arquivos a criar novos
5. **Regra Cursor (índice):** o agente deve seguir [`.cursor/rules/importacao-epic-indice.mdc`](.cursor/rules/importacao-epic-indice.mdc) — roteador que aponta para a § correta deste arquivo e para os itens `Fx-xxx` do checklist conforme o módulo ou fase em execução

---

## 27. Referências do projeto

- [`.cursor/rules/importacao-epic-indice.mdc`](.cursor/rules/importacao-epic-indice.mdc) — índice Cursor (alwaysApply): roteia tarefa → § deste arquivo + checklist
- [blueprint_controle_importacao_organizado_v1_3.md](blueprint_controle_importacao_organizado_v1_3.md)
- [02_resumo_executivo_modulo_importacao_epic_v2.md](02_resumo_executivo_modulo_importacao_epic_v2.md)
- [03_prompts_cursor_modulo_importacao_epic_v4_final.md](03_prompts_cursor_modulo_importacao_epic_v4_final.md)
- [CHECKLIST_MVP_IMPORTACAO_EPIC.md](CHECKLIST_MVP_IMPORTACAO_EPIC.md)
