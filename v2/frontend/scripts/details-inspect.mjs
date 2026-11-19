import { chromium, expect } from '@playwright/test';
import { readFileSync,mkdirSync,writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const out=resolve('../../docs/v2/etapa-detalhes-recebimento-20261118');const f=JSON.parse(readFileSync(resolve(out,'fixtures.json'),'utf8'));mkdirSync(resolve(out,'after'),{recursive:true});
const browser=await chromium.launch();const page=await browser.newPage({baseURL:'http://127.0.0.1:8103',viewport:{width:1366,height:768},locale:'pt-BR'});const errors=[];page.on('pageerror',e=>errors.push(String(e)));page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/'))errors.push(r.status()+' '+r.url());});
try{
 await page.goto('/login');await page.getByRole('button',{name:/acesso.*admin/i}).click();await expect(page.getByTestId('dashboard-page')).toBeVisible();
 for(const [route,name] of [[`/customs/${f['case1-submitted'].id}`,'operation-none'],[`/customs/${f['case10-submitted'].id}`,'operation-pending'],[`/orders/${f['mixed-confirmed'].id}`,'order'],[`/orders/${f['mixed-confirmed'].id}/commercial`,'commercial'],['/inventory/receiving?state=all','receiving']]){
  await page.goto(route);await page.waitForLoadState('networkidle');await page.screenshot({path:resolve(out,'after',name+'-top.png')});
  console.log(name,await page.locator('[data-testid="record-work-header"]').innerText().catch(()=>''),await page.locator('[data-testid="record-topics"]').innerText().catch(()=>''));
  if(name==='operation-pending'||name==='commercial'){await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));await page.waitForTimeout(200);await page.screenshot({path:resolve(out,'after',name+'-bottom.png')});console.log('header at bottom',await page.getByTestId('record-work-header').boundingBox());}
 }
 console.log('errors',JSON.stringify(errors));
}finally{await browser.close();}
