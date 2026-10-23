import {test,expect,type Page} from "@playwright/test";
import {mkdirSync,writeFileSync} from "node:fs";
import {join} from "node:path";
const evidence=process.env.EXPERIENCE_EVIDENCE_DIR!;
const views=[{width:1366,height:681},{width:1366,height:768},{width:1920,height:1080},{width:1024,height:768}];
async function login(page:Page) {
  expect(new URL(test.info().project.use.baseURL!).port).toBe(process.env.EXPERIENCE_PROMOTED === "true" ? "8082" : "8085");
  expect((await page.request.get("/api/health")).ok()).toBeTruthy();
  expect((await page.request.post("/api/auth/dev-login")).ok()).toBeTruthy();
}
async function capture(page:Page,name:string) {if(evidence){mkdirSync(evidence,{recursive:true});await page.screenshot({path:join(evidence,name+".png")});}}
for(const viewport of views) test(`G1 complete real document and context ${viewport.width}x${viewport.height}`,async({page})=>{
  await page.setViewportSize(viewport);await login(page);
  const errors:string[]=[], writes:string[]=[];
  page.on("pageerror",e=>errors.push(e.message));page.on("request",r=>{if(!["GET","HEAD","OPTIONS"].includes(r.method())&&!r.url().includes("/fx/quotes/"))writes.push(r.method()+" "+r.url());});
  await page.goto("/dashboard?view=executiva");
  await expect(page.getByTestId("executive-stock")).toContainText("produtos com saldo");
  await expect(page.getByTestId("executive-priorities")).toHaveAttribute("data-demo-control-state","settled");
  await expect(page.getByTestId("nav-stock")).toBeInViewport();
  await expect(page.getByTestId("executive-priorities").getByRole("link", {name:"Consultar origem →"})).toBeInViewport({ratio:1});
  await capture(page,`dashboard-${viewport.width}x${viewport.height}`);
  await page.getByRole("link",{name:"Consultar estoque →"}).click();
  await expect(page.getByTestId("stock-positions")).toBeVisible();
  await page.getByRole("textbox",{name:"Buscar produto"}).fill("Atlas");
  await page.getByLabel("Ordenar",{exact:true}).selectOption("-DOMESTIC");
  await expect(page.locator("#stock-product-1")).toBeVisible();
  const search=new URL(page.url()).search;
  await capture(page,`stock-${viewport.width}x${viewport.height}`);
  await page.locator("#stock-product-1").click();
  await expect(page.getByTestId("stock-product-context")).toContainText("Raquete Atlas");
  await page.locator("#purchase-1").click();
  await expect(page.getByTestId("stock-product-context")).toContainText(/620,00/);
  await expect(page.getByTestId("stock-product-context")).toContainText("Base de 10");
  await capture(page,`product-${viewport.width}x${viewport.height}`);
  await page.locator("#open-cost-composition").click();
  await expect(page.getByTestId("stock-product-context")).toContainText("6.000,00");
  await expect(page.getByTestId("stock-product-context")).toContainText("12.000,00");
  await capture(page,`composition-${viewport.width}x${viewport.height}`);
  await page.getByRole("button",{name:"DEMO-comercial.pdf ↗"}).click();
  await expect(page.locator('[data-pdf-ready="true"]')).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();
  await capture(page,`document-${viewport.width}x${viewport.height}`);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button",{name:"DEMO-comercial.pdf ↗"})).toBeFocused();
  await page.goBack();await expect(page.locator("#open-cost-composition")).toBeFocused();
  await page.goBack();await expect(page.locator("#purchase-1")).toBeVisible();
  await page.goBack();await expect(page.locator("#stock-product-1")).toBeFocused();
  expect(new URL(page.url()).search).toBe(search);
  await expect(page.getByLabel("Ordenar",{exact:true})).toHaveValue("-DOMESTIC");
  await expect(page.getByRole("textbox",{name:"Buscar produto"})).toHaveValue("Atlas");
  await page.reload();await expect(page.locator("#stock-product-1")).toBeVisible();
  expect(errors).toEqual([]);expect(writes).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
});

test("stock error, retry, empty, delayed response, collapse and resize",async({page})=>{
  await page.setViewportSize(views[0]);await login(page);
  let fail=true;
  await page.route("**/api/reporting/stock-positions?*",async route=>{
    if(fail)await route.fulfill({status:503,contentType:"application/json",body:'{"message":"fixture failure"}'});
    else if(new URL(route.request().url()).searchParams.get("q")==="slow") {await new Promise(r=>setTimeout(r,1800));await route.continue().catch(()=>{});}
    else await route.continue();
  });
  await page.goto("/inventory/positions");await expect(page.getByRole("alert")).toBeVisible();
  fail=false;await page.getByRole("button",{name:"Tentar novamente"}).click();await expect(page.locator("#stock-product-1")).toBeVisible();
  await page.getByRole("textbox",{name:"Buscar produto"}).fill("slow");
  await page.getByRole("textbox",{name:"Buscar produto"}).fill("Atlas");
  await expect(page.locator("#stock-product-1")).toBeVisible();await page.waitForTimeout(2100);await expect(page.locator("#stock-product-1")).toBeVisible();
  await page.getByRole("textbox",{name:"Buscar produto"}).fill("nenhum-produto");await expect(page.getByText("Nenhum produto neste recorte.",{exact:false})).toBeVisible();
  await capture(page,"stock-empty");
  await page.getByRole("button",{name:"Limpar filtros"}).click();
  await page.getByTestId("shell-rail-toggle").click();await expect(page.getByTestId("shell-rail-toggle")).toHaveAttribute("aria-expanded","false");
  await page.setViewportSize(views[3]);await expect(page.getByTestId("nav-stock")).toBeInViewport();
  await page.getByTestId("shell-rail-toggle").click();await expect(page.getByTestId("shell-rail-toggle")).toHaveAttribute("aria-expanded","true");
  await expect(page.getByTestId("nav-stock")).toBeInViewport();
});

test("E0 failed SKU resolution does not request all movements; FX recovers",async({page})=>{
  await login(page);const movements:string[]=[];
  page.on("request",r=>{if(r.url().includes("/api/inventory/movements"))movements.push(r.url());});
  await page.route("**/api/products?*",route=>route.fulfill({status:503,contentType:"application/json",body:"{}"}));
  await page.goto("/inventory/movements?q=Atlas");await expect(page.getByText("Não foi possível identificar o produto.",{exact:false})).toBeVisible();expect(movements).toEqual([]);
  await page.unroute("**/api/products?*");
  let fail=true;
  await page.route("**/api/payables/1/fx*",async route=>{if(fail)await route.fulfill({status:503,contentType:"application/json",body:"{}"});else await route.continue();});
  await page.goto("/payables/1/fx");await expect(page.getByText("Não foi possível carregar o câmbio.",{exact:false})).toBeVisible();
  fail=false;await page.getByRole("button",{name:"Tentar novamente"}).click();await expect(page.getByTestId("payable-fx-panel")).toBeVisible();
});

test("visual normal AP and costs remain operational",async({page})=>{
  await login(page);await page.setViewportSize(views[0]);
  await page.goto("/payables");await expect(page.getByTestId("ap-table")).toBeVisible();await capture(page,"ap-laptop");
  await page.getByTestId("ap-row-1").click();await expect(page.getByRole("dialog")).toBeVisible();await page.keyboard.press("Escape");await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto("/costing/1");await expect(page.getByTestId("costing-result")).toBeVisible();await capture(page,"costs-laptop");
  if(evidence)writeFileSync(join(evidence,"viewport-metadata.json"),JSON.stringify(await page.evaluate(()=>({inner:[innerWidth,innerHeight],outer:[outerWidth,outerHeight],dpr:devicePixelRatio,scale:visualViewport?.scale,build:document.querySelector('[data-testid="runtime-badge"]')?.getAttribute("title")})),null,2));
});

test("E0 commercial filter failure never falls back to the broad snapshot",async({page})=>{
  await login(page);let fail=false;
  await page.route("**/api/reporting/commercial-availability?*",async route=>fail?route.fulfill({status:503,json:{message:"fixture"}}):route.continue());
  await page.goto("/dashboard?view=comercial");const table=page.getByTestId("commercial-table");
  await expect(table.locator("tbody tr")).toHaveCount(2);fail=true;
  await table.getByLabel("Busca",{exact:true}).fill("Atlas");await expect(table.getByRole("alert")).toBeVisible();await expect(table.locator("tbody tr")).toHaveCount(0);
  fail=false;await table.getByRole("button",{name:"Tentar novamente"}).click();await expect(table.locator("tbody tr")).toHaveCount(1);await expect(table).toContainText("Atlas");
});
