# J3_RUX_ADVISOR_HANDOFF

**Etapa:** J3-RUX (RUX-1R-A → RUX-3B)  
**Status:** **PARTIAL** — execução técnica até 3B; **RUX-3C** aguarda validação manual. **Não** ACCEPTED.

## Estado anterior → atual

| Antes | Agora |
|---|---|
| UIV REJECTED; viewer quebrado (`getOrInsertComputed` / worker fetch) | Viewer PASS em dist@8081 (Ordine 589 visível) |
| Plano dizia RUX-0…5 DONE sem runtime saudável | P0 auditou WIP; corte viewer fechado; Catalog/commit avançados |
| Sem refs / SKU EPIC / tax_id | Alembic **020**; `EPIC-########`; refs híbridas; Modelo B savepoints |

## Hipóteses H-EXEC (confirmação)

| ID | Veredito |
|---|---|
| H-EXEC-01 SUGGEST | **Confirmada** — `SUGGESTED_SKU_MATCH` sem auto-bind; readiness exige confirmação |
| H-EXEC-02 constraints | **Confirmada** — índices parciais EAN/CLASS em 020 |
| H-EXEC-03 SKU | **Confirmada** — `product_sku_seq` → `EPIC-########` |
| H-EXEC-04 fiscal | **Confirmada** — `tax_id` + `country_code` obrigatório se tax_id |
| H-EXEC-05 reextract | **Confirmada** — `POST .../reextract`; bloqueio pós-`create_order` SUCCEEDED |
| H-EXEC-06 Modelo B | **Confirmada** — `begin_nested` por op; PARTIAL honesto; resume skip SUCCEEDED |

## Viewer (P1/P2)

- **Causa:** Windows `mimetypes` → `.mjs` como `text/plain`  
- **Fix:** `mimetypes.add_type` + middleware; `PdfViewerPanel` `finally` loading  
- **Evidência:** screenshot `screenshots/rux-1r-a-p2-viewer-pass.png`; worker `Content-Type: application/javascript`

## Gates técnicos (amostra)

- `pytest tests/test_catalog_rux3a.py tests/test_ingestion_rux_tx.py tests/test_ingestion_i3.py tests/test_ingestion_rux_reextract.py` — PASS na execução  
- Build FE regenerado (`index-DmHwE2Uf.js` na rodada P2; rebuild após badge recomendado)

## Runtime para RUX-3C (manual)

| Item | Valor |
|---|---|
| URL aceite | `http://127.0.0.1:8081/ingestion` (dist) **ou** `npm run dev:test` → Vite 5174 → API **8082** |
| Evitar | `npm run dev` sem mode test (proxy **8081** ops) |
| Badge | sidebar `runtime-badge` — lane Teste/Operação + DB lógico + build |
| Credenciais | `admin@epic.com.br` / `admin123` |
| Fixture | `v2/tests/fixtures/ingestion/corpus_589/Ordine_589.pdf` |
| Banco | ops `epic_v2` @8081; teste `epic_v2_test` @8082 — aplicar `alembic upgrade head` (020) |
| Browser | Chromium/Cursor; hard reload após rebuild |

### Checklist manual RUX-3C

1. Badge mostra lane correta  
2. Upload Ordine 589 em catálogo vazio  
3. PDF visível (sem cinza / sem erro worker)  
4. 3 pendências: Supplier, I.V.2, I.V.1  
5. Criar supplier + 2 products (SKU vazio → EPIC)  
6. Preview → Order DRAFT 2 linhas + DocumentLink  
7. Segunda importação: SUGGEST exige confirmação  
8. Sem `catalog:write`: vincular ok; criar bloqueado com mensagem  

## Pendências

- RUX-3C manual  
- Fattura match via refs EAN (parcialmente no Catalog; adapter Fattura pode ainda usar path antigo)  
- OpenAPI regenerate / drift check se advisor exigir  
- Não iniciar RUX-4 / J#6  

## Arquivos relevantes

- `v2/app/foundation/create_app.py` (MIME)  
- `v2/frontend/.../PdfViewerPanel.tsx`, `RuntimeBadge.tsx`, `MatchingPanel.tsx`  
- `v2/alembic/versions/020_catalog_rux_identity_refs.py`  
- `v2/app/catalog/*`  
- `v2/app/ingestion/commit_commands.py`, `staging_commands.py`, `adapters/ordine_heroes_v1.py`  

## Recomendação

Advisor executa checklist RUX-3C no runtime acima. Só então marcar aceite operacional e liberar J#6.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (0.5.77); docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; J3_RUX_ADVISOR_HANDOFF.md; evidências P1/P2
- Evidence: screenshots/rux-1r-a-p2-viewer-pass.png; RUX_1R_A_P1/P2 md; pytest catalog/i3/rux_tx/reextract
- Roadmap status: 0.5.76 → 0.5.77; próxima RUX-3C manual
- Next TODO: validação manual RUX-3C
- Return to advisor: docs/v2/etapa-j3/J3_RUX_ADVISOR_HANDOFF.md
```
