import {test,expect,type Page} from '@playwright/test';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';import {resolve} from 'node:path';
const lab=resolve('../../../audit-lab/receiving-20261023'),out=resolve(lab,'evidence'),f=JSON.parse(readFileSync(resolve(lab,'fixtures.json'),'utf8'));
mkdirSync(out,{recursive:true});
const source=(name:string)=>f['nat-items-'+name].items[0].id;
async function login(page:Page,role='estoque'){
 expect(new URL(test.info().project.use.baseURL!).port).toBe('8092');const h=await(await page.request.get('/api/health')).json();expect(h.alembic_head).toBe('034');
 await page.goto('/login');await page.getByLabel(/e-?mail/i).fill(role+'@epic.com.br');await page.getByLabel(/senha/i).fill(role==='admin'?'admin123':'ensaio123');await page.getByRole('button',{name:/entrar/i}).click();await expect(page.getByTestId('nav-receiving')).toBeVisible();expect((await(await page.request.get('/api/auth/me')).json()).role).toBe(role);
}
async function read(page:Page,name:string){return (await(await page.request.get(`/api/inventory/receiving?item_id=${source(name)}&state=all`)).json()).rows[0];}
async function open(page:Page,name:string){await page.goto(`/inventory/receiving?q=QA-RCV-${name}&state=all`);await page.locator('#receive-open-'+source(name)).click();await expect(page.getByRole('heading',{name:'QA recebimento · '+name,exact:true})).toBeVisible();}
async function shot(page:Page,name:string){await page.screenshot({path:resolve(out,name+'.png')});}
test('estoque: partial, persistence, rest with lost response/reload/retry, ACL',async({page})=>{
 test.setTimeout(90000);await page.setViewportSize({width:1366,height:681});await login(page);await page.getByTestId('nav-receiving').click();await expect(page.getByRole('heading',{name:'Recebimentos',exact:true})).toBeVisible();await page.getByLabel('Situação do recebimento').selectOption('all');await page.getByLabel('Buscar recebimento').fill('QA-RCV');await expect(page.locator('.experience-table')).toContainText('QA-RCV-STOCK');await shot(page,'01-queue-stock');
 let initial=await read(page,'STOCK');expect([0,4,10]).toContain(Number(initial.received_qty));const log:any[]=[{before:initial,executor:'Playwright UI authenticated estoque'}];await open(page,'STOCK');
 if(Number(initial.received_qty)===0){
  await page.getByLabel('Quantidade (UN)').fill('11');await expect(page.getByRole('button',{name:'Conferir recebimento',exact:true})).toBeDisabled();await expect(page.locator('#receiving-quantity-error')).toContainText('até 10 UN');await shot(page,'02-over-limit');
  const bad=await page.request.post('/api/inventory/receiving/confirm',{data:{item_id:source('STOCK'),quantity:'11',unit:'UN',location_code:'DOMESTIC-MAIN',request_key:crypto.randomUUID()}});expect(bad.status()).toBe(409);
  await page.getByLabel('Quantidade (UN)').fill('4');await page.getByLabel('Destino').selectOption('DOMESTIC-MAIN');await page.getByRole('button',{name:'Conferir recebimento',exact:true}).click();await expect(page.getByRole('heading',{name:'Conferir recebimento'})).toBeFocused();await shot(page,'03-review-partial');
  await page.getByRole('button',{name:'Confirmar recebimento',exact:true}).dblclick();await expect(page.locator('#receipt-result')).toContainText('confirmado');await expect(page.getByTestId('receiving-pending')).toHaveText('6 UN');log.push({partial:await read(page,'STOCK')});
 }
 await page.reload();initial=await read(page,'STOCK');if(Number(initial.received_qty)===4){
  await expect(page.getByTestId('receiving-pending')).toHaveText('6 UN');await shot(page,'04-partial-reload');
  await page.getByLabel('Quantidade (UN)').fill('6');await page.getByRole('button',{name:'Conferir recebimento',exact:true}).click();let result:any;
  await page.route('**/api/inventory/receiving/confirm',async route=>{const response=await route.fetch();expect(response.ok()).toBeTruthy();result=await response.json();await route.abort('failed');});
  await page.getByRole('button',{name:'Confirmar recebimento',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Resposta não recebida');expect(Number((await read(page,'STOCK')).received_qty)).toBe(10);await shot(page,'05-lost-response');
  await page.unroute('**/api/inventory/receiving/confirm');await page.reload();await expect(page.getByRole('heading',{name:'Conferir recebimento'})).toBeVisible();await page.getByRole('button',{name:'Confirmar recebimento',exact:true}).click();await expect(page.locator('#receipt-result')).toContainText('#'+result.receipt_id);await expect(page.getByTestId('receiving-pending')).toHaveText('0 UN');await shot(page,'06-complete');log.push({retrySameReceipt:result.receipt_id,final:await read(page,'STOCK')});
  await page.getByRole('link',{name:'Ver saldo',exact:true}).click();await expect(page.getByTestId('sku-buckets')).toContainText('10');await page.goBack();await expect(page.getByTestId('receiving-pending')).toHaveText('0 UN');
 }
 const moves=await(await page.request.get(`/api/inventory/movements?product_id=${f['product-STOCK'].id}`)).json();expect(moves.length).toBe(2);expect(moves.map((m:any)=>Number(m.quantity_delta)).sort()).toEqual([4,6]);
 await open(page,'BLOCKED');await expect(page.getByRole('alert')).toContainText('Aguardando liberação');await expect(page.getByRole('button',{name:'Conferir recebimento',exact:true})).toHaveCount(0);await shot(page,'07-blocked');
 const denied=await page.request.post('/api/inventory/receiving/confirm',{data:{item_id:source('BLOCKED'),quantity:'1',unit:'UN',location_code:'DOMESTIC-MAIN',request_key:crypto.randomUUID()}});expect(denied.status()).toBe(409);
 for(const path of ['/api/import-processes/10','/api/payables/2','/api/payments/2','/api/costing/cases/2','/api/catalog/sales-prices?product_id=3'])expect((await page.request.get(path)).status(),path).toBe(403);
 for(const [route,message] of [['/customs/10','Sem permissão para processos aduaneiros.'],['/costing/2','É preciso costing:read.'],['/catalog/prices/import','Você não tem permissão para alterar preços.']]){await page.goto(route);await expect(page.getByText(message,{exact:true})).toBeVisible();}
 log.push({movements:moves,blocked:await read(page,'BLOCKED')});writeFileSync(resolve(out,'stock-flow.json'),JSON.stringify(log,null,2));
});
test('two estoque browser sessions compete for the same release',async({browser})=>{
 const a=await browser.newPage({baseURL:test.info().project.use.baseURL}),b=await browser.newPage({baseURL:test.info().project.use.baseURL});await login(a);await login(b);const before=await read(a,'RACE');expect(Number(before.received_qty),'reconcile previous race before a retest').toBe(0);
 for(const page of [a,b]){await open(page,'RACE');await page.getByLabel('Quantidade (UN)').fill('6');await page.getByRole('button',{name:'Conferir recebimento',exact:true}).click();}
 await Promise.all([a.getByRole('button',{name:'Confirmar recebimento',exact:true}).click(),b.getByRole('button',{name:'Confirmar recebimento',exact:true}).click()]);
 await expect.poll(async()=>Number((await read(a,'RACE')).received_qty)).toBe(6);await expect.poll(async()=>await a.locator('#receipt-result').count()+await b.locator('#receipt-result').count()).toBe(1);
 const loser=await a.locator('#receipt-result').count()?b:a;await expect(loser.getByRole('alert')).toContainText('saldo liberado disponível');await shot(loser,'08-concurrent-blocked');writeFileSync(resolve(out,'race.json'),JSON.stringify(await read(a,'RACE'),null,2));await a.close();await b.close();
});
test('admin existing Customs receipt panel remains operational',async({page})=>{
 await login(page,'admin');const before=await read(page,'ADMIN');expect(Number(before.received_qty),'reconcile existing receipt before repeating').toBe(0);await page.goto(`/customs/${f.process.id}?section=liberacoes`);const panel=page.getByTestId('customs-receipt-panel');await expect(panel).toBeVisible();
 for(const input of await panel.locator('input[data-testid^="receipt-proposed-"]').all())await input.fill('0');await page.getByTestId('receipt-proposed-'+source('ADMIN')).fill('1');await panel.getByTestId('receipt-receive').click();await expect(page.getByTestId('receipt-residual-qty-'+source('ADMIN'))).toHaveText('3');await page.reload();await expect(page.getByTestId('receipt-residual-qty-'+source('ADMIN'))).toHaveText('3');await panel.scrollIntoViewIfNeeded();await shot(page,'09-admin-regression');
 expect(Number((await read(page,'ADMIN')).received_qty)).toBe(1);
});
