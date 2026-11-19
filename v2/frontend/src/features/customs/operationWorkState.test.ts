import { describe,it,expect } from "vitest";
import { entryState,releaseState } from "./operationWorkState";
import type { ReceivingRow } from "../inventory/processReceiving";
import type { ClearanceResidual } from "../inventory/inventoryApi";
const row=(received:number,pending:number,extra:Partial<ReceivingRow>={}):ReceivingRow=>({item_id:1,nationalization_id:1,process_id:1,process_code:"IMP-1",process_reference:null,release_reference:null,product_id:1,sku:"A",product_name:"A",unit:"UN",released_qty:String(received+pending),received_qty:String(received),pending_qty:String(pending),state:pending?"pending":"complete",block_reason:null,...extra});
const scope=(released:number,remaining:number):ClearanceResidual[]=>[{source_kind:"invoice_item",invoice_item_id:1,shipment_item_id:null,allocated_qty:String(released+remaining),nationalized_qty:String(released),residual_qty:String(remaining),product_id:1,product_sku:"A",product_name:"A",shipped_qty:String(released+remaining)}];
describe("authoritative release versus physical entry",()=>{
 it("does not turn no released rows into completion",()=>expect(entryState([],scope(0,16),true).state).toBe("Aguardando liberação"));
 it("shows released but not yet received",()=>expect(entryState([row(0,10)],scope(10,6),true).state).toBe("A receber"));
 it("keeps 16 total / 10 released / 10 received partial",()=>expect(entryState([row(10,0)],scope(10,6),true).state).toBe("Parcial — resta liberar"));
 it("shows a partial physical receipt",()=>expect(entryState([row(4,6)],scope(10,6),true).state).toBe("Recebimento parcial"));
 it("requires the complete applicable scope",()=>expect(entryState([row(16,0)],scope(16,0),true).state).toBe("Escopo integral recebido"));
 it("does not infer the denominator for an inventory-only reader",()=>expect(entryState([row(10,0)],null,false).tone).toBe("info"));
 it("does not complete an incompletely allocated process",()=>expect(entryState([row(10,0)],scope(10,0),false).tone).toBe("info"));
 it("keeps blocked eligibility separate from released quantities",()=>expect(entryState([row(0,10,{state:"blocked",block_reason:"Produto inativo"})],scope(10,0),true).result).toBe("Produto inativo"));
 it("never adds incompatible units",()=>expect(entryState([row(4,6),row(1,2,{item_id:2,unit:"KG"})],scope(13,0),true).result).toContain("4 UN · 1 KG"));
 it("a released scope is independent of physical entry",()=>expect(releaseState(scope(16,0)).state).toBe("Escopo alocado liberado"));
});
