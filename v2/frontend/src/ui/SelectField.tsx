import type { SelectHTMLAttributes } from "react";

export type SelectOption = { value: string; label: string; disabled?: boolean };

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  options: SelectOption[];
  invalid?: boolean;
  placeholder?: string;
};

/** Select nativo estilizado (appearance:none via CSS). */
export function SelectField({
  options,
  className,
  invalid,
  placeholder,
  children,
  ...rest
}: Props) {
  return (
    <select
      className={["ds-select", invalid ? "ds-input--invalid" : null, className].filter(Boolean).join(" ")}
      aria-invalid={invalid || undefined}
      {...rest}
    >
      {placeholder ? (
        <option value="" disabled={rest.required}>
          {placeholder}
        </option>
      ) : null}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} disabled={opt.disabled}>
          {opt.label}
        </option>
      ))}
      {children}
    </select>
  );
}
