import { useCallback, useMemo, useState } from "react";
import type { Product } from "../../api";
import {
  bulkEligible,
  type BulkAction,
  type BulkEligibility,
} from "./productCatalogUtils";

export function useProductSelection(rows: Product[]) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const selectedProducts = useMemo(
    () => rows.filter((r) => selectedIds.has(r.id)),
    [rows, selectedIds],
  );

  const allVisibleSelected = rows.length > 0 && rows.every((r) => selectedIds.has(r.id));

  const toggle = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAllVisible = useCallback(() => {
    setSelectedIds(new Set(rows.map((r) => r.id)));
  }, [rows]);

  const clear = useCallback(() => setSelectedIds(new Set()), []);

  const toggleAllVisible = useCallback(() => {
    if (allVisibleSelected) clear();
    else selectAllVisible();
  }, [allVisibleSelected, clear, selectAllVisible]);

  const eligibleFor = useCallback(
    (action: BulkAction): BulkEligibility => bulkEligible(selectedProducts, action),
    [selectedProducts],
  );

  return {
    selectedIds,
    selectedProducts,
    count: selectedIds.size,
    allVisibleSelected,
    toggle,
    toggleAllVisible,
    selectAllVisible,
    clear,
    eligibleFor,
  };
}
