# J3-P0-a — Forense e evidências

| Campo | Valor |
|---|---|
| Data | 2026-08-04 |
| Roadmap | 0.5.64 (IN_PROGRESS) → fechamento P0 |
| Tooling | `v2/.venv` + **pypdf**; poppler `pdftotext -layout`; **pdfplumber não usado** (ausente no venv; não adicionado a requirements) |
| Script | [`p0-analysis/forensic_inventory.py`](p0-analysis/forensic_inventory.py) |
| Inventário JSON | [`p0-analysis/INVENTORY.json`](p0-analysis/INVENTORY.json) |
| Manifest cópias | [`p0-analysis/FIXTURE_COPY_MANIFEST.json`](p0-analysis/FIXTURE_COPY_MANIFEST.json) |

## 1. Baseline de execução

- Branch: `main` @ `67f73151d8b19d879810fda630766602e9785dac`
- WIP pré-existente **preservado** (sem commit/reset/clean)
- Alembic head: `015`
- Blueprint: 0.2.16 (não alterado nesta etapa)
- J#5 DONE; J#3 era a próxima fase autorizada

## 2. Fixtures V2 (cópias hash-verificadas)

Fonte: `v1/tests/Fwd_ A_C Ricardo/` (+ ZIP F181 + e2e xlsx). Destino: `v2/tests/fixtures/ingestion/`. Fontes V1 **não alteradas**.

| Destino | SHA-256 | Bytes | Págs | Chars (Σ extract) |
|---|---|---|---|---|
| `corpus_589/Ordine_589.pdf` | `85EDC96C…4D4C0E` | 60144 | 1 | 1416 |
| `corpus_202/Fattura_202.pdf` | `C0B047AD…67B023` | 61120 | 1 | 1774 |
| `corpus_202/PackingListGrouped_202.pdf` | `63893C38…50AC2C` | 170146 | 1 | 1357 |
| `corpus_202/PackingList_202.pdf` | `6FB13DC6…CDA65E` | 168349 | 7 | 15549 |
| `corpus_202/FatturaDoganale_202.pdf` | `41692600…7F3A3E44` | 170147 | 1 | 1441 |
| `corpus_202/PrintDeclaration_202.pdf` | `1F815ECE…65BC52C4` | 107691 | 2 | 7355 |
| `corpus_202/Solicitacao_Numerario.pdf` | `7CBAAA17…1E9999F` | 30386 | 1 | 2019 |
| `corpus_328/*` (5 PDFs) | ver INVENTORY | — | 1–2 | ≥1000 cada |
| `corpus_181/Fattura_181-con_acconti.pdf` | `88CA8C64…5416659D` | 325419 | 1 | 1977 |
| `corpus_181/*` (mais 4 PDFs do ZIP) | ver manifest | — | — | — |
| `xlsx/ordine758.xlsx` / `759.xlsx` | ver manifest | — | — | — |

MIME: todos os PDFs `%PDF` → `application/pdf`. XLSX → ZIP/`PK`.

## 3. H-P0-01 — Corpus digital

**CONFIRMADA** para o corpus prioritário: todos os PDFs analisados têm texto digital extraível (chars ≫ 0; PL detalhado 202 = 15549 chars / 7 págs). OCR **não** necessário para esses casos. PrintDeclaration tem ruído de ordem de glyphs, ainda digital.

## 4. H-P0-02 — Origin annotations

### Família 202 (CONFIRMADA)

| Arquivo | FreeText Contents | Rect (PDF user space) | Content stream |
|---|---|---|---|
| `FatturaDoganale_202.pdf` p1 | `china` | `[190.17, 395.58, 221.92, 412.62]` | `Italy` @ x=318 y=371 |
| `PackingListGrouped_202.pdf` p1 | `china` | `[186.19, 433.44, 217.93, 450.47]` | `Italy` @ x=318 y=305 |
| `PackingList_202.pdf` p6 | `china` | `[195.07, 225.90, 226.81, 242.94]` | `Italy` @ x=318 y=5508 |

- Sem AcroForm fields.
- Annotations: `/Square` (caixa) + `/FreeText` (valor), nome `Jessica`.
- `pdftotext -layout`: `chinaItaly` ou `china` + linha `Italy`.
- pypdf visitor no content: só `Italy`.

**Mecanismo:** valor de negócio na FreeText; `Italy` = fantasma no content na faixa do rótulo.

### Família 328 (NÃO generalizar)

| Arquivo | FreeText china | Content |
|---|---|---|
| Doganale/PL/Grouped 328 | **Ausente** | `Italy` no content; pdftotext: `Country of origin/acquisition: Italy` |

**Veredito H-P0-02: PARCIAL** — mecanismo annotation×content confirmado **somente** nos layouts 202 amostrados; F328 não replica FreeText `china`. Regra de extração: **por layout/versão**, não global.

## 5. H-P0-03 — Packing List Grouped

### Observado (202)

Layout `pdftotext` (trecho):

| Units col | NCM | Description | Amount | unit net | unit gross | tot net | tot gross |
|---|---|---|---|---|---|---|---|
| 600 | 4202… | GRAVITY ARION | 23.688,00 | 0,90 | 1,00 | 690 | 747 |
| 1000 | 4202… | WASH BAG ARION | 6.500,00 | 0,16 | 0,17 | 160 | 169 |
| 50/30/20 | 4819… | embalagens | 0 | … | … | … | … |

Header imprime `Units per CTNS`, mas os valores **600/1000** comportam-se como **totais de unidades agregadas**, não “unidades por caixa”.

### Relação com Fattura / Doganale / PL detalhado 202

| SKU | Fattura qty (PZ) | Doganale qty (SET) | PL detalhado (Σ units) | Grouped “Units” |
|---|---|---|---|---|
| GRAVITY ARION | 300 | 300 | 300 (CTNS 1–50 ×6) | **600** |
| WASH BAG ARION | 300 | 300 | 300 | **1000** |
| Outros 5 SKUs Fattura | presentes | presentes | presentes | **ausentes** no Grouped |
| Amount GRAVITY | 10.779 | 10.779 | — | **23.688** |
| Amount WASH BAG ARION | 1.950 | 1.950 | — | **6.500** (=1000×6,50) |

**Conclusão semântica (P0):** Grouped 202 **não** é SoT comercial nem espelho 1:1 do detalhado. É vista agregada/alternativa com:

- granularidade diferente (só 2 SKUs comerciais + embalagem);
- coluna “Units per CTNS” semanticamente ambígua (totais ≠ per-CTN do detalhado);
- amounts inconsistentes com Fattura/Doganale para GRAVITY;
- linhas 4819 = embalagem (não criar Product/OrderItem).

**Grouped 328** (controle): 1 SKU comercial qty **50** + 1 embalagem — alinhável à Fattura 328. Mostra que o *layout* Grouped pode ser coerente; o *conteúdo* 202 é o caso de ambiguidade/reconciliação.

**Veredito H-P0-03: CONFIRMADA** — diferente ≠ automaticamente “errado”; sem base para descartar; cobertura obrigatória de reconciliação.

Detalhe: [`PL_GROUPED_ANALYSIS.md`](p0-analysis/PL_GROUPED_ANALYSIS.md).

## 6. H-P0-04 — F181

**CONFIRMADA.** Presente em `v1/tests/Fwd_ A_C Ricardo/F181 HK (5).zip` → copiada para `v2/tests/fixtures/ingestion/corpus_181/Fattura_181-con_acconti.pdf` (SHA `88CA8C64…`).

Texto: `BONIFICO ANTICIPATO 50%, SALDO 90 GG DFFM`; scadenze 82.500 + 90.717,30; total €173.217,30; múltiplos DDT; **sem** string literal “ACCONTO” como tipo de fatura no extract amostrado.

**Não fecha DEC-ACCONTO.** Informa análise; tipagem permanece FINAL/PROFORMA no código; issue se ambíguo.

## 7. Fixtures ausentes / gaps

| Gap | Impacto |
|---|---|
| Ordine correspondente à Fattura 202 | I4 sem pedido nativo no corpus |
| PDF escaneado representativo | OCR real = backlog |
| `Fattura_181` solta (fora do ZIP) | Mitigado pela cópia V2 |
| pdfplumber no venv produção | Não bloqueia P0; pypdf+poppler bastaram |

## 8. Gate P0-a

**PASS** — inventário, hashes, origin reproduzível, PL Grouped documentado, F181 verificada, gaps explícitos.

## 9. Comando reproduzível

```bat
cd v2
.venv\Scripts\python.exe ..\docs\v2\etapa-j3\p0-analysis\forensic_inventory.py
```
