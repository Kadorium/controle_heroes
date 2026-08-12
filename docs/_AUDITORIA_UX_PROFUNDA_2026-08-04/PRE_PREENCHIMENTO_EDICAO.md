# Pré-preenchimento e edição — carregamento, loading, erro e race conditions

Data: 2026-08-04. Esta é a fase de maior risco da auditoria (potencial perda silenciosa de dado) — cada afirmação abaixo aponta para arquivo e linha específicos para poder ser verificada diretamente no código.

## A) Como o dado é carregado

Não há `SWR`, `React Query` nem qualquer biblioteca de data-fetching com cache (confirmado em `package.json` — dependências são só `openapi-fetch`, `react`, `react-dom`, `react-router-dom`). **100% do carregamento de dados no app segue o mesmo padrão manual**: `useEffect` + `useState` + `fetch`/client gerado (`api.GET(...)`), a página busca sozinha (nenhuma tela recebe dado já carregado via prop do pai, exceto os painéis de Aduana que recebem `processId` e buscam por conta própria).

Padrão típico (presente em praticamente toda tela de detalhe/edição — `OrderDetailPage`, `InvoiceDetailPage`, `ShipmentDetailPage`, `PaymentDetailPage`, `CustomsDetailPage`, os 4 painéis de Aduana):

```
useEffect(() => {
  let cancelled = false;
  void (async () => {
    try {
      const data = await getX(id);
      if (!cancelled) { setX(data); setFormField(data.field ?? ""); }
    } catch (e) { if (!cancelled) setError(...); }
  })();
  return () => { cancelled = true; };
}, [id]);
```

O flag `cancelled` protege contra "setState depois de desmontar" — mas **não protege contra sobrescrever o que o usuário está digitando** (ver seção D).

**Exceção sem guarda `cancelled`**: `ApQueuePage.load()` (`ApQueuePage.tsx:141-153`) e `OrderCockpitPage` (`OrderCockpitPage.tsx:63-67`) chamam a API sem flag de cancelamento. Como `load()` em `ApQueuePage` é re-executado a cada mudança de filtro (`useEffect(() => { load(); }, [load])`, e `load` depende de `query`), trocar filtros rapidamente pode fazer duas requisições concorrentes cujas respostas cheguem fora de ordem — a resposta mais antiga (de um filtro já abandonado) pode chegar depois e sobrescrever a tabela com dados que não correspondem mais aos filtros visíveis na tela. É um risco de **exibição de dado errado**, não de perda de edição (esta tela não tem campos de formulário sendo digitados durante o carregamento).

## B) Loading state — o que o usuário vê antes do dado chegar

Consistente e simples em todo o app: o componente `LoadingState` (`Feedback.tsx:46-52`) renderiza um único `<p className="muted">Carregando…</p>` (ou uma variante com mensagem específica, ex. "Carregando pedido…").

- **Não existe skeleton loading em nenhuma tela do app** — nenhuma ocorrência de placeholder cinza/shimmer.
- **Não existe spinner visual** (nem ícone giratório) — só texto.
- **Padrão de substituição total**: em praticamente todas as telas de edição/detalhe, a página inteira retorna cedo (`if (!order) return <LoadingState .../>`) — ou seja, **nenhum campo de formulário existe no DOM enquanto o dado não chega**. Isso tem uma consequência boa (elimina a race condition clássica de "digitar antes do dado chegar", ver seção D) e uma consequência ruim (a tela "pisca": sai do zero, mostra uma linha de texto, e então o layout inteiro aparece de uma vez — sem transição, sem preservar cabeçalho/breadcrumb, que também são recriados do zero).
- Duas variações de UX de loading coexistem para telas de **listagem** — verificado linha a linha, não só pela leitura superficial do JSX final:
  - **Substituição total** (`OrdersListPage`, `InvoicesListPage`, `PaymentsListPage`, `ShipmentsListPage`, e também **`CustomsListPage`** e **`MovementsPage`**, que na primeira leitura pareciam preservar o cabeçalho mas na verdade também o descartam): todas essas telas fazem `setRows(null)` (ou `setRows(undefined)`) **antes** de disparar a nova busca, e o `return` condicional (`if (rows === null) return <LoadingState/>`) fica **acima** do `PageHeader`/`KpiStrip`/`FilterBar` no JSX — ou seja, ao clicar num chip de status ou aplicar um filtro, a tela inteira (cabeçalho, KPIs e os próprios filtros que acabaram de ser clicados) some e reaparece do zero. Confirmado em 6 das 7 listagens do app.
  - **Chrome preservado — só `ApQueuePage`**: esta é a **única** tela do app que não zera seu estado de dados (`data`) antes de recarregar — só alterna uma flag `loading`. Como a condição que renderiza a tabela (`data && data.items.length > 0`) não depende de `loading`, a tabela **antiga permanece visível** enquanto a nova busca ocorre, com o texto "Carregando contas a pagar…" aparecendo *acima* da tabela desatualizada — não é um estado "limpo" (não há dimming/opacidade reduzida na tabela antiga, ela fica com aparência 100% normal enquanto já está desatualizada), mas é a única tela que não descarta o cabeçalho/filtros durante o refetch.
- **Campos ficam disabled durante o carregamento?** Não se aplica na maioria dos casos (os campos não existem ainda). Nas exceções onde a tela mantém formulário visível durante refetch (ex.: filtros de `ApQueuePage`, `ShipmentsListPage` durante troca de filtro), os inputs de filtro **permanecem interativos** durante o carregamento da tabela — não há `disabled` nem indicação visual de que uma nova busca está em andamento além da tabela sumir e reaparecer.

## C) Erro de carregamento

Componente padrão `ErrorState` (`Feedback.tsx:25-44`): mensagem + botão "Tentar novamente" **opcional** (só aparece se a prop `onRetry` for passada).

Inconsistência real e verificável — quais telas dão a opção de retry sem precisar recarregar o navegador:

| Com `onRetry` (recuperável na própria tela) | Sem `onRetry` (usuário precisa dar F5) |
|---|---|
| `ApQueuePage` (`onRetry={load}`) | `OrdersListPage` |
| `CustomsListPage` (`onRetry={() => setReloadKey(k => k+1)}`) | `InvoicesListPage` |
| `MovementsPage` (idem) | `PaymentsListPage` |
| `SkuPositionPage` (idem) | `OrderCockpitPage` |
| | `PayableFxPage` |
| | `OrderDetailPage`, `InvoiceDetailPage`, `ShipmentDetailPage`, `PaymentDetailPage`, `CustomsDetailPage` (todas as telas de detalhe/edição) |

Ou seja: **nenhuma tela de detalhe/edição (a categoria de tela onde um erro de rede é mais frustrante, porque o usuário já navegou fundo na aplicação) oferece retry** — só as listagens mais recentes (`ApQueuePage`, `CustomsListPage`, `MovementsPage`, `SkuPositionPage`) têm esse cuidado. Um erro de rede momentâneo ao abrir `/orders/42/commercial` deixa o usuário preso numa tela de erro sem botão, precisando recarregar a página inteira (perdendo, inclusive, a posição de navegação anterior salva por `useListReturn`, se aplicável).

## D) Race condition — o item de maior risco desta fase

**Pergunta do escopo**: se o usuário digitar num campo antes do dado chegar e o dado chegar depois, o campo é sobrescrito?

**Resposta para o carregamento inicial**: não é possível, porque o campo não existe no DOM antes do dado chegar (ver seção B — o padrão `if (!data) return <LoadingState>` impede a montagem do formulário). Este risco específico está mitigado em todo o app.

**Risco real e confirmado — não no carregamento inicial, mas em recargas (`reload()`) disparadas por outra ação na mesma tela**: várias telas chamam uma função `reload()`/`syncForm()` que **sobrescreve incondicionalmente todos os campos de formulário com o valor vindo do servidor**, mesmo quando a ação que disparou o reload é sobre uma seção completamente diferente da tela. Não há nenhuma guarda (`isDirty`, comparação de timestamp, `AbortController`, confirmação ao usuário) em nenhum dos três casos abaixo — todos verificáveis diretamente no código:

### 1. `OrderDetailPage` — botão "Atualizar" sobrescreve "Notas" sem aviso

```
async function reload() {
  const data = await getOrder(id);
  setOrder(data);
  setOrderDate(data.order_date ?? "");
  setNotes(data.notes ?? "");     // <- sobrescreve incondicionalmente
}
...
<Button variant="secondary" onClick={() => void reload()}>Atualizar</Button>
```
(`OrderDetailPage.tsx:53-58` e `430-432`)

**Cenário concreto**: o usuário está digitando um texto longo no campo "Notas" (mesma página, seção "Cabeçalho") e clica em "Atualizar" (botão sempre visível no rodapé da mesma página, sem relação direta com o campo Notas) — por curiosidade, para ver o estado mais recente do pedido, ou por engano. `reload()` busca o pedido do servidor e substitui `notes` pelo valor salvo, **descartando silenciosamente** o que estava sendo digitado. Não há confirmação, não há aviso de "alterações não salvas", não há `isDirty` bloqueando o botão.

### 2. `ShipmentDetailPage` — qualquer conflito de versão em QUALQUER ação reseta o formulário de cabeçalho inteiro

```
async function handle409<T>(fn: () => Promise<T>, preserveDraft = false): Promise<T | null> {
  try { return await fn(); }
  catch (e) {
    if (st === 409) {
      const fresh = await getShipment(id);
      setShipment(fresh);
      syncForm(fresh);              // <- sempre executa, reseta modal/origin/destination/provider/datas/notas
      if (!preserveDraft) setDraftQty({});
      setError("Conflito de versão — estado recarregado. Revise e tente de novo (rascunhos locais preservados quando aplicável).");
      return null;
    }
    throw e;
  }
}
```
(`ShipmentDetailPage.tsx:356-373`)

`handle409` é usado por **11 ações independentes** na mesma página: salvar resumo, avançar status, anular, excluir, adicionar/editar/remover item, adicionar/editar/remover pacote, lote de pacotes, salvar conteúdo de volume, salvar resumo declarado, adicionar/remover referência. O parâmetro `preserveDraft` só protege `draftQty` (quantidades de item em edição) — **não** protege os campos do formulário "Resumo" (`modal`, `origin`, `destination`, `providerId`, `plannedDeparture`, `plannedArrival`, `notes`), que são sempre resetados via `syncForm(fresh)`.

**Cenário concreto**: usuário está editando o campo "Notas" do resumo do embarque; em paralelo (ou em outra aba), alguém mais avança o status do mesmo embarque, incrementando sua `version`. O usuário então clica em "Adicionar volume" (ação não relacionada às Notas) — essa ação falha com 409 porque a versão mudou, e o `handle409` recarrega o embarque inteiro, **apagando o texto que estava sendo digitado em Notas**, sem qualquer aviso além da mensagem genérica de conflito. A própria mensagem de erro do sistema admite a limitação ("rascunhos locais preservados quando aplicável") — ou seja, o código já reconhece que nem todo rascunho é preservado, mas isso não é comunicado ao usuário de forma específica no momento em que ocorre.

### 3. `CustomsDetailPage` — qualquer ação bem-sucedida recarrega o processo inteiro e reseta "Ref. externa"

```
async function run(action: () => Promise<void>) {
  setBusy(true); setError(null);
  try {
    await action();
    await reload();          // <- reload() sempre executa após QUALQUER ação bem-sucedida
  } catch (e) { setError(conflictMessage(e)); }
  finally { setBusy(false); }
}

const reload = useCallback(async () => {
  const p = await getImportProcess(id);
  setProcess(p);
  setExtRef(p.external_reference ?? "");   // <- sobrescreve incondicionalmente
  ...
}, [id]);
```
(`CustomsDetailPage.tsx:73-95, 117-128`)

`run()` envolve **todas** as ações de escrita da página: atualizar ref. externa, submeter, cancelar, vincular/desvincular fatura, vincular/desvincular embarque, alocar item de fatura, alocar item de embarque. Todas chamam `reload()` ao final, que reseta `extRef` para o valor do servidor.

**Cenário concreto**: usuário está editando "Atualizar ref. externa" (campo de texto no topo da página) e, antes de clicar em "Salvar ref.", clica em "Vincular fatura" (ação diferente, mesma página, seção "Faturas" logo abaixo) — a vinculação é bem-sucedida, dispara `reload()`, e o texto que estava sendo digitado em "Ref. externa" é substituído pelo valor anterior do servidor. Mesma classe de problema dos dois casos acima: nenhuma guarda, nenhum aviso.

### Padrão comum aos três casos

Em nenhum dos três há:
- Flag de "campo sujo" (`isDirty`) que impeça o reset de um campo que o usuário está ativamente editando;
- Comparação entre o valor local e o valor recebido antes de decidir sobrescrever;
- `AbortController` para cancelar a requisição de reload em voo caso o componente ou o campo mude de estado;
- Qualquer confirmação ("Você tem alterações não salvas em X — deseja descartá-las?") antes de aplicar o reset.

Isso é exatamente o padrão de "perda de dado silenciosa" mais arriscado: **a ação que causa a perda não é a mesma ação que o usuário associaria ao campo perdido** — ele estava editando "Notas"/"Ref. externa" e a perda foi causada por um botão em outra seção da mesma tela, tornando o efeito colateral praticamente imprevisível para quem usa o sistema no dia a dia.

## Conclusão da Fase 5

O carregamento inicial de formulários é seguro (formulário só existe depois que o dado chega). O risco real está em **recargas pós-ação dentro da mesma sessão de tela**, presente em pelo menos 3 telas de alto uso operacional (Pedido comercial, Embarque, Processo aduaneiro) e estruturalmente decorrente do padrão "uma função `reload()`/`syncForm()` genérica, chamada por todas as ações da página, que sempre reescreve todo o formulário a partir do servidor". Ver `TABELA_PRIORIDADES_PROFUNDA.md` para impacto/esforço de correção.
