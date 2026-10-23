import {test,expect,type Page} from "@playwright/test";
import {mkdirSync,writeFileSync} from "node:fs";
import {join} from "node:path";
test.use({viewport:{width:1366,height:681},deviceScaleFactor:1});
const evidence=process.env.EXPERIENCE_EVIDENCE_DIR;
async function login(page:Page,role="admin") {
  expect(new URL(test.info().project.use.baseURL!).port).toBe("8086");
  if(role==="admin") {expect((await page.request.post("/api/auth/dev-login")).ok()).toBeTruthy();return;}
  await page.goto("/login");await page.getByLabel("E-mail",{exact:true}).fill(`lab-${role}@example.com`);
  await page.getByLabel("Senha",{exact:true}).fill("lab-only-2026");await page.getByRole("button",{name:"Entrar",exact:true}).click();await expect(page.locator("#main-content")).toBeVisible();
}
async function capture(page:Page,name:string){if(evidence){mkdirSync(evidence,{recursive:true});await page.screenshot({path:join(evidence,name+".png")});}}
test("volume, stable totals, paging, scroll, focus and keyboard",async({page})=>{
  await login(page);await page.goto("/inventory/positions?q=LAB-VOLUME&status=all");
  await expect(page.getByTestId("stock-positions")).toContainText("537 produtos");
  await page.evaluate(async()=>{await document.fonts.ready;await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));});
  const totals=await page.locator(".experience-stats").textContent();
  const visibleRows=await page.locator(".experience-table tbody tr").evaluateAll(rows=>rows.filter(r=>{const b=r.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight;}).length);
  await capture(page,"volume-laptop");
  if(evidence)writeFileSync(join(evidence,"volume-metrics.json"),JSON.stringify({visibleRows,viewport:page.viewportSize(),total:537}));
  await page.getByLabel("Ordenar",{exact:true}).selectOption("-DOMESTIC");await expect(page.locator(".experience-stats")).toHaveText(totals!);
  await page.getByRole("button",{name:"Próxima",exact:true}).click();await expect(page.getByText("26–50 de 537",{exact:true})).toBeVisible();
  const target=page.locator(".product-name").nth(18), id=await target.getAttribute("id");
  await target.scrollIntoViewIfNeeded();await target.focus();const scroll=await page.evaluate(()=>scrollY), search=new URL(page.url()).search;
  await page.keyboard.press("Enter");await expect(page.getByTestId("stock-product-context")).toContainText("Nenhum custo vinculado");
  await page.keyboard.press("Escape");await expect(page.locator(`#${id}`)).toBeFocused();
  expect(new URL(page.url()).search).toBe(search);expect(Math.abs(await page.evaluate(()=>scrollY)-scroll)).toBeLessThan(6);
  await page.reload();await expect(page.getByText("26–50 de 537",{exact:true})).toBeVisible();
});
test("two purchases, published pointer, draft version, real two page PDF and return",async({page})=>{
  await login(page);await page.goto("/inventory/positions?product=1");
  await expect(page.locator("#purchase-1")).toBeVisible();await expect(page.locator("#purchase-2")).toBeVisible();
  await page.locator("#purchase-2").focus();await page.keyboard.press("Enter");
  await expect(page.getByRole("combobox",{name:"Versão",exact:true})).toHaveValue("2");await expect(page.getByTestId("stock-product-context")).toContainText("Base de 3");
  await page.getByRole("combobox",{name:"Versão",exact:true}).selectOption("3");await expect(page.getByTestId("stock-product-context")).toContainText("Rascunho");
  await page.reload();await expect(page.getByRole("combobox",{name:"Versão",exact:true})).toHaveValue("3");
  await capture(page,"multi-purchase-version");
  await page.locator("#open-cost-composition").focus();await page.keyboard.press("Enter");
  await page.getByRole("button",{name:"LAB-FAT-MULTI.pdf ↗"}).focus();await page.keyboard.press("Enter");
  await expect(page.locator('[data-pdf-ready="true"]')).toBeVisible();
  await page.getByTestId("pdf-next-page").click();await expect(page.getByText(/Pág. 2/)).toBeVisible();
  await page.getByTestId("pdf-zoom-in").click();await expect(page.getByTestId("pdf-zoom-label")).toHaveText("110%");await page.getByTestId("pdf-zoom-reset").click();
  const downloadPromise=page.waitForEvent("download");await page.getByRole("link",{name:"Baixar PDF"}).click();const download=await downloadPromise;expect(await download.failure()).toBeNull();
  await capture(page,"variant-pdf-page2");await page.keyboard.press("Escape");await expect(page.getByRole("button",{name:"LAB-FAT-MULTI.pdf ↗"})).toBeFocused();
});
test("inventory-only actual role: no catalog, reporting or costing dependency",async({page})=>{
  await login(page,"inventory");await page.goto("/inventory/positions?q=Atlas");await page.locator("#stock-product-1").click();
  await expect(page.getByText("Custo não disponível para este acesso.",{exact:false})).toBeVisible();await expect(page.locator(".experience-stats")).toContainText("6");
  expect((await page.request.get("/api/costing/products/1/sources")).status()).toBe(403);
  expect((await page.request.get("/api/reporting/dashboard")).status()).toBe(403);
  await page.getByRole("link",{name:"Ver movimentos",exact:true}).click();await expect(page.getByTestId("inventory-movements-page")).toBeVisible();
  await page.getByRole("link",{name:"← Voltar ao estoque"}).click();await expect(page.getByTestId("stock-product-context")).toContainText("Raquete Atlas");
  await capture(page,"inventory-only");
});
test("cost reader cannot see document metadata or content without documents permission",async({page})=>{
  await login(page,"cost");await page.goto("/inventory/positions?product=1&case=1&version=1&section=sources");
  await expect(page.getByTestId("stock-product-context")).toContainText("6.200,00");
  await expect(page.getByRole("button",{name:"DEMO-comercial.pdf ↗"})).toHaveCount(0);
  expect((await page.request.get("/api/documents/2/content")).status()).toBe(403);
  const source=await(await page.request.get("/api/costing/products/1/sources")).json();expect(source.rows.every((r:{purchases:unknown[]})=>!r.purchases.length)).toBeTruthy();
});
test("cost source failure, retry, denied document and invalid PDF recovery",async({page})=>{
  await login(page);let fail=true;
  await page.route("**/api/costing/products/1/sources*",async route=>fail?route.fulfill({status:503,body:"{}"}):route.continue());
  await page.goto("/inventory/positions?product=1");await expect(page.getByRole("alert")).toBeVisible();fail=false;await page.getByRole("button",{name:"Tentar novamente"}).click();await page.locator("#purchase-1").click();await page.locator("#open-cost-composition").click();
  let broken=true;
  await page.route("**/api/documents/2/content",async route=>broken?route.fulfill({status:200,contentType:"application/pdf",body:"invalid fixture"}):route.continue());
  await page.getByRole("button",{name:"DEMO-comercial.pdf ↗"}).click();await expect(page.getByTestId("pdf-retry-canvas")).toBeVisible();broken=false;await page.getByTestId("pdf-retry-canvas").click();await expect(page.locator('[data-pdf-ready="true"]')).toBeVisible();
});

test("personal dashboard copy: identity, hide, reorder, restore and reload",async({page})=>{
  await login(page,"reader");await page.goto("/dashboard?view=executiva");await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-demo-ready","true");
  await page.getByRole("button",{name:"Personalizar",exact:true}).click();
  const dialog=page.getByRole("dialog");await dialog.getByRole("textbox").fill("Laboratório integração pessoal");await dialog.getByRole("button",{name:"Duplicar visão atual"}).click();
  await expect(page).toHaveURL(/view=\d+/);const personalUrl=page.url();
  if(!await dialog.isVisible())await page.getByRole("button",{name:"Personalizar",exact:true}).click();
  const items=dialog.locator(".dash-customize-list li"), initial=await items.count(), name=await items.nth(0).locator("span").first().innerText();
  await items.nth(0).getByRole("button",{name:"Descer",exact:true}).click();await expect(items.nth(1)).toContainText(name);
  await items.nth(0).getByRole("button",{name:"Ocultar",exact:true}).click();await expect(items).toHaveCount(initial-1);
  await page.keyboard.press("Escape");await page.reload();expect(page.url()).toBe(personalUrl);
  await page.getByRole("button",{name:"Personalizar",exact:true}).click();await expect(dialog.locator(".dash-customize-list li")).toHaveCount(initial-1);
  await dialog.getByRole("button",{name:"Restaurar preset"}).click();await expect(dialog.locator(".dash-customize-list li")).toHaveCount(initial);
  await dialog.getByRole("button",{name:"Excluir visão pessoal"}).click();await expect(page).toHaveURL(/view=executiva/);
});

test("partial coverage, missing values and delayed cost response are explicit contract fixtures",async({page})=>{
  await login(page);
  await page.route("**/api/costing/products/1/versions/*",async route=>{
    const response=await route.fetch();const body=await response.json();
    body.partial_coverage=true;body.product.unit_brl=null;body.coverage.coverage="PARTIAL";body.fx.kind="parcial";
    if(route.request().url().endsWith("/2"))await new Promise(r=>setTimeout(r,1200));
    await route.fulfill({response,json:body});
  });
  await page.goto("/inventory/positions?product=1&case=2&version=2");await expect(page.getByRole("combobox",{name:"Versão",exact:true})).toBeVisible();
  await page.getByRole("combobox",{name:"Versão",exact:true}).selectOption("3");await expect(page.getByTestId("stock-product-context")).toContainText("Cobertura parcial");
  await expect(page.locator(".experience-cost-value")).toContainText("Não informado");
  await page.waitForTimeout(1400);await expect(page.getByRole("combobox",{name:"Versão",exact:true})).toHaveValue("3");await expect(page.getByTestId("stock-product-context")).toContainText("Rascunho");
});

test("finance without reporting: predictable payable, payment and FX paths",async({page})=>{
  await login(page,"finance");await expect(page).toHaveURL(/\/payables$/);await expect(page.getByTestId("payables-list-page")).toBeVisible();
  await page.getByText("Financeiro",{exact:true}).click();await page.getByRole("link",{name:"Câmbio por obrigação"}).click();
  await expect(page.getByRole("heading",{name:"Câmbio · escolha a obrigação"})).toBeVisible();await page.getByRole("link",{name:"Ver câmbio",exact:true}).first().click();await expect(page.getByTestId("payable-fx-panel")).toBeVisible();
  await page.getByRole("link",{name:"Pagamentos",exact:true}).click();await expect(page).toHaveURL(/\/payments$/);
});
