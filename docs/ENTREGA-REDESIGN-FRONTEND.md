# Entrega — Redesign Frontend Epic Importações

Documento de referência da entrega de redesign do frontend React do sistema **Epic Importações**. Descreve o que mudou, por quê, como está organizado e como validar.

> **Escopo:** apenas `frontend/`. O backend (`app/`) **não foi alterado**. Contratos de API existentes foram preservados; apenas adições em `api.ts`.

---

## 1. Resumo executivo

Antes, a aplicação usava um roteador interno baseado em estado (`HomePage.tsx` + `Layout.tsx`): a URL não refletia a tela aberta, não havia deep-link com refresh, e o detalhe da importação dependia de abas horizontais aninhadas.

Depois desta entrega:

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Roteamento | Estado local (`useState` de view) | `react-router-dom` v6 com URLs reais |
| Deep-link | Não (refresh voltava à home) | Sim — SPA fallback do FastAPI já existia |
| Navegação global | Menu claro genérico | Topbar escura fixa (`AppShell`) |
| Detalhe importação | Abas horizontais | Sidebar clara com 8 sub-rotas |
| Aduaneiro / Conciliação | Sub-abas internas | Página scroll única com cards empilhados |
| Home | Texto de boas-vindas | Dashboard com métricas derivadas das APIs |
| Feedback | `.meta` inline / texto estático | Toasts + `LoadingState` / `Spinner` |
| Design | CSS ad hoc | Tokens CSS + biblioteca de componentes |

---

## 2. Arquitetura de rotas

```
/login                          → Login (público)

/                               → DashboardPage
/importacoes                    → Lista de importações
/importacoes/:id                → redirect → /importacoes/:id/resumo
/importacoes/:id/resumo
/importacoes/:id/itens
/importacoes/:id/invoices
/importacoes/:id/financeiro
/importacoes/:id/documentos
/importacoes/:id/logistica
/importacoes/:id/aduaneiro
/importacoes/:id/conciliacao

/skus                           → Produtos / SKUs
/financeiro                     → Financeiro global
/documentos                     → Documentos global
/revisao                        → Fila de revisão
/heroes                         → Upload Heroes
```

### Hierarquia de layouts

```
App (AuthProvider + ToastProvider)
└── AppRouter
    ├── /login → LoginRoute
    └── ProtectedRoute (redireciona se !user)
        └── AppShell (topbar escura + Outlet)
            ├── páginas globais
            └── ImportationLayout (header PO + sidebar + Outlet)
                └── ImportationSectionPage (conteúdo por seção)
```

**Deep-link:** o FastAPI em `app/main.py` já devolve `index.html` para paths que não começam com `api`. Após `npm run build`, refresh em `/importacoes/4/invoices` funciona sem mudança no backend.

---

## 3. Etapas da entrega (detalhamento)

### Etapa 1 — Migração para react-router-dom

**Objetivo:** URLs compartilháveis, histórico do browser, auth gate centralizado.

**Arquivos criados:**

| Arquivo | Função |
|---------|--------|
| `frontend/src/router.tsx` | Definição de todas as rotas |
| `frontend/src/layouts/ProtectedRoute.tsx` | Gate de autenticação |
| `frontend/src/layouts/AppShell.tsx` | Shell global (inicialmente simples; refinado na Etapa 3) |
| `frontend/src/context/AuthContext.tsx` | Estado de usuário + `login` / `logout` |
| `frontend/src/pages/importation/ImportationLayout.tsx` | Layout do detalhe |
| `frontend/src/pages/importation/ImportationSectionPage.tsx` | Conteúdo por seção |
| `frontend/src/pages/importation/types.ts` | Tipos e constantes compartilhadas |

**Arquivos removidos:**

- `frontend/src/HomePage.tsx` — roteador por estado
- `frontend/src/Layout.tsx` — layout antigo
- `frontend/src/pages/ImportationDetailPage.tsx` — monolito com abas

**Alterações:**

- `main.tsx` — envolve app com `BrowserRouter`
- `App.tsx` — `AuthProvider` + `AppRouter` (sem lógica de view)
- `LoginPage.tsx` — após login, `navigate("/")` em vez de callback
- Páginas de lista — `onOpen(id)` trocado por `navigate(...)` / `Link`

**Checkpoint A:** `npm run build` + login, lista, detalhe, refresh em sub-rota, redirect sem sessão.

---

### Etapa 2 — Design system (tokens + componentes)

**Objetivo:** base visual consistente sem migrar todas as telas de uma vez.

**Tokens em `frontend/src/index.css`:**

- Cores: primary `#2563eb`, texto, superfície, topbar `#1e293b`, sidebar
- Espaçamento: 4 / 8 / 12 / 16 / 24 / 32 px
- Radius, sombras, tamanhos de fonte
- Classes legadas (`.card`, `.nav-link`, `.data-table`) mantidas como aliases para compatibilidade

**Componentes em `frontend/src/components/`:**

| Componente | Variantes / props principais |
|------------|------------------------------|
| `Button` | `primary`, `secondary`, `ghost`, `danger`; `loading`, `disabled`; `type` (incl. `submit`) |
| `Badge` | `tone` ou `status` → `statusToTone()` |
| `Card` | `title?`, `compact`, `id` (âncoras) |
| `Table` | wrapper zebra + hover |
| `PageHeader` | `title`, `subtitle?`, `actions?` |
| `EmptyState` | `title`, `description?` |
| `Spinner` / `LoadingState` | tamanho sm/md; label customizável |
| `ToastProvider` / `useToast` | `success`, `error`, `info` |

**Mapa `statusToTone` (Badge):**

| Tom | Status típicos |
|-----|----------------|
| `neutral` | `PO_CREATED`, `ON_HOLD`, rascunho |
| `info` | `BOOKED`, `SHIPPED`, `IN_TRANSIT`, `ARRIVED`, operacional |
| `warning` | `PENDING`, `OPEN`, `DIVERGENT` |
| `success` | `CLOSED`, `CLEARED`, `OK`, `FULL_PAID` |
| `danger` | `CANCELLED`, `REJECTED`, bloqueante |

Export barrel: `frontend/src/components/index.ts`.

---

### Etapa 3 — Hierarquia visual de navegação

**Topbar global escura** (`AppShell.tsx`):

- Fundo `--color-topbar-bg`, links `--color-topbar-muted`, ativo com accent primary
- Esquerda: "Epic Importações — {user.name}" + `Badge` com role
- Direita: Dashboard, Importações, SKUs, Financeiro, Documentos, Revisão, Heroes, Sair
- `NavLink` do react-router para estado ativo (substitui `.nav-active` manual)

**Conteúdo principal:** área `app-main` full-width; páginas usam `Card` branco com sombra tokenizada.

A sidebar clara do detalhe fica restrita ao `ImportationLayout` (Etapa 4), criando contraste visual entre navegação global e navegação contextual.

---

### Etapa 4 — Detalhe da importação com sidebar

**`ImportationLayout.tsx`:**

1. Carrega dados compartilhados uma vez: importação, itens, invoices, resumo financeiro, documentos
2. Expõe via `Outlet` context (`ImportationOutletContext`) — evita refetch duplicado em cada seção
3. Header fixo: Voltar → `/importacoes`, H1 com PO, `Badge` status, moeda · incoterm
4. Sidebar (~220px) com grupos:

| Grupo | Itens |
|-------|-------|
| Visão geral | Resumo, Itens, Invoices, Financeiro |
| Operação | Logística, Aduaneiro |
| Fechamento | Conciliação, Documentos |

5. Cada item é `NavLink` → `/importacoes/:id/{secao}`; ativo = borda esquerda primary + fundo leve

**`ImportationSectionPage.tsx`:** switch por `section` reutilizando painéis existentes (`LogisticsPanel`, `CustomsStockPanel`, `ReconciliationClosurePanel`).

**Checkpoint B:** build + navegação sidebar + refresh em sub-rota + Voltar.

---

### Etapa 5 — Sub-abas achatadas

#### `CustomsStockPanel.tsx` (Aduaneiro)

Removido state de sub-abas. Quatro `Card`s empilhados com IDs de âncora:

| ID | Conteúdo |
|----|----------|
| `#di-duimp` | Documentos aduaneiros (DI/DUIMP) |
| `#impostos` | Impostos |
| `#nacionalizacao` | Nacionalização / estoque |
| `#landed-cost` | Landed cost e versões |

Barra de âncoras no topo (`anchor-nav`) para scroll interno.

#### `ReconciliationClosurePanel.tsx` (Conciliação)

Três cards empilhados:

| ID | Conteúdo |
|----|----------|
| `#conciliacao` | Lista + botão executar conciliação |
| `#fechamento` | Checklist + fechar importação |
| `#timeline` | Histórico e timeline |

---

### Etapa 6 — Dashboard operacional

**`frontend/src/pages/DashboardPage.tsx`** + hook **`useDashboardMetrics.ts`**.

Métricas calculadas no frontend (sem novos endpoints):

| Card | Fonte API | Lógica |
|------|-----------|--------|
| Importações abertas | `importationsApi.list()` | `current_status !== "CLOSED"`; top 5 com link |
| Aguardando documento | `importsApi.reviewQueue()` + checklist | fila revisão + proforma falha na amostra |
| Com divergência | `reconciliationApi.list(id)` | `DIVERGENT` ou severity `BLOCKING` |
| Próximas desembaraço | list + `customsApi.listDocuments(id)` | `ARRIVED`/`IN_TRANSIT` sem doc `OFFICIAL` |
| LC estimado vs realizado | `financeApi.summary` implícito via `estimated_total` + `landedCostApi.listVersions` | comparar estimado vs `total_cost` atual |

**Cap de performance:** cards que fazem N+1 usam no máximo **8 importações abertas mais recentes** (`created_at` desc). Constante `METRICS_CAP = 8` em `useDashboardMetrics.ts`.

**Card LC:** omitido (`hasLcCard === false`) se nenhuma importação da amostra tiver dados comparáveis.

Rodapé: `healthApi.check()` → linha `Health: ok / DB: ...`.

---

### Etapa 7 — Polish de listas e feedback

**`ImportationsPage.tsx`:**

- Busca por PO ou nome do fornecedor (`suppliersApi.list()` → map)
- Paginação via `usePagination(items, 10)`
- `Table`, `Badge`, `PageHeader`, `EmptyState`, `LoadingState`
- Toasts em create / erro

**`DocumentsPage.tsx`:**

- Zona drag-and-drop com highlight (`drop-zone--active`)
- `<input type="file">` hidden como fallback
- Toasts no upload

**Demais:**

- `ProtectedRoute`, `LoginRoute`, gates de auth → `LoadingState`
- `LoginPage` → `Card` + `Button` com loading
- `ImportationSectionPage` → `Table`, `Button`, `useToast` nas ações
- `ToastProvider` no root (`App.tsx`)

**Hook:** `frontend/src/hooks/usePagination.ts` — page, totalPages, pageItems, goTo, resetPage.

---

### Etapa 8 — UX de fechamento / reabertura

**Em `ReconciliationClosurePanel` (card Fechamento):**

Checklist visual com ícones:

- ✓ verde — item aprovado
- ✗ vermelho — bloqueante
- ⚠ âmbar — `blocking_count > 0` em reconciliations mesmo com `passed`

Links de pendência (`CHECKLIST_ROUTE_MAP` em `types.ts`):

| id checklist | Rota destino |
|--------------|--------------|
| `invoices` | `/importacoes/:id/invoices` |
| `finance` | `/importacoes/:id/financeiro` |
| `customs` | `/importacoes/:id/aduaneiro#di-duimp` |
| `proforma` | `/importacoes/:id/documentos` |
| `landed_cost` | `/importacoes/:id/aduaneiro#landed-cost` |
| `nationalization` | `/importacoes/:id/aduaneiro#nacionalizacao` |
| `reconciliations` | `/importacoes/:id/conciliacao#conciliacao` |

- Botão **Fechar importação:** `disabled` se houver bloqueante; `title` com labels falhos
- Modal **Reabrir:** select `reason_code` filtrado `category === "reabertura"` + textarea justificativa

**Adição em `api.ts` (permitida, não breaking):**

```typescript
export interface ReasonCode { ... }
export const usersApi = {
  listReasonCodes: () => api<ReasonCode[]>("/api/users/reason-codes"),
};
```

---

## 4. Mapa de arquivos

### Criados

```
frontend/src/
├── router.tsx
├── context/AuthContext.tsx
├── layouts/
│   ├── AppShell.tsx
│   └── ProtectedRoute.tsx
├── components/
│   ├── Badge.tsx
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── EmptyState.tsx
│   ├── PageHeader.tsx
│   ├── Spinner.tsx
│   ├── Table.tsx
│   ├── ToastProvider.tsx
│   └── index.ts
├── hooks/
│   ├── usePagination.ts
│   └── useDashboardMetrics.ts
└── pages/
    ├── DashboardPage.tsx
    └── importation/
        ├── ImportationLayout.tsx
        ├── ImportationSectionPage.tsx
        └── types.ts
```

### Alterados (principais)

- `main.tsx`, `App.tsx`, `LoginPage.tsx`
- `index.css` — tokens + estilos topbar, sidebar, dashboard, toast, modal, drop-zone, checklist
- `api.ts` — `ReasonCode`, `usersApi`
- `ImportationsPage.tsx`, `DocumentsPage.tsx`
- `CustomsStockPanel.tsx`, `ReconciliationClosurePanel.tsx`

### Removidos

- `HomePage.tsx`
- `Layout.tsx`
- `pages/ImportationDetailPage.tsx`

---

## 5. Fluxo de autenticação

```
1. App monta → AuthProvider chama authApi.me()
2. loading=true → LoadingState
3. !user → ProtectedRoute redireciona /login
4. Login → authApi.login → setUser → navigate("/")
5. Logout → authApi.logout → setUser(null) → navigate("/login")
```

Cookie HTTP-only do backend permanece inalterado.

---

## 6. Validação

### Automatizada (executada na entrega)

```bash
cd frontend && npm run build    # ✓ sem erros TypeScript
pytest tests/ -v                # ✓ 81 passed
```

### Manual recomendada

```bash
# Subir API (exemplo)
uvicorn app.main:app --port 8082

# Seed demo
curl -X POST http://localhost:8082/api/demo/seed

# Login: admin@epic.com.br / admin123
```

| # | Teste | Esperado |
|---|-------|----------|
| 1 | Login | Redireciona para `/` (dashboard) |
| 2 | `/importacoes` | Lista com busca e paginação |
| 3 | Abrir `DEMO-04-3INV` | URL `/importacoes/:id/resumo`, header PO visível |
| 4 | Clicar cada item sidebar | URL muda, conteúdo carrega |
| 5 | Refresh `/importacoes/:id/aduaneiro` | Sidebar ativa correta |
| 6 | Aduaneiro | 4 cards empilhados, âncoras funcionam |
| 7 | Conciliação | Checklist com links; fechar/reabrir |
| 8 | Documentos global | Drag-and-drop upload |
| 9 | Sem sessão | Redirect `/login` |
| 10 | Dashboard | Cards métricas; health no rodapé |

---

## 7. Decisões e limitações

| Tópico | Decisão |
|--------|---------|
| Backend | Zero alterações — SPA fallback já existia |
| Dashboard N+1 | Cap fixo de 8 importações abertas |
| Dados compartilhados no detalhe | `Outlet` context no layout, não Context API separado |
| i18n | Status da API permanecem em EN (`PO_CREATED`, etc.); Badge colore visualmente — ver comentários `// i18n-todo` onde aplicável |
| Telas secundárias | `FinancePage`, `ProductsPage`, `ReviewQueuePage`, `HeroesUploadPage` mantêm layout anterior parcial; polish principal em Importações, Documentos, Detalhe |
| Card LC dashboard | Omitido quando não há pares estimado/LC na amostra |

---

## 8. Mock visual

Para visualizar a hierarquia de layout **sem subir o app**, abra no browser:

**[`docs/mock-redesign-ui.html`](./mock-redesign-ui.html)**

O mock é estático (HTML + CSS inline) e ilustra:

1. Topbar escura global
2. Dashboard com grid de cards
3. Detalhe com sidebar clara e conteúdo empilhado
4. Paleta de tokens usada no redesign

---

## 9. Próximos passos sugeridos (fora desta entrega)

- Migrar `FinancePage`, `ProductsPage`, `ReviewQueuePage` para componentes do design system
- Lazy load no dashboard além das 8 importações (scroll infinito)
- Tradução de labels de status (`i18n`)
- Testes E2E (Playwright) para deep-link e checklist de fechamento

---

*Documento gerado em referência à entrega "Redesign Frontend — Epic Importações". Backend e contratos de API permanecem estáveis.*
