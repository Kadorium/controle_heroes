# J3-P0 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | J3-P0 — Forense, matrizes, decisões + consolidação de handoff |
| Status | **DONE** |
| Data | 2026-08-04 |
| Roadmap | **0.5.66** (após esta consolidação) |
| Alembic | `015` (sem migration) |
| I0 | **NOT_STARTED** |
| Apêndice técnico | [`J3_P0_TECHNICAL_APPENDIX.md`](J3_P0_TECHNICAL_APPENDIX.md) |

Este documento é **autocontido** para decisão. Evidência bruta (JSON, layouts, fixtures) permanece no repositório e não precisa ser lida para ratificar o caminho.

---

## 1. Estado anterior → atual

| Momento | Estado |
|---|---|
| Antes do P0 | Roadmap 0.5.63; J#5 DONE; J#3 TODO (planejar); foothold `parse_it` only |
| Após P0-a/b | Roadmap 0.5.65; J#3 IN_PROGRESS; P0-a/P0-b DONE; I0 bloqueado até advisor |
| Agora | Pacote advisor consolidado (≤2 MD); **decisões P0 ratificadas** abaixo; I0 ainda não autorizado |

---

## 2. Hipóteses H-P0 (resultado)

| ID | Veredito | Resumo |
|---|---|---|
| H-P0-01 | **CONFIRMADA** | Corpus prioritário digital; OCR não necessário |
| H-P0-02 | **PARCIAL** | Layout 202: FreeText `china` + content `Italy`; F328 **sem** FreeText china |
| H-P0-03 | **CONFIRMADA** | PL Grouped 202 ambíguo/diferente; não pré-condenar |
| H-P0-04 | **CONFIRMADA** | F181 no ZIP, fixture V2 hash-ok; não fecha DEC-ACCONTO |
| H-P0-05 | **CONFIRMADA** (necessidade) | Agrupamento funcional sim; persistência = relação+projeção |
| H-P0-06 | **CONFIRMADA** | Quarantine ≠ Document oficial; promote no commit |
| H-P0-07 | **CONFIRMADA** | Ledger obrigatório; extensões owner sob demanda |
| H-P0-08 | **CONFIRMADA** | I4 A/B/C1/C2; Billing CONFIRMED preservado |

---

## 3. Gates

| Gate | Resultado |
|---|---|
| P0-a (forense) | **PASS** |
| P0-b (matrizes + decisões) | **PASS** |
| Consolidação handoff | **PASS** (este pacote) |

---

## 4. Entregas P0

- Fixtures hash-verificadas em `v2/tests/fixtures/ingestion/`
- Forense reproduzível (`p0-analysis/`)
- Matrizes campo/cross/owner/layout/qualidade/E2E
- Protocolo permanente de handoff (§6.1 em `.cursor/rules/epic-v2.mdc` + `docs/README.md` §3)
- **Sem** adapters, models, migrations, APIs, FE, requirements de produção

---

## 5. Decisões ratificadas (canônicas para I0+)

Substitui, para fins de decisão, as “recomendações abertas” de `P0B_DECISIONS.md` (preservado como histórico interno).

### 5.1 Agrupamento documental

- Aceitar **relação explícita opcional** + **projeção por business keys**.
- Não criar agregado rico prematuramente.
- Implementar a relação em **J3-I1**; **J3-I0** foca occurrence, quarantine, hash, segurança e upload.

### 5.2 Hash e identidade documental

Distinguir: reuso físico do blob · occurrence · identidade de negócio · versão · Document oficial · DocumentLink.

- Hash idêntico pode permitir reuso físico dos bytes.
- Hash **não** implica reutilizar automaticamente a identidade de um Document oficial.
- Document oficial só pode ser reutilizado/relinkado se contexto, papel documental e identidade de negócio forem compatíveis.

### 5.3 Quarantine e promoção

- Upload permanece na quarantine.
- Aprovação de campo **não** promove o arquivo.
- Promotion somente no **commit aprovado**.
- Links oficiais somente após existência da entidade owner.

### 5.4 Retenção

- REJECTED / ABANDONED: purge dos bytes após **30 dias** (configurável).
- Documento em revisão ativa **não** é removido.
- Preservar metadata mínima, hash, motivo, ator e Audit.
- Oficiais: política imutável de Documents.

### 5.5 Idempotência

- Ledger da Ingestion **obrigatório**.
- Extensões públicas nos owners **somente** quando o vertical provar necessidade.
- Não criar fundação transversal ampla por antecipação.
- 409 + entidade existente com fingerprint divergente = **conflito explícito** (não GET cego).

### 5.6 Política I4 (Order × Fattura)

| Caminho | Política |
|---|---|
| **A** | Order CONFIRMED existente — **preferido** |
| **B** | Order DRAFT existente — confirmação **separada e explícita** |
| **C1** | Sem Order — criar reconstrução DRAFT e aguardar confirmação |
| **C2** | Create+confirm na mesma sessão — **exceção** com warning, reason, provenance, Audit, preview separado |

**Nunca:** Invoice com Order DRAFT; confirmação silenciosa; Payment automático; ACCONTO inferido.

### 5.7 UI

- SCR-037 — fila
- SCR-038 — workspace de conferência
- SCR-039 — preview, commit e resultado do ledger
- Integração com SCR-017 (matching SKU)

(Atualização formal Blueprint UI/UX = entrega futura, não bloqueia I0.)

### 5.8 RBAC (dupla autorização)

Commit exige **simultaneamente**:

1. permissão adequada `ingestion:*`;
2. permissão de escrita do módulo owner.

Exemplos: Orders/Catalog → comprador com perms dos owners; Billing → financeiro; Logistics → operador/logística; Customs → aduana; waive → admin ou gestor (salvo L-005).

`ingestion:commit` **não** concede sozinho escrita a todos os owners.

### 5.9 XLSX

Manter em **J3-I7**.

### 5.10 Tooling PDF

`pypdf` = baseline inicial (texto, estrutura, annotations). **Não** exclusividade: adapter pode justificar biblioteca complementar com evidência (ex. tabelas).

### 5.11 Annotations

Extrair FreeText `/Contents` + Rect; preferência **por layout versionado**. Sem regra global “annotation sempre vence content”.

### 5.12 Métricas

Thresholds numéricos calibrados a partir do primeiro vertical real em **J3-I3**.

---

## 6. Divergências relevantes

- Origin 202 ≠ F328 (annotation `china` só em 202).
- PL Grouped 202 diverge de Fattura/PL detalhado; 328 Grouped é coerente.
- Blueprint §5.9 mínimo vs modelo operacional rico — expandir Blueprint após I0/I1 conforme necessário.
- DEC-ACCONTO permanece aberta; F181 informa, não fecha.

---

## 7. Riscos e pendências

| Item | Nota |
|---|---|
| Extensões idempotency HTTP | Sob demanda por vertical |
| SCR no Blueprint UI/UX | Ainda não editado |
| L-005 | Aberto; não ampliar papéis silenciosamente |
| OCR real | Backlog até PDF escaneado |

---

## 8. Preparação J3-I0 (não iniciado)

**Escopo I0:** occurrence, quarantine storage, hash/fingerprint, validação de segurança de upload, RBAC `ingestion:*`, edges Documents/Audit no graph **sem** promover Document no upload.

**Fora de I0:** DocumentSet/join (I1); adapters; staging IR completo; FE workspace; commit multi-owner.

---

## 9. Próxima etapa

**Aguardar autorização explícita do advisor para J3-I0** sob o escopo da §8.

Não iniciar I0 automaticamente após este handoff.

---

## 10. Evidências internas (âncoras)

| Âncora | Conteúdo |
|---|---|
| [`J3_P0_TECHNICAL_APPENDIX.md`](J3_P0_TECHNICAL_APPENDIX.md) | Matrizes + forense condensados |
| [`p0-analysis/`](p0-analysis/) | JSON, layouts, script |
| `v2/tests/fixtures/ingestion/` | Fixtures V2 |
| `P0_*.md` (histórico) | Pré-consolidação |

---

## 11. Arquivos relevantes desta consolidação

- `.cursor/rules/epic-v2.mdc` (§6.1)
- `docs/README.md` (§3 Return to advisor)
- Este handoff + apêndice técnico
- `ROADMAP_V2_EPIC.md` (0.5.66)
- `docs/v2/etapa-j3/README.md`

---

## 12. Recomendação

1. Aceitar este handoff como pacote canônico de decisão do P0.
2. Tratar decisões §5 como baseline de I0+.
3. Autorizar J3-I0 explicitamente quando desejado (pedido separado).

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: .cursor/rules/epic-v2.mdc; docs/README.md; ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_P0_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_P0_TECHNICAL_APPENDIX.md; docs/v2/etapa-j3/README.md; banners P0_REPORT.md / P0B_DECISIONS.md
- Evidence: docs/v2/etapa-j3/
- Roadmap status: 0.5.66 — handoff P0 publicado; decisões P0 ratificadas; I0 NOT_STARTED; próxima = aguardar autorização I0
- Next TODO: Aguardar autorização explícita para J3-I0
- Return to advisor: docs/v2/etapa-j3/J3_P0_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_P0_TECHNICAL_APPENDIX.md
```
