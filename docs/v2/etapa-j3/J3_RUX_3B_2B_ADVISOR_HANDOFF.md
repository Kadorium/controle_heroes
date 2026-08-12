# J3-RUX — RUX-3B-2b (UI jornada Ordine) — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-3B-2b** — UI jornada Ordine (catálogo vazio → Order DRAFT) |
| Status | **DONE** (gates desta fatia) — **RUX-3C = aceite manual do Ricardo (não auto-executado)** |
| Data | 2026-08-07 |
| Alembic | **021** (inalterado; sem 020) |
| Fora | Outras famílias, reextract UI, readiness, PendencyList genérico, RUX-3A, mig 020, RUX-4, J#6 |

---

## WIP na árvore — NÃO desta fatia (C5)

1. Migration **020** isolada em `_wip_isolated_rux3a_rux2rb/` — **não aplicada**
2. reextract rota **501**
3. **Débito RUX-4:** PARTIAL + `uow.commit()` cego em Numerário / XLSX / Dossiê
4. Outras famílias de documento / redesign fora da jornada Ordine

---

## Entregas (escopo Ordine na tela)

1. **CTA "Cadastrar fornecedor"** — modal pré-preenchido editável; confirmação explícita; grava `pending_create_supplier` no IR (**sem** chamada Catalog); sem `catalog:write`: CTA desabilitado com texto humano.
2. **Bloco "Próximo passo"** — preview em português (5 passos); sem `op_key` técnico; CTA "Criar pedido em rascunho" só se `can_commit`.
3. **Resultado** — sucesso com link para comercial do pedido; falha em PT + “nada persistiu”; 409 vincular → pendência (não erro genérico).
4. **Aviso confirm (V2-b)** — ao confirmar Order com linhas COMMITMENT, aviso de que produtos reais virão pela fatura.
5. **ERROR dismiss** — justificativa obrigatória + Audit (backend + UI).

### Correções de runtime nesta fatia

- `load({ soft: true })` após commit — evita `setDoc(null)` desmontar o painel e apagar o resultado.
- Link "Abrir pedido" → `/orders/:id/commercial` (linhas de compromisso visíveis).
- E2E: console limpo **após** login (401 do probe de sessão pré-auth não conta na jornada).

---

## Resposta: ERROR / justificativa

**Sim — dispensar ERROR exige justificativa e vai para Audit.**

| Camada | Comportamento |
|---|---|
| Backend | `DISMISSED` + `severity=ERROR` sem `justification` → `IssueJustificationRequired` (422) |
| Audit | Detalhes incluem `justification`, `severity`, `code` |
| UI | Campo de motivo; sem texto → mensagem humana; botão "Ignorar" não passa |
| Teste | `test_dismiss_error_requires_justification_and_audits` |

Com isso, `can_commit` (“zero ERROR aberto”) não é formalidade: a única saída do operador para ERROR matemático real é Ignorar **com motivo auditado**.

---

## Gates provados

| Gate | Evidência |
|---|---|
| Jornada 6 screenshots, catálogo vazio (sem seed) | `screenshots/rux-3b-2b/01…06-*.png` |
| Zero código técnico na UI da jornada | asserts E2E `assertNoTechLeak` |
| Console limpo (pós-auth) | E2E `consoleErrors` / `unauthorized` vazios |
| Chromium | `screenshots/rux-3b-2b/chromium-version.txt` → `149.0.7827.55` |
| E2E Playwright | `npm run e2e:rux-3b-2b` — **1 passed** |
| pytest completo | **452 passed** — `logs/rux3b2b-pytest-full.txt` |

### Screenshots (âncora)

`docs/v2/etapa-j3/screenshots/rux-3b-2b/`

1. `01-ordine-589-fila.png`
2. `02-revisao-pendencia.png`
3. `03-modal-cadastro-fornecedor.png`
4. `04-preview-portugues.png`
5. `05-resultado-pedido-criado.png`
6. `06-pedido-compromissos.png`

---

## Checklist RUX-3C — aceite manual do Ricardo

> **RUX-3C não foi auto-executado.** Ordem abaixo = o que o Ricardo deve fazer no **seu** runtime, catálogo **vazio** (sem seed de Heroes).

### Preparação

1. Runtime próprio (não o do Cursor), app sobe, login como operador com `ingestion:*`, `orders:write`, `catalog:write`.
2. Confirmar catálogo **sem** o fornecedor do Ordine 589 (Heroe's).
3. Abrir DevTools → Console (deve permanecer limpo após login).

### Passos e o que observar

| # | Ação | Observar |
|---|---|---|
| 1 | Ingestão → importar `Ordine_589.pdf` → escolher adapter → processar | Documento na fila; abrir revisão |
| 2 | Tela de revisão | Bloco "Antes de criar o pedido" com **1 pendência** de fornecedor; **nenhum** `create_supplier` / `store_document` / `add_item` visível |
| 3 | Clicar "Cadastrar fornecedor" | Modal com nome (e campos) pré-preenchidos do documento, editáveis |
| 4 | Confirmar no modal | **Não** cria fornecedor ainda; volta à revisão; pendência vira intent; preview atualiza |
| 5 | Bloco "Próximo passo" | Lista em português: cadastrar fornecedor, guardar documento, criar pedido 589 em rascunho, registrar 2 linhas de compromisso, vincular documento; CTA **Criar pedido em rascunho** habilitado |
| 6 | Criar pedido | Resultado de sucesso + link "Abrir pedido"; console limpo |
| 7 | Abrir pedido | Comercial: **2 linhas Tipo = Compromisso**, unidade PZ; status Rascunho |
| 8 | (Opcional) Confirmar pedido | Aviso: produtos reais ainda não definidos / virão pela fatura |

### Critérios de aceite

- [ ] Completou 1→7 sem terminal, sem Cursor, sem ler código
- [ ] Zero texto técnico de operação na UI
- [ ] Catálogo estava vazio no início; fornecedor só nasce no commit
- [ ] Console limpo após login
- [ ] Pedido DRAFT com 2 compromissos

---

## Anotado, não feito (fora de escopo)

- Outras famílias de documento; reextract UI; readiness; PendencyList genérico; RUX-3A; migration 020; RUX-4; J#6; redesign fora da jornada Ordine.

---

## Arquivos relevantes (curto)

- `v2/frontend/src/features/ingestion/CommitResultPanel.tsx`
- `v2/frontend/src/features/ingestion/ordinePreviewHuman.ts`
- `v2/frontend/src/features/ingestion/MatchingPanel.tsx`
- `v2/frontend/src/features/ingestion/IngestionWorkspacePage.tsx`
- `v2/frontend/src/features/orders/OrderDetailPage.tsx`
- `v2/app/ingestion/staging_commands.py` (+ schemas/errors/routes)
- `v2/frontend/e2e/rux-3b-2b-ordine-journey.spec.ts`

---

## Recomendação

**Aceitar RUX-3B-2b** após Ricardo executar o checklist **RUX-3C** no runtime dele. Próximo só com auth: o que o plano mestre definir pós-aceite (não iniciar 3A/020/J#6).

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (0.5.86); docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/J3_RUX_3B_2B_ADVISOR_HANDOFF.md
- Evidence: docs/v2/etapa-j3/screenshots/rux-3b-2b/; docs/v2/etapa-j3/logs/rux3b2b-pytest-full.txt; e2e rux-3b-2b
- Roadmap status: 0.5.86 — RUX-3B-2b DONE; próxima = RUX-3C (aceite manual Ricardo)
- Next TODO: RUX-3C aceite manual no runtime do Ricardo (checklist neste handoff)
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3B_2B_ADVISOR_HANDOFF.md
```
