import { useState, type ChangeEvent, type InputHTMLAttributes } from "react";
import { formatDateOnly, parseDateToIso } from "./format";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  invalid?: boolean;
};

function emitIso(
  e: ChangeEvent<HTMLInputElement>,
  iso: string,
  onChange?: (ev: ChangeEvent<HTMLInputElement>) => void,
) {
  if (!onChange) return;
  onChange({
    ...e,
    target: { value: iso } as HTMLInputElement,
    currentTarget: { value: iso } as HTMLInputElement,
  });
}

/** Data em dd/mm/aaaa na tela; o valor enviado continua YYYY-MM-DD. */
export function DateInput({ className, invalid, value, onChange, onFocus, onBlur, ...rest }: Props) {
  const iso = typeof value === "string" ? value.slice(0, 10) : "";
  const [focused, setFocused] = useState(false);
  const [draft, setDraft] = useState("");
  const formatted = iso ? formatDateOnly(iso) : "";
  const shown = focused ? draft : formatted === "—" ? "" : formatted;

  return (
    <input
      {...rest}
      type="text"
      inputMode="numeric"
      placeholder="dd/mm/aaaa"
      autoComplete="off"
      lang="pt-BR"
      className={["ds-input", "date-input", invalid ? "ds-input--invalid" : null, className]
        .filter(Boolean)
        .join(" ")}
      aria-invalid={invalid || undefined}
      value={shown}
      onFocus={(e) => {
        setFocused(true);
        setDraft(iso ? formatDateOnly(iso) : "");
        onFocus?.(e);
      }}
      onChange={(e) => {
        const raw = e.target.value;
        setDraft(raw);
        if (!raw.trim()) {
          emitIso(e, "", onChange);
          return;
        }
        const parsed = parseDateToIso(raw);
        if (parsed) emitIso(e, parsed, onChange);
      }}
      onBlur={(e) => {
        const parsed = parseDateToIso(e.target.value);
        setFocused(false);
        if (parsed) emitIso(e, parsed, onChange);
        else setDraft(iso ? formatDateOnly(iso) : "");
        onBlur?.(e);
      }}
    />
  );
}
