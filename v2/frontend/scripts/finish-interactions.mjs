import{chromium,expect}from'@playwright/test';import{readFileSync,writeFileSync}from'node:fs';import{resolve}from'node:path';
const out=resolve('../../docs/v2/etapa-acabamento-financeiro-20261119'),fixtures=JSON.parse(readFileSync(out+'/long-text-fixtures.json','utf8'));
const b=await chromium.launch(),result={runtime:'8104 / 5461',build:'executive-20261119.1',actions:[],profiles:[],longText:[],flows:[],errors:[],writes:[]};
const save=()=>writeFileSync(out+'/interaction-results.json',JSON.stringify(result,null,2));
async function session(role='admin'){
 const c=await b.newContext({baseURL:'http://127.0.0.1:8104',viewport:{width:1366,height:768},locale:'pt-BR',permissions:['clipboard-read','clipboard-write']}),p=await c.newPage();p.setDefaultTimeout(10000);p.on('pageerror',e=>result.errors.push(String(e)));p.on('request',r=>{if(r.method()!=='GET'&&!r.url().includes('/auth/')&&!r.url().includes('/fx/quotes/refresh'))result.writes.push(r.method()+' '+r.url());});
 await p.goto('/login');if(role==='admin')await p.getByTestId('login-dev-shortcut').click();else{await p.getByLabel('E-mail').fill(role+'@epic.com.br');await p.getByLabel('Senha',{exact:true}).fill('ensaio123');await p.getByRole('button',{name:'Entrar',exact:true}).click();}await expect(p.locator('.shell-side-nav')).toBeVisible();return{p,c};
}
async function frames(p){await p.evaluate(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(r))));});}
async function ready(p){await p.waitForLoadState('networkidle');await frames(p);}
async function sidebar(p,expanded){const collapsed=await p.locator('.experience-collapsed').count();if(expanded&&collapsed)await p.getByRole('button',{name:'Expandir navegação'}).click();if(!expanded&&!collapsed)await p.getByRole('button',{name:'Recolher navegação'}).click();await frames(p);}
async function header(p){return p.getByTestId('record-work-header').evaluate(e=>{
 const widths=[...e.querySelectorAll('[data-action-measure]')].map(x=>x.getBoundingClientRect().width),trigger=e.querySelector('.record-trigger-measure').getBoundingClientRect().width,id=e.querySelector('.record-identity').getBoundingClientRect(),stacked=e.classList.contains('actions-stacked'),available=e.clientWidth-(stacked?0:id.width+16),visible=[...e.querySelectorAll('.record-actions>.record-action [data-record-action]')],menu=[...e.querySelectorAll('.record-more-list [data-record-action]')];
 const total=widths.reduce((a,b)=>a+b,0)+Math.max(0,widths.length-1)*8;let expected=total<=available-2?widths.length:e.querySelector('[data-record-primary]')?1:0;
 if(expected<widths.length)for(let n=expected+1;n<widths.length;n++){if(widths.slice(0,n).reduce((a,b)=>a+b,0)+n*8+trigger>available-2)break;expected=n;}
 return{width:e.clientWidth,available,stacked,visible:visible.map(x=>x.textContent),menu:menu.map(x=>x.textContent),expected,measurementError:Math.max(0,...visible.map((x,i)=>Math.abs(x.getBoundingClientRect().width-widths[i]))),focus:document.activeElement?.getAttribute('data-record-action'),overflow:document.documentElement.scrollWidth-innerWidth};
 });}
const {p,c}=await session();
try{
 await p.setViewportSize({width:1920,height:900});await p.goto('/orders/2/commercial');await ready(p);
 let lastCount=null,transitions=[];
 for(let width=1920;width>=900;width-=8){await p.setViewportSize({width,height:900});await frames(p);const m=await header(p);expect(m.overflow).toBe(0);expect(m.visible.length).toBe(m.expected);expect(m.measurementError).toBeLessThanOrEqual(1);if(m.visible.length!==lastCount){transitions.push({viewport:width,...m});lastCount=m.visible.length;}}
 // Repeat both sides of each observed transition at 1px steps and settle twice.
 for(const transition of transitions.slice(1))for(let width=transition.viewport-3;width<=transition.viewport+9;width++){
  await p.setViewportSize({width,height:900});await frames(p);const a=await header(p);await frames(p);const z=await header(p);expect(z.visible).toEqual(a.visible);expect(z.visible.length).toBe(z.expected);expect(z.overflow).toBe(0);
 }
 result.actions.push({task:'Redimensionamento lento e limiares',steps:128,transitionSweeps:transitions.length-1,transitions,result:'Prefixo máximo estável, erro entre medidas/controles <=1 px; menu conforme largura útil'});save();
 await p.setViewportSize({width:1366,height:768});await p.goto('/orders/2/commercial');await ready(p);await p.locator('.record-more summary').focus();await p.keyboard.press('Enter');await expect(p.locator('.record-more')).toHaveAttribute('open','');await p.keyboard.press('Tab');
 const focused=await p.evaluate(()=>{document.activeElement.__finishIdentity='retained';return document.activeElement.getAttribute('data-record-action');});expect(focused).toBeTruthy();
 for(const width of [1100,1920,1250]){await p.setViewportSize({width,height:900});await frames(p);expect(await p.evaluate(()=>document.activeElement.__finishIdentity)).toBe('retained');expect(await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBe(0);await expect(p.locator('.record-more')).toHaveAttribute('open','');}
 await p.screenshot({path:out+'/verified/menu-open-resize.png'});await p.keyboard.press('Escape');await expect(p.locator('.record-more summary')).toBeFocused();await expect(p.locator('.record-more')).not.toHaveAttribute('open','');await p.keyboard.press('Tab');await frames(p);expect((await header(p)).visible.length).toBe((await header(p)).expected);
 result.actions.push({task:'Menu aberto e foco em ação',focused,result:'Mesma instância durante redução/ampliação; Escape retorna ao gatilho; redistribuição ao sair do grupo'});
 await p.setViewportSize({width:1920,height:900});await p.locator('.record-title h1').click();await p.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));await frames(p);await expect(p.locator('.record-more')).toHaveCount(0);const refresh=p.getByTestId('record-work-header').getByRole('button',{name:'Atualizar',exact:true});await refresh.focus();await refresh.evaluate(e=>e.__finishIdentity='pointer');const box=await refresh.boundingBox();await p.mouse.move(box.x+box.width/2,box.y+box.height/2);await p.mouse.down();await p.setViewportSize({width:1060,height:768});await frames(p);expect(await refresh.evaluate(e=>e.__finishIdentity)).toBe('pointer');await p.mouse.up();expect(await refresh.evaluate(e=>e.__finishIdentity)).toBe('pointer');await p.locator('.record-title h1').click();await frames(p);expect((await header(p)).visible.length).toBe((await header(p)).expected);
 result.actions.push({task:'Ação focada/ponteiro pressionado',result:'Controle mantido durante ativação, sem transação pela redistribuição'});save();
 // Three references: same prefix/suffix with middle differences, plus tail-only difference.
 await p.setViewportSize({width:1366,height:768});await sidebar(p,true);await p.goto(`/payables?pending=ALL&supplier_id=${fixtures.supplier.id}`);await ready(p);const rows=p.getByTestId('ap-table').locator('tbody tr');await expect(rows).toHaveCount(6);
 for(let i=0;i<3;i++){
  const ref=fixtures[`issued${i}`].invoice_number;await p.getByRole('button',{name:`Ver referência completa: Fatura ${fixtures[`issued${i}`].id}`,exact:true}).first().click();const drawer=p.getByRole('dialog');await expect(drawer).toBeVisible();await expect(drawer.locator('.ap-full-text>span').filter({hasText:ref}).first()).toBeVisible();const copy=drawer.locator('.ap-full-text').filter({hasText:ref}).first().getByRole('button',{name:'Copiar',exact:true});await copy.click();expect(await p.evaluate(()=>navigator.clipboard.readText())).toBe(ref);await p.keyboard.press('Escape');
  result.longText.push({reference:ref,invoice:fixtures[`issued${i}`].id,abri:'Contas filtradas FIN19',vi:'Abreviação explícita e número distinto',cliquei:'Referência completa e Copiar',resultado:'Texto integral consultado/copied sem alteração dos dados'});
 }
 await rows.first().locator('[data-column-id="supplier"] button').click();await expect(p.getByRole('dialog')).toContainText(fixtures.supplier.name);await p.screenshot({path:out+'/verified/full-reference-drawer.png'});await p.keyboard.press('Escape');await p.screenshot({path:out+'/verified/long-references.png'});expect(await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBe(0);
 // Long identity in the same production consumer; inspect both header states.
 await p.goto(`/orders/${fixtures.oc0.id}/commercial`);await ready(p);for(const compact of [false,true]){await p.evaluate(v=>window.scrollTo(0,v?document.documentElement.scrollHeight:0),compact);await frames(p);const m=await header(p);expect(m.overflow).toBe(0);expect(m.visible.length).toBe(m.expected);result.actions.push({task:'Identificação longa',compact,...m});await p.screenshot({path:out+`/verified/long-header-${compact}.png`});}
 save();
}catch(error){result.failure=String(error);await p.screenshot({path:out+'/verified/interactions-failure.png'});save();throw error;}finally{await c.close();}
try{
 for(const [role,routes] of [['det_order_read',['/orders/2','/orders/2/commercial','/payables']],['det_customs_read',['/customs/12']]]){
  const {p,c}=await session(role);
  try{for(const width of [1366,1440])for(const expanded of [true,false]){
   await p.setViewportSize({width,height:width===1366?768:900});await sidebar(p,expanded);
   for(const route of routes){await p.goto(route);await ready(p);if(route==='/payables'){await expect(p.getByTestId('ap-table')).toBeVisible();result.profiles.push({role,route,width,expanded,result:'Fila em leitura acessível'});continue;}
    for(const compact of [false,true]){await p.evaluate(v=>window.scrollTo(0,v?document.documentElement.scrollHeight:0),compact);await frames(p);const m=await header(p);expect(m.overflow).toBe(0);expect(m.visible.length).toBe(m.expected);expect([...m.visible,...m.menu].join('|')).not.toMatch(/Encerrar|Reabrir|Cancelar|Confirmar|Faturar|Receber mercadorias/);result.profiles.push({role,route,width,expanded,compact,...m});}
   }
  }await p.screenshot({path:out+`/verified/readonly-${role}.png`});}finally{await c.close();save();}
 }
 expect(result.errors).toHaveLength(0);expect(result.writes).toHaveLength(0);
}finally{save();await b.close();}
console.log(JSON.stringify({actions:result.actions.length,profiles:result.profiles.length,longText:result.longText.length,errors:result.errors,writes:result.writes}));
