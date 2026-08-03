import type { ReactNode } from "react";

type Tone = "info" | "warning" | "danger";

type Props = {
  tone?: Tone;
  title?: string;
  children: ReactNode;
  className?: string;
  "data-testid"?: string;
};

/** Banner de aviso operacional (info / warning / danger). */
export function Notice({
  tone = "info",
  title,
  children,
  className,
  "data-testid": testId = "notice",
}: Props) {
  return (
    <div
      className={["notice", `notice--${tone}`, className].filter(Boolean).join(" ")}
      role={tone === "danger" ? "alert" : "status"}
      data-testid={testId}
    >
      {title ? <strong className="notice-title">{title}</strong> : null}
      <div className="notice-body">{children}</div>
    </div>
  );
}
