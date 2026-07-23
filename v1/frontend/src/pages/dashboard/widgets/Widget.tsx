import type { ReactNode } from "react";
import { DotsIcon } from "../icons";

interface WidgetProps {
  title: string;
  count?: number;
  span: 4 | 5 | 6 | 7 | 8 | 12;
  children: ReactNode;
}

export function Widget({ title, count, span, children }: WidgetProps) {
  return (
    <div className={`w col-${span}`}>
      <div className="w-head">
        <h3>{title}</h3>
        {count != null && <span className="w-count">{count}</span>}
        <div className="w-grip" aria-hidden>
          <DotsIcon className="ico" />
        </div>
      </div>
      <div className="w-body">{children}</div>
    </div>
  );
}
