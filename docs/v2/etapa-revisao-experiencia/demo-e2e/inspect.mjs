import {chromium} from '../../../../v2/frontend/node_modules/playwright-core/index.mjs';
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
const output=resolve('../audit-lab/stock-executive-20261023/evidence');mkdirSync(output,{recursive:true});
const browser=await chromium.launch({headless:true});const context=await browser.newContext({baseURL:'http://127.0.0.1:8088',viewport:{width:1366,height:681}});const page=await context.newPage();
await context.request.post('/api/auth/dev-login');
const api=await context.request.get('/api/reporting/stock-explorer?modality_ids=bt&group_by=item_kind');
writeFileSync(resolve(output,'explorer-read.json'),await api.text());console.log('explorer',api.status());
page.on('pageerror',e=>console.log('ERROR',e.message));
for(const [name,path] of [['dashboard','/dashboard?view=executiva'],['stock','/inventory/positions'],['show','/inventory/positions?q=SHOW26']]){
 await page.goto(path);await page.locator('[data-testid="executive-stock"], [data-testid="stock-positions"]').waitFor();await page.getByRole('status').filter({hasText:'Consultando estoque'}).waitFor({state:'hidden'});await page.locator('.stock-numbers').waitFor({timeout:20000});await page.screenshot({path:resolve(output,name+'.png')});console.log(name,(await page.locator('main').innerText()).slice(0,900));
}
await browser.close();
