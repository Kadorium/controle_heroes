/**
 * Papéis operacionais no E2E (epic_v2_test). Não seed em epic_v2.
 */
import { test, expect } from "@playwright/test";
import { loginAs } from "./helpers/orderCreate";

const PASSWORD = "ensaio123";

test.describe("RBAC roles (test-only users)", () => {
  test("comprador vê Pedidos e não vê Usuários", async ({ page }) => {
    await loginAs(page, "comprador@epic.com.br", PASSWORD);
    const nav = page.getByRole("navigation", { name: /módulos/i });
    await expect(nav.getByRole("link", { name: "Pedidos" })).toBeVisible({ timeout: 15_000 });
    await expect(nav.getByRole("link", { name: "Usuários" })).toHaveCount(0);
  });

  test("aduana vê Processos; não vê Estoque nem publicar custo", async ({ page }) => {
    await loginAs(page, "aduana@epic.com.br", PASSWORD);
    const nav = page.getByRole("navigation", { name: /módulos/i });
    await expect(nav.getByRole("link", { name: "Processos" })).toBeVisible({ timeout: 15_000 });
    await expect(nav.getByRole("link", { name: "Estoque" })).toHaveCount(0);
    await page.goto("/costing");
    await expect(page.getByTestId("costing-publish")).toHaveCount(0);
    await expect(page.getByTestId("costing-publish-partial")).toHaveCount(0);
  });

  test("estoque vê Estoque e não vê Pedidos", async ({ page }) => {
    await loginAs(page, "estoque@epic.com.br", PASSWORD);
    const nav = page.getByRole("navigation", { name: /módulos/i });
    await expect(nav.getByRole("link", { name: "Estoque" })).toBeVisible({ timeout: 15_000 });
    await expect(nav.getByRole("link", { name: "Pedidos" })).toHaveCount(0);
  });
});
