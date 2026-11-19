import { describe, it, expect } from "vitest";
import { accountsWorkState, billingWorkState } from "./orderWorkState";
import type { OrderQtyRow } from "../billing/billingApi";
import type { ApQueueCurrencyKpis, ApQueueResponse } from "../reporting/reportingApi";
const line=(extra:Partial<OrderQtyRow>={}):OrderQtyRow=>({order_item_id:1,ordered_qty:"16",issued_qty:"0",available_qty:"16",billable:true,...extra});
const group=(extra:Partial<ApQueueCurrencyKpis>={}):ApQueueCurrencyKpis=>({currency:"BRL",open_balance:"100",overdue_balance:"0",due_today_balance:"0",next_7d_balance:"0",overdue_count:0,total_count:1,...extra});
const queue=(groups:ApQueueCurrencyKpis[]):ApQueueResponse=>({items:[],total:100,limit:1,offset:0,kpis:{kpis_by_currency:groups}});
describe("order header states use quantities and complete queue KPIs",()=>{
  it("preserves eligible lines beside unbound commitments",()=>expect(billingWorkState([line(),line({order_item_id:2,billable:false})],"CONFIRMED").eligible).toBe(true));
  it("does not infer billing completion from an issued subset",()=>expect(billingWorkState([line({issued_qty:"10",available_qty:"6"})],"CONFIRMED").state).toBe("Faturamento parcial"));
  it("requires every line to prove completion",()=>expect(billingWorkState([line({issued_qty:"16",available_qty:"0"})],"CONFIRMED").tone).toBe("complete"));
  it("does not bill a draft or closed order",()=>{expect(billingWorkState([line()],"DRAFT").eligible).toBe(false);expect(billingWorkState([line()],"CLOSED").eligible).toBe(false);});
  it("does not claim completion for an empty source",()=>expect(billingWorkState([],"CONFIRMED").tone).not.toBe("complete"));
  it("uses overdue KPIs even when no rows in the page",()=>expect(accountsWorkState(queue([group({overdue_count:3})])).overdue).toBe(true));
  it("keeps currencies separate",()=>{const state=accountsWorkState(queue([group(),group({currency:"EUR",open_balance:"20"})]));expect(state.result).toContain("100");expect(state.result).toContain("20");expect(state.result).not.toContain("120");});
  it("does not label absence as settled accounts",()=>expect(accountsWorkState(queue([])).tone).toBe("empty"));
  it("labels settled only for existing accounts with zero balance",()=>expect(accountsWorkState(queue([group({open_balance:"0"})])).tone).toBe("complete"));
});
