import type { ReactNode } from "react";
import { Button } from "./Button";

export function EmptyState({
  message,
  title,
  action,
  orientation,
}: {
  message: string;
  title?: string;
  action?: ReactNode;
  orientation?: string;
}) {
  return (
    <div className="empty-state" data-testid="empty-state">
      {title ? <p className="empty-state-title">{title}</p> : null}
      <p className="empty">{message}</p>
      {orientation ? <p className="muted empty-state-orientation">{orientation}</p> : null}
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  retryLabel = "Tentar novamente",
}: {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div className="error error-state" role="alert" data-testid="error-state">
      <p>{message}</p>
      {onRetry ? (
        <Button type="button" variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}

export function LoadingState({ message = "Carregando…" }: { message?: string }) {
  return (
    <p className="muted" data-testid="loading-state">
      {message}
    </p>
  );
}
