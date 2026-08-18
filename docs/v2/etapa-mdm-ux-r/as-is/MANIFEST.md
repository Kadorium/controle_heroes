# MDM-UX-R R0 — manifesto forense

Gerado 2026-08-18. **Zero DELETE** no produto. Backup externo **não** faz parte desta campanha (dono, manual).

## Git (evidência, não backup)

Fonte: [`git-counts.txt`](git-counts.txt), [`git-head.txt`](git-head.txt), [`git-status-short.txt`](git-status-short.txt).

- HEAD: `3b10deb` (Roadmap git 0.5.106)
- `git status --short`: **229** linhas
- untracked `??`: **101**

O working tree mistura Elo 7/8, J4-FIN, J5, cadeia-46, G2, MDM-UX, OpenAPI, Roadmap e Blueprint. Este manifesto **não** substitui cópia integral fora do repo.

## Páginas MDM NEW (cópia integral)

Pasta [`pages/`](pages/) — snapshot das páginas atuais recusadas visualmente:

- `ProductListPage.tsx` · `ProductDetailPage.tsx` · `ProductCreatePage.tsx`
- `SupplierListPage.tsx` · `SupplierDetailPage.tsx` · `SupplierCreatePage.tsx`
- `UsersListPage.tsx` · `UserDetailPage.tsx` · `UserCreatePage.tsx`
- `CatalogPages.test.tsx` · `UsersPages.test.tsx`

## MIXED (cópia para hunks de nav/rotas)

Pasta [`mixed/`](mixed/):

- `AppShell.tsx` — grupo Produtos+Fornecedores; Prestadores no rail Logística
- `AppShell.nav.test.tsx`
- `App.tsx` — rotas `/catalog/*` e `/admin/users*` additive

Inventário de hunks: [`MIXED_INVENTORY.md`](MIXED_INVENTORY.md).  
Classificação: [`CLASSIFICATION.md`](CLASSIFICATION.md).  
Navegação recusada: [`NAV_REFUSED.md`](NAV_REFUSED.md).

## R0 DONE

Há evidência suficiente para, depois do GATE, preservar backend/APIs/hooks e reconstruir páginas + IA do rail sem depender do working tree vivo.
