import { useEffect, useState } from "react";
import { listProducts, listSuppliers, type Product, type Supplier } from "./catalogApi";

/** Debounce GET array com q — não trata os primeiros N como catálogo inteiro. */
export function useProductSearch(q: string, opts?: { activeOnly?: boolean; limit?: number }) {
  const activeOnly = opts?.activeOnly ?? true;
  const limit = opts?.limit ?? 20;
  const [items, setItems] = useState<Product[]>([]);
  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      void listProducts(q.trim() || undefined, { activeOnly, limit })
        .then((rows) => {
          if (!cancelled) setItems(rows);
        })
        .catch(() => {
          if (!cancelled) setItems([]);
        });
    }, 200);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [q, activeOnly, limit]);
  return items;
}

export function useSupplierSearch(q: string, opts?: { activeOnly?: boolean; limit?: number }) {
  const activeOnly = opts?.activeOnly ?? true;
  const limit = opts?.limit ?? 20;
  const [items, setItems] = useState<Supplier[]>([]);
  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      void listSuppliers(q.trim() || undefined, { activeOnly, limit })
        .then((rows) => {
          if (!cancelled) setItems(rows);
        })
        .catch(() => {
          if (!cancelled) setItems([]);
        });
    }, 200);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [q, activeOnly, limit]);
  return items;
}
