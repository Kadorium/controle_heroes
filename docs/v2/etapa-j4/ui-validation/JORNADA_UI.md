# Validação UI Logistics — jornada por cliques

| Campo | Valor |
|---|---|
| Data | 2026-08-02 |
| Ambiente | `epic_v2_test` @ 8082 |
| Spec | `v2/frontend/e2e/j4-logistics-ui-journey.spec.ts` |
| Suite | `npm run` → `node scripts/e2e-suite.mjs logistics-ui-journey` |
| Resultado harness | **1 passed** |
| Roadmap nesta validação | **UNCHANGED** (versão corrente no repo: 0.5.50) |

## Separação de canais

| Canal | O que foi usado |
|---|---|
| **UI (cliques)** | Login, pedido+SKU, prestador, lista/create/detail shipment, item picker, package, refs, advances, reabrir |
| **API como prova** | **Não** — apenas network observation do POST disparado pela UI |
| **Componente (Vitest)** | Fora deste relatório |
| **NOT_IN_UI** | Pesos/dims de package; `set_package_contents`; upsert document summary / upload |

## Tela de criação (estado atual demonstrado)

| Aspecto | Observado |
|---|---|
| Modal | DOM `<select>` (`SELECT`); labels pt-BR: Marítimo, Aéreo, Rodoviário, Courier, Multimodal, Outro |
| Transportador | DOM `<select>` (`SELECT`); opções = prestadores elegíveis ativos (`Carrier …`) |
| Obrigatórios no create | Nenhum `required` no PLANNED; Notice: exigidos ao BOOKED |
| Datas | `input type="date"`; hint `dd/mm/aaaa`; value ISO `yyyy-mm-dd` |
| Microcopy | “Cadastre os dados básicos. Itens, volumes e documentos serão adicionados após a criação.” |
| Payload | `modal`, `origin`, `destination`, `logistics_provider_id`, datas, `notes` — **sem** `carrier` free-text |
| Persistido | `modal=SEA`, FK provider, `carrier_name_snapshot` derivado |

## Passos 1–14

Ver JSON: [`logs/jornada-ui-steps.json`](logs/jornada-ui-steps.json) · screenshots em [`screenshots/`](screenshots/).

| # | Veredito | Canal |
|---|---|---|
| 1 Lista | PASS | UI |
| 2 Novo embarque | PASS | UI |
| 3 Preencher | PASS | UI |
| 4 Criar | PASS | UI |
| 5 Redirect detalhe | PASS | UI |
| 6 Item | PASS | UI |
| 7 Qty parcial | PASS | UI |
| 8 Package | PARTIAL | UI (tipo/qtd); pesos/dims NOT_IN_UI |
| 9 DDT+BL | PASS | UI |
| 10 Totais | PARTIAL | UI mostra seção; pesos/volume 0 sem dims |
| 11→BOOKED | PASS | UI |
| 12 Estrutura bloqueada | PASS | UI |
| 13 IN_TRANSIT/ARRIVED | PASS | UI |
| 14 Lista+reabrir | PASS | UI |

## Conclusões

1. Existe E2E completo por cliques (esta suite); o gate `e2e:logistics` legado ainda é majoritariamente API-first.
2. Só via API (não na UI): pesos/dims de package, contents de package, document summary upsert/upload.
3. UI operacional para usuário sem acesso técnico **após** cadastrar prestador em `/logistics-providers` e ter pedido confirmado.
4. J4-UX1: já implementado no código validado (selects + FK); era obrigatório antes de planejar J#5 e está DONE no Roadmap 0.5.50.
