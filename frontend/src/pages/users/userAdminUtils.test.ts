import { describe, expect, it } from "vitest";
import { canCancelUser, roleLabel, statusLabel } from "./userAdminUtils";
import type { AdminUser } from "../../api";

const sample: AdminUser = {
  id: 1,
  email: "a@epic.com.br",
  name: "Admin",
  role: "admin",
  permissions: [],
  last_login: null,
  is_active: true,
};

describe("userAdminUtils", () => {
  it("roleLabel traduz papéis conhecidos", () => {
    expect(roleLabel("operador")).toBe("Operador");
    expect(roleLabel("unknown")).toBe("unknown");
  });

  it("canCancelUser bloqueia self e anulados", () => {
    expect(canCancelUser(sample, 1)).toBe(false);
    expect(canCancelUser(sample, 2)).toBe(true);
    expect(canCancelUser({ ...sample, is_active: false }, 2)).toBe(false);
  });

  it("statusLabel trata is_active ausente como ativo", () => {
    expect(statusLabel({ ...sample, is_active: undefined as unknown as boolean })).toBe("Ativo");
    expect(statusLabel({ ...sample, is_active: false })).toBe("Anulado");
  });
});
