# Cenário canônico — MCK v0.1

**Autoridade:** fonte única de dados para mockups Etapa 5.  
**Não** inserir no banco nem no runtime.  
**Data de referência do cenário:** 2026-07-28 (para vencidos / stale).

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
| Quote EUR/BRL | **6,2180** · Frankfurter · `stale` |

---

## Order — PO-2026-0181

| Campo | Valor |
|---|---|
| Status | CONFIRMED |
| Moeda | EUR |
| Data | 2026-05-12 |
| Fornecedor | Heroes |

### Itens

| Pos. | SKU | Quantidade | Preço unitário | Total linha |
|---:|---|---:|---:|---:|
| 1 | HR-JKET-101 | 100 | EUR 12,50 | EUR 1.250,00 |
| 2 | HR-SHOE-220 | 40 | EUR 45,00 | EUR 1.800,00 |
| 3 | HR-BAG-015 | 20 | — | — |

| Agregado | Valor |
|---|---|
| Total comercial precificado | **EUR 3.050,00** |
| `commercial_total` completo | **null / —** (há item sem preço) |
| Exceção | 1 item sem preço — **nunca** total = 0 |

---

## Invoice ISSUED — INV-H-8841

| Campo | Valor |
|---|---|
| Order | PO-2026-0181 |
| Status | ISSUED |
| Total | EUR 3.050,00 |
| Itens | pos. 1 e 2 (precificados) |
| Documento | anexado |
| PaymentTerms | PERCENT 30 / 40 / 30 |

### Payables (nascidos na emissão)

| Payable | Vencimento | Valor | Alocado | Saldo | Status |
|---|---|---:|---:|---:|---|
| **PY-8841-1** | 2026-06-15 | 915,00 | 600,00 | 315,00 | PARTIALLY_PAID · **vencido** |
| **PY-8841-2** | 2026-07-30 | 1.220,00 | 0,00 | 1.220,00 | OPEN · **FX planejado** |
| **PY-8841-3** | 2026-09-15 | 915,00 | 0,00 | 915,00 | OPEN |

Σ balances = 315 + 1.220 + 915 = **2.450,00 EUR** (coerente: 3.050 − 600 alocado).

---

## Invoice DRAFT — INV-H-8910

| Campo | Valor |
|---|---|
| Order | PO-2026-0181 |
| Status | DRAFT |
| Item | HR-BAG-015 · qty 20 · EUR 28,00 = **560,00** |
| Terms preview | 50 / 50 → 2 Payables **ainda inexistentes** |
| Uso nos mockups Ciclo 1 | aparece na fila Orders (enrichment) e contexto; detalhe = Ciclo 2 |

---

## Payment histórico — PAY-2026-0042

| Campo | Valor |
|---|---|
| Valor | EUR 1.500,00 |
| Alocado | EUR 600,00 |
| Residual | EUR 900,00 |
| Allocation | EUR 600,00 → **PY-8841-1** |
| Documento | comprovante WT-7781 |

**Regra:** Create Payment **não** reduziu Payable; só a Allocation reduziu PY-8841-1.

---

## Jornada futura (MCK-005 / MCK-006) — reservada, não desenhada no Ciclo 1

Origem AP: **PY-8841-2** (saldo antes = EUR 1.220,00).

| Passo | Entidade | Efeito |
|---|---|---|
| Create Payment | **PAY-2026-0043** · EUR 700,00 | Residual Payment = 700,00 · **Payable permanece 1.220,00** |
| Allocate | EUR 700,00 → PY-8841-2 | Payable saldo **520,00** · Payment residual **0,00** · status **PARTIALLY_PAID** |

Preserva invariantes: Create ≠ liquidação; Allocation reduz saldo.

---

## FX (PY-8841-2) — referência Ciclo 1 / detalhe Ciclo 2

| Visão | Valor |
|---|---|
| Plan current | INITIAL · 6,1500 · as-of 2026-05-21 |
| Market | 6,2180 · stale |
| BRL projetado (saldo × plan) | 1.220,00 × 6,1500 ≈ **EUR→BRL 7.503,00** |
| Execution | nenhuma |

---

## Linha temporal (referência 2026-07-28)

```text
2026-05-12  Order CONFIRMED
2026-05-20  INV-H-8841 ISSUED → 3 Payables
2026-05-21  FX plan INITIAL em PY-8841-2
2026-06-15  PY-8841-1 vence
2026-07-10  PAY-2026-0042 registrado
2026-07-10  Allocation 600 → PY-8841-1
2026-07-28  “hoje” nos mockups (PY-8841-1 vencido; quote stale)
2026-07-30  PY-8841-2 vence (em 2 dias)
2026-09-15  PY-8841-3 vence
```

---

## Filas — dados de volume (Ciclo 1)

Além de PO-2026-0181 / payables 8841, as pranchas incluem linhas auxiliares **coerentes com Heroes/EUR** só para densidade visual (não contradizem o núcleo acima). IDs auxiliares: `PO-2026-0175`…`0180`, payables de outras invoices Heroes já liquidadas ou abertas — sem reutilizar totais do núcleo.
