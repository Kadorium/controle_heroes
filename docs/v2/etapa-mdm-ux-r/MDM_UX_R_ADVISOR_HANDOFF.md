# MDM-UX-R — retorno ao advisor (R0–R2 · GATE VISUAL)

```text
Etapa: MDM-UX-R R0 → R1 → R2
Status: DONE até GATE VISUAL
GATE: PASS (1 ciclo de correção A2)
R3–R6: NÃO INICIADOS (STOP)
Roadmap / Blueprint: NÃO ALTERADOS
Backend / schema / OpenAPI / frontend de produção: NÃO ALTERADOS
epic_v2 / epic_v2_test: NÃO ESCRITOS
```

Campanha excepcional de reconstrução **visual**. Capacidade HTTP MDM-UX permanece encerrada. Numerário (`CUSTOMS_FUNDING`) continua a próxima ação da cadeia.

Servir o proto: `python -m http.server 8765` em [`docs/v2/etapa-mdm-ux-r/prototype/`](prototype/) → `http://127.0.0.1:8765/`

---

## Decisão pedida

Aprovar ou reprovar o **alvo visual**. Reprovar = iterar o proto (R2), **não** abrir R3.  
R3–R6 só depois de aceite explícito.

## Estado R0

**DONE.** Registro forense em [`as-is/`](as-is/). Backup externo **não** fez parte desta campanha.

- Cópias das páginas MDM NEW: [`as-is/pages/`](as-is/pages/)
- MIXED (AppShell/App): [`as-is/mixed/`](as-is/mixed/)
- Classificação KEEP / REBUILD: [`as-is/CLASSIFICATION.md`](as-is/CLASSIFICATION.md)
- Hunks MIXED: [`as-is/MIXED_INVENTORY.md`](as-is/MIXED_INVENTORY.md)
- Rail recusado (produção intacta): [`as-is/NAV_REFUSED.md`](as-is/NAV_REFUSED.md)
- Git evidência no início da campanha: **229** linhas / **101** `??` · HEAD `3b10deb`

## Estado R1 — Arquitetura de Informação (só proto)

Rail prototipado:

```text
COMPRAS / FINANCEIRO / LOGÍSTICA (só Embarques) / ADUANA
CATÁLOGO → Produtos
ADMINISTRAÇÃO → Usuários
```

Fornecedores e Prestadores **fora** do rail. Fornecedor: overflow `⋯` → Heroe's Srl. Prestadores: CTA em Embarques. `AppShell.tsx` de produção **intocado** (B11).

HUMAN-IDENTITY no proto: descrição principal quando útil; SKU secundário; se description = SKU / vazia / genérica (`Item …`) → SKU uma vez + **Sem descrição comercial**.

## Estado R2 — proto interativo

Path: [`docs/v2/etapa-mdm-ux-r/prototype/`](prototype/)  
`index.html` + `proto.css` + `app.js` + fixture [`fixtures/catalog-visual.json`](prototype/fixtures/catalog-visual.json).

Fixture visual: 92 SKUs do CSV V1 **somente leitura** + 8 fakes (`source=proto-fake`). Não é migração V1→V2 nem requisito de CSV.

Mutações (criar/editar) ficam em `sessionStorage`. Zero PATCH.

## Screenshots

Pasta: [`prototype/screenshots/`](prototype/screenshots/)

1440×900 e 1366×768: lista rica, incompletos, Mais filtros, detail leitura/edição, create, sidebar, supplier, users.  
1100: rail compacto + lista + create + users.  
Extra: overflow supplier, mock FUTURO, fallback B5.

## Percurso A2

Literal em [`prototype/A2_WALK.md`](prototype/A2_WALK.md). Os 10 passos obrigatórios foram executados (busca, quick filter, Mais filtros, chip, paginação, sort, ficha, voltar com query, edição, create).

## Checklist A2

### Estrutura

1. Sidebar nova no proto — PASS (Catálogo→Produtos; sem Fornecedores/Prestadores no rail)
2. Product List interativa — PASS
3. Product Detail leitura — PASS
4. Product Detail edição — PASS
5. Create mínimo — PASS
6. Supplier contextual — PASS (`⋯` / ficha Heroes)
7. Users — PASS (nome, e-mail, papel, Ativo/Inativo)
8. Sem `epic_v2` / PATCH — PASS

### Modernidade

- Não parece CRUD/admin genérico (lista identidade humana + qualidade; busca dominante) — PASS após ciclo 1
- Busca domina; filtros secundários — PASS (sem botão Buscar)
- Densidade profissional / hierarquia — PASS
- Descrição domina SKU quando útil — PASS; fallback B5 honesto — PASS
- Badges no lugar de Sim/Não — PASS
- Ações frequentes evidentes (`+ Novo produto`, Editar); raras no `⋯` — PASS
- Hover/focus/loading/empty/no-results — PASS (`demo=empty` vs busca sem match)
- Teclado: `/` foca busca; Enter na linha; Escape fecha menus — PASS
- Supplier não é domínio primário — PASS
- Seleção assistida natural, rotulada **FUTURO**, sem chat de IA — PASS (não é critério de FAIL se ausente; foi exercitada)

### Interação

Os 10 passos do percurso — PASS (evidência JSON + markdown).

## FAILs nomeados (ciclo 1) e correção

Não houve segundo ciclo. Correções no próprio proto:

1. **SKU=EAN duplicado** no subtítulo HUMAN-IDENTITY quando iguais — corrigido (EAN omitido se = SKU).
2. **Screenshot de create** saiu da ficha pós-submit — recapturado no formulário mínimo.
3. **Tipo 9px** nos títulos de grupo do rail — fora da escala §26.4; passou a caption 10.5.
4. **Fundos cinza em `<dd>`** (leitura parecia grade admin) — removidos; hair dividers.
5. **1366 Mais filtros** — o toggle fechava o painel já aberto; captura corrigida.

## EXCEPTIONS de DS

Ver [`prototype/EXCEPTIONS.md`](prototype/EXCEPTIONS.md).

- **EXCEPTION-COMPACT-RAIL** — 56px ≤1100 (token de produção `--shell-sidebar-rail`; §26 só lista 220 expandida). Obrigatória pelo gate 1100.
- **EXCEPTION-PROTO-BANNER** — faixa warning de isolamento; não vai para produção (B11).
- Overlay do menu reusa shade §26.6 já EXCEPTION.

Sem terceira paleta. Sem biblioteca nova.

## GATE

**PASS.** STOP. Não iniciar R3–R6.

## Proposta de Roadmap (NÃO aplicada)

```text
B.1 versão: 0.5.126 (proposta)
MDM-UX HTTP DONE. Aceite visual da campanha 0.5.125 RECUSADO (GAP-MDM-VISUAL).
WIP uncommitted: HEAD 0.5.106 vs arquivo 0.5.125 (GAP-WIP-UNCOMMITTED).
Catálogo V2 operação = 24 ensaios; V1 CSV = 92 SKUs (GAP-CATALOG-MASS; CSV FUTURO).
MDM-UX-R R0–R2 DONE; GATE VISUAL PASS no proto isolado.
R3–R6 bloqueados até aceite do dono. Não relançar MDM-1…CF.
Alembic 026. Barras 8/10.
Próxima ação da CADEIA: pagar numerário (CUSTOMS_FUNDING).
Rail de produção permanece na IA recusada até pós-gate (B11).
```

## Próxima etapa proposta

1. Dono/advisor **julga o proto** em `http://127.0.0.1:8765/`.
2. Se aprovar: autorizar R3 (Product List real + `summary`) — **não nesta run**.
3. Cadeia operacional: **pagar numerário**.
4. B6 (tax_id Heroes) continua avulsa na UI atual, fora de R3.

## Recomendação

Aceitar o alvo visual (IA Catálogo→Produtos, lista de qualidade, ficha leitura+editar, create mínimo, supplier overflow). Não copiar o proto para `App.tsx`/`AppShell` sem R3 autorizado.
