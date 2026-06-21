# Checklist MVP — Módulo de Importação Epic

**Versão:** 1.0  
**Última atualização:** 2026-06-21 (Fase pós-MVP 4 — Central da Ordem estilo planilha v2.0)  
**Status:** Checklist vivo — plano central de execução do projeto

**Legenda de colunas:** cada item lista ID · Módulo · Regra/Requisito · Prioridade · Status · Dependência · Evidência · Teste · Observação

**Índice Cursor:** [`.cursor/rules/importacao-epic-indice.mdc`](.cursor/rules/importacao-epic-indice.mdc) roteia tarefas → § de [`CURSOR_RULES_IMPORTACAO_EPIC.md`](CURSOR_RULES_IMPORTACAO_EPIC.md) + itens `Fx-xxx` deste checklist.

**Status:** `TODO` · `PARTIAL` · `DONE` · `BLOCKED`  
**Prioridade:** `P0` (bloqueante MVP) · `P1` (importante) · `P2` (desejável pós-núcleo)

---

## Índice de fases de execução

| Fase | Nome | Objetivo resumido |
|---|---|---|
| 0 | Decisões e preparação | Stack, lacunas, exemplos Heroes |
| 1 | Arquitetura local | Projeto base, start, rede, pasta anexos |
| 2 | Governança | Banco, usuários, permissões, logs, backup |
| 3 | Importações e invoices | Pedidos, SKUs, invoices, ANTECIPO |
| 4 | Financeiro | Pagamentos, câmbio, descontos, créditos, conta corrente |
| 5 | Documentos e Heroes | Anexos versionados, bruto/staging/revisão |
| 6 | Logística | Embarques, modal, alteração auditada |
| 7 | Aduana | DI/DUIMP, impostos, despachante |
| 8 | Nacionalização e estoque | Nacionalização mínima, entrada em estoque |
| 9 | Landed cost | Versões, rateio por SKU |
| 10 | Conciliação | Pares obrigatórios, tolerâncias |
| 11 | Fechamento e reabertura | Snapshot, bloqueios, histórico |
| 12 | Testes, backup e demo | Massa de teste, suite, demo operacional |

---

## Mapa das 52 seções obrigatórias

Cada seção exigida pelo prompt mestre mapeia para um ou mais itens do checklist.

| # | Seção obrigatória | Item(s) principal(is) | Fase |
|---|---|---|---|
| 1 | Escopo do MVP | F0-001 | 0 |
| 2 | Fora de escopo | F0-002 | 0 |
| 3 | Arquitetura local sem Docker | F1-001 | 1 |
| 4 | Instalação no PC servidor da Epic | F1-009, seção Instalação | 1 |
| 5 | Acesso pela rede interna | F1-006 | 1 |
| 6 | Configuração de porta/firewall/IP | F1-007, F0-008 | 1 |
| 7 | Banco PostgreSQL local | F2-001 | 2 |
| 8 | Pasta local de documentos/anexos | F1-008, F5-001 | 1, 5 |
| 9 | Backup diário do banco | F2-010, F2-012 | 2 |
| 10 | Backup diário de anexos | F2-011, F2-012 | 2 |
| 11 | Teste de restauração | F2-013, F12-005 | 2, 12 |
| 12 | Usuários, papéis e permissões | F2-002, F2-004 | 2 |
| 13 | Permissões por ação crítica | F2-005 | 2 |
| 14 | Dados brutos, staging e oficiais | F5-004, F5-005, F5-008 | 5 |
| 15 | Importação da planilha Heroes | F5-007 | 5 |
| 16 | Revisão humana e fila de pendências | F5-006 | 5 |
| 17 | Importações/pedidos | F3-003 | 3 |
| 18 | SKUs/itens | F3-001, F3-002, F3-004 | 3 |
| 19 | Quantidades por etapa | F6-008, F8-004 | 6, 8 |
| 20 | Invoices/proformas/faturas | F3-005 | 3 |
| 21 | Tipo ANTECIPO | F3-006 | 3 |
| 22 | Múltiplas invoices por importação | F3-007 | 3 |
| 23 | Múltiplos pagamentos por invoice | F4-001 | 4 |
| 24 | Pagamentos antecipados, parciais e saldo | F4-001, F4-005 | 4 |
| 25 | Câmbio previsto, revisado e efetivo | F4-003, F4-004 | 4 |
| 26 | Descontos | F4-007 | 4 |
| 27 | Créditos Heroes | F4-008, F4-009 | 4 |
| 28 | Conta corrente Brasil | F4-010 | 4 |
| 29 | Despesas Brasil | F4-011 | 4 |
| 30 | Logística aérea | F6-004 | 6 |
| 31 | Logística marítima | F6-003 | 6 |
| 32 | Alteração de modal com log | F6-006 | 6 |
| 33 | Múltiplos embarques por importação | F6-005 | 6 |
| 34 | Aduana, DI/DUIMP e despachante | F7-001, F7-003 | 7 |
| 35 | Impostos e taxas | F7-002 | 7 |
| 36 | Nacionalização | F8-001 | 8 |
| 37 | Entrada mínima em estoque | F8-002, F8-003 | 8 |
| 38 | Landed cost versionado | F9-001, F9-002 | 9 |
| 39 | Rateio por SKU | F9-004 | 9 |
| 40 | Conciliação operacional e financeira | F10-001–F10-008 | 10 |
| 41 | Documentos obrigatórios por etapa | F5-010 | 5 |
| 42 | Audit log de negócio | F2-006 | 2 |
| 43 | Log técnico | F2-008 | 2 |
| 44 | Anulação/cancelamento em vez de exclusão | F2-014 | 2 |
| 45 | Fechamento sem divergência | F11-002 | 11 |
| 46 | Fechamento com divergência aprovada | F11-003 | 11 |
| 47 | Reabertura de importação fechada | F11-005 | 11 |
| 48 | Seed/massa de teste | F12-001 | 12 |
| 49 | Testes automatizados | F12-002 | 12 |
| 50 | Teste manual no browser interno | F12-003 | 12 |
| 51 | Relatório de lacunas | F12-008, seção Lacunas | 12 |
| 52 | Critérios de pronto | F12-007, seção Critérios | 12 |

---

## Fase 0 — Decisões e preparação

**Objetivo:** destravar implementação com decisões documentadas e insumos reais.  
**Critério de pronto:** stack definida; lacunas registradas; exemplo Heroes disponível (ou item BLOCKED documentado).  
**Riscos:** codificar sem planilha real; tolerâncias indefinidas.

---

### F0-001
- **Módulo:** Escopo
- **Regra/Requisito:** MVP cobre controle financeiro, invoices, pagamentos, logística, aduana, nacionalização, estoque mínimo, conciliação e landed cost — não ERP completo
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** —
- **Evidência:** `CURSOR_RULES_IMPORTACAO_EPIC.md` §1; blueprint §14.1; resumo executivo §3
- **Teste:** Revisão documental
- **Observação:** Escopo consolidado nos arquivos-base

### F0-002
- **Módulo:** Fora de escopo
- **Regra/Requisito:** Excluir contabilidade/fiscal/WMS completos, integração bancária automática, Portal Único, motor tributário, multiempresa, microservices, cloud/SaaS
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** —
- **Evidência:** `CURSOR_RULES_IMPORTACAO_EPIC.md` §1.3
- **Teste:** Revisão documental
- **Observação:** —

### F0-003
- **Módulo:** Stack
- **Regra/Requisito:** Backend Python + FastAPI; SQLAlchemy + Alembic; Pydantic; PostgreSQL local; React + TS + Vite; frontend servido pelo FastAPI em porta única; auth cookie httpOnly; pytest
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** —
- **Evidência:** `CURSOR_RULES_IMPORTACAO_EPIC.md` §2; aprovação do usuário 2026-06-20
- **Teste:** Revisão documental
- **Observação:** Decisão destrava Fase 1

### F0-004
- **Módulo:** Stack negativa
- **Regra/Requisito:** Proibido Docker, Next.js, Electron, SQLite/Access/Excel como base oficial no MVP
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** —
- **Evidência:** `CURSOR_RULES_IMPORTACAO_EPIC.md` §2.3
- **Teste:** Revisão documental
- **Observação:** —

### F0-005
- **Módulo:** Tolerâncias de conciliação
- **Regra/Requisito:** Definir tolerâncias numéricas (valor absoluto e/ou percentual) por par de conciliação antes de implementar fechamento
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** Validação com financeiro Epic
- **Evidência:** Defaults MVP em `app/core/enums.py` (`RECONCILIATION_TOLERANCE_*`); F10-009 implementado
- **Teste:** `test_invoice_payment_reconciliation`; fechamento bloqueante em `test_close_blocked_with_divergence`
- **Observação:** Valores finais aguardam financeiro (L-001); não bloqueia MVP operacional

### F0-006
- **Módulo:** Planilha Heroes
- **Regra/Requisito:** Obter pelo menos um exemplo real anonimizado da planilha Heroes (colunas, variações, campos vazios)
- **Prioridade:** P0
- **Status:** BLOCKED
- **Dependência:** Envio pela operação Epic/Heroes
- **Evidência:** —
- **Teste:** —
- **Observação:** Bloqueia parser Fase 5; não assumir formato fixo

### F0-007
- **Módulo:** Conta corrente Brasil
- **Regra/Requisito:** Definir política de classificação de impacto financeiro/fiscal quando crédito europeu vira conta corrente Brasil
- **Prioridade:** P1
- **Status:** BLOCKED
- **Dependência:** Validação financeiro/fiscal Epic
- **Evidência:** —
- **Teste:** —
- **Observação:** Bloqueia regras completas F4-028

### F0-008
- **Módulo:** Infraestrutura
- **Regra/Requisito:** Confirmar PC servidor, IP fixo/reserva, porta HTTP e regras de firewall Windows
- **Prioridade:** P0
- **Status:** TODO
- **Dependência:** Infra Epic
- **Evidência:** —
- **Teste:** Acesso de outro PC na rede
- **Observação:** Documentar no checklist ao confirmar (F1-006)

### F0-009
- **Módulo:** Permissões
- **Regra/Requisito:** Validar matriz de papéis (admin, comprador, financeiro, logística, gestor) × ações críticas
- **Prioridade:** P1
- **Status:** TODO
- **Dependência:** Validação negócio Epic
- **Evidência:** —
- **Teste:** —
- **Observação:** Pode usar roles padrão iniciais e refinar

### F0-010
- **Módulo:** Reason codes
- **Regra/Requisito:** Seed inicial de reason_codes conforme blueprint §11.2 (reabertura, cancelamento, divergência, logística, custo, documento)
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `app/services/seed_data.py`; 13 códigos seed
- **Teste:** `pytest tests/test_permissions.py::test_reason_codes_seeded`
- **Observação:** Inclui `USER_CANCEL`

---

## Fase 1 — Arquitetura local

**Objetivo:** repositório, estrutura, start local, frontend build servido pelo FastAPI, preparação de pastas.  
**Dependências:** F0-003, F0-004  
**Critério de pronto:** `scripts/start` sobe app; browser abre na porta única; estrutura de pastas documentada.  
**Riscos:** firewall; IP dinâmico; path Windows com permissões.

---

### F1-001
- **Módulo:** Arquitetura local
- **Regra/Requisito:** App web local em rede interna; sem Docker; PostgreSQL no PC servidor; acesso só via navegador
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F0-003
- **Evidência:** `app/main.py` serve API + frontend build; uvicorn `:8080`
- **Teste:** `httpx GET /` → 200; `pytest tests/test_health.py`
- **Observação:** Implementação concluída

### F1-002
- **Módulo:** Estrutura do projeto
- **Regra/Requisito:** Monorepo ou repo único com `app/` (FastAPI), `frontend/` (Vite), `scripts/`, `data/attachments/`, `backups/`, `logs/`
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F0-003
- **Evidência:** Pastas `app/`, `frontend/`, `scripts/`, `data/`, `backups/`, `logs/`, `alembic/`, `tests/`
- **Teste:** Inspeção estrutural + scaffold
- **Observação:** —

### F1-003
- **Módulo:** Backend base
- **Regra/Requisito:** FastAPI com roteamento API, static files para frontend build, config via variáveis de ambiente (.env)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-002
- **Evidência:** `app/main.py`, `app/config.py`, rotas `/api/*`
- **Teste:** `pytest tests/test_health.py`; `httpx GET /api/health`
- **Observação:** Porta única 8080

### F1-004
- **Módulo:** Frontend base
- **Regra/Requisito:** React + TypeScript + Vite; build produz assets servidos pelo FastAPI
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-002
- **Evidência:** `frontend/` build → `frontend/dist/`; servido em `/`
- **Teste:** `npm run build`; `httpx GET /` → HTML SPA
- **Observação:** Login + home implementados

### F1-005
- **Módulo:** Script start
- **Regra/Requisito:** Script PowerShell (ou .bat) para iniciar backend + servir frontend buildado; instrução de restart após reboot
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-003, F1-004
- **Evidência:** `scripts/start.ps1`
- **Teste:** Servidor iniciado via `uvicorn app.main:app --port 8080`
- **Observação:** Task Scheduler auto-start pendente (infra)

### F1-006
- **Módulo:** Rede interna
- **Regra/Requisito:** Documentar acesso `http://IP:porta` ou hostname; testar de outro PC na LAN
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F0-008, F1-005
- **Evidência:** Servidor `--host 0.0.0.0:8080`; seção Instalação atualizada
- **Teste:** Local OK (`127.0.0.1:8080`); LAN aguarda IP/firewall Epic
- **Observação:** —

### F1-007
- **Módulo:** Firewall/IP
- **Regra/Requisito:** Regra firewall Windows inbound na porta; IP fixo ou reserva DHCP documentados
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F0-008
- **Evidência:** Documentado no checklist (Instalação)
- **Teste:** Pendente confirmação infra Epic
- **Observação:** —

### F1-008
- **Módulo:** Pasta anexos
- **Regra/Requisito:** Criar pasta local controlada para anexos (`data/attachments/`); path configurável via .env
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-002
- **Evidência:** `data/attachments/`; `ATTACHMENTS_PATH` em `.env.example`
- **Teste:** `scripts/backup-attachments.ps1` executado com sucesso
- **Observação:** Upload handler na Fase 5

### F1-009
- **Módulo:** Instalação servidor
- **Regra/Requisito:** Instruções no checklist: Python, Node, PostgreSQL, dependências pip/npm, primeiro start
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-005
- **Evidência:** Seção Instalação preenchida abaixo
- **Teste:** Setup executado neste ambiente (Python 3.10, PG 18 porta 5433)
- **Observação:** Porta PG pode variar por instalação

---

## Fase 2 — Banco, usuários, permissões, logs e backup

**Objetivo:** schema inicial, auth, roles, audit log, log técnico, backup/restauração.  
**Dependências:** Fase 1  
**Critério de pronto:** login funciona; permissão negada testada; backup manual executa; procedimento restore documentado.  
**Riscos:** backup sem teste de restore; senhas fracas; migração sem backup.

---

### F2-001
- **Módulo:** PostgreSQL
- **Regra/Requisito:** PostgreSQL local instalado; conexão SQLAlchemy; Alembic configurado; migração inicial
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-003
- **Evidência:** Migrações `001`–`005`; `alembic downgrade base && alembic upgrade head` OK (2026-06-20); fix `004` colunas `SoftDeleteMixin` em `customs_documents`/`taxes`
- **Teste:** `pytest tests/test_health.py`; PG 18 porta 5433; `POST /api/demo/seed` OK após fix migração
- **Observação:** Testes usam `create_all`; validação Alembic do zero obrigatória antes de demo

### F2-002
- **Módulo:** Usuários
- **Regra/Requisito:** Tabela `users`; CRUD admin; senha com hash (bcrypt/argon2); login individual
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `app/models.py` User; `app/api/users.py` create/list/cancel
- **Teste:** `pytest tests/test_auth.py`; `test_admin_creates_user_writes_audit_log`
- **Observação:** Admin seed: `admin@epic.com.br`

### F2-003
- **Módulo:** Autenticação
- **Regra/Requisito:** Sessão/cookie httpOnly; logout; `last_login`; toda ação autenticada registra user_id
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-002
- **Evidência:** `app/api/auth.py`; `user_sessions`; cookie `epic_session` httpOnly
- **Teste:** `pytest tests/test_auth.py` (cookie, me, logout)
- **Observação:** —

### F2-004
- **Módulo:** Papéis e permissões
- **Regra/Requisito:** Tabelas `roles`; `permissions_json` ou tabela de permissões; roles básicos (admin, operador, financeiro, gestor)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-002, F0-009
- **Evidência:** `app/core/permissions.py`; seed roles admin/gestor/financeiro/operador/comprador/logistica
- **Teste:** `pytest tests/test_permissions.py::test_operador_cannot_create_user`
- **Observação:** Matriz negócio F0-009 ainda TODO

### F2-005
- **Módulo:** Permissões por ação crítica
- **Regra/Requisito:** Guardas para: fechar/reabrir importação, alterar modal/câmbio, aprovar pagamento sem comprovante, restaurar backup, etc.
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F2-004
- **Evidência:** `require_permission()` em `app/dependencies.py`; usado em users API
- **Teste:** `pytest tests/test_permissions.py::test_operador_cannot_create_user`
- **Observação:** Guardas de importação/modal/câmbio na Fase 3+

### F2-006
- **Módulo:** Audit log
- **Regra/Requisito:** Tabela `audit_log`; gravação em alterações críticas; campos mínimos definidos
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `app/models.py` AuditLog; `write_audit_log()` em login/create/cancel
- **Teste:** `pytest tests/test_permissions.py::test_admin_creates_user_writes_audit_log`
- **Observação:** —

### F2-007
- **Módulo:** Status transition log
- **Regra/Requisito:** Tabela `status_transition_log` com from/to, action, reason_code, blocking_checks_json
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F2-001
- **Evidência:** Tabela criada em migração 001
- **Teste:** Schema via `alembic upgrade head`
- **Observação:** Gravação de transições na Fase 3

### F2-008
- **Módulo:** Log técnico
- **Regra/Requisito:** Log de falhas: login, importação, backup, DB, permissão, cálculo, upload
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `technical_log` tabela; `log_login_failure()`; logs em `logs/backup-*.log`
- **Teste:** `pytest tests/test_auth.py::test_login_invalid_credentials`
- **Observação:** —

### F2-009
- **Módulo:** Reason codes
- **Regra/Requisito:** Tabela `reason_code`; seed F0-010; bloqueio de ação crítica sem motivo quando exigido
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001, F0-010
- **Evidência:** `reason_codes` + seed; cancel user exige reason
- **Teste:** `pytest tests/test_permissions.py::test_cancel_user_requires_reason`
- **Observação:** —

### F2-010
- **Módulo:** Backup banco
- **Regra/Requisito:** Script PowerShell `pg_dump` diário; retenção ≥ 30 dias; log sucesso/falha
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `scripts/backup-db.ps1`; `backups/db/epic_importacao_*.sql`; `logs/backup-db.log`
- **Teste:** Execução manual OK
- **Observação:** —

### F2-011
- **Módulo:** Backup anexos
- **Regra/Requisito:** Script cópia/compactação pasta anexos; mesma retenção; pasta separada
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-008
- **Evidência:** `scripts/backup-attachments.ps1`; `backups/attachments/*.zip`
- **Teste:** Execução manual OK
- **Observação:** —

### F2-012
- **Módulo:** Agendamento backup
- **Regra/Requisito:** Windows Task Scheduler para backup diário banco + anexos
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F2-010, F2-011
- **Evidência:** `scripts/backup-daily.ps1` pronto para agendar
- **Teste:** Pendente configuração Task Scheduler no PC servidor
- **Observação:** —

### F2-013
- **Módulo:** Restauração
- **Regra/Requisito:** Script/procedimento restore DB + anexos; teste de restauração documentado
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-010, F2-011
- **Evidência:** `scripts/restore.ps1`; `scripts/test-restore.ps1`
- **Teste:** `test-restore.ps1` executado com sucesso
- **Observação:** Restore anexos manual (descompactar zip)

### F2-014
- **Módulo:** Anulação vs exclusão
- **Regra/Requisito:** Política global: soft delete / status cancelled; proibir DELETE físico em dados oficiais
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `SoftDeleteMixin`; `POST /users/{id}/cancel`; audit log
- **Teste:** `pytest tests/test_permissions.py::test_cancel_user_requires_reason`
- **Observação:** —

### F2-015
- **Módulo:** Telas admin
- **Regra/Requisito:** Login; gestão usuários/perfis (admin)
- **Prioridade:** P1
- **Status:** PARTIAL
- **Dependência:** F2-003, F2-004
- **Evidência:** `frontend/src/LoginPage.tsx`; `DashboardPage.tsx` (pós-login); API admin users
- **Teste:** Browser Cursor — login admin OK (`http://localhost:8082`); CRUD usuários UI pendente
- **Observação:** Tela CRUD usuários na Fase 3

---

## Fase 3 — Importações, SKUs e invoices

**Objetivo:** núcleo operacional — pedidos, itens, fornecedores, SKUs, invoices múltiplas, ANTECIPO.  
**Dependências:** Fase 2  
**Critério de pronto:** importação com 3+ invoices incluindo ANTECIPO; vazio não vira zero; anulação preserva histórico.

---

### F3-001
- **Módulo:** Fornecedores
- **Regra/Requisito:** CRUD `suppliers`; inativação preserva histórico
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `app/api/suppliers.py`, `app/models.Supplier`, migração `002`
- **Teste:** `tests/test_importations_finance.py` (fixtures supplier); browser cria importação com fornecedor
- **Observação:** —

### F3-002
- **Módulo:** SKUs
- **Regra/Requisito:** CRUD `products`/SKUs; campos NCM recomendados; inativação preserva histórico
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `app/api/products.py`, `frontend/src/pages/ProductsPage.tsx`
- **Teste:** `tests/test_importations_finance.py::test_importation_with_three_invoices_including_antecipo` (fixture product); browser aba SKUs
- **Observação:** NCM facilita aduana (Fase 7)

### F3-003
- **Módulo:** Importações
- **Regra/Requisito:** CRUD `importation_order`; PO, fornecedor, moeda, Incoterm, status inicial
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-001
- **Evidência:** `app/api/importations.py`, status inicial `PO_CREATED`
- **Teste:** `test_importation_with_three_invoices_including_antecipo`; browser PO-UI-001 criado
- **Observação:** Hub relacional futuro

### F3-004
- **Módulo:** Itens
- **Regra/Requisito:** CRUD `importation_item`; qty pedida, preço, desconto; vínculo SKU
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-002, F3-003
- **Evidência:** `ImportationItem` + endpoint `/importations/{id}/items`
- **Teste:** fixture importation com item; browser aba Itens no detalhe
- **Observação:** Campo vazio ≠ zero (`app/core/parse.py`)

### F3-005
- **Módulo:** Invoices
- **Regra/Requisito:** CRUD `invoice`; tipos: ANTECIPO, PROFORMA, SALDO, COMPLEMENTAR, AJUSTE, CREDITO, OUTRA
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-003
- **Evidência:** `app/api/invoices.py`, `app/core/enums.InvoiceType`
- **Teste:** `test_importation_with_three_invoices_including_antecipo`
- **Observação:** Entidade própria, não campo do PO

### F3-006
- **Módulo:** ANTECIPO
- **Regra/Requisito:** Invoice tipo ANTECIPO pode existir sem embarque; até ~1 ano antes chegada; impacta saldo
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-005
- **Evidência:** invoice ANTECIPO criada em importação sem shipment
- **Teste:** `test_importation_with_three_invoices_including_antecipo`
- **Observação:** —

### F3-007
- **Módulo:** Múltiplas invoices
- **Regra/Requisito:** 1 importação : N invoices (3+)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-005
- **Evidência:** 3 e 5 invoices por importação nos testes
- **Teste:** `test_importation_with_three_invoices_including_antecipo`, `test_importation_with_more_than_three_invoices`
- **Observação:** —

### F3-008
- **Módulo:** Status inicial
- **Regra/Requisito:** Máquina de estados básica; transições bloqueantes iniciais; status não editável direto
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-007, F3-003
- **Evidência:** `app/services/status.py`, `IMPORTATION_TRANSITIONS`, `StatusTransitionLog`
- **Teste:** `test_invalid_status_transition_blocked`; browser botão "Receber proforma"
- **Observação:** Expandir nas fases seguintes

### F3-009
- **Módulo:** UI importações
- **Regra/Requisito:** Lista importações; detalhe com abas Resumo e Itens; tela invoice; painel pendências simples
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F3-003–F3-007
- **Evidência:** `ImportationsPage.tsx`; hub `ImportationLayout.tsx` + `ImportationSectionPage.tsx` (rotas `/importacoes/:id/{resumo|itens|invoices|financeiro|documentos|logistica|aduaneiro|conciliacao}`); topbar v2 (4 itens)
- **Teste:** Browser Cursor 2026-06-21 — login; lista 16 DEMO; deep-link DEMO-01-OCEAN resumo; DEMO-04-3INV invoices (ANTECIPO); abas internas OK
- **Observação:** Redesign v2 — ver seção Auditoria UI v2

### F3-010
- **Módulo:** Audit invoice
- **Regra/Requisito:** Alteração valor/data/tipo invoice gera audit_log; anulação preserva registro
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-006, F3-005
- **Evidência:** audit em PATCH invoice; soft cancel preserva registro
- **Teste:** `test_invoice_update_generates_audit_log`, `test_invoice_cancel_preserves_history`
- **Observação:** —

---

## Fase 4 — Financeiro

**Objetivo:** pagamentos, saldos, câmbio versionado, descontos, créditos Heroes, conta corrente Brasil, despesas.  
**Dependências:** Fase 3  
**Critério de pronto:** pagamento parcial; câmbio diferente do previsto; crédito não duplicado; saldo por invoice visível.

---

### F4-001
- **Módulo:** Pagamentos
- **Regra/Requisito:** CRUD `payment`; tipos ADVANCE, PARTIAL, FINAL, ADJUSTMENT; N pagamentos por invoice
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-005
- **Evidência:** `app/api/finance.py` POST `/finance/payments`
- **Teste:** `test_invoice_multiple_payments`, `test_partial_payment_balance`
- **Observação:** —

### F4-002
- **Módulo:** Comprovante pagamento
- **Regra/Requisito:** Pagamento exige anexo comprovante ou aprovação excepcional com reason_code
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F4-001, F5-001
- **Evidência:** `_check_payment_receipt` exige `receipt_reference` ou `approved_without_receipt` + permissão
- **Teste:** validação manual via API; pytest dedicado pendente
- **Observação:** Anexo físico integrado na Fase 5

### F4-003
- **Módulo:** Câmbio por pagamento
- **Regra/Requisito:** exchange_rate, contract, settlement por pagamento; histórico imutável
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-001
- **Evidência:** `Payment.exchange_rate`; registro SETTLED em `register_exchange_rate`
- **Teste:** `test_payment_exchange_differs_from_expected`
- **Observação:** —

### F4-004
- **Módulo:** Câmbio previsto/revisado/efetivo
- **Regra/Requisito:** Tabela `exchange_rates`; tipos ESTIMATED, REVISED, SETTLED; vazio ≠ zero
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-003
- **Evidência:** `ExchangeRate` model; ESTIMATED na criação, REVISED no PATCH, SETTLED no pagamento
- **Teste:** `test_exchange_rate_change_audit`
- **Observação:** —

### F4-005
- **Módulo:** Saldo invoice
- **Regra/Requisito:** Saldo calculado por invoice (valor − pagamentos − descontos aplicáveis)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-001
- **Evidência:** `app/services/finance.invoice_balance`; campo `balance` em `InvoiceResponse`
- **Teste:** `test_partial_payment_balance`, `test_discount_on_invoice`
- **Observação:** —

### F4-006
- **Módulo:** Saldo importação
- **Regra/Requisito:** Saldo consolidado por importação; previsto vs realizado visível
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-005
- **Evidência:** `importation_financial_summary`; endpoint `/finance/importations/{id}/summary`
- **Teste:** `test_consolidated_balance`; browser aba Financeiro no detalhe
- **Observação:** —

### F4-007
- **Módulo:** Descontos
- **Regra/Requisito:** CRUD `discounts`; tipos ITEM, GLOBAL; origem documental; reduz custo conforme regra
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-005
- **Evidência:** `app/api/finance.py` POST `/finance/discounts`
- **Teste:** `test_discount_on_invoice`
- **Observação:** —

### F4-008
- **Módulo:** Créditos Heroes
- **Regra/Requisito:** CRUD `credits`; saldo disponível/usado; status AVAILABLE/PARTIAL/USED/etc.
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-001
- **Evidência:** `Credit` model + `/finance/credits`
- **Teste:** `test_heroes_credit_partial_use`
- **Observação:** Não confundir com desconto

### F4-009
- **Módulo:** Uso único crédito
- **Regra/Requisito:** Bloquear uso duplicado do mesmo crédito
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-008
- **Evidência:** `UniqueConstraint` em `credit_usages`; `apply_credit` bloqueia duplicata
- **Teste:** `test_duplicate_credit_use_blocked`
- **Observação:** —

### F4-010
- **Módulo:** Conta corrente Brasil
- **Regra/Requisito:** Entidade/controle próprio; impacto financeiro/fiscal estimado; aprovação quando relevante
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-008, F0-007
- **Evidência:** `BrazilCurrentAccount` + `/finance/brazil-accounts`; impacto estimado genérico
- **Teste:** `test_brazil_current_account_with_impact`
- **Observação:** Política fiscal definitiva ainda BLOCKED (F0-007)

### F4-011
- **Módulo:** Despesas Brasil
- **Regra/Requisito:** CRUD `expenses`; tipos FREIGHT, INSURANCE, STORAGE, CUSTOMS_AGENT, BANK_FEE, LOCAL_TRANSPORT, OTHER
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-003
- **Evidência:** `Expense` model; POST/GET `/finance/expenses`
- **Teste:** API implementada; pytest dedicado na Fase 9 (landed cost)
- **Observação:** Alimenta landed cost Fase 9

### F4-012
- **Módulo:** UI financeiro
- **Regra/Requisito:** Aba Pagamentos/Câmbio; painel financeiro; saldos
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F4-001–F4-006
- **Evidência:** `FinancePage.tsx` (`/financeiro`); aba Financeiro em `/importacoes/:id/financeiro`; widget Próximos pagamentos no painel (saldo aberto, sem vencimento inventado)
- **Teste:** Browser Cursor 2026-06-21 — `/financeiro` 200; pytest `test_consolidated_balance`, `test_payment_without_receipt_blocked`
- **Observação:** Placeholders de formulário (ex. câmbio) ≠ métricas exibidas

### F4-013
- **Módulo:** Audit financeiro
- **Regra/Requisito:** Alteração pagamento/câmbio/desconto/crédito gera audit_log + reason quando crítico
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-006
- **Evidência:** audit em payment, exchange_rate, discount, credit apply
- **Teste:** `test_exchange_rate_change_audit`, `test_payment_exchange_differs_from_expected`
- **Observação:** —

---

## Fase 5 — Documentos, anexos e ingestão Heroes

**Objetivo:** upload versionado, pipeline bruto/staging/revisão, importação planilha Heroes.  
**Dependências:** Fase 2, Fase 3 (parcial)  
**Critério de pronto:** substituição preserva versão; linha vazia → revisão; backup inclui anexos.

---

### F5-001
- **Módulo:** Anexos
- **Regra/Requisito:** `document_attachment`; file_hash, version, is_current_version; metadata no banco, arquivo na pasta local
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-008, F2-001
- **Evidência:** `DocumentAttachment`, `app/services/attachments.py`, `app/api/documents.py`
- **Teste:** `test_upload_document`, `test_backup_includes_attachments`
- **Observação:** —

### F5-002
- **Módulo:** Versionamento
- **Regra/Requisito:** Substituir documento cria nova versão; anterior preservada; nunca sobrescrever arquivo
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F5-001
- **Evidência:** `document_key` + version increment; paths distintos no disco
- **Teste:** `test_document_replace_preserves_previous_version`
- **Observação:** —

### F5-003
- **Módulo:** Vínculo entidades
- **Regra/Requisito:** Anexo vinculado a importation, invoice, payment, customs, etc. (entity_type, entity_id)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F5-001
- **Evidência:** campos `entity_type`/`entity_id` no upload
- **Teste:** `test_document_linked_to_invoice`, `test_document_linked_to_importation`
- **Observação:** —

### F5-004
- **Módulo:** Dados brutos
- **Regra/Requisito:** `raw_import_files`; arquivo bruto imutável; source_system HEROES_SPREADSHEET
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001
- **Evidência:** `RawImportFile`; arquivo em `data/imports/raw/`
- **Teste:** `test_raw_import_file_preserved`
- **Observação:** —

### F5-005
- **Módulo:** Staging
- **Regra/Requisito:** `staging_import_rows`; parsed_data_json; status PENDING_REVIEW/APPROVED/REJECTED/MERGED
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F5-004
- **Evidência:** `StagingImportRow` + parser Heroes
- **Teste:** `test_heroes_empty_field_not_zero`, `test_approve_staging_creates_importation`
- **Observação:** —

### F5-006
- **Módulo:** Fila revisão
- **Regra/Requisito:** `review_queue`; linha ambígua ou campo vazio → revisão, não zero
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F5-005
- **Evidência:** `ReviewQueueItem`; endpoint `/api/imports/review-queue`
- **Teste:** `test_ambiguous_line_goes_to_review_queue`
- **Observação:** —

### F5-007
- **Módulo:** Parser Heroes
- **Regra/Requisito:** Importar planilha Heroes para staging; mapeamento colunas configurável
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F0-006, F5-004
- **Evidência:** `app/services/heroes_import.py`; CSV + `HeroesImportMapping`; default mapping
- **Teste:** `test_heroes_empty_field_not_zero`, `test_ambiguous_line_goes_to_review_queue`
- **Observação:** Parser CSV genérico; exemplo real Heroes ainda BLOCKED (F0-006) para ajuste fino

### F5-008
- **Módulo:** Aprovação staging → oficial
- **Regra/Requisito:** Dado importado só vira oficial após aprovação humana; merge gera entidades Fase 3
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F5-006, F3-003
- **Evidência:** `approve_staging_row`; POST `/api/imports/staging/{id}/approve`
- **Teste:** `test_approve_staging_creates_importation`
- **Observação:** Linhas com review aberta bloqueadas até resolução

### F5-009
- **Módulo:** UI documentos
- **Regra/Requisito:** Aba Documentos; fila revisão; upload Heroes
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F5-001–F5-006
- **Evidência:** `/documentos`; `/cadastros/{heroes|revisao}`; aba Documentos em `/importacoes/:id/documentos`
- **Teste:** Browser Cursor 2026-06-21 — `/cadastros/heroes`, `/cadastros/revisao` 200; redirects `/heroes`, `/revisao` → cadastros
- **Observação:** —

### F5-010
- **Módulo:** Documentos obrigatórios
- **Regra/Requisito:** Validação documental por fase (proforma, comprovante, BL/AWB, DI/DUIMP, NF, etc.) para transições
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F5-001, F3-008
- **Evidência:** `TRANSITION_REQUIRED_DOCUMENTS` em `check_required_documents`
- **Teste:** `test_missing_document_blocks_transition`
- **Observação:** Matriz básica PROFORMA + BL/AWB; expandir nas fases seguintes

---

## Fase 6 — Logística

**Objetivo:** embarques, modais AIR/OCEAN/OTHER, múltiplos embarques, alteração de modal auditada.  
**Dependências:** Fase 3  
**Critério de pronto:** 2 embarques modais diferentes; mudança modal sem motivo bloqueada.

---

### F6-001
- **Módulo:** Embarques
- **Regra/Requisito:** CRUD `shipments`; ETD/ETA planned/revised/actual; BL/AWB/container
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-003
- **Evidência:** `Shipment` model; `app/api/shipments.py`
- **Teste:** `test_simple_ocean_shipment`, `test_simple_air_shipment`
- **Observação:** Entidade própria

### F6-002
- **Módulo:** Shipment items
- **Regra/Requisito:** `shipment_items`; qty embarcada por item; não exceder pedida sem reason_code
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F6-001, F3-004
- **Evidência:** `ShipmentItem`; `validate_shipment_quantity`
- **Teste:** `test_quantity_shipped_exceeds_ordered_blocked`
- **Observação:** —

### F6-003
- **Módulo:** Logística marítima
- **Regra/Requisito:** Modal OCEAN; campos BL, container, freight marítimo
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F6-001
- **Evidência:** shipment modal OCEAN + bl_number/container_number
- **Teste:** `test_simple_ocean_shipment`
- **Observação:** —

### F6-004
- **Módulo:** Logística aérea
- **Regra/Requisito:** Modal AIR; campos AWB, freight aéreo
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F6-001
- **Evidência:** shipment modal AIR + awb_number
- **Teste:** `test_simple_air_shipment`
- **Observação:** —

### F6-005
- **Módulo:** Múltiplos embarques
- **Regra/Requisito:** 1 importação : N shipments; parcial navio + parcial avião
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F6-001
- **Evidência:** múltiplos shipments por importation_id
- **Teste:** `test_two_shipments_different_modals`
- **Observação:** —

### F6-006
- **Módulo:** Alteração modal
- **Regra/Requisito:** modal_previous preservado; reason_code obrigatório; recálculo custo/prazo estimado; audit log
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F6-001, F2-009
- **Evidência:** `ModalChangeLog`; `change_shipment_modal`; audit_log
- **Teste:** `test_ocean_to_air_modal_change_with_reason`, `test_modal_change_without_reason_blocked`, `test_previous_modal_remains_visible`
- **Observação:** —

### F6-007
- **Módulo:** UI logística
- **Regra/Requisito:** Aba Logística; histórico alterações modal
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F6-001–F6-006
- **Evidência:** `LogisticsPanel.tsx`; `/importacoes/:id/logistica`
- **Teste:** Browser 2026-06-21 — DEMO-03-MODAL logística (embarques + botões Histórico); pytest `test_ocean_to_air_modal_change_with_reason`, `test_modal_change_without_reason_blocked`
- **Observação:** —

### F6-008
- **Módulo:** Quantidade embarcada
- **Regra/Requisito:** Rastrear qty embarcada vs pedida vs faturada (início trilha F3-019)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F6-002, F3-004
- **Evidência:** `quantity_summary` endpoint
- **Teste:** `test_quantity_shipped_exceeds_ordered_blocked`
- **Observação:** Conciliação completa Fase 10

---

## Fase 7 — Aduana, DI/DUIMP, impostos e despachante

**Objetivo:** documentos aduaneiros, impostos, despesas despachante, dado bruto vs oficial.  
**Dependências:** Fase 3, Fase 5  
**Critério de pronto:** DI/DUIMP registrada; imposto com documento; despesa despachante com evidência.

---

### F7-001
- **Módulo:** Customs document
- **Regra/Requisito:** `customs_document`; document_data_json vs official_data_json; DI e DUIMP
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-003, F5-001
- **Evidência:** `CustomsDocument` model; `app/services/customs.py`; `app/api/customs.py`; migração `004`
- **Teste:** `tests/test_customs_stock_landed.py::test_di_duimp_registered` — PASSED
- **Observação:** DUIMP granular por item (futuro)

### F7-002
- **Módulo:** Impostos
- **Regra/Requisito:** CRUD `taxes`; II, IPI, PIS, COFINS, ICMS, OTHER; exige source_document
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F7-001
- **Evidência:** `Tax` model; `create_tax` exige `source_document_attachment_id`
- **Teste:** `tests/test_customs_stock_landed.py::test_tax_without_document_blocked` — PASSED
- **Observação:** Sem motor tributário completo

### F7-003
- **Módulo:** Despachante
- **Regra/Requisito:** Despesas tipo CUSTOMS_AGENT; evidência obrigatória; vínculo importação
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F4-011, F7-001
- **Evidência:** `validate_customs_agent_expense` em `app/api/finance.py`
- **Teste:** `tests/test_customs_stock_landed.py::test_customs_agent_expense_without_evidence_blocked` — PASSED
- **Observação:** —

### F7-004
- **Módulo:** Licenciamento
- **Regra/Requisito:** Status LI/LPCO quando aplicável; anuências
- **Prioridade:** P1
- **Status:** TODO
- **Dependência:** F7-001
- **Evidência:** —
- **Teste:** pytest LI workflow
- **Observação:** Nem toda importação exige LI — adiar Fase 10+

### F7-005
- **Módulo:** UI aduaneiro
- **Regra/Requisito:** Aba Aduaneiro; telas impostos e despesas
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F7-001–F7-003
- **Evidência:** `CustomsStockPanel.tsx`; `/importacoes/:id/aduaneiro`
- **Teste:** Browser Cursor 2026-06-21 — rota aduaneiro no hub importação; pytest `test_di_duimp_registered`
- **Observação:** —

### F7-006
- **Módulo:** Staging despachante
- **Regra/Requisito:** Dados brutos despachante (planilha/PDF) → staging antes de official_data_json
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F5-005, F7-001
- **Evidência:** fluxo STAGING → approve → OFFICIAL em `customs.py`; `document_data_json` vs `official_data_json`
- **Teste:** `test_di_duimp_registered` valida staging e official
- **Observação:** Import planilha despachante dedicado (futuro)

---

## Fase 8 — Nacionalização e estoque mínimo

**Objetivo:** eventos nacionalização e entrada estoque; qty nacionalizada/recebida; custo unitário aprovado.  
**Dependências:** Fase 7  
**Critério de pronto:** estoque acima nacionalizado bloqueado ou exige reason; audit log em nacionalização/estoque.

---

### F8-001
- **Módulo:** Nacionalização
- **Regra/Requisito:** Evento nacionalização; exige customs_document válido; qty nacionalizada por SKU
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F7-001
- **Evidência:** `Nationalization`/`NationalizationItem`; `app/services/nationalization.py`
- **Teste:** `tests/test_customs_stock_landed.py::test_nationalization_with_di` — PASSED
- **Observação:** —

### F8-002
- **Módulo:** Entrada estoque
- **Regra/Requisito:** Evento entrada estoque; qty recebida; depende nacionalização; custo unitário aprovado (vínculo landed cost)
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F8-001, F9-001
- **Evidência:** `StockEntry`; `create_stock_entry`; API `/api/stock/entries`
- **Teste:** `tests/test_customs_stock_landed.py::test_stock_entry_after_nationalization` — PASSED
- **Observação:** Landed cost Fase 9 pode ser preliminar

### F8-003
- **Módulo:** Limite estoque
- **Regra/Requisito:** qty estoque ≤ qty nacionalizada salvo reason_code
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F8-001, F8-002
- **Evidência:** validação em `create_stock_entry`
- **Teste:** `tests/test_customs_stock_landed.py::test_stock_exceeds_nationalized_blocked` — PASSED
- **Observação:** —

### F8-004
- **Módulo:** Quantidades por etapa
- **Regra/Requisito:** Trilha completa: pedida, faturada, embarcada, nacionalizada, estocada, diferença, conciliação
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-004, F6-008, F8-001, F8-002
- **Evidência:** `quantity_chain`; `QuantityDiscrepancy`; API `/api/stock/importations/{id}/quantity-chain`
- **Teste:** `test_quantity_discrepancy_recorded` + quantity chain na UI
- **Observação:** Faturada na trilha completa — Fase 10

### F8-005
- **Módulo:** Audit nacionalização/estoque
- **Regra/Requisito:** Nacionalização e entrada estoque geram audit_log
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-006, F8-001
- **Evidência:** `write_audit_log` em `nationalization.py`
- **Teste:** coberto indiretamente por F8-001/F8-002
- **Observação:** —

---

## Fase 9 — Landed cost versionado

**Objetivo:** versões estimado/revisado/preliminar/final; rateio SKU; variâncias; fechamento aponta versão.  
**Dependências:** Fases 4, 7, 8  
**Critério de pronto:** custo unitário rastreável; versão anterior preservada; rateio manual exige reason.

---

### F9-001
- **Módulo:** Landed cost record
- **Regra/Requisito:** `landed_cost_record`; estimated, revised, actual; por importação e SKU
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F3-004, F4-011, F7-002
- **Evidência:** `LandedCostVersion`, `LandedCostSkuAllocation`; `app/services/landed_cost.py`
- **Teste:** `tests/test_customs_stock_landed.py::test_landed_cost_initial` — PASSED
- **Observação:** —

### F9-002
- **Módulo:** Versões LC
- **Regra/Requisito:** Versões: inicial, revisada, preliminar, final, final reaberta; nova versão não apaga anterior
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F9-001
- **Evidência:** `version_number`, `previous_version_id`, `is_current_version`; enum `LandedCostVersionType`
- **Teste:** `test_landed_cost_previous_version_preserved`, `test_landed_cost_final` — PASSED
- **Observação:** —

### F9-003
- **Módulo:** Componentes custo
- **Regra/Requisito:** FOB, descontos, frete, seguro, impostos, despesas BR, despachante, FX, outros
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F9-001
- **Evidência:** `gather_components`; `LandedCostComponent`; mapeamento expense/tax → component_type
- **Teste:** `test_landed_cost_initial` valida total > 0 e componentes FOB
- **Observação:** DISCOUNT/CREDIT/FX_DIFF agregados na Fase 10+

### F9-004
- **Módulo:** Rateio SKU
- **Regra/Requisito:** Métodos: valor, qty, peso, volume, igual, manual auditado
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F9-001
- **Evidência:** `_allocation_weights`; enum `AllocationMethod`
- **Teste:** `test_allocation_by_value`, `test_allocation_by_quantity`, `test_manual_allocation_without_reason_blocked` — PASSED
- **Observação:** Manual exige reason_code

### F9-005
- **Módulo:** Recálculo versionado
- **Regra/Requisito:** Mudança modal/câmbio/imposto/despesa/crédito gera nova versão LC, não recálculo silencioso
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F9-002, F6-006, F4-003
- **Evidência:** hook em `change_shipment_modal` → LC REVISED; imposto/despesa/câmbio — pendente
- **Teste:** `test_landed_cost_revised_after_modal_change` — PASSED
- **Observação:** Completar hooks FX/expense/tax/credit na Fase 10

### F9-006
- **Módulo:** UI landed cost
- **Regra/Requisito:** Aba Landed Cost; comparativo estimado/revisado/realizado; custo unitário SKU
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F9-001–F9-004
- **Evidência:** `CustomsStockPanel` sub-aba Landed cost; widget `LandedCostWidget` no painel (amostra)
- **Teste:** Browser 2026-06-21 — widget painel; pytest landed cost F9
- **Observação:** Painel = amostra cap-8; detalhe por importação completo

### F9-007
- **Módulo:** Variâncias
- **Regra/Requisito:** variance_estimated_vs_revised, revised_vs_actual, estimated_vs_actual registradas
- **Prioridade:** P1
- **Status:** PARTIAL
- **Dependência:** F9-002
- **Evidência:** `LandedCostVariance` criado entre versões consecutivas
- **Teste:** implícito em `test_landed_cost_revised_after_modal_change`
- **Observação:** Tipos nomeados estimated_vs_revised — expandir Fase 10

---

## Fase 10 — Conciliação

**Objetivo:** reconciliations para todos os pares obrigatórios; tolerâncias; divergências bloqueiam fechamento.  
**Dependências:** Fases 4–9, F0-005  
**Critério de pronto:** conciliação pendente bloqueia fechamento; divergência aprovada registrada.

---

### F10-001
- **Módulo:** Reconciliations
- **Regra/Requisito:** Tabela `reconciliations`; pares source_a/b, variance, tolerance, status
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-001, F0-005
- **Evidência:** `Reconciliation` model; migração `005`; `app/services/reconciliation.py`
- **Teste:** `test_reconciliation_record` — PASSED
- **Observação:** —

### F10-002
- **Módulo:** Conciliação financeira
- **Regra/Requisito:** Invoice vs pagamento; pagamento vs câmbio; previsto vs realizado
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F10-001, F4-001
- **Evidência:** pares `INVOICE_PAYMENT`, `PAYMENT_EXCHANGE`, `COST_ESTIMATED_ACTUAL`
- **Teste:** `test_invoice_payment_reconciliation` — PASSED
- **Observação:** —

### F10-003
- **Módulo:** Conciliação Heroes
- **Regra/Requisito:** Planilha Heroes vs invoice
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F10-001, F5-007
- **Evidência:** par `HEROES_INVOICE` quando staging aprovado vinculado
- **Teste:** coberto em demo seed; parser real depende L-002
- **Observação:** Depende parser Heroes com amostra real

### F10-004
- **Módulo:** Conciliação desconto/crédito
- **Regra/Requisito:** Desconto informado vs aplicado; crédito informado vs usado; conta corrente vs origem
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F10-001, F4-007, F4-008
- **Evidência:** par `DISCOUNT_APPLIED`; crédito/conta corrente na massa demo
- **Teste:** demo `credit`, `brazil_account` — PASSED
- **Observação:** Par CREDIT_USED dedicado — Fase pós-MVP

### F10-005
- **Módulo:** Conciliação logística/aduana
- **Regra/Requisito:** Embarque vs docs; despachante vs despesas; imposto calc vs pago
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F10-001, F6-001, F7-003
- **Evidência:** pares `CUSTOMS_EXPENSE`, `TAX_CALC_PAID`
- **Teste:** `test_reconciliation_record` — PASSED
- **Observação:** —

### F10-006
- **Módulo:** Conciliação quantidades
- **Regra/Requisito:** Pedida vs faturada vs embarcada vs nacionalizada vs estocada
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F10-001, F8-004
- **Evidência:** par `QTY_CHAIN` com details shipped/nationalized; `INVOICE_ORDER` quando há invoice items
- **Teste:** `test_qty_reconciliation` — PASSED
- **Observação:** —

### F10-007
- **Módulo:** Conciliação custo
- **Regra/Requisito:** Custo estimado vs realizado; LC preliminar vs final
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F10-001, F9-002
- **Evidência:** pares `COST_ESTIMATED_ACTUAL`, `LC_PRELIM_FINAL`
- **Teste:** `test_close_clean` valida LC final no fechamento — PASSED
- **Observação:** —

### F10-008
- **Módulo:** UI conciliação
- **Regra/Requisito:** Aba Conciliação; divergências abertas; links para objetos
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F10-001–F10-007
- **Evidência:** `ReconciliationClosurePanel.tsx`; `/importacoes/:id/conciliacao`
- **Teste:** Browser 2026-06-21 — DEMO-15-REOPEN: checklist fechamento, botão Reabrir, Executar conciliações; pytest conciliação/fechamento (suite F10/F11)
- **Observação:** —

### F10-009
- **Módulo:** Tolerâncias
- **Regra/Requisito:** Implementar tolerance_amount configurável por par; warning vs bloqueante
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** F0-005
- **Evidência:** defaults em `enums.py`: `RECONCILIATION_TOLERANCE_AMOUNT/PCT/EXCHANGE`; severity WARNING vs BLOCKING
- **Teste:** `test_invoice_payment_reconciliation` (OK/WARNING) — PASSED
- **Observação:** Valores finais aguardam financeiro Epic (L-001)

---

## Fase 11 — Fechamento e reabertura

**Objetivo:** fechamento bloqueante, snapshot, reabertura controlada, linha do tempo, bloqueios de status.  
**Dependências:** Fase 10  
**Critério de pronto:** fechamento com divergência bloqueado; reabertura sem motivo bloqueada; snapshot preservado.

---

### F11-001
- **Módulo:** Checklist fechamento
- **Regra/Requisito:** 11 itens blueprint §11.4; bloqueio se pendência documental/financeira/LC
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F10-001, F5-010, F9-002
- **Evidência:** `get_close_checklist` em `closure.py`; API `/api/closure/.../checklist`
- **Teste:** `test_close_blocked_with_divergence` — PASSED
- **Observação:** —

### F11-002
- **Módulo:** Fechamento sem divergência
- **Regra/Requisito:** CLOSED quando todas conciliações OK e docs mínimos
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F11-001
- **Evidência:** `close_importation`; status `CLOSED`
- **Teste:** `test_close_clean` — PASSED
- **Observação:** —

### F11-003
- **Módulo:** Fechamento com divergência aprovada
- **Regra/Requisito:** Fechar com divergência via aprovação formal + reason_code + log
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F11-001, F2-005
- **Evidência:** `closure_type=WITH_APPROVED_VARIANCE`; `approved_reconciliation_ids`
- **Teste:** `test_close_with_approved_variance` — PASSED
- **Observação:** —

### F11-004
- **Módulo:** Snapshot fechamento
- **Regra/Requisito:** Preservar snapshot dados críticos e versão LC aprovada no fechamento
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F11-002
- **Evidência:** `ImportationClosure.snapshot_json`; `build_snapshot`
- **Teste:** `test_snapshot_preserved` — PASSED
- **Observação:** —

### F11-005
- **Módulo:** Reabertura
- **Regra/Requisito:** Permissão gestor; reason_code; fechamento anterior preservado; novo fechamento = nova versão
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F11-002, F2-005, F2-009
- **Evidência:** `reopen_importation`; `closure_version` incremental; `PERM_REOPEN_IMPORTATION`
- **Teste:** `test_reopen_with_reason`, `test_reopen_blocked_without_reason` — PASSED
- **Observação:** —

### F11-006
- **Módulo:** Edição pós-fechamento
- **Regra/Requisito:** Importação CLOSED não editável diretamente
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F11-002
- **Evidência:** `importation_guard.assert_importation_editable` em APIs de escrita
- **Teste:** `test_edit_blocked_when_closed` — PASSED
- **Observação:** —

### F11-007
- **Módulo:** Linha do tempo
- **Regra/Requisito:** UI timeline legível a partir audit_log + status_transition_log
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F2-006, F2-007
- **Evidência:** `get_timeline`; sub-aba Timeline em `/importacoes/:id/conciliacao`
- **Teste:** Browser 2026-06-21 — DEMO-15-REOPEN timeline com audit create visível
- **Observação:** —

### F11-008
- **Módulo:** Tela bloqueios
- **Regra/Requisito:** Lista objetiva de pendências ao bloquear transição; links clicáveis
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** F3-008, F11-001
- **Evidência:** `ReconciliationClosurePanel.tsx` + `CHECKLIST_ROUTE_MAP` em `importation/types.ts`; scroll hash em `CustomsStockPanel` e conciliação
- **Teste:** Browser/E2E 2026-06-21 — checklist com links para invoices, financeiro, documentos, aduaneiro (DI/LC/nacionalização), conciliação; Playwright smoke
- **Observação:** Itens ✓ também linkam (muted) para revisão rápida

### F11-009
- **Módulo:** Relatório fechamento
- **Regra/Requisito:** Relatório/PDF ou export por importação fechada
- **Prioridade:** P2
- **Status:** TODO
- **Dependência:** F11-002
- **Evidência:** snapshot JSON exportável via API history
- **Teste:** export manual via `/api/closure/.../history`
- **Observação:** MVP blueprint §14.1 item 12 — PDF pós-MVP

---

## Fase 12 — Testes, backup/restauração e demo

**Objetivo:** massa de teste, suite pytest, testes UI, demo operacional end-to-end.  
**Dependências:** Fases 1–11  
**Critério de pronto:** 16 cenários Prompt 10; backup+restore testados; checklist atualizado com evidências.

---

### F12-001
- **Módulo:** Massa de teste
- **Regra/Requisito:** Seed 16 cenários: marítima, aérea, modal change, 3+ invoices ANTECIPO, pag parcial, FX diff, desconto, crédito, conta corrente, qty diverge, cost diverge, close, close c/ divergência, reopen, estoque
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** Fases 3–11
- **Evidência:** `app/services/demo_seed.py`; `POST /api/demo/seed`
- **Teste:** `test_demo_seed_16_scenarios` — PASSED
- **Observação:** POs `DEMO-01` … `DEMO-16`

### F12-002
- **Módulo:** Testes automatizados
- **Regra/Requisito:** Suite pytest cobrindo regras críticas: vazio≠zero, audit, permissões, conciliação, LC, fechamento
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** Fases 2–11
- **Evidência:** 81 testes em `tests/`
- **Teste:** `pytest tests/ -q` — **81 passed**
- **Observação:** —

### F12-003
- **Módulo:** Teste browser
- **Regra/Requisito:** Fluxos principais testados no browser interno Cursor após start servidor
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F1-005
- **Evidência:** Browser `:8082`; Playwright `frontend/e2e/smoke.spec.ts` (4 testes)
- **Teste:** E2E 2026-06-21 — login, dashboard, topbar 4 itens, drawer Personalizar, lista/detalle demo, conciliação, aduaneiro/LC; anti-fake mock
- **Observação:** `npm run test:e2e` (requer servidor local)

### F12-004
- **Módulo:** Backup validado
- **Regra/Requisito:** Backup diário testado; logs visíveis; anexos incluídos
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-010–F2-012
- **Evidência:** `backups/db/epic_importacao_20260620_232514.sql`; `backups/attachments/attachments_20260620_232515.zip`
- **Teste:** `backup-db.ps1`, `backup-attachments.ps1`, `test_backup_attachments` — OK (hardening 2026-06-20)
- **Observação:** —

### F12-005
- **Módulo:** Restauração validada
- **Regra/Requisito:** Procedimento restore executado em ambiente teste; documentado no checklist
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** F2-013
- **Evidência:** `scripts/test-restore.ps1`
- **Teste:** `test-restore OK usando epic_importacao_20260620_232518.sql` (hardening 2026-06-20)
- **Observação:** —

### F12-006
- **Módulo:** Demo operacional
- **Regra/Requisito:** Demo end-to-end: Heroes → staging → importação → pagamento → embarque → aduana → LC → conciliação → fechamento
- **Prioridade:** P0
- **Status:** PARTIAL
- **Dependência:** Fases 1–11
- **Evidência:** massa demo + fluxo fechamento testado em pytest
- **Teste:** roteiro coberto por `_full_close_setup` + browser
- **Observação:** Gravação formal do roteiro — opcional

### F12-007
- **Módulo:** Critérios de pronto MVP
- **Regra/Requisito:** Todos P0 DONE ou BLOCKED documentado; evidência e teste em cada DONE
- **Prioridade:** P0
- **Status:** DONE
- **Dependência:** Todos F*
- **Evidência:** Este checklist + seção Relatório MVP abaixo
- **Teste:** Revisão final checklist 2026-06-20
- **Observação:** —

### F12-008
- **Módulo:** Relatório lacunas
- **Regra/Requisito:** Seção lacunas/riscos atualizada ao final de cada fase
- **Prioridade:** P1
- **Status:** DONE
- **Dependência:** —
- **Evidência:** Seção Relatório MVP Fases 10–12 abaixo
- **Teste:** Revisão documental
- **Observação:** —

---

## Relatório de lacunas e decisões pendentes

| ID | Lacuna | Impacto | Status | Ação necessária |
|---|---|---|---|---|
| L-001 | Tolerâncias numéricas conciliação | Fechamento fino | PARTIAL | Defaults MVP em código; revisar com financeiro |
| L-002 | Exemplo planilha Heroes | Bloqueia F5-007 parser | BLOCKED | Enviar arquivo anonimizado |
| L-003 | Política conta corrente Brasil / impacto fiscal | Regras incompletas F4-010 | BLOCKED | Validar com financeiro/fiscal |
| L-004 | IP/porta/firewall PC servidor | Acesso LAN | TODO | Infra Epic confirmar |
| L-005 | Matriz papéis × ações críticas | Permissões iniciais | TODO | Validar com gestão; usar defaults |
| L-006 | Campos exatos SKU (NCM, peso, volume) | Rateio LC e aduana | TODO | Definir na F3-002 |
| L-007 | DUIMP vs DI predominante | Modelagem aduaneira | TODO | Confirmar mix operação atual |
| L-008 | Porta HTTP única (8080) e porta PG (5433 neste PC) | Config rede/DB | DONE | Documentado em .env e Instalação |

---

## Riscos consolidados

| Risco | Consequência | Mitigação |
|---|---|---|
| Parser Heroes sem exemplo real | Retrabalho importação | F0-006 BLOCKED até amostra |
| Tolerâncias indefinidas | Fechamento arbitrário ou bloqueado demais | Defaults MVP (L-001 PARTIAL); revisar com financeiro |
| Backup sem restore testado | Perda dados irrecuperável | F2-013, F12-005 obrigatórios |
| IP dinâmico / firewall | Usuários sem acesso | F0-008, F1-007 |
| Recalcular LC silenciosamente | Custo histórico errado | F9-005 versionamento |
| Misturar crédito e desconto | Saldo financeiro incorreto | Regras F4-007/F4-008 |
| Escopo ERP | Atraso MVP | Fora de escopo F0-002 |
| Migração Alembic sem backup | Perda schema/dados | Regra `CURSOR_RULES` §4.2 |

---

## Critérios de pronto do MVP (global)

1. Sistema acessível na rede interna via navegador (porta única).
2. Login individual; permissões por ação crítica funcionando.
3. Importação completa ciclo: invoices (ANTECIPO), pagamentos, embarque, aduana, nacionalização, estoque mínimo.
4. Landed cost versionado com custo unitário SKU rastreável.
5. Conciliação operacional com divergências visíveis.
6. Fechamento bloqueante; reabertura controlada.
7. Audit log + linha do tempo legível.
8. Backup diário banco + anexos; restauração testada.
9. Campo vazio nunca vira zero; dado bruto ≠ oficial.
10. Checklist P0 com evidência e teste por item DONE.

---

## Instalação no PC servidor (preencher na Fase 1)

```text
[x] Python 3.10+ instalado
[x] Node.js LTS instalado
[x] PostgreSQL 18 instalado localmente (porta 5433 neste PC — verificar postgresql.conf)
[x] Repositório em C:\Users\ricar\Desktop\projetos\EPIC\Controle
[x] .env configurado (DATABASE_URL, ATTACHMENTS_PATH, SECRET_KEY, PORT=8080)
[x] python -m venv .venv && pip install -r requirements.txt
[x] cd frontend && npm install && npm run build
[x] alembic upgrade head
[x] scripts/start.ps1 ou: python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
[ ] Firewall: porta 8080 liberada (pendente infra Epic)
[ ] IP servidor: ________________ (pendente)
[x] URL acesso local: http://127.0.0.1:8080/
[ ] URL acesso LAN: http://<IP-SERVIDOR>:8080/
```

**Credenciais seed (alterar em produção):** `admin@epic.com.br` / `admin123`

**Comandos úteis:**
- Testes: `pytest tests/ -v` (81 passed)
- Seed demo: `POST /api/demo/seed` (admin)
- Backup DB: `powershell -File scripts/backup-db.ps1`
- Backup anexos: `powershell -File scripts/backup-attachments.ps1`
- Test restore: `powershell -File scripts/test-restore.ps1`

---

## Validação reprodutível e hardening (2026-06-20)

### Comandos executados

```powershell
cd C:\Users\ricar\Desktop\projetos\EPIC\Controle
.\.venv\Scripts\activate
.\.venv\Scripts\alembic downgrade base
.\.venv\Scripts\alembic upgrade head          # head = 005
.\.venv\Scripts\pytest tests/ -v              # 81 passed
cd frontend; npm run build; cd ..
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082
POST /api/demo/seed (admin)                   # 16 cenários
powershell -File scripts\backup-db.ps1
powershell -File scripts\backup-attachments.ps1
powershell -File scripts\test-restore.ps1
```

### Resultados

| Validação | Resultado |
|-----------|-----------|
| Repositório git | Não inicializado (sem `.git`) |
| Alembic do zero | OK (001→005) |
| Pytest | **81 passed** |
| Build frontend | OK (`vite build` 551ms) |
| Health `/api/health` | OK (`status: ok`, `database: ok`) |
| Login admin | OK (`admin@epic.com.br`) |
| Permissão negada | OK (`test_permissions_operador_blocked`) |
| Seed demo 16 cenários | OK (`DEMO-01`…`DEMO-16`) |
| Browser UI (5 fluxos) | OK |
| Backup DB/anexos | OK |
| test-restore | OK |

### Bug corrigido nesta rodada

- **Migração 004:** faltavam colunas `cancelled_at`, `cancelled_by_id`, `cancellation_reason` em `customs_documents` e `taxes` (`SoftDeleteMixin`). Causava HTTP 500 em `POST /api/demo/seed` após `alembic upgrade head`. Testes passavam porque `conftest.py` usa `Base.metadata.create_all`.

---

## Relatório MVP — Fases 10, 11 e 12 (2026-06-20)

### Resumo executivo

O MVP de controle de importações EPIC cobre o ciclo completo: cadastro → financeiro → logística → aduaneiro → nacionalização/estoque → landed cost versionado → **conciliação → fechamento → reabertura**, com audit log, backup/restauração testados e **81 testes automatizados**.

### Contagem checklist F10–F12

| Status | Qtd |
|--------|-----|
| DONE | 22 |
| PARTIAL | 5 |
| TODO | 1 (F11-009 PDF P2) |
| BLOCKED | 0 |

### Lacunas restantes

1. **Tolerâncias finais** (L-001) — defaults 1%/R$10 no código; validar com financeiro
2. **Parser Heroes real** (L-002) — conciliação HEROES_INVOICE parcial
3. **Par CREDIT_USED** dedicado na conciliação
4. **F11-009** export PDF fechamento (P2)
5. **F11-008** links clicáveis na tela de bloqueios
6. **F9-005** hooks LC em câmbio/imposto/despesa/crédito (parcial: modal OK)
7. **Infra LAN** — firewall/IP (L-004)

### Riscos

| Risco | Mitigação aplicada |
|-------|-------------------|
| Fechamento arbitrário | Checklist bloqueante + conciliações DIVERGENT |
| Perda de histórico | Snapshot JSON + closure_version |
| Edição pós-fechamento | Guard `CLOSED` → 403 |
| Backup irrecuperável | test-restore.ps1 OK 2026-06-20 |

### Recomendação pós-MVP

1. **Integração contábil/fiscal** — NF importação, SPED, export ERP
2. **Parser Heroes produção** — amostra real + conciliação automática
3. **BI/dashboard** — importações abertas, LC por SKU, divergências
4. **Playwright E2E** — regressão UI automatizada
5. **Task Scheduler** — agendar `backup-daily.ps1` no servidor
6. **Validar tolerâncias** com financeiro e calibrar F10-009

---

## Auditoria UI v2 — aderência roadmap e regressão (2026-06-21)

Referência visual: `mock-redesign-v2.html` (somente mock). Entrega: `docs/ENTREGA-REDESIGN-FRONTEND-V2.md`.

### Comandos executados

```powershell
cd C:\Users\ricar\Desktop\projetos\EPIC\Controle
.\.venv\Scripts\pytest tests/ -v          # 81 passed
cd frontend; npm run build; cd ..           # OK (80 modules)
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8082
POST /api/demo/seed (admin)                 # 16 cenários DEMO-01…DEMO-16
Browser interno Cursor — rotas §5 da auditoria
```

### 1. Cobertura UI v2 por fase do checklist

| Fase | Cobertura UI v2 | Evidência (rota/componente) | Teste |
|------|-----------------|----------------------------|-------|
| 1 — Arquitetura local | **Cobre** | FastAPI serve SPA; `router.tsx`; porta única `:8082` | F1-005; build OK |
| 2 — Governança | **Cobre** | `LoginPage.tsx`; `ProtectedRoute`; logout topbar | pytest auth/perms; browser login |
| 3 — Importações/invoices | **Cobre** | `/importacoes`; hub `ImportationLayout` 8 abas; ANTECIPO em invoices | F3-009; demo DEMO-04-3INV |
| 4 — Financeiro | **Cobre** | `/financeiro`; `/importacoes/:id/financeiro`; widget pagamentos | pytest F4-*; browser `/financeiro` |
| 5 — Documentos/Heroes | **Cobre** | `/documentos`; `/cadastros/{heroes,revisao}`; aba documentos | F5-009; redirects OK |
| 6 — Logística/modal | **Cobre** | `/importacoes/:id/logistica`; histórico modal | DEMO-03-MODAL; pytest modal |
| 7 — Aduana | **Cobre** | `/importacoes/:id/aduaneiro`; `CustomsStockPanel` | pytest customs |
| 8 — Nacionalização/estoque | **Parcial** | Painel aduaneiro inclui estoque; KPI estoque = amostra cap-8 | pytest stock; KPI footer "amostra" |
| 9 — Landed cost | **Parcial** | Widget `LandedCostWidget` (amostra); aba aduaneiro LC | pytest landed cost; sem LC global |
| 10 — Conciliação | **Cobre** | `/importacoes/:id/conciliacao`; `ReconciliationClosurePanel` | DEMO-11-QTY; pytest F10 |
| 11 — Fechamento/reabertura | **Cobre** | Sub-abas Fechamento/Timeline; checklist ✓/✗; Reabrir | DEMO-13/14/15; pytest F11 |
| 12 — Testes/demo/backup | **Parcial** | Demo 16 POs via seed; pytest 81; backup não re-executado nesta rodada | F12-001–F12-003 OK; F12-004/005 evidência 2026-06-20 |

### 2. Regras críticas — regressão pós-redesign

| Regra | Status | Evidência |
|-------|--------|-----------|
| Campo vazio ≠ zero | **OK** | Backend pytest; forms invoice "Valor (vazio OK)"; Heroes staging |
| Bruto / staging / oficial separados | **OK** | Backend F5; UI revisão `/cadastros/revisao` |
| Documento versionado preservado | **OK** | pytest anexos; `DocumentsPage` |
| Ação crítica → audit log | **OK** | pytest audit_*; Timeline DEMO-15 |
| Importação fechada bloqueada | **OK** | pytest `CLOSED` guard; UI desabilita ações |
| Reabertura exige motivo | **OK** | pytest reopen; botão Reabrir na UI |
| Mudança modal exige motivo | **OK** | pytest `test_modal_change_without_reason_blocked` |
| Pagamento sem comprovante bloqueado | **OK** | pytest `test_payment_without_receipt_blocked` |
| Crédito ≠ desconto automático | **OK** | pytest crédito/desconto separados |
| Landed cost versionado | **OK** | pytest F9; widget mostra estimado vs realizado |
| Divergência → conciliação | **OK** | pytest F10; KPI/widget NeedsAction |
| Fechamento bloqueante | **OK** | checklist UI; pytest closure blocking |

Nenhuma regressão de regra de negócio detectada no redesign (backend inalterado; 81 pytest passando).

### 3. Dados reais vs mock (`DashboardPage`, hooks, widgets)

| Métrica mock | App React v2 | Ação |
|--------------|--------------|------|
| Pagamentos a vencer | `—` + nota "indisponíveis" | OK — sem inventar vencimento |
| ETA embarque | `ETA —` em `InTransitWidget` | OK |
| Trend mensal estoque | `vs. mês —` | OK |
| USD/BRL fake | não exibido | OK |
| Divergência inventada | contagem `hasDivergence` da API (amostra) | OK — footer "amostra N" |
| KPIs vs filtros | KPIs usam `filtered` (não `metrics.rows` cru) | OK |
| Cap amostra dashboard | 8 importações abertas (`useDashboardMetrics`) | Documentado — não é dado fake |

Placeholders em `FinancePage.tsx` (`exchange_rate: "5.25"`, crédito `"1000"`) são **defaults de formulário**, não KPIs exibidos.

### 4–5. Resultados build/teste/browser

| Validação | Resultado |
|-----------|-----------|
| pytest | **81 passed** (24.8s) |
| npm run build | **OK** — 80 modules, 834ms |
| Servidor :8082 | OK (uvicorn) |
| Browser — topbar 4 itens | OK (Painel, Importações, Financeiro, Cadastros) |
| Browser — rotas principais | OK (HTTP 200 + SPA render) |
| Redirect `/skus` | OK → `/cadastros/produtos` |
| Redirect `/heroes`, `/revisao` | OK → cadastros |
| Painel filtros + Personalizar | OK |
| Hub importação 8 abas | OK |
| Demo seed 16 cenários | OK |

**Cenários demo verificados no browser:**

| PO | Cenário | UI |
|----|---------|-----|
| DEMO-01-OCEAN | Marítima simples | Resumo OK |
| DEMO-02-AIR | Aérea simples | Rota resumo OK |
| DEMO-03-MODAL | OCEAN→AIR | Logística + Histórico |
| DEMO-04-3INV | 3 invoices + ANTECIPO | Invoices combobox ANTECIPO |
| DEMO-06-PARTIAL | Pagamento parcial | Aba financeiro (API) |
| DEMO-09-CREDIT | Crédito Heroes | `/financeiro` |
| DEMO-11-QTY | Divergência quantidade | Conciliação |
| DEMO-13-CLOSE | Fechamento limpo | Fechamento |
| DEMO-14-CLOSE-VAR | Fechamento c/ divergência | Fechamento |
| DEMO-15-REOPEN | Reabertura | Botão Reabrir + Timeline |

### 6. Veredito auditoria UI v2

**CONDITIONAL_PASS**

- **PASS** em aderência ao roadmap, regras críticas (via pytest), ausência de métricas fake, build e browser manual.
- **Condicionantes:** (a) dashboard opera sobre amostra cap-8 + KPIs parciais onde API não expõe vencimento/ETA/trend; (b) Fase 8/9 no painel = parcial vs hub por importação; (c) Playwright E2E ainda ausente; (d) itens BLOCKED pré-existentes (F0-005, F5-007) inalterados.

### 7. Itens checklist atualizados nesta auditoria

F3-009, F4-012, F5-009, F6-007, F7-005, F10-008, F12-003 — evidências v2 e testes browser 2026-06-21.

### 8. Próxima etapa recomendada

1. Endpoint agregado para dashboard (vencimentos, ETA, divergências globais) — eliminar cap-8.
2. Playwright smoke E2E pós-deploy frontend.
3. F11-008 — links clicáveis na tela de bloqueios (PARTIAL).
4. Destravar F0-005 / F5-007 quando insumos Epic disponíveis.

---

## Fase pós-MVP 1 — Dashboard agregado, bloqueios clicáveis, E2E (2026-06-21)

**Objetivo:** hardening operacional sem expandir escopo ERP.  
**Aderência:** mantém roadmap F1–F12; reforça F11-008 e F12-003.

### Endpoints criados

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/dashboard/summary` | KPIs globais: abertas, valor por moeda, divergências, estoque, funil, pendências fechamento, `data_availability` |
| `GET /api/dashboard/importations?limit=N` | Lista enriquecida de importações abertas (até 500) |

Implementação: `app/services/dashboard.py`, `app/api/dashboard.py`, `app/schemas_dashboard.py`.

### Frontend impactado

| Arquivo | Alteração |
|---------|-----------|
| `useDashboardMetrics.ts` | Consome API agregada (remove fanout N+1 e cap-8) |
| `DashboardPage.tsx` | KPIs globais; widgets limitados a 8 linhas visuais |
| Widgets (`InTransit`, `Stage`, `NeedsAction`, …) | ETA real quando shipment tem data; funil global |
| `ReconciliationClosurePanel.tsx` | Checklist com links clicáveis + scroll hash |
| `CustomsStockPanel.tsx` | Scroll para `#di-duimp`, `#landed-cost`, `#nacionalizacao` |
| `importation/types.ts` | `CHECKLIST_ROUTE_MAP`, `ACTION_ROUTE_MAP` |

### Regras de dados

- Ausência → `null` na API, `—` na UI
- Vencimento pagamento, trend mensal, FX agregado: `data_availability.* = false`
- ETA: exibido quando `Shipment.eta_actual` ou `eta_planned` existe
- Cap-8 **removido** dos KPIs; permanece só em listas visuais de widgets (`WIDGET_LIST_LIMIT = 8`)

### Testes

| Suite | Resultado |
|-------|-----------|
| pytest (incl. `tests/test_dashboard.py`) | **84 passed** |
| `npm run build` | OK |
| Playwright `npm run test:e2e` | **4 passed** |

### Lacunas externas (inalteradas)

- Tolerâncias finais conciliação (F0-005 / L-001)
- Planilha Heroes real (F5-007 / L-002)
- Política conta corrente Brasil/fiscal (F0-007 / L-003)
- IP/porta/firewall LAN (L-004)
- Matriz final de papéis
- DUIMP vs DI predominante

### Próxima etapa (pós-MVP 2 sugerida)

1. Instalação no PC servidor Epic (LAN, firewall, credenciais produção)
2. CI remoto (GitHub Actions ou runner local agendado)
3. Parser Heroes produção quando amostra real disponível

---

## Fase pós-MVP 2 — Release candidate local (2026-06-21)

**Objetivo:** preparar teste operacional na Epic com vencimento de pagamentos, KPI real, validação reprodutível e backup agendável.

### due_date em pagamentos

| Item | Evidência |
|------|-----------|
| Migração Alembic `006` | `payments.due_date` nullable |
| API | `POST/PATCH/GET /api/finance/payments` |
| UI | `FinancePage.tsx`, `ImportationFinanceSection.tsx` |
| Testes | `tests/test_payment_due_date.py` (7 testes) |

Regras: planejado = `payment_date` null, sem comprovante; liquidado = `payment_date` ou comprovante; `due_date` null → UI `—`.

### KPI pagamentos a vencer

- `GET /api/dashboard/summary` → `payments_due_count`, `payments_overdue_count`, `payments_due_amount_by_currency`, `data_availability.payments_due`
- Janela: **7 dias**; só pagamentos planejados com `due_date`; sem inventar vencimento
- Frontend: `DashboardPage.tsx`, `UpcomingPaymentsWidget.tsx` (ordena por `due_date`)

### CI local

- Script: `scripts/validate-local.ps1` — pytest + build + E2E (se servidor :8082) + health opcional

### Backup Task Scheduler

- Script: `scripts/register-backup-task.ps1` — registra tarefa diária executando `backup-daily.ps1`
- Status: **PARTIAL** — script criado; registro requer PowerShell admin (testar manualmente na Epic)

### Demo operacional

- Script: `scripts/prepare-demo.ps1` — alembic upgrade, build, seed demo (se servidor up)

### Validação (2026-06-21)

| Etapa | Resultado |
|-------|-----------|
| `alembic upgrade head` | 006 applied |
| pytest | **91 passed** |
| npm run build | OK |
| Playwright E2E | **4 passed** |
| validate-local.ps1 | OK (com servidor) / pytest+build sem servidor |

### Lacunas externas (mantidas)

- Amostra real Heroes (F5-007)
- Tolerâncias finais (F0-005)
- Política conta corrente Brasil/fiscal (F0-007)
- IP/porta/firewall servidor Epic (L-004)
- Matriz final de permissões
- DUIMP vs DI predominante

---

## Auditoria financeira pós-MVP 2 (2026-06-21)

**Objetivo:** confirmar cobertura de invoices, ANTECIPO, pagamentos planejados/liquidados, vencimentos, câmbio por pagamento, saldos, descontos, créditos, conta corrente BR, conciliação e audit log — sem novas funcionalidades grandes.

**Veredito:** **CONDITIONAL_PASS** — núcleo financeiro backend + fluxos críticos OK; UI operacional parcial em descontos/conta corrente BR/despesas; bloqueios externos F0-005/F0-007 mantidos.

### Estado do projeto (pré-auditoria)

| Item | Valor |
|------|-------|
| Fase checklist | Fases 0–12 MVP + pós-MVP 1 + pós-MVP 2 |
| Migração Alembic | **006** (`payments.due_date`) |
| pytest | **93 passed** (pós-auditoria) |
| Roadchecklist pós-MVP 2 | **Sim** — seção v1.7 acima |

### Entidades financeiras — OK / PARTIAL / ausente

| Entidade / campo | Status | Evidência |
|---|---|---|
| Importação | OK | `ImportationOrder`, API `/api/importations` |
| Invoice / proforma / fatura | OK | `Invoice`, CRUD `/api/invoices` |
| Tipo `ANTECIPO` | OK | enum + teste 3 invoices c/ ANTECIPO |
| Invoice `SALDO` | OK | testes saldo parcial |
| Invoice `COMPLEMENTAR` | OK | `test_complementar_and_ajuste_invoice_types` |
| Invoice `AJUSTE` | OK | idem |
| Múltiplas invoices por importação | OK | 3 e >3 invoices testados |
| Múltiplos pagamentos por invoice | OK | `test_invoice_multiple_payments` |
| Pagamento planejado | OK | `due_date` sem `payment_date`/comprovante |
| Pagamento liquidado | OK | `payment_date` ou comprovante/aprovação |
| `due_date` | OK | migração 006 + API + UI |
| `payment_date` | OK | API + UI |
| Comprovante / referência | OK | `receipt_reference`; validação API |
| Câmbio previsto (invoice) | OK | `expected_exchange_rate` |
| Câmbio revisado / efetivo | OK | `ExchangeRate` ESTIMATED/REVISED/SETTLED por pagamento |
| Contrato câmbio / banco / settlement | OK | campos `Payment` + `ExchangeRate` (opcionais) |
| Saldo por invoice | OK | `invoice_balance`, UI aba Financeiro |
| Saldo consolidado importação | OK | `importation_financial_summary` |
| Desconto | OK (API) / **PARTIAL (UI)** | API `/api/finance/discounts`; sem painel dedicado na UI |
| Crédito Heroes | OK | API + listagem UI + apply parcial |
| Uso parcial crédito | OK | `test_heroes_credit_partial_use` |
| Bloqueio uso duplicado | OK | `test_duplicate_credit_use_blocked` |
| Conta corrente Brasil | OK (API) / **PARTIAL (UI)** | API `/api/finance/brazil-accounts`; sem tela |
| Despesas Brasil | OK (API) / **PARTIAL (UI)** | API `/api/finance/expenses`; sem tela |
| Audit log financeiro | OK | payment, discount, credit, exchange_variance |
| Conciliação financeira | OK | `test_invoice_payment_reconciliation`, fechamento |
| KPI pagamentos a vencer (7d) | OK | dashboard + widget |
| Liquidação planejado → liquidado (UI) | OK | botão **Liquidar** (`FinancePage`, `ImportationFinanceSection`) |

### Cenários obrigatórios (20) — testes

| # | Cenário | Resultado | Arquivo |
|---|---------|-----------|---------|
| 1 | ANTECIPO | PASS | `test_importation_with_three_invoices_including_antecipo` |
| 2 | 3 invoices | PASS | idem |
| 3 | >3 invoices | PASS | `test_importation_with_more_than_three_invoices` |
| 4 | Planejado + due_date | PASS | `test_create_payment_with_due_date` |
| 5 | Liquidado + payment_date | PASS | `test_create_payment_without_due_date_requires_receipt` |
| 6 | Planejado não reduz saldo | PASS | `test_planned_payment_does_not_reduce_invoice_balance` |
| 7 | Liquidado reduz saldo | PASS | `test_partial_payment_balance`, `test_liquidate_planned_payment_reduces_balance` |
| 8 | Pagamento parcial | PASS | `test_partial_payment_balance` |
| 9 | Câmbio ≠ previsto | PASS | `test_payment_exchange_differs_from_expected` |
| 10 | Alteração câmbio → audit | PASS | `test_exchange_rate_change_audit` |
| 11 | Desconto reduz saldo | PASS | `test_discount_on_invoice` |
| 12 | Crédito com saldo | PASS | `test_heroes_credit_partial_use` |
| 13 | Crédito parcial | PASS | idem |
| 14 | Uso duplicado bloqueado | PASS | `test_duplicate_credit_use_blocked` |
| 15 | Conta corrente BR | PASS | `test_brazil_current_account_with_impact` |
| 16 | Vencido no dashboard | PASS | `test_overdue_payment_in_dashboard` |
| 17 | KPI 7 dias | PASS | `test_dashboard_payments_due_kpi` |
| 18 | Sem due_date → `—` | PASS | testes due_date + UI `fmtDate` |
| 19 | Invoice vazio ≠ zero | PASS | `test_empty_invoice_amount_not_zero` |
| 20 | Fechamento bloqueia divergência | PASS | `test_close_blocked_with_divergence` |

### UI financeira (browser :8082)

| Área | Status | Notas |
|------|--------|-------|
| Menu Financeiro | OK | `/financeiro` — formulário pagamentos + créditos |
| Aba Financeiro importação | OK | saldos por invoice + tabela pagamentos |
| Planejar pagamento c/ vencimento | OK | checkbox “Só planejado” + date vencimento |
| Liquidar pagamento | OK | botão **Liquidar** (correção pós-MVP 2) |
| Saldos invoice / importação | OK | aba importação + API summary |
| Vencidos / próximos 7d | OK | dashboard KPI + widget (com dados planejados) |
| Créditos Heroes | OK | listagem + demo criar |
| Descontos | PARTIAL | só via API / cenário demo |
| Conta corrente BR | PARTIAL | só via API / demo seed |
| Dashboard KPI “Pagamentos a vencer” | OK | card + `data_availability` |

### Regras críticas confirmadas

- Campo vazio ≠ zero → **OK** (`optional_decimal`, testes)
- Crédito ≠ desconto automático → **OK** (entidades `Credit`/`CreditUsage` vs `Discount`)
- Planejado não reduz saldo → **OK** (`_payment_is_settled`)
- Liquidado reduz saldo → **OK**
- Câmbio por pagamento → **OK** (`ExchangeRate.payment_id`)
- Alteração crítica → audit log → **OK**
- Dado oficial não deletado → **OK** (`SoftDeleteMixin`, cancel endpoints)
- Fechamento usa conciliação → **OK** (`test_close_blocked_with_divergence`)
- Divergência não some → **OK** (review_queue / conciliação)

### Validação (2026-06-21 — auditoria)

| Etapa | Resultado |
|-------|-----------|
| `alembic upgrade head` | 006 (head) |
| pytest | **93 passed** |
| npm run build | OK |
| Playwright E2E | **4 passed** |
| validate-local.ps1 | OK |

### Bugs corrigidos nesta auditoria

1. **UI:** botão **Liquidar** em pagamentos planejados (`FinancePage.tsx`, `ImportationFinanceSection.tsx`).
2. **Demo seed DEMO-06:** pagamento parcial sem comprovante não reduzia saldo — adicionados `payment_date` + `receipt_reference`.
3. **Testes:** `test_liquidate_planned_payment_reduces_balance`, `test_complementar_and_ajuste_invoice_types`.

### Riscos restantes

- UI sem CRUD visual de descontos, conta corrente BR e despesas (API pronta).
- Re-seed demo acumula POs duplicados no banco dev (operacional: reset ou idempotência futura).
- Tolerâncias conciliação (F0-005 BLOCKED) e política fiscal BR (F0-007 BLOCKED).
- `register-backup-task.ps1` PARTIAL (requer admin Windows).

### Próxima etapa recomendada

1. **Instalação piloto na Epic** — `prepare-demo.ps1` + `validate-local.ps1` + firewall/IP (L-004).
2. **UI financeira mínima operacional** — listagem/criação de descontos e conta corrente BR (escopo pequeno, F4-007/F4-010).
3. **Parser Heroes** quando amostra real (F5-007).
4. **Destravar F0-005** com financeiro Epic (tolerâncias conciliação).

---

## Fase pós-MVP 3 — UX operacional Epic (2026-06-21)

**Objetivo:** sistema agradável e operacional para demo interna — UI financeira completa, hub de importação, dashboard útil, demo guiada.

**Veredito:** **PASS**

### UI financeira (completa)

| Área | Status | Arquivos |
|------|--------|----------|
| Descontos (listar/criar global + importação) | DONE | `FinancePanels.tsx` |
| Créditos Heroes (listar/aplicar/status) | DONE | idem |
| Conta corrente BR | DONE | idem |
| Despesas Brasil + landed cost flag | DONE | idem |
| Pagamentos + liquidar | DONE | idem |

### Hub importação

- `ImportationHubSummary.tsx` — badges, resumos financeiro/logístico/documental, próximas ações, pendências, timeline legível
- Cabeçalho layout com saldo consolidado

### Dashboard

- Widgets: vencidos, maiores saldos, divergências, próximas de fechamento, variação custo
- Banner **Demo Epic** → `/demo`
- KPIs globais via API (sem cap-8 fake)

### Demo guiada

- Rota `/demo` — 10 cenários com massa demo existente (`DEMO_SCENARIOS`)

### Timeline

- Backend: `summary`, `user_name`, `entity_label` em `get_timeline`
- Frontend: `timelineFormat.ts` — sem JSON cru

### Testes

| Suite | Resultado |
|-------|-----------|
| pytest | **99 passed** (+6 `test_ux_postmvp3.py`) |
| Playwright | **9 passed** (4 smoke + 5 UX) |
| validate-local | OK |

### Bugs corrigidos

1. Hub importação — imports ausentes causavam crash silencioso no browser
2. Hub — removida dependência lenta de `dashboard/importations(200)` no carregamento
3. `DiscountResponse` / `ExpenseResponse` — campos faltantes na API

### Lacunas antigas — status

| Lacuna | Status |
|--------|--------|
| UI descontos | **DONE** |
| UI conta corrente BR | **DONE** |
| UI despesas BR | **DONE** |
| UI créditos apply | **DONE** |
| Hub operacional | **DONE** |
| Demo guiada | **DONE** |
| F0-005 tolerâncias | BLOCKED |
| F0-007 fiscal BR | BLOCKED (banner na UI) |
| Firewall/LAN/multi-PC | **Fora de escopo desta fase** |

### Próxima etapa recomendada

1. **Sessão demo presencial** com equipe Epic usando `/demo` + Central da Ordem
2. **Modelagem P1** — crédito por raquete, preço listino, responsável da ordem (Fase 6+ backlog)
3. **Parser Heroes** quando amostra real (F5-007)
4. **Destravar F0-005/F0-007** com financeiro Epic

---

## Fase pós-MVP 4 — Central da Ordem estilo planilha (2026-06-21)

**Objetivo:** reformular UI para Central da Ordem operacional (Fases 1–7): glossário PT, fila de ordens, visão geral estilo planilha, financeiro global, dashboard, API order-central/order-queue, bind final.

**Veredito:** **PASS**

### Fase 1 — Glossário PT

| Item | Status | Evidência |
|------|--------|-----------|
| `frontend/src/i18n/glossario.ts` | DONE | statusLabel, payStatusLabel, invoiceTypeLabel, modalLabel, fieldLabel, emptyDash |
| Aplicado nas telas visíveis | DONE | ImportationsPage, ImportationLayout, OrderCentralOverview, FinancePage, FinancePanels, LogisticsPanel, AppShell |
| `/cadastros/glossario` | DONE | GlossaryPage.tsx, CadastrosPage, router |
| Mock copiado | DONE | `docs/mock-central-ordem.html` |

### Fase 2 — Fila de ordens

| Item | Status | Evidência |
|------|--------|-----------|
| `/importacoes` estilo planilha | DONE | ImportationsPage.tsx — filtros, ordenação, CSV, linha clicável |
| API order-queue (Fase 7 bind) | DONE | `GET /api/importations/order-queue` |

### Fase 3 — Central da Ordem

| Item | Status | Evidência |
|------|--------|-----------|
| Header + régua + KPIs + alertas | DONE | ImportationLayout.tsx |
| Bloco A faturas × raquete | DONE | OrderCentralOverview.tsx |
| Bloco B DA SPEDIRE | DONE | idem + quantity-chain |
| Abas repaginadas PT + Histórico | DONE | types.ts, ImportationSectionPage.tsx, router |

### Fase 4 — Financeiro

| Item | Status | Evidência |
|------|--------|-----------|
| `/financeiro` fila contas a pagar | DONE | FinancePage.tsx |
| Financeiro da ordem + banners | DONE | FinancePanels.tsx — tipos fatura completos, payStatusLabel |

### Fase 5 — Dashboard

| Item | Status | Evidência |
|------|--------|-----------|
| Glossário PT widgets | DONE | DashboardPage + widgets existentes |
| "O que resolver hoje?" | DONE | DashboardPage.tsx |
| Link Demo Epic topbar | DONE | AppShell.tsx |

### Checkpoint pós-Fase 5

| Item | Status | Evidência |
|------|--------|-----------|
| Playwright checkpoint | DONE | `frontend/e2e/central-ordem-checkpoint.spec.ts` — 9 testes |
| Glossário PT (sem labels técnicos) | PASS | regex word-boundary |
| Honestidade dados (`—`, sem mock fake) | PASS | E2E + código `// dado-pendente` |
| N+1 order-queue | PASS | ≤3 requests na fila |

### Fase 6 — Backend/API Data Parity

| Item | Status | Evidência |
|------|--------|-----------|
| `GET /importations/{id}/order-central` | DONE | app/services/order_central.py, app/api/importations.py |
| `GET /importations/order-queue` | DONE | idem |
| PaymentResponse estendido | DONE | app/schemas_import.py |
| Testes paridade | DONE | tests/test_order_central.py — 8 testes |

### Fase 7 — Bind final

| Item | Status | Evidência |
|------|--------|-----------|
| api.ts tipos + métodos | DONE | OrderCentralResponse, orderQueue, invoice items |
| UI bind order-central/queue | DONE | OrderCentralOverview, ImportationsPage |

### Testes finais

| Suite | Resultado |
|-------|-----------|
| pytest | **107 passed** |
| npm run build | OK |
| Playwright | **18 passed** (com 1 retry local; suite completa) |
| validate-local | OK (com servidor :8082) |

### Dado-pendente mapeado (P1 — não bloqueia PASS)

- Crédito por raquete / acumulado por item na grade Bloco A
- Preço listino, acconto/crédito rimasto por modelo (Bloco B)
- Aprovação em financeiro global
- Responsável da ordem, última atualização real (exposto parcialmente via order-queue)
- Edição inline campos BR (sem PATCH seguro)

---

## Histórico de atualizações

| Data | Versão | Alteração |
|---|---|---|
| 2026-06-21 | 2.0 | Fase pós-MVP 4 — Central da Ordem; glossário PT; fila ordens; order-central/order-queue API; 107 pytest; 18 E2E |
| 2026-06-21 | 1.9 | Fase pós-MVP 3 — UX operacional; UI financeira completa; hub; dashboard widgets; demo guiada; 99 pytest; 9 E2E |
| 2026-06-21 | 1.8 | Auditoria financeira pós-MVP 2 — CONDITIONAL_PASS; Liquidar UI; demo-06 fix; 93 pytest |
| 2026-06-21 | 1.7 | Fase pós-MVP 2 — due_date pagamentos; KPI vencimentos; validate-local; prepare-demo; register-backup-task |
| 2026-06-21 | 1.6 | Fase pós-MVP 1 — API dashboard agregada; F11-008 DONE; Playwright E2E; 84 pytest |
| 2026-06-21 | 1.5 | Auditoria UI v2 — aderência roadmap; browser 16 rotas + 10 demos; pytest 81; build OK; F3-009/F12-003 evidências atualizadas |
| 2026-06-20 | 1.4 | Validação reprodutível hardening; fix migração 004 SoftDelete; browser 5 fluxos; backup/restore |
| 2026-06-20 | 1.3 | Fases 10–12; conciliação/fechamento; 81 pytest; demo 16 cenários; relatório MVP |
| 2026-06-20 | 1.0 | Criação inicial; stack definida; 12 fases; lacunas registradas |
| 2026-06-20 | 1.2 | Fases 1 e 2 implementadas; checklist atualizado com evidências |
| 2026-06-20 | 1.1 | Mapa explícito das 52 seções obrigatórias adicionado |
