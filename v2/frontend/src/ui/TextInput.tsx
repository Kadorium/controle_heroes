import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean;
};

/** Input de texto estilizado DS — nativo no DOM. */
export function TextInput({ className, invalid, ...rest }: Props) {
  return (
    <input
      className={["ds-input", invalid ? "ds-input--invalid" : null, className].filter(Boolean).join(" ")}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
}
