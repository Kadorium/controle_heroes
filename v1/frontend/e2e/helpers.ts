import { expect, type Page } from "@playwright/test";

export const ADMIN = { email: "admin@epic.com.br", password: "admin123" };

export async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/e-mail|email/i).fill(ADMIN.email);
  await page.getByLabel(/senha|password/i).fill(ADMIN.password);
  await page.getByRole("button", { name: /entrar|login/i }).click();
  await expect(page).toHaveURL(/\/(\?.*)?$/, { timeout: 30000 });
}

export async function getDemoImportationId(
  page: Page,
  poNumber = "DEMO-04-3INV"
): Promise<number> {
  const impsRes = await page.request.get("/api/importations");
  expect(impsRes.ok()).toBeTruthy();
  const imps = await impsRes.json();
  const demo =
    imps.find((i: { po_number: string }) => i.po_number === poNumber) ??
    imps.find((i: { po_number: string }) => i.po_number.startsWith("DEMO-"));
  expect(demo?.id).toBeTruthy();
  return demo.id as number;
}
