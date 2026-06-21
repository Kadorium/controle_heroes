# Blueprint de Sistema de Controle de Importação

**Versão:** 1.1  
**Origem:** texto-base fornecido pelo usuário  
**Objetivo:** organizar padrões funcionais para um sistema de controle de importações com foco em ciclo operacional, financeiro, landed cost, documentação, conciliação, auditoria e navegação operacional orientada a documentos.

---

## 1. Objetivo do documento

Este documento consolida uma referência prática para desenho de um sistema de controle de importações. O foco é operacional e financeiro, não a construção de um ERP completo.

O sistema deve ajudar a controlar:

- pedidos de importação;
- proformas e invoices finais;
- pagamentos antecipados, parciais e finais;
- contratos e taxas de câmbio;
- embarque, chegada, DI/DUIMP e desembaraço;
- documentos do despachante;
- landed cost por SKU;
- conciliação entre pedido, invoice, pagamento, impostos, estoque e documentos;
- auditoria e versionamento de alterações relevantes.

---

## 2. Princípios funcionais

1. **Importação é um processo, não apenas uma compra.**  
   O sistema precisa enxergar o ciclo completo: pedido, pagamento, embarque, nacionalização, estoque e fechamento.

2. **Pagamento não deve ser tratado como evento único.**  
   Uma mesma importação pode ter adiantamento, pagamentos parciais, saldo final e contratos de câmbio distintos.

3. **Invoice, proforma e PO não são a mesma coisa.**  
   A proforma pode iniciar o pagamento antecipado; a invoice final e os documentos oficiais fecham o custo real.

4. **Landed cost deve ter estágios.**  
   O custo precisa existir em pelo menos três versões: estimado, revisado e realizado.

5. **Documento é parte do dado.**  
   Alterações críticas devem exigir anexo ou referência documental.

6. **Fechamento precisa ser auditável e reversível com controle.**  
   Uma importação fechada só deve ser reaberta com permissão, justificativa e log.

7. **A navegação deve ser relacional e orientada ao documento.**  
   A partir de qualquer evento físico, financeiro ou documental, o usuário deve conseguir navegar para os objetos conectados: pedido original, proformas, invoices, pagamentos, contratos de câmbio, documentos aduaneiros, SKUs, custos rateados, anexos e histórico de alterações. A tela não deve obrigar o usuário a “caçar” a informação em módulos isolados.

8. **Justificativas críticas devem ser padronizadas por códigos de motivo.**  
   Exceções, cancelamentos, reaberturas, divergências e mudanças de modal não devem depender apenas de texto livre. O usuário deve selecionar um motivo controlado e, quando necessário, complementar com comentário. Isso permite análise futura por causa-raiz.

9. **Status deve ser regra de negócio, não apenas campo editável.**  
   Toda transição relevante de status deve passar por validação de documentação, permissão do usuário e conciliação financeira. O sistema deve bloquear avanço de etapa quando qualquer uma dessas travas falhar.

---

## 3. Ciclo de vida operacional da importação

### 3.1 Fluxo padrão ponta a ponta

| Etapa | Status sugerido | Atores | Evento-chave |
|---|---|---|---|
| Pedido | `PO_CREATED` / `SI_OPEN` | Comprador | Criação do pedido ou solicitação de importação com moeda, Incoterm e NCM |
| Proforma | `PROFORMA_RECEIVED` | Fornecedor + comprador | Recebimento da Proforma Invoice |
| Pagamento antecipado | `ADVANCE_PAID` | Financeiro + banco | Adiantamento de câmbio vinculado à proforma |
| Licenciamento | `LI_PENDING` → `LI_APPROVED` | Despachante | Licença de Importação, LPCO ou anuência aplicável |
| Embarque | `BOOKED` / `SHIPPED` | Fornecedor + transportadora | Booking, BL ou AWB |
| Trânsito internacional | `IN_TRANSIT` | Logística | Mercadoria em transporte internacional |
| Chegada no Brasil | `ARRIVED` / `UNLOADED` | Terminal + despachante | Desembarque no porto ou aeroporto |
| Declaração aduaneira | `DI_SUBMITTED` / `DUIMP_REGISTERED` | Despachante | Registro da DI ou DUIMP |
| Anuência | `ANUENCIA_PENDING` → `ANUENCIA_APPROVED` | Órgãos anuentes | Liberação por autoridade competente, quando aplicável |
| Desembaraço | `CUSTOMS_RELEASED` / `CLEARED` | Alfândega + despachante | Desembaraço aduaneiro |
| Saída do terminal | `DELIVERED` | Transportadora interna | Entrega física ao destino |
| Recebimento em estoque | `RECEIVED_IN_STOCK` | Estoque / almoxarifado | Conferência quantitativa e qualitativa |
| Faturamento / NF | `INVOICED` | Fiscal + financeiro | Invoice final e Nota Fiscal de Importação vinculadas |
| Conciliação | `CONCILIATION_DONE` | Financeiro + fiscal + comex | Conciliação entre invoice, pagamentos, DI/DUIMP, NF e landed cost |
| Fechamento | `CLOSED` | Gestor responsável | Importação fechada e bloqueada para alterações ordinárias |

### 3.2 Taxonomia consolidada de status

| Categoria | Status | Descrição |
|---|---|---|
| Pedido | `PO_CREATED`, `SI_OPEN`, `PROFORMA_RECEIVED` | Da criação do pedido ao recebimento da proforma |
| Financeiro | `ADVANCE_PAID`, `PARTIAL_PAID`, `FULL_PAID` | Pagamentos vinculados a proformas ou invoices |
| Licenciamento | `LI_PENDING`, `LI_APPROVED`, `LPCO_PENDING`, `LPCO_APPROVED` | Licenças, permissões, certificados e anuências prévias |
| Embarque | `BOOKED`, `SHIPPED`, `IN_TRANSIT`, `ARRIVED`, `UNLOADED` | Da reserva logística à chegada no Brasil |
| Aduaneiro | `DI_SUBMITTED`, `DUIMP_REGISTERED`, `ANUENCIA_PENDING`, `ANUENCIA_APPROVED`, `CUSTOMS_RELEASED`, `CLEARED` | Registro e liberação aduaneira |
| Logística interna | `DELIVERED`, `RECEIVED_IN_STOCK` | Entrega e conferência no estoque |
| Fiscal | `NF_IMPORT_ISSUED`, `INVOICED` | Emissão e vínculo da NF de Importação |
| Conciliação | `CONCILIATION_PENDING`, `CONCILIATION_DONE`, `CLOSED` | Conciliação financeira, documental e de custo |
| Exceção | `ON_HOLD`, `DISCREPANCY_OPEN`, `REOPENED`, `CANCELLED` | Pendências, divergências, reabertura ou cancelamento |

### 3.3 Transições de status com bloqueios formais

A mudança de status deve ser controlada por uma máquina de estados simples. O usuário não deve conseguir avançar, retroceder, cancelar ou reabrir um processo apenas editando um campo.

Cada transição relevante deve validar simultaneamente três travas:

| Trava | O que valida | Exemplo de bloqueio |
|---|---|---|
| Documental | Se os documentos obrigatórios daquela etapa existem, estão vinculados e são a versão atual | Não permitir `CUSTOMS_RELEASED` sem DI/DUIMP anexada ou validada |
| Permissão | Se o usuário tem papel suficiente para executar a transição | Não permitir `CLOSED` por usuário sem perfil de gestor/financeiro autorizado |
| Conciliação financeira | Se valores, pagamentos, câmbio, invoice, NF e landed cost estão dentro da tolerância definida | Não permitir `CONCILIATION_DONE` com diferença não justificada entre invoice e pagamento |

Regras recomendadas:

```text
Status não é editável diretamente.
Status muda por ação controlada: avançar etapa, abrir divergência, conciliar, fechar, reabrir ou cancelar.
Toda transição crítica grava log.
Toda transição crítica exige reason_code quando houver exceção, divergência, cancelamento, reabertura ou override.
Toda transição pode retornar erro bloqueante com lista objetiva de pendências.
```

Campos mínimos para histórico de status:

```text
status_transition_log
├─ id
├─ importation_id
├─ from_status
├─ to_status
├─ action
├─ user_id
├─ timestamp
├─ reason_code_id
├─ comment
├─ blocking_checks_json
└─ attachment_id
```

---

## 4. Referências funcionais por sistema

### 4.1 TOTVS Protheus / SIGAEIC — Easy Import Control

Funcionalidades aproveitáveis:

- entidades como Solicitação de Importação, Purchase Order, Licença de Importação, Embarque e Desembaraço;
- tratamento de pagamento antecipado vinculado à Proforma Invoice;
- fluxo de controle de câmbio;
- suporte a DUIMP, Catálogo de Produtos, Operador Estrangeiro e LPCO;
- vínculo entre embarque/desembaraço e invoice.

Pontos de atenção:

- estrutura funcional tende a ser mais pesada do que o necessário para um MVP local;
- usar como referência de processo, não como modelo integral de sistema.

Referências citadas no texto-base:

- [TOTVS — Pagamento antecipado para Purchase Order](https://centraldeatendimento.totvs.com/hc/pt-br/articles/360000091867-Cross-Segmento-TOTVS-Backoffice-Linha-Protheus-SIGAEIC-Pagamento-antecipado-para-a-purchase-order)
- [TOTVS — Cronograma DUIMP no Protheus](https://centraldeatendimento.totvs.com/hc/pt-br/articles/26319522861079-Cross-Segmento-TOTVS-Backoffice-Linha-Protheus-SIGAEIC-Cronograma-de-implementa%C3%A7%C3%A3o-da-DUIMP)
- [TOTVS — Itens DUIMP](https://centraldeatendimento.totvs.com/hc/pt-br/articles/10930457324439-Cross-Segmento-TOTVS-Backoffice-Linha-Protheus-SIGAEIC-Itens-DUIMP)

### 4.2 Odoo

Funcionalidades aproveitáveis:

- conceito de `Landed Costs` por produto/categoria;
- aplicação de custos adicionais após validação de transferências de estoque;
- métodos de rateio por quantidade, valor, peso, volume ou divisão igual;
- uso como benchmark para estruturação simples de custo adicional.

Pontos de atenção:

- o Odoo parte de uma lógica ERP integrada;
- para o MVP, o conceito de landed cost é mais útil do que a arquitetura completa.

Referência citada no texto-base:

- [Odoo — Landed Costs](https://www.odoo.com/documentation/saas-19.1/pt_BR/applications/inventory_and_mrp/inventory/inventory_valuation/landed_costs.html)

### 4.3 SAP Business One

Funcionalidades aproveitáveis:

- declaração de importação como base para emissão da Nota Fiscal de Importação;
- landed costs no destino baseados em entrada de mercadoria ou invoice;
- vínculo entre documento aduaneiro, entrada de mercadoria, fiscal e financeiro.

Referências citadas no texto-base:

- [SAP — Import Declaration / NF Importação](https://help.sap.com/doc/0aec5858c4254edb80d7319476e4af9d/2023.002/pt-BR/314006cc37984e6296edcd4010604d43_pt.pdf)
- [SAP Business One — Landed Costs](https://help.sap.com/docs/SAP_BUSINESS_ONE/68a2e87fb29941b5bf959a184d9c6727/44f8c616445241aae10000000a114a6b.html?locale=pt-PT)

### 4.4 Dynamics 365

Funcionalidades aproveitáveis:

- separação entre custo previsto e custo real;
- avaliação por área de custo e tipo de custo;
- relatórios de landed cost por componente.

Referência citada no texto-base:

- [Microsoft Dynamics 365 — Landed Cost Reports](https://learn.microsoft.com/pt-br/dynamics365/supply-chain/landed-cost/landed-cost-reports)

### 4.5 FazComex / Logcomex / sistemas especializados

Funcionalidades aproveitáveis:

- conciliação bancária com upload de OFX;
- centralização de documentos como DI, DUIMP, AWB e BL;
- rastreabilidade do fechamento de câmbio;
- compartilhamento de informação entre importador, despachante e demais envolvidos.

Referências citadas no texto-base:

- [FazComex — Fechamento de câmbio](https://www.fazcomex.com.br/comex/fechamento-de-cambio/)
- [FazComex — Conciliação bancária no comércio exterior](https://www.fazcomex.com.br/comex/fazer-conciliacao-bancaria-comercio-exterior-de-forma-automatica/)
- [Logcomex — Importadores e exportadores](https://www.logcomex.com/segmentos/importadores-e-exportadores)
- [Logcomex — Cronograma DUIMP](https://blog.logcomex.com/duimp/cronograma)

---

## 5. Controle financeiro

### 5.1 Pagamento antecipado

O pagamento antecipado deve ser tratado como evento financeiro autônomo, vinculado à proforma e ao processo de importação.

Padrão funcional recomendado:

```text
Pré-requisitos:
1. Pedido de importação criado.
2. Proforma Invoice recebida.
3. Condição de pagamento antecipado identificada.
4. Valor, moeda, percentual e vencimento cadastrados.

Fluxo:
1. Financeiro registra adiantamento.
2. Sistema vincula pagamento à proforma.
3. Sistema registra taxa de câmbio, contrato, data de contratação e data de liquidação.
4. Pagamento entra no custo estimado/revisado conforme estágio da importação.
5. Após invoice final, sistema permite compensar o adiantamento contra a invoice definitiva.
```

Regras críticas:

- pagamento antecipado não deve ser lançado apenas contra o PO;
- a proforma deve ser entidade própria;
- mesmo com 100% antecipado, o processo de embarque, desembaraço e invoice final deve continuar existindo;
- o pagamento antecipado precisa ser conciliado com contrato de câmbio e comprovante bancário.

### 5.2 Pagamentos parciais e múltiplas invoices

Estrutura típica:

| Entidade | Campos principais | Relacionamento |
|---|---|---|
| `importation_order` | `id`, `po_number`, `supplier_id`, `currency`, `incoterm`, `estimated_total`, `status` | 1:N com `invoice` |
| `invoice` | `id`, `importation_id`, `invoice_number`, `invoice_date`, `amount`, `currency`, `is_proforma`, `payment_status` | 1:N com `payment` |
| `payment` | `id`, `invoice_id`, `payment_date`, `amount_foreign`, `amount_local`, `exchange_rate`, `exchange_contract`, `payment_type` | N:1 com `invoice` |

Tipos de pagamento sugeridos:

| Tipo | Status | Uso |
|---|---|---|
| Adiantamento | `ADVANCE` | Pagamento antes da invoice final, normalmente baseado na proforma |
| Parcial | `PARTIAL` | Pagamento intermediário da invoice |
| Final | `FINAL` | Liquidação final do saldo |
| Ajuste | `ADJUSTMENT` | Correção, diferença cambial, tarifa ou acerto manual auditado |

### 5.3 Câmbio versionado por pagamento

O câmbio deve ser versionado por pagamento, não apenas por invoice ou pedido.

Campos recomendados:

```text
payment
├─ id
├─ invoice_id
├─ payment_date
├─ amount_foreign
├─ currency_foreign
├─ amount_local
├─ currency_local
├─ exchange_rate
├─ exchange_contract_number
├─ exchange_contract_date
├─ settlement_date
├─ bank_name
├─ fx_fee_amount
├─ fx_variation_amount
├─ attachment_id
└─ audit_status
```

Lógica de cálculo:

```text
Custo financeiro da mercadoria = Σ(amount_foreign × exchange_rate) por pagamento vinculado

Variação cambial = diferença entre taxa estimada, taxa contratada e taxa efetivamente liquidada
```

---

## 6. Landed cost

### 6.1 Fórmula geral

```text
Landed Cost = Produto + Frete + Seguro + Impostos + Despesas locais + Custo financeiro
```

Custo unitário:

```text
Custo unitário = Landed Cost total alocado ao SKU / Quantidade recebida do SKU
```

### 6.2 Componentes do landed cost

| Componente | Descrição | Exemplos |
|---|---|---|
| Produto | Valor da mercadoria | Invoice value, desconto comercial |
| Frete internacional | Transporte externo | Ocean freight, air freight |
| Seguro | Seguro internacional | Insurance premium |
| Impostos | Tributos de importação | II, IPI, PIS, COFINS, ICMS quando aplicável |
| Despesas aduaneiras | Custos do processo aduaneiro | Despachante, armazenagem, taxas portuárias, AFRMM quando aplicável |
| Logística local | Transporte e custos internos | Frete interno, manuseio, entrega ao estoque |
| Custo financeiro | Câmbio e capital | Spread, tarifas, variação cambial, custo de antecipação |

### 6.3 Métodos de rateio por SKU

| Método | Lógica | Uso recomendado |
|---|---|---|
| Igual | Divide o custo igualmente entre os itens | Embarques simples ou custo administrativo fixo |
| Por quantidade | Proporcional à quantidade de unidades | Produtos homogêneos |
| Por valor | Proporcional ao valor da mercadoria | Produtos com valores unitários muito diferentes |
| Por peso | Proporcional ao peso | Fretes ou armazenagem por peso |
| Por volume | Proporcional ao volume | Produtos volumosos |
| Manual auditado | Usuário define percentuais | Casos excepcionais, sempre com justificativa |

### 6.4 Estágios de custo

O sistema deve separar claramente três visões de custo:

| Estágio | Momento | Finalidade |
|---|---|---|
| Estimado | Criação do pedido / proforma | Previsão inicial de margem, caixa e custo |
| Revisado | Chegada de invoice, frete, despachante ou simulação fiscal | Atualização intermediária antes do fechamento |
| Realizado | Pagamentos, DI/DUIMP, NF e despesas finais conciliadas | Custo final auditável para estoque e margem |

Modelo conceitual:

```text
landed_cost_record
├─ id
├─ importation_id
├─ sku_id
├─ cost_type
├─ allocation_method
├─ estimated_amount
├─ estimated_currency
├─ estimated_fx_rate
├─ revised_amount
├─ revised_currency
├─ revised_fx_rate
├─ actual_amount
├─ actual_currency
├─ actual_fx_rate
├─ variance_estimated_vs_revised
├─ variance_revised_vs_actual
├─ variance_estimated_vs_actual
├─ source_document_id
└─ audit_status
```

### 6.5 Fluxo de atualização do landed cost

```text
1. PO/proforma criada
   → sistema calcula custo estimado.

2. Invoice, frete ou estimativas do despachante chegam
   → sistema calcula custo revisado.

3. Pagamentos, impostos, NF e documentos oficiais são registrados
   → sistema calcula custo realizado.

4. Conciliação final
   → custo realizado é travado e distribuído por SKU.

5. Fechamento
   → alteração posterior exige reabertura auditada.
```

---

## 7. Conciliação

### 7.1 Objetivo da conciliação

A conciliação deve garantir que o processo esteja consistente entre documentos, pagamentos, impostos, estoque e custo.

O fechamento só deveria ocorrer quando:

- proforma está vinculada ao pedido;
- invoice final está vinculada à importação;
- pagamentos estão vinculados à invoice correta;
- contratos de câmbio estão registrados;
- DI/DUIMP está vinculada;
- NF de Importação está vinculada;
- documentos obrigatórios estão anexados;
- landed cost realizado está calculado;
- divergências acima de tolerância estão justificadas.

### 7.2 Matriz de conciliação

| Documento / dado | Valor | Moeda | Data | Campo de ligação |
|---|---:|---|---|---|
| Proforma Invoice | Valor estimado | Moeda estrangeira | Data da proforma | `proforma_number` |
| Invoice final | Valor final | Moeda estrangeira | Data da invoice | `invoice_number` |
| Pagamento bancário | Valor pago | BRL e moeda estrangeira | Data do pagamento | `payment_id`, `exchange_contract_number` |
| Contrato de câmbio | Valor contratado | BRL e moeda estrangeira | Contratação / liquidação | `exchange_contract_number` |
| DI/DUIMP | Valor aduaneiro / tributos | BRL | Data de registro | `customs_document_number` |
| NF de Importação | Valor fiscal | BRL | Data de emissão | `nf_number` |
| Custo estimado | Valor previsto | BRL | Data da estimativa | `cost_version_id` |
| Custo realizado | Valor final | BRL | Data do fechamento | `landed_cost_record_id` |

### 7.3 Regras de validação

| Regra | Validação | Severidade sugerida |
|---|---|---|
| Invoice vs pagamento | Soma dos pagamentos deve bater com a invoice, respeitando tolerância | Bloqueante no fechamento |
| Pagamento vs câmbio | Todo pagamento em moeda estrangeira deve ter taxa e contrato ou justificativa | Bloqueante no fechamento |
| DUIMP/DI vs NF | Valores fiscais precisam estar coerentes ou justificados | Bloqueante no fechamento |
| Landed cost vs componentes | Custo realizado deve ser a soma dos componentes alocados | Bloqueante no fechamento |
| Estoque vs recebimento | Quantidade recebida deve bater com quantidade nacionalizada ou ter ajuste | Bloqueante no fechamento |
| Documento obrigatório | Ausência de documento crítico bloqueia fechamento | Bloqueante |
| Diferença pequena | Diferença dentro de tolerância pode ser aprovada com log | Warning auditável |

---

## 8. Descontos, créditos e compensações

### 8.1 Separação conceitual

| Conceito | Definição | Tratamento no sistema | Efeito no landed cost |
|---|---|---|---|
| Desconto comercial | Redução explícita no valor da invoice | Campo `discount_amount` na invoice | Reduz custo do produto |
| Crédito do fornecedor | Crédito posterior por erro, qualidade ou negociação | Entidade `supplier_credit_note` | Normalmente não altera custo já fechado, salvo reabertura |
| Compensação local | Abate ou acerto em compra futura | Entidade de acordo comercial | Não afeta a importação atual, salvo vínculo documental explícito |
| Ajuste financeiro | Diferença cambial, tarifa, IOF, spread ou custo bancário | Registro em `payment_adjustment` | Pode entrar como custo financeiro, se política assim definir |

### 8.2 Regra recomendada

```text
Desconto na invoice → reduz landed cost.
Crédito posterior → vira crédito a receber ou ajuste em compra futura.
Compensação local → não altera custo da importação atual sem aprovação e documento.
Ajuste financeiro → entra no custo financeiro se for diretamente atribuível à importação.
```

Referência citada no texto-base:

- [Consistem — Dados de Importação / desconto na DI](https://ajuda.consistem.com.br/modulos/comercial/manuais-de-telas/comercial-faturamento/faturamento/produtos-para-implantacao-da-nf/aba-dados-importacao)

---

## 9. DI, DUIMP e documentação aduaneira brasileira

### 9.1 Conceitos funcionais

O sistema deve tratar documentos aduaneiros como entidades estruturadas e anexadas ao processo.

Documentos principais:

| Documento | Finalidade |
|---|---|
| Proforma Invoice | Base inicial de negociação e, muitas vezes, do adiantamento |
| Commercial Invoice | Documento comercial final da venda internacional |
| Packing List | Detalhamento físico dos volumes e itens |
| BL / AWB | Conhecimento de embarque marítimo ou aéreo |
| LI / LPCO | Licença, permissão, certificado ou outro documento de anuência |
| DI / DUIMP | Declaração aduaneira |
| Comprovante de Importação | Comprovação da nacionalização |
| Contrato de câmbio | Evidência financeira do fechamento de câmbio |
| NF de Importação | Documento fiscal local |
| Comprovantes de pagamento | Evidência bancária dos pagamentos |
| Documentos do despachante | Taxas, guias, relatórios, memória de cálculo e recibos |

### 9.2 Dados brutos vs dados oficiais

Separar dados importados, digitados ou estimados dos dados oficiais homologados.

```text
customs_document
├─ document_data_json       # dados brutos: planilha, e-mail, PDF, XML, EDI ou input manual
├─ official_data_json       # dados oficiais após registro, homologação ou liberação
├─ status
├─ source_type
├─ source_document_id
└─ validated_at
```

Regra:

```text
official_data_json só deve ser preenchido quando o documento estiver registrado, aprovado, liberado ou homologado, conforme o tipo documental.
```

### 9.3 DUIMP — pontos relevantes para modelagem

Pontos do texto-base:

- DUIMP tende a centralizar e substituir gradualmente a lógica anterior de DI em operações obrigatórias;
- controle passa a ser mais granular por item;
- informações de Catálogo de Produtos, operador estrangeiro e LPCO podem ser reaproveitadas;
- o sistema deve estar preparado para guardar dados por item e não apenas por processo agregado.

---

## 10. Modelo de dados conceitual

### 10.1 Entidades principais

```text
importation_order
├─ id
├─ po_number
├─ supplier_id
├─ importer_entity_id
├─ currency
├─ incoterm
├─ estimated_total
├─ current_status
├─ created_at
├─ created_by
└─ closed_at

invoice
├─ id
├─ importation_id
├─ invoice_number
├─ invoice_date
├─ amount
├─ currency
├─ is_proforma
├─ payment_status
├─ discount_amount
├─ source_document_id
└─ audit_status

payment
├─ id
├─ invoice_id
├─ payment_type
├─ payment_date
├─ amount_foreign
├─ amount_local
├─ exchange_rate
├─ exchange_contract_number
├─ settlement_date
├─ bank_name
├─ source_document_id
└─ audit_status

importation_item
├─ id
├─ importation_id
├─ sku_id
├─ supplier_sku
├─ description
├─ quantity_ordered
├─ quantity_shipped
├─ quantity_received
├─ unit_price_foreign
├─ gross_amount_foreign
├─ discount_amount_foreign
└─ net_amount_foreign

landed_cost_record
├─ id
├─ importation_id
├─ sku_id
├─ cost_type
├─ allocation_method
├─ estimated_amount
├─ revised_amount
├─ actual_amount
├─ variance_amount
├─ source_document_id
└─ audit_status

customs_document
├─ id
├─ importation_id
├─ document_type
├─ document_number
├─ document_date
├─ document_data_json
├─ official_data_json
├─ status
├─ source_document_id
└─ validated_at

document_attachment
├─ id
├─ importation_id
├─ entity_type
├─ entity_id
├─ file_name
├─ file_hash
├─ version
├─ uploaded_by
├─ uploaded_at
└─ is_current_version

reason_code
├─ id
├─ code
├─ category
├─ label
├─ description
├─ is_active
├─ requires_comment
└─ created_at

status_transition_log
├─ id
├─ importation_id
├─ from_status
├─ to_status
├─ action
├─ user_id
├─ timestamp
├─ reason_code_id
├─ comment
├─ blocking_checks_json
└─ attachment_id

audit_log
├─ id
├─ entity_type
├─ entity_id
├─ action
├─ user_id
├─ timestamp
├─ old_value_json
├─ new_value_json
├─ reason_code_id
├─ justification
├─ attachment_id
└─ ip_or_machine_info
```

### 10.2 Relacionamentos principais

```text
importation_order 1:N invoice
invoice 1:N payment
importation_order 1:N importation_item
importation_item 1:N landed_cost_record
importation_order 1:N customs_document
importation_order 1:N document_attachment
importation_order 1:N status_transition_log
reason_code 1:N audit_log
reason_code 1:N status_transition_log
qualquer entidade crítica 1:N audit_log
```


### 10.3 Entidades complementares obrigatórias

```text
users
├─ id
├─ name
├─ email
├─ password_hash
├─ role_id
├─ is_active
├─ created_at
└─ last_login

roles
├─ id
├─ name
├─ description
├─ permissions_json
└─ created_at

suppliers
├─ id
├─ name
├─ country
├─ tax_id
├─ contact_name
├─ contact_email
├─ currency_default
└─ is_active

shipments
├─ id
├─ importation_id
├─ modal (AIR | OCEAN | OTHER)
├─ modal_previous
├─ etd_planned
├─ etd_revised
├─ etd_actual
├─ eta_planned
├─ eta_revised
├─ eta_actual
├─ bl_number
├─ awb_number
├─ container_number
├─ freight_amount
├─ freight_currency
├─ status
├─ reason_code_id
├─ created_by
└─ created_at

shipment_items
├─ id
├─ shipment_id
├─ importation_item_id
├─ sku_id
└─ quantity_shipped

taxes
├─ id
├─ importation_id
├─ customs_document_id
├─ tax_type (II | IPI | PIS | COFINS | ICMS | OTHER)
├─ base_amount
├─ rate
├─ calculated_amount
├─ paid_amount
├─ variance_amount
├─ source_document_id
├─ status
└─ audit_status

expenses
├─ id
├─ importation_id
├─ expense_type (FREIGHT | INSURANCE | STORAGE | CUSTOMS_AGENT | BANK_FEE | LOCAL_TRANSPORT | OTHER)
├─ description
├─ amount
├─ currency
├─ exchange_rate
├─ amount_local
├─ supplier_id
├─ source_document_id
├─ is_included_in_landed_cost
└─ audit_status

discounts
├─ id
├─ invoice_id
├─ importation_item_id (nullable)
├─ discount_type (ITEM | GLOBAL)
├─ amount
├─ currency
├─ reason
├─ source_document_id
└─ audit_status

credits
├─ id
├─ supplier_id
├─ origin_importation_id
├─ credit_type
├─ amount
├─ currency
├─ amount_used
├─ amount_available
├─ status (AVAILABLE | PARTIAL | USED | CANCELLED | DISPUTED)
├─ source_document_id
├─ used_in_importation_id (nullable)
├─ approved_by
└─ audit_status

exchange_rates
├─ id
├─ currency_from
├─ currency_to
├─ rate_date
├─ rate_type (ESTIMATED | CONTRACTED | SETTLED)
├─ rate_value
├─ source
├─ importation_id (nullable)
├─ payment_id (nullable)
├─ registered_by
└─ registered_at

reconciliations
├─ id
├─ importation_id
├─ reconciliation_type
├─ source_a_entity
├─ source_a_id
├─ source_a_value
├─ source_b_entity
├─ source_b_id
├─ source_b_value
├─ variance_amount
├─ tolerance_amount
├─ status (RECONCILED | DIVERGENT | PENDING_DOCUMENT | PENDING_APPROVAL | MANUAL_APPROVED | IGNORED_WITH_JUSTIFICATION)
├─ reason_code_id
├─ resolved_by
├─ resolved_at
└─ audit_status

raw_import_files
├─ id
├─ file_name
├─ file_hash
├─ file_size
├─ file_type
├─ source_system (HEROES_SPREADSHEET | EMAIL | OTHER)
├─ uploaded_by
├─ uploaded_at
├─ status (PENDING | PROCESSING | DONE | ERROR)
└─ error_log

staging_import_rows
├─ id
├─ raw_import_file_id
├─ row_number
├─ raw_data_json
├─ parsed_data_json
├─ status (PENDING_REVIEW | APPROVED | REJECTED | MERGED)
├─ issues_json
├─ reviewed_by
├─ reviewed_at
├─ merged_into_entity
└─ merged_into_id

review_queue
├─ id
├─ staging_import_row_id
├─ importation_id (nullable)
├─ issue_type
├─ issue_description
├─ assigned_to
├─ priority
├─ status (OPEN | IN_REVIEW | RESOLVED | IGNORED)
├─ resolved_by
├─ resolved_at
└─ resolution_note
```

### 10.4 Relacionamentos complementares

```text
importation_order N:1 suppliers
importation_order 1:N shipments
shipment 1:N shipment_items
importation_order 1:N taxes
importation_order 1:N expenses
invoice 1:N discounts
suppliers 1:N credits
importation_order 1:N reconciliations
raw_import_files 1:N staging_import_rows
staging_import_rows 1:N review_queue
users N:1 roles
```

### 10.5 Diferença entre camadas de dado

| Camada | Tabelas | Finalidade |
|---|---|---|
| Bruta | raw_import_files | Arquivo original recebido. Nunca alterado, nunca apagado. |
| Staging | staging_import_rows | Dados parseados linha a linha. Aguardam revisão humana. |
| Revisão | review_queue | Itens com problema ou ambiguidade que exigem decisão manual. |
| Oficial | importation_order, invoice, payment, shipment, taxes, expenses, discounts, credits | Dado aprovado e rastreável. Nunca deletado, apenas anulado com log. |
| Calculada | landed_cost_record, reconciliations, exchange_rates | Derivada dos dados oficiais. Versionada e auditável. |
| Auditoria | audit_log, status_transition_log | Histórico imutável de quem fez o quê, quando e por quê. |

---

## 11. Governança mínima

### 11.1 Auditoria obrigatória

Eventos que devem gerar log:

- criação de pedido;
- alteração de valores, moeda, quantidade, fornecedor, SKU ou Incoterm;
- inclusão, edição ou exclusão de invoice;
- registro ou alteração de pagamento;
- alteração de taxa de câmbio;
- inclusão ou substituição de documento crítico;
- alteração de landed cost;
- fechamento da importação;
- reabertura da importação;
- cancelamento de processo;
- override manual de rateio ou custo.

Campos mínimos do log:

```text
Quem alterou
Quando alterou
Qual entidade alterou
Qual ação executou
Valor anterior
Valor novo
Justificativa
Documento/anexo associado, quando aplicável
```

Referências citadas no texto-base:

- [UAN — Auditoria de documentos](https://www.uan.com.br/blog/auditoria-de-documentos-como-rastrear-acessos-e-alteracoes-em-arquivos-criticos-com-seguranca)
- [SIMA Gestão — GED e auditoria](https://simagestao.com.br/3-perguntas-que-todo-auditor-faz-e-como-responde-las-com-um-ged-gestao-de-documentos/)

### 11.2 Códigos de motivo obrigatórios

Justificativas críticas devem ser estruturadas com códigos de motivo controlados. O campo de texto livre deve existir apenas como complemento, não como fonte primária da classificação.

Eventos que devem exigir `reason_code`:

- reabertura de importação fechada;
- cancelamento de processo;
- divergência de quantidade recebida vs embarcada;
- divergência financeira acima da tolerância;
- alteração de modal logístico;
- troca de fornecedor, SKU, NCM ou Incoterm após aprovação;
- override manual de landed cost ou método de rateio;
- substituição de documento oficial;
- baixa manual de pendência documental ou financeira.

Tabela de motivos sugerida:

| Categoria | Código | Uso |
|---|---|---|
| Reabertura | `REOPEN_QTY_DISCREPANCY` | Reabrir por divergência de quantidade |
| Reabertura | `REOPEN_FINANCIAL_DISCREPANCY` | Reabrir por diferença financeira/cambial |
| Reabertura | `REOPEN_DOCUMENT_CORRECTION` | Reabrir por documento incorreto ou substituído |
| Cancelamento | `CANCEL_SUPPLIER_REQUEST` | Cancelamento solicitado pelo fornecedor |
| Cancelamento | `CANCEL_INTERNAL_DECISION` | Cancelamento por decisão interna |
| Divergência | `DISCREPANCY_PRICE` | Divergência de preço unitário ou total |
| Divergência | `DISCREPANCY_QUANTITY` | Divergência de quantidade |
| Divergência | `DISCREPANCY_EXCHANGE_RATE` | Divergência de taxa ou contrato de câmbio |
| Logística | `MODAL_CHANGE_COST` | Mudança de modal por custo |
| Logística | `MODAL_CHANGE_URGENCY` | Mudança de modal por urgência/prazo |
| Custo | `LANDED_COST_OVERRIDE` | Ajuste manual de landed cost |
| Documento | `OFFICIAL_DOC_REPLACED` | Substituição de documento oficial |

Regra de implementação:

```text
reason_code.category define onde o motivo pode ser usado.
reason_code.requires_comment define se o usuário precisa complementar a justificativa.
Motivos inativos não aparecem para novas ações, mas permanecem no histórico.
Relatórios devem permitir filtros por reason_code, categoria, usuário e período.
```

### 11.3 Anexos obrigatórios por fase

| Fase | Documento obrigatório |
|---|---|
| Proforma | Proforma Invoice |
| Pagamento antecipado | Comprovante bancário e/ou contrato de câmbio |
| Embarque | BL, AWB ou documento equivalente |
| Desembaraço | DI/DUIMP e documentos do despachante |
| Fiscal | NF de Importação |
| Recebimento | Conferência de estoque ou documento de recebimento |
| Fechamento | Relatório de conciliação |
| Reabertura | Justificativa e termo/documento de reabertura |

### 11.4 Fechamento financeiro auditável

Checklist de fechamento:

```text
1. Todas as invoices relevantes estão cadastradas.
2. Todas as invoices têm status financeiro coerente.
3. Todos os pagamentos têm contrato/taxa de câmbio ou justificativa.
4. Todos os documentos críticos estão anexados.
5. DI/DUIMP está registrada e vinculada.
6. NF de Importação está vinculada.
7. Quantidades recebidas foram conferidas.
8. Landed cost realizado foi calculado e alocado por SKU.
9. Diferenças acima da tolerância foram justificadas.
10. Usuário autorizado executou fechamento.
11. AuditLog registrou o fechamento.
```

### 11.5 Reabertura controlada

Regra sugerida:

```text
Uma importação fechada não pode ser editada diretamente.
Para alterar, o usuário precisa reabrir o processo.
A reabertura exige permissão, reason_code, justificativa complementar quando aplicável e registro no AuditLog.
Após reabertura, todas as novas alterações geram nova trilha de auditoria.
```

Referência citada no texto-base:

- [VExpenses — Conciliação e desconciliação](https://suporte.vexpenses.com.br/hc/pt-br/articles/17136141730452-Como-conciliar-as-despesas-enviadas-pelo-banco-para-a-presta%C3%A7%C3%A3o-de-contas)

---

## 12. Fluxo operacional consolidado

```text
PO_CREATED
  ↓
PROFORMA_RECEIVED
  ↓
ADVANCE_PAID                  # opcional, mas comum
  ↓
LI_PENDING / LPCO_PENDING     # se aplicável
  ↓
LI_APPROVED / LPCO_APPROVED
  ↓
BOOKED
  ↓
SHIPPED
  ↓
IN_TRANSIT
  ↓
ARRIVED / UNLOADED
  ↓
DI_SUBMITTED ou DUIMP_REGISTERED
  ↓
ANUENCIA_PENDING              # se aplicável
  ↓
ANUENCIA_APPROVED             # se aplicável
  ↓
CUSTOMS_RELEASED / CLEARED
  ↓
DELIVERED
  ↓
RECEIVED_IN_STOCK
  ↓
NF_IMPORT_ISSUED / INVOICED
  ↓
CONCILIATION_DONE
  ↓
CLOSED
```

---

## 13. Telas sugeridas para o sistema

### 13.1 Dashboard de importações

Objetivo: visão executiva dos processos em aberto.

Componentes:

- cards por status;
- importações atrasadas;
- importações com divergência financeira;
- importações aguardando documento;
- importações próximas do desembaraço;
- landed cost estimado vs realizado;
- pagamentos pendentes;
- alertas de documentação.

### 13.2 Tela de processo de importação

Abas sugeridas:

1. **Resumo** — status, fornecedor, PO, moeda, Incoterm, valor, datas principais.
2. **Itens/SKUs** — quantidades, preços, descontos, NCM, peso, volume.
3. **Invoices** — proforma, invoices finais, descontos e vínculos.
4. **Pagamentos/Câmbio** — adiantamentos, parciais, finais, contratos, taxas.
5. **Logística** — booking, BL/AWB, previsão, chegada e entrega.
6. **Aduaneiro** — DI/DUIMP, LI/LPCO, anuências e documentos oficiais.
7. **Landed Cost** — estimado, revisado, realizado e rateio por SKU.
8. **Conciliação** — checks, divergências, tolerâncias e aprovação.
9. **Documentos** — anexos versionados.
10. **Linha do tempo** — histórico cronológico legível do processo.
11. **Auditoria** — trilha técnica de alterações.

Comportamento obrigatório de navegação relacional:

- qualquer card, documento, pagamento, invoice, item ou evento físico deve ter link para o processo de importação relacionado;
- a partir de uma chegada de mercadoria, o usuário deve visualizar pedido original, proformas, invoices, pagamentos, documentos de embarque, DI/DUIMP, NF, SKUs recebidos e landed cost rateado;
- a partir de uma invoice, o usuário deve visualizar pagamentos, câmbio, descontos, documentos associados, itens cobertos e impacto no landed cost;
- a partir de um SKU, o usuário deve visualizar importações relacionadas, quantidades, custos rateados, documentos e divergências;
- a interface deve evitar módulos estanques. O processo de importação deve funcionar como “hub” relacional.

### 13.3 Tela de landed cost

Campos principais:

- visão por importação;
- visão por SKU;
- custo estimado, revisado e realizado;
- método de rateio;
- variações absolutas e percentuais;
- origem documental de cada custo;
- status de validação.

### 13.4 Tela de conciliação

Blocos sugeridos:

- invoice vs pagamentos;
- pagamentos vs contratos de câmbio;
- invoice vs DI/DUIMP;
- DI/DUIMP vs NF;
- landed cost vs componentes;
- quantidade importada vs quantidade recebida;
- divergências abertas;
- botão de fechamento, apenas se não houver bloqueios.

### 13.5 Linha do tempo de atividades

A linha do tempo deve transformar o `audit_log` e o `status_transition_log` em uma história operacional legível da importação. Não basta o sistema gravar logs técnicos; o usuário precisa conseguir entender o que aconteceu, em que ordem, por quem e com qual impacto.

Cada evento da linha do tempo deve exibir:

| Campo | Descrição |
|---|---|
| Data/hora | Momento exato do evento |
| Usuário | Quem executou a ação |
| Tipo de evento | Status, documento, pagamento, invoice, landed cost, divergência, conciliação ou reabertura |
| Entidade afetada | Objeto impactado pela ação |
| Impacto | Resumo do que mudou |
| Motivo | `reason_code` quando aplicável |
| Documento associado | Link para anexo ou versão documental |
| Ação disponível | Abrir documento, ver diff, abrir invoice, abrir pagamento, abrir custo ou abrir divergência |

Eventos que devem aparecer na linha do tempo:

- criação do processo;
- recebimento de proforma;
- registro de pagamento ou contrato de câmbio;
- alteração de status logístico;
- inclusão/substituição de documento;
- registro de DI/DUIMP, NF ou desembaraço;
- alteração de landed cost;
- abertura e resolução de divergência;
- conciliação;
- fechamento;
- reabertura;
- cancelamento.

### 13.6 Tela de bloqueios de status

Sempre que o usuário tentar avançar uma etapa e o sistema bloquear a transição, a interface deve mostrar uma lista objetiva de pendências.

Exemplo:

```text
Não foi possível mover de RECEIVED_IN_STOCK para CONCILIATION_DONE.
Bloqueios encontrados:
1. Invoice final INV-2026-014 não possui pagamento final vinculado.
2. Contrato de câmbio do pagamento PAY-003 está sem comprovante.
3. Landed cost realizado possui divergência de R$ 4.320 acima da tolerância.
4. NF de Importação ainda não foi anexada.
```

A tela deve permitir que o usuário clique diretamente na pendência para ir ao objeto responsável pelo bloqueio.

---

## 14. MVP recomendado

### 14.1 O que entra no MVP

Priorizar o que reduz risco operacional e financeiro rapidamente:

1. Cadastro de importação/processo.
2. Cadastro de fornecedores e SKUs básicos.
3. Importação ou digitação de proforma/invoice.
4. Controle de pagamentos e câmbio.
5. Upload/versionamento de documentos.
6. Status operacional simples com transições bloqueantes.
7. Landed cost estimado/revisado/realizado.
8. Conciliação básica.
9. AuditLog para alterações críticas.
10. Códigos de motivo para exceções, divergências, cancelamentos e reaberturas.
11. Linha do tempo visível por processo.
12. Relatório de fechamento por importação.

### 14.2 O que não deveria entrar no MVP

Evitar escopo de ERP completo:

- contabilidade completa;
- fiscal completo;
- WMS completo;
- integração bancária automática complexa;
- integração direta com Portal Único;
- motor tributário sofisticado;
- workflow corporativo pesado;
- multiempresa avançado;
- permissões excessivamente granulares.

### 14.3 Premissa de arquitetura para MVP local

Arquitetura coerente com operação pequena:

```text
Aplicação web local em rede interna
PostgreSQL local
Sem Docker no MVP
Login e senha
Auditoria forte
Backup diário
Anexos versionados em pasta controlada
Exportação Excel/CSV/PDF quando necessário
```

---

## 15. Decisões práticas para o projeto

| Tema | Decisão recomendada |
|---|---|
| Status | Usar taxonomia simples, com histórico de status e transições bloqueantes |
| Proforma | Entidade própria, não apenas campo do PO |
| Invoice | Permitir múltiplas invoices por importação |
| Pagamento | Permitir múltiplos pagamentos por invoice |
| Câmbio | Versionar por pagamento |
| Landed cost | Separar estimado, revisado e realizado |
| Rateio | Permitir método por custo, quantidade, valor, peso, volume ou manual auditado |
| Desconto | Desconto na invoice reduz custo; crédito posterior não reduz automaticamente |
| Documento | Anexo obrigatório para eventos críticos |
| Navegação | Processo de importação como hub relacional entre pedido, invoice, pagamento, documento, SKU e custo |
| Justificativa | Usar códigos de motivo controlados, com texto livre apenas como complemento |
| Fechamento | Bloqueado se houver divergência crítica, documento pendente ou conciliação inválida |
| Reabertura | Só com permissão, reason_code, justificativa complementar e log |
| Auditoria | Obrigatória em qualquer dado financeiro, fiscal, documental ou de custo; linha do tempo visível ao usuário |

---

## 16. Riscos funcionais

| Risco | Consequência | Mitigação |
|---|---|---|
| Misturar PO, proforma e invoice | Perda de rastreabilidade financeira | Modelar entidades separadas |
| Tratar pagamento como único | Erro em importações com adiantamento/parciais | Permitir 1:N entre invoice e pagamento |
| Usar uma taxa de câmbio por processo | Custo errado quando há múltiplos pagamentos | Câmbio por pagamento |
| Não separar custo estimado/revisado/realizado | Margem e estoque inconsistentes | Versionar landed cost por estágio |
| Não guardar documentos | Sistema vira planilha sem prova | Anexos obrigatórios e versionados |
| Fechar processo sem conciliação | Erro fiscal/financeiro escondido | Checklist de fechamento bloqueante |
| Reabrir sem controle | Perda de governança | Reabertura auditada |
| Copiar ERP completo | Escopo grande demais para MVP | Inspirar-se nos ERPs, mas implementar apenas o núcleo necessário |
| Navegação fragmentada por módulo | Usuário não entende rapidamente a história da importação | Processo como hub relacional e links entre documentos/eventos |
| Justificativas em texto livre | Baixa capacidade de análise de causa-raiz | Códigos de motivo obrigatórios e filtráveis |
| Status editável sem regra | Fechamento ou avanço indevido de processo pendente | Máquina de estados com bloqueios por documento, permissão e conciliação |
| Log técnico invisível | Auditoria existe, mas operação não consegue usar | Linha do tempo cronológica dentro do processo |

---

## 17. Glossário rápido

| Termo | Significado |
|---|---|
| PO | Purchase Order / pedido de compra |
| SI | Solicitação de Importação |
| Proforma Invoice | Documento preliminar usado para negociação e, muitas vezes, pagamento antecipado |
| Commercial Invoice | Invoice final da venda internacional |
| BL | Bill of Lading, conhecimento de embarque marítimo |
| AWB | Air Waybill, conhecimento de embarque aéreo |
| LI | Licença de Importação |
| LPCO | Licenças, Permissões, Certificados e Outros documentos |
| DI | Declaração de Importação |
| DUIMP | Declaração Única de Importação |
| NF de Importação | Nota Fiscal emitida no Brasil para nacionalização fiscal |
| Landed Cost | Custo total da mercadoria importada até estar disponível em estoque |
| Incoterm | Termo internacional que define responsabilidades de frete, risco e custos |
| Rateio | Distribuição de custos entre SKUs ou itens |
| Anuência | Aprovação de órgão regulador ou fiscalizador |

---

## 18. Resumo executivo

O sistema ideal para este caso deve ser um controle de importação enxuto, com forte rastreabilidade financeira, documental e operacional. A modelagem central deve separar pedido, proforma, invoice, pagamento, câmbio, documentos aduaneiros, itens e landed cost. A interface deve tratar o processo de importação como hub relacional: de qualquer documento, evento físico, pagamento, invoice ou SKU, o usuário deve conseguir chegar rapidamente aos demais objetos conectados.

O principal risco é tentar copiar um ERP completo; o melhor caminho é absorver os padrões funcionais de ERPs e sistemas de comex, mas implementar um núcleo local, auditável e objetivo. Status não deve ser um campo livre: deve ser controlado por transições bloqueantes que validam documentação, permissão e conciliação financeira. Exceções, cancelamentos, divergências e reaberturas devem usar códigos de motivo padronizados.

O MVP deve entregar rapidamente uma visão confiável de: onde está cada importação, quanto já foi pago, qual taxa de câmbio foi usada, quais documentos existem, qual é o custo estimado/revisado/realizado, por que houve exceções, quais bloqueios impedem o fechamento e qual é a linha do tempo completa do processo.

---

## 19. Roadmap por fases

### Fase 0 — Levantamento e blueprint

**Objetivo:** mapear fluxo real, documentos, planilhas existentes e decisões pendentes antes de codificar.

**Entregáveis:**
- blueprint finalizado;
- checklist de requisitos;
- exemplos reais de planilha e emails da Heroes anonimizados;
- lista de status;
- lista de reason codes;
- definição de tolerâncias de conciliação;
- decisão de stack.

**Entidades/tabelas envolvidas:**
- nenhuma criada ainda.

**Telas:**
- nenhuma.

**Regras de negócio ativas nesta fase:**
- nenhuma.

**Critérios de aceite:**
- blueprint aprovado;
- stack definido;
- pelo menos um exemplo real de planilha da Heroes disponível para testes.

**Riscos:**
- começar a codificar sem exemplo real de planilha;
- não definir tolerâncias de conciliação antes de implementar.

**Fora desta fase:**
- qualquer código.

---

### Fase 1 — Fundação técnica e governança

**Objetivo:** sistema rodando localmente com login, permissões, audit log e backup funcionando.

**Entregáveis:**
- app web acessível na rede interna via navegador;
- PostgreSQL local;
- login individual;
- roles e permissions básicos;
- audit_log gravando;
- backup diário configurado;
- script de start/restart documentado.

**Entidades/tabelas envolvidas:**
- users;
- roles;
- audit_log;
- status_transition_log;
- reason_code.

**Telas:**
- login;
- tela de usuários e perfis (admin).

**Regras de negócio ativas nesta fase:**
- autenticação obrigatória;
- toda ação crítica grava audit_log;
- reason_code obrigatório para ações de exceção.

**Critérios de aceite:**
- outro computador da rede acessa o sistema pelo navegador;
- login inválido é bloqueado;
- alteração crítica sem motivo é bloqueada;
- backup roda e gera log de sucesso.

**Riscos:**
- IP do servidor não fixo;
- firewall bloqueando porta;
- backup sem teste de restauração.

**Fora desta fase:**
- qualquer módulo operacional.

---

### Fase 2 — Cadastros mestres

**Objetivo:** estrutura básica de fornecedores, SKUs, moedas e tipos de custo disponível.

**Entregáveis:**
- CRUD de suppliers;
- CRUD de products/SKUs;
- CRUD de exchange_rates;
- CRUD de reason_codes;
- tipos de despesa/documento.

**Entidades/tabelas envolvidas:**
- suppliers;
- products (SKUs);
- exchange_rates;
- reason_code.

**Telas:**
- cadastro de fornecedores;
- cadastro de SKUs;
- cadastro de moedas/taxas;
- cadastro de reason codes.

**Regras de negócio ativas nesta fase:**
- fornecedor e SKU obrigatórios para criar importação;
- campo vazio não vira zero;
- dado inativado não some do histórico.

**Critérios de aceite:**
- usuário consegue cadastrar fornecedor, SKU e taxa de câmbio;
- inativação preserva histórico.

**Riscos:**
- SKU sem NCM dificulta aduana futura;
- não definir campos obrigatórios agora gera retrabalho.

**Fora desta fase:**
- importações;
- invoices;
- financeiro.

---

### Fase 3 — Importações, itens e invoices

**Objetivo:** registrar pedidos de importação com itens e invoices vinculadas, incluindo ANTECIPO.

**Entregáveis:**
- CRUD de importation_order;
- CRUD de importation_item;
- CRUD de invoice;
- invoice com tipo ANTECIPO, PROFORMA, SALDO, COMPLEMENTAR, AJUSTE, CREDITO, OUTRA;
- múltiplas invoices por importação;
- status inicial com transições bloqueantes básicas.

**Entidades/tabelas envolvidas:**
- importation_order;
- importation_item;
- invoice;
- status_transition_log.

**Telas:**
- lista de importações;
- detalhe da importação (abas Resumo e Itens/SKUs);
- tela de invoice;
- painel simples de pendências.

**Regras de negócio ativas nesta fase:**
- uma importação pode ter N invoices;
- ANTECIPO pode existir sem embarque vinculado;
- campo vazio não vira zero;
- alteração de invoice gera audit_log;
- anulação preserva histórico.

**Critérios de aceite:**
- importação com 3 invoices incluindo ANTECIPO funciona;
- invoice com campo vazio não cria zero;
- anulação de invoice mantém registro.

**Riscos:**
- modelar invoice como campo do pedido em vez de entidade própria;
- não separar proforma de invoice final.

**Fora desta fase:**
- pagamentos;
- embarques;
- aduana.

---

### Fase 4 — Controle financeiro

**Objetivo:** pagamentos, câmbio versionado, descontos, créditos e saldos por invoice e por importação.

**Entregáveis:**
- CRUD de payments;
- CRUD de discounts;
- CRUD de credits;
- exchange_rates por pagamento;
- saldo calculado por invoice;
- saldo consolidado por importação;
- diferença previsto vs realizado visível.

**Entidades/tabelas envolvidas:**
- payment;
- discounts;
- credits;
- exchange_rates.

**Telas:**
- painel financeiro da importação;
- tela de pagamentos;
- tela de descontos e créditos;
- saldo por invoice;
- saldo consolidado.

**Regras de negócio ativas nesta fase:**
- pagamento exige comprovante ou justificativa aprovada;
- câmbio versionado por pagamento;
- crédito não vira desconto automaticamente;
- uso duplicado de crédito bloqueado;
- alteração financeira crítica exige reason_code.

**Critérios de aceite:**
- pagamento parcial funciona;
- câmbio diferente do previsto registra variação;
- uso duplicado de crédito é bloqueado;
- saldo por invoice é calculado corretamente.

**Riscos:**
- lançar câmbio único por importação em vez de por pagamento;
- não separar crédito de desconto.

**Fora desta fase:**
- embarques;
- aduana;
- landed cost.

---

### Fase 5 — Documentos e ingestão da planilha Heroes

**Objetivo:** upload de documentos versionados e pipeline de ingestão bruto/staging/revisão para a planilha italiana.

**Entregáveis:**
- upload de document_attachment com versionamento e hash;
- raw_import_files;
- staging_import_rows;
- review_queue;
- fila de revisão humana antes de oficializar qualquer dado importado;
- backup incluindo pasta de anexos.

**Entidades/tabelas envolvidas:**
- document_attachment;
- raw_import_files;
- staging_import_rows;
- review_queue.

**Telas:**
- tela de documentos por importação;
- tela de fila de revisão;
- tela de importação de arquivo Heroes.

**Regras de negócio ativas nesta fase:**
- arquivo bruto nunca apagado;
- documento substituído mantém histórico com hash;
- dado importado não vira oficial sem aprovação humana;
- linha ambígua vai para review_queue;
- erro de importação entra no log técnico.

**Critérios de aceite:**
- upload com substituição preserva versão anterior;
- linha da planilha Heroes com campo vazio vai para revisão, não vira zero;
- backup inclui pasta de anexos.

**Riscos:**
- assumir que a planilha da Heroes tem formato fixo;
- não tratar colunas ausentes ou renomeadas.

**Fora desta fase:**
- logística;
- aduana.

---

### Fase 6 — Logística e embarques

**Objetivo:** controle de embarques com modal, múltiplos embarques por importação e alteração de modal auditada.

**Entregáveis:**
- CRUD de shipments e shipment_items;
- suporte a AIR, OCEAN, OTHER;
- múltiplos embarques por importação;
- alteração de modal com reason_code, log e recálculo de prazo/custo estimado;
- rastreamento de quantidades por etapa (pedida, embarcada).

**Entidades/tabelas envolvidas:**
- shipments;
- shipment_items.

**Telas:**
- aba Logística no processo de importação;
- tela de embarque;
- histórico de alterações de modal.

**Regras de negócio ativas nesta fase:**
- alteração de modal exige reason_code;
- modal anterior preservado;
- custo estimado recalculado após mudança;
- quantidade embarcada não pode exceder pedida sem justificativa.

**Critérios de aceite:**
- importação com 2 embarques de modais diferentes funciona;
- mudança de modal sem motivo é bloqueada;
- histórico de modal anterior visível.

**Riscos:**
- modelar embarque como campo da importação em vez de entidade própria.

**Fora desta fase:**
- aduana;
- landed cost.

---

### Fase 7 — Aduana, impostos e nacionalização

**Objetivo:** DI/DUIMP, impostos, despesas do despachante, nacionalização e entrada mínima em estoque.

**Entregáveis:**
- customs_document com dado bruto vs oficial;
- taxes por tipo (II, IPI, PIS, COFINS, ICMS);
- expenses por tipo (despachante, armazenagem, frete interno, taxas portuárias);
- evento de nacionalização;
- quantidade nacionalizada por SKU;
- entrada mínima em estoque vinculada à nacionalização.

**Entidades/tabelas envolvidas:**
- customs_document;
- taxes;
- expenses.

**Telas:**
- aba Aduaneiro no processo de importação;
- tela de despesas;
- tela de impostos;
- tela de nacionalização.

**Regras de negócio ativas nesta fase:**
- imposto exige documento;
- despesa de despachante exige evidência;
- nacionalização exige DI/DUIMP válida;
- entrada em estoque não pode exceder quantidade nacionalizada sem justificativa;
- divergência de quantidade vai para reconciliations.

**Critérios de aceite:**
- importação com DI/DUIMP, impostos e despesas registrados fecha fase aduaneira;
- tentativa de estoque acima do nacionalizado é bloqueada ou exige reason_code.

**Riscos:**
- não tratar dados brutos do despachante como staging antes de oficializar.

**Fora desta fase:**
- landed cost;
- conciliação.

---

### Fase 8 — Landed cost

**Objetivo:** cálculo de custo total por importação e custo unitário por SKU, versionado e rastreável.

**Entregáveis:**
- landed_cost_record com estimado, revisado e realizado;
- métodos de rateio (valor FOB, quantidade, peso, volume, manual auditado);
- custo unitário por SKU;
- variâncias entre versões;
- versão aprovada apontada pelo fechamento.

**Entidades/tabelas envolvidas:**
- landed_cost_record (versões).

**Telas:**
- aba Landed Cost no processo;
- tela de rateio por SKU;
- comparativo estimado vs revisado vs realizado.

**Regras de negócio ativas nesta fase:**
- nova versão não apaga versão anterior;
- mudança de modal, câmbio, imposto, despesa ou crédito pode gerar nova versão;
- rateio manual exige reason_code;
- fechamento aponta versão aprovada.

**Critérios de aceite:**
- custo unitário por SKU calculado e rastreável até seus componentes;
- versão anterior preservada após revisão;
- rateio manual sem justificativa bloqueado.

**Riscos:**
- recalcular versão anterior silenciosamente ao alterar câmbio ou despesa.

**Fora desta fase:**
- conciliação formal;
- fechamento.

---

### Fase 9 — Conciliação e fechamento

**Objetivo:** regras de conciliação entre todas as fontes, fechamento auditável e reabertura controlada.

**Entregáveis:**
- reconciliations para todos os pares obrigatórios;
- tela de conciliação com divergências e tolerâncias;
- checklist de fechamento bloqueante;
- fechamento com snapshot de dados críticos;
- reabertura com reason_code e novo fechamento gerando nova versão;
- linha do tempo completa do processo.

**Entidades/tabelas envolvidas:**
- reconciliations;
- status_transition_log (completo).

**Telas:**
- tela de conciliação;
- tela de fechamento;
- tela de bloqueios de status;
- linha do tempo de atividades.

**Regras de negócio ativas nesta fase:**
- divergência acima da tolerância bloqueia fechamento ou exige aprovação formal;
- fechamento exige documentos mínimos e conciliações resolvidas;
- importação fechada não editável sem reabertura;
- reabertura exige permissão, reason_code e log;
- novo fechamento gera nova versão.

**Critérios de aceite:**
- fechamento com divergência não justificada é bloqueado;
- reabertura sem motivo é bloqueada;
- linha do tempo mostra história completa legível;
- snapshot do fechamento preservado após reabertura.

**Riscos:**
- não definir tolerâncias numéricas antes de implementar;
- deixar divergências "menores" sem fila de revisão.

**Fora desta fase:**
- integração com contabilidade;
- fiscal completo;
- WMS;
- BI.

