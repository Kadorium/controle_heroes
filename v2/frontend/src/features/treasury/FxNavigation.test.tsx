import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { PayablesListPage } from "../billing/InvoicesListPage";
import { PayableFxPage } from "./PayableFxPage";
import { getPayable } from "../billing/billingApi";
vi.mock("../billing/billingApi",()=>({getPayable:vi.fn(),listInvoices:vi.fn()}));
vi.mock("./FxPanels",()=>({PayableFxPanel:()=> <div>FX permitido</div>}));
const actor={id:11,name:"FX",email:"fx@example.com",role:"fx-only",permissions:["treasury:fx_read"]};
afterEach(()=>{cleanup();vi.restoreAllMocks();sessionStorage.clear();});
function Location(){return <p data-testid="location">{useLocation().pathname}</p>;}
it("FX-only enters the existing obligation route without loading the AP list",()=>{
 const fetchSpy=vi.spyOn(globalThis,"fetch");
 render(<MemoryRouter initialEntries={["/payables?purpose=fx"]}><PayablesListPage user={actor}/><Location/></MemoryRouter>);
 expect(fetchSpy).not.toHaveBeenCalled();
 expect(screen.getByRole("button",{name:"Abrir câmbio"})).toBeDisabled();
 fireEvent.change(screen.getByLabelText("Número da obrigação"),{target:{value:"2"}});
 fireEvent.click(screen.getByRole("button",{name:"Abrir câmbio"}));
 expect(screen.getByTestId("location")).toHaveTextContent("/payables/2/fx");
});
it("FX-only does not request billing context or display its loading state",()=>{
 render(<MemoryRouter initialEntries={["/payables/2/fx"]}><Routes><Route path="/payables/:payableId/fx" element={<PayableFxPage user={actor}/>}/></Routes></MemoryRouter>);
 expect(getPayable).not.toHaveBeenCalled();expect(screen.getByText("FX permitido")).toBeVisible();
 expect(screen.queryByText("Carregando obrigação…")).toBeNull();
 expect(screen.getByRole("link",{name:"Voltar à fila"})).toHaveAttribute("href","/payables?purpose=fx");
});
it("a user without billing or FX cannot enter the lookup or load the queue",()=>{
 const fetchSpy=vi.spyOn(globalThis,"fetch");
 render(<MemoryRouter initialEntries={["/payables?purpose=fx"]}><PayablesListPage user={{...actor,permissions:[]}}/></MemoryRouter>);
 expect(screen.queryByLabelText("Número da obrigação")).toBeNull();expect(fetchSpy).not.toHaveBeenCalled();
});
