import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { loadReturnState, saveReturnState } from "../navigation/returnState";

/** Persiste search da fila; restaura scroll/seleção ao voltar (I9-9). */
export function useListReturn(listPath: string, selectedId?: string | null) {
  const location = useLocation();

  useEffect(() => {
    if (location.pathname !== listPath) return;
    saveReturnState(listPath, {
      search: location.search,
      scrollY: window.scrollY,
      selectedId: selectedId ?? null,
    });
  }, [listPath, location.pathname, location.search, selectedId]);

  useEffect(() => {
    if (location.pathname !== listPath) return;
    const snap = loadReturnState(listPath);
    if (!snap) return;
    const y = snap.scrollY;
    requestAnimationFrame(() => {
      window.scrollTo(0, y);
      if (snap.selectedId) {
        document
          .querySelector(`[data-row-id="${snap.selectedId}"]`)
          ?.scrollIntoView({ block: "nearest" });
      }
    });
  }, [listPath, location.pathname, location.key]);
}
