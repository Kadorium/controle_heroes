import { useEffect, useState, type InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type"> & {
  value: string;
  onValueChange: (next: string) => void;
  currency?: string | null;
  invalid?: boolean;
};

/** Converte digitação pt-BR/`1.234,56` ou cru `1234.56` → string API com ponto. */
export function parseMoneyInput(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const normalized = trimmed.includes(",")
    ? trimmed.replace(/\./g, "").replace(",", ".")
    : trimmed;
  if (!/^-?\d+(\.\d+)?$/.test(normalized)) return trimmed;
  return normalized;
}

function formatDisplay(apiValue: string): string {
  if (!apiValue.trim()) return "";
  const n = Number(apiValue);
  if (!Number.isFinite(n)) return apiValue;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

/**
 * Input monetário: exibe pt-BR no blur; emite string com ponto para o contrato.
 * Preserva `<input>` real para E2E (`eligible-table tbody tr input`).
 */
export function MoneyInput({
  value,
  onValueChange,
  currency,
  invalid,
  className,
  onBlur,
  onFocus,
  disabled,
  ...rest
}: Props) {
  const [focused, setFocused] = useState(false);
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    if (!focused) setDraft(value);
  }, [value, focused]);

  const display = focused ? draft : formatDisplay(value);

  return (
    <span className={["money-input-wrap", className].filter(Boolean).join(" ")}>
      {currency ? <span className="money-input-currency">{currency}</span> : null}
      <input
        type="text"
        inputMode="decimal"
        className={["ds-input", "money-input", "num", invalid ? "ds-input--invalid" : null]
          .filter(Boolean)
          .join(" ")}
        value={display}
        disabled={disabled}
        aria-invalid={invalid || undefined}
        onFocus={(e) => {
          setFocused(true);
          setDraft(value);
          onFocus?.(e);
          requestAnimationFrame(() => e.target.select());
        }}
        onChange={(e) => {
          const next = e.target.value;
          setDraft(next);
          onValueChange(parseMoneyInput(next));
        }}
        onBlur={(e) => {
          setFocused(false);
          const parsed = parseMoneyInput(draft);
          onValueChange(parsed);
          setDraft(parsed);
          onBlur?.(e);
        }}
        {...rest}
      />
    </span>
  );
}
