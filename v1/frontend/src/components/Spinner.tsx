interface SpinnerProps {
  size?: "sm" | "md";
}

export function Spinner({ size = "md" }: SpinnerProps) {
  return <span className={`ui-spinner ui-spinner--${size}`} role="status" aria-label="Carregando" />;
}

export function LoadingState({
  label = "Carregando...",
  detail,
}: {
  label?: string;
  detail?: string;
}) {
  return (
    <div className="ui-loading">
      <Spinner />
      <span>
        {label}
        {detail ? <span className="ui-loading__detail"> — {detail}</span> : null}
      </span>
    </div>
  );
}
