import { useEffect, useState, type InputHTMLAttributes } from "react";
import { parseMoneyInput } from "./MoneyInput";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type"> & {
  value: string;
  onValueChange: (next: string) => void;
  fractionDigits?: number;
  invalid?: boolean;
};

function formatRateDisplay(apiValue: string, fractionDigits: number): string {
  if (!apiValue.trim()) return "";
  const n = Number(apiValue);
  if (!Number.isFinite(n)) return apiValue;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(n);
}

/** Input de taxa: exibe localizado; emite string com ponto sem arredondar para 2 casas. */
export function RateInput({
  value,
  onValueChange,
  fractionDigits = 4,
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

  const display = focused ? draft : formatRateDisplay(value, fractionDigits);

  return (
    <input
      type="text"
      inputMode="decimal"
      className={["ds-input", "rate-input", "num", invalid ? "ds-input--invalid" : null, className]
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
  );
}
