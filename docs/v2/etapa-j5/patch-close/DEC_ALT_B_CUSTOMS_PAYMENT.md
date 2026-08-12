# DEC — Alternativa B: Payable CUSTOMS_FUNDING (rascunho C0)

| Campo | Valor |
|---|---|
| ID | DEC-J5-CLOSE-ALT-B |
| Status | **ACCEPTED** (C5 — canônico no Blueprint 0.2.16 / Roadmap 0.5.63) |
| Data | 2026-08-04 |
| Checkpoint | J5-C0 |

## Decisão

Payable origem `CUSTOMS_FUNDING` é **obrigação registrada** criada pelo confirm de FundingRequest (Numerário).

Nesta release:

- Treasury **não** permite Payment nem Allocation para essa origem;
- Backend mantém bloqueios (`list_eligible_payables` INNER JOIN Invoice; reject `invoice_id is None`);
- UI remove ações impossíveis (Invoice, Order, FX, Novo pagamento);
- FundingRequest→Payable **não** é jornada liquidável.

## Backlog explícito (não minor)

`Treasury settlement for CUSTOMS_FUNDING` — redesign de counterparty (Payee ≠ Supplier), elegibilidade, lifecycle ISSUED/SETTLED, comprovante.

## Classificação alvo (C5)

| Artefato | Classificação |
|---|---|
| Core J#5 | DONE |
| Patch corretivo | DONE (após gates) |
| Fluxo financeiro Customs | PARTIAL |
| UI J#5 | ACCEPTED_WITH_BACKLOG |

## Texto normativo futuro — Blueprint (colar em C5)

> Payable `CUSTOMS_FUNDING` representa obrigação registrada a partir do Numerário (FundingRequest). Não é liquidável pelo módulo Treasury atual (Payment/Allocation exigem Invoice/Supplier). Liquidação Customs é backlog `Treasury settlement for CUSTOMS_FUNDING`.

## Texto normativo futuro — Roadmap (colar em C5)

> Patch fechamento operacional J#5 DONE. UI ACCEPTED_WITH_BACKLOG. Backlog: **Treasury settlement for CUSTOMS_FUNDING**. Próxima ação: planejar J#3.
