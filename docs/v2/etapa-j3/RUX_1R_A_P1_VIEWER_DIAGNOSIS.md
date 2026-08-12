# RUX-1R-A P1 — Rediagnóstico viewer (2026-08-06)

## Erros manuais

1. `getOrInsertComputed is not a function` (pdfjs moderno sem polyfill)
2. `Failed to fetch dynamically imported module: http://localhost:8081/assets/pdf.worker.min-CLrFZWeq.mjs`

## P1-a — HTTP / MIME

| Check | Resultado |
|---|---|
| HEAD worker | 200 |
| GET worker | 200 |
| Content-Length | 1312452 (bate com arquivo em disk) |
| Body início | comentário Mozilla / JS real |
| **Content-Type** | **`text/plain; charset=utf-8`** |
| HEAD vs GET | idem |

`python -c "mimetypes.guess_type('x.mjs')"` → `('text/plain', None)` no Windows do operador.

## P1-b — Dist

- Path: `v2/frontend/dist` (settings `frontend_dist_path`)
- HTML: `/assets/index-DLCAC02q.js` + `index-BYO_VvyO.css`
- Worker presente: `pdf.worker.min-CLrFZWeq.mjs` mtime 2026-08-05 18:16
- Processo 8081: uvicorn `--reload` serve esse dist

## P1-c — Catch-all SPA

- `/assets/DOES_NOT_EXIST.mjs` → **404 JSON** (StaticFiles), **não** index.html
- Catch-all SPA **não** é a causa do worker existente

## P1-d — Origem

- Erro 2 originou worker em **8081** → runtime **dist@8081**
- Vite 5174 sem `--mode test` proxy → 8081; URL inexistente no Vite devolve HTML (outro vetor se hash errado no HMR)

## P1-e / P1-f

- Hash pedido = hash em disk (não stale missing file)
- Causa não é cache de HTML apontando hash removido

## Causa provada

**MIME `text/plain` para `.mjs` via StaticFiles/mimetypes no Windows.**  
Browser bloqueia dynamic import / module worker.

Não é: SPA catch-all HTML, arquivo ausente, proxy Vite sozinho, getOrInsertComputed (já endereçado no source legacy).

## Correção autorizada (P2)

Registrar `mimetypes.add_type("application/javascript", ".mjs")` antes do mount `/assets` em `create_app.py`. Escopo só viewer/static serving.
