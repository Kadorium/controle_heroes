import type { ReactNode } from "react";
import { emptyDash } from "../../i18n/glossario";

export const CATEGORY_OPTIONS = [
  { value: "RACKET", label: "Raquete" },
  { value: "BALL", label: "Bola" },
  { value: "BAG_ACCESSORY", label: "Bolsa/Acessório" },
  { value: "APPAREL", label: "Roupa" },
  { value: "PICKLEBALL", label: "Pickleball" },
  { value: "OTHER", label: "Outro" },
];

export function heroesCell(value: string | null | undefined, heroesSource?: boolean) {
  if (value == null || value === "") return emptyDash(null);
  if (!heroesSource) return value;
  return (
    <span title="Origem: planilha Heroes — não equivale a dado oficial sem comprovante">
      {value}
      <span className="sheet-flag-it" style={{ marginLeft: 4 }}>
        H
      </span>
    </span>
  );
}

export function LockedCell({
  children,
  onOverride,
  title,
}: {
  children: ReactNode;
  onOverride?: () => void;
  title?: string;
}) {
  const defaultTitle = "Campo origem Itália — não pode ser editado diretamente";
  if (!onOverride) {
    return (
      <span className="sheet-cell sheet-cell--locked" title={title ?? defaultTitle}>
        {children}
        <span className="sheet-flag-it">IT</span>
      </span>
    );
  }
  return (
    <button
      type="button"
      className="sheet-cell sheet-cell--locked sheet-cell--locked-btn"
      title={
        title ??
        "Campo origem Itália. Não pode ser editado diretamente — use override auditado (motivo + anexo)."
      }
      onClick={onOverride}
    >
      {children}
      <span className="sheet-flag-it">IT</span>
    </button>
  );
}
