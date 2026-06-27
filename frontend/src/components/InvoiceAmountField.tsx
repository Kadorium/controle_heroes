import { emptyDash, formatMoney } from "../i18n/glossario";
import {
  INVOICE_AMOUNT_MODES,
  resolveInvoiceAmount,
  type InvoiceAmountMode,
} from "../pages/importation/novaOrdemInvoice";

interface Props {
  label?: string;
  mode: InvoiceAmountMode;
  value: string;
  baseEur: number | null;
  provisionRate: string;
  onModeChange: (mode: InvoiceAmountMode) => void;
  onValueChange: (value: string) => void;
}

export function InvoiceAmountField({
  label = "Valor da fatura",
  mode,
  value,
  baseEur,
  provisionRate,
  onModeChange,
  onValueChange,
}: Props) {
  const rate = Number(String(provisionRate).replace(",", "."));
  const appliedRate = Number.isNaN(rate) ? null : rate;
  const resolved = resolveInvoiceAmount(mode, value, baseEur, appliedRate);
  const modeMeta = INVOICE_AMOUNT_MODES.find((m) => m.id === mode)!;
  const isPercent = mode === "PCT_EUR" || mode === "PCT_BRL";

  return (
    <div className="invoice-amount">
      <span className="invoice-amount__label">{label}</span>
      <div className="invoice-amount__modes" role="radiogroup" aria-label="Tipo de valor da fatura">
        {INVOICE_AMOUNT_MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={mode === m.id}
            className={`invoice-amount__mode${mode === m.id ? " invoice-amount__mode--on" : ""}`}
            title={m.label}
            onClick={() => onModeChange(m.id)}
          >
            {m.short}
          </button>
        ))}
      </div>
      <div className="invoice-amount__input-wrap">
        <input
          type="text"
          inputMode="decimal"
          className="invoice-amount__input"
          value={value}
          onChange={(e) => onValueChange(e.target.value)}
          placeholder={isPercent ? "ex.: 30" : mode === "BRL" ? "ex.: 15.000,00" : "ex.: 2.500,00"}
          aria-label={modeMeta.label}
        />
        {modeMeta.inputSuffix && (
          <span className="invoice-amount__input-suffix">{modeMeta.inputSuffix}</span>
        )}
      </div>
      {(resolved.previewEur !== null || resolved.previewBrl !== null) && (
        <p className="invoice-amount__preview meta">
          <strong>
            {resolved.previewEur !== null ? formatMoney(resolved.previewEur, "EUR") : emptyDash(null)}
          </strong>
          {resolved.previewBrl !== null && (
            <>
              {" · "}
              <strong>{formatMoney(resolved.previewBrl, "BRL")}</strong>
            </>
          )}
        </p>
      )}
      {isPercent && baseEur === null && value.trim() && (
        <p className="meta invoice-amount__hint">Informe itens ou total da ordem para calcular o %.</p>
      )}
      {!appliedRate && value.trim() && (
        <p className="meta invoice-amount__hint">Câmbio provisionado necessário para conversão.</p>
      )}
    </div>
  );
}
