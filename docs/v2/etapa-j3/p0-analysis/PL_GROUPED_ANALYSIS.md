# Análise semântica — PackingListGrouped (P0-a)

## Método

- `pdftotext -layout` (poppler) sobre fixtures V2 hash-verificadas.
- Comparação manual com Fattura/Doganale/PL detalhado (mesmos hashes do inventário).
- Sem adapter de produção.

## Grouped 202

### Colunas aparentes (header)

`Units per CTNS | NCM | Description of goods | Amount | Unit weight | Unit gross weight | Total net weight | Total gross weight`

### Linhas

1. **Comerciais (2):** GRAVITY ARION (600 / 23.688,00); WASH BAG ARION (1000 / 6.500,00)
2. **Embalagem NCM 4819 (3):** Imballaggio / Box thunder / imballo wash bag — Amount 0

### Interpretação candidata (hipótese, não SoT)

| Hipótese | Evidência a favor | Evidência contra |
|---|---|---|
| A — “Units” = total de unidades agregadas mal rotulado | WASH BAG amount = 1000×6,50 | Qty ≠ Fattura/Doganale/PL det.; GRAVITY amount ≠ 600×35,93 |
| B — Documento de planejamento/outro corte | Subconjunto de SKUs | Sem marcador explícito no PDF |
| C — Bug de geração do PDF | Inconsistência matemática vs Fattura | 328 Grouped é coerente |

**Recomendação P0:** tratar Grouped 202 como **fonte de issues de reconciliação**; precedência comercial = Fattura; física detalhada = PL detalhado; aduaneira = Doganale; Grouped = complementar/ambíguo até decisão humana no review.

### Embalagem

Linhas 4819: **não** criar Product/OrderItem; candidatos a `ShipmentPackage` / packaging NCM (Logistics), via commit futuro — não em P0.

## Grouped 328 (controle)

- 1 linha comercial qty 50 + 1 embalagem — coerente com Fattura 328.
- Demonstra que o layout Grouped **pode** alinhar; 202 é caso especial de divergência.

## Grouped 181

- Múltiplas linhas comerciais + embalagens; útil como terceira amostra de layout (P0 inventário apenas).
