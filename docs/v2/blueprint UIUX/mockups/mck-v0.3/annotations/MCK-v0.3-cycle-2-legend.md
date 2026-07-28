# Legenda — MCK v0.3 Ciclo 2

Anotações fora do viewport. Checkpoints **C/D pendentes** de revisão externa.

## Ajustes de fechamento do Ciclo 1

| Item | Correção |
|---|---|
| MCK-001 | Filtro **Rascunhos** (plural) |
| MCK-004 | Removido ID futuro do drawer; **Valor sugerido para registro: EUR 700,00**; saldo permanece 1.220,00 até alocação |

## Matriz de consistência

| Elemento | 001 | 002 | 003 | 004 | 005 | 006 | 007 |
|---|---|---|---|---|---|---|---|
| Shell Compras/Fin | x | x | x | x | x | x | x |
| Admin/Sair | x | x | x | x | x | x | x |
| Datas DD/MM/AAAA | x | x | x | x | x | x | x |
| Badges PT | x | x | x | x | — | x | x |
| Money EUR tabular | x | x | x | x | x | x | EUR+BRL |
| PO-2026-0181 | foco | id | link | filtro | banner | — | subtítulo |
| PY-8841-2 | — | lista | — | drawer | origem | eligible | workspace |
| PAY-2026-0042 | — | card | — | — | — | — | — |
| PAY-2026-0043 | — | — | — | — | só sucesso | foco | — |
| Docs/Audit | — | lista | painel | drawer | upload | doc | painel |
| Mutação financeira | — | **não** | emitir | — | registrar | alocar | plan/quote |

## Classificação AS-IS / TARGET / GAP

| Tema | Classificação |
|---|---|
| Cockpit read-only + deep links | AS-IS capacidade / TARGET visual |
| Docs sem página dedicada | AS-IS listagem · GAP deep link |
| G02 contexto AP→Payment | TARGET no mock · **GAP** wiring |
| Enrichment Orders | TARGET · GAP read model |
| Payment create fields | AS-IS (supplier, date, amount, currency, ref, file) |
| Allocate batch + version | AS-IS domínio · TARGET preview UX |
| FX 3 visões + ausência ≠ 0 | AS-IS · TARGET layout |
| SCR-028 hub | **omitido** (GAP) |
| Fallback sem reporting:read | só legenda (TARGET/GAP) |

## FLW / SCR

| Mock | SCR | FLW |
|---|---|---|
| 001 | 003 | entrada |
| 002 | 005 | 006 |
| 003 | 007 | 001/002 |
| 004 | 008 | 003/005/007 |
| 005 | 011 | 003 |
| 006 | 012 | 004 |
| 007 | 009 | 005 |
| AUX | vários | confirmações / 403 / 409 / empty / FX fail |

## Domínio × badge

CONFIRMED→Confirmado · DRAFT→Rascunho · ISSUED→Emitida · OPEN→Aberto · REGISTERED→Registrado · INITIAL permanece técnico FX.
