# Auditoria UX/UI — EPIC Controle V2 (frontend)

Data da auditoria: 2026-08-03
Auditor: agente de leitura (somente análise, nenhum arquivo do projeto foi modificado)

## Aviso de mapeamento — divergência da hipótese inicial

O prompt original assumia um stack com **Tailwind CSS** (`tailwind.config.*`, classes utilitárias). Isso **não existe neste projeto**. O frontend V2 é:

- **Caminho:** `v2/frontend/`
- **Stack:** Vite + React 18 + TypeScript + React Router. Sem Tailwind, sem Ant Design, sem shadcn/ui, sem nenhuma lib de UI de terceiros.
- **Estilo:** um único arquivo CSS global (`v2/frontend/src/index.css`, 1601 linhas) implementando um **design system próprio baseado em CSS custom properties (design tokens)**, consumido por componentes React em `v2/frontend/src/ui/*.tsx`.
- Não existem arquivos `theme.ts`, `tokens.ts` ou `colors.ts` separados — os tokens vivem todos no `:root` de `index.css` (linhas 7–76).
- Não existem arquivos com comentários/nomes `SCR-003`/`SCR-006`/`SCR-008`/`SCR-010`. Apenas `SCR-009` aparece, em `index.css:45` (`--fx-columns-stack-viewport-max`) e em código de features (`apQueueColumns.tsx`, `invoicesQueueColumns.tsx`, `ordersQueueColumns.tsx`, `paymentsQueueColumns.tsx`, `PayableFxPage.tsx`, `api/generated/*`), como referência de rastreamento de requisito, não como nome de arquivo.
- `AppShell`, `FilterBar` e `OperationalTable` existem exatamente com esses nomes em `v2/frontend/src/app-shell/AppShell.tsx`, `v2/frontend/src/ui/FilterBar.tsx` e `v2/frontend/src/ui/OperationalTable.tsx`.

Conclusão prática: a auditoria abaixo foi replanejada para avaliar o sistema de tokens CSS + componentes React reais, em vez de configuração Tailwind (inexistente).

---

## A) Paleta de cores

**Estado atual**
- Sistema de tokens semânticos coerente em `:root` (`index.css:11-32`): `--color-canvas`, `--color-surface`, `--color-sidebar`, `--color-text`, `--color-muted`, `--color-accent`, `--color-accent-wash`, cores de status (`success/warning/danger`) com par bg/fg, e bordas em 3 níveis (`interactive`, `decorative`, `hair`).
- Zero cores hardcoded em componentes `.tsx` (confirmado via busca por `#[0-9a-f]{3,6}` em todo `src/**/*.tsx` — nenhuma ocorrência). Toda cor de UI passa por `var(--color-*)`.
- Existem "legacy aliases" (`--bg`, `--panel`, `--text`, `--muted`, `--accent`, `--border`, linhas 67-73) mapeados para os tokens semânticos, mantidos para compatibilidade com classes antigas (`.panel`, `.login-form`) — dívida técnica já documentada no próprio arquivo (linha 2-4).
- Contraste WCAG AA (4.5:1) verificado por cálculo de luminância relativa nos pares mais usados:
  - `--color-muted` (#5b6b7c) sobre `--color-surface` (#fff): **5.46:1** — passa AA.
  - `--color-sidebar-muted` (#9aa8b8) sobre `--color-sidebar` (#1b2a41): **5.97:1** — passa AA.
  - `--color-accent` (#1f4e79) sobre branco: **8.67:1** — passa AAA.
  - `--color-warning-fg`/`--color-warning-bg`: **4.99:1** — passa AA, margem apertada.
  - `--color-success-fg`/`--color-success-bg`: **5.08:1** — passa AA, margem apertada.
- Não há dark mode / `prefers-color-scheme` — `color-scheme: light` fixo (`index.css:8`).

**Problema identificado**
- Nenhum problema crítico de contraste. O ponto fraco é a **duplicação de sistema** (tokens novos + aliases legados coexistindo), o que cria ambiguidade sobre qual classe usar em código novo (`.panel`/`.login-form` vs. componentes do design system em `ui/`).
- Cores de status warning/success estão com margem de contraste apertada (~5:1); qualquer escurecimento futuro do bg quebra AA.

**Recomendação**
- Depreciar formalmente os aliases legados (`--bg`, `--panel`, `--text`, `--muted`, `--accent`, `--border`) com um prazo, migrando `.panel`/`.login-form` para os componentes `ui/*` existentes.
- Não alterar bg de warning/success sem reverificar contraste (ferramenta: WebAIM Contrast Checker).

**Comparação honesta com Ant Design 5 / shadcn/ui**
- Estruturalmente (tokens semânticos, bg/fg pareados por status) está **conceitualmente alinhado** com o modelo de tokens do Ant Design 5 (`colorPrimary`, `colorSuccessBg`, etc.) e do shadcn/ui (CSS vars `--primary`, `--destructive`).
- Visualmente está **mais próximo do Ant Design 5** (paleta azul-acinzentada corporativa, bordas visíveis, sem gradientes) do que do shadcn/ui (que tende a neutros mais frios e uso de sombra/blur). Não há paridade de contraste dinâmico nem paleta gerada algoritmicamente (Ant Design gera 10 tons por cor via `@ant-design/colors`); aqui os tons são fixos e escritos à mão.

---

## B) Tipografia

**Estado atual**
- Família: `--font-ui: "Segoe UI", system-ui, -apple-system, Calibri, Arial, sans-serif` (`index.css:34`) — **fonte de sistema**, sem Google Fonts nem fonte custom. Confirmado: `index.html` não carrega nenhum `<link>` de fonte externa.
- Fonte mono: `ui-monospace, "Cascadia Mono", Consolas, monospace` — usada em `.id-ref` e `.mono`.
- Escala tipográfica existe, mas é **implícita e dispersa**, não nomeada como h1–h6:
  - `--font-size-title: 22px` (títulos de página, `.page-header h1`, `.panel h1`)
  - `--font-size-body: 14px`, `--font-size-secondary: 13px`, `--font-size-meta: 12px`, `--font-size-label: 11px`, `--font-size-micro: 10.5px`
  - Fora da escala tokenizada: `.login-form h1` usa `1.75rem` (28px) hardcoded — **diferente** do `--font-size-title` (22px) usado no resto do app.
  - `.drawer-header h2` (1.1rem/17.6px), `.section-card-title` (0.95rem/15.2px), `.cockpit-grid h2` (1rem/16px) — cada um com valor próprio não tokenizado.
- `line-height`: definido pontualmente (`.login-form h1` não define; `.detail-shell .page-header h1` define `1.25`; hints/subtítulos definem `1.35`/`1.4`), mas a maioria do corpo de texto (`body`, `td`, `.data-table`) **não define line-height**, herdando o padrão do navegador (~1.2, apertado para 14px em tabelas densas).
- `letter-spacing`: usado só em pontos específicos — títulos (`-0.02em` no h1 do login) e labels uppercase (`0.04em`–`0.06em` em `.nav-group-title`, `.summary-grid-item dt`). Não sistemático.

**Problema identificado**
- Escala tipográfica não é uma "escala" no sentido formal (razão fixa entre níveis); são 6 tamanhos de corpo + 3-4 tamanhos de título definidos ad hoc, com pelo menos uma inconsistência clara (h1 do login em 28px vs. h1 do app em 22px).
- Ausência de `line-height` de base para o `body` deixa textos de 12-14px com respiro vertical inferior ao recomendado (WCAG 1.4.12 sugere ≥1.5 para parágrafos; aqui fica no padrão do browser).
- 100% fonte de sistema é uma escolha legítima (rápida, sem FOUT, nativa no SO) — não é um problema em si, mas distancia visualmente do "look" de produto que geralmente usa uma fonte com personalidade (Inter, no caso do shadcn/ui).

**Recomendação**
- Definir `--line-height-body: 1.45` (ou similar) no `body` e reutilizar nos textos de tabela/formulário.
- Unificar `.login-form h1` para `var(--font-size-title)` ou criar um token `--font-size-h1-page: 22px` versus `--font-size-h1-auth: 28px` explícito, deixando claro que é intencional (hoje parece esquecimento).
- Se o objetivo é aproximar de shadcn/ui, considerar trocar `--font-ui` para incluir `Inter` como primeira opção com fallback de sistema — baixo custo, alto ganho de percepção "produto moderno".

---

## C) Campos de entrada (input, select, textarea, datepicker, checkbox, radio)

**Estado atual**
- Componentes React dedicados e consistentes: `TextInput`, `SelectField`, `DateInput`, `MoneyInput`, `RateInput` — todos usam a classe base `.ds-input`/`.ds-select` (`index.css:681-727`).
- **Border-radius:** `--radius-control: 4px` (`index.css:48`) — aplicado uniformemente via token.
- **Padding:** **inconsistente entre contextos** — três valores diferentes para "a mesma coisa":
  - `.ds-input`/`.ds-select` (design system atual): `0.35rem 0.55rem` (`index.css:689`)
  - `.panel input, .panel select` (legado): `0.55rem 0.75rem` (`index.css:280`)
  - `.login-form input` (legado): `0.7rem 0.8rem` (`index.css:154`)
- **Focus state:** bem implementado — `outline: 2px solid var(--color-focus); outline-offset: 1px` em `.ds-input:focus-visible`/`.ds-select:focus-visible` (`index.css:710-716`), mais um `:focus-visible` global (`index.css:93-96`) como fallback.
- **Hover:** `.ds-input:hover:not(:disabled)` muda `border-color` para `--color-accent` (`index.css:703-708`).
- **Disabled:** `opacity: 0.55; cursor: not-allowed; background: var(--color-draft-bg)` (`index.css:718-723`).
- **Error/invalid:** classe `.ds-input--invalid` muda a borda para `--color-danger-fg` (`index.css:725-727`); a mensagem de erro é renderizada separadamente pelo componente `FormField` (`role="alert"`).
- **Checkbox/radio:** **sem nenhuma estilização própria.** Buscando `type="checkbox"`/`type="radio"` no código, aparecem apenas em 3 arquivos de feature (`ShipmentLogisticsPanels.tsx`, `InvoiceDetailPage.tsx`, `PaymentCreatePage.tsx`), todos usando o `<input>` nativo do navegador sem classe `.ds-*` e sem `accent-color` definido em `index.css`.
- **Textarea:** não há componente `Textarea` dedicado nem regra CSS própria — não localizado no design system atual.

**O que está faltando vs. padrão profissional moderno**
- Checkbox/radio ficam com a aparência default do SO (azul do Chrome/cinza do Edge), quebrando a consistência visual do resto do formulário — o único ponto onde o "sistema" trinca visivelmente.
- Sem componente/estilo de `Textarea` — se alguma feature precisar de texto longo, corre o risco de reinventar ad hoc.
- Sem estado de "read-only" visualmente diferenciado de "editável".
- Sem `Select` custom com dropdown estilizado (usa `<select>` nativo com seta customizada via `background-image`, o que é uma solução legítima e leve, mas limita customização de largura da lista de opções, que segue o SO).

**Recomendação**
- Migrar `.panel input/select` e `.login-form input` para as classes `.ds-input`/`.ds-select` (ou trocar os elementos nativos pelos componentes `TextInput`/`SelectField`), eliminando os 3 paddings divergentes.
- Adicionar `input[type="checkbox"], input[type="radio"] { accent-color: var(--color-accent); width: 16px; height: 16px; }` — 1 linha, resolve o ponto mais visível de inconsistência.

---

## D) Botões

**Estado atual**
- Componente único `Button.tsx` com variantes `primary` (default), `secondary`, `ghost`, `danger`, e tamanhos `md`/`lg` (`Button.tsx:3-4`).
- `disabled` e `busy` (loading) implementados: `disabled={disabled || busy}`, `aria-busy`, com CSS correspondente `.btn:disabled` (opacity 0.55) e `.btn[aria-busy="true"]` (opacity 0.75, `cursor: progress`) — **sem spinner visual**, apenas mudança de opacidade e cursor.
- Sizing consistente: todos os botões herdam `--button-height-md` (32px) ou `--button-height-lg` (36px) via token, usado em várias páginas.

**Problema identificado**
- **Nenhum estado de `:hover` definido para nenhuma variante de botão** (`.ui-button`, `.ui-button--secondary`, `.ui-button--ghost`, `.ui-button--danger`) — busca confirma zero regras `:hover` associadas a botões em `index.css`. O único feedback ao passar o mouse é o `cursor: pointer` herdado do `.btn`. Isso é uma lacuna de usabilidade perceptível em qualquer clique.
- Loading state (`busy`) não tem indicador visual de progresso (spinner/ícone), só opacidade — usuário pode não perceber que uma ação está em andamento, especialmente em conexões lentas.
- Não existe variante `link` (mencionada como padrão de mercado) — existe uma classe separada `.row-link` para links de tabela, mas não como variante de `Button`.

**Recomendação**
- Adicionar hover para as 4 variantes, ex.: `.ui-button:hover:not(:disabled) { filter: brightness(0.92); }` ou trocar `background` por um tom levemente mais escuro via `color-mix()` (já usado em outras partes do CSS, ex. linha 977, 986, 1082).
- Adicionar um spinner simples (borda animada) no estado `busy`, reaproveitando os `::after` do botão.

---

## E) Layout e espaçamento

**Estado atual**
- Sem Tailwind — não há "escala Tailwind" a avaliar. O espaçamento é feito com valores `rem` majoritariamente múltiplos de `0.25rem`/`0.35rem`/`0.5rem` (ex.: `gap: 0.5rem`, `0.75rem`, `1rem`, `1.25rem`), mas **não é uma escala tokenizada** (não existem `--space-1`, `--space-2`, etc.) — cada regra escreve o valor em rem diretamente. Não chega a ser caótico (a maioria dos valores é consistente entre si), mas não há garantia estrutural contra "valores mágicos" novos.
- Densidade de tabelas operacionais é tratada como token de primeira classe: `--table-row-standard: 40px` e `--table-row-finance: 44px` (`index.css:54-55`), aplicadas via classes `.density-standard`/`.density-finance` em `OperationalTable.tsx`. Isso é um ponto forte — densidade é intencional e nomeada, não acidental.
- Existe também `.data-table.dense` (padding reduzido) como variante adicional mais antiga, coexistindo com o sistema `.operational-table` novo — duas soluções de densidade em paralelo (dívida técnica, mesma raiz da divisão "legacy vs. target" já citada na seção A).
- Largura máxima de página tokenizada por contexto: `--page-max-form: 1120px`, `--page-max-detail: 1440px`, `--page-max-queue: 1680px` — bom sinal de sistema pensado por tipo de tela.
- Sidebar: fixa em 220px expandida / 56px em modo compacto (`--shell-sidebar-width`, `--shell-sidebar-rail`), com colapso automático via media query em `max-width: 1100px` (`index.css:1192`) escondendo labels de texto (clip via classe utilitária de "visually hidden").
- Header: não há um header horizontal fixo — o app usa sidebar-only layout (`.shell-sidebar-layout`); existe CSS legado de `.shell-header` marcado explicitamente como "legado inerte (sem JSX atual)" (`index.css:184`), ou seja, código morto documentado.

**Problema identificado**
- CSS morto conhecido (`.shell-header`, linha 184-192) ainda no bundle de produção — aumenta o CSS enviado ao navegador sem uso.
- Dois sistemas de tabela (`.data-table` antigo vs. `.operational-table` novo) aumentam a superfície de manutenção.
- Espaçamento sem tokens nomeados dificulta auditoria futura (não há como buscar "todos os usos de space-lg", por exemplo).

**Recomendação**
- Remover `.shell-header` e seletores relacionados após confirmar via grep (o próprio comentário já pede isso).
- Tokenizar ao menos 4-5 níveis de espaçamento (`--space-xs: 0.35rem`, `--space-sm: 0.5rem`, `--space-md: 0.75rem`, `--space-lg: 1rem`, `--space-xl: 1.5rem`) e migrar gradualmente — não bloqueante, mas melhora manutenibilidade.

---

## F) Sombras e elevação

**Estado atual**
- **Apenas uma única regra `box-shadow` em todo o arquivo CSS** (`index.css:1273`): o painel `.filter-bar-more-panel` (dropdown "Mais filtros") usa `box-shadow: 0 8px 24px var(--color-drawer-shade)`.
- Também há um `box-shadow` como *ring* de foco em `.kpi-card--action:focus-visible` (`index.css:651`) — não é elevação, é indicador de foco.
- **Cards, painéis, modais e drawers não têm sombra nenhuma**: `.panel`, `.section-card`, `.kpi-card`, `.notice`, `.alert-list`, `.drawer-panel` (usado tanto pelo `DetailDrawer` quanto pelo `ConfirmationModal`) dependem exclusivamente de `border: 1px solid var(--color-border-decorative)` para se separar do fundo.
- O `drawer-backdrop` (fundo escurecido atrás de modal/drawer) existe (`rgba` semitransparente), mas o painel do drawer/modal em si **flutua sem nenhuma sombra própria** — só a borda esquerda (`border-left`) o separa do conteúdo por trás, o que é insuficiente para comunicar "isto está acima de tudo" numa camada modal.

**Problema identificado**
- Tudo é essencialmente plano (flat design via bordas), sem hierarquia de profundidade. Isso é uma escolha de design válida (Ant Design em modo "borderless" também é assim em alguns componentes), mas **modal e drawer sem sombra é uma lacuna real**, não uma escolha estética: são elementos que sobrepõem conteúdo e usuários esperam uma pista visual de "camada acima" além do backdrop.
- Dropdown de filtros (`.filter-bar-more-panel`) é o único elemento com sombra — cria inconsistência: por que só ele tem elevação e o modal de confirmação não?

**Recomendação**
- Adicionar tokens de elevação, ex.: `--shadow-sm: 0 1px 2px rgba(16,24,32,.06); --shadow-md: 0 4px 12px rgba(16,24,32,.12); --shadow-lg: 0 12px 32px rgba(16,24,32,.18)`.
- Aplicar `--shadow-lg` em `.drawer-panel` (modal e drawer) e `--shadow-sm` opcionalmente em `.kpi-card`/`.section-card` para dar leve destaque sem pesar o visual denso das telas operacionais.

---

## Tabela de prioridades

| Item | Impacto (1-3) | Esforço (1-3) | Arquivo afetado |
|---|---|---|---|
| Botões sem `:hover` em todas as variantes | 3 | 1 | `v2/frontend/src/index.css` |
| Modal/Drawer sem `box-shadow` (elevação) | 3 | 1 | `v2/frontend/src/index.css` |
| Checkbox/radio sem estilo (`accent-color`) | 3 | 1 | `v2/frontend/src/index.css` |
| 3 paddings diferentes para input em contextos distintos | 2 | 2 | `v2/frontend/src/index.css` |
| `.login-form h1` fora da escala tipográfica (28px vs 22px) | 1 | 1 | `v2/frontend/src/index.css` |
| Sem `line-height` de base para corpo/tabela | 2 | 1 | `v2/frontend/src/index.css` |
| Loading state de botão sem spinner visual | 2 | 2 | `v2/frontend/src/ui/Button.tsx`, `index.css` |
| CSS morto `.shell-header` (marcado como legado inerte) | 1 | 1 | `v2/frontend/src/index.css` |
| Dois sistemas de tabela em paralelo (`.data-table` vs `.operational-table`) | 2 | 3 | `v2/frontend/src/index.css`, features que ainda usam `.data-table` |
| Sem componente `Textarea` dedicado | 1 | 2 | `v2/frontend/src/ui/` |
| Aliases legados de cor coexistindo com tokens novos | 1 | 3 | `v2/frontend/src/index.css` |
| Sem tokens de espaçamento nomeados | 1 | 3 | `v2/frontend/src/index.css` |

---

## Nota sobre "componentes com problemas graves"

O escopo original da tarefa pedia para copiar, com sufixo `_AUDITADO`, componentes com "sem focus state, sem disabled state, cores hardcoded extensivas". **Nenhum componente do design system atual (`v2/frontend/src/ui/*.tsx`) se enquadra nesse critério estrito**: todos os inputs/botões auditados têm focus state (via `:focus-visible` global + regras específicas), disabled state implementado, e não há cores hardcoded em nenhum `.tsx`. Por isso, nenhuma cópia `_AUDITADO` de componente foi feita — os problemas reais encontrados (hover ausente em botões, falta de sombra em modais, checkbox nativo) são lacunas de polish, não ausência de estado básico, e estão descritos acima com recomendação concreta.
