import type { DashboardSnapshot, DashboardWidget } from "./dashboardApi";

function dated(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`;
}

/** Carry only filters the metric actually applied and the destination supports. */
export function dashboardNavigation(snapshot: DashboardSnapshot): DashboardSnapshot {
  const month = snapshot.widgets.find(w => w.widget_id === "ap.cash_committed")?.display.as_of_month;
  const generated = new Date(snapshot.generated_at);
  const monthStart = typeof month === "string" ? month : dated(new Date(generated.getFullYear(), generated.getMonth(), 1));
  const endOfQuarter = dated(new Date(Number(monthStart.slice(0,4)), Number(monthStart.slice(5,7))+2, 0));
  const link = (href: string, w: DashboardWidget): string => {
    if (!href.startsWith("/payables") || href.split("?")[0] !== "/payables") return href;
    const [path, search] = href.split("?");
    const params = new URLSearchParams(search);
    const mapping = { date_from:"due_after", date_to:"due_before", currency:"currency", supplier_id:"supplier_id" } as const;
    for (const [source, target] of Object.entries(mapping)) {
      const value = snapshot.filters[source as keyof typeof mapping];
      if (w.filters_applied.includes(source) && value != null && value !== "" && !params.has(target)) params.set(target, String(value));
    }
    if (w.widget_id.startsWith("ap.") || w.widget_id === "treasury.fx_exposure") {
      params.set("pending", w.widget_id === "ap.overdue" ? "OVERDUE" : "OPEN_BALANCE");
    }
    if (["ap.cash_due","ap.cash_committed"].includes(w.widget_id)) {
      if (w.widget_id === "ap.cash_due") params.set("due_after", monthStart);
      // The agenda includes overdue plus three civil months, not all future payments.
      const until = params.get("due_before");
      let last = until && until < endOfQuarter ? until : endOfQuarter;
      if (w.widget_id === "ap.cash_committed") {
        const overdueEnd = dated(new Date(Number(monthStart.slice(0,4)),Number(monthStart.slice(5,7))-1,0));
        if (last < overdueEnd) last = overdueEnd;
      }
      params.set("due_before", last);
    }
    if (w.widget_id === "ap.next_7d") {
      const first = new Date(generated); first.setDate(first.getDate()+1);
      const last = new Date(generated); last.setDate(last.getDate()+7);
      const after=params.get("due_after"),before=params.get("due_before");
      params.set("due_after",after && after>dated(first)?after:dated(first));
      params.set("due_before",before && before<dated(last)?before:dated(last));
    }
    if (w.widget_id === "treasury.fx_exposure" && !params.has("currency") && w.currencies.length === 1) params.set("currency",w.currencies[0]);
    return path + (params.size ? `?${params}` : "");
  };
  return { ...snapshot, widgets:snapshot.widgets.map(w => {
    let display=w.display;
    if (w.widget_id === "goods.flow" && Array.isArray(display.segments)) {
      display={...display,segments:display.segments.map(segment => {
        const row=segment as Record<string,unknown>;
        if (row.key === "stock" && row.href) return {...row,href:"/inventory/positions?status=positive&position_ids=&modality_ids=&item_kind_ids=&model_ids=&location_ids=&q="};
        if (row.key === "confirmed" && row.href) return {...row,href:"/orders?status=CONFIRMED"};
        return row;
      })};
    }
    if (Array.isArray(display.items)) display={...display,items:display.items.map(item=>{
      const row=item as Record<string,unknown>;
      return typeof row.href === "string" ? {...row,href:link(row.href,w)} : row;
    })};
    return {...w,display,drill:link(w.drill,w)};
  }) };
}
