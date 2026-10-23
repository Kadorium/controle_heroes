import {test,expect,type Page} from '@playwright/test';
import {readFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
const lab=resolve('../../../audit-lab/stock-executive-20261023'),manifest=JSON.parse(readFileSync(resolve(lab,'scenario/manifest.json'),'utf8'));
const show=manifest.products[0],a=manifest.stories[0];
const evidence=resolve(lab,'evidence');mkdirSync(evidence,{recursive:true});
async function login(page:Page){expect(new URL(test.info().project.use.baseURL!).port).toBe('8088');const h=await(await page.request.get('/api/health')).json();expect(h.alembic_head).toBe('033');await page.request.post('/api/auth/dev-login');}
async function ready(page:Page){await expect(page.locator('.stock-numbers')).toBeVisible();await expect(page.getByText('Consultando estoque…',{exact:true})).toHaveCount(0);}
for(const viewport of [{width:1366,height:681},{width:1366,height:768},{width:1920,height:1080},{width:1024,height:768}])test(`G2 stock journey ${viewport.width}x${viewport.height}`,async({page})=>{
 await page.setViewportSize(viewport);await login(page);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/dashboard?view=executiva');await ready(page);await expect(page.getByTestId('nav-stock')).toBeInViewport();await page.screenshot({path:resolve(evidence,`dashboard-${viewport.width}x${viewport.height}.png`)});
 await page.getByRole('link',{name:'Explorar estoque →'}).click();await ready(page);await page.getByRole('textbox',{name:'Buscar produto'}).fill('SHOW26');await ready(page);
 await expect(page.locator('.stock-numbers')).toContainText('54.900,00');await expect(page.locator('.stock-numbers')).toContainText('138.138,00');
 await page.getByLabel('Ordenar',{exact:true}).selectOption('-cost');await ready(page);const context=new URL(page.url()).search;
 await page.screenshot({path:resolve(evidence,`stock-${viewport.width}x${viewport.height}.png`)});
 await page.locator(`#stock-product-${show.id}`).click();await expect(page.getByTestId('stock-value-detail')).toContainText('54.900,00');
 await page.locator(`#purchase-${a.case.id}`).click();await expect(page.getByTestId('stock-product-context')).toContainText('Base de 20');await expect(page.getByTestId('stock-product-context')).toContainText('1.200,00');
 await page.screenshot({path:resolve(evidence,`product-${viewport.width}x${viewport.height}.png`)});
 await page.locator('#open-cost-composition').click();await expect(page.getByTestId('stock-product-context')).toContainText('18.000,00');
 const doc=page.getByRole('button',{name:'A-commercial.pdf ↗'});await doc.click();await expect(page.locator('[data-pdf-ready="true"]')).toBeVisible();await expect(page.locator('canvas')).toBeVisible();
 await page.screenshot({path:resolve(evidence,`document-${viewport.width}x${viewport.height}.png`)});await page.keyboard.press('Escape');await expect(doc).toBeFocused();
 await page.goBack();await expect(page.locator('#open-cost-composition')).toBeFocused();await page.goBack();await expect(page.locator(`#purchase-${a.case.id}`)).toBeFocused();await page.goBack();await ready(page);
 await expect(page.locator(`#stock-product-${show.id}`)).toBeFocused();expect(new URL(page.url()).search).toBe(context);await page.reload();await ready(page);await expect(page.getByRole('textbox',{name:'Buscar produto'})).toHaveValue('SHOW26');
 expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
test('multiple filters, grouping independent, views, clear and reload',async({page})=>{
 await login(page);await page.goto('/inventory/positions?modality_ids=bt&group_by=item_kind');await ready(page);
 await page.locator('.stock-select').filter({has:page.locator('summary',{hasText:'Tipo de item'})}).locator('summary').click();
 for(const label of ['Roupas','Raquetes','Bolas']){await page.locator('.stock-select-options').getByLabel(new RegExp(label)).check();await ready(page);}
 await page.keyboard.press('Escape');
 const values=await page.locator('.stock-numbers').innerText();for(const group of ['model','modality','']){await page.getByLabel('Agrupar por',{exact:true}).selectOption(group);await ready(page);expect(await page.locator('.stock-numbers').innerText()).toBe(values);}
 await page.getByRole('button',{name:'Salvar visão',exact:true}).click();await page.getByLabel('Nome da visão').fill('Executiva E2E '+Date.now());await page.getByLabel('Usar como meu padrão').check();await page.getByRole('button',{name:'Salvar',exact:true}).click();await expect(page.getByRole('status')).toContainText('Visão salva');
 const url=page.url();await page.goto('/inventory/positions');await ready(page);await expect(page.locator('.stock-chips')).toContainText('Roupas');await expect(page.locator('.stock-chips')).toContainText('Bolas');await page.goto('/inventory/positions?modality_ids=&group_by=');await ready(page);await expect(page.locator('.stock-chips')).not.toContainText('Beach Tennis');await page.goto(url);await ready(page);
 await page.screenshot({path:resolve(evidence,'stock-combined.png')});
});
test('error, recovery, no matches, delayed response and resize',async({page})=>{
 await login(page);let fail=true;await page.route('**/api/reporting/stock-explorer?*',async r=>{if(fail)await r.fulfill({status:503,contentType:'application/json',body:'{"message":"Indisponível no teste"}'});else await r.continue();});
 await page.goto('/inventory/positions');await expect(page.getByRole('alert')).toBeVisible();fail=false;await page.getByRole('button',{name:'Tentar novamente',exact:true}).click();await ready(page);
 await page.getByRole('textbox',{name:'Buscar produto'}).fill('SEM-RESULTADO-XYZ');await ready(page);await expect(page.getByText('Nenhum produto nesta seleção. Ajuste os filtros.')).toBeVisible();
 await page.unroute('**/api/reporting/stock-explorer?*');await page.route('**/api/reporting/stock-explorer?*',async r=>{if(r.request().url().includes('q=SHOW'))await new Promise(resolve=>setTimeout(resolve,600));await r.continue().catch(()=>{});});
 await page.getByRole('textbox',{name:'Buscar produto'}).fill('SHOW');await page.getByRole('textbox',{name:'Buscar produto'}).fill('FIERCE');await ready(page);await expect(page.locator('tbody')).not.toContainText('SHOW26');
 await page.setViewportSize({width:1024,height:768});await expect(page.getByTestId('nav-stock')).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
test('price creation through UI, overlap blocked, persistence',async({page})=>{
 await login(page);const r=await page.request.post('/api/products',{data:{sku:'QA-PRICE-'+Date.now(),description:'DEMONSTRAÇÃO validação de preço'}});const p=await r.json();await page.request.patch(`/api/products/${p.id}`,{data:{unit:'UN'}});
 await page.goto(`/catalog/products/${p.id}`);await page.getByRole('button',{name:'Novo preço'}).click();await page.getByLabel('Preço em reais').fill('750');await page.getByLabel('Preço válido de').fill('2027-01-23');await page.getByLabel('Preço válido até').fill('2027-02-23');await page.getByLabel('Motivo do preço').fill('Validação UI isolada de vigência futura');await page.getByRole('button',{name:'Registrar preço'}).click();await expect(page.getByTestId('sales-prices')).toContainText('Preço registrado.');await page.reload();await expect(page.getByTestId('sales-prices')).toContainText('750,00');
 await page.getByRole('button',{name:'Novo preço'}).click();await page.getByLabel('Preço em reais').fill('800');await page.getByLabel('Preço válido de').fill('2027-01-24');await page.getByLabel('Motivo do preço').fill('Sobreposição deve ser bloqueada');await page.getByRole('button',{name:'Registrar preço'}).click();await expect(page.getByTestId('sales-prices')).toContainText('Já existe preço');await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Novo preço'})).toBeFocused();
});
