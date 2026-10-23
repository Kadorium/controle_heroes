import {test,expect} from '@playwright/test';import {writeFileSync} from 'node:fs';import {resolve} from 'node:path';import {loginAs} from './helpers/orderCreate';
const out=resolve('../../../audit-lab/integrated-20261023/package');
test('FIN-05 API auxiliary volume then real UI pagination discovery',async({page})=>{
 test.setTimeout(60000);expect(new URL(test.info().project.use.baseURL!).port).toBe('8094');await page.setViewportSize({width:1366,height:681});await loginAs(page,'admin@epic.com.br',process.env.AUDIT_ADMIN_PASSWORD);
 const get=async(p:string)=>(await(await page.request.get(p)).json());const send=async(method:string,p:string,data:any)=>{const r=await page.request.fetch(p,{method,data});expect(r.ok(),await r.text()).toBeTruthy();return r.json();};
 // Explicit auxiliary API preparation, NOT credited as UI purchase/billing execution.
 const orders=await get('/api/orders');let o=orders.find((x:any)=>x.code==='AUD26-PAGE');if(!o)o=await send('POST','/api/orders',{code:'AUD26-PAGE',supplier_id:5,currency:'EUR',notes:'Auxiliary pagination fixture, API-prepared; no external effect'});o=await get(`/api/orders/${o.id}`);
 if(!o.items.length)o=await send('POST',`/api/orders/${o.id}/items`,{expected_version:o.version,product_id:43,quantity:'1',unit:'UN',unit_price:'30'});
 if(o.status==='DRAFT')o=await send('POST',`/api/orders/${o.id}/confirm`,{expected_version:o.version});
 let invoices=await get('/api/invoices');let inv=invoices.find((i:any)=>i.invoice_number==='AUD26-PAGE-30');if(!inv)inv=await send('POST',`/api/orders/${o.id}/invoices`,{invoice_number:'AUD26-PAGE-30'});inv=await get(`/api/invoices/${inv.id}`);
 if(inv.status==='DRAFT'){
  inv=await send('PUT',`/api/invoices/${inv.id}/items`,{expected_version:inv.version,items:inv.items.map((i:any)=>({order_item_id:i.order_item_id,quantity:'1',unit_price_gross:'30',unit:'UN',discount_type:'NONE'}))});
  inv=await send('PUT',`/api/invoices/${inv.id}/terms`,{expected_version:inv.version,mode:'AMOUNT',terms:Array.from({length:30},(_,i)=>({due_date:`2026-12-${String(i+1).padStart(2,'0')}`,amount:'1'}))});
  inv=await send('POST',`/api/invoices/${inv.id}/issue`,{expected_version:inv.version,issue_without_document:true,reason_code:'AUD26_PAGINATION_FIXTURE'});
 }
  expect(inv.payables).toHaveLength(30);await page.goto('/payables');await expect(page.getByTestId('ap-table')).toBeVisible();await page.waitForTimeout(500);const rows=await page.getByTestId('ap-table').locator('tbody tr').count();const more=await page.getByRole('button',{name:/^(Próxima|Próximo|Seguinte|Carregar mais)$/i}).count();const footer=page.getByText(/Exibindo/);await footer.scrollIntoViewIfNeeded();await page.screenshot({path:resolve(out,'prints/FIN-05_01_fila_sem_paginacao.png')});const ui=await page.locator('#main-content').innerText();const data=await get('/api/reporting/ap-queue?limit=50'),second=await get('/api/reporting/ap-queue?limit=50&offset=50');
 writeFileSync(resolve(out,'evidencias/FIN-05.json'),JSON.stringify({auxiliaryPreparation:{method:'Public API',order:o.id,invoice:inv.id,payables:30,amountEUR:30,document:'Explicit issue-without-document for volume test only'},uiRows:rows,nextControlCount:more,ui,first:{total:data.total,kpis:data.kpis,count:data.items.length},second:{total:second.total,kpis:second.kpis,count:second.items.length},finding:more===0&&data.total>rows?'FAIL: server pagination exists, no UI page control':'Requires review'},null,2));
  expect(data.total).toBeGreaterThan(50);expect(more,'Observed product defect: no pagination control').toBe(0);
  const captures=[];for(const offset of [0,50]){await page.goto(`/payables?offset=${offset}`);await expect(page.getByTestId('ap-table')).toBeVisible();await page.waitForTimeout(500);const text=await page.locator('#main-content').innerText();await page.screenshot({path:resolve(out,`prints/FIN-06_0${offset===0?1:2}_resumo_pagina${offset===0?1:2}.png`)});captures.push({offset,url:page.url(),text});}
  writeFileSync(resolve(out,'evidencias/FIN-06.json'),JSON.stringify({method:'UI loaded at explicit page URLs because no next control exists. Same population, different offset.',captures,first:data.kpis,second:second.kpis},null,2));
  expect(data.kpis.kpis_by_currency).toEqual(second.kpis.kpis_by_currency);
  expect(data.kpis.unallocated_by_currency).not.toEqual(second.kpis.unallocated_by_currency);
});
