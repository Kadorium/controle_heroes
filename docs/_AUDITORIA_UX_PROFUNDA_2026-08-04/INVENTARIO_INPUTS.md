# Inventário de inputs

Data: 2026-08-04. Cobertura: todos os formulários encontrados na Fase 1 (22 telas + 4 painéis de Aduana).

## A) Padrões gerais observados (antes das tabelas por formulário)

- **`autocomplete=`**: só é definido explicitamente em 2 campos do app inteiro — `email`/`password` do `LoginPage` (`autoComplete="username"` / `"current-password"`, `LoginPage.tsx:71,82`). Em todos os outros ~140 campos de texto/número do app, o atributo está **ausente** — o navegador decide sozinho, o que é aceitável para campos de negócio (código de pedido, NCM, IDs), mas ausente também em campos que se beneficiariam de `autocomplete="off"` explícito (referências de documento, chaves PIX) ou de um valor semântico (não há equivalente HTML padrão para "nome de fornecedor", então isso é esperado).
- **`inputMode=`**: definido em apenas 3 pontos do app — `MoneyInput`/`RateInput` (`inputMode="decimal"`, componentes compartilhados) e o filtro `ap-filter-order` em `ApQueuePage` (`inputMode="numeric"`). Todos os outros campos que só aceitam dígitos — e são muitos: todo campo "ID do X" no módulo de Aduana (`customs-link-invoice-id`, `customs-link-shipment-id`, `customs-alloc-inv-item`, `customs-alloc-shp-item`, `nationalization-product-id`, `nationalization-shipment-item`, `nationalization-invoice-item`, `receipt-product-id`, `receipt-nat-id`, `receipt-nat-item-id`, `movements-product-filter`, campos de quantidade como `line-qty`, `picker-qty`, `item-qty-*`) — **não** definem `inputMode="numeric"`. Em teclado mobile/tablet isso força o usuário a trocar de teclado manualmente para digitar um ID puramente numérico.
- **Placeholder como substituto de label (anti-padrão)**: ocorre em `OrderCreatePage`, na linha de adição de item (`line-sku`, `line-qty`, `line-unit`, `line-price` — linhas 279-309): os 4 campos não têm `FormField`/`<label>`, só `placeholder="SKU"`, `"Qtd"`, `"UM (PZ)"`, `"Preço (opcional)"`. Assim que o usuário digita, a identificação do campo desaparece — em um formulário de 4 campos lado a lado isso é recuperável visualmente pela ordem, mas é o único ponto do app sem rótulo persistente em campo de entrada de dado de negócio.
- **`maxLength`**: usado em só 3 campos do app: motivo de cancelamento de pedido (`cancel-reason`, 64 — reforçado por validação JS redundante), unidade de item de pedido (`order-item-unit-edit-*`, 16) e unidade de item de fatura (`unit-*`, 16). Nenhum outro campo de texto livre (notas, descrições, motivos de override, nomes de fornecedor/payee) tem limite de tamanho no cliente — o primeiro feedback de "texto longo demais" (se existir) só chega depois do POST/PUT, via erro de API.
- **`min`/`max` em numéricos e datas**: **nenhum** campo do app define `min`/`max`. Todos os campos numéricos são `type="text"` com `inputMode` (não `type="number"`), então `min`/`max` HTML não se aplicariam de qualquer forma — mas também não há nenhuma validação client-side equivalente, exceto o caso pontual de quantidade em `OrderCreatePage.addLine()` (`Number(qty) <= 0` → erro). Datas (`DateInput`, `type="date"`) nunca recebem `min`/`max`: nada impede registrar `planned_arrival` anterior a `planned_departure` em `ShipmentCreatePage`/`ShipmentDetailPage`, ou uma data de fatura futura, sem que o navegador ou o React avisem antes do envio.

## B) Consistência de height entre inputs

Três alturas de input coexistem no app, todas visualmente parecidas mas definidas por regras CSS diferentes:

| Classe | Altura | Onde é usada | Fonte no CSS |
|---|---|---|---|
| `.ds-input` / `.ds-select` (componentes `TextInput`/`SelectField`/`DateInput`/`MoneyInput`/`RateInput`) | `min-height: var(--button-height-md)` = **32px** | Todos os formulários "novos" (Orders, Billing, Treasury, Shipments create/detail, Customs create) | `index.css:689` |
| `.panel input, .panel select` (legado) | Sem `min-height` — altura resulta de `padding: 0.55rem 0.75rem` + `line-height` do browser (~34–36px conforme fonte) | Qualquer input dentro de um `<section className="panel">` que não passe pelos componentes `ds-*` — na prática nenhum formulário atual usa isso diretamente (é herança do CSS antigo), mas a regra continua ativa e pode ser acidentalmente aplicada por qualquer `input`/`select` cru dentro de `.panel` (ex.: os campos de Aduana que usam `TextInput`, que já aplica `.ds-input`, então na prática escapam desta regra — mas o `<table className="data-table">` de `LogisticsProvidersPage` não tem inputs, então este seletor está hoje largamente órfão) | `index.css:274-282` |
| `.login-form input` | `min-height: 32px` (hardcoded, não via `var(--button-height-md)`) + `padding: 0.7rem 0.8rem` (maior que `.ds-input`) | Só `LoginPage` | `index.css:149-157` |

**Conclusão**: na prática todos os formulários ativos usam os componentes `ds-*` e ficam nos 32px corretos — a única tela genuinamente diferente é o **Login**, cujos inputs têm padding visivelmente maior (`0.7rem 0.8rem` vs `0.35rem 0.55rem` do `.ds-input`) mesmo com a mesma `min-height`. É perceptível ao alternar entre a tela de login e qualquer tela interna: os campos de login parecem mais "largos" verticalmente por dentro.

## C) Campos monetários e de taxa (MoneyInput, RateInput) — foco em risco cambial

- **Máscara de entrada**: sim, via `parseMoneyInput()` (`MoneyInput.tsx:11-19`, compartilhada com `RateInput`). Aceita tanto `1.234,56` (pt-BR) quanto `1234.56` (cru) na digitação; ao perder foco, formata para exibição via `Intl.NumberFormat("pt-BR")`; o valor enviado à API sempre usa ponto decimal. Não usa `imask`/`cleave` — é uma implementação própria, pequena e funcional.
- **Separador decimal exibido ao usuário**: sempre **vírgula** (formato pt-BR), inclusive para valores em **EUR** — ou seja, um valor em euros aparece como `EUR 1.234,56`, não como `EUR 1,234.56` (formato europeu/internacional mais comum para EUR). É uma escolha consistente em todo o app (não há mistura), mas vale registrar que a interface trata EUR com convenção de exibição brasileira, não com a convenção do próprio código de moeda.
- **Prefix/suffix visível no campo**: **inconsistente**. `MoneyInput` só mostra o código da moeda (`<span className="money-input-currency">{currency}</span>`) quando a prop `currency` é passada pelo componente pai. Isso acontece na maioria dos casos (`OrderCreatePage` → `currency="EUR"`, `InvoiceDetailPage` → `currency={inv.currency}`, `PaymentCreatePage` → `currency={currency}`), mas **não** em `PaymentDetailPage`, no campo de valor a alocar por obrigação elegível (`alloc-amt-${e.id}`, linha 332-337): o `MoneyInput` é renderizado sem a prop `currency`, então o campo de digitação não mostra nenhum código de moeda — só a coluna de saldo ao lado (`MoneyDisplay`) mostra `e.currency`. Em uma tela que aloca pagamentos entre obrigações que podem estar em moedas diferentes, o campo onde o usuário efetivamente digita o valor é o único sem indicação de moeda.
- **Nunca é usado o símbolo `€`/`R$`** — sempre o código ISO (`EUR`/`BRL`) como texto, tanto no campo quanto na exibição (`formatMoney`, `format.ts:29`). É uma escolha deliberada e sem ambiguidade (código ISO é mais seguro que símbolo em contexto de exposição cambial), mas o suffix nunca aparece como símbolo compacto — sempre 3 letras antes do valor, o que ocupa mais espaço horizontal em tabelas densas.
- **EUR e BRL são diferenciados visualmente?** Não. Não há cor, ícone, ou peso de fonte diferente por moeda em nenhum ponto do app — a única diferenciação é textual (o código de 3 letras). Em telas que mostram as duas moedas lado a lado na mesma vista (ex.: `OrderCockpitPage`, KPIs "Exposição FX" e "FX realizado" em BRL ao lado de "Pedido"/"Faturado"/"Pago" em EUR — `OrderCockpitPage.tsx:139-146`), a leitura correta depende inteiramente de o usuário notar o prefixo de 3 letras em cada card do `KpiStrip`. Dado que o sistema existe justamente por causa da exposição cambial EUR→BRL, a ausência de qualquer pista visual não-textual (cor de acento, por exemplo) é um ponto de atenção real, não cosmético.
- **`RateInput`** (taxa de câmbio): sem prefixo/sufixo (correto, é adimensional), 4 casas decimais por padrão (`fractionDigits=4`), mesma máscara pt-BR. Não há indicação de "para qual par de moedas" a taxa se aplica dentro do próprio input — depende do rótulo do `FormField` ao redor (que sempre está presente, ex.: "Taxa de mercado", "Taxa projetada").

## Tabelas por formulário

### Login (`LoginPage`)

| Campo | Componente | type= | autocomplete= | inputMode= | Placeholder | Problemas |
|---|---|---|---|---|---|---|
| E-mail | `TextInput` | text (default) | `username` | ausente | nenhum (label acima) | Sem toggle de mostrar/ocultar senha no campo abaixo |
| Senha | `TextInput` | `password` | `current-password` | ausente | nenhum | Idem — nenhum ícone "olho" para revelar senha, padrão comum em produtos modernos |

### Pedido — criação (`OrderCreatePage`)

| Campo | Componente | type= | autocomplete= | inputMode= | Placeholder | Problemas |
|---|---|---|---|---|---|---|
| Código / Nº pedido | `TextInput` | text | ausente | ausente | "ex.: 758" | — |
| Fornecedor | `SelectField` | — | ausente | — | "— criar novo —" (como opção) | Limitado a 50 fornecedores (`listSuppliers()` sem paginação real, ver `AUTOCOMPLETE_CAMPOS_INTELIGENTES.md`); não marcado `required` embora obrigatório na prática |
| Novo fornecedor | `TextInput` | text | ausente | ausente | nenhum | Só aparece condicionalmente; sem validação de duplicidade no cliente |
| Data do pedido | `DateInput` | date | ausente | — | — | Sem `min`/`max` |
| Notas | `TextInput` | text | ausente | ausente | "Observações documentais (opcional)" | — |
| SKU (linha de item) | `TextInput` + `datalist` | text | ausente | ausente | "SKU" (placeholder-only, sem label) | Ver anti-padrão citado acima; datalist carrega até 50 produtos |
| Qtd | `TextInput` | text | ausente | ausente | "Qtd" (placeholder-only) | Sem `inputMode="decimal"` apesar de ser quantidade numérica |
| UM | `TextInput` | text | ausente | ausente | "UM (PZ)" (placeholder-only) | — |
| Preço | `MoneyInput` | text | ausente | decimal | "Preço (opcional)" | `currency="EUR"` fixo — correto, pedidos são sempre EUR |

### Fatura — detalhe/edição (`InvoiceDetailPage`)

| Campo | Componente | type= | autocomplete= | inputMode= | Placeholder | Problemas |
|---|---|---|---|---|---|---|
| Data da fatura | `DateInput` | date | ausente | — | — | Sem `min`/`max` (poderia ser anterior à data do pedido) |
| Qtd (item) | `TextInput` | text | ausente | ausente | nenhum | Sem `inputMode="decimal"` |
| Un. (item) | `TextInput` | text | ausente | ausente | "PZ" | `maxLength=16` |
| Preço bruto | `MoneyInput` | text | ausente | decimal | nenhum | `currency={inv.currency}` — OK |
| Desconto (tipo) | `SelectField` | — | ausente | — | — | — |
| Valor desc. (unit) | `MoneyInput` | text | ausente | decimal | nenhum | `currency={inv.currency}` — OK |
| Valor desc. (%) | `TextInput` | text | ausente | ausente | nenhum | Sem `inputMode="decimal"`, sem sufixo "%" visível no próprio campo |
| Motivo override (emitir sem doc.) | `TextInput` | text | ausente | ausente | nenhum | — |
| Modo (condições) | `SelectField` | — | ausente | — | — | — |
| Vencimento (parcela) | `DateInput` | date | ausente | — | — | — |
| % / Valor (parcela) | `TextInput` / `MoneyInput` | text | ausente | ausente/decimal | "%" no campo percentual | — |

### Pagamento — criação (`PaymentCreatePage`)

| Campo | Componente | type= | autocomplete= | inputMode= | Placeholder | Problemas |
|---|---|---|---|---|---|---|
| Fornecedor | `SelectField` | — | ausente | — | "Selecione" | `required`; limitado a 50 via `listSuppliers()` |
| Data | `DateInput` | date | ausente | — | — | `required`, sem `min`/`max` |
| Moeda | `TextInput` **livre** | text | ausente | ausente | nenhum | **Campo de texto livre, não `SelectField`**, para um valor que deveria ser um enum fechado (EUR/BRL/outro suportado) — risco de digitar código inválido/inconsistente; único tratamento é `.toUpperCase()` no `onChange` |
| Valor | `MoneyInput` | text | ausente | decimal | nenhum | `required`; **valor inicial hardcoded `"1000"`** quando não há contexto de fila (`g02.amount || "1000"`) — ver `PRE_PREENCHIMENTO_EDICAO.md` e `TABELA_PRIORIDADES_PROFUNDA.md`, é o achado mais crítico da auditoria |
| Referência | `TextInput` | text | ausente | ausente | nenhum | — |
| Motivo override (sem doc.) | `TextInput` | text | ausente | ausente | nenhum | — |

### Embarque — criação/detalhe (`ShipmentCreatePage` / `ShipmentDetailPage`)

| Campo | Componente | type= | autocomplete= | inputMode= | Placeholder | Problemas |
|---|---|---|---|---|---|---|
| Modal de transporte | `SelectField` | — | ausente | — | "Selecione o modal" | — |
| Origem / Destino | `TextInput` | text | ausente | ausente | nenhum | Texto livre — sem sugestão/lista de portos conhecidos (ver Fase 4) |
| Empresa transportadora | `SelectField` | — | ausente | — | "Selecione a transportadora" | Limitado a 200 via `limit: 200` fixo (sem busca) |
| Saída/Chegada prevista | `DateInput` | date | ausente | — | — | Sem `min`/`max` — chegada pode ser anterior à saída sem aviso |
| Notas | `TextInput` | text | ausente | ausente | nenhum | — |
| Pedido (código) — picker de item | `TextInput` | text | ausente | ausente | nenhum | Campo-chave de uma busca manual (ver Fase 4) |
| SKU (opcional) — picker | `TextInput` | text | ausente | ausente | nenhum | — |
| Quantidade — picker | `TextInput` | text | ausente | ausente | nenhum | Sem `inputMode="decimal"` |
| Dimensões/pesos de volume (10+ campos) | `TextInput` | text | ausente | ausente | vários com `hint` no `FormField` | Nenhum tem `inputMode="decimal"` apesar de serem todos numéricos (comprimento, largura, altura, pesos, volume) |

### Aduana — todos os painéis (`CustomsDetailPage`, `DoganalePanel`, `NumerarioPanel`, `NationalizationPanel`, `ReceiptPanel`)

| Campo (padrão repetido) | Componente | type= | autocomplete= | inputMode= | Placeholder | Problemas |
|---|---|---|---|---|---|---|
| "ID da fatura" / "ID do embarque" / "ID do item de fatura" / "ID do item de embarque" / "ID do produto" / "ID item embarque" / "ID item fatura" / "ID da liberação" / "ID item da liberação" (9 campos distintos no total) | `TextInput` | text | ausente | **ausente** (deveria ser `numeric`) | nenhum | Nenhuma busca/validação — usuário digita um ID interno de banco de dados sem qualquer forma de descobri-lo pela própria UI (ver `AUTOCOMPLETE_CAMPOS_INTELIGENTES.md`, achado mais crítico da Fase 4) |
| Quantidade (várias) | `TextInput` | text | ausente | ausente | nenhum/"1" | — |
| Moeda (`NumerarioPanel`) | `TextInput` **livre** | text | ausente | ausente | nenhum | Mesmo problema do campo Moeda em `PaymentCreatePage` — deveria ser `SelectField` |
| NCM | `TextInput` | text | ausente | ausente | hint via `FormField` em alguns pontos | Sem máscara/validação de formato (NCM tem 8 dígitos) |
| Nome do payee / Banco / PIX | `TextInput` | text | ausente | ausente | nenhum | **Valores iniciais hardcoded**: `payeeName="Bechtrans"`, `bankName="Banco Exemplo"` — ver achado crítico |
| Total declarado / Base / Tributo / Despesa | `TextInput` **livre** (não `MoneyInput`) | text | ausente | ausente | nenhum | Campos monetários que **não usam o componente `MoneyInput`** — sem máscara, sem formatação pt-BR, sem indicação de moeda; **valores iniciais hardcoded** (`"1500.00"`, `"1000"`, `"300"`, `"200"`) |
