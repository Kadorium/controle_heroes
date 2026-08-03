import { test, expect } from "@playwright/test";

test("I9-1 login ?next= deep link interno", async ({ page, context }) => {
  await context.clearCookies();
  await page.goto("/payables");
  await expect(page).toHaveURL(/\/login\?next=/);
  await expect(page.getByTestId("login-page")).toBeVisible();

  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  await expect(page).toHaveURL(/\/payables/, { timeout: 15000 });
  await expect(page.getByRole("navigation", { name: /módulos/i })).toBeVisible();
});

test("I9-1 login rejeita next externo", async ({ page, context }) => {
  await context.clearCookies();
  await page.goto("/login?next=" + encodeURIComponent("https://evil.example/x"));
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page).toHaveURL(/\/orders$/, { timeout: 15000 });
});
