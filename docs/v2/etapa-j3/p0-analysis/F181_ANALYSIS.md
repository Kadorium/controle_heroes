# Análise F181 — Fattura_181-con acconti (P0-a)

| Campo | Valor |
|---|---|
| Fonte ZIP | `v1/tests/Fwd_ A_C Ricardo/F181 HK (5).zip` → `F181 HK/Fattura_181-con acconti.pdf` |
| Fixture V2 | `v2/tests/fixtures/ingestion/corpus_181/Fattura_181-con_acconti.pdf` |
| SHA-256 | `88CA8C6401E47C7DC009ACCA328D65A80F28FF618AF458C14507DAFB5416659D` |
| Bytes | 325419 |
| Páginas | 1 |

## Conteúdo relevante (extract pypdf)

- Pagamento: `BONIFICO ANTICIPATO 50%, SALDO 90 GG DFFM`
- Scadenze: `25/03/2026` 82.500,00 € + `30/06/2026` 90.717,30 € (≠ 50/50 exato)
- Total documento: € 173.217,30
- IVA N3.1 exportação
- Múltiplos blocos DDT (371, 372, …)
- Filename contém “acconti”; extract **não** mostra tipo documental `ACCONTO` como enum

## Impacto DEC-ACCONTO

- Fixture **informa** discussão de tipagem / payment terms vs tipo Invoice.
- **Não** autoriza fechar DEC-ACCONTO nem criar enum nova em P0/I4.
- Política vigente do plano: preservar texto bruto; tipos código = FINAL\|PROFORMA; ambiguidade → issue.
