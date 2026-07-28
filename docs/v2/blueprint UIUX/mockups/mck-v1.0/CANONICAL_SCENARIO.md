# Cenário canônico — MCK v1.0

**Autoridade:** fonte única de dados para mockups Etapa 5 (versão corrente).  
**Não** inserir no banco nem no runtime.  
**Data de referência:** **2026-07-28**.  
**Base:** MCK v0.4 + ajustes editoriais finais (sem alteração de valores centrais). **Aprovado** (Checkpoints A–D).

---

## Identidade

| Entidade | Valor |
|---|---|
| Supplier operacional | Heroes |
| Order | **PO-2026-0181** |
| Invoice ISSUED | **INV-H-8841** |
| Invoice DRAFT | **INV-H-8910** |
| Payment histórico | **PAY-2026-0042** |
| Payment Ciclo 2 | **PAY-2026-0043** (após registro) |
| Quote EUR/BRL | **6,2180** · Frankfurter · desatualizado · **27/07/2026 18:00 UTC** |

---

## Linha temporal por mockup

| Momento | Mockups | Estado |
|---|---|---|
| **T0** | MCK-001, 002, 003, 004, 005, 007 | PY-8841-2 saldo **1.220,00**; PAY-2026-0043 **não existe** |
| **T1** | AUX — sucesso Payment | PAY-2026-0043 registrado 700 · residual 700; PY-8841-2 ainda 1.220 |
| **T2** | MCK-006 (principal) | Prévia: alocar 700 → saldo projetado 520 · residual projetado 0 |
| **T3** | AUX — sucesso Allocation | Residual 0 · PY-8841-2 saldo 520 · parcialmente pago |

**Regra:** artboards principais **não** misturam T0/T1/T2/T3.

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
| Total comercial completo | **indisponível** (1 item sem preço) |

---

## Invoice ISSUED — INV-H-8841

Valor **EUR 3.050,00** · Emitida · documento anexado.

### Payables

| Payable | Vencimento | Valor | Alocado | Saldo | Notas |
|---|---|---:|---:|---:|---|
| PY-8841-1 | **15/06/2026** | 915,00 | 600,00 | 315,00 | Parcial · **vencido** (vencido desde 15/06 em 28/07) |
| PY-8841-2 | 30/07/2026 | 1.220,00 | 0 | 1.220,00 | Aberto · **plano FX** |
| PY-8841-3 | 15/09/2026 | 915,00 | 0 | 915,00 | Aberto |

---

## Invoice DRAFT — INV-H-8910

| Campo | Valor |
|---|---|
| Status UI | Rascunho |
| Item | HR-BAG-015 · qty 20 · preço unit. **28,00** · Sem desconto · total **560,00** |
| Modo condições | Percentual (50% / 50%) |
| Parcela 1 | 50% · venc. **28/08/2026** · EUR 280,00 |
| Parcela 2 | 50% · venc. **28/10/2026** · EUR 280,00 |
| Obrigações | **não existem** antes da emissão |

---

## Payment — PAY-2026-0042

Valor 1.500,00 · Alocado 600,00 → PY-8841-1 · Residual 900,00.

---

## Payment — PAY-2026-0043 (Ciclo 2)

| Momento | Estado |
|---|---|
| T0 | Não existe |
| T1 | Registrado · 700,00 · residual 700 · PY-8841-2 intacto |
| T2 | Preview alocação 700 → PY-8841-2 |
| T3 | Residual 0 · PY-8841-2 saldo 520 · parcialmente pago |

---

## FX — PY-8841-2

| Visão | Valor |
|---|---|
| Plano | INITIAL · **6,1500** · vigência 21/05/2026 |
| Mercado | **6,2180** · Frankfurter · desatualizado · 27/07/2026 18:00 UTC |
| Executado | **nenhuma execução** (ausência ≠ zero) |
| BRL projetado (plano) | **7.503,00** (= 1.220 × 6,1500) |

Ações UI: Replanejar · Corrigir plano · (quando houver valuation) Reatribuir avaliação cambial.  
Códigos domínio: REFORECAST / CORRECTION / `rebind_valuation` — só em legenda.

---

## Fila AP (MCK-004) — 12 linhas

Ordem: vencidos → hoje → futuros.

| # | Payable | Vencimento | Saldo | FX | Flag |
|---|---|---|---:|---|---|
| 1 | PY-8841-1 | 15/06/2026 | 315,00 | — | vencido |
| 2 | PY-8855-1 | **28/07/2026** | **700,00** | — | **hoje** |
| 3 | PY-8841-2 | 30/07/2026 | 1.220,00 | 6,1500 | aberto · selecionado |
| 4 | PY-8712-1 | 02/08/2026 | 890,00 | 6,1800 | aberto |
| 5 | PY-8790-2 | 05/08/2026 | 420,00 | — | aberto |
| 6 | PY-8860-3 | 20/08/2026 | 880,00 | — | aberto |
| 7 | PY-8888-1 | 25/08/2026 | 550,00 | — | aberto |
| 8 | PY-8890-1 | 01/09/2026 | 310,00 | — | aberto |
| 9 | PY-8701-1 | 10/09/2026 | 1.390,00 | — | aberto |
| 10 | PY-8841-3 | 15/09/2026 | 915,00 | — | aberto |
| 11 | PY-8901-1 | 20/09/2026 | 640,00 | — | aberto |
| 12 | PY-8910-1 | 30/09/2026 | 480,00 | — | aberto |

### KPIs

| KPI | Valor | Contagem |
|---|---|---|
| Vencido | EUR 315,00 | 1 |
| Hoje | EUR 700,00 | 1 |
| Próx. 7d | EUR 2.110,00 | 2 |
| Saldo aberto | EUR 8.710,00 | 12 |
| Sem plano FX | EUR 6.600,00 | 10 |

Drawer PY-8841-2: **Valor sugerido para registro: EUR 700,00** (sem ID Payment futuro).
