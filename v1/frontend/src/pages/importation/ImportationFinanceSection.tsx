import { useState } from "react";
import type { FinancialSummary, Importation, ImportationItem, Invoice } from "../../api";
import { FinanceTabBar, FinanceTabContent, type FinanceTab } from "../finance/FinancePanels";

interface Props {
  importationId: number;
  importation: Importation;
  summary: FinancialSummary;
  invoices: Invoice[];
  items: ImportationItem[];
  onReload: () => Promise<void>;
}

export function ImportationFinanceSection({
  importationId,
  importation,
  summary,
  invoices,
  items,
  onReload,
}: Props) {
  const [tab, setTab] = useState<FinanceTab>("pagamentos");

  const scope = {
    mode: "importation" as const,
    importationId,
    importation,
    invoices,
    items,
    summary,
    currency: importation.currency,
    supplierId: importation.supplier_id,
    onReload,
  };

  return (
    <div>
      <FinanceTabBar active={tab} onChange={setTab} />
      <FinanceTabContent tab={tab} scope={scope} />
    </div>
  );
}
