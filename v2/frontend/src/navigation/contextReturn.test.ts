import { describe, it, expect } from "vitest";
import { contextReturn, withContextReturn } from "./contextReturn";
describe("explicit return context",()=>{
 it("preserves origin query and anchor",()=>{const url=withContextReturn("/inventory/receiving?process_id=15&state=all","/customs/15?source=queue#customs-entry");expect(new URL(url,"http://local").searchParams.get("return_to")).toBe("/customs/15?source=queue#customs-entry");});
 it("accepts the owner form and original queue",()=>{expect(contextReturn("/orders/15/commercial#order-invoices")).toBeTruthy();expect(contextReturn("/inventory/receiving?q=SKU&state=all&offset=25")).toBeTruthy();});
 it("rejects external and unrelated destinations",()=>{for(const url of ["//evil.test","https://evil.test","/users","/customs/15\\evil","/customs/15\n"])expect(contextReturn(url)).toBeNull();});
});
