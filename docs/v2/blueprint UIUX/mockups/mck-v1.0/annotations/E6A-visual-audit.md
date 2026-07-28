# E6A — Auditoria visual consolidada (MCK v1.0)

**Data:** 2026-07-28  
**Escopo:** Etapa 6A apenas — **sem** correção de mockups  
**Fontes:** SVG + PNG 1440 + PDF 8 págs + smoke 1366 + cenário + direção + legenda + UI/UX §§20–25  
**Evidências derivadas:** [`../review/e6a-evidence/`](../review/e6a-evidence/)

---

## 1. Sumário executivo

| Métrica | Valor |
|---|---|
| Total de achados | **17** |
| BLOCKER | **0** |
| MAJOR | **1** |
| MINOR | **5** |
| POLISH | **11** |
| Naturezas | conteúdo · a11y · UX · visual · responsividade · domínio · implementação futura |
| Telas afetadas | MCK-001…007 + AUX (todas) |
| BLOCKER de compreensão | **não** |

**Recomendação preliminar para 6B:**  
Pacote editorial **MINOR** (E6-001…004, opcional E6-014) → eventual **MCK v1.1**.  
**E6-012** (contraste de bordas) → **Etapa 7** (token DS).  
POLISH opcionais sob critério humano. Gaps técnicos → **Etapa 9**.  
**Não** iniciar 6B nesta entrega. Checkpoint **E6-A** pendente de revisão externa.

---

## 2. Estado documental e visual

| Artefato | Esperado | Encontrado | Veredito |
|---|---|---|---|
| UI/UX | v3.6 + §25 | v3.6 + §25 | OK |
| Roadmap (pré-6A) | 0.5.19 | 0.5.19 | OK |
| Etapa 5 | DONE | DONE | OK |
| Etapa 6 | não iniciada | não iniciada antes desta auditoria | OK |
| MCK | v1.0 aprovado | v1.0 · A–D aprovados | OK |
| SVGs | 8 | 8 | OK |
| PDF | 8 páginas | 8 | OK |
| PNG 1440 | 8 | 8 | OK |
| Smoke 1366 | 001…007 | 7 oficiais; AUX ausente | OK c/ E6-011 |
| Blueprint Sistema | 0.2.8 | 0.2.8 | OK |
| Inc-6 | TODO | TODO | OK |
| Divergência material | — | nenhuma | — |

---

## 3. Hipóteses H-E6

| Hipótese | Veredito | Evidência | Ressalva |
|---|---|---|---|
| H-E6-1 | **CONFIRMADA** | Shell, cores, badges, tipografia e botões consistentes nos 8 SVG | — |
| H-E6-2 | **CONFIRMADA COM RESSALVAS** | Objeto/status/valor/risco/ação identificáveis em 3s | E6-001/002 nomenclatura |
| H-E6-3 | **CONFIRMADA COM RESSALVAS** | 14/12 linhas escaneáveis; filtros; ordenação | Volume alto = E6-017 futuro |
| H-E6-4 | **CONFIRMADA** | Fatura ≠ obrigação ≠ pagamento ≠ alocação; residual ≠ saldo | — |
| H-E6-5 | **CONFIRMADA** | Painéis A/B/C; ausência como em dash; stale textual | E6-003 rodapé |
| H-E6-6 | **CONFIRMADA COM RESSALVAS** | CTAs primários claros | E6-014 plano FX |
| H-E6-7 | **CONFIRMADA** | Densidade alta sem vazios materiais em 1440 | — |
| H-E6-8 | **CONFIRMADA COM RESSALVAS** | Smoke 1366: CTAs e FX 3 colunas acima da dobra | Scroll Cockpit; AUX só evidência |
| H-E6-9 | **CONFIRMADA COM RESSALVAS** | Textos ≥4,5:1; badges OK | E6-012 bordas; E6-015 chips |
| H-E6-10 | **CONFIRMADA** | Severidade visual ok/warn/err; recuperação presente | E6-009 códigos SCR |
| H-E6-11 | **CONFIRMADA COM RESSALVAS** | Família estável o bastante para derivar DS | Após 6B editorial + token borda na Etapa 7 |
| H-E6-12 | **CONFIRMADA** | Achados não alteram domínio/arquitetura | Gaps → Etapa 9 |

---

## 4. Achados

### E6-001 — Nomenclatura curta de Câmbio

| Campo | Conteúdo |
|---|---|
| Mockup / PDF | MCK-002 p.2 · MCK-004 p.4 · breadcrumb MCK-007 |
| Região | Link obrigações; botão drawer; breadcrumb `… / Câmbio` |
| Elemento | `Câmbio PY-8841-2 ›` · `Câmbio` · breadcrumb `Câmbio` |
| Evidência | SVG 002/004/007; título aprovado = **Câmbio da obrigação**; link longo no painel FX do Cockpit já correto |
| Problema | Rótulos curtos divergem do nome final da superfície |
| Impacto | Risco de confundir com hub global SCR-028 |
| Severidade | MINOR · conteúdo · **6B** |
| Correção sugerida | Unificar “Câmbio da obrigação” / “Abrir câmbio da obrigação” |
| Risco regressão | baixo |

### E6-002 — “Preview” residual

| Campo | Conteúdo |
|---|---|
| Mockup / PDF | MCK-006 p.6 |
| Região | Banner informativo |
| Elemento | `Preview abaixo ainda não foi confirmado` |
| Evidência | SVG/PNG/smoke 006; UI usa “Prévia” em outros pontos |
| Problema | Inglês residual |
| Impacto | Quebra de idioma |
| Severidade | MINOR · conteúdo · **6B** |
| Correção sugerida | `Prévia abaixo ainda não foi confirmada.` |
| Risco regressão | baixo |

### E6-003 — “Workspace da obrigação”

| Campo | Conteúdo |
|---|---|
| Mockup / PDF | MCK-007 p.7 |
| Região | Rodapé auditoria |
| Elemento | `Workspace da obrigação — …` |
| Evidência | SVG/PNG 007; smoke 1366 mostra a linha |
| Problema | Termo legado EN vs título PT aprovado |
| Severidade | MINOR · conteúdo · **6B** |
| Correção sugerida | Substituir por “Câmbio da obrigação — …” |
| Risco regressão | baixo |

### E6-004 — Abreviação “AP”

| Campo | Conteúdo |
|---|---|
| Mockup / PDF | MCK-002 · 005 · 007 |
| Elemento | `Fila AP` · `Voltar à AP` |
| Evidência | Textos literais nos SVG |
| Problema | AP não expandido |
| Severidade | MINOR · conteúdo · **6B** |
| Correção sugerida | “contas a pagar” por extenso |
| Risco regressão | baixo |

### E6-005 — Coluna `FX / BRL`

| Campo | Conteúdo |
|---|---|
| Mockup | MCK-004 |
| Evidência | Header de coluna na fila |
| Problema | Sigla FX |
| Severidade | POLISH · conteúdo · 6B ou Etapa 7 |
| Correção sugerida | `Câmbio / BRL` se couber |
| Risco regressão | médio |

### E6-006 — KPI `Sem plano FX`

| Campo | Conteúdo |
|---|---|
| Mockup | MCK-004 |
| Evidência | KPI card |
| Severidade | POLISH · conteúdo · 6B ou Etapa 7 |
| Correção sugerida | `Sem plano cambial` |
| Risco regressão | baixo |

### E6-007 — Badge `INITIAL`

| Campo | Conteúdo |
|---|---|
| Mockup | 002 · 004 · 007 |
| Evidência | Badge/plano; legenda mapeia kinds de domínio |
| Problema | Código de domínio na UI |
| Severidade | POLISH · domínio · **não corrigir** (manter kind) · Etapa 7 tooltip |
| Risco regressão | médio se traduzir |

### E6-008 — Shell `Order-to-Pay`

| Campo | Conteúdo |
|---|---|
| Mockup | Todos |
| Evidência | Subtítulo sidebar |
| Severidade | POLISH · conteúdo · **não corrigir** até decisão de produto · Etapa 7 |
| Risco regressão | baixo |

### E6-009 — Labels SCR/FLW no AUX

| Campo | Conteúdo |
|---|---|
| Mockup | MCK-AUX-01 |
| Evidência | Rodapé dos cards; evidência 1366 |
| Severidade | POLISH · conteúdo · **não corrigir** na prancha de referência · Etapa 7 (UI produto sem códigos) |
| Risco regressão | baixo |

### E6-010 — KPI `Pago por alocação`

| Campo | Conteúdo |
|---|---|
| Mockup | MCK-002 |
| Evidência | PNG 1440: texto completo na caixa 186px; sem clipping |
| Problema | Semente de truncamento |
| Veredito semente | **REFUTADA** como defeito no artboard atual |
| Severidade | POLISH · visual · **não corrigir** |
| Risco regressão | — |

### E6-011 — Smoke AUX 1366 ausente no pacote oficial

| Campo | Conteúdo |
|---|---|
| Evidência | `smoke-1366/` tem 7 arquivos; gerado `e6a-evidence/MCK-AUX-01-above-fold-1366x768.png` |
| Severidade | POLISH · processo · 6B opcional promover ao smoke oficial |
| Risco regressão | baixo |

### E6-012 — Contraste de bordas ghost/input (MAJOR)

| Campo | Conteúdo |
|---|---|
| Mockup | Transversal |
| Elemento | `#D5DCE5` sobre `#FFFFFF` |
| Evidência | `e6a-evidence/contrast-pairs.tsv` · razão **1,38:1** (ref. não-texto 3:1) |
| Problema | Borda de controles abaixo do limiar de componente |
| Impacto | Risco a11y sistêmico; não impede compreensão do mock |
| Severidade | **MAJOR** · a11y · **Etapa 7** |
| Correção sugerida | Token de borda ≥3:1 no DS |
| Risco regressão | médio |

### E6-013 — `Próx. venc.` / `Próx. 7d`

| Campo | Conteúdo |
|---|---|
| Mockup | 001 · 004 |
| Severidade | POLISH · conteúdo · Etapa 7 |
| Correção sugerida | Expandir se espaço permitir |
| Risco regressão | médio |

### E6-014 — Hierarquia Replanejar / Corrigir plano

| Campo | Conteúdo |
|---|---|
| Mockup | MCK-007 |
| Evidência | Dois ghost iguais; primário global = Atualizar cotação |
| Severidade | MINOR · UX · 6B ou Etapa 7 |
| Correção sugerida | Definir ênfase conforme frequência de uso |
| Risco regressão | médio |

### E6-015 — Altura de chip 28px

| Campo | Conteúdo |
|---|---|
| Mockup | MCK-001 |
| Evidência | `button-heights.tsv` |
| Severidade | POLISH · a11y · Etapa 7 |
| Correção sugerida | Chip ≥32px |
| Risco regressão | baixo |

### E6-016 — 1920×1080 não exercitado

| Campo | Conteúdo |
|---|---|
| Evidência | Só artboard 1440; §20.4 prevê teto por arquétipo |
| Problema | Expansão/max-width não validada visualmente |
| Severidade | POLISH · responsividade · **Etapa 7** |
| Correção sugerida | Spec de max-width no DS; não redesenhar mock agora |
| Risco regressão | — |

### E6-017 — Volume 50 / 100 / 500

| Campo | Conteúdo |
|---|---|
| Mockup | 001 · 004 |
| Evidência | Amostra 14/12 legível; UI/UX §21 filas menciona sticky/virtualização |
| Problema | Inferência de necessidade futura, não falha do mock |
| Severidade | POLISH · implementação futura · **Etapa 7/9** |
| Correção sugerida | Sticky header + paginação; virtualização se necessário — **não** no SVG |
| Risco regressão | — |

---

## 5. Sementes obrigatórias

| Semente | Veredito | Achado |
|---|---|---|
| Câmbio PY-8841-2 vs Câmbio da obrigação | **CONFIRMADA** como inconsistência | E6-001 |
| Preview abaixo… | **CONFIRMADA** | E6-002 |
| Workspace da obrigação | **CONFIRMADA** | E6-003 |
| Fila AP | **CONFIRMADA** (abreviação) | E6-004 |
| FX / BRL | **CONFIRMADA** (sigla) | E6-005 |
| Sem plano FX | **CONFIRMADA** (sigla) | E6-006 |
| badge INITIAL | **CONFIRMADA** presença · não defeito obrigatório | E6-007 |
| shell Order-to-Pay | **CONFIRMADA** presença · decisão de produto | E6-008 |
| SCR/FLW no AUX | **CONFIRMADA** · aceitável em prancha de referência | E6-009 |
| KPI Pago por alocação | **REFUTADA** como clipping | E6-010 |
| smoke AUX 1366 ausente | **CONFIRMADA** · mitigado por evidência E6A | E6-011 |

---

## 6. Matriz de consistência transversal

Legenda: **OK** · **Δ** (ver achado) · **N/A**

| Elemento | 001 | 002 | 003 | 004 | 005 | 006 | 007 | AUX |
|---|---|---|---|---|---|---|---|---|
| shell | OK | OK | OK | OK | OK | OK | OK | OK |
| breadcrumb | OK | OK | OK | OK | OK | OK | Δ E6-001 | OK |
| títulos | OK | OK | OK | OK | OK | OK | OK | OK |
| botões | OK | N/A | OK | OK | OK | OK | Δ E6-014 | OK |
| campos | N/A | N/A | OK | N/A | OK | OK | N/A | N/A |
| tabelas | OK | OK | OK | OK | N/A | OK | N/A | N/A |
| cards/painéis | OK | OK | OK | OK | OK | OK | OK | OK |
| badges | OK | OK | OK | OK | N/A | OK | Δ E6-007 | OK |
| alertas | N/A | OK | OK | OK | OK | Δ E6-002 | OK | OK |
| drawer | N/A | N/A | N/A | OK | N/A | N/A | N/A | N/A |
| dinheiro | OK | OK | OK | OK | OK | OK | OK | OK |
| datas | OK | OK | OK | OK | OK | OK | OK | OK |
| documentos | N/A | OK | OK | OK | OK | OK | OK | N/A |
| auditoria | N/A | OK | OK | OK | N/A | N/A | Δ E6-003 | N/A |
| espaçamento | OK | OK | OK | OK | OK | OK | OK | OK |
| bordas | Δ E6-012 | Δ E6-012 | Δ E6-012 | Δ E6-012 | Δ E6-012 | Δ E6-012 | Δ E6-012 | Δ E6-012 |
| radius | OK | OK | OK | OK | OK | OK | OK | OK |
| tipografia | OK | OK | OK | OK | OK | OK | OK | OK |
| estados | OK | OK | OK | OK | OK | OK | OK | OK |
| idioma | Δ E6-013 | Δ E6-001/004 | OK | Δ E6-005/006 | Δ E6-004 | Δ E6-002 | Δ E6-003 | Δ E6-009 |

Shell subtítulo EN: ver E6-008 (todas as telas).

---

## 7. Contraste e acessibilidade visual

Fonte: tokens nos SVG. Medição: luminância relativa WCAG. Arquivo: `e6a-evidence/contrast-pairs.tsv`.

| Elemento | FG | BG | Razão | Tipo | Resultado |
|---|---|---|---:|---|---|
| texto / canvas | `#1A2332` | `#F4F6F8` | 14,57 | texto | ≥4,5 OK |
| muted / canvas | `#5B6B7C` | `#F4F6F8` | 5,05 | texto | ≥4,5 OK |
| texto / surface | `#1A2332` | `#FFFFFF` | 15,78 | texto | OK |
| muted / surface | `#5B6B7C` | `#FFFFFF` | 5,47 | texto | OK |
| branco / accent | `#FFFFFF` | `#1F4E79` | 8,66 | texto | OK |
| danger / canvas | `#B42318` | `#F4F6F8` | 6,07 | texto | OK |
| warn / canvas | `#B54708` | `#F4F6F8` | 5,01 | texto | OK |
| side-text / sidebar | `#E8EEF4` | `#1B2A41` | 12,36 | texto | OK |
| side-muted / sidebar | `#9AA8B8` | `#1B2A41` | 5,96 | texto | OK |
| badge-ok | `#067647` | `#E8F5EE` | 5,07 | texto | OK |
| badge-over | `#B42318` | `#FCEBEA` | 5,70 | texto | OK |
| badge-att | `#B54708` | `#FEF4E6` | 4,99 | texto | OK |
| badge-open | `#1F4E79` | `#E8F1F8` | 7,58 | texto | OK |
| badge-draft | `#5B6B7C` | `#EEF2F6` | 4,86 | texto | OK |
| warn on warnbox | `#B54708` | `#FEF4E6` | 4,99 | texto | OK |
| borda ghost/input | `#D5DCE5` | `#FFFFFF` | **1,38** | UI | &lt;3:1 → E6-012 |
| borda accent | `#1F4E79` | `#FFFFFF` | 8,66 | UI | OK |

**Menor razão medida:** 1,38 (borda UI).  
**Limitações:** tokens declarados (não raster); sem hover/focus reais; **não** declarar WCAG compliant global.

| Tema | Achado |
|---|---|
| Cor + texto | Badges textuais — OK |
| Texto pequeno muted | ≥4,5 — OK |
| Área botões | CTAs 32–44px OK; chips 28px → E6-015 |
| Foco / teclado / SR | NÃO VERIFICÁVEL no SVG → Etapa 7/9 |
| Ícones sem label | Ações textuais — OK |

---

## 8. Resoluções

### 1440×900

Oito artboards: composição coerente; drawer AP + tabela; FX 3 colunas; CTAs acessíveis; sem clipping material nos PNG.

### 1366×768

Smoke 001–007: primárias acima da dobra; FX 3 colunas; drawer AP utilizável. Cockpit: comercial abaixo da dobra (scroll esperado). AUX: evidência em `e6a-evidence/`.

### 1920×1080

Hipótese §20.4 max-width por arquétipo → **Etapa 7** (E6-016). Sem novo mockup.

---

## 9. Filas em volume

| Amostra | Observação |
|---|---|
| 14 / 12 | Escaneáveis; tabular; badges de exceção |
| 50–100 | Sticky + paginação |
| 500 | Avaliar virtualização |

Ausência de virtualização no mock **não** é defeito (E6-017).

---

## 10. Formulários (003 · 005)

| Tema | 003 | 005 |
|---|---|---|
| Edição | Contorno accent | Inputs claros |
| Ordem | Itens → condições → prévia | Origem → dados → Importante → CTA |
| Documento | Anexado | Comprovante |
| Erro / unsaved / duplicate | Não no artboard | Não no artboard → Etapa 7/9 |

---

## 11. Entidades financeiras

| Conceito | Onde | Distinto? | Risco |
|---|---|---|---|
| Fatura | 002 · 003 · 004 | Sim | Baixo |
| Obrigação | 002 · 004 · 005 · 006 · 007 | Sim | Baixo |
| Pagamento | 002 · 005 · 006 · AUX | Sim | Baixo |
| Alocação | 006 · AUX T3 | Sim | Baixo |
| Saldo | Obrigação / pedido | Sim | Baixo c/ copy residual |
| Residual | Payment | Sim | Baixo |
| Planejado | 007 A · 002 | Sim | Baixo |
| Mercado | 007 B · strip | Sim | Baixo |
| Executado | 007 C (`—`) | Sim | Baixo |
| Resultado cambial | 007 C | Sim | Baixo |

---

## 12. Pacote sugerido para decisão humana (6B)

**Incluir:** E6-001, E6-002, E6-003, E6-004.  
**Opcional:** E6-014, E6-005, E6-006, E6-011.  
**Etapa 7:** E6-012 (MAJOR), E6-013, E6-015, E6-016.  
**Etapa 9:** E6-017 + gaps G02/SCR-028/enrichment.  
**Não corrigir:** E6-007, E6-008, E6-009, E6-010.

---

## 13. Gates 6A

| Gate | Status |
|---|---|
| Oito artboards inspecionados | OK |
| PDF/SVG/PNG/smoke usados | OK |
| H-E6 revalidados | OK |
| Matriz de achados | OK |
| Matriz transversal | OK |
| Contrastes medidos | OK |
| 1440 / 1366 | OK |
| AUX avaliado | OK |
| Sementes classificadas | OK |
| Sem correção de SVG | OK |
| MCK v1.0 / UI/UX v3.6 | OK |
| 6B / Etapa 7 não iniciadas | OK |
| Sistema 0.2.8 / Inc-6 TODO | OK |

---

## 14. Revisão externa do Checkpoint E6-A

**Decisão:** E6-A = **APROVADO COM AJUSTES** (autorização externa).

**Efeitos sobre o pacote preliminar da 6A:**

| Ajuste | Detalhe |
|---|---|
| E6-012 | Movido da Etapa 7 → **6B** (obrigatório: bordas de controles interativos) |
| E6-018 | **Criado** nesta revisão (AUX 1366 — card *Cotação indisponível* cortado) → **6B** |
| Escopo 6B aprovado | E6-001…006 · E6-011 · E6-012 · E6-018 → produzir **MCK v1.1** |
| Explicitamente **não** autorizados | E6-007 · E6-008 · E6-009 · E6-010 · E6-013 · E6-014 · E6-015 · E6-016 · E6-017 |

**E6-018 (registro):**

| Campo | Conteúdo |
|---|---|
| ID | E6-018 |
| Mockup | MCK-AUX-01 |
| Evidência | smoke derivado 1366 (`e6a-evidence`) |
| Problema | card *Cotação indisponível* cortado à direita |
| Impacto | evidência 1366 não demonstra composição íntegra |
| Severidade | MINOR |
| Natureza | responsividade / processo |
| Destino | **6B** |
| Correção | reorganizar a prancha AUX para caber sem clipping |
| Risco | baixo |

**Histórico 6A (seções 1–13):** preservado sem reescrita. Execução das correções: Etapa **6B** / pacote `mck-v1.1/` (changelog `E6B-change-log.md`).  
**Etapa 7:** não iniciada nesta autorização.
