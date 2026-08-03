import { describe, expect, it, beforeEach } from "vitest";
import {
  buildReturnTo,
  clearReturnState,
  loadReturnState,
  saveReturnState,
} from "./returnState";

describe("returnState", () => {
  beforeEach(() => {
    clearReturnState("/orders");
    sessionStorage.clear();
  });

  it("salva e restaura search/scroll/selected", () => {
    saveReturnState("/orders", { search: "?status=DRAFT", scrollY: 120, selectedId: "42" });
    const snap = loadReturnState("/orders");
    expect(snap?.search).toBe("?status=DRAFT");
    expect(snap?.scrollY).toBe(120);
    expect(snap?.selectedId).toBe("42");
  });

  it("buildReturnTo usa snapshot ou fallback", () => {
    expect(buildReturnTo("/orders", "status=OPEN")).toBe("/orders?status=OPEN");
    saveReturnState("/orders", { search: "?status=CONFIRMED" });
    expect(buildReturnTo("/orders")).toBe("/orders?status=CONFIRMED");
  });

  it("não inventa filtro quando vazio", () => {
    expect(buildReturnTo("/payables")).toBe("/payables");
  });
});
