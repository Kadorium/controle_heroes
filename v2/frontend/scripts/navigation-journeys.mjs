import { chromium, expect } from '@playwright/test';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
const baseURL='http://127.0.0.1:8102';
const out=resolve('../../docs/v2/etapa-consolidacao-navegacao/ui');mkdirSync(out,{recursive:true});
const fixture=JSON.parse(readFileSync(resolve(out,'../fixtures.json'),'utf8'));
const results=[],errors=[],mutations=[];
const browser=await chromium.launch();let page,profile;
const nav=()=>page.getByRole('navigation',{name:'Módulos',exact:true});
const settle=async()=>{await page.waitForLoadState('networkidle');};
const area=async(name,section)=>{await nav().getByRole('link',{name,exact:true}).click();await settle();if(section){await page.locator('.area-navigation').getByRole('link',{name:section,exact:true}).click();await settle();}};
async function login(role){
 profile=role;if(page)await page.context().close();page=await browser.newPage({baseURL,viewport:{width:1366,height:768},locale:'pt-BR'});
 page.on('pageerror',e=>errors.push({profile,message:e.message}));
 page.on('request',request=>{if(['POST','PUT','PATCH','DELETE'].includes(request.method())&&!request.url().includes('/auth/')&&!request.url().includes('/fx/quotes/refresh'))mutations.push({profile,method:request.method(),url:request.url(),body:request.postData()});});
 await page.goto('/login');if(role==='admin')await page.getByRole('button',{name:/acesso.*admin/i}).click();else{await page.getByLabel(/e-?mail/i).fill(role+'@epic.com.br');await page.getByLabel(/senha/i).fill('ensaio123');await page.getByRole('button',{name:/entrar/i}).click();}await expect(nav()).toBeVisible();await settle();
}
async function record(name,fn){try{const detail=await fn();results.push({name,profile,runtime:baseURL,result:'PASS',url:page.url(),detail});console.log('PASS '+name);}catch(e){results.push({name,profile,runtime:baseURL,result:'FAIL',url:page?.url(),error:e.message});await page.screenshot({path:resolve(out,`journey-failure-${results.length}.png`)});console.log('FAIL '+name+' '+e.message.slice(0,800));}finally{writeFileSync(resolve(out,'journeys.json'),JSON.stringify({results,errors,mutations},null,2));}}
async function shot(name){await page.screenshot({path:resolve(out,name+'.png')});}
try{
 await login('admin');
 await record('1 e 2 / produto com saldo, custo, histórico e retorno',async()=>{
  await area('Produtos');await page.getByPlaceholder('Nome ou código do produto (SKU)').fill('SHOW26');await expect(page.locator('#stock-product-3')).toBeVisible();
  const origin=page.url();await page.locator('#stock-product-3').click();await expect(page.getByTestId('stock-value-detail')).toBeVisible();
  await page.locator('#purchase-2').click();await expect(page.locator('#open-cost-composition')).toBeVisible();await page.locator('#open-cost-composition').click();await settle();
  await expect(page.locator('main')).toContainText('Composição do custo');await shot('product-cost');
  await page.locator('#stock-context-back').click();await settle();
  const detail=page.url();await page.getByRole('link',{name:'Histórico de estoque',exact:true}).last().click();await expect(page.getByRole('heading',{name:'Histórico de estoque',exact:true}).first()).toBeVisible();
  expect(new URL(page.url()).searchParams.get('product_id')).toBe('3');await page.reload();await settle();
  await page.getByRole('link',{name:'← Voltar ao estoque'}).click();await settle();expect(page.url()).toBe(detail);
  return {opened:origin,saw:'SHOW26, base e versão do custo desembarcado',clicked:'Produto → compra → composição → histórico → voltar',result:'Filtro de produto e contexto do retorno preservados'};
 });
 await record('1 / catálogo inclui produto sem estoque',async()=>{
  await area('Produtos','Catálogo e preços');await page.getByTestId('products-search').fill('NAV18-SEM-ESTOQUE');await expect(page.getByTestId('products-table')).toContainText('NAV18-SEM-ESTOQUE');
  await page.getByTestId('products-table').locator('tr').filter({hasText:'NAV18-SEM-ESTOQUE'}).getByRole('link',{name:'Ver estoque →',exact:true}).click();await settle();await expect(page.locator('main')).toContainText('NAV18 Produto fictício sem estoque');
  return 'Abri Catálogo e preços / Vi NAV18-SEM-ESTOQUE / Cliquei Ver estoque / Resultado: produto acessível sem saldo físico';
 });
 await record('3 / fatura → obrigação → câmbio → formulário de pagamento → retorno',async()=>{
  await area('Compras','Faturas');await page.locator('main a[href="/invoices/2"]').first().click();await expect(page.getByTestId('invoice-detail')).toBeVisible();
  await page.getByRole('link',{name:'Contas desta fatura'}).click();await settle();expect(new URL(page.url()).searchParams.get('invoice_id')).toBe('2');
  const row=page.locator('[data-testid^="ap-row-"]').first();await row.click();
  await page.getByRole('link',{name:'Câmbio da obrigação',exact:true}).click();await expect(page.getByTestId('payable-fx-panel')).toBeVisible();await shot('invoice-fx');
  await page.getByRole('link',{name:'Voltar à fila',exact:true}).click();await settle();expect(new URL(page.url()).searchParams.get('invoice_id')).toBe('2');
  if(!await page.getByTestId('detail-drawer').isVisible())await page.locator('[data-testid^="ap-row-"]').first().click();
  await page.getByTestId('ap-g02-new-payment').click();await settle();expect(new URL(page.url()).pathname).toBe('/payments/new');expect(new URL(page.url()).searchParams.get('payable_id')).toBeTruthy();
  await page.getByRole('link',{name:/Voltar|Cancelar/}).last().click();await settle();
  return 'Contas filtradas pela fatura; câmbio existente; formulário com obrigação/moeda/valor; retorno preservado, sem registrar pagamento';
 });
 await record('4 / pagamento com crédito em aberto e detalhe',async()=>{
  await page.keyboard.press('Escape');await area('Financeiro','Pagamentos realizados');await page.getByTestId('payments-residual-only').click();await settle();
  const link=page.locator('[data-testid^="payment-open-"]').first();await expect(link).toBeVisible();const href=await link.getAttribute('href');await link.click();await settle();
  await expect(page.locator('main')).toContainText(/Aberto|Não alocado|Disponível/i);await shot('payment-credit');
  await page.getByRole('link',{name:'Voltar à fila',exact:true}).click();await settle();expect(new URL(page.url()).searchParams.get('unallocated_only')).toBe('1');
  return {opened:'Financeiro → Pagamentos realizados',clicked:'Somente crédito em aberto → Abrir → Voltar à fila',payment:href,result:'Crédito e filtro de retorno mantidos'};
 });
 await record('5 / chegada, liberação e entrada física são etapas distintas',async()=>{
  await area('Importações','Embarques');await page.getByRole('button',{name:'Chegou',exact:true}).click();await settle();await page.locator('a[href="/shipments/2"]').first().click();await settle();
  await expect(page.locator('main')).toContainText('Chegou');
  await area('Importações','Operações');await page.locator('a[href="/customs/2"]').first().click();await settle();await expect(page.locator('main')).toContainText('Liberado');
  await page.getByRole('link',{name:'Receber mercadorias',exact:true}).last().click();await settle();await expect(page.getByTestId('receiving-page')).toContainText('Recebido');
  await shot('import-receiving-context');
  return 'Abri Embarques / Vi Chegou / Cliquei Operações → processo → Receber mercadorias / Resultado: fila da operação mostra liberado, recebido e pendente separadamente';
 });
 await record('7 / documento de transporte ou importação pela entrada transversal',async()=>{
  await area('Conferir documentos');
  const queue=await(await page.request.get('/api/ingestion/staging/queue')).json();
  const doc=queue.find(x=>/PACKING|DOGANALE|NUMERARIO|PRINT|DECLARATION/.test(x.doc_type));
  if(!doc)throw new Error('No existing transport/import document in staging queue; prepare a minimal synthetic test document before completing');
  await page.getByTestId('ingestion-row-'+doc.id).click();await settle();expect(new URL(page.url()).pathname).toBe('/ingestion/'+doc.id);
  await expect(page.locator('main')).toContainText(/Confer|Documento|Preview|Revisão/i);await shot('transversal-document');
  await page.goBack();await settle();expect(new URL(page.url()).pathname).toBe('/ingestion');
  return {opened:'Conferir documentos',document:doc.id,type:doc.doc_type,clicked:'Linha do documento → revisão → voltar',result:'Fila transversal e workspace acessíveis; nenhuma gravação do documento'};
 });
 await record('9 / indicador vencido conserva período, moeda e conjunto',async()=>{
  await area('Visão geral');await page.goto('/dashboard?view=executiva&period=custom&date_from=2020-01-01&date_to=2026-11-18&currency=EUR');await settle();
  const card=page.getByTestId('dash-widget-ap.overdue');await expect(card).toBeVisible();
  const expected=await(await page.request.get('/api/reporting/dashboard?view=executiva&period=custom&date_from=2020-01-01&date_to=2026-11-18&currency=EUR')).json();
  const metric=expected.widgets.find(w=>w.widget_id==='ap.overdue');
  await card.getByRole('link').click();await settle();const p=new URL(page.url()).searchParams;
  expect(p.get('pending')).toBe('OVERDUE');expect(p.get('currency')).toBe('EUR');expect(p.get('due_after')).toBe('2020-01-01');expect(p.get('due_before')).toBe('2026-11-18');
  const response=await page.request.get('/api/reporting/ap-queue?'+p);expect(response.ok()).toBeTruthy();const queue=await response.json();
  await shot('dashboard-filtered-ap');
  return {opened:'Visão geral / vencidos no recorte EUR',clicked:'Abrir fila de vencidas',result:'Período/moeda/situação preservados',metric:metric.display,queueTotal:queue.total,kpis:queue.kpis};
 });
 await record('6 / estoque recebe parcialmente e consulta saldo/histórico',async()=>{
  await login('estoque');await area('Importações');await expect(page.getByRole('heading',{name:'Receber mercadorias',exact:true})).toBeVisible();
  await page.getByLabel('Buscar recebimento').fill('NAV18');await expect(page.locator('#receive-open-'+fixture['nat-items'].items[0].id)).toBeVisible();await page.locator('#receive-open-'+fixture['nat-items'].items[0].id).click();
  const remaining=await page.getByTestId('receiving-pending').innerText();if(remaining==='10 UN'){await page.getByLabel('Quantidade (UN)').fill('4');await page.getByRole('button',{name:'Conferir recebimento',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Conferir recebimento',exact:true})).toBeFocused();await page.getByRole('button',{name:'Confirmar recebimento',exact:true}).click();
  await expect(page.getByTestId('receiving-pending')).toHaveText('6 UN');await expect(page.locator('#receipt-result')).toContainText('confirmado');}else{expect(remaining).toBe('6 UN');}await shot('partial-receiving');
  if(await page.getByRole('link',{name:'Ver saldo',exact:true}).count()){await page.getByRole('link',{name:'Ver saldo',exact:true}).click();}else{await area('Produtos');await page.getByPlaceholder('Nome ou código do produto (SKU)').fill('NAV18-RECEBIMENTO');await page.locator('#stock-product-'+fixture.product.id).click();}await settle();await expect(page.locator('main')).toContainText('4');await area('Importações');await page.getByLabel('Buscar recebimento').fill('NAV18-RECEBIMENTO');await page.locator('#receive-open-'+fixture['nat-items'].items[0].id).click();await page.reload();await settle();await expect(page.getByTestId('receiving-pending')).toHaveText('6 UN');
  await area('Produtos','Histórico de estoque');await page.getByTestId('movements-product-filter').fill('NAV18-RECEBIMENTO');await page.getByTestId('movements-filter-apply').click();await settle();await expect(page.locator('main')).toContainText('NAV18-RECEBIMENTO');
  const read=await(await page.request.get('/api/inventory/receiving?state=all&item_id='+fixture['nat-items'].items[0].id)).json();expect(Number(read.rows[0].received_qty)).toBe(4);expect(Number(read.rows[0].pending_qty)).toBe(6);
  return 'Abri Importações como Estoque / Vi 10 liberadas / Confirmei 4 fictícias / Resultado: saldo 4, pendente 6, recarga e histórico coerentes';
 });
 await record('8 / cadastro autorizado sem acesso a Pedidos',async()=>{
  await login('nav_catalog');await area('Compras');expect(new URL(page.url()).pathname).toBe('/catalog/suppliers');
  await page.getByRole('link',{name:/Novo fornecedor/}).click();await page.getByTestId('supplier-name').fill('NAV18 Cadastro pela UI validado');await page.getByTestId('supplier-code').fill('NAV18-UI-2');await page.getByTestId('supplier-country').fill('BR');await page.getByTestId('supplier-create-submit').click();
  await expect(page.getByTestId('supplier-detail-page')).toBeVisible();await expect(page.getByRole('heading',{name:'NAV18 Cadastro pela UI validado',exact:true})).toBeVisible();await shot('catalog-only-supplier');
  await page.getByRole('link',{name:/Voltar/}).click();await settle();expect(new URL(page.url()).pathname).toBe('/catalog/suppliers');
  await page.goto('/orders');await settle();await expect(page.locator('main')).toContainText(/403|permissão|forbidden|Erro/i);
  return 'Abri Compras → Fornecedores por fallback / Cadastrei NAV18-UI / Voltei à lista / URL de Pedidos continua negada';
 });
 await record('FX exclusivo / acesso permitido sem consulta de Billing',async()=>{
  await login('nav_fx');const requests=[];page.on('request',r=>{if(r.url().includes('/api/'))requests.push(r.url());});
  await area('Financeiro');await page.getByLabel('Número da obrigação').fill('2');await page.getByRole('button',{name:'Abrir câmbio',exact:true}).click();await expect(page.getByTestId('payable-fx-panel')).toBeVisible();
  expect(requests.some(url=>/\/api\/payables(?:\?|\/2$)/.test(url))).toBe(false);await expect(page.getByTestId('fx-plan-form')).toHaveCount(0);await shot('fx-only');
  await page.getByRole('link',{name:'Voltar à fila',exact:true}).click();await expect(page.getByLabel('Número da obrigação')).toBeVisible();
  return 'Financeiro → número da obrigação → câmbio existente; sem listagem de contas, sem escrita e sem novas permissões';
 });
}finally{await browser.close();writeFileSync(resolve(out,'journeys.json'),JSON.stringify({results,errors,mutations},null,2));console.log(JSON.stringify({passed:results.filter(r=>r.result==='PASS').length,failed:results.filter(r=>r.result==='FAIL').length,mutations:mutations.length,errors}));}
