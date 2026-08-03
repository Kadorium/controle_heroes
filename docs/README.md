# Documentação EPIC Controle V2

Ponto de entrada da documentação. O desenvolvimento ativo é a **V2**; a V1 é legado congelado (consulta excepcional).

**Checklist V1 nunca é DoD da V2.** Estado e sequência atuais: consultar o [Roadmap](../ROADMAP_V2_EPIC.md).

---

## 1. Mapa documental

| Preciso saber | Documento | Autoridade | Ciclo de vida |
|---|---|---|---|
| Onde estamos, o que vem agora, gates, ADRs | [`ROADMAP_V2_EPIC.md`](../ROADMAP_V2_EPIC.md) | Canônico (estado/sequência) | Ativo — atualizar após mudança operacional material |
| Como o sistema deve funcionar (produto/arch/aceite) | [`BLUEPRINT_SISTEMA_EPIC_V2.md`](v2/BLUEPRINT_SISTEMA_EPIC_V2.md) | Canônico (produto) | Ativo — atualizar em mudança de domínio/arch |
| Design de interface, Handoff, mockups | [Blueprint UI/UX](v2/blueprint%20UIUX/BLUEPRINT_UI_UX_EPIC_v3.md) · [Handoff](v2/blueprint%20UIUX/HANDOFF_UI_UX_EPIC_V2.md) · [MCK](v2/blueprint%20UIUX/mockups/) | Referência de design; autoridade e status de implementação definidos no Roadmap e nos próprios artefatos | Ativo / histórico conforme o artefato |
| Regras operacionais do Cursor | [`.cursor/rules/epic-v2.mdc`](../.cursor/rules/epic-v2.mdc) | Canônica (`alwaysApply`) | Ativo — método de trabalho |
| Evidências de execuções materiais | [`docs/v2/etapa-*`](v2/) (ex.: [`etapa-inc-6/`](v2/etapa-inc-6/), [`etapa-9/`](v2/etapa-9/), [`etapa-9v/`](v2/etapa-9v/)) | Histórico local de evidência | Imutável após fechamento da entrega |
| Diário integral até Inc-6 | [Snapshot 0.5.42](v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md) · [como ler](v2/archive/roadmap/README.md) | Histórico (não operacional) | **Imutável** |
| Legado V1 | [`docs/v1/README.md`](v1/README.md) · código `v1/` | Histórico / consulta | Congelado (ADR-16) |

O código evidencia o estado implementado na investigação. Divergências corrigem-se no documento responsável.

---

## 2. Histórico e evidências

- **Snapshot 0.5.42** = narrativa integral da reconstrução até a Inc-6; **imutável**. Links relativos do snapshot resolvem a partir da **raiz** do repositório, não de `docs/v2/archive/roadmap/`.
- **`docs/v2/etapa-*`** = logs, testes, screenshots e evidências reproduzíveis de execuções materiais.
- Status dentro de READMEs/evidências de etapa é **histórico** do momento em que foram produzidos.
- **Status atual** pertence exclusivamente ao Roadmap.
- **`docs/v1/**`** = legado histórico (não é DoD nem backlog da V2).

### Linha do tempo (marcos concluídos)

| Marco | Resultado | Relato | Evidência |
|---|---|---|---|
| Decisão de reconstrução modular | Alternativa B | snapshot §§A–E | Blueprint Sistema |
| Fundação | V1 movida + scaffold V2 | snapshot §N | — |
| Inc-1 | Catalog + Orders | snapshot §O.1 | — |
| Inc-2 | Billing + Payables | snapshot §O.2 | — |
| Inc-3 | Payments + Allocation | snapshot §O.3 | — |
| Inc-4 | FX (três visões) | snapshot §O.4 | — |
| Inc-5 | AP + Cockpit + UX-0 | snapshot §O.5 | [`docs/evidence/ux-0/`](evidence/ux-0/) |
| Design + Horizon A | UI/UX Etapas 2–9 + 9V | snapshot §§M.7–M.28 | [`etapa-9/`](v2/etapa-9/) · [`etapa-9v/`](v2/etapa-9v/) |
| Inc-6 | E2E / goldens / aceite Order-to-Pay | snapshot §O.6 | [`etapa-inc-6/`](v2/etapa-inc-6/) |
| Document Readiness A1+A2+DR-UX | Capacidade documental + fechamento UI operacional (H-FIX) | Roadmap 0.5.54 | [`etapa-doc-readiness/`](v2/etapa-doc-readiness/) |
| J#5 I5-0 | Decisões Customs/Inventory + scaffold | Roadmap 0.5.55 | [`etapa-j5/`](v2/etapa-j5/) |
| J#5 I5-1 | ImportProcess + joins + UI `/customs` | Roadmap 0.5.56 | [`etapa-j5/`](v2/etapa-j5/) |
| J#5 DONE (I5-0…I5-6) | Aduana + Inventory; SC-07/09/10; e2e:j5 | Roadmap 0.5.62 | [`etapa-j5/`](v2/etapa-j5/) |

Estado e sequência atuais: consultar o Roadmap. Evidências concluídas ficam em `docs/v2/etapa-*`.

---

## 3. Protocolo DOC_DELTA

Toda entrega da trilha V2 deve terminar com o bloco abaixo (preenchido). Registrar fatos; não classificar em enums extras.

```text
DOC_DELTA
- Updated: NONE | <paths alterados>
- Evidence: NONE | <paths de evidência>
- Roadmap status: UNCHANGED | <mudança e versão>
- Next TODO: <ação confirmada no Roadmap>
- Return to advisor: NONE | <paths a retornar>
```

- **Updated** — arquivos alterados nesta entrega (ou `NONE`).
- **Evidence** — paths em `docs/v2/etapa-*` / `docs/evidence/` quando houver execução material; senão `NONE`.
- **Roadmap status** — `UNCHANGED` se o Roadmap não mudou; caso contrário descrever a mudança e a versão.
- **Next TODO** — próxima ação confirmada **no Roadmap** (não inventar aqui).
- **Return to advisor** — paths que o advisor deve reler, ou `NONE`.

Não criar pasta `etapa-*` só por edição documental de índice/regra/README.
