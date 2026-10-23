import {test,expect} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
const out=process.env.LAPTOP_EVIDENCE||resolve('../../../audit-lab/stock-executive-20261023/laptop/before');mkdirSync(out,{recursive:true});
const baseline=process.env.LAPTOP_BASELINE==='true';
for(const viewport of [{width:1366,height:681},{width:1366,height:768},{width:1920,height:1080},{width:1024,height:768}])test(`density and journey ${viewport.width}x${viewport.height}`,async({page})=>{
 await page.setViewportSize(viewport);await page.request.post('/api/auth/dev-login');const build=await(await page.request.get('/assets/build-info.json')).json();
 const result:any={viewport,build,executor:'Playwright',screens:{}};
 for(const [name,route,selector] of [['stock','/inventory/positions?modality_ids=bt&group_by=item_kind','.stock-result'],['ap','/payables','[data-testid="ap-table"]'],['dashboard','/dashboard?view=executiva','[data-testid="executive-stock"]']]){
  await page.goto(route);await expect(page.locator(selector)).toBeVisible();await expect(page.getByText('Consultando estoque…',{exact:true})).toHaveCount(0);await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>scrollTo(0,0));
  result.screens[name]=await page.locator(selector).evaluate(el=>({top:el.getBoundingClientRect().top,rows:[...el.querySelectorAll('tbody tr')].filter(r=>{const b=r.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight}).length,font:getComputedStyle(el).fontSize,zoom:visualViewport?.scale,overflow:document.documentElement.scrollWidth>innerWidth+1}));
  await page.screenshot({path:resolve(out,`${name}-${viewport.width}x${viewport.height}.png`)});
  if(!baseline&&viewport.width===1366&&viewport.height===681&&name!=='dashboard')expect(result.screens[name].rows).toBeGreaterThanOrEqual(5);
 }
 writeFileSync(resolve(out,`density-${viewport.width}x${viewport.height}.json`),JSON.stringify(result,null,2));
});
