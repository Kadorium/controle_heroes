# RUX-1R-A P3/P4/P5 — preservação e cortes (sem alterar .plan)

Conteúdo canônico permanece no plano mestre `j3-rux_operational_ux_6992440c.plan.md`
(usuário pediu: não editar o `.plan` nesta execução). Este arquivo confirma que
P3–P5 estão **incorporados e vigentes**.

## P3 — Preservado

- Matemática L1–L5 + tolerância ±0,02 HALF_UP
- Hipótese SCONTI aberta (não subtrair de novo na L3 sem fixture)
- Golden I3 = mudança semântica deliberada se alterar MATH_TAXABLE_ZERO_MISMATCH
- Política IR já ingerido: reextract explícito; SUPERSEDED; raw; preview; NEEDS_RECONFIRMATION

## P4 — DEF-RUX-TX-01

Registrado. **Não corrigido** no corte viewer.

Evidência inicial: `execute_commit` PARTIAL + `uow.commit()` na route; flushes
podem persistir. Correção autorizada em **RUX-2R** (Modelo B savepoints).

BLOCKER para create_supplier/create_product até semântica clara.

## P5 — Corte RUX-3A

- **RUX-3A-1** — primeira importação (fiscal/SKU/create) sem matching 2ª importação
- **RUX-3A-2** — refs / SUGGEST / AUTO / 2ª importação

Limitação consciente: 3A-1 pode perguntar de novo na 2ª importação.
