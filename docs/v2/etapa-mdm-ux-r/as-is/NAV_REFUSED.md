# Navegação e superfícies recusadas (produção intacta)

Cópia de referência: [`mixed/AppShell.tsx`](mixed/AppShell.tsx) linhas do rail atual.

## Rail de produção (recusado visualmente; permanece até pós-GATE)

```text
PRODUTOS
  Produtos
  Fornecedores          ← recusado como item primário
COMPRAS
  Pedidos · Faturas · Ingestão
FINANCEIRO
  Contas a pagar · Pagamentos realizados
LOGÍSTICA
  Embarques
  Prestadores           ← recusado no rail (CTA Embarques existe)
ADUANA
  Processos · Estoque
ADMINISTRAÇÃO
  Usuários
```

## Alvo no protótipo (não muta AppShell)

```text
COMPRAS          Pedidos · Faturas · Ingestão
FINANCEIRO       Contas a pagar · Pagamentos realizados
LOGÍSTICA        Embarques
ADUANA           Processos · Estoque
CATÁLOGO         Produtos
ADMINISTRAÇÃO    Usuários
```

- Fornecedor: overflow `⋯` em Catálogo / Produtos → Heroe's Srl
- Prestadores: CTA na página proto de Embarques
- Sem `/admin/settings`
- Sem Fornecedores na página Usuários

## Páginas recusadas como baseline visual

Product List: 4 colunas SKU|Descrição|NCM|Sim/Não; botão Buscar; Tamanho/Cor permanentes.  
Product Detail: título = SKU; sempre edição.  
Supplier list: List Report desproporcional à frequência.
