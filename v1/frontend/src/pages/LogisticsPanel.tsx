import { LogisticsWorkflowPage } from "./importation/logistics/LogisticsWorkflowPage";

/** @deprecated Use LogisticsWorkflowPage via /importacoes/:id/logistica */
export function LogisticsPanel({ importationId }: { importationId: number }) {
  return <LogisticsWorkflowPage importationId={importationId} />;
}

export { LogisticsWorkflowPage };
