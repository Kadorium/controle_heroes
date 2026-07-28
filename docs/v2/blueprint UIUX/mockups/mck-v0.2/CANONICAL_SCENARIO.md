# Cenário canônico — MCK v0.2

**Autoridade:** fonte única de dados para mockups Etapa 5.  
**Não** inserir no banco nem no runtime.  
**Data de referência:** **2026-07-28**.  
**Base:** MCK v0.1 + correções de remediação (KPI Hoje, ordenação AP, volume auxiliar).

---

## Identidade

| Entidade | Valor |
|---|---|
| Supplier operacional | Heroes |
| Order | **PO-2026-0181** |
| Invoice ISSUED | **INV-H-8841** |
| Invoice DRAFT | **INV-H-8910** |
| Payment histórico | **PAY-2026-0042** |
| Payment futuro (Ciclo 2) | **PAY-2026-0043** |
| Quote EUR/BRL | **6,2180** · Frankfurter · desatualizado (`stale`) |

---

## Order — PO-2026-0181

| Campo | Valor |
|---|---|
| Status domínio | CONFIRMED (badge UI: **Confirmado**) |
| Moeda | EUR |
| Data | 12/05/2026 |

### Itens

| Pos. | SKU | Qtd | Preço | Total |
|---:|---|---:|---:|---:|
| 1 | HR-JKET-101 | 100 | 12,50 | 1.250,00 |
| 2 | HR-SHOE-220 | 40 | 45,00 | 1.800,00 |
| 3 | HR-BAG-015 | 20 | — | — |

| Agregado | Valor |
|---|---|
| Subtotal precificado | **EUR 3.050,00** |
| `commercial_total` completo | **ausente** (1 item sem preço) |

---

## Payables núcleo (INV-H-8841)

| Payable | Vencimento | Valor | Alocado | Saldo | Notas |
|---|---|---:|---:|---:|---|
| PY-8841-1 | 15/06/2026 | 915,00 | 600,00 | 315,00 | Parcial · **vencido** |
| PY-8841-2 | 30/07/2026 | 1.220,00 | 0 | 1.220,00 | Aberto · **plano FX** · seleção drawer |
| PY-8841-3 | 15/09/2026 | 915,00 | 0 | 915,00 | Aberto |

---

## Payment — PAY-2026-0042

Valor 1.500,00 · Alocado 600,00 → PY-8841-1 · Residual 900,00.

## Jornada futura — PAY-2026-0043 (não desenhada)

Origem PY-8841-2 · Create 700,00 (saldo obrigação intacto) · Allocate 700 → saldo 520.

---

## Fila AP exibida (MCK-004) — 12 linhas ordenadas

Ordem: vencidos → hoje → futuros (crescente).

| # | Payable | Vencimento | Saldo | FX | Flag |
|---|---|---|---:|---|---|
| 1 | PY-8841-1 | 15/06/2026 | 315,00 | — | vencido |
| 2 | PY-8855-1 | **28/07/2026** | **700,00** | — | **hoje** |
| 3 | PY-8841-2 | 30/07/2026 | 1.220,00 | 6,1500 | aberto · selecionado |
| 4 | PY-8712-1 | 02/08/2026 | 890,00 | 6,1800 | aberto |
| 5 | PY-8790-2 | 05/08/2026 | 420,00 | — | aberto |
| 6 | PY-8860-3 | 20/08/2026 | 880,00 | — | aberto |
| 7 | PY-8888-1 | 25/08/2026 | 550,00 | — | aberto (aux) |
| 8 | PY-8890-1 | 01/09/2026 | 310,00 | — | aberto (aux) |
| 9 | PY-8701-1 | 10/09/2026 | 1.390,00 | — | aberto |
| 10 | PY-8841-3 | 15/09/2026 | 915,00 | — | aberto |
| 11 | PY-8901-1 | 20/09/2026 | 640,00 | — | aberto (aux) |
| 12 | PY-8910-1 | 30/09/2026 | 480,00 | — | aberto (aux) |

### KPIs derivados das 12 linhas

| KPI | Valor | Contagem | Cálculo |
|---|---|---|---|
| Vencido | EUR 315,00 | 1 | PY-8841-1 |
| Hoje | EUR 700,00 | 1 | PY-8855-1 |
| Próx. 7d | EUR 2.110,00 | 2 | PY-8841-2 + PY-8712-1 (29/07–04/08) |
| Saldo aberto | EUR 8.710,00 | 12 | Σ saldos |
| Sem plano FX | EUR 6.600,00 | 10 | Σ saldos sem cotação/plano (exclui 8841-2 e 8712-1) |

**Escolha C3:** KPI **Sem plano FX** (não Unalloc. residual de Payment).
