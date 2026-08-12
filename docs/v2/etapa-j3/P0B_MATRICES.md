# J3-P0-b — Matrizes

Corpus prioritário: Ordine 589, dossier 202 (Fattura, PL det., PL Grouped, Doganale, PrintDecl, Numerário), amostra 328, F181 (estudo), XLSX 758/759.

---

## 5.1 Matriz campo-documento (prioritária)

| Campo | Exemplo real | Layout | Página/locator | Camada PDF | Raw | Normalização | Tipo | Obrig. | Owner | Destino | Matching | Conflito | Editável | Blocker | Teste |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| order_number | 589 | Ordine Heroes | p1 header | content | `589` | str | sim | Orders | Order.code/external_ref | exact/normalized | dup oficial | sim | sim se conflito não waived | golden Ordine |
| order_date | 04/06/2026 | Ordine | p1 | content | IT date | date via parse_it_date | sim | Orders | order_date | — | needs_review | sim | — | parse_it |
| line.code | `I.V. 1` / `I.V. 2` | Ordine | linhas | content | text | SKU candidate | sim | Catalog/Orders | Product/OrderItem | assistido; **não** auto-SKU | ambíguo | sim | policy unmatched | matching |
| line.qty | 14600 / 2000 | Ordine | linhas | content | IT number | Decimal | sim | Orders | qty | — | — | sim | empty≠0 | golden |
| line.unit | PZ | Ordine | linhas | content | `PZ` | UM | sim | Orders | unit | — | — | sim | — | |
| line.price / total | 50 / 830000 | Ordine | linhas/footer | content | IT number | Decimal | sim | Orders | prices | — | math Σ | sim | math fail | |
| invoice_number | 202 | Fattura Heroes | header | content | `202` | str | sim | Billing | invoice_number | supplier+number | dup | sim | sim | |
| invoice_date | 30/03/2026 | Fattura | header | content | IT date | date | sim | Billing | invoice_date | — | — | sim | — | |
| line.ean | 8057628955191 | Fattura | linhas | content | digits | GTIN | não | Catalog | Product | GTIN exact | multi-hit | sim | — | |
| line.qty/um/price/amount | 300 PZ … | Fattura | 7 linhas | content | IT | Decimal+UM | sim | Billing | InvoiceItem | OrderItem assistido | — | sim | lines≠7 | |
| doc_total | 30188,00 | Fattura | footer | content | IT | Decimal | sim | Billing | total | — | Σ lines | sim | math | |
| scadenza[] | 15094×2 | Fattura | block | content | IT | terms | sim | Billing | PaymentTerms | — | ≠Payment | sim | — | anti-Payment |
| payment_terms_text | BONIFICO ANTICIPATO… | Fattura/F181 | footer | content | text | raw preserved | não | Billing | notes/terms text | — | ≠ACCONTO auto | sim | — | DEC-ACCONTO |
| ddt | 389 | Fattura | header | content | text | ref | não | Logistics | ShipmentReference cand. | — | — | sim | — | |
| pl_units_col | 600 / 1000 | PL Grouped 202 | table | content/table | number | Decimal | cond. | Logistics | TBD após review | — | vs Fattura/PL det. | sim | se commit Grouped cego | reconciler |
| pl_detail_ctns | 1…100 | PL det. 202 | multipage | content/table | int | int | sim p/ PL | Logistics | packages/contents | — | — | sim | — | |
| doganale_qty_um | 300 SET | Doganale | lines | content | number+UM | Decimal; UM≠PZ | sim | Customs | DoganaleLine | Fattura line | SET vs PZ label | sim | — | |
| doganale_weights | 850 / 1000 | Doganale | footer | content | IT | Decimal kg | sim | Customs | weights | vs PL | 916 vs 1000 PL | sim | — | |
| country_of_origin_acquisition | **china** | Doganale/PL 202 | caixa | **annotation FreeText** | `china` | country | sim p/ Customs | Customs | origin | — | vs content `Italy` | sim | unresolved mismatch | **annot vs content** |
| country_ghost | Italy | mesmos | mesma Y label | **content stream** | `Italy` | — | não (ghost) | — | — | — | mismatch issue | — | — | |
| country_328 | Italy | Doganale/PL 328 | campo | **content** (sem FreeText china) | `Italy` | country | sim | Customs | origin | — | — | sim | — | layout-specific |
| funding_refs | INV 181/202/… | Numerário | header | content | text | list | sim | Customs | FundingRequest | Invoice match | multi | sim | — | |
| funding_fx / totals | FOB/CIF/FX | Numerário | body | content | IT/BR numbers | Decimal+FX | sim | Customs | bases/tax | — | math | sim | confirm forbidden | |
| print_ref | fattura 202 | PrintDecl | body | content | text | ref | não | Documents | metadata/full_text | Invoice | — | sim | — | |
| packaging_ncm | 4819… | PL Grouped | lines | content | NCM | code | não | Logistics | packaging | — | ≠Product | sim | criar Product | |

---

## 5.2 Matriz entre documentos

| Fato | Ordine | Fattura | PL detalhado | PL agrupado | Doganale | Numerário | Declaration | Owner canônico | Regra de precedência | Divergência |
|---|---|---|---|---|---|---|---|---|---|---|
| Pedido 589 | SoT | — | — | — | — | — | — | Orders | Ordine | Isolado do 202 |
| Invoice #202 | — | SoT comercial | mesmo # | mesmo # | mesmo # | um de N | ref texto | Billing | Fattura para $ / linhas comerciais | Datas 30/03 vs 16/04 export |
| Qty SKU | — | PZ SoT comercial | Σ CTNS alinhável | **agregado/diverge (202)** | SET = qty Fattura | consol. | — | Fattura comercial; Doganale aduaneira; PL det. físico | Grouped 202 ≠ SoT |
| Amount € | — | SoT | — | diverge (202) | = Fattura | parte FOB | — | Billing | — |
| NCM produto | — | — | sim | sim+4819 | sim | — | — | Customs | Embalagem ≠ Product |
| Pesos | — | — | 850/916/1000 | parciais | 850/1000 | — | — | Doganale aduaneiro | Gross PL vs Doganale |
| Origin | — | — | annot china | annot china | annot china | — | — | Annotation Contents (layout 202); 328 = content Italy | content Italy ghost |
| UM | — | PZ | CTNS/units | ambígua | SET | — | — | Não colapsar | labels |
| Pagamento | — | terms/scadenze | — | — | — | PIX/banco | — | Terms≠Payment; Funding≠Payment | — |

**Precedência Grouped:** não definida como SoT; reconciler gera issues até review.

---

## 5.3 Matriz owner/API/idempotência

| Operação | Owner | API atual | Lifecycle | Natural key | Operation key | Fingerprint | Version/concorrência | Retry | Gap público | Recomendação |
|---|---|---|---|---|---|---|---|---|---|---|
| promote bytes | Documents | `store_document` | oficial | file_hash (dedupe físico ≠ occurrence) | `ingest:{attempt}:documents:promote:{hash}` | hash+filename policy | Document.version | ledger replay | sem find-by-hash oficial; sem quarantine | Promote só no commit; ledger; opcional find-by-hash depois |
| link | Documents | `link_document` | link | (doc, entity, role) unique | `…:link:{entity}` | ids+role | — | replay | — | Só pós entidade |
| create supplier | Catalog | POST | master | code unique | `…:catalog:supplier:{code\|fp}` | payload canônico | **sem version no response** | 409+payload diverge = **conflito explícito** (não GET cego) | version pública opcional | Ledger + natural key; conflito se fingerprint≠ |
| create product | Catalog | POST | master | sku unique | `…:product:{sku}` | payload | idem | idem | idem | idem |
| create/update order | Orders | POST/PATCH | **DRAFT** | code unique | `…:orders:create:{code}` | payload | version+updated_at | replay | idempotency_key HTTP | Preferir key; senão code+ledger |
| confirm order | Orders | POST confirm | CONFIRMED | — | `…:orders:confirm:{id}` | version | expected_version | replay | — | **Só explícito** |
| create invoice | Billing | POST via order | **DRAFT** | (supplier, number) | `…:billing:invoice:{sup}:{num}` | payload | version | replay | exige Order CONFIRMED; sem key HTTP | Gate CONFIRMED; ledger; key desejável |
| issue invoice | Billing | issue | ISSUED+AP | — | — | — | — | — | — | **Fora** commit ingestão |
| create shipment | Logistics | POST | PLANNED | code | `…:logistics:ship:{code}` | payload | version | replay | key HTTP | ledger+code |
| advance shipment | Logistics | advance | BOOKED+ | — | — | — | — | — | — | **Fora** auto |
| create process | Customs | POST | DRAFT | — | `…:customs:process:{fp}` | payload | version | replay | key | ledger |
| doganale version | Customs | POST | DRAFT | + idempotency_key | usar key nativa | payload | version | nativo | — | Preferir API existente |
| funding create | Customs | POST | **DRAFT** | + key | nativa | payload | version | nativo | — | **Proibido** confirm |
| funding confirm | Customs | confirm | CONFIRMED+AP | — | — | — | — | — | — | **Fora** |
| audit | Audit | record_event | append | — | — | — | mesma UoW | — | — | Sempre |

**Catalog 409:** se operation_key nova com sku/code existente mas fingerprint divergente → **rejeitar** com conflito; não sobrescrever via GET.

---

## 5.4 Matriz layouts/adapters

| Família | Layout | Fixture | Sinais | Camadas extração | Adapter candidato | OCR | Golden | Cobertura |
|---|---|---|---|---|---|---|---|---|
| Ordine Heroes | v1 | Ordine_589 | “Ordine”, N3.1 | content | `ordine_heroes_v1` | fallback | I3 | I3 |
| Fattura Heroes | v1 | Fattura_202 / 328 / 181 | Fattura, scadenze, DDT | content | `fattura_heroes_v1` | fallback | I4 | I4 |
| PL detalhado | multipage | PL_202 / 328 / 181 | CTNS seq | content/table | `pl_detailed_heroes_v1` | fallback | I5 | I5 |
| PL agrupado | 1p | Grouped_202/328/181 | poucas linhas+4819 | content/table | `pl_grouped_heroes_v1` | fallback | golden **issues** | I5 obrigatório |
| Doganale | 1p | Doganale_202/328/181 | SET, pesos | content + **annots (202)** | `doganale_heroes_v1` | fallback | I5 | I5 |
| Numerário BR | 1p | Solicitacao | DUIMP, FX, PIX | content posicional | `numerario_br_v1` | fallback | I6 | I6 |
| PrintDecl | 2p | Print_* | Y*, fattura N | content | `print_decl_heroes_v1` | se ruído | meta | I5 |
| Heroes XLSX | sheets | 758/759 | sheet types | xlsx | `heroes_xlsx_v1` | N/A | I7 | I7 |

---

## 5.5 Matriz qualidade hipotética

| Documento | Campos críticos | Resultado esperado | Locator obrig. | Issues obrigatórias | Blockers | Calibrar em |
|---|---|---|---|---|---|---|
| Ordine 589 | nº, data, 2 lines, totais | lines=2; empty≠0 | sim nº/linhas | unmatched SKU se policy | unmatched blocker policy | **I3** precisão/cobertura |
| Fattura 202 | nº, 7 lines, 30188, 2 scadenze | lines=7; sem Payment | sim | texto antecipo | Order CONFIRMED | **I4** |
| PL det. 202 | CTNS/qty, NCM, origin annot | qty alinhável Fattura | origin annot Rect | annot vs content | origin unresolved | **I5** |
| PL Grouped 202 | classificar+extrair+reconcilar | issues vs Fattura/PL | origin | granularidade/amounts | commit cego Grouped | **I5** (não % inventado) |
| Doganale 202 | 7 SET, pesos, origin annot | match qty/valor Fattura | origin | SET≠PZ; annot | origin | **I5** |
| Numerário | multi-INV, FX, totais | DRAFT only | parcial | math | confirm funding | **I6** |
| PrintDecl | ref+full_text | metadata | opcional | ruído Y | — | I5 |
| F181 | terms/scadenze | texto bruto; issue tipagem | — | ACCONTO ambíguo | — | pós-DEC |

Sem percentuais inventados. Métricas a calibrar pós-I3: field/row precision, false conflict rate, review time.

---

## 5.6 Matriz E2E

| Documento | Upload | Classificação | Extração | Revisão | Correção | Matching | Preview | Commit | Reupload | Deep link |
|---|---|---|---|---|---|---|---|---|---|---|
| Ordine 589 | I3 | I3 | I3 | I3 | I3 | I3 | I3 | Orders DRAFT I3 | occurrence I3 | Order |
| Fattura 202 | I4 | I4 | I4 | I4 | I4 | Order/Product I4 | I4 | Invoice DRAFT I4 | I4 | Invoice |
| PL detalhado | I5 | I5 | I5 | I5 | I5 | I5 | I5 | Shipment PLANNED I5 | I5 | Shipment |
| PL Grouped | I5 | I5 | I5 | reconciler | I5 | I5 | issues | só se aprovado | I5 | — |
| Doganale | I5 | I5 | annot+content | I5 | I5 | I5 | I5 | Customs DRAFT | I5 | Doganale |
| PrintDecl | I5 | I5 | text | meta | — | ref | link | promote+link | I5 | Document |
| Numerário | I6 | I6 | I6 | I6 | I6 | multi-INV | I6 | Funding DRAFT | I6 | Funding |
| Dossiê 202 | I5–I6 | sim | sim | cross-doc | sim | sim | multi | PARTIAL-aware | sim | multi |
| XLSX | I7 | I7 | I7 | I7 | I7 | I7 | I7 | Orders/Billing | I7 | entidades |

Suites: `e2e:j3-ordine`, `e2e:j3-fattura`, `e2e:j3-dossier-202`, `e2e:j3-numerario`, `e2e:j3-xlsx`.
