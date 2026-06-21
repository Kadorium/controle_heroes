interface SpinnerProps {
  size?: "sm" | "md";
}

export function Spinner({ size = "md" }: SpinnerProps) {
  return <span className={`ui-spinner ui-spinner--${size}`} role="status" aria-label="Carregando" />;
}

export function LoadingState({ label = "Carregando..." }: { label?: string }) {
  return (
    <div className="ui-loading">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}
