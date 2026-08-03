import type { ReactNode } from "react";

type Props = {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
};

/** Wrapper label + hint/erro + controle. */
export function FormField({
  label,
  htmlFor,
  hint,
  error,
  required,
  children,
  className,
}: Props) {
  return (
    <div
      className={["form-field", error ? "form-field--error" : null, className].filter(Boolean).join(" ")}
      data-testid="form-field"
    >
      <label className="form-field-label" htmlFor={htmlFor}>
        {label}
        {required ? <span className="form-field-required" aria-hidden="true"> *</span> : null}
      </label>
      {children}
      {error ? (
        <p className="form-field-error" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="form-field-hint">{hint}</p>
      ) : null}
    </div>
  );
}
