# EXCEPTIONS de Design System (protótipo MDM-UX-R)

Autoridade: Blueprint UI/UX §26–§27. Tokens DERIVED / NORMALIZED / TARGET usados no CSS (`proto.css`).

## EXCEPTION-COMPACT-RAIL

- **O quê:** `sidebar.rail.width = 56px` em viewport ≤1100px; labels e títulos de grupo ocultos; ícones permanecem.
- **Por quê:** §26.2 só lista `sidebar.width = 220` expandida. O gate B7 exige compact rail obrigatório. Valor copiado do token de produção `--shell-sidebar-rail` (`v2/frontend/src/index.css`), não inventado.
- **Classificação:** EXCEPTION (não está em §26.2; proveniência = AS-IS de produção).

## EXCEPTION-PROTO-BANNER

- **O quê:** faixa sticky 28px (`color.warning`) acima do shell: “Protótipo MDM-UX-R · sem API”.
- **Por quê:** B11 — o rail de produção permanece recusado; o proto precisa ser inconfundível para o dono não julgar as duas IAs como a mesma UI.
- **Classificação:** EXCEPTION de campanha (chrome de isolamento; não vai para produção).

## EXCEPTION-DRAWER-SHADE (já no DS)

Sombra do menu overflow usa `#1A2332` @18% — token §26.6 já classificado EXCEPTION de overlay. Reuso, não desvio novo.

## Não-exceptions (conformes)

- Paleta, tipografia (title 22 / body 12 / label 11 / caption 10.5), spacing 4–32, gutter 24@1366 / 32@1440, chip 28 / hit ≥32, row 40, badge 20, radius 4/6/14, botão 32/36.
- Sem terceira paleta, sem Bootstrap, sem tabela com inputs soltos acima.
