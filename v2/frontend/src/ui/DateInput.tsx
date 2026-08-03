import type { InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  invalid?: boolean;
};

/** Date input nativo estilizado (`type="date"`). */
export function DateInput({ className, invalid, ...rest }: Props) {
  return (
    <input
      type="date"
      className={["ds-input", "date-input", invalid ? "ds-input--invalid" : null, className]
        .filter(Boolean)
        .join(" ")}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
}
