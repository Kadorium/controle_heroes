import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, it, expect, vi } from "vitest";
import { RecordWorkHeader } from "./RecordWorkHeader";
afterEach(cleanup);
describe("record work navigation",()=>{
 it("opens and focuses a collapsed section without transacting",()=>{
  const mutate=vi.fn();HTMLElement.prototype.scrollIntoView=vi.fn();
  render(<MemoryRouter><RecordWorkHeader title="Operação" primary={{label:"Receber mercadorias",onClick:mutate}} topics={[{id:"entry",label:"Entrada no estoque",state:"Parcial",result:"4 UN recebidas",href:"#entry",tone:"partial"}]}/><details><summary>Detalhes</summary><section id="entry">Recebimentos</section></details></MemoryRouter>);
  fireEvent.click(screen.getByTestId("record-topic-entry"));expect(mutate).not.toHaveBeenCalled();expect(document.activeElement?.id).toBe("entry");expect(document.querySelector("details")?.open).toBe(true);
 });
 it("explains business blocking independently of permission",()=>{
  render(<MemoryRouter><RecordWorkHeader title="Operação" primary={{label:"Submeter operação",disabled:true,reason:"Informe a referência da declaração."}} topics={[]}/></MemoryRouter>);
  const button=screen.getByRole("button",{name:"Submeter operação"});expect(button).toBeDisabled();expect(button).toHaveAccessibleDescription("Informe a referência da declaração.");
 });
 it("closes the actions menu with Escape and restores keyboard focus",()=>{
  render(<MemoryRouter><RecordWorkHeader title="Pedido" more={[{label:"Atualizar",onClick:vi.fn()}]} topics={[]}/></MemoryRouter>);
  const menu=document.querySelector("details")!;menu.open=true;fireEvent.keyDown(document,{key:"Escape"});expect(menu.open).toBe(false);expect(document.activeElement?.tagName).toBe("SUMMARY");
 });
});
