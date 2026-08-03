import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  pressed?: boolean;
  children: ReactNode;
};

/** Chip de filtro — base DS (§27.2). Adoção nas filas = incrementos verticais. */
export function FilterChip({ pressed = false, className, children, type = "button", ...rest }: Props) {
  return (
    <button
      type={type}
      className={["filter-chip", pressed ? "is-on" : null, className].filter(Boolean).join(" ")}
      aria-pressed={pressed}
      {...rest}
    >
      {children}
    </button>
  );
}
