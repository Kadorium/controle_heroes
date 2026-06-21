# Resumo Executivo — Módulo de Importação Epic

## 1) Problema que o sistema resolve

A Epic hoje depende de planilhas soltas, e-mails e conferência manual para controlar importações, pagamentos, custos e documentos. Isso cria risco de erro de custo final, perda de rastreabilidade, divergência entre fontes e dificuldade para fechar cada importação com segurança. Um blueprint evita começar “no improviso” e depois descobrir que a estrutura não suporta auditoria, conciliação nem expansão futura.

## 2) Princípio do sistema

O sistema deve ser:

- Simples para usar.
- Auditável de ponta a ponta.
- Incremental, começando pelo controle operacional.
- Com controle mínimo de nacionalização e entrada em estoque no MVP, e integrável no futuro com estoque completo, fiscal, contábil, financeiro e BI.

A lógica central é separar claramente:

- dado bruto;
- dado revisado;
- dado oficial;
- cálculo;
- auditoria;
- relatório gerencial.

## 3) O que entra no MVP rápido

O MVP não deve tentar ser um ERP inteiro. Ele deve entregar rapidamente:

- cadastro de importações;
- cadastro de SKUs;
- invoices;
- pagamentos;
- despesas;
- descontos e créditos;
- status operacional;
- anexos/documentos;
- custo estimado;
- painel de pendências;
- trilha básica de auditoria.

Isso já reduz ansiedade porque mostra o que está aberto, quanto falta, o que foi pago, o que está pendente e quais documentos faltam.

## 4) Arquitetura recomendada

Para a Epic, a melhor base pragmática é um **app web simples, com login, permissões básicas e banco centralizado**, acessado pelo navegador. Na primeira versão, a arquitetura definida é: app web local em um PC servidor da Epic, acessado pelos funcionários via navegador na rede interna, com PostgreSQL local, sem Docker no MVP, anexos em pasta controlada, backup diário do banco e dos documentos, login individual e auditoria. Isso é mais seguro e evolutivo do que depender de Excel/Access como solução principal, mas ainda leve o suficiente para uma operação pequena. Se a equipe precisar de velocidade extrema no começo, Excel/low-code pode servir só como ponte temporária, não como base final.

## 5) Fluxo operacional mínimo

O fluxo deve ser assim:

1. Receber planilha/e-mail da Heroes.
2. Salvar arquivo bruto.
3. Jogar dados para staging.
4. Mandar divergências para revisão.
5. Aprovar e transformar em dado oficial.
6. Registrar invoice.
7. Registrar adiantamentos e pagamentos parciais.
8. Registrar descontos e créditos.
9. Registrar embarque, chegada, DI/DUIMP e despesas.
10. Calcular landed cost estimado e realizado.
11. Conciliar diferenças.
12. Fechar a importação com auditoria.

## 6) Regra mais importante

Nenhum custo, desconto, imposto ou pagamento deve entrar sem origem/documento.
Nenhum dado vazio pode virar zero automaticamente.
Nenhuma divergência deve desaparecer: ela precisa virar fila de revisão.

## 7) Conclusão prática

Se a Epic quer valor rápido sem criar dívida técnica, a prioridade é esta:

- primeiro visibilidade;
- depois controle financeiro;
- depois conciliação;
- depois landed cost;
- só então integração com estoque, fiscal, contábil e BI.

A melhor aposta é construir uma base pequena, mas correta, em vez de um sistema grande e frágil.

