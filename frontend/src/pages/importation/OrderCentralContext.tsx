import { createContext, useContext, type ReactNode } from "react";
import type { OrderCentralResponse } from "../../api";

export interface OrderCentralContextValue {
  data: OrderCentralResponse | null;
  loading: boolean;
  error: string;
  reloadCentral: () => Promise<void>;
}

const OrderCentralContext = createContext<OrderCentralContextValue | null>(null);

export function OrderCentralProvider({
  value,
  children,
}: {
  value: OrderCentralContextValue;
  children: ReactNode;
}) {
  return <OrderCentralContext.Provider value={value}>{children}</OrderCentralContext.Provider>;
}

export function useOrderCentral(): OrderCentralContextValue {
  const ctx = useContext(OrderCentralContext);
  if (!ctx) {
    throw new Error("useOrderCentral must be used within OrderCentralProvider");
  }
  return ctx;
}
