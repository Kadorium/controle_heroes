import { chromium, expect } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const out = resolve('../../docs/v2/etapa-consolidacao-navegacao/before');
mkdirSync(out,{recursive:true});
const browser=await chromium.launch();
const page=await browser.newPage({baseURL:'http://127.0.0.1:8082',viewport:{width:1366,height:768},locale:'pt-BR'});
const evidence=[];
try {
 await page.goto('/login');await page.getByRole('button',{name:/acesso.*admin/i}).click();await expect(page.getByTestId('dashboard-page')).toBeVisible();
 const build=await (await page.request.get('/assets/build-info.json')).json();
 const nav=page.getByRole('navigation',{name:'Módulos',exact:true});
 const links=await nav.locator('a').evaluateAll(xs=>xs.map(x=>({label:x.getAttribute('aria-label'),href:x.getAttribute('href')})));
 for (const [route,name] of [['/inventory/positions','stock'],['/inventory/receiving?state=all&q=SHOW26','receiving'],['/costing','costing'],['/payables?purpose=fx','fx'],['/catalog/suppliers','suppliers']]) {
  await page.goto(route);await page.waitForLoadState('networkidle');
  evidence.push({profile:'admin',url:page.url(),headings:await page.locator('h1,h2').allTextContents(),controls:await page.locator('main a,main button').evaluateAll(xs=>xs.map(x=>({text:x.textContent,href:x.getAttribute('href')})))});
  if(['stock','costing'].includes(name))await page.screenshot({path:resolve(out,name+'.png')});
 }
 writeFileSync(resolve(out,'navigation.json'),JSON.stringify({build,links,evidence},null,2));
 console.log(JSON.stringify({build:build.build_id,count:links.length,visited:evidence.map(e=>e.url)}));
}finally{await browser.close();}
