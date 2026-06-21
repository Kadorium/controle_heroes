# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: central-ordem-checkpoint.spec.ts >> Central da Ordem — checkpoint pós-Fase 5 >> central: Visão Geral, Bloco A e Bloco B
- Location: e2e\central-ordem-checkpoint.spec.ts:67:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: /Faturas · acconto/i })
Expected: visible
Timeout: 20000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 20000ms
  - waiting for getByRole('heading', { name: /Faturas · acconto/i })

```

```yaml
- banner:
  - text: Epic
  - navigation:
    - link "Painel":
      - /url: /
      - img
      - text: Painel
    - link "Ordens":
      - /url: /importacoes
      - img
      - text: Ordens
    - link "Financeiro":
      - /url: /financeiro
      - img
      - text: Financeiro
    - link "Demo Epic":
      - /url: /demo
      - img
      - text: Demo Epic
    - link "Cadastros":
      - /url: /cadastros
      - img
      - text: Cadastros
  - button "Buscar":
    - img
  - button "Notificações":
    - img
  - text: A Administrador admin
  - button "Sair":
    - img
- main:
  - button "← Voltar"
  - heading "Central da Ordem DEMO-04-3INV Chegou ao Brasil" [level=1]
  - paragraph: — · 2026 · USD · FOB · atualizado 20/06/2026
  - button "Fatura"
  - button "Pagamento"
  - button "Despacho"
  - button "Anexar"
  - button "Conciliar / fechar"
  - text: ✓ Pedido ✓ Faturado ✓ Acconto ✓ A despachar ✓ Em trânsito 6 Aduana 7 Estoque 8 Fechado Valor faturado 480000.0000 Acconto versado 0 Acconto rimasto 480000.0000 Saldo a pagar 480000.0000 Próximo vencimento — Crédito acumulado — A despachar — Pendências —
  - complementary "Abas da ordem":
    - paragraph: Visão geral
    - link "Visão Geral":
      - /url: /importacoes/4/resumo
    - paragraph: Operação
    - link "Faturas e pagamentos":
      - /url: /importacoes/4/invoices
    - link "Produtos e quantidades":
      - /url: /importacoes/4/itens
    - link "Logística":
      - /url: /importacoes/4/logistica
    - link "Crédito / conta corrente":
      - /url: /importacoes/4/financeiro
    - link "Documentos":
      - /url: /importacoes/4/documentos
    - link "Aduana e custos BR":
      - /url: /importacoes/4/aduaneiro
    - paragraph: Fechamento
    - link "Conciliação e fechamento":
      - /url: /importacoes/4/conciliacao
    - link "Histórico":
      - /url: /importacoes/4/historico
  - status "Carregando"
  - text: Carregando visão geral...
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | import { getDemoImportationId } from "./helpers";
  3   | 
  4   | /** Labels técnicos que não devem aparecer como texto principal visível (word boundary). */
  5   | const TECH_LABEL_PATTERNS = [
  6   |   /\bPO_CREATED\b/,
  7   |   /\bPROFORMA_RECEIVED\b/,
  8   |   /\bIN_TRANSIT\b/,
  9   |   /\bCLOSED\b/,
  10  |   /\bPENDING\b/,
  11  |   /\bInvoices\b/,
  12  |   /\bShipment\b/,
  13  |   /\bLanded Cost\b/,
  14  |   /\breason_code\b/,
  15  | ];
  16  | 
  17  | /** Valores fictícios do mock central da ordem — não devem aparecer hardcoded. */
  18  | const MOCK_FAKE_VALUES = ["447.500", "397.500", "178.750", "6.560"];
  19  | 
  20  | test.describe("Central da Ordem — checkpoint pós-Fase 5", () => {
  21  |   test("topbar: Ordens, Financeiro, Demo Epic", async ({ page }) => {
  22  |     await page.goto("/");
  23  |     await expect(page.getByRole("link", { name: "Painel" })).toBeVisible();
  24  |     await expect(page.getByRole("link", { name: "Ordens" })).toBeVisible();
  25  |     await expect(page.getByRole("link", { name: "Financeiro" })).toBeVisible();
  26  |     await expect(page.getByRole("link", { name: "Demo Epic" })).toBeVisible();
  27  |   });
  28  | 
  29  |   test("glossário PT — ausência de labels técnicos principais", async ({ page }) => {
  30  |     const demoId = await getDemoImportationId(page);
  31  | 
  32  |     const routes = ["/", "/importacoes", `/importacoes/${demoId}/resumo`, "/financeiro"];
  33  |     for (const route of routes) {
  34  |       await page.goto(route, { waitUntil: "domcontentloaded" });
  35  |       const body = await page.locator("body").innerText();
  36  |       for (const pattern of TECH_LABEL_PATTERNS) {
  37  |         expect(body, `label técnico ${pattern} em ${route}`).not.toMatch(pattern);
  38  |       }
  39  |     }
  40  |   });
  41  | 
  42  |   test("honestidade — sem números fake do mock", async ({ page }) => {
  43  |     const demoId = await getDemoImportationId(page, "DEMO-01-OCEAN");
  44  |     await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
  45  |     await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 30000 });
  46  |     await expect(page.getByRole("heading", { name: /Faturas · acconto/i })).toBeVisible({ timeout: 20000 });
  47  |     const body = await page.locator("body").innerText();
  48  |     for (const fake of MOCK_FAKE_VALUES) {
  49  |       expect(body).not.toContain(fake);
  50  |     }
  51  |   });
  52  | 
  53  |   test("fila de ordens carrega e abre central", async ({ page }) => {
  54  |     const queueReady = page.waitForResponse(
  55  |       (r) => r.url().includes("/api/importations/order-queue") && r.ok(),
  56  |       { timeout: 120_000 }
  57  |     );
  58  |     await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
  59  |     await queueReady;
  60  |     await expect(page.getByRole("heading", { name: /Fila de ordens/i })).toBeVisible({ timeout: 20000 });
  61  |     const firstRow = page.locator(".order-queue__row").first();
  62  |     await expect(firstRow).toBeVisible({ timeout: 15000 });
  63  |     await firstRow.click();
  64  |     await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 15000 });
  65  |   });
  66  | 
  67  |   test("central: Visão Geral, Bloco A e Bloco B", async ({ page }) => {
  68  |     const demoId = await getDemoImportationId(page);
  69  |     await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
  70  |     const sidebar = page.getByRole("complementary");
  71  |     await expect(sidebar.getByRole("link", { name: "Visão Geral", exact: true })).toBeVisible({
  72  |       timeout: 15000,
  73  |     });
> 74  |     await expect(page.getByRole("heading", { name: /Faturas · acconto/i })).toBeVisible({ timeout: 20000 });
      |                                                                             ^ Error: expect(locator).toBeVisible() failed
  75  |     await expect(page.getByRole("heading", { name: /DA SPEDIRE/i })).toBeVisible({ timeout: 20000 });
  76  |   });
  77  | 
  78  |   test("Demo Epic navega para /demo", async ({ page }) => {
  79  |     await page.goto("/");
  80  |     await page.getByRole("link", { name: "Demo Epic" }).click();
  81  |     await expect(page).toHaveURL(/\/demo/);
  82  |   });
  83  | 
  84  |   test("financeiro global carrega fila", async ({ page }) => {
  85  |     await page.goto("/financeiro");
  86  |     await expect(page.getByRole("heading", { name: /Financeiro|Contas a pagar/i })).toBeVisible({ timeout: 15000 });
  87  |   });
  88  | 
  89  |   test("glossário operacional em cadastros", async ({ page }) => {
  90  |     await page.goto("/cadastros/glossario");
  91  |     await expect(page.getByRole("heading", { name: /Glossário operacional/i })).toBeVisible();
  92  |   });
  93  | 
  94  |   test("order-queue API responde com ordens", async ({ page }) => {
  95  |     const res = await page.request.get("/api/importations/order-queue?limit=20", { timeout: 120_000 });
  96  |     expect(res.ok()).toBeTruthy();
  97  |     const body = await res.json();
  98  |     expect(body.items?.length ?? 0).toBeGreaterThan(0);
  99  |   });
  100 | });
  101 | 
```