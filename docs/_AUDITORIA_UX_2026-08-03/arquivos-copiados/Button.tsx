import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  busy?: boolean;
  children: ReactNode;
};

export function Button({
  variant = "primary",
  size = "md",
  busy = false,
  disabled,
  className,
  children,
  type = "button",
  ...rest
}: Props) {
  const classes = [
    "ui-button",
    variant === "secondary" ? "ui-button--secondary" : null,
    variant === "ghost" ? "ui-button--ghost" : null,
    variant === "danger" ? "ui-button--danger" : null,
    size === "lg" ? "ui-button--lg" : null,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {children}
    </button>
  );
}
