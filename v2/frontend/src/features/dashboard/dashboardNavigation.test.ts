import { describe, expect, it } from "vitest";
import { dashboardNavigation } from "./dashboardNavigation";
import type { DashboardSnapshot, DashboardWidget } from "./dashboardApi";
const widget=(id:string,extra:Partial<DashboardWidget>={}):DashboardWidget=>({widget_id:id,metric_id:id,label:id,short_description:"",kind:"kpi_currency",status:"AVAILABLE",display:{},drill:"/payables",currencies:["EUR"],filters_applied:["date_from","date_to","currency","supplier_id"],filters_ignored:[],...extra});
const snapshot=(widgets:DashboardWidget[]):DashboardSnapshot=>({generated_at:"2026-11-18T12:00:00Z",view_id:null,view_name:null,base_preset:"executiva",filters:{date_from:"2026-11-01",date_to:"2027-02-28",currency:"EUR",supplier_id:2},lane:{lane:"Teste",includes_trial_mass:true},widgets,home_ok:true,fallback_path:"/orders",default_preset:"executiva"});
describe("dashboard navigation preserves the metric's scope",()=>{
 it("keeps overdue state, due period, currency and supplier",()=>{
  const result=dashboardNavigation(snapshot([widget("ap.overdue")]));
  const q=new URLSearchParams(result.widgets[0].drill.split("?")[1]);
  expect(Object.fromEntries(q)).toEqual({pending:"OVERDUE",due_after:"2026-11-01",due_before:"2027-02-28",currency:"EUR",supplier_id:"2"});
 });
 it("carries only applied filters and retains existing link parameters",()=>{
  const result=dashboardNavigation(snapshot([widget("attention.inbox",{drill:"/payables?purpose=fx&currency=USD",filters_applied:["currency"]})]));
  expect(result.widgets[0].drill).toBe("/payables?purpose=fx&currency=USD");
 });
 it("limits cash due to the three civil months and uses the response month",()=>{
  const result=dashboardNavigation(snapshot([widget("ap.cash_due",{filters_applied:["date_to"]}),widget("ap.cash_committed",{display:{as_of_month:"2026-11-01"},filters_applied:["date_to"]})]));
  expect(result.widgets[0].drill).toContain("due_before=2027-01-31");
  expect(result.widgets[0].drill).toContain("due_after=2026-11-01");
  expect(result.widgets[1].drill).not.toContain("due_after");
 });
 it("intersects the seven-day metric with the selected period",()=>{
  const result=dashboardNavigation(snapshot([widget("ap.next_7d")]));
  expect(result.widgets[0].drill).toContain("due_after=2026-11-19");
  expect(result.widgets[0].drill).toContain("due_before=2026-11-25");
 });
 it("opens stock positions across regimes and does not invent permission or missing links",()=>{
  const result=dashboardNavigation(snapshot([widget("goods.flow",{drill:"",display:{segments:[{key:"stock",href:"/inventory/movements"},{key:"confirmed",href:"/orders"},{key:"stock"}]}})]));
  expect(result.widgets[0].display.segments).toEqual([{key:"stock",href:"/inventory/positions?status=positive&position_ids=&modality_ids=&item_kind_ids=&model_ids=&location_ids=&q="},{key:"confirmed",href:"/orders?status=CONFIRMED"},{key:"stock"}]);
 });
});
