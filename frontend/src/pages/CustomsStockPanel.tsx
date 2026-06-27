import { Navigate } from "react-router-dom";

/** @deprecated Aduana integrada em /importacoes/:id/logistica */
export function CustomsStockPanel({
  importationId,
}: {
  importationId: number;
  items?: unknown[];
}) {
  return <Navigate to={`/importacoes/${importationId}/logistica#aduana`} replace />;
}
