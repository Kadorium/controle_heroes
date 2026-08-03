import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  use: {
    // E2E Inc-5+: prefer PLAYWRIGHT_BASE_URL → servidor com epic_v2_test (nunca poluir epic_v2)
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8081",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
