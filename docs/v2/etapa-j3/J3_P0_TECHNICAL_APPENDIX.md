# J3-P0 — Technical Appendix

Material para análise aprofundada. Decisão operacional: [`J3_P0_ADVISOR_HANDOFF.md`](J3_P0_ADVISOR_HANDOFF.md).

Artefatos brutos **não** embutidos: ver §8 (ponteiros).

---

## 1. Inventário fixtures V2 (hash-verificadas)

Fonte V1 / ZIP não alterada. Destino: `v2/tests/fixtures/ingestion/`.

| Destino | SHA-256 (prefix) | Bytes | Págs | Chars Σ |
|---|---|---|---|---|
| `corpus_589/Ordine_589.pdf` | `85EDC96C…` | 60144 | 1 | 1416 |
| `corpus_202/Fattura_202.pdf` | `C0B047AD…` | 61120 | 1 | 1774 |
| `corpus_202/PackingListGrouped_202.pdf` | `63893C38…` | 170146 | 1 | 1357 |
| `corpus_202/PackingList_202.pdf` | `6FB13DC6…` | 168349 | 7 | 15549 |
| `corpus_202/FatturaDoganale_202.pdf` | `41692600…` | 170147 | 1 | 1441 |
| `corpus_202/PrintDeclaration_202.pdf` | `1F815ECE…` | 107691 | 2 | 7355 |
| `corpus_202/Solicitacao_Numerario.pdf` | `7CBAAA17…` | 30386 | 1 | 2019 |
| `corpus_328/*` (5 PDFs) | ver manifest | — | 1–2 | ≥1000 |
| `corpus_181/Fattura_181-con_acconti.pdf` | `88CA8C64…` | 325419 | 1 | 1977 |
| `corpus_181/*` (+4 do ZIP) | ver manifest | — | — | — |
| `xlsx/ordine758.xlsx` / `759.xlsx` | ver manifest | — | — | — |

Manifest completo: [`p0-analysis/FIXTURE_COPY_MANIFEST.json`](p0-analysis/FIXTURE_COPY_MANIFEST.json).

MIME: PDFs `%PDF`; XLSX `PK`.

---

## 2. Origin — annotation × content

### Família 202

| Arquivo | FreeText Contents | Rect | Content stream |
|---|---|---|---|
| `FatturaDoganale_202.pdf` p1 | `china` | `[190.17, 395.58, 221.92, 412.62]` | `Italy` @ x=318 y=371 |
| `PackingListGrouped_202.pdf` p1 | `china` | `[186.19, 433.44, 217.93, 450.47]` | `Italy` @ x=318 y=305 |
| `PackingList_202.pdf` p6 | `china` | `[195.07, 225.90, 226.81, 242.94]` | `Italy` @ x=318 y=5508 |

- Sem AcroForm; annotations `/Square` + `/FreeText` (`T=Jessica`).
- `pdftotext -layout`: `chinaItaly` ou linhas adjacentes.
- pypdf visitor no content: só `Italy`.

### Família 328

Sem FreeText `china`; content/pdftotext: `Country of origin/acquisition: Italy`.

**Implicação:** preferência annotation **por layout versionado**, não regra global.

---

## 3. Packing List Grouped — semântica

### Grouped 202 (pdftotext)

| Units col | NCM | Description | Amount |
|---|---|---|---|
| 600 | 4202… | GRAVITY ARION | 23.688,00 |
| 1000 | 4202… | WASH BAG ARION | 6.500,00 |
| 50/30/20 | 4819… | embalagens | 0 |

Header `Units per CTNS` vs valores que se comportam como **totais agregados**.

| SKU | Fattura/Doganale/PL det. | Grouped “Units” / Amount |
|---|---|---|
| GRAVITY | 300 / 10.779 | **600** / **23.688** |
| WASH BAG ARION | 300 / 1.950 | **1000** / **6.500** |
| Outros 5 SKUs | presentes | **ausentes** |

Grouped 328 (controle): qty 50 alinhável à Fattura 328.

**Precedência:** Fattura (comercial $); PL detalhado (físico); Doganale (aduaneiro); Grouped = issues de reconciliação até review. Embalagem 4819 ≠ Product.

Detalhe: [`p0-analysis/PL_GROUPED_ANALYSIS.md`](p0-analysis/PL_GROUPED_ANALYSIS.md).

---

## 4. F181

| Campo | Valor |
|---|---|
| ZIP | `v1/tests/Fwd_ A_C Ricardo/F181 HK (5).zip` |
| Fixture V2 | `corpus_181/Fattura_181-con_acconti.pdf` |
| SHA-256 | `88CA8C6401E47C7DC009ACCA328D65A80F28FF618AF458C14507DAFB5416659D` |
| Extract | `BONIFICO ANTICIPATO 50%, SALDO 90 GG DFFM`; scadenze 82500 + 90717,30; total 173217,30 |

Informa DEC-ACCONTO; **não** fecha enum. Ver [`p0-analysis/F181_ANALYSIS.md`](p0-analysis/F181_ANALYSIS.md).

---

## 5. Matriz campo-documento (prioritária)

| Campo | Exemplo | Layout | Locator | Camada | Raw | Owner | Destino | Conflito / Blocker | Teste |
|---|---|---|---|---|---|---|---|---|---|
| order_number | 589 | Ordine | header | content | `589` | Orders | code/external_ref | dup | golden |
| line.code | I.V. 1/2 | Ordine | linhas | content | text | Catalog/Orders | match assistido | não auto-SKU | matching |
| invoice_number | 202 | Fattura | header | content | `202` | Billing | invoice_number | dup | |
| line×7 + total | 30188 | Fattura | linhas/footer | content | IT num | Billing | items/total | math; ≠Payment | |
| scadenza[] | 15094×2 | Fattura | block | content | IT | Billing | PaymentTerms | ≠Payment | anti-Payment |
| payment_terms_text | BONIFICO… | Fattura/F181 | footer | content | text | Billing | notes | ≠ACCONTO auto | DEC |
| pl_units_col | 600/1000 | Grouped 202 | table | content/table | num | Logistics | TBD review | vs Fattura | reconciler |
| pl_detail_ctns | 1…100 | PL det. | multipage | content/table | int | Logistics | packages | — | |
| doganale qty/UM | 300 SET | Doganale | lines | content | num+UM | Customs | DoganaleLine | SET≠PZ | |
| origin | china | Doganale/PL 202 | caixa | **annotation** | `china` | Customs | origin | vs content Italy | annot vs content |
| origin ghost | Italy | mesmos | mesma Y | **content** | `Italy` | — | — | mismatch issue | |
| origin 328 | Italy | 328 | campo | content | Italy | Customs | origin | — | layout-specific |
| funding_refs | INV 181/202/… | Numerário | header | content | text | Customs | Funding DRAFT | multi | confirm forbidden |
| print_ref | fattura 202 | PrintDecl | body | content | text | Documents | meta/full_text | — | |
| packaging_ncm | 4819 | Grouped | lines | content | NCM | Logistics | packaging | ≠Product | |

---

## 6. Matriz entre documentos

| Fato | Ordine | Fattura | PL det. | PL agrup. | Doganale | Numerário | Decl. | Owner / precedência | Divergência |
|---|---|---|---|---|---|---|---|---|---|
| Pedido 589 | SoT | — | — | — | — | — | — | Orders | Isolado do 202 |
| Inv #202 | — | SoT $ | mesmo # | mesmo # | mesmo # | um de N | ref | Billing comercial | Datas 30/03 vs 16/04 |
| Qty SKU | — | PZ SoT | Σ alinhável | **diverge 202** | SET=Fattura | consol. | — | Fattura / Doganale / PL det. | Grouped ≠ SoT |
| Amount | — | SoT | — | diverge 202 | =Fattura | parte FOB | — | Billing | |
| NCM | — | — | sim | +4819 | sim | — | — | Customs; emb. ≠ Product | |
| Pesos | — | — | 850/916/1000 | parcial | 850/1000 | — | — | Doganale | Gross PL |
| Origin | — | — | annot china | annot china | annot china | — | — | Layout 202 annot; 328 content | Italy ghost |
| Pagamento | — | terms | — | — | — | PIX | — | ≠Payment | |

---

## 7. Matriz owner/API/idempotência

| Operação | Owner | API | Lifecycle | Natural key / key | Concorrência | Gap / regra |
|---|---|---|---|---|---|---|
| promote | Documents | store_document | oficial | hash físico ≠ occurrence | version | só no commit; ledger |
| link | Documents | link_document | link | (doc,entity,role) | — | pós entidade |
| supplier/product | Catalog | POST | master | code/sku | sem version no response | 409+fp diverge = conflito |
| order create/patch | Orders | POST/PATCH | DRAFT | code | version | ledger; key desejável |
| confirm order | Orders | confirm | CONFIRMED | — | expected_version | **só explícito** |
| invoice create | Billing | POST | DRAFT | (sup, number) | version | exige CONFIRMED |
| issue / advance / funding confirm | — | — | — | — | — | **fora** commit ingestão |
| doganale / funding create | Customs | POST + key nativa | DRAFT | idempotency_key | version | preferir nativo |
| audit | Audit | record_event | append | — | mesma UoW | sempre |

Ledger Ingestion: `operation_key` + `command_fingerprint` + replay; key+payload divergente = rejeitar.

---

## 8. Matriz layouts / qualidade / E2E

### Layouts

| Família | Fixture | Camadas | Adapter | Cobertura |
|---|---|---|---|---|
| Ordine Heroes | Ordine_589 | content | ordine_heroes_v1 | I3 |
| Fattura Heroes | Fattura_202/328/181 | content | fattura_heroes_v1 | I4 |
| PL detalhado | PL_* | content/table | pl_detailed_heroes_v1 | I5 |
| PL agrupado | Grouped_* | content/table | pl_grouped_heroes_v1 | I5 (issues) |
| Doganale | Doganale_* | content + annots (202) | doganale_heroes_v1 | I5 |
| Numerário | Solicitacao | content | numerario_br_v1 | I6 |
| PrintDecl | Print_* | content | print_decl_heroes_v1 | I5 |
| XLSX | 758/759 | xlsx | heroes_xlsx_v1 | I7 |

### Qualidade (hipóteses; % após I3)

| Doc | Críticos | Issues/blockers chave | Calibrar |
|---|---|---|---|
| Ordine 589 | nº, 2 lines, totais | unmatched SKU | I3 |
| Fattura 202 | 7 lines, 30188, scadenze | Order CONFIRMED; ≠Payment | I4 |
| PL/Doganale 202 | qty, origin annot | annot vs content | I5 |
| Grouped 202 | classificar+reconciliar | granularidade | I5 |
| Numerário | multi-INV, FX | confirm forbidden | I6 |

### E2E (suites nomeadas)

`e2e:j3-ordine` · `e2e:j3-fattura` · `e2e:j3-dossier-202` · `e2e:j3-numerario` · `e2e:j3-xlsx`

Jornada Ordine: upload→classificação→extração→revisão→correção→matching→preview→commit DRAFT→reupload occurrence→deep link.

---

## 9. Comando reproduzível

```bat
cd v2
.venv\Scripts\python.exe ..\docs\v2\etapa-j3\p0-analysis\forensic_inventory.py
```

Tooling: pypdf no venv V2; poppler `pdftotext`; pdfplumber **não** em requirements de produção.

---

## 10. Ponteiros a artefatos brutos

| Path | Uso |
|---|---|
| [`p0-analysis/INVENTORY.json`](p0-analysis/INVENTORY.json) | Inventário máquina completo |
| [`p0-analysis/FIXTURE_COPY_MANIFEST.json`](p0-analysis/FIXTURE_COPY_MANIFEST.json) | Hashes cópias |
| [`p0-analysis/forensic_inventory.py`](p0-analysis/forensic_inventory.py) | Script descartável |
| `p0-analysis/layout_*.txt` | pdftotext -layout |
| [`P0A_FORENSIC_REPORT.md`](P0A_FORENSIC_REPORT.md) | Relato forense histórico |
| [`P0B_MATRICES.md`](P0B_MATRICES.md) | Matrizes históricas integrais |
| [`P0B_DECISIONS.md`](P0B_DECISIONS.md) | Propostas pré-ratificação |
| `v2/tests/fixtures/ingestion/**` | Fixtures |
