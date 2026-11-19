import { chromium, expect } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const out=resolve('../../docs/v2/etapa-detalhes-recebimento-20261118/before');mkdirSync(out,{recursive:true});
const browser=await chromium.launch();const page=await browser.newPage({baseURL:'http://127.0.0.1:8082',viewport:{width:1366,height:768},locale:'pt-BR'});const results=[];
try {
 await page.goto('/login');await page.getByRole('button',{name:/acesso.*admin/i}).click();await expect(page.getByTestId('dashboard-page')).toBeVisible();
 const build=await (await page.request.get('/assets/build-info.json')).json();
 for(const [route,name] of [['/orders/2','order'],['/orders/2/commercial','commercial'],['/customs/2','operation'],['/inventory/receiving?state=all','receiving']]){
  await page.goto(route);await page.waitForLoadState('networkidle');await page.screenshot({path:resolve(out,name+'-top.png')});
  const controls=await page.locator('main a,main button').evaluateAll(xs=>xs.map(x=>({label:x.textContent.trim(),href:x.getAttribute('href'),y:Math.round(x.getBoundingClientRect().y)})));
  await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));await page.screenshot({path:resolve(out,name+'-bottom.png')});
  results.push({runtime:'8082 / 5458',profile:'admin',route,headings:await page.locator('h1,h2').allTextContents(),controls});
 }
 await page.goto('/customs/2');await page.waitForLoadState('networkidle');let clicks=0;
 await page.getByTestId('page-header').getByRole('link',{name:'Receber mercadorias',exact:true}).click();clicks++;await page.waitForLoadState('networkidle');const queue=page.url();
 const receive=page.getByRole('button',{name:'Receber',exact:true}).first();
 if(await receive.count()){await receive.click();clicks++;await page.waitForLoadState('networkidle');await page.getByRole('button',{name:'Conferir recebimento',exact:true}).click();clicks++;}
 results.push({task:'Operação → conferência, sem gravar',clicks,queue,result:await page.locator('main').innerText()});
 await page.goto('/orders/2');await page.waitForLoadState('networkidle');await page.getByTestId('cockpit-commercial-link').click();await page.waitForLoadState('networkidle');
 results.push({task:'Pedido → comercial / faturamento',clicks:1,invoiceSectionY:await page.getByTestId('order-invoices').evaluate(x=>Math.round(x.getBoundingClientRect().y)),result:'Exige rolar até Faturas após abrir o comercial; nenhuma gravação.'});
 writeFileSync(resolve(out,'baseline.json'),JSON.stringify({build:build.build_id,results},null,2));console.log('Baseline UI saved: '+results.length+' observations');
}finally{await browser.close();}
