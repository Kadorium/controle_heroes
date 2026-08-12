# J3-RUX — RUX-3C-DRYRUN (ensaio UI Ordine) — **DONE**

| Campo | Valor |
|---|---|
| Etapa | **RUX-3C-DRYRUN** |
| Status | **DONE** |
| Runs | 2026-08-08 (1º) · **2026-08-10 (re-run narrativo, sem screenshots)** |
| Runtime | `http://127.0.0.1:8081` · `epic_v2` · badge `AMBIENTE: OPERAÇÃO` · Alembic **021** |
| Aceite | **NÃO** — isto **não** é G6; próximo = aceite **manual** Ricardo |

---

## Relato 2026-08-10 (clique → o que apareceu)

Pré-voo: SQL `docs=0` / sem 589 / sem Heroes; `/api/health` `schema_ok=true`. Login `admin@epic.com.br`.

### Passo 1 — Fila vazia
- **Abri** `/ingestion`.
- **Vi:** `Nenhuma importação na fila` · `Envio atual: —` · `AMBIENTE: OPERAÇÃO`.

### Passo 2 — Upload (limite do Browser)
- Browser MCP **não** preenche `<input type=file>` → upload por API (batch **#21**, occ **#26**, `Ordine_589.pdf`).
- **Liguei** `sessionStorage` `epic-ingestion-active-batch-id=21` e recarreguei.
- **Vi:** `Envio atual: #21` · tabela com `Ordine_589.pdf` · `58.7 KB` · `PDF` · `Pronto · Recebido` · combobox de tipo · `Extrair dados` · `Remover`. Fila ainda vazia.

### Passo 3 — Extrair
- Combobox já em `Ordine Heroes (PDF)`.
- **Cliquei** `Extrair dados` → botão virou `Extraindo…`.
- **Vi na fila:** `#23` · `Pedido de compra` · `Rascunho` · Pedido `—` · Pendências `4` · `Excluir`.
- Apareceu link `Abrir` no ficheiro.

### Passos 4–5 — Workspace + pendência fornecedor
- **Cliquei** `Abrir` → `/ingestion/23`.
- **Vi título:** `Pedido de compra (Ordine)` · `Importação #23 · Conferindo — pedido ainda não criado`.
- **Resumo:** `Número do documento 589` · `Fornecedor Heroe's Srl` · `Data 04/06/2026` · `Moeda EUR` · `Quantidade 16.600 PZ` · `Total € 830.000,00`.
- Linhas: ambas com badge `compromisso` · `14.600` / `2.000` PZ.
- **Antes de criar:** `Heroe's Srl (PI 02610500395) — ainda não cadastrado` · `Buscar fornecedor` · `Cadastrar fornecedor`.
- **Próximo passo:** `Pedido não será criado até resolver o fornecedor.` · falta `Fornecedor não vinculado nem marcado para criar` · `Order não criada: fornecedor ausente`.
- Botão `Criar pedido em rascunho` **disabled**.

### Passo 8 — Editar quantidade (fecho narrativo)
- **Cliquei** `Corrigir` na 1ª linha → campos `Descrição` / `Quantidade=14600` / `Unidade=PZ` / `Preço unitário=50.00` · `Salvar linha` · `Cancelar`.
- **Alterei** Quantidade para `14601` · **cliquei** `Salvar linha`.
- **Depois:**
  - linha: `14.601 PZ · € 50,00 · total € 730.050,00`
  - soma Resumo: `Quantidade 16.601 PZ`
  - **Total cabeçalho permanece `€ 830.000,00`** (não recalculou)
- **Reverti:** Corrigir → `14600` → Salvar · voltou `14.600` / `16.600` / totais de linha originais.

### Passo 15 — Painel técnico
- No mesmo workspace, probe do texto da página: **sem** `JSON`, `cells_json`, `raw_value`, `adapter_id`, `fingerprint`, `painel técnico`.

### Passo 14 — Zoom
- **Cliquei** `+` no viewer · rótulo passou de `100 %` para `110 %`. PDF continua no painel (`PDF.js (legacy)`).

### Passos 6–7 — Fornecedor + texto compromisso
- **Cliquei** `Cadastrar fornecedor`.
- **Vi:** `Confirme os dados do documento. O fornecedor só será cadastrado ao criar o pedido — nada é gravado agora.` · Nome `Heroe's Srl` · PI `02610500395` · `Confirmar cadastro no pedido`.
- **Cliquei** confirmar.
- **Próximo passo passou a:** `Pronto para criar pedido rascunho 589.`
- Lista:
  1. `Cadastrar fornecedor Heroe's Srl`
  2. `Guardar o documento`
  3. `Criar pedido 589 em rascunho`
  4. **`Registrar 2 linhas de compromisso (produtos reais virão pela fatura)`**
  5. `Vincular o documento ao pedido`
- `Criar pedido em rascunho` ficou **enabled**. Código interno = `589`. Helper: `O número do documento (vínculo com a fatura) permanece o do PDF.`

### Passos 9–10 — Código + criar
- Campo editável `Código interno do pedido` = `589`; Resumo mostra `Número do documento` `589` (não confundir).
- **Cliquei** `Criar pedido em rascunho`.
- **Vi:** subtítulo `Importação #23 · Pedido criado (589)` · caixa `Pedido criado` · `O pedido foi criado em rascunho. Abrir pedido`.

### Passo 11 — Pedido DRAFT
- **Cliquei** `Abrir pedido` → `/orders/29/commercial`.
- **Vi:** `Pedido 589` · `Heroe's Srl · EUR · 04/06/2026` · badge `Rascunho` · linhas **Compromisso** I.V.2 14.600 / I.V.1 2.000 · `Total comercial: EUR 830.000,00` · documento `Ordine_589.pdf`.

### Passo 12 — Fila
- `/ingestion` (depois da jornada):
  - `#23` · `Pedido criado` · link `589` · Pendências `3`
  - (mais tarde) `#24` · `Pedido criado` · `589-DRYRUN`
  - `#25` · `Rejeitado` (S1)
- **Não** aparece “Rejeitado” nos docs que criaram pedido.

### Passo 13 — Colisão
- Reimport API → doc **#24**. Abrir `/ingestion/24`.
- **Cliquei** `Criar pedido em rascunho` com código `589`.
- **Vi:** `O pedido 589 já existe no sistema.` · `Nada foi gravado.` · `Abrir pedido existente` · `Criar com outro código:` · `Criar com este código`.
- **13A:** clique `Abrir pedido existente` → `/orders/29/commercial`.
- **13B:** voltei a `#24`, provoquei de novo a colisão, preenchi `589-DRYRUN`, cliquei `Criar com este código`.
- **Vi:** `Importação #24 · Pedido criado (589-DRYRUN)`. DB: order **30** code `589-DRYRUN`, `external_ref=589`, DRAFT.

### S1 — Descartar / Cancelar
- Doc **#25** sem pedido. Hook: `confirm` → **false** (Cancelar); `prompt` → motivo.
- Texto do confirm: `Excluir esta importação em definitivo? … OK = excluir e sumir da fila · Cancelar = só marcar como rejeitada.`
- Prompt: `Motivo para rejeitar a importação (obrigatório):`
- **Resultado:** fila `#25` · `Rejeitado`; DB `review_status=REJECTED`. Cancelar **não** aborta — marca rejeitada.

### S2 / S3
- Docs com pedido (`#23`, `#24`): gravados `READY`; UI `Pedido criado` + link (não “Rejeitado”).

### Restore G4
- Script reset: apagou orders 29/30 DRAFT + Heroes + fila.
- Prova: `docs 0` · `orders589 0` · `heroes 0` · `batches 0`.

---

## Divergências (sem correção nesta fatia)

| Gravidade | Achado |
|---|---|
| Atrapalha | Total do **cabeçalho** não recalcula ao editar qty (passo 8) |
| Atrapalha | Pendências fila `3`/`4` vs. uma ação de fornecedor no workspace |
| Cosmético / limite | Upload via API (`AUTO_LIMIT` Browser MCP) |
| S1 | Cancelar no confirm de excluir → ainda REJECTED (comportamento explícito no texto do confirm) |

---

## Escopo

- Zero alteração de código de produto.
- Não é aceite G6.
- Sem 3A / 020 / J#6.

## Próxima

**Aceite manual Ricardo (G6)** em `:8081` / `epic_v2` (limpo).

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_3C_DRYRUN_UI.md
- Evidence: NONE (relato textual; screenshots não usados neste re-run)
- Roadmap status: UNCHANGED (0.5.91; evidência narrativa reforçada)
- Next TODO: aceite manual Ricardo (RUX-3C G6)
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3C_DRYRUN_UI.md
```
