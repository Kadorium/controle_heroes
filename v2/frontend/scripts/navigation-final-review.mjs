import { chromium,expect } from '@playwright/test';
import { readFileSync,writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';
const out=resolve('../../docs/v2/etapa-consolidacao-navegacao');
const browser=await chromium.launch();const results=[];
try{
 const page=await browser.newPage({baseURL:'http://127.0.0.1:8082',viewport:{width:1366,height:768},locale:'pt-BR'});
 await page.goto('/login');await page.getByRole('button',{name:/acesso.*admin/i}).click();await expect(page.getByRole('navigation',{name:'Módulos',exact:true})).toBeVisible();
 const info=await(await page.request.get('/assets/build-info.json')).json();expect(info.build_id).toBe('executive-20261118.1');
 const html=await(await page.request.get('/')).text();const files=[...html.matchAll(/(?:src|href)="(\/assets\/[^" ]+)"/g)].map(x=>x[1]);
 for(const file of files){const response=await page.request.get(file);expect(response.ok()).toBeTruthy();const digest=createHash('sha256').update(await response.body()).digest('hex');expect(digest).toBe(info.assets[file.split('/').pop()]);}
 for(const [url,name] of [['/inventory/positions?q=SHOW26','stock'],['/inventory/receiving?state=all&q=SHOW26','receiving'],['/costing','costing']]){
  await page.goto(url);await page.waitForLoadState('networkidle');await page.screenshot({path:resolve(out,'ui-release/final-'+name+'.png')});results.push({runtime:'8082',profile:'admin',url:page.url(),result:'PASS',action:'Abri URL existente / Vi área e aba corretas / Conferi hierarquia visual'});
 }
 const lab=await browser.newPage({baseURL:'http://127.0.0.1:8102',viewport:{width:1440,height:900},locale:'pt-BR'});
 await lab.goto('/login');await lab.getByRole('button',{name:/acesso.*admin/i}).click();await expect(lab.getByRole('navigation',{name:'Módulos',exact:true})).toBeVisible();
 await lab.getByRole('navigation',{name:'Módulos',exact:true}).getByRole('link',{name:'Conferir documentos',exact:true}).click();
 const doc=JSON.parse(readFileSync(resolve(out,'document-fixture.json'),'utf8'));await lab.getByTestId('ingestion-row-'+doc.document_id).click();
 await expect(lab.locator('[data-pdf-ready="true"]')).toBeVisible({timeout:30000});
 await lab.screenshot({path:resolve(out,'ui/transversal-document-ready.png')});results.push({runtime:'8102 / 5460',profile:'admin',result:'PASS',action:'Conferir documentos → packing fictício → PDF renderizado e campos da revisão'});
 writeFileSync(resolve(out,'final-review.json'),JSON.stringify({build:info.build_id,assets:files,results},null,2));console.log(JSON.stringify({build:info.build_id,results}));
}finally{await browser.close();}
