# J#3 — Handoff: atualização do plano mestre pós-I0

| Campo | Valor |
|---|---|
| Etapa | Atualização do plano mestre J#3 pós-I0 |
| Status | **DONE** |
| Data | 2026-08-04 |
| Escopo | Somente documental / planning |
| I1 | **NOT_STARTED** (não autorizado nesta rodada) |

---

## 1. Estado anterior

| Item | Situação |
|---|---|
| Plano mestre Cursor `planning_j3_ingestão_909721db.plan.md` | Desatualizado (0.5.63; P0/I0 todos `pending`) |
| Plano específico I0 `j3-i0_fundação_ingestão_3475ba90.plan.md` | Concluído (todos `completed`); útil como apêndice |
| Espelho `J3_EXECUTION_PLAN.md` | Declarava-se “autoridade de detalhe” e planos Cursor “não canônicos” |
| Roadmap | **0.5.67** — I0 DONE; próxima = revisão I0 |
| Alembic | **016** |

---

## 2. Alterações desta rodada

- Status checkpoints no mestre: P0-a/b, governance, I0 → **completed**; I1…I7 → **pending**
- Snapshot atual (0.5.67 / 016 / foundation / APIs / RBAC / `ingestion→audit`)
- Resultado I0 incorporado (fechamento + gates + pendências→I1+)
- Decisões P0 ratificadas resumidas; forense não re-colado
- I1…I7 reorganizados com objetivo/pré/escopo/fora/gates/stop (expectativas futuras, não código afirmado)
- Espelho versionado sincronizado (hierarquia mestre/espelho)
- Plano I0 marcado **superseded** operacionalmente (arquivo preservado)
- **Sem** alteração de código / migrations / Blueprint / testes

---

## 3. Hipóteses

| Hipótese | Veredito |
|---|---|
| Plano mestre pôde ser atualizado in-place | **CONFIRMADA** |
| Espelho versionado sincronizado | **CONFIRMADA** |
| Nenhuma nova implementação iniciada | **CONFIRMADA** |

---

## 4. Hierarquia documental

1. Roadmap — status global  
2. Plano mestre Cursor — trabalho da fase  
3. `J3_EXECUTION_PLAN.md` — espelho resumido no repo  
4. Handoffs — evidência  

---

## 5. Texto proposto para `.cursor/rules/epic-v2.mdc` (NÃO aplicado)

Inserir sob §2 Ciclo operacional (ou §6.1), após autorização explícita:

> Quando já existir um plano mestre ativo para uma fase (ex.: `planning_j3_ingestão_*.plan.md`), o agente deve **atualizá-lo** em vez de criar um novo `.plan`. Planos adicionais só para campanha excepcional que não caiba no mestre, com justificativa explícita e marcação de **apêndice temporário**. O espelho versionado em `docs/v2/etapa-*` deve ser sincronizado na mesma rodada. Status global permanece no Roadmap.

---

## 6. Arquivos

| Path | Papel |
|---|---|
| `.cursor/plans/planning_j3_ingestão_909721db.plan.md` | Plano mestre atualizado |
| `docs/v2/etapa-j3/J3_EXECUTION_PLAN.md` | Espelho sync |
| `docs/v2/etapa-j3/README.md` | Índice hierarquia |
| Este handoff | Return advisor |
| `ROADMAP_V2_EPIC.md` | Próxima ação alinhada (versão 0.5.67 UNCHANGED) |

---

## 7. Pendências

- Advisor revisa **este handoff** + **plano mestre** + **handoff I0**
- Autorizar (ou não) inserção da regra em `epic-v2.mdc`
- **Não** iniciar I1 até pedido explícito

---

## 8. Próxima etapa lógica

**Revisão do plano mestre atualizado e do handoff J3-I0 pelo advisor — não iniciar J3-I1.**

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: .cursor/plans/planning_j3_ingestão_909721db.plan.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/README.md; docs/v2/etapa-j3/J3_MASTER_PLAN_UPDATE_HANDOFF.md; ROADMAP_V2_EPIC.md (próxima ação)
- Evidence: docs/v2/etapa-j3/
- Roadmap status: 0.5.67 UNCHANGED (versão); próxima ação alinhada à revisão mestre+I0
- Next TODO: Revisão plano mestre + handoff J3-I0 — não iniciar I1
- Return to advisor: docs/v2/etapa-j3/J3_MASTER_PLAN_UPDATE_HANDOFF.md; (plano mestre Cursor path citado acima)
```
