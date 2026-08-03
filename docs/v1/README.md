STATUS: ARQUIVADO — REFERÊNCIA HISTÓRICA DA V1
NÃO UTILIZAR COMO ESPECIFICAÇÃO OU DoD DA V2

# Documentação V1 — referência histórica

Índice do legado V1. **Não** usar como especificação ou DoD da V2.

Canônicos V2: [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](../v2/BLUEPRINT_SISTEMA_EPIC_V2.md) · [`ROADMAP_V2_EPIC.md`](../../ROADMAP_V2_EPIC.md) · [`docs/README.md`](../README.md).

Código legado: [`v1/`](../../v1/).

## Documentos V1 (referência)

| Documento | Papel |
|---|---|
| [`BLUEPRINT_SISTEMA_EPIC_V1.md`](BLUEPRINT_SISTEMA_EPIC_V1.md) | Blueprint funcional histórico V1 |
| [`DOCUMENTACAO_TECNICA_EPIC_V1.md`](DOCUMENTACAO_TECNICA_EPIC_V1.md) | As-built técnico V1 |
| [`CHECKLIST_MVP_IMPORTACAO_EPIC_V1.md`](CHECKLIST_MVP_IMPORTACAO_EPIC_V1.md) | Checklist F0–F12 + evidências (histórico) |
| [`CURSOR_RULES_IMPORTACAO_EPIC.md`](CURSOR_RULES_IMPORTACAO_EPIC.md) | Regras permanentes de negócio V1 (método na trilha legado) |

## Arquivo (`archive/`)

Entregas, guias de tela, relatórios, mocks, resumo executivo inicial e prompt-mestre Cursor — todos históricos.

| Arquivo | Origem |
|---|---|
| [`archive/RESUMO_EXECUTIVO_INICIAL_EPIC_V1.md`](archive/RESUMO_EXECUTIVO_INICIAL_EPIC_V1.md) | `02_resumo_executivo_…` |
| [`archive/PROMPT_MESTRE_CURSOR_EPIC_V1.md`](archive/PROMPT_MESTRE_CURSOR_EPIC_V1.md) | `03_prompts_cursor_…` |
| [`archive/GUIA_COMPLETO_MVP_REPASSE.md`](archive/GUIA_COMPLETO_MVP_REPASSE.md) | Guia de repasse MVP |
| `archive/ENTREGA-*.md`, `GUIA-TELA-*.md`, `RELATORIO_*.md`, mocks, QA | Entregas e evidências de UI |

**Cursor (guarda V1):** [`.cursor/rules/epic-v2.mdc`](../../.cursor/rules/epic-v2.mdc) §4 — legado congelado (ADR-16); só manutenção/goldens/segurança. Checklist desta pasta **nunca** é DoD da V2.

---

## O que NÃO herdar da V1 na V2

### Modelo e estados

| Não herdar | Por quê | Substituto V2 |
|---|---|---|
| Ordem como contêiner universal | Impede 1 DUIMP → N invoices | Order / Shipment / ImportProcess |
| Status único multi-domínio | Máquina confusa | Estados por agregado |
| Payment só em Invoice | Scadenze/antecipo | Payable + PaymentAllocation |
| Shipment com order_id obrigatório | Multi-ordem frágil | ShipmentItem → OrderItem |
| Expense em Treasury | Mistura caixa com custo | Expense ∈ Costing |

### Código e UI

Não herdar: `order_central`, dumps globais multi-domínio, `api.ts` monolítico, god pages, routers com regra densa.

### O que PODE portar (com testes)

Regras de ouro; finance / fx_pnl / landed_cost / reconciliation; parser Heroes como adapter; attachments/audit; enums/RBAC com revisão; fixtures como golden files.
