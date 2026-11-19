import { render,screen,cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach,it,expect } from "vitest";
import { ApProjection,ApReference,apPendingText } from "./apQueuePresentation";
afterEach(cleanup);
it("does not infer absence/zero/inapplicability from BRL alone",()=>{
 const view=render(<ApProjection row={{id:1,currency:"BRL",fx_projected_rate:"0",fx_projected_brl:"0"}}/>);
 expect(screen.getByText("BRL 0,00")).toBeVisible();expect(screen.queryByText(/Não aplicável/)).toBeNull();
 view.rerender(<ApProjection row={{id:1,currency:"BRL"}}/>);expect(screen.getByText("Sem projeção cambial")).toBeVisible();
 view.rerender(<ApProjection row={{id:1,currency:"EUR",fx_projected_rate:"5.1"}}/>);expect(screen.getByText("BRL não informado")).toBeVisible();
 view.rerender(<ApProjection row={{id:1,currency:"BRL",source_type:"CUSTOMS_FUNDING"}}/>);expect(screen.getByText("Não aplicável ao numerário")).toBeVisible();
});
it("only removes overdue when the date actually communicates the delay",()=>{
 expect(apPendingText({id:1,due_date:"2026-01-01",days_overdue:34,pendencies:["OVERDUE","MISSING_FX","OPEN_BALANCE","REVIEW_NEW"]})).toBe("Sem plano cambial, Saldo aberto, REVIEW_NEW");
 expect(apPendingText({id:1,days_overdue:0,pendencies:["OVERDUE"]})).toBe("Vencido");
});
it("keeps middle-colliding references distinguishable and complete destinations accessible",()=>{
 const references=["PREFIXO-COMPARTILHADO-AAA-MEIO-SUFIXO-COMPARTILHADO", "PREFIXO-COMPARTILHADO-BBB-MEIO-SUFIXO-COMPARTILHADO"];
 render(<MemoryRouter>{references.map((text,i)=><ApReference key={text} text={text} id={i+1} entity="Fatura" href={`/invoices/${i+1}`}/>)}</MemoryRouter>);
 expect(screen.getByRole("link",{name:`Fatura ${references[0]}`})).toHaveAttribute("href","/invoices/1");
 expect(screen.getByRole("button",{name:"Ver referência completa: Fatura 1"})).toHaveTextContent("#1");
 expect(screen.getByRole("button",{name:"Ver referência completa: Fatura 2"})).toHaveTextContent("#2");
});
