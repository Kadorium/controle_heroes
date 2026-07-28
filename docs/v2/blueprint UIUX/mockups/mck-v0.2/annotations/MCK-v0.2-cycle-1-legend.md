# Legenda — MCK v0.2 Ciclo 1 (remediação)

Anotações **fora** do viewport. Interface limpa = aplicação real.

## Verificação dos problemas (v0.1 → v0.2)

| ID | Veredito v0.1 | Correção v0.2 |
|---|---|---|
| C1 | CONFIRMADO (Hoje=0 com PY-8855-1 em 28/07) | KPI Hoje = EUR 700,00 · 1 título |
| C2 | CONFIRMADO (ordem não priorizava hoje) | vencido → hoje → futuros crescentes |
| C3 | CONFIRMADO (Unalloc. PAY) | **Sem plano FX** EUR 6.600,00 · 10 títulos |
| C4 | CONFIRMADO (PAY-0042) | PAY-2026-0042 / 0043 integrais |
| C5 | CONFIRMADO (EN no drawer) | Labels PT |
| C6 | CONFIRMADO (Pag/FX) | Pagamento / Câmbio |
| C7 | CONFIRMADO (só texto rodapé) | × “Fechar detalhe” no canto |
| C8 | CONFIRMADO (8 linhas) | **12** linhas |
| C9 | CONFIRMADO (ISO dates) | DD/MM/AAAA |
| C10 | CONFIRMADO (EN badges) | Confirmado / Rascunho / Cancelado |
| C11 | CONFIRMADO (3.050*) | Coluna **Subtotal precificado** + badge |
| C12 | CONFIRMADO (2ª linha cockpit) | Chevron › mesma altura |
| C13 | CONFIRMADO (só rodapé) | “Ordenar por: Atualização recente” |
| C14 | CONFIRMADO (notas técnicas) | Removidas do viewport |
| C15 | CONFIRMADO (sem user) | Admin / Sair |
| C16 | CONFIRMADO (mix) | PT na UI principal |
| C17 | CONFIRMADO (hierarquia) | Ações completas; badges alinhados |

## Domínio × UI (badges)

| Domínio | Badge UI |
|---|---|
| CONFIRMED | Confirmado |
| DRAFT | Rascunho |
| CANCELLED | Cancelado |
| OPEN | Aberto |
| PARTIALLY_PAID (vencido) | Vencido |
| due = hoje | Hoje |

## Gaps (só legenda)

- Colunas Faturado/Saldo/Próx.venc. na fila Pedidos = TARGET + GAP read model.
- G02: CTA Registrar pagamento TARGET; wiring AS-IS sem query.
- Chevron › = affordance cockpit (SCR-005); a11y implícita na linha focada.
- Botão × = **Fechar detalhe** (`aria-label`).

## SCR / FLW

- MCK-001 → SCR-003 · entrada FLW-006/007.
- MCK-004 → SCR-008 · FLW-003/005/007 · seleção PY-8841-2 → PAY-2026-0043.
