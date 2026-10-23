import { afterEach, describe, expect, it, vi } from "vitest";
import { pointer, validateManifest } from "./demoManifest";
import { waitForTarget } from "./demoWait";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); document.body.innerHTML = ""; });
describe("demo read-only gates", () => {
  it("waits for the complete filtered route, not only its pathname", async () => {
    vi.useFakeTimers();const prior=location.pathname+location.search;
    history.replaceState({},"","/inventory/positions?q=SHOW&modality_ids=");
    const el=document.createElement("div");el.id="stock-target";el.textContent="42 UN";document.body.append(el);
    el.getBoundingClientRect=()=>({height:50} as DOMRect);
    const result=waitForTarget("/inventory/positions?q=SHOW&modality_ids=","#stock-target",new AbortController().signal);
    await vi.advanceTimersByTimeAsync(350);expect(await result).toBe(el);expect(vi.getTimerCount()).toBe(0);history.replaceState({},"",prior);
  });
  it("reads nested fields and array lengths without evaluation", () => {
    expect(pointer({ rows: [{ amount: "2" }] }, "rows.0.amount")).toBe("2");
    expect(pointer({ rows: [] }, "rows.length")).toBe(0);
    expect(pointer({}, "missing.field")).toBeUndefined();
  });
  it("refuses an operational database before loading manifest", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ app_env: "test", logical_database: "epic_v2", schema_ok: true }), { headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetch);
    await expect(validateManifest(new AbortController().signal)).rejects.toThrow(/Isolamento/);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("explains an HTML fallback instead of parsing it as a manifest", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ app_env: "test", logical_database: "epic_v2_test", schema_ok: true }), { headers: { "content-type": "application/json" } })).mockResolvedValueOnce(new Response("<html/>", { headers: { "content-type": "text/html" } })));
    await expect(validateManifest(new AbortController().signal)).rejects.toThrow(/não servido como JSON/);
  });
  it("rejects incomplete manifests before any data preparation", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ app_env: "test", logical_database: "epic_v2_test", schema_ok: true }), { headers: { "content-type": "application/json" } })).mockResolvedValueOnce(new Response('{}', { headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetch);
    await expect(validateManifest(new AbortController().signal)).rejects.toThrow(/Manifesto/);
    expect(fetch.mock.calls.every(([, init]) => !init.method || init.method === "GET")).toBe(true);
  });
  it("cancels target waiting immediately and clears polling", async () => {
    vi.useFakeTimers(); const controller = new AbortController();
    const result = waitForTarget("/missing", "[data-test-missing]", controller.signal);
    const assertion = expect(result).rejects.toMatchObject({ name: "AbortError" });
    controller.abort(); await assertion; expect(vi.getTimerCount()).toBe(0);
  });
  it("missing target times out instead of advancing blindly", async () => {
    vi.useFakeTimers();
    const result = waitForTarget("/missing", "[data-test-missing]", new AbortController().signal);
    const assertion = expect(result).rejects.toThrow(/interrompido/);
    await vi.advanceTimersByTimeAsync(15100); await assertion; expect(vi.getTimerCount()).toBe(0);
  });
});
