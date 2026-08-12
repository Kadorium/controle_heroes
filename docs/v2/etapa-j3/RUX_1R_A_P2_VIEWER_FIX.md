# RUX-1R-A P2 — Correção viewer (tentativa 1–2)

## Tentativa 1

| Campo | Valor |
|---|---|
| Hipótese | `mimetypes.add_type("application/javascript", ".mjs")` antes do mount StaticFiles |
| Mudança | [`create_app.py`](../../../v2/app/foundation/create_app.py) |
| Resultado | Código ok em TestClient; **processo 8081 antigo não recarregou** — MIME continuou `text/plain` |
| Decisão | Reiniciar processo + reforço middleware |

## Tentativa 2

| Campo | Valor |
|---|---|
| Hipótese | Fresh process + add_type + middleware forçando `Content-Type: application/javascript` em `/assets/*.mjs` |
| Comando | restart uvicorn 8081; `curl -I http://localhost:8081/assets/pdf.worker.min-CLrFZWeq.mjs` |
| Resultado | **`content-type: application/javascript`** · 200 · length 1312452 |
| Decisão | PASS HTTP; validar browser |

## Tentativa 3 (loading stuck)

| Campo | Valor |
|---|---|
| Hipótese | `setLoading(false)` omitido em early-return (`!canvas` / Strict Mode) deixava "Carregando PDF…" com canvas já pintado |
| Mudança | `finally { if (!cancelled) setLoading(false) }` + throws explícitos; `npm run build` → `index-DmHwE2Uf.js` |
| Resultado browser | `loadingText:false`, canvas 743×1052, engine `PDF.js (legacy)`, script `index-DmHwE2Uf.js` |
| Screenshot | `docs/v2/etapa-j3/screenshots/rux-1r-a-p2-viewer-pass.png` |

## Gate P2 — PASS

- Worker MIME `application/javascript`
- Ordine 589 canvas renderizado em dist@8081
- Sem "Carregando" eterno / sem erro de módulo no estado final
- Escopo só viewer/static — sem Catalog/matching/math/ledger/shell

## Escopo

Somente serving estático / MIME + loading do PdfViewerPanel. Sem Catalog, matching, math, ledger, shell.
