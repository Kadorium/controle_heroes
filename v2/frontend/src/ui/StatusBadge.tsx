import {
  statusLabel,
  statusSemantics,
  type StatusEntity,
  type StatusSemantics,
} from "./statusLabels";

const SEMANTICS_CLASS: Record<StatusSemantics, string> = {
  neutral: "status-neutral",
  information: "status-info",
  success: "status-ok",
  warning: "status-warn",
  danger: "status-bad",
};

export function StatusBadge({
  status,
  entity = "generic",
}: {
  status: string;
  entity?: StatusEntity;
}) {
  const label = statusLabel(status, entity);
  const semantics = statusSemantics(status, entity);
  return (
    <span
      className={`status-badge ${SEMANTICS_CLASS[semantics]}`}
      data-testid="status-badge"
      data-status={status}
      data-semantics={semantics}
    >
      <span className="status-mark" aria-hidden />
      {label}
    </span>
  );
}
