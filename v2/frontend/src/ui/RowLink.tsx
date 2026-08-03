import { Link, type LinkProps } from "react-router-dom";

type Props = LinkProps & { "data-testid"?: string };

/** Ação de linha: navegação via Link com visual DS (não sublinhado cru). */
export function RowLink({ className, children, "data-testid": testId = "row-link", ...props }: Props) {
  return (
    <Link {...props} className={className ? `row-link ${className}` : "row-link"} data-testid={testId}>
      {children}
    </Link>
  );
}
