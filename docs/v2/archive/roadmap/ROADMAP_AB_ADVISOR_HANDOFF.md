# ROADMAP A/B — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **ROADMAP-AB** (painel + contrato + operação) |
| Status | **DONE** |
| Data | **2026-08-13** |
| Versão | **0.5.113** |
| Escopo | Só documentação + auditoria só-leitura |
| Próxima ação | **FIN-4** (cronograma no pedido) quando autorizado |

---

## Gate 0 — auditoria de realidade

Runtime `:8081` · health `ok` · DB `epic_v2` · alembic **024** · `schema_ok=true`.

| # | Onde | Resultado |
|---|---|---|
| API | Sem pacote `costing/`; sem `close_order`; sem rota Dashboard; módulos presentes (orders…treasury) | Confirma Custo 0%, Painel 0%, elo 10 FALTA |
| UI comercial (pedido de origem PDF) | Itens; **Vincular produto**; painel **Adiantamentos** (formulário; crédito zerado); Faturas; Cancelar (sem Encerrar) | Confirma A.3 bind/adiantamento; elo 10 só cancelar |
| Embarques | Fila + **Novo embarque** | Embarque manual existe |
| Aduana | Fila + **Novo processo** (lista vazia) | Módulo na mão; sem massa preenchida por PDF nesta sessão |
| Estoque | Movimentações (filtro por produto) | Posição/movimentos existem |
| Contas a pagar | Fila operacional | Crédito/saldo via AP existem |
| Nav | Pedidos…Estoque; **sem** painel executivo / custo da raquete | Confirma Painel 0% / Custo 0% |
| GET autenticado pedido | Uma linha PRODUCT + uma COMMITMENT; origem ingestão | Capacidade mista existe; **não** usado para calibrar Parte A |

**Divergências que baixem n:** nenhuma. Livro-razão do plano mantido (cadeia **2/10 = 20%**).

Passos só-API: health; GET pedido via sessão do browser (sem POST).

---

## Contagens

| Bloco | Linhas |
|---|---|
| Arquivo total | **219** (teto 300) |
| Parte A (`# Parte A` … antes do Contrato) | **70** (teto 70) |
| Contrato | **19** (teto 25) |
| Parte B | **124** (~200) |

Busca na Parte A por jargão interno / IDs de ensaio (`SC-`, `I5-`, `DEC-`, `ADR-`, `J#`, `FIN-`, `RUX-`, `589`, `I.V.`, `pedido 31`, `TESTE-CICLO`, alembic, pytest): **zero ocorrências**.

Snapshot `ROADMAP_V2_EPIC_0.5.42_FULL.md`: **intocado**.

---

## Cadeia — três números

| Qual | % | Motivo |
|---|---|---|
| Antigo §0.5 | ~25% | julgamento “compra real”; sem n/d |
| Plano pré-adendo | 40% (4/10) | PRONTO = só costura LIGADA; contava elos 4 e 5 |
| **Final** | **20% (2/10)** | PRONTO = LIGADA **e** exercitado com documento do fornecedor; 4 e 5 só em amostra de módulo |

Outras barras vs §0.5: ingestão 50→**29** (2/7); aduana 65→**33** (1/3). Financeiro 80, logística 50, custo 0, painel 0 — inalterados na fórmula. **Nenhum denominador mudou** nesta fatia.

---

## O que saiu para onde (nada some)

| Bloco removido do vivo | Destino |
|---|---|
| §9 linhas 0.5.103…0.5.41 | [`ROADMAP_HISTORICO.md`](ROADMAP_HISTORICO.md) |
| Checkpoints I5-0…I5-6 / patch | já em [`docs/v2/etapa-j5/`](../../etapa-j5/) |
| Checkpoints J3-P0…I7 / RUX | já em [`docs/v2/etapa-j3/`](../../etapa-j3/) |
| Detalhe J#4 / UX / DR | já em [`etapa-j4/`](../../etapa-j4/) · [`etapa-doc-readiness/`](../../etapa-doc-readiness/) |
| Fatias J4-FIN | já em [`etapa-j4-fin/`](../../etapa-j4-fin/) |
| §0.3 “paradas do 589” | gaps → A.4; capacidades → A.3; sem A.5 |
| §7 R3/R6 | Contrato |
| §7 R1/R4/R5 | rodapé B.1 |

---

## Passada de coerência

| A.1 / A.2 | Sustentado por |
|---|---|
| Cadeia 20% | livro-razão 2/10; B.2 elos 1–2 LIGADOS com origem PDF |
| Financeiro 80% | B.1 J4-FIN; falta FIN-4 |
| Ingestão 29% | B.1 J#3 + B.4 aceite só Ordine |
| Logística 50% | B.2 elo 6 NÃO EXISTE; B.4 J#4 DONE |
| Aduana 33% | B.2 elos 7–8 FRÁGIL; B.6 CUSTOMS_FUNDING |
| Custo / Painel 0% | B.4 J#6/J#7 NOT_STARTED; Gate 0 |
| “Para na fatura” | primeiro não-PRONTO = elo 3 (B.2 FRÁGIL) |

---

## Arquivos alterados

- `ROADMAP_V2_EPIC.md` (reescrito)
- `docs/v2/archive/roadmap/ROADMAP_HISTORICO.md` (novo)
- `docs/v2/archive/roadmap/README.md`
- `docs/v2/archive/roadmap/ROADMAP_AB_ADVISOR_HANDOFF.md` (este)
- `.cursor/rules/epic-v2.mdc`
- `docs/README.md`

## Recomendação

Aceitar 0.5.113. Próxima canônica: **FIN-4**. Não 3A/020/J#6/J#5-REC.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md · docs/v2/archive/roadmap/ROADMAP_HISTORICO.md · docs/v2/archive/roadmap/README.md · docs/v2/archive/roadmap/ROADMAP_AB_ADVISOR_HANDOFF.md · .cursor/rules/epic-v2.mdc · docs/README.md
- Evidence: NONE (só docs + Gate 0 só-leitura)
- Roadmap status: 0.5.113 ROADMAP-AB DONE; A/B: A reescrita (painel n/d); B reescrita (canônico+livro-razão); Contrato novo
- Next TODO: FIN-4 cronograma no pedido (quando autorizado)
- Return to advisor: docs/v2/archive/roadmap/ROADMAP_AB_ADVISOR_HANDOFF.md
```
