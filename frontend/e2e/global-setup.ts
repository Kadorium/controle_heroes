import { chromium, type FullConfig } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";
import { ADMIN } from "./helpers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function globalSetup(_config: FullConfig) {
  const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8082";
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();

  await page.goto("/login");
  await page.getByLabel(/e-mail|email/i).fill(ADMIN.email);
  await page.getByLabel(/senha|password/i).fill(ADMIN.password);
  await page.getByRole("button", { name: /entrar|login/i }).click();
  await page.waitForURL(/\/(\?.*)?$/, { timeout: 30000 });

  // Gera fixture XLSX para E2E Heroes (Ordine 758 sintética)
  const { execSync } = await import("child_process");
  const root = path.join(__dirname, "..", "..");
  try {
    execSync(
      `${path.join(root, ".venv", "Scripts", "python.exe")} -c "from tests.fixtures.heroes_xlsx_builder import build_ordine_758_xlsx, build_ordine_759_xlsx; import pathlib; p=pathlib.Path('frontend/e2e/fixtures'); p.mkdir(parents=True, exist_ok=True); p.joinpath('ordine758.xlsx').write_bytes(build_ordine_758_xlsx()); p.joinpath('ordine759.xlsx').write_bytes(build_ordine_759_xlsx())"`,
      { cwd: root, stdio: "ignore" }
    );
  } catch {
    /* fixture opcional */
  }

  await context.storageState({ path: "e2e/.auth/admin.json" });
  await browser.close();
}

export default globalSetup;
