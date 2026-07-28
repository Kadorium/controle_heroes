# Direção visual provisória — MCK v0.1 (Ciclo 1)

**Natureza:** hipótese visual a validar nos Checkpoints A/B. **Não** é Design System (Etapa 7).  
**Não** copiar o tema escuro AS-IS do frontend (`v2/frontend/src/index.css`).

---

## Família

| Token | Valor | Uso |
|---|---|---|
| Canvas | `#F4F6F8` | Fundo da área operacional |
| Surface | `#FFFFFF` | Tabelas, painéis, drawer |
| Sidebar | `#1B2A41` | Navegação contrastante |
| Sidebar text | `#E8EEF4` / muted `#9AA8B8` | Labels nav |
| Accent / CTA | `#1F4E79` | Ação primária única |
| Text | `#1A2332` | Corpo |
| Muted | `#5B6B7C` | Secundário |
| Border | `#D5DCE5` | Divisórias |
| Row hover/focus | `#E8F1F8` | Seleção de linha |
| Danger | `#B42318` | Vencido / erro semântico |
| Warning | `#B54708` | Atenção / unpriced / stale |
| Success | `#067647` | OK / PAID parcial positivo |

## Tipografia (somente fontes locais)

| Papel | Família | Evidência local |
|---|---|---|
| UI | `Segoe UI`, `Calibri`, `Arial`, sans-serif | `C:\Windows\Fonts\segoeui.ttf` |
| Números tabulares | `Cascadia Mono`, `Consolas`, monospace | `C:\Windows\Fonts\CascadiaMono.ttf` |

**Não** foram baixadas nem embutidas fontes proprietary nos artefatos além do `font-family` CSS no SVG (o renderizador do SO resolve). Fallback seguro se Cascadia ausente: Consolas → monospace.

## Densidade e forma

- Row height tabela ≈ 36 px; header sticky.
- Radius 4–6 px; sombra mínima (drawer apenas).
- Sem gradientes decorativos; sem cards de KPI theater (KPI strip = métricas acionáveis).
- Sidebar ≈ 220 px; content gutters 24 px.

## Shell TARGET

```text
Compras
  Pedidos
  Faturas
Financeiro
  Contas a pagar
  Pagamentos
  (Câmbio hub = não operacional — omitido / não inventar SCR-028)
```

FX strip discreto no rodapé da sidebar (cotação EUR/BRL do cenário).

## AS-IS vs TARGET (visual)

| Aspecto | AS-IS código | TARGET nestes mockups |
|---|---|---|
| Tema | Dark `#0f1720` | Claro operacional |
| Nav | Ordens \| Financeiro | Compras \| Financeiro |
| Faturas | sob Financeiro | sob Compras |
| Orders enrichment | ausente | colunas TARGET (GAP read model — só na legenda) |
