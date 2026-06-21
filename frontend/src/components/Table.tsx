import type { ReactNode } from "react";

interface TableProps {
  children: ReactNode;
  className?: string;
}

export function Table({ children, className = "" }: TableProps) {
  return (
    <div className="ui-table-wrap">
      <table className={`ui-table ${className}`.trim()}>{children}</table>
    </div>
  );
}
