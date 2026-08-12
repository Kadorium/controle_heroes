# Autocomplete e campos inteligentes

Data: 2026-08-04.

## Resultado da busca (Fase 1)

Busca por `react-select`, `downshift`, `cmdk`, `Combobox`, `useDebounce`, `debounce`, `role="combobox"`, `aria-autocomplete` em todo `v2/frontend/src`: **zero ocorrências**. Confirmado: **não existe autocomplete/typeahead real no projeto** — nem biblioteca de terceiros, nem implementação própria com debounce.

Isso não significa que não exista *nenhuma* forma de busca assistida — existem dois padrões manuais que se aproximam da ideia, e ambos foram inspecionados:

### Padrão 1 — `<datalist>` nativo (SKU em `OrderCreatePage`)

```
<TextInput ... list="sku-list" />
<datalist id="sku-list">
  {products.map((p) => <option key={p.id} value={p.sku} />)}
</datalist>
```

- É a sugestão nativa do navegador (`<datalist>`), não um componente React.
- A lista de opções vem de `listProducts()`, que busca **no máximo 50 produtos** (`catalogApi.ts:26-30`, `limit: 50` fixo) e é carregada uma única vez no `useEffect` de montagem da página — não há busca incremental por texto (o parâmetro `q` existe na função `listProducts(q?)` mas **nunca é chamado com um valor** nesta tela).
- Sem debounce (não se aplica — `<datalist>` filtra localmente no navegador).
- Sem loading state, sem "sem resultado" customizado (comportamento é 100% do navegador).
- Sem acessibilidade ARIA customizada (é nativo, então o navegador cuida disso, mas com suporte inconsistente entre navegadores/leitores de tela — `<datalist>` tem suporte historicamente fraco a leitores de tela).
- **Efeito prático**: se o catálogo tiver mais de 50 produtos, os produtos além do 50º **não aparecem na sugestão nem podem ser adicionados ao pedido pelo SKU** — o único jeito de usá-los seria digitar o SKU exato de memória (o campo aceita texto livre, então tecnicamente funciona se o usuário souber o SKU exato, mas perde toda a assistência).

### Padrão 2 — busca manual em duas etapas (`OrderItemPicker` em `ShipmentDetailPage`)

Modal (`ConfirmationModal`) com: campo "Pedido (código)" → campo "SKU (opcional)" → botão "Buscar candidatos" (clique explícito, sem digitação incremental) → resultado popula um `SelectField` com os itens elegíveis → usuário escolhe um → digita quantidade → confirma.

- **Não é autocomplete** — é uma busca em lote acionada por clique, não por digitação (`ShipmentDetailPage.tsx:128-145`, função `search()` chamada só no `onClick` do botão "Buscar candidatos").
- Sem debounce (não se aplica, não há digitação incremental).
- Loading state: nenhum indicador visual durante a chamada `orderItemCandidates()` — o botão não entra em estado `busy`, então entre o clique e o resultado aparecer não há feedback.
- Estado sem resultado: tratado (`"Nenhum item elegível encontrado"`, `ShipmentDetailPage.tsx:141`).
- Acessibilidade: nenhum `role="combobox"`/`aria-autocomplete` — é um formulário comum com `SelectField` nativo após a busca.
- **Este é hoje o padrão mais sofisticado de busca assistida do projeto**, e mesmo assim exige: (1) saber o código exato do pedido, (2) um clique extra, (3) escolher em uma lista que só existe depois da busca.

## Campos onde autocomplete real seria esperado — o que existe hoje

| Campo esperado | Onde apareceria | O que existe hoje | Gap |
|---|---|---|---|
| Busca de produto por nome/SKU | `OrderCreatePage` (linha de item) | `<datalist>` nativo, capado em 50 produtos, sem busca por nome (só por SKU exato via `value`) | **Alto** — acima de 50 produtos, parte do catálogo fica inacessível por essa via |
| Seleção de fornecedor | `OrderCreatePage`, `PaymentCreatePage`, `ApQueuePage` (filtro) | `<SelectField>` populado com `listSuppliers()`, capado em **50 fornecedores**, sem campo de busca por texto (a função aceita `q` mas nenhuma tela o usa) | **Alto** — mesmo problema do produto; um `<select>` nativo com 50+ opções já é ruim de navegar, e acima de 50 fica literalmente incompleto |
| Seleção de pedido em campos relacionados | `ShipmentDetailPage` (picker), `CustomsDetailPage` (vincular fatura/embarque) | No picker de embarque: busca manual por código exato (padrão 2 acima). Em `CustomsDetailPage`: **nenhuma busca** — é um campo de texto puro esperando o **ID interno numérico** da fatura/embarque, sem nenhuma forma de descobrir esse ID pela interface (não há link "buscar", não há select, não há preview do que será vinculado antes de confirmar) | **Crítico** — é o pior caso do app: vincular pela ID crua, sem confirmação visual do que está sendo vinculado |
| Porto/destino | `ShipmentCreatePage`/`ShipmentDetailPage` (Origem/Destino) | `TextInput` livre, sem lista de portos conhecidos, sem normalização (dois embarques podem registrar o mesmo porto com grafias diferentes, ex. "Santos" vs "Porto de Santos") | **Médio** — não é bloqueante, mas gera inconsistência de dados ao longo do tempo (impacta filtros/relatórios futuros que dependam de agrupar por origem/destino) |
| Transportadora/prestador logístico | `ShipmentCreatePage`, `ShipmentDetailPage`, `ShipmentsListPage` (filtro) | `<SelectField>` populado com `listLogisticsProviders({ limit: 200 })` — teto mais alto que fornecedores/produtos, mas ainda um teto fixo sem busca por texto | **Médio** — 200 é uma margem confortável hoje, mas o padrão (teto fixo + sem busca) é o mesmo risco estrutural dos outros campos, só que adiado |

## `<select>` existentes de fornecedor/produto/pedido — carregam tudo de uma vez?

Sim, em todos os casos. Não há paginação, scroll infinito, nem busca no servidor acionada pela digitação em nenhum desses selects — a página inteira de opções é buscada de uma vez no `useEffect` de montagem e mantida em `useState` local.

| Fonte | Limite hardcoded | Onde | Comportamento acima do limite |
|---|---|---|---|
| `listSuppliers()` | `limit: 50` (`catalogApi.ts:8`) | `OrderCreatePage`, `PaymentCreatePage`, `ApQueuePage` (filtro) | Fornecedores além do 50º (por ordem de retorno da API, não necessariamente alfabética) somem do dropdown — não há indicação para o usuário de que a lista está truncada |
| `listProducts()` | `limit: 50` (`catalogApi.ts:27`) | `OrderCreatePage` (datalist) | Mesmo problema |
| `listLogisticsProviders()` | `limit: 200` (chamado explicitamente em cada tela: `ShipmentsListPage`, `ShipmentCreatePage`, `ShipmentDetailPage`, `LogisticsProvidersPage`) | Filtros e formulários de embarque | Mesmo problema, teto mais alto |

### O componente `<select>` nativo aguenta 200+ itens sem degradar a UX?

Tecnicamente o `<select>` HTML nativo (usado via `SelectField`) renderiza sem problema de performance até milhares de `<option>` — não há degradação técnica/de renderização. O problema é de **usabilidade humana**, não técnico: um `<select>` nativo sem busca interna (sem campo de filtro) se torna difícil de navegar visualmente acima de ~20-30 itens (o usuário precisa rolar uma lista longa e sem destaque de correspondência parcial). Em 50 fornecedores isso já é incômodo; em 200 prestadores logísticos é pior ainda — o teto técnico dos dados (50/200) e o teto prático de usabilidade do `<select>` nativo (dezenas) já se cruzam hoje, mesmo sem contar o problema adicional de itens que ficam de fora do teto de busca.

## Conclusão da Fase 4

O sistema não tem, em nenhum ponto, um campo de busca com digitação incremental + debounce + resultados do servidor. Os dois padrões existentes (`datalist` e busca manual por clique) cobrem parcialmente dois casos (produto por SKU exato, item de pedido por código exato de pedido) e mesmo esses dois são limitados por tetos de paginação sem interface de busca. Os campos de vínculo por ID cru no módulo de Aduana são o ponto mais crítico: não há *nenhuma* forma assistida, nem mesmo as parciais descritas acima.
