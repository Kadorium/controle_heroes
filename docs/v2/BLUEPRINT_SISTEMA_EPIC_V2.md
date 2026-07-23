# Blueprint do Sistema Epic Controle — V2

## 1. Identidade, escopo e autoridade documental

| Campo | Valor |
|---|---|
| **Título** | Blueprint do Sistema Epic Controle V2 |
| **Versão** | 0.2.4 |
| **Status** | Aprovado — baseline funcional e arquitetural da V2 |
| **Data** | 2026-07-22 |
| **Objetivo** | Definir o **destino** do sistema V2 (produto, módulos, regras, telas, NFR, aceite) sem status de execução |

### 1.1 Documentos relacionados

| Documento | Papel |
|---|---|
| [`ROADMAP_V2_EPIC.md`](../../ROADMAP_V2_EPIC.md) | Execução, fases, gates, ADRs, evidências, bloqueios |
| [`docs/README.md`](../README.md) | Índice e autoridade por assunto |
| [`.cursor/rules/epic-project-router.mdc`](../../.cursor/rules/epic-project-router.mdc) | Roteamento global V1 vs V2 |
| [`.cursor/rules/epic-v2-architecture.mdc`](../../.cursor/rules/epic-v2-architecture.mdc) | Método em `v2/**` + docs V2 |
| Documentação V1 (`docs/v1/`) | Referência legada — ver [`docs/v1/README.md`](../v1/README.md); canônicos históricos: `BLUEPRINT_SISTEMA_EPIC_V1.md`, `DOCUMENTACAO_TECNICA_EPIC_V1.md`, `CHECKLIST_MVP_IMPORTACAO_EPIC_V1.md` |

### 1.2 Autoridade documental por assunto

Não há precedência linear única. O canônico depende do assunto:

| Assunto | Documento canônico |
|---|---|
| Comportamento, produto, arquitetura-alvo, telas, fluxos, critérios de aceite | **Este Blueprint** |
| Fases, status, gates, ADRs vigentes, evidências, bloqueios abertos | **Roadmap V2** |
| Método de investigação e implementação no código/docs V2 | **`.cursor/rules` V2** (+ router global) |
| Histórico V1, checklist de evidências passadas, as-built | **Documentação V1** |
| Verdade em runtime durante execução | **Código real** (inspecionado) |

Em conflito **no mesmo assunto**: registrar a divergência no Roadmap e atualizar o documento canônico correspondente. Em conflito estrutural V1↔V2, prevalece este Blueprint + ADRs do Roadmap.

**Checklist V1 nunca é DoD da V2.**

**Não pertence a este Blueprint:** resultados de comandos, status de testes, evidências de execução, checkpoint Git, plano de move, changelog operacional detalhado (ficam no Roadmap).

### 1.3 Escopo deste documento

Cobertura §§2–17: visão, princípios, personas, mapa modular, modelo, fluxos, telas, regras, documentos, permissões, relatórios, NFR, releases, cenários, glossário, rastreabilidade.

---

## 2. Visão do produto

### 2.1 Problema

A Epic controla importações (Heroes / China / despachante BR) com planilhas, e-mails e conferência manual. Isso gera risco de custo final errado, perda de rastreabilidade, divergências entre fontes e dificuldade de fechamento auditável.

### 2.2 Contexto Epic / Heroes

| Elemento | Definição |
|---|---|
| Empresa | Epic (Brasil) |
| Parceira comercial | Heroes (Itália) — Ordine, Fattura, Packing List, etc. |
| Fabricação | China |
| Despacho | Despachante brasileiro (DUIMP, Numerário, etc.) |
| Operação do sistema | App web local em LAN; PostgreSQL local; sem Docker nesta fase |

### 2.3 Usuários

Admin, gestor, comprador, financeiro, logística/operador, (futuro) despachante/estoque com papéis restritos. Matriz detalhada na §4.

### 2.4 Objetivos

1. Visibilidade operacional e financeira do ciclo de importação.
2. Rastreabilidade documental de ponta a ponta.
3. Liquidação correta (scadenze, antecipos, alocações, câmbio).
4. Embarques e aduana modelados sem forçar a ordem como hub universal.
5. Landed cost versionado por SKU; conciliação e fechamento auditáveis.
6. Base modular manutenível (Alt. B — reconstrução seletiva).

### 2.5 Resultado esperado

Operadores enxergam filas de ação; financeiro liquida por obrigação (Payable); logística e aduana avançam com estados próprios; gestor fecha com trilha; dashboard deriva dos fluxos — não inventa dados.

### 2.6 Limites do sistema

Controle de importação **operacional e financeiro**, com estoque mínimo (entreposto/nacionalização), não ERP.

### 2.7 Fora de escopo

ERP completo; contabilidade/fiscal/WMS completos; integração bancária automática complexa; Portal Único; motor tributário sofisticado; multiempresa avançado; microservices; cloud/SaaS; Docker nesta fase; Next.js/Electron; Excel/Access/SQLite como base oficial; migração de dados V1→V2.

---

## 3. Princípios funcionais

### 3.1 Princípios de negócio (portáveis)

1. **Vazio não vira zero** — campo ausente → `null` / `pending_review`.
2. **Documento integra a evidência** — custo, desconto, imposto, pagamento e transição crítica exigem origem documental.
3. **Estados independentes** — cada agregado persiste só o seu ciclo; status cruzados são read models.
4. **Ordem não é contêiner universal** — Order, Shipment e ImportProcess/DUIMP são agregados distintos.
5. **Cockpit resume e direciona** — não reimplementa Billing, Logistics, Customs etc.
6. **Módulos possuem ownership** — dados e regras pertencem a um owner; outros consomem contratos.
7. **Movimentos são fonte do estoque** — `StockBalance` é derivado.
8. **Alterações críticas são auditadas** — soft-annul; reason codes; sem hard delete de oficial.
9. **Falhas são explícitas** — divergência vira fila/conciliação; nunca some.
10. **Dashboard deriva dos fluxos operacionais** — última fatia de UI; só leitura agregada.

### 3.2 Princípios de modularidade e manutenibilidade

1. **Monólito modular não significa só pastas separadas** — significa fronteiras de ownership e contratos.
2. Cada módulo possui **dados, regras e internals próprios**.
3. Integração entre módulos ocorre por **contratos públicos** (comandos, consultas, facades) — não por imports de internals.
4. Dependências são **direcionais e sem ciclos** (ex.: Orders ← Billing ← Treasury).
5. **Cockpit e Reporting são read models** — não agregadores que recriam domínios (`order_central` é anti-padrão).
6. **Routers/controllers e páginas são finos**.
7. Regras de negócio **não** ficam em HTTP, componentes React ou código de apresentação.
8. Evitar **god files, god services, god components** e arquivos genéricos sem ownership (`models.py` / `services.py` / `utils.py` / `api.ts` globais multi-domínio).
9. Preferir **coesão e responsabilidade única**.
10. **Não fragmentar artificialmente** só para cumprir métrica de linhas.

### 3.3 Gatilhos de revisão de tamanho (referência, não limite cego)

| Gatilho | Ação |
|---|---|
| Arquivo manual ≈ **400** linhas | Revisar se há mais de uma responsabilidade |
| Arquivo ≈ **600** linhas | Justificar explicitamente no PR/Roadmap **ou** decompor |
| Função/método ≈ **50–60** linhas | Revisar |
| Componente React ≈ **250–300** linhas | Revisar |
| Router com regra de negócio | **Corrigir** independente do tamanho |
| Service/classe com mais de um domínio | Decompor |

**Excluir destas métricas automáticas:** código gerado; migrations; fixtures; arquivos declarativos; schemas extensos justificáveis; testes parametrizados.

---

## 4. Personas e matriz de responsabilidades

> Lacuna **L-005 / F0-009**: matriz completa papéis × ações críticas ainda pendente de validação operacional Epic. Abaixo = intent V2 a partir do as-built V1 + visão de produto.

### 4.1 Admin

| Aspecto | Conteúdo |
|---|---|
| Objetivo | Operar Identity, backup/restore, configuração |
| Informações | Usuários, papéis, saúde do sistema, auditoria |
| Ações | CRUD usuários/papéis; restore; migrações controladas |
| Aprovações | Overrides excepcionais |
| Restrições | Não “corrigir” saldos manuais sem documento |
| Telas | Usuários e permissões; auditoria; health |

### 4.2 Gestor

| Aspecto | Conteúdo |
|---|---|
| Objetivo | Visão executiva; fechamento; destravar bloqueios |
| Informações | Filas, KPIs, divergências, landed cost, PnL |
| Ações | Fechar/reabrir; aprovar overrides; ver dashboard |
| Aprovações | Fechamento, reabertura, tolerâncias (quando L-001 destravar) |
| Restrições | Não liquidar pagamento sem papel financeiro |
| Telas | Dashboard; cockpit; conciliação; auditoria |

### 4.3 Comprador

| Aspecto | Conteúdo |
|---|---|
| Objetivo | Ordens, catálogo, ingestão Ordine/Heroes |
| Informações | Ordens, itens, fornecedores, SKUs, status comercial |
| Ações | Criar/editar ordem; triagem de ingestão; catálogo |
| Aprovações | Confirmar ordem (conforme política) |
| Restrições | Não alterar alocações de pagamento |
| Telas | Fila de ordens; nova ordem; produtos; fornecedores; ingestão |

### 4.4 Financeiro

| Aspecto | Conteúdo |
|---|---|
| Objetivo | Invoices, payables, pagamentos, FX, créditos |
| Informações | Saldos, scadenze, alocações, câmbio, PnL |
| Ações | Registrar invoice/payable/payment/allocation/FX/crédito/desconto |
| Aprovações | Compensação de antecipo; aplicação de crédito |
| Restrições | Não mudar qty embarcada/nacionalizada |
| Telas | Central financeira; AP; invoices; pagamentos; câmbio; créditos |

### 4.5 Logística / operador

| Aspecto | Conteúdo |
|---|---|
| Objetivo | Embarques, documentos de transporte, chegada |
| Informações | Shipments, packing list, modal, datas |
| Ações | Criar/atualizar shipment e itens; anexar docs |
| Aprovações | Troca de modal (com reason code) |
| Restrições | Não liquidar financeiro; não CLEARED (Customs) |
| Telas | Embarques; cockpit (aba logística); documentos |

### 4.6 Despachante / aduana (perfil operacional)

| Aspecto | Conteúdo |
|---|---|
| Objetivo | ImportProcess/DUIMP, impostos, nacionalização |
| Informações | Invoices vinculadas, numerário, taxes |
| Ações | Registrar processo; vincular invoices; nacionalizar parcial |
| Aprovações | Conforme permissão |
| Restrições | Não criar Payment |
| Telas | Processo aduaneiro; documentos; estoque/entreposto |

---

## 5. Mapa funcional do sistema

### 5.0 Template de módulo (campos obrigatórios)

Para cada módulo abaixo:

| Campo | Significado |
|---|---|
| Objetivo | Por que existe |
| Owner | Time/papel responsável pelo domínio |
| Entidades | Agregados/entidades que possui |
| Funcionalidades | Capacidades |
| Comandos principais | Escritas |
| Consultas | Leituras |
| Dependências permitidas | Módulos que pode consumir (contratos públicos) |
| Imports / deps proibidos | O que não pode |
| Proibições de negócio | Regras “nunca” |
| Alertas | Sinais operacionais |
| Entregas de UI | Telas/partes |
| **API pública** | Facade / exports estáveis |
| **Internals privados** | Pacotes/arquivos não importáveis por outros módulos |
| **Casos de uso** | Orquestrações de domínio |
| **Ownership de persistência** | Tabelas/ORM sob responsabilidade do módulo |
| **Responsabilidade de transação** | Onde a UoW inicia/commit |
| **Estrutura interna recomendada** | Proporcional ao tamanho — **sem camadas vazias obrigatórias** |
| **Critérios de decomposição** | Quando quebrar arquivos/pacotes |
| **Testes** | Unitários, integração, arquitetura |

Hipótese de pastas internas (`domain` / `application` / `infrastructure` / `api`): **opcional**. Preferir package-by-domain com estrutura mínima coerente; o agente pode propor outra organização **com justificativa**.

### 5.1 Foundation

| Campo | Conteúdo |
|---|---|
| Objetivo | Bootstrap do monólito modular: config, health, error handler, OpenAPI, Alembic baseline, wiring |
| Owner | Engenharia |
| Entidades | Nenhuma de domínio |
| Funcionalidades | App factory; middleware; geração OpenAPI; settings |
| Comandos | — |
| Consultas | `/health` |
| Deps permitidas | stdlib / framework |
| Proibido | Regra de negócio; **qualquer** import de `v1/**` |
| API pública | `create_app`, settings, error types compartilhados mínimos |
| Internals | wiring interno |
| Transação | Não possui domínio |
| UI | — |
| Testes | health; OpenAPI schema freeze; arch imports |

### 5.2 Identity

| Campo | Conteúdo |
|---|---|
| Objetivo | Usuários, autenticação, papéis, permissões |
| Owner | Admin |
| Entidades | User, Role, Session |
| Funcionalidades | Login/logout; CRUD usuários; RBAC |
| Comandos | create_user, assign_role, login, logout |
| Consultas | me, list_users |
| **Deps permitidas** | Nenhuma (módulo raiz de identidade) |
| Proibido | Importar Audit ou Documents; regras de Order/Payment |
| Orquestração | Camada de aplicação/Foundation grava Audit após ações Identity, passando `actor_id` opaco |
| UI | Login; usuários e permissões |
| Persistência | users, roles, sessions |
| Transação | Nos use cases de Identity |

### 5.3 Audit

| Campo | Conteúdo |
|---|---|
| Objetivo | Trilha imutável de ações críticas e mudanças |
| Owner | Engenharia / Gestor |
| Entidades | AuditLog, (opcional) TechnicalLog |
| Funcionalidades | append-only; consulta por entidade/ator |
| Comandos | record_event(actor_id, …) |
| Consultas | history_by_entity |
| **Deps permitidas** | Nenhuma |
| Proibido | Depender de Identity; update/delete de eventos; resolver usuário internamente |
| Contrato | `actor_id` é identificador **opaco** (UUID/string); Audit não importa User/ORM de Identity |
| UI | Auditoria |
| Persistência | audit_log |

### 5.4 Documents

| Campo | Conteúdo |
|---|---|
| Objetivo | Anexos imutáveis, hash, versão, `document_links` |
| Owner | Operação transversal |
| Entidades | Document, DocumentVersion, DocumentLink |
| Funcionalidades | upload; supersede; link a entidade; download |
| Comandos | store_document(actor_id, …), link_document, supersede |
| Consultas | list_by_entity |
| **Deps permitidas** | Nenhuma |
| Proibido | Depender de Identity; mutar bytes após commit; apagar oficial sem supersede; conhecer regras de Billing |
| Contrato | Ator/contexto entram pela **API pública** (parâmetros); Documents não importa Identity |
| UI | Documentos; anexos nas telas de domínio |
| Persistência | documents, document_links; arquivos em pasta controlada |

### 5.5 Catalog

| Campo | Conteúdo |
|---|---|
| Objetivo | Fornecedores e produtos/SKUs |
| Owner | Comprador |
| Entidades | Supplier, Product (SKU), atributos (size/color etc.) |
| Funcionalidades | CRUD mestre; busca; (import CSV controlado) |
| Comandos | upsert_product, upsert_supplier |
| Consultas | search_products |
| **Deps permitidas** | Documents, Audit |
| Proibido | Quantidades de ordem/estoque aqui |
| UI | Produtos; fornecedores |
| Lacuna | L-006 campos SKU exatos |

### 5.6 Orders

| Campo | Conteúdo |
|---|---|
| Objetivo | Pedido comercial e itens |
| Owner | Comprador |
| Entidades | Order, OrderItem, termos comerciais |
| Funcionalidades | Criar/confirmar/cancelar/fechar ordem; itens |
| Comandos | create_order, confirm_order, add_item, close_order |
| Consultas | order_summary (comercial); fila |
| **Deps permitidas** | Catalog, Documents, Audit |
| **Proibido depender de** | Billing, Treasury, Logistics, Customs, Costing, Identity (ator via API/app) |
| Proibições | Persistir PARTIALLY_SHIPPED/SHIPPED na Order |
| Alertas | Ordem sem itens; confirmada sem documento |
| UI | Fila; nova ordem; cockpit (resumo comercial) |
| Persistência | orders, order_items |
| Transação | Use cases de Orders |

### 5.7 Billing

| Campo | Conteúdo |
|---|---|
| Objetivo | Proforma/Invoice/Acconto documental, scadenze → Payables |
| Owner | Financeiro |
| Entidades | Invoice, InvoiceItem, PaymentTerms, Payable |
| Tipos documentais de Invoice | **Implementados (Inc-2):** `PROFORMA` \| `FINAL`. **Alvo de produto:** `PROFORMA` \| `ACCONTO` \| `FINAL` — ver **DEC-ACCONTO-INVOICE** (pendente) |
| Funcionalidades | Emitir invoice; gerar N payables; cancelar DRAFT |
| Comandos | create_invoice, update_*, set_terms, issue_invoice, cancel_draft |
| Consultas | invoice_balance (= Σ payable balances); payables_queue |
| **Deps permitidas** | Orders, Catalog, Documents, Audit |
| **Proibido** | Treasury, Logistics, Customs |
| Proibições | Liquidar sem Payable; criar Payment a partir da emissão da Invoice; cancelar ISSUED no Inc-2 (SC-08); misturar terms %/valor |
| UI | Invoices; Payables; formulário scadenze |
| Persistência | invoices, invoice_items, payment_terms, payables |
| Inc-2 | ISSUED imutável; doc obrigatório na emissão (ou override auditado); supplier/moeda da Order; tipos persistidos só `FINAL`\|`PROFORMA` |
| Inc-3 saldo | `Payable.amount` original imutável; `balance` só via `billing.public.apply_payable_allocations`; `allocated=amount−balance` derivado; status `OPEN\|PARTIALLY_PAID\|PAID\|CANCELLED`; Invoice balance = Σ balances |

**Invoice ACCONTO vs Payment antecipado `[DECISÃO / princípio]`:**

| Conceito | Módulo | Papel |
|---|---|---|
| Invoice `ACCONTO` (se/quando tipada) | **Billing** | Documento de cobrança/formalização do adiantamento; **pode** gerar Payable via scadenze; **não** comprova pagamento |
| Payment antecipado (acconto pago) | **Treasury** | Dinheiro efetivamente pago (comprovante); pode ficar **sem** allocation; só reduz saldo ao alocar em Payable |

Criar/emitir Invoice (qualquer tipo) **não** cria Payment. Payment só existe com evidência financeira em Treasury. A operação **admite** Payment antecipado sem Invoice de acconto (SC-04 / §7.4).

**DEC-ACCONTO-INVOICE `[PENDENTE]`:** tipar `ACCONTO` como `invoice_type` em Billing. Evidência 2026-07-22: fixture `Fattura_181-con acconti.pdf` é **FATTURA** com cláusula *BONIFICO ANTICIPATO 50%* + scadenze — **não** é documento intitulado *Fattura di acconto*. V1 tinha `invoice_type=ANTECIPO` (legado); Heroes XLSX `acconto_amount` mapeia a **pagamentos**, não a tipo de fatura. Formalizar `ACCONTO` no código/migration só após exemplar documental claro ou confirmação de negócio.

### 5.8 Treasury

| Campo | Conteúdo |
|---|---|
| Objetivo | Pagamentos, alocações, FX (três visões), créditos, descontos, conta corrente BR |
| Owner | Financeiro |
| Entidades | Payment, PaymentAllocation, **FxPlanRate**, **FxMarketQuote**, **FxExecution**, **FxExecutionAllocation**, **FxAllocationValuation**; Credit/Discount/CC BR (futuro) |
| Funcionalidades | Registrar pagamento; alocar em Payable; FX projetado/online/realizado |
| Comandos | register_payment, allocate; register_plan_rate; register_execution; link execution↔allocation; refresh_quote |
| Consultas | unallocated_payments; payable/payment fx-view (benchmarks nomeados) |
| **Deps permitidas** | Billing, Documents, Audit |
| **Proibido** | Orders direto; Logistics; Customs |
| Proibições | Allocation → Invoice sem Payable; Expense como entidade Treasury; cotação online como versão de taxa projetada |
| Lacuna | L-003 política conta corrente BR |
| UI | Pagamentos; painel FX três visões; créditos/descontos (futuro) |
| Persistência | payments, payment_allocations, fx_* |
| Inc-4 FX | Ownership **só Treasury**; plan→Payable; quote→par; execution→Payment 1:N; N:M via FxExecutionAllocation; PnL histórico em valuation; Billing ↛ Treasury |

**Três visões FX `[DECISÃO]`:**

| Visão | Fonte | Notas |
|---|---|---|
| Projetada | `FxPlanRate` INITIAL/REFORECAST/CORRECTION | 1 current por Payable |
| Online | `FxMarketQuote` (par) | fresh/stale/missing; null≠0; provider abstrato |
| Realizada | `FxExecution` + links + valuation | snapshots não mudam com reforecast |

Convenção: `rate` = BRL por 1 foreign. Positivo = favorável.

### 5.9 Ingestion

| Campo | Conteúdo |
|---|---|
| Objetivo | Pipeline bruto → adapter → staging → revisão → commit idempotente |
| Owner | Comprador / operação |
| Entidades | IngestionBatch, StagingRow, AdapterResult |
| Funcionalidades | Identificar tipo; hash; staging; triage; commit |
| Comandos | ingest_file, approve_staging, commit_batch |
| Consultas | staging_queue |
| **Deps permitidas** | Documents, Audit, Catalog, Orders, Billing, Logistics, Customs (APIs públicas) |
| Proibido | Escrever direto em tabelas oficiais sem commit; **qualquer** import V1 |
| UI | Ingestão e revisão |
| Nota | Parser Heroes = lógica portada/reimplementada em V2; golden de caracterização sem import V1 |

### 5.10 Logistics

| Campo | Conteúdo |
|---|---|
| Objetivo | Embarques e itens embarcados |
| Owner | Logística |
| Entidades | Shipment, ShipmentItem |
| Funcionalidades | Planejar/booking/trânsito/chegada; parcial; multi-embarque |
| Comandos | create_shipment, add_shipment_item, advance_shipment_status |
| Consultas | shipped_qty_by_order_item; allocation_bases (peso/volume/qty) |
| **Deps permitidas** | Orders, Documents, Audit |
| **Proibido** | Billing, Treasury, Costing; `order_id` no Shipment |
| Proibições | Persistir CLEARED no Shipment |
| UI | Embarques; cockpit logística |

### 5.11 Customs

| Campo | Conteúdo |
|---|---|
| Objetivo | ImportProcess/DUIMP, taxes, nacionalização |
| Owner | Aduana / despachante |
| Entidades | ImportProcess, CustomsDocument, Tax, Nationalization |
| Funcionalidades | 1 DUIMP → N invoices; nacionalização parcial |
| Comandos | create_import_process, link_invoice, register_tax, nationalize |
| Consultas | process_by_invoice |
| **Deps permitidas** | Billing, Logistics, Documents, Audit |
| **Proibido** | Treasury |
| Pendências | DEC-DUIMP-MULTI-SHIP; L-007 DI vs DUIMP |
| UI | Processo aduaneiro / DUIMP |

### 5.12 Inventory

| Campo | Conteúdo |
|---|---|
| Objetivo | Movimentos e entreposto; saldo derivado |
| Owner | Estoque / operação |
| Entidades | InventoryMovement, EntrepostoMovement; StockBalance (read model) |
| Funcionalidades | Entrada; consumo; consulta saldo |
| Comandos | record_movement |
| Consultas | stock_balance |
| **Deps permitidas** | Customs, Catalog, Documents, Audit |
| **Proibido** | Billing, Treasury, Orders (qty operacional vem de Customs/Catalog, não do pedido) |
| Proibições | Saldo “editável” |
| UI | Estoque / entreposto |
| Justificativa | Catalog identifica SKU; Customs dispara nacionalização; Orders não é fonte de estoque |

### 5.13 Costing

| Campo | Conteúdo |
|---|---|
| Objetivo | Expenses + landed cost versionado por SKU |
| Owner | Financeiro / gestor |
| Entidades | Expense, LandedCostVersion, components |
| Funcionalidades | Registrar despesa; ratear; versões estimado/revisado/realizado |
| Comandos | add_expense, compute_landed_cost, publish_version |
| Consultas | landed_cost_by_sku |
| **Deps permitidas** | Orders, Billing, Customs, Logistics, Treasury, Documents, Audit |
| **Proibido** | Reporting (escrita); ser dono de FX (só **lê** taxas públicas de Treasury) |
| UI | Landed cost |
| Justificativa | Logistics → bases de rateio (peso/volume/qty embarcada); Treasury → FX para conversão; Expense permanece em Costing |

### 5.14 Reconciliation

| Campo | Conteúdo |
|---|---|
| Objetivo | Pares de conciliação; divergências; filas |
| Owner | Financeiro / gestor |
| Entidades | ReconciliationCase, ReconciliationPair |
| Funcionalidades | Abrir caso; resolver; bloquear fechamento se aberto |
| Comandos | open_case, resolve_case |
| Consultas | open_divergences |
| **Deps permitidas** | Leitura das APIs públicas de Orders, Billing, Treasury, Logistics, Customs, Costing, Inventory; Documents; Audit |
| Proibido | Escrever entidades de domínio alheias |
| Lacuna | **L-001** tolerâncias — não inventar política definitiva |
| UI | Conciliação |

### 5.15 Reporting

| Campo | Conteúdo |
|---|---|
| Objetivo | Read models, dashboard, exportações |
| Owner | Gestor |
| Entidades | Projeções / materializações de leitura |
| Funcionalidades | KPIs; filas; exports |
| Comandos | — (não escreve domínio) |
| Consultas | dashboard, queues |
| **Deps permitidas** | Leitura das APIs públicas dos módulos de domínio |
| Proibido | Escrever em tabelas de domínio |
| UI | Dashboard (fase tardia) |

### 5.16 Grafo canônico de dependências

**Semântica única:** `A --> B` significa que **A pode depender da API pública de B**.  
A não importa internals de B. O grafo é **acíclico** e é a base do teste arquitetural.

#### Plataforma (sem ciclos)

| Aresta | Motivo |
|---|---|
| Identity sem deps | Raiz de autenticação |
| Audit sem deps | `actor_id` opaco |
| Documents sem deps | ator/contexto por parâmetro de API |
| Módulos → Audit / Documents | Facades públicas; Identity **não** depende deles |

Orquestração Identity→Audit: **Foundation/application** chama `Audit.record` após o use case de Identity — não há aresta Identity→Audit no grafo de pacotes (evita acoplamento e ciclo potencial).

#### Domínio

```mermaid
flowchart LR
  Catalog --> Documents
  Catalog --> Audit
  Orders --> Catalog
  Orders --> Documents
  Orders --> Audit
  Billing --> Orders
  Billing --> Catalog
  Billing --> Documents
  Billing --> Audit
  Treasury --> Billing
  Treasury --> Documents
  Treasury --> Audit
  Logistics --> Orders
  Logistics --> Documents
  Logistics --> Audit
  Customs --> Billing
  Customs --> Logistics
  Customs --> Documents
  Customs --> Audit
  Inventory --> Customs
  Inventory --> Catalog
  Inventory --> Documents
  Inventory --> Audit
  Costing --> Orders
  Costing --> Billing
  Costing --> Customs
  Costing --> Logistics
  Costing --> Treasury
  Costing --> Documents
  Costing --> Audit
  Ingestion --> Catalog
  Ingestion --> Orders
  Ingestion --> Billing
  Ingestion --> Logistics
  Ingestion --> Customs
  Ingestion --> Documents
  Ingestion --> Audit
  Reporting --> Orders
  Reporting --> Billing
  Reporting --> Treasury
  Reporting --> Logistics
  Reporting --> Customs
  Reporting --> Inventory
  Reporting --> Costing
```

Reconciliation (omitido no diagrama por densidade): mesmas leituras que Reporting + Documents + Audit; **sem escrita** em domínio alheio.

**Proibido no grafo:** qualquer aresta inversa às listadas; ciclos; V2→V1.

## 6. Modelo operacional

### 6.1 Entidades e significados

| Entidade | Significado | Owner |
|---|---|---|
| Order / OrderItem | Pedido comercial e linhas | Orders |
| Invoice / InvoiceItem / Payable | Fatura e obrigações por scadenza | Billing |
| Payment / PaymentAllocation | Dinheiro e liquidação de Payable | Treasury |
| Fx* | Câmbio previsto/contratado/realizado | Treasury |
| Credit / Discount | Crédito e desconto documentados | Treasury |
| Shipment / ShipmentItem | Embarque físico ligado a OrderItem | Logistics |
| ImportProcess | Processo aduaneiro (DUIMP etc.) | Customs |
| Tax / Nationalization | Tributos e nacionalização | Customs |
| Expense / LandedCostVersion | Custo e rateio | Costing |
| InventoryMovement | Movimento de estoque | Inventory |
| StockBalance | Saldo **derivado** | Inventory (read) |
| Document / DocumentLink | Evidência imutável | Documents |

### 6.2 Cardinalidades canônicas

- Order **1:N** Invoice  
- Invoice **1:N** Payable (scadenze / payment terms)  
- Payment **N:M** Payable via PaymentAllocation  
- OrderItem **N:M** Shipment via ShipmentItem (**Shipment sem `order_id`**)  
- ImportProcess **1:N** Invoice (`invoice_id` UNIQUE no join)  
- Document **N:M** entidades via DocumentLink  

### 6.3 Unidade de liquidação

**Payable.** `PaymentAllocation` liquida somente Payable. Saldo da Invoice = Σ saldos dos Payables. Antecipo **não alocado** não reduz saldo.

### 6.4 Estados persistidos vs derivados

| Agregado | Persistidos | Não persistir (derivado / outro agregado) |
|---|---|---|
| Order | DRAFT → CONFIRMED → CLOSED / CANCELLED | PARTIALLY_SHIPPED, SHIPPED, PAID… |
| Shipment | PLANNED → BOOKED → IN_TRANSIT → ARRIVED | CLEARED |
| ImportProcess | … → CLEARED | — |
| Invoice / Payable / Payment | conforme máquina do domínio | “status global da importação” |
| Reconciliation / Closure | estados próprios | — |

### 6.5 Documentos, valores, versionamento, rastreabilidade

- Documentos imutáveis; substituição = nova versão + supersede + histórico.  
- Valores oficiais têm origem documental.  
- Landed cost e FX versionados (planejado / revisado / realizado).  
- AuditLog + reason codes em exceções, cancelamentos, reaberturas, overrides.

### 6.6 Decisões abertas (não inventar)

| ID | Tema |
|---|---|
| L-001 | Tolerâncias de conciliação |
| L-003 | Conta corrente BR / impacto fiscal |
| DEC-DUIMP-MULTI-SHIP | Relação DUIMP × múltiplos shipments |
| DEC-ENDERECO | Modelo de endereços |

**DEC-SCONTO-ITEM `[DECISÃO]` (fechada 2026-07-22):** Sconto comercial de linha ∈ **InvoiceItem** (não OrderItem). Representação: `discount_type` ∈ {`NONE`,`UNIT_AMOUNT`,`PERCENT`} com xor de `discount_unit_amount` / `discount_percent`. Fattura_202 tem coluna `% Sc` (vazia neste exemplar); Heroes/V1 usam valor unitário — modelo dual evita perda na ingestão. Payable e Costing futuro usam **líquido**. Desconto global/documental (Treasury) fora do slice Order-to-Pay Billing; proibida dupla aplicação. Arredondamento comercial: `ROUND_HALF_UP` **2 casas**; residual de scadenze % na última parcela.

---

## 7. Fluxos ponta a ponta

Cada fluxo: pré-condições → passos → regras → exceções → resultado. Sem status de execução.

### 7.1 Criação manual de ordem

- **Pré:** usuário comprador autenticado; supplier/SKU existentes ou criáveis.  
- **Passos:** nova ordem → itens → termos → DRAFT → confirmar.  
- **Regras:** vazio ≠ zero; confirmação auditada.  
- **Exceção:** SKU incompleto → pending_review.  
- **Resultado:** Order CONFIRMED.

### 7.2 Importação de Ordine

- **Pré:** PDF/arquivo Ordine; Documents disponível.  
- **Passos:** ingest → adapter → staging → revisão → commit Orders (+ Catalog se necessário).  
- **Regras:** hash imutável; commit idempotente.  
- **Exceção:** conflito de identificador → fila.  
- **Resultado:** Order oficial + documento linkado.

### 7.3 Invoice com múltiplas scadenze

- **Pré:** Order; documento Fattura.  
- **Passos:** Invoice → PaymentTerms → N Payables.  
- **Regras:** saldo Invoice = Σ Payables.  
- **Resultado:** obrigações distintas por vencimento.

### 7.4 Antecipo não alocado e compensação posterior

- **Pré:** Payment antecipado em Treasury (evidência financeira); Payable(s) existentes (de Invoice FINAL/PROFORMA/ACCONTO conforme tipagem).  
- **Passos:** registrar Payment **sem** allocation → depois allocate em Payable(s).  
- **Regras:** sem allocation, saldo Payable/Invoice **não** cai; sem dupla contagem; Invoice ACCONTO (se existir) **não** substitui nem cria o Payment.  
- **Resultado:** saldo correto pós-alocação.

### 7.5 Pagamento parcial

- **Pré:** Payable aberto.  
- **Passos:** Payment + Allocation parcial.  
- **Regras:** saldo residual explícito.  
- **Resultado:** Payable parcialmente liquidado.

### 7.6 Crédito aplicado em obrigação diferente

- **Pré:** Credit com origem documental (invoice/order A).  
- **Passos:** apply_credit em Payable B.  
- **Regras:** origem ≠ uso permitido e auditado; ≠ desconto ≠ conta corrente BR (L-003).  
- **Resultado:** B liquidado parcialmente/total via crédito.

### 7.7 Embarque parcial

- **Pré:** OrderItem com qty.  
- **Passos:** Shipment + ShipmentItem com qty &lt; pedida.  
- **Regras:** qty embarcada derivada; Order não muda para SHIPPED.  
- **Resultado:** residual a embarcar visível.

### 7.8 Item em múltiplos embarques

- **Pré:** mesmo OrderItem.  
- **Passos:** N ShipmentItems somando ≤ qty permitida.  
- **Regras:** sem `order_id` no Shipment; vínculo só via item.  
- **Resultado:** rastreio por embarque.

### 7.9 DUIMP com múltiplas invoices

- **Pré:** Numerário / docs; N invoices.  
- **Passos:** ImportProcess linka N invoices (1:N).  
- **Regras:** não subordinar DUIMP a uma única Order como contêiner.  
- **Resultado:** processo aduaneiro coerente com fixture Numerário.

### 7.10 Nacionalização parcial

- **Pré:** ImportProcess; qty embarcada/disponível.  
- **Passos:** nationalize qty parcial.  
- **Regras:** residual explícito; movimentos de inventário.  
- **Resultado:** qty nacionalizada &lt; total.

### 7.11 Entrada e consumo em entreposto

- **Pré:** política de entreposto aplicável.  
- **Passos:** movimento entrada → consumo; saldo derivado.  
- **Regras:** não editar StockBalance.  
- **Resultado:** saldo = Σ movimentos.

### 7.12 Landed cost por SKU

- **Pré:** Expenses + Taxes + itens.  
- **Passos:** rateio → LandedCostVersion.  
- **Regras:** versões estimado/revisado/realizado; Expense em Costing.  
- **Resultado:** custo por SKU auditável.

### 7.13 Retificação de invoice

- **Pré:** Invoice oficial.  
- **Passos:** nova versão / retificação; payables recalculados conforme regra; histórico.  
- **Regras:** não hard-delete; impacto em alocações → conciliação se divergir.  
- **Resultado:** versão atual + histórico.

### 7.14 Substituição de documento

- **Pré:** Document linkado.  
- **Passos:** upload nova versão → supersede → links atualizam versão atual.  
- **Regras:** bytes antigos preservados.  
- **Resultado:** trilha completa.

### 7.15 Conciliação

- **Pré:** par com diferença.  
- **Passos:** abrir caso → analisar → resolver ou manter aberto.  
- **Regras:** L-001 — tolerâncias provisórias isoladas; sem sumir divergência.  
- **Resultado:** caso resolvido ou bloqueio de fechamento.

### 7.16 Fechamento e reabertura

- **Pré:** permissões; sem divergências bloqueantes.  
- **Passos:** close snapshot → reopen com reason + permissão.  
- **Regras:** reabertura auditada; não edição silenciosa.  
- **Resultado:** CLOSED ou REOPENED controlado.

---

## 8. Arquitetura funcional das telas

Convenção: cada tela documenta propósito, usuário, header, KPIs, filtros, agrupamentos, tabela/colunas, ações, inline edit, drill-down, alertas, empty, permissões e aceite.
UI une Billing+Treasury na “Central financeira”, mas **ownership** permanece nos módulos. Cockpit é **read model** — não recria domínios.

### 8.1 Login

| Campo | Conteúdo |
|---|---|
| Propósito | Autenticar usuário |
| Usuário | Todos |
| Header | Marca Epic; sem nav autenticada |
| KPIs / filtros / tabela | — |
| Ações | Login; logout após sessão |
| Inline / drill | — |
| Alertas / empty | Credencial inválida explícita |
| Permissões | Público (não autenticado) |
| Aceite | Cookie httpOnly; sessão registrada; falha sem vazar detalhes internos |

### 8.2 Dashboard

| Campo | Conteúdo |
|---|---|
| Propósito | Visão executiva e filas derivadas dos fluxos |
| Usuário | Gestor (e perfis com leitura) |
| Header | Período; atalhos para filas críticas |
| KPIs | Exposição FX; total a pagar; ordens com pendência; shipments em trânsito; divergências abertas; unallocated |
| Filtros | Período; fornecedor; responsável |
| Agrupamentos | Por domínio (financeiro / logística / aduana / ingestão) |
| Tabela | Top N itens por fila (ordem, payable, shipment, caso) |
| Ações | Navegar para fila/cockpit; export resumido |
| Inline | Não |
| Drill-down | Widget → fila ou entidade |
| Alertas | Filas acima de limiar; casos L-001 |
| Empty | “Sem pendências no período” |
| Permissões | reporting:read |
| Aceite | Somente leitura; dados de Reporting; **última** fatia de UI; não grava domínio |

### 8.3 Fila de ordens

| Campo | Conteúdo |
|---|---|
| Propósito | Trabalhar ordens comerciais e enxergar saúde financeira/logística **derivada** |
| Usuário | Comprador; gestor |
| Header | Título; CTA Nova ordem; busca rápida |
| KPIs | Abertas; confirmadas; com saldo; com qty a despachar; com pendências |
| Filtros | Status comercial; ano; fornecedor; responsável; pendência; faixa de saldo |
| Agrupamentos | Opcional por fornecedor ou ano |
| **Colunas** | Ordem; ano; fornecedor; status comercial; valor faturado; pago; saldo; próximo vencimento; qtd a despachar; crédito; pendências; responsável; última atualização |
| Ações | Abrir cockpit; nova ordem; export |
| Inline | Não (valores financeiros são read models) |
| Drill-down | Linha → cockpit; saldo → AP filtrado; vencimento → payable |
| Alertas | Doc faltante; unallocated ligado; divergência; atraso de scadenza |
| Empty | “Nenhuma ordem — criar ou importar Ordine” |
| Permissões | orders:read; orders:write para criar |
| Aceite | Status comercial só Order; shipping/aduana como badges derivados; sem `order_central` |

### 8.4 Cockpit da ordem

| Campo | Conteúdo |
|---|---|
| Propósito | Resumir e direcionar: comercial + links aos domínios |
| Usuário | Comprador; financeiro; logística; gestor |
| Header | Código ordem; fornecedor; status comercial; ações contextuais |
| KPIs | Pedido; faturado; pago; saldo; embarcado; nacionalizado; LC versão atual |
| Filtros | — (contexto = uma ordem) |
| Agrupamentos | Seções: Comercial; Financeiro; Logística; Aduana; Documentos; Auditoria |
| Tabelas | Itens; invoices/payables (resumo); shipments; processos; anexos |
| Ações | Confirmar/cancelar/fechar (Orders); atalhos “ir para” Invoice/Shipment/DUIMP/Ingestão |
| Inline | Campos comerciais permitidos em DRAFT; demais via módulos |
| Drill-down | Cada linha → tela dona do agregado |
| Alertas | Pendências por seção; bloqueios de fechamento |
| Empty | Seção sem dados com CTA do módulo dono |
| Permissões | Leitura ampla; escritas por permissão do módulo |
| Aceite | Zero mega-aggregator; só consume APIs públicas / read models |

### 8.5 Nova ordem

| Campo | Conteúdo |
|---|---|
| Propósito | Criar Order + itens manualmente |
| Usuário | Comprador |
| Header | Formulário; salvar rascunho |
| KPIs | Total estimado itens (null se preço vazio) |
| Filtros | Busca SKU/supplier |
| Agrupamentos | Cabeçalho vs linhas |
| Tabela | SKU; descrição; qty; preço; moeda; NCM (se houver) |
| Ações | Salvar DRAFT; confirmar; cancelar |
| Inline | Sim nas linhas (qty/preço) com validação |
| Drill-down | SKU → ficha Catalog |
| Alertas | SKU incompleto → pending_review; vazio ≠ zero |
| Empty | Grade vazia com “adicionar item” |
| Permissões | orders:write |
| Aceite | DRAFT→CONFIRMED auditada; sem criar Invoice automaticamente |

### 8.6 Produtos / 8.7 Fornecedores

Cadastro mestre Catalog. Header com busca; tabela de atributos; ações CRUD; inline controlado; sem qty operacional; permissões catalog:\*; aceite L-006 consciente.

### 8.8 Central financeira

| Campo | Conteúdo |
|---|---|
| Propósito | Hub UI Billing+Treasury: obrigações, caixa e FX |
| Usuário | Financeiro; gestor |
| Header | Atalhos AP / Invoices / Pagamentos / FX / Créditos |
| KPIs | A pagar; vencido; unallocated; crédito disponível; PnL período |
| Filtros | Período; fornecedor; moeda; status liquidação |
| Agrupamentos | Por semana de vencimento ou fornecedor |
| Tabela | Resumo de payables + pagamentos recentes |
| Ações | Ir para filas; registrar pagamento (atalho) |
| Inline | Não |
| Drill-down | KPI → fila filtrada |
| Alertas | Unallocated; atraso; comprovante faltando |
| Empty | “Sem obrigações no filtro” |
| Permissões | billing:read; treasury:read/write conforme ação |
| Aceite | Não é dono de Expense (Costing); não liquida sem Payable |

### 8.9 Fila de contas a pagar

| Campo | Conteúdo |
|---|---|
| Propósito | Trabalhar Payables (unidade de liquidação) |
| Usuário | Financeiro |
| Header | Filtros rápidos: hoje / 7d / vencidos / unallocated |
| KPIs | Vencido; a vencer 7d; saldo total; qtd sem comprovante |
| Filtros | Vencimento; fornecedor; invoice; ordem; tipo; moeda; aprovação |
| Agrupamentos | Por vencimento ou fornecedor |
| **Colunas** | Vencimento; atraso; fornecedor; invoice; ordem; tipo; moeda; valor; alocado; saldo; FX previsto; BRL previsto; comprovante; aprovação; pendências; ações rápidas |
| Ações | Alocar; registrar pagamento; anexar comprovante; abrir invoice/ordem |
| Inline | Não para saldos; observação/pendência se permitido |
| Drill-down | Invoice; ordem; payment |
| Alertas | Atraso; saldo≠0 com payment unallocated; L-001 |
| Empty | “Nada a pagar no filtro” |
| Permissões | treasury:allocate; billing:read |
| Aceite | Linha = Payable; antecipo sem allocation não zera saldo |

### 8.10 Invoices

| Campo | Conteúdo |
|---|---|
| Propósito | Gerir invoices/proformas e scadenze |
| Usuário | Financeiro; comprador (leitura) |
| Header | Nova invoice; filtro tipo (**Proforma** / **Acconto** / **Final**) — Acconto reservado até DEC-ACCONTO-INVOICE |
| KPIs | Abertas; retificadas; saldo agregado |
| Filtros | Ordem; fornecedor; tipo; período |
| Agrupamentos | Por ordem |
| Colunas | Número; tipo; ordem; data; moeda; total; saldo; #payables; status; doc |
| Ações | Criar; retificar; gerar payables; anexar; abrir |
| Inline | Não em totais oficiais |
| Drill-down | Payables da invoice; itens; documento |
| Alertas | Sem payable; retificação pendente; doc ausente |
| Empty | CTA criar ou ingerir Fattura |
| Permissões | billing:\* |
| Aceite | N payables por scadenze; retificação versionada |

### 8.11 Pagamentos e alocações

| Campo | Conteúdo |
|---|---|
| Propósito | Registrar Payments e PaymentAllocations |
| Usuário | Financeiro |
| Header | Novo pagamento; toggle “somente unallocated” |
| KPIs | Unallocated total; alocado no período |
| Filtros | Período; moeda; fornecedor; status alocação |
| Agrupamentos | Por payment |
| Colunas | Data; valor; moeda; alocado; residual; FX; comprovante; refs |
| Ações | Registrar; alocar em Payable(s); compensar antecipo |
| Inline | Valor de allocation com validação ≤ residual |
| Drill-down | Payable; invoice |
| Alertas | Residual unallocated; dupla contagem bloqueada |
| Empty | “Sem pagamentos” |
| Permissões | treasury:write |
| Aceite | Allocation só → Payable; SC-04 |

### 8.12 Câmbio / PnL

| Campo | Conteúdo |
|---|---|
| Propósito | Taxas previstas/contratadas/realizadas e PnL |
| Usuário | Financeiro; gestor |
| Header | Período; moeda par |
| KPIs | PnL realizado; exposição; taxa média |
| Filtros | Período; payment |
| Agrupamentos | Por payment / mês |
| Colunas | Ref; previsto; contratado; realizado; delta; BRL |
| Ações | Registrar taxa versionada; export |
| Inline | Não sobrescrever histórico — nova versão |
| Drill-down | Payment |
| Alertas | Sem taxa realizada em payment liquidado |
| Empty | “Sem movimentos FX” |
| Permissões | treasury:fx |
| Aceite | Versionamento; Costing apenas **lê** taxas |

### 8.13 Créditos e descontos

Lista origem/uso; ações apply_credit; distinção desconto≠crédito≠CC BR (L-003); aceite audit+documento.

### 8.14 Ingestão e revisão

| Campo | Conteúdo |
|---|---|
| Propósito | Staging → revisão → commit idempotente |
| Usuário | Comprador; operação |
| Header | Upload; fila staging |
| KPIs | Pendentes; conflitos; commitados |
| Filtros | Tipo doc; status staging; batch |
| Agrupamentos | Por batch / tipo |
| Colunas | Arquivo; tipo; hash; status; conflitos; destino módulo |
| Ações | Upload; aprovar; rejeitar; commit; abrir diff |
| Inline | Correção de campos staging permitidos |
| Drill-down | Linha staging → preview; após commit → entidade |
| Alertas | Conflito de identificador; parse incompleto |
| Empty | “Envie Ordine/Fattura/…” |
| Permissões | ingestion:\* |
| Aceite | Raw imutável; commit idempotente; sem import V1 |

### 8.15 Embarques

| Campo | Conteúdo |
|---|---|
| Propósito | Shipments e itens (parcial / multi) |
| Usuário | Logística |
| Header | Novo embarque; filtro modal/status |
| KPIs | Em trânsito; chegados; qty parcial |
| Filtros | Status; modal; período; SKU; ordem (via item) |
| Agrupamentos | Por status |
| Colunas | Código; modal; status; origem/destino; datas; #itens; docs |
| Ações | Criar; avançar status; add item; anexar BL/AWB/PL |
| Inline | Datas/booking com validação |
| Drill-down | Itens → OrderItem; docs |
| Alertas | Qty > residual; doc faltante |
| Empty | CTA criar shipment |
| Permissões | logistics:\* |
| Aceite | Sem `order_id` no header; vínculo só ShipmentItem |

### 8.16 Processo aduaneiro / DUIMP

| Campo | Conteúdo |
|---|---|
| Propósito | ImportProcess; invoices 1:N; taxes; nacionalização |
| Usuário | Aduana / despachante; gestor |
| Header | Novo processo; busca DUIMP |
| KPIs | Em andamento; cleared; nacionalização parcial |
| Filtros | Status; período; invoice |
| Colunas | Ref DUIMP; status; #invoices; taxes; qty nac.; docs |
| Ações | Criar; link invoices; registrar tax; nacionalizar parcial |
| Inline | Não em taxes oficiais sem doc |
| Drill-down | Invoice; nationalization → Inventory |
| Alertas | Invoice sem link; Numerário incompleto |
| Empty | CTA + fixture Numerário na ingestão |
| Permissões | customs:\* |
| Aceite | 1 DUIMP → N invoices; SC-07 |

### 8.17 Estoque / entreposto

| Campo | Conteúdo |
|---|---|
| Propósito | Movimentos e saldo derivado |
| Usuário | Estoque; operação |
| Header | Filtro SKU/local |
| KPIs | Saldo total; entradas; consumos |
| Filtros | SKU; tipo movimento; período |
| Agrupamentos | Por SKU |
| Colunas | Data; tipo; SKU; qty; ref Customs; saldo após (derivado) |
| Ações | Registrar movimento (se manual permitido); ver saldo |
| Inline | Não no saldo |
| Drill-down | Movimento → nationalization/doc |
| Alertas | Consumo > saldo |
| Empty | “Sem movimentos” |
| Permissões | inventory:\* |
| Aceite | StockBalance read-only; Inventory→Catalog+Customs |

### 8.18 Landed cost

| Campo | Conteúdo |
|---|---|
| Propósito | Expenses + versões LC por SKU |
| Usuário | Financeiro; gestor |
| Header | Seleção ordem/processo; versão |
| KPIs | Estimado; revisado; realizado; delta |
| Filtros | Versão; SKU; componente |
| Agrupamentos | Por SKU |
| Colunas | SKU; bases rateio; mercadoria; frete; seguro; tax; outros; total unit |
| Ações | Add expense; recalcular; publicar versão |
| Inline | Não em totais publicados |
| Drill-down | Expense; tax; shipment bases |
| Alertas | Sem base de rateio; FX ausente |
| Empty | CTA despesas/taxes |
| Permissões | costing:\* |
| Aceite | Expense∈Costing; lê Logistics+Treasury; SC-12 |

### 8.19 Conciliação

| Campo | Conteúdo |
|---|---|
| Propósito | Casos e pares de divergência |
| Usuário | Financeiro; gestor |
| Header | Abertos / resolvidos |
| KPIs | Abertos; bloqueantes; resolvidos período |
| Filtros | Tipo par; status; entidade |
| Agrupamentos | Por tipo de par |
| Colunas | Par; esquerdo; direito; delta; status; L-001; responsável |
| Ações | Abrir; resolver; anexar; reason code |
| Inline | Comentário; não “sumir” delta |
| Drill-down | Entidades do par |
| Alertas | Bloqueio de fechamento |
| Empty | “Sem divergências” |
| Permissões | reconciliation:\* |
| Aceite | L-001 explícito; SC-17 |

### 8.20 Documentos

Biblioteca + links; supersede; filtro por entidade; aceite histórico de versões.

### 8.21 Usuários e permissões

CRUD Identity; papéis; aceite sem depender de Documents no pacote Identity.

### 8.22 Auditoria

Consulta Audit por entidade/ator; append-only; aceite `actor_id` opaco.

---

## 9. Regras de negócio e cálculos

### 9.1 Valores e saldos

- Previsto / pago / saldo por Payable; Invoice agrega.  
- Pagamentos não alocados: lista explícita; **não** reduzem saldo.  

### 9.2 Câmbio e PnL (Inc-4)

Convenção: `rate` = BRL / 1 foreign. Benchmarks **nomeados** (não misturar):

```text
realized_result_vs_reference = settled × (frozen_plan − realized)
realized_result_vs_initial   = settled × (initial − realized)
online_result_vs_current     = open × (current_forecast − market)
online_result_vs_initial     = open × (initial − market)
total_vs_current = realized_result_vs_reference + online_result_vs_current
total_vs_initial = realized_result_vs_initial + online_result_vs_initial
```

Positivo = favorável. Cotação ausente → `null` (nunca zero). Reforecast **não** altera valuation congelada. Cotação online via `FxQuoteProvider` (Manual/Fixture/HTTP); domínio sem HTTP concreto.
### 9.3 Descontos, créditos, despesas, impostos

- Desconto ≠ crédito ≠ conta corrente BR (**L-003**).  
- Expense ∈ Costing. Tax ∈ Customs.  
- **DEC-SCONTO-ITEM `[DECISÃO]`:** linha de InvoiceItem com `discount_type` NONE|UNIT_AMOUNT|PERCENT; derivados bruto/desconto/líquido; emissão exige tipo definido; Payable = net Invoice; Costing consome líquido; global Treasury fora do Inc-2 Billing. Arredondamento: HALF_UP 2 casas (Fattura Heroes).

**Contexto V1:** DA SPEDIRE `discount_unit` (€/un); Nova Ordem €/un; Fattura coluna `% Sc`; entidade `Discount` documental separada.  

### 9.4 Quantidades

Pedida (OrderItem) → faturada (InvoiceItem) → embarcada (Σ ShipmentItem) → nacionalizada → disponível (movimentos). Divergência → Reconciliation.

### 9.5 Landed cost e rateio

Critérios de rateio documentados por versão; componentes rastreáveis.

### 9.6 Divergências, tolerâncias, fechamento

- Divergência nunca some.  
- **L-001:** tolerâncias oficiais pendentes — qualquer default é provisório e isolado.  
- Fechamento bloqueado com casos abertos bloqueantes; reabertura com reason + permissão.  
- Reason codes padronizados para exceções.

---

## 10. Documentos e ingestão

| Tipo | Finalidade | Módulo destino | Extração | Revisão | Fixture representativa |
|---|---|---|---|---|---|
| Ordine | Pedido Heroes | Orders | Sim | Sim | Ordine PDF |
| Fattura / Fattura di acconto | Invoice, scadenze e eventual cobrança de acconto | Billing | Sim | Sim | `Fattura_181-con acconti.pdf` (FATTURA + BONIFICO ANTICIPATO; ver DEC-ACCONTO-INVOICE) |
| FatturaDoganale | Aduana | Customs | Sim | Sim | FatturaDoganale_* |
| Packing List | Embarque | Logistics | Sim | Sim | PackingList_* |
| PrintDeclaration | Evidência | Documents only | Não | — | PrintDeclaration_* |
| Solicitação de Numerário | DUIMP 1:N invoices | Customs (+ Costing) | Sim | Sim | Numerário |
| Heroes XLSX | Ordens/Billing via adapter | Ingestion → Orders/Billing | Sim | Sim | ordine*.xlsx |

**Campos:** identificadores do documento; hash; versionamento; conflitos → staging/fila; resultado esperado documentado junto à fixture (Roadmap G). PDFs atuais = fixtures, não produção (ADR-10).

**Regra Fattura → dinheiro:** a ingestão/emissão de Fattura (incl. menção a acconto já pago ou *BONIFICO ANTICIPATO*) **não** cria Payment automaticamente. Eventual pagamento antecipado é registrado **separadamente** em Treasury, somente com evidência financeira. Se o PDF apenas mencionar acconto já pago, registrar referência documental para revisão/conciliação — sem assumir que o Payment existe no sistema.

---

## 11. Permissões e auditoria

### 11.1 Papéis (baseline)

admin, gestor, financeiro, comprador, operador/logistica — refinar com L-005.

### 11.2 Ações críticas (exigem permissão + audit ± documento ± reason)

Criar/liquidar pagamento; aplicar crédito; retificar invoice; troca modal; nacionalizar; fechar/reabrir; supersede documento; restore backup; override de bloqueio.

### 11.3 Overrides e anexos

Override com reason code + ator + timestamp; anexo obrigatório quando a regra do domínio exigir origem documental.

### 11.4 Histórico

AuditLog append-only; consulta por entidade; fechamento/reabertura com snapshot.

---

## 12. Relatórios, alertas e dashboards

| Tipo | Exemplos |
|---|---|
| Executivo | Exposição FX; total em aberto; ordens bloqueadas |
| Operacional | Filas staging; scadenze; shipments em trânsito; DUIMP pendente |
| Alertas | Unallocated; divergência; doc faltante; qty residual |
| Exportações | CSV/XLSX de filas e LC (Excel = export, não base) |
| Por entidade | Ordem, Invoice, Shipment, DUIMP, SKU |

Dashboard = Reporting; não grava domínio.

---

## 13. Requisitos não funcionais

### 13.1 Operação e plataforma

LAN; PostgreSQL local; sem Docker nesta fase; backup/restore testáveis; porta distinta V1/V2 na transição; `.env` isolado.

### 13.2 Segurança e integridade

Auth individual; RBAC; cookie httpOnly; soft-annul; transações explícitas nos use cases; ingestão idempotente.

### 13.3 Observabilidade, performance, API

Logs técnicos; audit de negócio; OpenAPI + **client TS gerado** (não editar manualmente); erros explícitos e estáveis; a11y básica; exports controlados.

### 13.4 Manutenibilidade e arquitetura modular

1. **Ausência de ciclos** entre módulos (grafo §5.16).  
2. **Dependências verificáveis** automaticamente (§13.5).  
3. Arquivos e componentes **coesos** — coesão/responsabilidade são **revisão humana**, não garantia só de AST.  
4. Código **gerado** claramente separado (ex.: `generated/`).  
5. **Proibição absoluta V2→V1:** nenhum arquivo em `v2/**` pode importar código de `v1/**`, **inclusive testes V2**.  
6. **Caracterização:** processo/ambiente V1 separado → input determinístico → **golden output versionado**; V2 executa sua implementação e compara com o golden — sem importar V1.  
7. **Backend:** package-by-domain; routers finos; repos no owner; contratos públicos; sem dumps globais multi-domínio.  
8. **Frontend:** por feature; páginas coordenadas; OpenAPI client gerado; domínio não vive só no UI.  
9. **Gatilhos de revisão** (§3.3): relatório obrigatório na Fundação; exceções justificadas no Roadmap.

### 13.5 Teste automático vs revisão arquitetural

#### Verificações automáticas (`v2/tests/architecture/test_import_boundaries.py`)

O AST/pytest **deve falhar** se detectar:

- imports proibidos (incl. qualquer `v2` → `v1`);
- dependências fora do grafo §5.16;
- ciclos no grafo de pacotes;
- acesso a internals de outro módulo;
- Reporting (ou equivalente) **escrevendo** em pacotes de domínio.

#### Relatório / revisão obrigatória (não automatizada por AST “cego”)

Na Fundação e em PRs relevantes, registrar no Roadmap:

- arquivos acima dos gatilhos §3.3;
- routers com responsabilidades excessivas;
- componentes React grandes;
- god services;
- arquivos genéricos sem ownership;
- exceções justificadas (gerado, migrations, fixtures, schemas extensos).

AST sozinho **não** prova coesão ou responsabilidade única sem heurística confiável — por isso a revisão manual é gate explícito (N.8).

---

## 14. Escopo e releases

| Release | Conteúdo |
|---|---|
| **Fundação** | Layout repo; Identity/Audit/Documents; OpenAPI; arch tests; regra Cursor V2; `epic_v2` vazio |
| **MVP operacional** | Order-to-Pay (Order→Invoice→Payable→Payment→FX→Docs→Audit→fila→cockpit) |
| **V2 completa** | Ingestão; Logistics; Customs+Inventory; Costing+Reconciliation; Dashboard; aceite + arquivar V1 |
| **Pós-V2** | Integrações fiscais/WMS/BI; refinamentos L-* |
| **Fora** | ERP completo; cloud; Docker nesta fase; migração de linhas V1 |

---

## 15. Cenários canônicos e critérios de aceite

Mapeamento dos cenários do Roadmap M.3 + fluxos §7. **Sem status de execução.**

| ID | Cenário | Aceite principal |
|---|---|---|
| SC-01 | Ordem com várias invoices | N invoices sob 1 Order; saldos independentes |
| SC-02 | Invoice com vários vencimentos | N Payables; saldo Invoice = Σ |
| SC-03 | Vários pagamentos → allocations | Liquidação só via Payable |
| SC-04 | Antecipo não alocado depois compensado | Sem dupla contagem; saldo só após allocate |
| SC-05 | Ordem em vários embarques | Só via ShipmentItem; sem order_id no Shipment |
| SC-06 | Item embarcado parcialmente | Residual explícito |
| SC-07 | 1 DUIMP → N invoices | Join 1:N; fixture Numerário |
| SC-08 | Fatura retificada | Histórico; sem hard-delete |
| SC-09 | Nacionalização parcial | Qty parcial + movimento |
| SC-10 | Entrada/consumo entreposto | Saldo derivado |
| SC-11 | Crédito origem ≠ uso | Audit + documento |
| SC-12 | Landed cost por SKU | Expenses+Taxes rateados; versões |
| SC-13 | Documento supersedido | Versão atual + histórico |
| SC-14 | Fechamento e reabertura | Permissão + reason + audit |
| SC-15 | Criação manual de ordem | §7.1 |
| SC-16 | Importação Ordine | §7.2 |
| SC-17 | Conciliação | §7.15; L-001 explícito |

---

## 16. Glossário

| Termo | Significado |
|---|---|
| **Ordine** | Pedido/ordem comercial Heroes (IT) |
| **Fattura** | Invoice / fatura (FINAL ou tipagem documental equivalente) |
| **Acconto (documento)** | Candidato a `invoice_type=ACCONTO` em Billing (DEC pendente); formaliza cobrança de adiantamento; pode gerar Payable; **não** é pagamento |
| **Payment antecipado** | Adiantamento pago em Treasury; pode existir sem allocation; só reduz saldo ao alocar |
| **Scadenza** | Vencimento → Payable |
| **Saldo** | Residual a liquidar (por Payable; Invoice agrega) |
| **DDT** | Documento di trasporto |
| **Packing List** | Lista de embarque |
| **BL / AWB** | Bill of Lading / Air Waybill |
| **DUIMP** | Declaração Única de Importação (BR) |
| **Numerário** | Solicitação de numerário ao despachante |
| **Landed cost** | Custo landed versionado por SKU |
| **Entreposto** | Regime/estoque intermediário |
| **Payable** | Unidade de liquidação |
| **PaymentAllocation** | Elo Payment→Payable |
| **ImportProcess** | Agregado aduaneiro V2 |
| **Cockpit** | Read model de navegação da Order |
| **Staging** | Camada pré-oficial da ingestão |
| **Reason code** | Motivo controlado de exceção |
| **Soft-annul** | Anulação lógica sem hard delete |

---

## 17. Rastreabilidade Blueprint ↔ Roadmap

Formato: `REQ-V2-{MOD}-{nnn}`. Sem coluna de status de execução.

| ID | Módulo | § Blueprint | Fase Roadmap | Critério de aceite (resumo) |
|---|---|---|---|---|
| REQ-V2-FND-001 | Foundation | 5.1, 13 | 1 | App sobe; health; OpenAPI; sem drift client |
| REQ-V2-ID-001 | Identity | 5.2, 8.1, 11 | 1 | Login/RBAC |
| REQ-V2-AUD-001 | Audit | 5.3, 8.22 | 1 | Evento crítico registrado |
| REQ-V2-DOC-001 | Documents | 5.4, 10, 8.20 | 1 | Upload+link+supersede |
| REQ-V2-CAT-001 | Catalog | 5.5, 8.6–8.7 | 2+ | CRUD SKU/supplier |
| REQ-V2-ORD-001 | Orders | 5.6, 7.1, 8.3–8.5 | 2 | Order-to-Pay slice |
| REQ-V2-BIL-001 | Billing | 5.7, 7.3, 8.10 | 2 | Invoice+N Payables |
| REQ-V2-TRE-001 | Treasury | 5.8, 7.4–7.6, 8.11–8.13 | 2 | Allocation só Payable |
| REQ-V2-ING-001 | Ingestion | 5.9, 7.2, 8.14, 10 | 3 | Commit idempotente + golden |
| REQ-V2-LOG-001 | Logistics | 5.10, 7.7–7.8, 8.15 | 4 | ShipmentItem; sem order_id |
| REQ-V2-CUS-001 | Customs | 5.11, 7.9–7.10, 8.16 | 5 | DUIMP 1:N invoices |
| REQ-V2-INV-001 | Inventory | 5.12, 7.11, 8.17 | 5 | Saldo derivado |
| REQ-V2-CST-001 | Costing | 5.13, 7.12, 8.18 | 6 | LC por SKU + Expense |
| REQ-V2-REC-001 | Reconciliation | 5.14, 7.15, 8.19 | 6 | Casos; L-001 isolado |
| REQ-V2-REP-001 | Reporting | 5.15, 8.2, 12 | 7 | Dashboard read-only |
| REQ-V2-MOD-001 | Transversal | 3.2–3.3, 5.16, 13.4–13.5 | 1 | Arch test + revisão manual; sem ciclos; V2↛V1; regra Cursor |
| REQ-V2-ACC-001 | Aceite | 15 | 8 | SC-01…SC-17 + equivalência cálculos |

---

## Apêndice A — Regras de código backend (resumo normativo)

- Organização por domínio (package-by-domain).  
- Router: HTTP + auth + validação + chamada de caso de uso.  
- Domínio independente de FastAPI.  
- Repository no módulo proprietário.  
- Sem import direto de ORM/repository/service **interno** de outro módulo.  
- Comunicação por comandos/consultas/contratos públicos.  
- Transações explícitas nos casos de uso.  
- Reporting só lê.  
- Evitar `models.py` / `services.py` / `utils.py` / `helpers.py` globais multi-domínio.

## Apêndice B — Regras de código frontend (resumo normativo)

- Organização por módulo/feature.  
- Páginas coordenam layout e navegação.  
- Componentes com responsabilidade clara.  
- Não concentrar API + estado + transformação + tabela + modais num único componente.  
- Evitar client manual monolítico; OpenAPI client gerado **não** é editado.  
- Regras de domínio não existem apenas no frontend.  
- Imports entre features respeitam APIs públicas.  
- Estado global somente quando realmente compartilhado.

## Apêndice C — Teste arquitetural previsto (Fundação)

Arquivo alvo: `v2/tests/architecture/test_import_boundaries.py` (pytest + AST; sem import-linter na primeira versão).

**Automático (falha o CI/teste):**

1. Nenhum import `v2/**` → `v1/**` (produção **ou** teste).  
2. Arestas de import entre pacotes de módulo ⊆ grafo §5.16.  
3. Ausência de ciclos.  
4. Sem import de subpacotes/módulos marcados como internals.  
5. Reporting sem escritas em domínio.

**Fora do AST (relatório N.8):** gatilhos de tamanho, god files, routers gordos, exceções justificadas.

---

## Changelog do Blueprint

| Versão | Data | Notas |
|---|---|---|
| 0.2.4 | 2026-07-23 | Inc-4: três visões FX (plan/quote/execution); ownership Treasury; benchmarks separados; N:M execution↔allocation; §5.8/§9.2 |
| 0.2.3 | 2026-07-22 | Clarificação Invoice ACCONTO vs Payment antecipado; DEC-ACCONTO-INVOICE pendente; §5.7/§8.10/§10/§7.4/glossário; tipos alvo `PROFORMA\|ACCONTO\|FINAL` (código Inc-2 ainda só PROFORMA\|FINAL) |
| 0.2.2 | 2026-07-22 | DEC-SCONTO-ITEM fechada; §5.7 Billing Inc-2 (FINAL/PROFORMA; ISSUED imutável; terms PERCENT\|AMOUNT); **Inc-3:** ownership de saldo Payable (`balance` só via `billing.public.apply_payable_allocations`; status OPEN\|PARTIALLY_PAID\|PAID\|CANCELLED) |
| 0.2 | 2026-07-22 | **Status** atualizado para *Aprovado — baseline funcional e arquitetural da V2* (consolidação documental; sem mudança de regras funcionais) |
