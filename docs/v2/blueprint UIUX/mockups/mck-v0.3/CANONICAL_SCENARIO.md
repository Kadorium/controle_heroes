# Cenário canônico — MCK v0.3

**Data de referência:** 2026-07-28  
**Base:** MCK v0.2 + Ciclo 2 (Cockpit, Fatura, Payment, FX)  
**Não** inserir no banco.

---

## Identidade

| Entidade | Valor |
|---|---|
| Supplier | Heroes |
| Order | PO-2026-0181 · Confirmado · EUR · 12/05/2026 |
| Invoice ISSUED | INV-H-8841 · EUR 3.050,00 |
| Invoice DRAFT | INV-H-8910 · EUR 560,00 |
| Payment histórico | PAY-2026-0042 · 1.500 / aloc. 600 / residual 900 |
| Payment Ciclo 2 | PAY-2026-0043 · 700 (após registro) |
| Quote | EUR/BRL 6,2180 · Frankfurter · desatualizado |

---

## Linha temporal por mockup

### T0 — antes de PAY-2026-0043

Usado em: **MCK-001, 002, 003, 004, 007** (+ form de MCK-005).

| Entidade | Estado |
|---|---|
| PY-8841-2 | Saldo **EUR 1.220,00** · Aberto · plano FX 6,1500 |
| PAY-2026-0043 | **Ainda não existe** |

### T1 — após registrar Payment

Usado em: sucesso de **MCK-005**; estado principal de **MCK-006**.

| Entidade | Estado |
|---|---|
| PAY-2026-0043 | Registrado · EUR 700,00 · Residual **700,00** |
| PY-8841-2 | Saldo **permanece 1.220,00** |

### T2 — preview Allocation (MCK-006)

Alocar EUR 700,00 → PY-8841-2  
Saldo projetado obrigação **520,00** · Residual projetado Payment **0,00** · status projetado parcialmente pago.

### T3 — após confirmação (inset / AUX)

Residual Payment 0 · PY-8841-2 saldo 520 · parcialmente pago.

---

## INV-H-8910 — termos de emissão

| Parcela | % | due_date | Valor |
|---|---:|---|---:|
| 1 | 50 | **28/08/2026** | EUR 280,00 |
| 2 | 50 | **28/10/2026** | EUR 280,00 |

Item: HR-BAG-015 · qty 20 · EUR 28,00 · desconto **NONE** · total 560,00.  
Modo PaymentTerms: **PERCENT** (soma 100%). Obrigações **não** existem antes da emissão.

---

## Núcleo financeiro (inalterado v0.2)

Order items / INV-H-8841 payables / PAY-2026-0042 / fila AP 12 linhas / KPIs AP — ver v0.2; copiados nos artboards 001/004.

FX PY-8841-2: INITIAL 6,1500 as-of 21/05/2026 · mercado 6,2180 · BRL projetado 7.503,00 · **sem execução**.
