import {chromium,expect} from '@playwright/test';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';import{resolve}from'node:path';import{createHash}from'node:crypto';
const out=resolve('../../docs/v2/etapa-acabamento-financeiro-20261119'),base=process.env.FINISH_BASE||'http://127.0.0.1:8104';mkdirSync(out+'/verified',{recursive:true});
const browser=await chromium.launch(),results={base,build:'executive-20261119.1',ap:[],headers:[],journeys:[],transitions:[],errors:[],writes:[]};
const evidenceFile=base.includes('8082')?'release-ui.json':'ui-measurements.json';
const save=()=>writeFileSync(out+'/'+evidenceFile,JSON.stringify(results,null,2));
async function session(role='admin'){
 const context=await browser.newContext({baseURL:base,viewport:{width:1366,height:768},locale:'pt-BR',permissions:['clipboard-read','clipboard-write']});const p=await context.newPage();p.setDefaultTimeout(10000);
 p.on('pageerror',e=>results.errors.push(String(e)));p.on('request',r=>{if(r.method()!=='GET'&&!r.url().includes('/auth/')&&!r.url().includes('/fx/quotes/refresh'))results.writes.push(r.method()+' '+r.url());});
 await p.goto('/login');if(role==='admin')await p.getByTestId('login-dev-shortcut').click();else{await p.getByLabel('E-mail').fill(role+'@epic.com.br');await p.getByLabel('Senha',{exact:true}).fill('ensaio123');await p.getByRole('button',{name:'Entrar',exact:true}).click();}
 await expect(p.locator('.shell-side-nav')).toBeVisible();return{p,context};
}
async function settle(p){await p.waitForLoadState('networkidle');await p.evaluate(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});}
async function rail(p,expanded){const collapsed=await p.locator('.experience-collapsed').count();if(expanded&&collapsed)await p.getByRole('button',{name:'Expandir navegação'}).click();if(!expanded&&!collapsed)await p.getByRole('button',{name:'Recolher navegação'}).click();await settle(p);}
async function apMetrics(p){return p.evaluate(()=>{
 const table=document.querySelector('[data-testid="ap-table"]'),wrap=table.parentElement,rows=[...table.querySelectorAll('tbody tr')];
 const rect=e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom};};
 const textRect=e=>{const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n;while(n=walker.nextNode())if(n.textContent.trim()){const r=document.createRange();r.selectNodeContents(n);return rect(r);}return rect(e);};
 const axes=[...table.querySelectorAll('th')].map((th,i)=>{
  const td=rows[0].children[i],id=th.dataset.columnId,h=textRect(th);let value;
  if(id==='status'){const b=rect(td.querySelector('.status-badge'));value=b.x+b.w/2-(h.x+h.w/2);}
  else if(th.classList.contains('num'))value=textRect(td).right-h.right;
  else value=(td.querySelector('.ap-name')?rect(td.querySelector('.ap-name')).x:textRect(td).x)-h.x;
  return{id,delta:value};
 });
 const controls=[...document.querySelectorAll('.filter-bar-primary input,.filter-bar-primary select')].map(rect),more=rect(document.querySelector('[data-testid="filter-bar-more-trigger"]'));
 const badges=[...table.querySelectorAll('.status-badge')].map(e=>({text:e.textContent,...rect(e),nowrap:getComputedStyle(e).whiteSpace}));
 const monetary=[...table.querySelectorAll('.money')].map(e=>({text:e.textContent,nowrap:getComputedStyle(e).whiteSpace,fits:e.getBoundingClientRect().width<=e.closest('td').clientWidth-23}));
 const summaryRows=[...document.querySelectorAll('.ap-summary-row')].map(e=>({currency:e.querySelector('strong').textContent,values:[...e.querySelectorAll('button')].map(b=>({text:b.textContent,right:rect(b).right-parseFloat(getComputedStyle(b).paddingRight),nowrap:getComputedStyle(b).whiteSpace}))}));
 return{table:rect(table),tableWidth:table.scrollWidth,viewport:innerWidth,wrapWidth:wrap.clientWidth,pageOverflow:document.documentElement.scrollWidth-innerWidth,columns:[...table.querySelectorAll('th')].map(e=>e.dataset.columnId),rowHeights:rows.map(e=>rect(e).h),visibleRows:rows.filter(e=>rect(e).y>=0&&rect(e).bottom<=innerHeight).length,axes,filterDelta:more.y+more.h/2-(controls[0].y+controls[0].h/2),badges,monetary,summaryRows,summaryOverflow:document.querySelector('.ap-summary').scrollWidth-document.querySelector('.ap-summary').clientWidth};
 });}
async function headerMetrics(p){return p.getByTestId('record-work-header').evaluate(e=>{
 const visible=[...e.querySelectorAll('.record-actions>.record-action [data-record-action]')],hidden=[...e.querySelectorAll('.record-more-list [data-record-action]')],identity=e.querySelector('.record-identity').getBoundingClientRect(),bar=e.querySelector('.record-actions').getBoundingClientRect();
 const widths=[...e.querySelectorAll('[data-action-measure]')].map(x=>x.getBoundingClientRect().width),trigger=e.querySelector('.record-trigger-measure').getBoundingClientRect().width,available=e.clientWidth-(e.classList.contains('actions-stacked')?0:identity.width+16);
 const total=widths.reduce((a,b)=>a+b,0)+Math.max(0,widths.length-1)*8;
 let expected=total<=available-2?widths.length:e.querySelector('[data-record-primary]')?1:0;
 if(expected<widths.length)for(let n=expected+1;n<widths.length;n++){if(widths.slice(0,n).reduce((a,b)=>a+b,0)+n*8+trigger>available-2)break;expected=n;}
 return{width:e.clientWidth,identity:identity.width,available,widths,trigger,expected,visible:visible.map(x=>x.textContent),menu:hidden.map(x=>x.textContent),keys:[...visible,...hidden].map(x=>x.dataset.recordAction),hasMenu:!!e.querySelector('details'),primaryVisible:!e.querySelector('[data-record-primary]')||visible.includes(e.querySelector('[data-record-primary]')),collision:identity.right>bar.left+1&&identity.top<bar.bottom&&bar.top<identity.bottom,compact:e.classList.contains('is-compact'),stacked:e.classList.contains('actions-stacked'),pageOverflow:document.documentElement.scrollWidth-innerWidth};
 });}
function checkHeader(m){expect(m.visible.length).toBe(m.expected);expect(m.hasMenu).toBe(m.menu.length>0);expect(new Set(m.keys).size).toBe(m.keys.length);expect(m.primaryVisible).toBe(true);expect(m.collision).toBe(false);expect(m.pageOverflow).toBe(0);}
const {p,context}=await session();
try{
 const html=await(await p.request.get('/')).text();expect(html).toBe(readFileSync('dist-finish/index.html','utf8'));results.indexSha256=createHash('sha256').update(html).digest('hex');
 for(const width of [1366,1440])for(const expanded of [true,false]){
  await p.setViewportSize({width,height:width===1366?768:900});await rail(p,expanded);await p.goto('/payables');await settle(p);const m=await apMetrics(p);results.ap.push({width,expanded,...m});save();
  expect(m.pageOverflow).toBe(0);expect(m.columns).toHaveLength(11);expect(m.visibleRows).toBeGreaterThanOrEqual(6);expect(Math.max(...m.rowHeights)-Math.min(...m.rowHeights)).toBeLessThanOrEqual(2);expect(Math.abs(m.filterDelta)).toBeLessThanOrEqual(2);expect(m.axes.every(a=>Math.abs(a.delta)<=2)).toBe(true);expect(new Set(m.badges.map(b=>b.h)).size).toBe(1);expect(m.badges.every(b=>b.nowrap==='nowrap')).toBe(true);expect(m.monetary.every(x=>x.fits&&x.nowrap==='nowrap')).toBe(true);
  await p.screenshot({path:out+`/verified/ap-${width}-${expanded}.png`});const scroll=p.getByRole('region',{name:/Contas a pagar: todas/});await scroll.focus();await p.keyboard.press('End');await p.getByRole('button',{name:'Próximas colunas'}).click();await p.getByRole('button',{name:'Próximas colunas'}).click();await expect.poll(()=>scroll.evaluate(e=>e.scrollLeft)).toBeGreaterThan(400);await scroll.evaluate(e=>e.scrollLeft=e.scrollWidth);await p.screenshot({path:out+`/verified/ap-right-${width}-${expanded}.png`});await expect(p.getByTestId('ap-table').locator('th').last()).toBeInViewport();
  for(const route of ['/orders/2','/orders/2/commercial','/customs/12']){
   const actual=base.includes('8082')?route.replace('/customs/12','/customs/2'):route;await p.goto(actual);await settle(p);
   for(const compact of [false,true]){await p.evaluate(bottom=>window.scrollTo(0,bottom?document.documentElement.scrollHeight:0),compact);await settle(p);const m=await headerMetrics(p);results.headers.push({route:actual,viewportWidth:width,width,expanded,position:compact?'compact':'top',profile:'admin',...m});save();checkHeader(m);await p.screenshot({path:out+`/verified/header-${actual.replaceAll('/','-')}-${width}-${expanded}-${compact}.png`});}
  }
 }
 // Open the existing forms/dialogs; no business confirmation.
 await p.goto('/orders/2/commercial');await settle(p);let close=p.getByRole('button',{name:'Encerrar pedido',exact:true});if(!await close.isVisible())await p.locator('.record-more summary').click();await close.click();await expect(p.getByRole('dialog')).toBeVisible();await p.keyboard.press('Escape');results.journeys.push({abri:'Pedido comercial',vi:'Encerrar pedido autorizado',cliquei:'Abri e fechei confirmação',resultado:'Handler/diálogo preservado; nenhuma confirmação'});
 await p.goto('/payables');await settle(p);await p.getByTestId('filter-bar-more-trigger').click();await expect(p.getByTestId('filter-bar-more-panel')).toBeVisible();await p.keyboard.press('Escape');await p.getByTestId('ap-filter-currency').fill('EUR');await settle(p);expect(new URL(p.url()).searchParams.get('currency')).toBe('EUR');await p.reload();await settle(p);expect(await p.getByTestId('ap-filter-currency').inputValue()).toBe('EUR');await p.getByTestId('filter-bar-clear-all').click();await settle(p);results.journeys.push({abri:'Contas a pagar',vi:'Filtros disponíveis',cliquei:'Mais filtros, Escape, EUR, recarga, limpar',resultado:'Query preservada e filtros operantes'});
 // All additional operational-table consumers: same shared implementation, opt-in label only.
 for(const route of ['/orders','/invoices','/payments','/customs','/inventory/receiving']){await p.goto(route);await settle(p);expect(await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBe(0);await p.screenshot({path:out+'/verified/consumer-'+route.replaceAll('/','-')+'.png'});results.journeys.push({abri:route,vi:'Fila real e navegação local',cliquei:'Abri pelo destino',resultado:'Sem overflow de página; conteúdo preservado'});}
 save();
}catch(error){results.failure=String(error);await p.screenshot({path:out+'/verified/failure.png'});save();throw error;}finally{await context.close();await browser.close();}
console.log(JSON.stringify({ap:results.ap.length,headers:results.headers.length,journeys:results.journeys.length,errors:results.errors,writes:results.writes}));
