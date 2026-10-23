import {test,expect} from '@playwright/test';
test('scale UI >500, multi-modal deduplication, sort and last page totals',async({page})=>{
 expect(new URL(test.info().project.use.baseURL!).port).toBe('8089');await page.request.post('/api/auth/dev-login');
 await page.goto('/inventory/positions?modality_ids=bt,padel&group_by=modality');await expect(page.locator('.stock-numbers')).toContainText('507 PCT');await expect(page.locator('tbody tr')).toHaveCount(25);const totals=await page.locator('.stock-numbers').innerText();
 await page.getByLabel('Ordenar',{exact:true}).selectOption('-quantity');await expect(page.locator('.stock-numbers')).toBeVisible();expect(await page.locator('.stock-numbers').innerText()).toBe(totals);
 await page.getByLabel('Por página').selectOption('100');await expect(page.locator('tbody tr')).toHaveCount(100);
 for(let i=0;i<5;i++){await page.getByRole('button',{name:'Próxima',exact:true}).click();await expect(page.locator('.stock-numbers')).toBeVisible();}
 await expect(page.locator('tbody tr')).toHaveCount(7);expect(await page.locator('.stock-numbers').innerText()).toBe(totals);await expect(page.locator('.stock-composition')).toContainText('507 produtos');
 await page.reload();await expect(page.locator('tbody tr')).toHaveCount(7);await expect(page.locator('.experience-footer')).toContainText('501–507 de 507');
});
