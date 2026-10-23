import {test,expect} from '@playwright/test';
test.beforeEach(async({page})=>{expect(new URL(test.info().project.use.baseURL!).port).toBe('8086');expect((await page.request.post('/api/auth/dev-login')).ok()).toBeTruthy();});
test('local and regime filters remain explicit and survive return',async({page})=>{
 await page.goto('/inventory/positions?q=LAB-VOLUME');await expect(page.getByLabel('Local',{exact:true}).locator('option')).not.toHaveCount(1);
 const options=await page.getByLabel('Local',{exact:true}).locator('option').evaluateAll(es=>es.map(e=>({value:(e as HTMLOptionElement).value,label:e.textContent})));
 const domestic=options.find(o=>o.label?.includes('doméstico'))!;await page.getByLabel('Local',{exact:true}).selectOption(domestic.value);
 await page.getByLabel('Posição',{exact:true}).selectOption('DOMESTIC');await expect(page.locator('.product-name').first()).toBeVisible();
 const search=new URL(page.url()).search;await page.locator('.product-name').first().click();await page.keyboard.press('Escape');expect(new URL(page.url()).search).toBe(search);await expect(page.getByLabel('Local',{exact:true})).toHaveValue(domestic.value);
 await page.reload();await expect(page.getByLabel('Local',{exact:true})).toHaveValue(domestic.value);
});
for(const status of [403,404])test(`FX ${status} is recoverable, not infinite loading`,async({page})=>{
 let fail=true;await page.route('**/api/payables/1/fx*',r=>fail?r.fulfill({status,json:{message:'controlled'}}):r.continue());
 await page.goto('/payables/1/fx');await expect(page.getByText('Não foi possível carregar o câmbio.',{exact:false})).toBeVisible();fail=false;await page.getByRole('button',{name:'Tentar novamente'}).click();await expect(page.getByTestId('payable-fx-panel')).toBeVisible();
});
test('movement ambiguous and empty lookup never opens the broad list',async({page})=>{
 const requests:string[]=[];page.on('request',r=>{if(r.url().includes('/api/inventory/movements'))requests.push(r.url());});
 await page.goto('/inventory/movements?q=LAB-VOLUME');await expect(page.getByText('Mais de um produto encontrado.',{exact:false})).toBeVisible();expect(requests).toEqual([]);
 await page.goto('/inventory/movements?q=NOT-FOUND-ANYWHERE');await expect(page.getByText('Nenhum produto encontrado para a busca.')).toBeVisible();expect(requests).toEqual([]);
});
test('no publication and absent sources are honest read-only fixtures',async({page})=>{
 await page.route('**/api/costing/products/1/sources*',async r=>{const response=await r.fetch(),b=await response.json();b.rows=b.rows.filter((c:{case_id:number})=>c.case_id===2);b.total=1;b.rows[0].current_published_id=null;await r.fulfill({response,json:b});});
 await page.goto('/inventory/positions?product=1');await expect(page.locator('#purchase-2')).toContainText('sem versão publicada');await page.locator('#purchase-2').click();await expect(page.getByRole('combobox',{name:'Versão',exact:true})).toHaveValue('');await expect(page.locator('.experience-cost-value')).toHaveCount(0);
 await page.route('**/api/costing/products/1/versions/3',async r=>{const response=await r.fetch(),b=await response.json();b.components.forEach((c:{documents:unknown[]})=>c.documents=[]);await r.fulfill({response,json:b});});
 await page.getByRole('combobox',{name:'Versão',exact:true}).selectOption('3');await page.locator('#open-cost-composition').click();await expect(page.getByText('Documento ausente ou sem acesso').first()).toBeVisible();
});
test('reduced motion and 200-percent-equivalent reflow preserve reachable controls',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:683,height:340});await page.goto('/inventory/positions?q=LAB-VOLUME');await expect(page.locator('.product-name').first()).toBeVisible();
 await page.getByTestId('shell-rail-toggle').click();await expect(page.getByTestId('nav-stock')).toBeInViewport();
 await page.getByLabel('Buscar produto',{exact:true}).focus();await page.keyboard.press('Control+A');await page.keyboard.type('Atlas');await expect(page.locator('#stock-product-1')).toBeVisible();
 await page.locator('#stock-product-1').focus();await page.keyboard.press('Enter');await expect(page.locator('#purchase-1')).toBeVisible();await page.keyboard.press('Escape');await expect(page.locator('#stock-product-1')).toBeFocused();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
