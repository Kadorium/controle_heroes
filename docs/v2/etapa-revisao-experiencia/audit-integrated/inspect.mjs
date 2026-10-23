// Read-only route inventory of the preserved release. No application evaluation writes.
import { chromium } from '../../../../v2/frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const base='http://127.0.0.1:8094';
const out=resolve('../audit-lab/integrated-20261023/inspection');mkdirSync(out,{recursive:true});
const browser=await chromium.launch();const page=await browser.newPage({baseURL:base,viewport:{width:1366,height:681},deviceScaleFactor:1});
await page.goto('/login');await page.getByLabel(/e-?mail/i).fill('admin@epic.com.br');await page.getByLabel(/senha/i).fill(process.env.AUDIT_ADMIN_PASSWORD);await page.getByRole('button',{name:/entrar/i}).click();await page.waitForURL(u=>!u.pathname.includes('login'));
for(const route of process.argv.slice(2)){
 await page.goto(route);await page.waitForLoadState('networkidle');
 const name=route.replace(/[^a-z0-9]/gi,'_');
 const state=await page.locator('#main-content').evaluate(el=>({text:el.innerText,controls:[...el.querySelectorAll('input,select,textarea,button,a,[data-testid]')].map(e=>({tag:e.tagName,testid:e.getAttribute('data-testid'),type:e.getAttribute('type'),label:e.getAttribute('aria-label'),id:e.id,name:e.getAttribute('name'),placeholder:e.getAttribute('placeholder'),text:(e.innerText||'').slice(0,180),href:e.getAttribute('href'),value:e.value,options:e.tagName==='SELECT'?[...e.options].map(o=>({value:o.value,text:o.text})):undefined}))}));
 writeFileSync(resolve(out,name+'.json'),JSON.stringify(state,null,2));await page.screenshot({path:resolve(out,name+'.png')});console.log(route+'\n'+state.text.slice(0,18000));
}
await browser.close();
