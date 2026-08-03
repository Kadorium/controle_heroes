import { describe, expect, it } from "vitest";
import {
  canClearCustoms,
  canReadCustoms,
  canWriteCustoms,
  conflictMessage,
  statusLabel,
} from "./customsPermissions";
import type { User } from "../auth/types";

const base: User = {
  id: 1,
  email: "a@b.c",
  name: "A",
  role: "comprador",
  permissions: ["customs:read"],
};

describe("customsPermissions", () => {
  it("read/write/clear gates", () => {
    expect(canReadCustoms(base)).toBe(true);
    expect(canWriteCustoms(base)).toBe(false);
    expect(canClearCustoms(base)).toBe(false);
    expect(canWriteCustoms({ ...base, role: "admin", permissions: [] })).toBe(true);
    expect(canClearCustoms({ ...base, role: "admin", permissions: [] })).toBe(true);
    expect(
      canWriteCustoms({ ...base, role: "aduana", permissions: ["customs:read", "customs:write"] }),
    ).toBe(true);
    expect(
      canClearCustoms({
        ...base,
        role: "aduana",
        permissions: ["customs:read", "customs:write", "customs:clear"],
      }),
    ).toBe(true);
  });

  it("status labels pt-BR", () => {
    expect(statusLabel("DRAFT")).toBe("Rascunho");
    expect(statusLabel("SUBMITTED")).toBe("Submetido");
    expect(statusLabel("IN_CLEARANCE")).toBe("Em liberação");
    expect(statusLabel("PARTIALLY_CLEARED")).toBe("Parcialmente liberado");
    expect(statusLabel("CLEARED")).toBe("Liberado");
    expect(statusLabel("CANCELLED")).toBe("Cancelado");
  });

  it("conflict 409 message includes reason code", () => {
    const err = Object.assign(new Error("oversubscription"), {
      status: 409,
      code: "qty_oversubscribed",
    });
    expect(conflictMessage(err)).toContain("409");
    expect(conflictMessage(err)).toContain("qty_oversubscribed");
    expect(conflictMessage(err)).toContain("oversubscription");
  });
});

/** Matriz mínima de papéis operacionais (espelha seed Identity). */
describe("role permission matrix (I5-5)", () => {
  const ADUANA = [
    "customs:read",
    "customs:write",
    "customs:clear",
    "documents:read",
    "documents:write",
    "audit:read",
  ];
  const ESTOQUE = [
    "inventory:read",
    "inventory:write",
    "inventory:adjust",
    "documents:read",
    "audit:read",
  ];

  it("aduana pode operar customs e não inventário write", () => {
    const user: User = { ...base, role: "aduana", permissions: ADUANA };
    expect(canReadCustoms(user)).toBe(true);
    expect(canWriteCustoms(user)).toBe(true);
    expect(canClearCustoms(user)).toBe(true);
    expect(ADUANA).not.toContain("inventory:write");
  });

  it("estoque opera inventário e não customs write", () => {
    const user: User = { ...base, role: "estoque", permissions: ESTOQUE };
    expect(canReadCustoms(user)).toBe(false);
    expect(ESTOQUE).toContain("inventory:write");
    expect(ESTOQUE).toContain("inventory:adjust");
    expect(ESTOQUE).not.toContain("customs:write");
  });
});
