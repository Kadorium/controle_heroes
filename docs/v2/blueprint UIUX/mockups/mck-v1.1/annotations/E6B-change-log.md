# E6B — Change log (MCK v1.1)

## Escopo autorizado

E6-001…006 · E6-011 · E6-012 · E6-018.  
Não autorizados: E6-007…010, E6-013…017.

## Contraste — bordas interativas (E6-012)

| Uso | Cor anterior | Cor nova | Background | Razão anterior | Razão nova |
|---|---|---|---|---:|---:|
| btn-ghost | `#D5DCE5` | `#818C9C` | `#FFFFFF` | 1.38 | 3.41 |
| input | `#D5DCE5` | `#818C9C` | `#FFFFFF` | 1.38 | 3.41 |
| filter-chip | `#D5DCE5` | `#818C9C` | `#FFFFFF` | 1.38 | 3.41 |
| close-hit | `#D5DCE5` | `#818C9C` | `#FFFFFF` | 1.38 | 3.41 |
| edit (foco) | `#1F4E79` | `#1F4E79` (inalterado) | `#FFFFFF` | 8,66 | 8,66 |

### Decorativos preservados (`#D5DCE5`)

panel · kpi-box · `.border` de superfícies · drawer frame · hair `#E6EBF1`.

**Não** declarar WCAG global. Par mínimo corrigido: **3.41:1** (alvo ≥3:1 para identificação do controle).

## Editorial

| ID | Antes | Depois |
|---|---|---|
| E6-001 | Câmbio PY-… / breadcrumb / drawer | Câmbio da obrigação (links: Abrir…); ação densa na tabela AP permanece rótulo curto **Câmbio** por densidade — sem hub SCR-028 |
| E6-002 | Preview abaixo… | A prévia abaixo ainda não foi confirmada. |
| E6-003 | Workspace da obrigação… | Câmbio da obrigação — planejamento… |
| E6-004 | Fila AP / Voltar à AP | Contas a pagar / Voltar para contas a pagar |
| E6-005 | FX / BRL | Câmbio / BRL |
| E6-006 | Sem plano FX | Sem plano cambial |

## AUX (E6-018 / E6-011)

Grid 2×4 (cards 548×148, x até 1356). Smoke oficial: `review/smoke-1366/MCK-AUX-01-states-above-fold-1366x768.png`.  
Evidência histórica 6A preservada em `mck-v1.0/review/e6a-evidence/`.

## Gates

Oito SVG · PDF 8 págs · PNG 1440×8 · smoke 1366×8 · v1.0 preservado · Sem código.

## Fechamento externo E6-B

- regressão localizada no retorno do MCK-007 corrigida;
- link integralmente visível em 1440 e 1366;
- sem alteração de versão ou arquitetura;
- PDF regenerado.

**Detalhe:** cluster `Aberto · Heroes · EUR · sem execução vinculada` deslocado à direita na linha contextual do MCK-007 (`badge` x=470), preservando `‹ Voltar para contas a pagar` em `font-size="12"`. Demais artboards inalterados.

**Sincronização Etapa 7A:** Checkpoint **E6-B = APROVADO** (fato histórico; não reverter em rollback da Etapa 7).

