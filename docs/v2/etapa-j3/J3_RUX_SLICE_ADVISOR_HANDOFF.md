# J3-RUX — Slice fino (badge + Q4/C1/C2) — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | J3-RUX slice fino (badge OBJ-EXEC-04 + copy Q4 + 3 blocos + esconder CTA) |
| Status | **DONE** (UI-only; RUX-2R+ não iniciados) |
| Data | 2026-08-06 |
| Runtime | `http://127.0.0.1:8081` · Vite/dist · DB `epic_v2` |

## Estado anterior → atual

| Antes | Depois |
|---|---|
| Health legado sem `runtime_lane` / `logical_database` → badge `DB —` | API reiniciada; health com lane+DB; badge `Ambiente: Operação` (técnico só no tooltip) |
| "Pendências de catálogo" + Issues com códigos + 3 pendências | Três blocos: **Resumo** \| **Antes de criar o pedido** \| **Próximo passo** |
| Linhas I.V.* como pendência de produto + CTA criar produto | Compromisso no Resumo; CTA create product oculto; só fornecedor (+ math C2) em Antes |

## Hipóteses / decisões aplicadas

- Q3=(B) invertida: toda linha Ordine PDF = compromisso por padrão, exceto EAN / já resolvido — **UI-only** neste slice.
- C1: linhas fora de "Antes de criar".
- C2 (i): math falsa **visível** com copy humana (sem `MATH_*`).
- C3/C4: só documentados; sem Orders/migrations/adapter.

## Gate (evidência)

| Critério | Resultado |
|---|---|
| Screenshot tela completa | PASS — `docs/v2/etapa-j3/screenshots/j3-rux-slice-ordine-589.png` |
| Badge Operação\|Teste + DB | PASS — `Ambiente: Operação`; tooltip `DB epic_v2` |
| Pendências | PASS — **1 real** (fornecedor) + **1 conhecida-falsa** (math); linhas no Resumo |
| Zero códigos técnicos no operador | PASS — sem `SUPPLIER_NOT_FOUND` / `AMBIGUOUS_SKU` / `IR #` |
| Sem CTA criar produto | PASS |
| Browser | Cursor/3.14.7 · Chromium 144 / Electron 40.10.3 |

## Entregas de código (principais)

- `RuntimeBadge.tsx` — copy Ambiente + tooltip técnico
- `ordineShellHelpers.ts`, `OrdineSummaryPanel.tsx`, `OrdineBeforeCreatePanel.tsx`
- `MatchingPanel.tsx` — modo compromisso; sem create product
- `IngestionWorkspacePage.tsx` — 3 blocos + detalhes técnicos colapsados
- `PdfViewerPanel.tsx` — `compactChrome`
- Vitest `IngestionPages.test.tsx` atualizado

## Pendências / não autorizado

- RUX-2R (math real + unsqueeze + C4 dual-form) — **NÃO autorizado**
- DEC-RUX-ORDERITEM-NULL — fora da campanha
- RUX-3A/B/C, RUX-4, J#6 — **NÃO autorizados**
- Glyph squeeze nas descrições do Resumo permanece (adapter) até RUX-2R

## Próxima etapa lógica

Parar. Aceite manual advisor do slice se desejado; **não** iniciar RUX-2R sem autorização explícita.

## DOC_DELTA

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md (0.5.78); este handoff
- Evidence: docs/v2/etapa-j3/screenshots/j3-rux-slice-ordine-589.png
- Roadmap status: 0.5.78 — slice fino EXECUTADO; próxima = aguardar auth RUX-2R ou aceite manual
- Next TODO: NÃO iniciar RUX-2R sem autorização; opcional RUX-3C manual do slice
- Return to advisor: docs/v2/etapa-j3/J3_RUX_SLICE_ADVISOR_HANDOFF.md
```

## Recomendação

Aceitar o slice UI como **DONE**. Autorizar RUX-2R só quando quiser corrigir math falsa + unsqueeze (débito C4).
