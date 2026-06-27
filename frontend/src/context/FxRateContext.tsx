import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { financeApi, type FxReference } from "../api";

interface FxRateContextValue {
  reference: FxReference | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const FxRateContext = createContext<FxRateContextValue | null>(null);

export function FxRateProvider({ children }: { children: ReactNode }) {
  const [reference, setReference] = useState<FxReference | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const ref = await financeApi.fxReference();
      setReference(ref);
    } catch {
      setReference({
        currency_from: "EUR",
        currency_to: "BRL",
        rate: null,
        rate_date: null,
        source: null,
        disclaimer: "Cotação indisponível — clique para tentar novamente.",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <FxRateContext.Provider value={{ reference, loading, refresh }}>
      {children}
    </FxRateContext.Provider>
  );
}

export function useFxRate(): FxRateContextValue {
  const ctx = useContext(FxRateContext);
  if (!ctx) {
    throw new Error("useFxRate must be used within FxRateProvider");
  }
  return ctx;
}
