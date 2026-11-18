import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { SupplierDetailPage } from "./SupplierDetailPage";
import { getSupplier } from "./catalogApi";
import { listEntityAudit } from "../customs/customsApi";
vi.mock("./catalogApi",()=>({getSupplier:vi.fn(),patchSupplier:vi.fn()}));
vi.mock("../customs/customsApi",()=>({listEntityAudit:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
it("catalog access alone opens the supplier without requesting audit",async()=>{
 vi.mocked(getSupplier).mockResolvedValue({id:2,name:"Fornecedor permitido",code:null,country_code:null,tax_id:null,is_active:true} as Awaited<ReturnType<typeof getSupplier>>);
 const user={id:11,name:"Catálogo",email:"c@example.com",role:"catalog-only",permissions:["catalog:read","catalog:write"]};
 render(<MemoryRouter initialEntries={["/catalog/suppliers/2"]}><Routes><Route path="/catalog/suppliers/:supplierId" element={<SupplierDetailPage user={user}/>}/></Routes></MemoryRouter>);
 expect(await screen.findByRole("heading",{name:"Fornecedor permitido"})).toBeVisible();expect(listEntityAudit).not.toHaveBeenCalled();
});
