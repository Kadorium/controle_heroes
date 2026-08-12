# Quick Wins — Impacto 3 / Esforço 1

Todos os itens abaixo são mudanças em um único arquivo (`v2/frontend/src/index.css`), sem tocar em componentes React, sem risco de quebrar lógica, com efeito visual imediato em todo o app.

---

## 1. Botões sem feedback de `:hover`

**Problema:** nenhuma variante de botão (`primary`, `secondary`, `ghost`, `danger`) muda de aparência ao passar o mouse. O único feedback é o `cursor: pointer`. Em qualquer app profissional isso é o mínimo esperado de affordance de clique.

**Onde:** `v2/frontend/src/index.css`, bloco `.btn, .actions button, .line-row button, .ui-button` (linhas 319-338) e as variantes logo abaixo (linhas 340-361).

**Mudança sugerida** (adicionar após a regra `.ui-button--danger`, ~linha 361):

```css
.ui-button:hover:not(:disabled) {
  filter: brightness(0.93);
}

.ui-button--secondary:hover:not(:disabled),
.btn-secondary:hover:not(:disabled) {
  background: var(--color-accent-wash) !important;
}

.ui-button--ghost:hover:not(:disabled) {
  background: var(--color-accent-wash);
}
```

---

## 2. Modal e Drawer sem sombra (sem elevação visual)

**Problema:** `.drawer-panel` (usado por `DetailDrawer` e `ConfirmationModal`) flutua sobre o backdrop sem nenhum `box-shadow`. A única separação visual é uma borda de 1px à esquerda — insuficiente para comunicar que é uma camada acima do conteúdo.

**Onde:** `v2/frontend/src/index.css`, regra `.drawer-panel` (linhas 1010-1017).

**Mudança sugerida:**

```css
.drawer-panel {
  width: min(var(--detail-drawer-width), 100%);
  background: var(--color-surface);
  border-left: 1px solid var(--color-border-decorative);
  padding: 1rem;
  overflow: auto;
  color: var(--color-text);
  box-shadow: -8px 0 24px rgba(16, 24, 32, 0.16); /* adicionar esta linha */
}
```

---

## 3. Checkboxes e radios sem nenhum estilo

**Problema:** `type="checkbox"`/`type="radio"` (usados em `ShipmentLogisticsPanels.tsx`, `InvoiceDetailPage.tsx`, `PaymentCreatePage.tsx`) renderizam com a aparência default do navegador (azul do Chrome, cinza do Edge), destoando de todo o resto do design system que usa `--color-accent`.

**Onde:** `v2/frontend/src/index.css` — adicionar uma regra nova, próxima ao bloco `.ds-input`/`.ds-select` (perto da linha 727).

**Mudança sugerida:**

```css
input[type="checkbox"],
input[type="radio"] {
  accent-color: var(--color-accent);
  width: 16px;
  height: 16px;
}
```

---

## Como validar depois de aplicar

1. `npm run dev` em `v2/frontend`.
2. Passar o mouse sobre qualquer botão em qualquer página (ex.: `/orders`) — deve escurecer levemente.
3. Abrir um `DetailDrawer` (ex.: clicar numa linha de pedido) — o painel deve ter sombra visível à esquerda.
4. Abrir uma tela com checkbox (ex.: `PaymentCreatePage`) — o checkbox marcado deve usar a cor azul do design system (`--color-accent`), não o azul padrão do navegador.
