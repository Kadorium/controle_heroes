import { chromium, expect } from '@playwright/test';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
const baseURL=process.env.NAV_URL||'http://127.0.0.1:8102';
const out=resolve('../../docs/v2/etapa-consolidacao-navegacao/'+(baseURL.endsWith(':8082')?'ui-release':'ui'));mkdirSync(out,{recursive:true});
const results=[],errors=[];
const browser=await chromium.launch();
let page,profile='admin';
const primary=()=>page.getByRole('navigation',{name:'Módulos',exact:true});
const settle=async()=>{await page.waitForLoadState('networkidle');};
async function record(name,fn){try{const detail=await fn();results.push({name,profile,runtime:baseURL,result:'PASS',url:page.url(),detail});console.log('PASS '+name);}catch(e){results.push({name,profile,runtime:baseURL,result:'FAIL',url:page?.url(),error:e.message});if(page)await page.screenshot({path:resolve(out,`failure-${results.length}.png`)});console.log('FAIL '+name+' '+e.message.slice(0,500));}finally{writeFileSync(resolve(out,'smoke.json'),JSON.stringify({results,errors},null,2));}}
async function login(role){
 profile=role;if(page)await page.context().close();
 const context=await browser.newContext({baseURL,viewport:{width:1366,height:768},locale:'pt-BR'});page=await context.newPage();
 page.on('pageerror',e=>errors.push({profile,message:e.message}));
 await page.goto('/login');
 if(role==='admin')await page.getByRole('button',{name:/acesso.*admin/i}).click();
 else{await page.getByLabel(/e-?mail/i).fill(role+'@epic.com.br');await page.getByLabel(/senha/i).fill('ensaio123');await page.getByRole('button',{name:/entrar/i}).click();}
 await expect(primary()).toBeVisible();await settle();
 const me=await(await page.request.get('/api/auth/me')).json();expect(me.role).toBe(role);return me;
}
const areas=[
 ['Produtos',[['Estoque atual','/inventory/positions'],['Catálogo e preços','/catalog/products'],['Histórico de estoque','/inventory/movements']]],
 ['Compras',[['Pedidos','/orders'],['Faturas','/invoices'],['Fornecedores','/catalog/suppliers']]],
 ['Importações',[['Operações','/customs'],['Embarques','/shipments'],['Receber mercadorias','/inventory/receiving'],['Custo desembarcado','/costing'],['Prestadores logísticos','/logistics-providers']]],
 ['Financeiro',[['Contas a pagar','/payables'],['Pagamentos realizados','/payments']]],
];
async function layout(){
 const failures=await page.locator('.consolidated-nav a,.area-navigation a').evaluateAll(xs=>xs.flatMap(x=>{const r=x.getBoundingClientRect();const label=x.querySelector('.nav-rail-caption')||x.querySelector('.shell-nav-label')||x;const style=getComputedStyle(label);const range=document.createRange();range.selectNodeContents(label);const lr=range.getBoundingClientRect();return r.width&&((r.right>innerWidth+1||r.left<0)||(style.display!=='none'&&lr.width>r.width+1))?[{text:x.textContent,rect:r.toJSON(),label:lr.toJSON()}]:[]}));
 expect(failures).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
}
try{
 await login('admin');
 const index=await page.request.get('/');const html=await index.text();
 const assets=[...html.matchAll(/(?:src|href)="(\/assets\/[^" ]+)"/g)].map(x=>x[1]);
 writeFileSync(resolve(out,'runtime.json'),JSON.stringify({baseURL,assets,health:await(await page.request.get('/api/health')).json()},null,2));
 for(const [width,height] of [[1366,768],[1440,900]])for(const collapsed of [false,true]){
  await page.setViewportSize({width,height});
  if((await page.getByTestId('shell-rail-toggle').getAttribute('aria-expanded'))===String(collapsed))await page.getByTestId('shell-rail-toggle').click();
  for(const [area,sections] of areas){
   await record(`${width}x${height} ${collapsed?'recolhida':'expandida'} / ${area}`,async()=>{
    await primary().getByRole('link',{name:area,exact:true}).click();await settle();
    for(const [label,path] of sections){
     const nav=page.getByRole('navigation',{name:'Área de '+area.toLocaleLowerCase('pt-BR'),exact:true});
     await nav.getByRole('link',{name:label,exact:true}).click();await settle();
     expect(new URL(page.url()).pathname).toBe(path);await expect(nav.getByRole('link',{name:label,exact:true})).toHaveAttribute('aria-current','page');
     await expect(primary().getByRole('link',{name:area,exact:true})).toHaveAttribute('aria-current','page');await layout();
     expect(await page.locator('.product-area-nav').count()).toBe(0);
    }
    if(area==='Importações'||area==='Produtos')await page.screenshot({path:resolve(out,`${width}-${collapsed?'rail':'expanded'}-${area==='Produtos'?'products':'imports'}.png`)});
    return {opened:area,clicked:sections.map(x=>x[0]),observed:'URLs e seleção corretas; sem sobreposição na navegação'};
   });
  }
 }
 for(const [label,path]of [['Visão geral','/dashboard'],['Conferir documentos','/ingestion'],['Usuários e acessos','/admin/users']])await record('Secundário / '+label,async()=>{await primary().getByRole('link',{name:label,exact:true}).focus();await page.keyboard.press('Enter');await settle();expect(new URL(page.url()).pathname).toBe(path);await layout();return 'Foco por teclado e Enter abriram '+path;});
 await record('Link antigo de câmbio / recarga / voltar / avançar',async()=>{
  await page.goto('/payables?purpose=fx&currency=EUR&pending=ALL');await settle();
  await expect(primary().getByRole('link',{name:'Financeiro',exact:true})).toHaveAttribute('aria-current','page');
  await page.reload();await settle();expect(new URL(page.url()).searchParams.get('purpose')).toBe('fx');
  await primary().getByRole('link',{name:'Compras',exact:true}).click();await settle();await page.goBack();await settle();expect(new URL(page.url()).searchParams.get('currency')).toBe('EUR');
  await page.goForward();await settle();expect(new URL(page.url()).pathname).toBe('/orders');
  return 'URL antiga, purpose/currency e histórico do navegador preservados';
 });
 const profiles=[
  ['comprador',['Visão geral','Produtos','Compras','Importações','Financeiro','Conferir documentos']],
  ['aduana',['Visão geral','Importações']],['estoque',['Visão geral','Produtos','Importações']],
  ['nav_catalog',['Produtos','Compras']],['nav_cost',['Importações']],['nav_stock',['Produtos','Importações']],
  ['nav_logistics',['Importações']],['nav_fx',['Financeiro']],['nav_payments',['Financeiro']],
 ];
 for(const [role,labels] of (baseURL.endsWith(':8082')?[]:profiles))await record('Perfil / '+role,async()=>{
  await login(role);expect(await primary().getByRole('link').allTextContents()).toEqual(labels);
  const paths=[];
  for(const label of labels){
   await primary().getByRole('link',{name:label,exact:true}).click();await settle();
   paths.push(new URL(page.url()).pathname+new URL(page.url()).search);
   const links=await page.locator('.area-navigation a').evaluateAll(xs=>xs.map(x=>({label:x.textContent,href:x.getAttribute('href')})));
   for(const section of links){await page.locator('.area-navigation').getByRole('link',{name:section.label,exact:true}).click();await settle();expect(new URL(page.url()).pathname).toBe(section.href.split('?')[0]);}
   await layout();
   expect(await page.locator('main').innerText()).not.toMatch(/Permissão insuficiente|Sem permissão|É preciso costing:read|Erro ao listar/);
  }
  if(role==='estoque'||role==='aduana')await page.screenshot({path:resolve(out,'profile-'+role+'.png')});
  return {visible:labels,entryPoints:paths,readOnlyFxLimitation:role==='nav_fx'?await page.locator('main').innerText():undefined};
 });
}finally{await browser.close();writeFileSync(resolve(out,'smoke.json'),JSON.stringify({results,errors},null,2));console.log(JSON.stringify({passed:results.filter(r=>r.result==='PASS').length,failed:results.filter(r=>r.result==='FAIL').length,errors}));}
