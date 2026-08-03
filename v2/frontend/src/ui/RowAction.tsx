import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  to?: never;
  children: ReactNode;
  "data-testid"?: string;
};

type LinkActionProps = Omit<LinkProps, "className"> & {
  children: ReactNode;
  className?: string;
  "data-testid"?: string;
};

type Props = ButtonProps | LinkActionProps;

function isLink(props: Props): props is LinkActionProps {
  return "to" in props && props.to != null;
}

/** Ação de linha DS — botão ou Link semântico. */
export function RowAction(props: Props) {
  const testId = props["data-testid"] ?? "row-action";
  if (isLink(props)) {
    const { className, children, "data-testid": _t, ...rest } = props;
    return (
      <Link
        {...rest}
        className={["row-action", "row-link", className].filter(Boolean).join(" ")}
        data-testid={testId}
      >
        {children}
      </Link>
    );
  }
  const { className, children, type = "button", ...rest } = props;
  return (
    <button
      type={type}
      className={["row-action", "ui-button", "ui-button--ghost", className].filter(Boolean).join(" ")}
      data-testid={testId}
      {...rest}
    >
      {children}
    </button>
  );
}
