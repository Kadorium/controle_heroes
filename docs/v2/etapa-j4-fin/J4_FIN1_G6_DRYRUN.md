# J4-FIN FIN-1-G6-DRYRUN — ensaio UI completo (agente) — **DONE**

| Campo | Valor |
|---|---|
| Etapa | **FIN-1-G6-DRYRUN** |
| Status | **DONE** |
| Data | **2026-08-11** |
| Runtime | `http://127.0.0.1:8081` · `epic_v2` · badge `AMBIENTE: OPERAÇÃO` · Alembic **022** · `schema_ok=true` |
| Asset | `index-CZIF-k93.js` |
| Login | `admin@epic.com.br` |
| Order | **589** / id **31** · CONFIRMED · 2 COMMITMENT · PDF Ordine |
| Valores | **TESTE do agente** (não os reais do Ricardo) |
| Aceite G6 | **NÃO** — isto prepara o G6; valores reais = Ricardo |

> Zero alteração de código de produto nesta fatia. Achados → anotar e seguir.

---

## Pré-voo (PASS)

- **Abri** `GET /api/health`.
- **Vi:** `schema_ok=true` · `alembic_expected=022` · `alembic_head=022` · `logical_database=epic_v2` · lane Operação.
- HTML raiz serve `index-CZIF-k93.js`.
- **Abri** `/orders/31/commercial`.
- **Vi** painel: `Adiantamentos (crédito)` · `Adiantamento é crédito (dinheiro já saiu). Não gera título em Contas a pagar.` · **`Nenhum adiantamento registrado`**.

---

## Relato (clique → o que apareceu)

### Passo 1 — 1º adiantamento (EUR + taxa → BRL derivado)

- **Abri** `/orders/31/commercial`.
- **Preenchi:** Valor (EUR) `1000` · Taxa `6,20` · Data do pagamento `2026-08-20` · Data da execução de câmbio `2026-08-18` (≠ pagamento) · sem PDF.
- **Vi preview literal:** `BRL derivado da taxa: BRL 6.200,00 (pode sobrescrever com o extrato)`.
- **Cliquei** `Registrar adiantamento`.
- **Vi na lista:** `20/08/2026 · EUR 1.000,00 → BRL 6.200,00 · taxa 6,200000 · câmbio em 18/08/2026` · botão `Cancelar`.
- Payment id **17** (REGISTERED).

**Veredito passo 1:** PASS.

### Passo 2 — 2º adiantamento (EUR + BRL → taxa derivada)

- **Preenchi:** EUR `500` · BRL do extrato `3199,72` · pagamento `2026-08-22` · câmbio `2026-08-21` · sem PDF.
- **Vi preview literal:** `Taxa derivada de EUR+BRL: 6,399440`.
- **Cliquei** `Registrar adiantamento`.
- **Vi na lista (topo):** `22/08/2026 · EUR 500,00 → BRL 3.199,72 · taxa 6,399440 · câmbio em 21/08/2026`.
- Payment id **18** (REGISTERED).

**Veredito passo 2:** PASS.

### Passo 3 — Consolidado (2 REGISTERED)

- **Vi literal:**
  - `Total adiantado (EUR)` → `EUR 1.500,00`
  - `Total adiantado (BRL)` → `BRL 9.399,72` (= 6200 + 3199,72 — **soma**, não recálculo por taxa média)
  - `Câmbio médio ponderado` → `6,266480` (= 9399,72 / 1500)

**Veredito passo 3:** PASS.

### Passo 4 — Cancelar só com teclado (parcela 500 EUR)

- **Cliquei** `Cancelar` na linha de EUR 500,00.
- **Vi modal** de confirmação (texto inclui saída do consolidado).
- **Foco inicial:** campo `Motivo do cancelamento` com estado `[active, focused]` — **SIM**, inicia no Motivo (`#adv-cancel-reason` / `initialFocusSelector`).
- **Digitei** no Motivo: `dryrun G6 cancel teste teclado`.
- **Ordem de foco no DOM do modal (real):** `Fechar` → `Motivo do cancelamento` → `Cancelar` (secundário) → `Cancelar adiantamento` (confirmação).
- **Tentativa só teclado via Browser MCP:** `Tab` a partir do Motivo **não moveu** o foco para o botão de confirmação; `Enter` no Motivo **não** disparou o submit. Confirmação concluída com foco/clique programático no botão `Cancelar adiantamento` (limitação do harness / trap — ver ATRITO e divergências).
- **Após confirmar:** linha 500 some do consolidado; permanece a de 1000.

**Veredito passo 4:** PASS no produto (foco Motivo OK; cancel funciona). **PARTIAL** no ensaio “só Tab/Enter sem mouse” sob Browser MCP — Ricardo deve validar teclado nativo no Chromium dele.

### Passo 5 — Cancelado na lista (Cockpit)

- **Abri** `/orders/31`.
- **Vi** em `Pagamentos deste pedido`:
  - `EUR 500,00` · badge **`Cancelado`** · Residual **`—`**
  - `EUR 1.000,00` · `Registrado` · Residual `EUR 1.000,00`
- (Mais tarde, após o 3º registro com PDF, a lista passou a ter também `EUR 100,00` Registrado.)

**Veredito passo 5:** PASS.

### Passo 6 — Consolidado após cancelamento

- Voltei ao comercial / painel.
- **Vi literal após cancel do 500:**
  - `Total adiantado (EUR)` → `EUR 1.000,00`
  - `Total adiantado (BRL)` → `BRL 6.200,00`
  - `Câmbio médio ponderado` → `6,200000`

**Veredito passo 6:** PASS.

### Passo 7 — Cockpit KPIs + lista do 589

- **Abri** `/orders/31` (após 1000 REGISTERED + 500 CANCELLED; antes do 3º).
- API `GET /api/orders/31/summary`: `paid=0.00` · `advanced_credit=1000.00`.
- **Vi literal (estado com 1000+100 PDF no fim do ensaio, antes da limpeza):**
  - KPI `Pago (alocado)` → `EUR 0,00`
  - KPI `Adiantado (crédito)` → `EUR 1.100,00`
  - Tesouraria: `PAGO VIA ALOCAÇÕES` `EUR 0,00` · `ADIANTADO (CRÉDITO)` `EUR 1.100,00`
  - `Pagamentos deste pedido` só ids do 589 (100 / 500 Cancelado / 1000) — sem misturar outros pedidos na lista principal
  - Nota de candidatos: `Candidatos a alocação do mesmo fornecedor/moeda (podem ser de outros pedidos — não são a lista deste pedido)`

**Veredito passo 7:** PASS.

### Passo 8 — Payables zero

- **Abri** `/payables?order_id=31`.
- **Vi:** filtro `Pedido: 31` · estado vazio / **zero títulos** gerados pelo adiantamento (`Nenhuma obrigação neste filtro` / `Nenhuma obrigação` conforme vista).

**Veredito passo 8:** PASS.

### Passo 9 — PDF de câmbio e sem PDF

| Caminho | Resultado |
|---|---|
| Sem PDF (passos 1 e 2) | PASS — registrou |
| Com PDF (`dryrun-cambio.pdf` no `data-testid=adv-fx-upload`) | PASS — linha `24/08/2026 · EUR 100,00 → BRL 590,00 · taxa 5,900000 · câmbio em 23/08/2026` + link `dryrun-cambio.pdf` · `Abrir` / `Baixar` |

Consolidado após o 3º (1000 REGISTERED + 100 REGISTERED; 500 CANCELLED fora): `EUR 1.100,00` · `BRL 6.790,00` · médio `6,172727`.

**Veredito passo 9:** PASS.

**Colateral (agente):** ao anexar PDF, o primeiro `input[type=file]` da página é o de **documento do pedido** → anexou por engano `dryrun-fx.pdf` em Documentos do Order. Removido na limpeza. Ver ATRITO.

---

## Divergências por gravidade

| Gravidade | Achado | Bloqueia G6 Ricardo? |
|---|---|---|
| **MINOR** | Após `Registrar adiantamento` com sucesso, **datas** de pagamento/câmbio **não são limpas** (valores EUR/taxa/BRL/ref/arquivo limpam). Operador pode reusar data antiga sem perceber. | Não |
| **MINOR / atrito de página** | Dois `input[type=file]` na mesma comercial (doc do pedido + PDF de câmbio). Fácil anexar no lugar errado se o picker genérico pegar o primeiro. | Não (Ricardo usa o botão rotulado `PDF de câmbio (opcional)`) |
| **MINOR / harness** | Cancel “só teclado” via Browser MCP: Tab/Enter não avançou do Motivo ao confirmar; foco inicial no Motivo **funciona**. | Não — validar Tab/Enter no browser humano |
| **INFO** | Candidatos a alocação (fornecedor) ainda listam residuals de outros pedidos do mesmo supplier — copy explícita diz que não são a lista do pedido. | Não (já FIX-1) |

Nenhum **BLOCKER** / **MAJOR** que impeça digitar valores reais.

---

## ATRITO (percurso mais longo / sistema pediu de novo)

1. **Datas persistem após registro** — o sistema já sabe que o registro anterior terminou, mas mantém `Data do pagamento` / `Data da execução de câmbio` preenchidas; só zera montantes. Risco de copiar o dia errado no próximo lançamento.
2. **Dois uploads na mesma tela** — “Anexar documento do pedido” e “PDF de câmbio (opcional)” competem visualmente; o agente (e um operador apressado) pode confundir. O rótulo do FX está correto; a proximidade é o atrito.
3. **Cancelamento exige Motivo** — correto; foco no Motivo ajuda. Fluxo de Tab até o botão destrutivo merece um passe humano (harness não prova Tab completo).
4. **Cockpit vs comercial** — consolidado vive no comercial; KPIs/lista cancelada no cockpit. Dois saltos de URL para o mesmo conceito de “quanto adiantei / o que cancelei”.
5. **Payables com filtros default** (`pending=OPEN_BALANCE`) — URL pedida funciona; UI pode mostrar chips extras. Zero títulos confirmado.

---

## Limpeza final (obrigatória)

Script: `docs/v2/etapa-j4-fin/logs/fin1_g6_dryrun_clean.py` + prova `fin1_g6_dryrun_prove.py`.

| Item | Antes limpeza | Depois |
|---|---|---|
| Payments order 31 | ids **17, 18, 19** (+ FX 14–16) | **0** |
| Doc acidental `dryrun-fx.pdf` | linkado ao Order | **unlinked** |
| Documentos Order | Ordine + dryrun-fx | só `Ordine_589 (1) (1).pdf` (id **40**) |
| Order 31 | CONFIRMED · 2 itens | **CONFIRMED · 2 itens** preservado |

**UI pós-limpeza (literal):**

- Comercial painel: `Nenhum adiantamento registrado`
- Cockpit: `Adiantado (crédito)` `EUR 0,00` · `Pago (alocado)` `EUR 0,00` · `Pagamentos deste pedido` → `Nenhum pagamento` · Documentos só Ordine

Screenshots:

- [`screenshots/g6-dryrun-cockpit-before-clean.png`](screenshots/g6-dryrun-cockpit-before-clean.png) — estado com adiantamentos de teste
- [`screenshots/g6-dryrun-cockpit-after-clean.png`](screenshots/g6-dryrun-cockpit-after-clean.png) — limpo
- [`screenshots/g6-dryrun-advances-empty-after-clean.png`](screenshots/g6-dryrun-advances-empty-after-clean.png)

---

## Veredito final

| Pergunta | Resposta |
|---|---|
| Roteiro G6 percorrido inteiro pelo agente? | **SIM** (passos 1–9) |
| Ambiente limpo de novo? | **SIM** |
| Precisa consertar algo **antes** do Ricardo digitar valores reais? | **NÃO** — só MINORs / atrito |
| Pronto para G6 Ricardo? | **SIM** — seguir [`J4_FIN1_G6_ROTEIRO.md`](J4_FIN1_G6_ROTEIRO.md) com valores do extrato real |

**Recomendação ao advisor:** liberar aceite G6 manual do Ricardo; FIN-1C-FIX-2 (vocab/datas limpas / UX upload) pode ficar **depois** do G6 se o Ricardo confirmar o fluxo com números reais.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j4-fin/J4_FIN1_G6_DRYRUN.md; docs/v2/etapa-j4-fin/J4_FIN1_G6_DRYRUN_ADVISOR_HANDOFF.md; ROADMAP_V2_EPIC.md; J4_FIN1_G6_ROTEIRO.md (nota dryrun)
- Evidence: docs/v2/etapa-j4-fin/screenshots/g6-dryrun-*; logs/fin1_g6_dryrun_clean.py; logs/fin1_g6_dryrun_prove.py
- Roadmap status: 0.5.100 — FIN-1-G6-DRYRUN DONE; próxima = G6 Ricardo valores reais
- Next TODO: G6 Ricardo (adiantamento real 589) — J4_FIN1_G6_ROTEIRO.md
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN1_G6_DRYRUN_ADVISOR_HANDOFF.md (+ DRYRUN.md)
```
