import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { shouldPrefillLoginCredentials } from "./LoginPage";

describe("shouldPrefillLoginCredentials", () => {
  const env = import.meta.env;

  beforeEach(() => {
    vi.stubEnv("MODE", "production");
    vi.stubEnv("VITE_LOGIN_PREFILL", undefined);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("não pré-preenche em production sem flag", () => {
    vi.stubEnv("MODE", "production");
    delete (env as { VITE_LOGIN_PREFILL?: string }).VITE_LOGIN_PREFILL;
    expect(shouldPrefillLoginCredentials()).toBe(false);
  });

  it("pré-preenche em development", () => {
    vi.stubEnv("MODE", "development");
    expect(shouldPrefillLoginCredentials()).toBe(true);
  });

  it("pré-preenche quando VITE_LOGIN_PREFILL=1", () => {
    vi.stubEnv("MODE", "production");
    vi.stubEnv("VITE_LOGIN_PREFILL", "1");
    expect(shouldPrefillLoginCredentials()).toBe(true);
  });

  it("respeita VITE_LOGIN_PREFILL=0 mesmo em development", () => {
    vi.stubEnv("MODE", "development");
    vi.stubEnv("VITE_LOGIN_PREFILL", "0");
    expect(shouldPrefillLoginCredentials()).toBe(false);
  });
});
